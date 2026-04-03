"""Build a combined private-library local supplement from managed source-catalog inputs.

This script now:
- reads managed-source records from `state/dataset_build/source_catalog.json`
- reuses canonical copied books under `state/library_sources/`
- screens every reachable book through the canonical parse pipeline
- writes tracked source/corpus/split/local-ref manifests for the combined local pool
- writes larger local-only supplement datasets under state/eval_local_datasets/

The tracked manifests keep the benchmark family unified across storage modes, while
the text-bearing derived datasets remain local-only because they come from private
or copyrighted source text.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
from typing import Any

try:
    from .corpus_builder import (
        ROOT,
        MANIFEST_ROOT,
        STATE_LOCAL_DATASET_ROOT,
        CandidateSpec,
        chapter_row_from_candidate,
        dataset_manifest,
        load_json,
        load_book_document,
        make_compatibility_fixtures,
        make_runtime_fixtures,
        screen_source_book,
        write_json,
        write_jsonl,
    )
    from .ingest_library_sources import SourceIntakePaths, run_library_source_bootstrap
    from .question_aligned_case_construction import (
        CLUSTERED_SELECTION_MODE,
        CLUSTERED_TARGET_PROFILE_ORDER,
        build_question_aligned_excerpt_scope,
    )
except ImportError:  # pragma: no cover - script execution path
    from corpus_builder import (
        ROOT,
        MANIFEST_ROOT,
        STATE_LOCAL_DATASET_ROOT,
        CandidateSpec,
        chapter_row_from_candidate,
        dataset_manifest,
        load_json,
        load_book_document,
        make_compatibility_fixtures,
        make_runtime_fixtures,
        screen_source_book,
        write_json,
        write_jsonl,
    )
    from ingest_library_sources import SourceIntakePaths, run_library_source_bootstrap
    from question_aligned_case_construction import (
        CLUSTERED_SELECTION_MODE,
        CLUSTERED_TARGET_PROFILE_ORDER,
        build_question_aligned_excerpt_scope,
    )

SOURCE_MANIFEST_ID = "attentional_v2_private_library_screen_v2"
LOCAL_REFS_MANIFEST_ID = "attentional_v2_private_library_v2_local_refs"
CORPUS_MANIFEST_ID = "attentional_v2_private_library_bilingual_v2"
SPLITS_MANIFEST_ID = "attentional_v2_private_library_bilingual_v2_splits"
SOURCE_CATALOG_PATH = ROOT / "state" / "dataset_build" / "source_catalog.json"
TRACKED_SOURCE_MANIFEST_PATH = MANIFEST_ROOT / "source_books" / f"{SOURCE_MANIFEST_ID}.json"

PRIMARY_ROLE_ORDER = ("expository", "argumentative", "narrative_reflective", "reference_heavy")
MAX_CHAPTERS_PER_SOURCE = 4
MIN_RUNTIME_SENTENCE_COUNT = 18
QUESTION_ALIGNED_SCOPE_ID = "attentional_v2_private_library_excerpt_question_aligned_v1"
QUESTION_ALIGNED_EXCERPT_DATASET_IDS = {
    "en": "attentional_v2_private_library_excerpt_en_question_aligned_v1",
    "zh": "attentional_v2_private_library_excerpt_zh_question_aligned_v1",
}
LEGACY_PRIVATE_LIBRARY_FEEDBACK_DATASET_IDS = {
    "en": "attentional_v2_private_library_excerpt_en_v2",
    "zh": "attentional_v2_private_library_excerpt_zh_v2",
}
SCRATCH_RUN_ROOT = ROOT / "state" / "dataset_build" / "build_runs"
DEFAULT_BENCHMARK_MODE = "default"
CLUSTERED_BENCHMARK_MODE = "clustered_benchmark_v1"
BENCHMARK_MODE_VALUES = (DEFAULT_BENCHMARK_MODE, CLUSTERED_BENCHMARK_MODE)
CLUSTERED_BENCHMARK_CHAPTER_CASE_IDS = (
    "supremacy_private_en__13",
    "steve_jobs_private_en__17",
    "zouchu_weiyi_zhenliguan_private_zh__14",
    "meiguoren_de_xingge_private_zh__19",
)
CLUSTERED_CASES_PER_CHAPTER = 12
CLUSTERED_RESERVES_PER_CHAPTER = 4
CLUSTERED_SOURCE_MANIFEST_ID = "attentional_v2_clustered_benchmark_v1_source_books"
CLUSTERED_LOCAL_REFS_MANIFEST_ID = "attentional_v2_clustered_benchmark_v1_local_refs"
CLUSTERED_CORPUS_MANIFEST_ID = "attentional_v2_clustered_benchmark_v1_corpus"
CLUSTERED_SPLITS_MANIFEST_ID = "attentional_v2_clustered_benchmark_v1_splits"
CLUSTERED_QUESTION_ALIGNED_SCOPE_ID = "attentional_v2_clustered_benchmark_v1_excerpt_scope"
CLUSTERED_LIVE_PACKAGE_IDS = {
    "chapter_corpora": {
        "en": "attentional_v2_clustered_benchmark_v1_chapters_en",
        "zh": "attentional_v2_clustered_benchmark_v1_chapters_zh",
    },
    "runtime_fixtures": {
        "en": "attentional_v2_clustered_benchmark_v1_runtime_en",
        "zh": "attentional_v2_clustered_benchmark_v1_runtime_zh",
    },
    "excerpt_cases": {
        "en": "attentional_v2_clustered_benchmark_v1_excerpt_en",
        "zh": "attentional_v2_clustered_benchmark_v1_excerpt_zh",
    },
    "compatibility_fixtures": {
        "shared": "attentional_v2_clustered_benchmark_v1_compat_shared",
    },
}


@dataclass(frozen=True)
class SupplementBuildOptions:
    run_id: str = ""
    scratch: bool = False
    benchmark_mode: str = DEFAULT_BENCHMARK_MODE
    source_ids: tuple[str, ...] = ()
    chapter_case_ids: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    limit_sources: int = 0
    cases_per_chapter: int = 0
    reserves_per_chapter: int = 0
    feedback_dataset_ids: dict[str, str] | None = None
    tracked_override_manifest_path: str = ""
    use_tracked_overrides: bool = True
    bootstrap_catalog_if_missing: bool = True


@dataclass(frozen=True)
class SupplementBuildIds:
    source_manifest_id: str
    source_manifest_file_stem: str
    local_refs_manifest_id: str
    local_refs_manifest_file_stem: str
    corpus_manifest_id: str
    corpus_manifest_file_stem: str
    splits_manifest_id: str
    splits_manifest_file_stem: str
    question_aligned_scope_id: str
    package_ids: dict[str, dict[str, str]]


@dataclass(frozen=True)
class SupplementBuildConfig:
    root: Path
    run_id: str
    scratch: bool
    benchmark_mode: str
    catalog_path: Path
    tracked_override_manifest_path: Path | None
    feedback_dataset_ids: dict[str, str]
    source_ids: tuple[str, ...]
    chapter_case_ids: tuple[str, ...]
    languages: tuple[str, ...]
    limit_sources: int
    cases_per_chapter: int
    reserves_per_chapter: int
    target_profile_ids: tuple[str, ...]
    max_chapters_per_source: int
    manifest_root: Path
    dataset_build_artifact_root: Path
    local_dataset_root: Path
    run_root: Path | None
    ids: SupplementBuildIds
    summary_json_path: Path | None
    summary_md_path: Path | None
    bootstrap_catalog_if_missing: bool


@dataclass
class SupplementBuildState:
    source_records: list[dict[str, Any]]
    source_refs: list[dict[str, Any]]
    chapter_rows_by_language: dict[str, list[dict[str, Any]]]
    runtime_rows_by_language: dict[str, list[dict[str, Any]]]


@dataclass(frozen=True)
class ManifestBundleRefs:
    source_manifest_path: Path
    local_refs_manifest_path: Path
    corpora_manifest_path: Path
    splits_manifest_path: Path
    source_manifest_refs: list[str]
    split_refs: list[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _sanitize_run_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", str(value or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or default_run_id()


LIVE_PACKAGE_IDS = {
    "chapter_corpora": {
        "en": "attentional_v2_private_library_chapters_en_v2",
        "zh": "attentional_v2_private_library_chapters_zh_v2",
    },
    "runtime_fixtures": {
        "en": "attentional_v2_private_library_runtime_en_v2",
        "zh": "attentional_v2_private_library_runtime_zh_v2",
    },
    "excerpt_cases": dict(QUESTION_ALIGNED_EXCERPT_DATASET_IDS),
    "compatibility_fixtures": {
        "shared": "attentional_v2_private_library_compat_shared_v2",
    },
}


def _copy_package_ids(package_ids: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    return {
        family: {track: dataset_id for track, dataset_id in tracks.items()}
        for family, tracks in package_ids.items()
    }


def _suffix_id(value: str, run_id: str) -> str:
    return f"{value}__scratch__{run_id}"


def _benchmark_mode(value: str) -> str:
    cleaned = str(value or "").strip() or DEFAULT_BENCHMARK_MODE
    if cleaned not in BENCHMARK_MODE_VALUES:
        raise ValueError(f"Unsupported benchmark mode: {cleaned}")
    return cleaned


def _normalized_chapter_case_ids(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))


def _chapter_source_id(chapter_case_id: str) -> str:
    prefix, _separator, _chapter_id = str(chapter_case_id).rpartition("__")
    return prefix or str(chapter_case_id)


def live_build_ids(benchmark_mode: str = DEFAULT_BENCHMARK_MODE) -> SupplementBuildIds:
    benchmark_mode = _benchmark_mode(benchmark_mode)
    if benchmark_mode == CLUSTERED_BENCHMARK_MODE:
        return SupplementBuildIds(
            source_manifest_id=CLUSTERED_SOURCE_MANIFEST_ID,
            source_manifest_file_stem=CLUSTERED_SOURCE_MANIFEST_ID,
            local_refs_manifest_id=CLUSTERED_LOCAL_REFS_MANIFEST_ID,
            local_refs_manifest_file_stem=CLUSTERED_LOCAL_REFS_MANIFEST_ID,
            corpus_manifest_id=CLUSTERED_CORPUS_MANIFEST_ID,
            corpus_manifest_file_stem=CLUSTERED_CORPUS_MANIFEST_ID,
            splits_manifest_id=CLUSTERED_SPLITS_MANIFEST_ID,
            splits_manifest_file_stem=CLUSTERED_SPLITS_MANIFEST_ID,
            question_aligned_scope_id=CLUSTERED_QUESTION_ALIGNED_SCOPE_ID,
            package_ids=_copy_package_ids(CLUSTERED_LIVE_PACKAGE_IDS),
        )
    return SupplementBuildIds(
        source_manifest_id=SOURCE_MANIFEST_ID,
        source_manifest_file_stem=SOURCE_MANIFEST_ID,
        local_refs_manifest_id=LOCAL_REFS_MANIFEST_ID,
        local_refs_manifest_file_stem="attentional_v2_private_library_v2",
        corpus_manifest_id=CORPUS_MANIFEST_ID,
        corpus_manifest_file_stem=CORPUS_MANIFEST_ID,
        splits_manifest_id=SPLITS_MANIFEST_ID,
        splits_manifest_file_stem=CORPUS_MANIFEST_ID,
        question_aligned_scope_id=QUESTION_ALIGNED_SCOPE_ID,
        package_ids=_copy_package_ids(LIVE_PACKAGE_IDS),
    )


def namespaced_build_ids(run_id: str, benchmark_mode: str = DEFAULT_BENCHMARK_MODE) -> SupplementBuildIds:
    live_ids = live_build_ids(benchmark_mode)
    return SupplementBuildIds(
        source_manifest_id=_suffix_id(live_ids.source_manifest_id, run_id),
        source_manifest_file_stem=_suffix_id(live_ids.source_manifest_file_stem, run_id),
        local_refs_manifest_id=_suffix_id(live_ids.local_refs_manifest_id, run_id),
        local_refs_manifest_file_stem=_suffix_id(live_ids.local_refs_manifest_file_stem, run_id),
        corpus_manifest_id=_suffix_id(live_ids.corpus_manifest_id, run_id),
        corpus_manifest_file_stem=_suffix_id(live_ids.corpus_manifest_file_stem, run_id),
        splits_manifest_id=_suffix_id(live_ids.splits_manifest_id, run_id),
        splits_manifest_file_stem=_suffix_id(live_ids.splits_manifest_file_stem, run_id),
        question_aligned_scope_id=_suffix_id(live_ids.question_aligned_scope_id, run_id),
        package_ids={
            family: {
                track: _suffix_id(dataset_id, run_id)
                for track, dataset_id in tracks.items()
            }
            for family, tracks in live_ids.package_ids.items()
        },
    )


def _normalized_language_tuple(values: tuple[str, ...]) -> tuple[str, ...]:
    languages = tuple(dict.fromkeys(value.strip() for value in values if value.strip()))
    invalid = sorted(language for language in languages if language not in {"en", "zh"})
    if invalid:
        raise ValueError(f"Unsupported --language values: {', '.join(invalid)}")
    return languages


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_list(value: Any) -> list[str]:
    items = value if isinstance(value, list) else []
    return [str(item).strip() for item in items if str(item).strip()]


def _selection_priority(value: Any, *, fallback: int = 9999) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _language_group(source_records: list[dict[str, Any]], *, language: str) -> list[str]:
    return sorted(str(record["source_id"]) for record in source_records if record["language"] == language)


def _tracked_private_library_overrides(path: Path | None = TRACKED_SOURCE_MANIFEST_PATH) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    payload = load_json(path)
    books = payload.get("books", [])
    if not isinstance(books, list):
        return {}
    overrides: dict[str, dict[str, Any]] = {}
    for record in books:
        if not isinstance(record, dict):
            continue
        source_id = _clean_text(record.get("source_id"))
        if not source_id:
            continue
        overrides[source_id] = dict(record)
    return overrides


def _catalog_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing managed source catalog at {path}. Run make library-source-intake first."
        )
    payload = load_json(path)
    records = payload.get("records", [])
    if not isinstance(records, list):
        raise ValueError(f"Expected 'records' list in managed source catalog at {path}")
    return [dict(record) for record in records if isinstance(record, dict)]


def _resolve_batch_id(record: dict[str, Any], override: dict[str, Any]) -> str:
    override_batch = _clean_text(override.get("acquisition_batch_id"))
    if override_batch:
        return override_batch
    ingest_batches = record.get("ingest_batch_ids")
    if isinstance(ingest_batches, list):
        for value in reversed(ingest_batches):
            cleaned = _clean_text(value)
            if cleaned:
                return cleaned
    acquisition = record.get("acquisition")
    if isinstance(acquisition, dict):
        return _clean_text(acquisition.get("ingest_batch_id"))
    return ""


def load_private_library_source_items(
    *,
    root: Path = ROOT,
    catalog_path: Path = SOURCE_CATALOG_PATH,
    tracked_manifest_path: Path | None = TRACKED_SOURCE_MANIFEST_PATH,
) -> list[dict[str, Any]]:
    # Historical manifest and dataset ids still say "private_library", but the
    # managed source path now stays source-agnostic and does not gate on
    # visibility metadata.
    overrides = _tracked_private_library_overrides(tracked_manifest_path)
    items: list[dict[str, Any]] = []
    for record in _catalog_records(catalog_path):
        language = _clean_text(record.get("language"))
        if language not in {"en", "zh"}:
            continue
        source_id = _clean_text(record.get("source_id"))
        relative_local_path = _clean_text(record.get("relative_local_path"))
        if not source_id or not relative_local_path:
            continue
        if not relative_local_path.startswith("state/library_sources/"):
            continue

        source_path = root / relative_local_path
        if not source_path.exists():
            raise FileNotFoundError(source_path)

        override = overrides.get(source_id, {})
        selection_priority = _selection_priority(record.get("selection_priority"))
        if selection_priority == 9999:
            selection_priority = _selection_priority(override.get("selection_priority"))

        type_tags = _normalize_list(record.get("type_tags")) or _normalize_list(override.get("type_tags"))
        role_tags = _normalize_list(record.get("role_tags")) or _normalize_list(override.get("role_tags"))
        notes = _normalize_list(record.get("notes")) or _normalize_list(override.get("notes"))
        title = _clean_text(record.get("title")) or _clean_text(override.get("title")) or source_path.stem
        author = _clean_text(record.get("author")) or _clean_text(override.get("author"))
        origin = _clean_text(record.get("origin")) or _clean_text(override.get("origin")) or "managed-library-source"
        acquisition_batch_id = _resolve_batch_id(record, override)
        acquisition = record.get("acquisition") if isinstance(record.get("acquisition"), dict) else {}
        promoted_local_path = relative_local_path.replace("state/library_sources/", "", 1)

        items.append(
            {
                "spec": CandidateSpec(
                    source_id=source_id,
                    title=title,
                    author=author,
                    language=language,
                    origin=origin,
                    storage_mode="local-only",
                    promoted_local_path=promoted_local_path,
                    acquisition={"kind": "managed_source_catalog", **acquisition},
                    type_tags=type_tags,
                    role_tags=role_tags,
                    selection_priority=selection_priority,
                    notes=notes,
                ),
                "source_path": source_path,
                "acquisition_batch_id": acquisition_batch_id,
                "origin_filename": _clean_text(record.get("original_filename")) or source_path.name,
                "relative_local_path": relative_local_path,
            }
        )
    items.sort(
        key=lambda item: (
            int(item["spec"].selection_priority),
            str(item["spec"].language),
            str(item["spec"].source_id),
        )
    )
    return items


def build_private_library_splits(source_records: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    splits: dict[str, dict[str, list[str]]] = {
        "all_private_library_sources": {
            "en": _language_group(source_records, language="en"),
            "zh": _language_group(source_records, language="zh"),
        },
        "chapter_corpus_eligible": {
            "en": sorted(
                str(record["source_id"])
                for record in source_records
                if record["language"] == "en" and record["corpus_lane"] == "chapter_corpus_eligible"
            ),
            "zh": sorted(
                str(record["source_id"])
                for record in source_records
                if record["language"] == "zh" and record["corpus_lane"] == "chapter_corpus_eligible"
            ),
        },
        "excerpt_only": {
            "en": sorted(
                str(record["source_id"])
                for record in source_records
                if record["language"] == "en" and record["corpus_lane"] == "excerpt_only"
            ),
            "zh": sorted(
                str(record["source_id"])
                for record in source_records
                if record["language"] == "zh" and record["corpus_lane"] == "excerpt_only"
            ),
        },
        "reject_this_pass": {
            "en": sorted(
                str(record["source_id"])
                for record in source_records
                if record["language"] == "en" and record["corpus_lane"] == "reject"
            ),
            "zh": sorted(
                str(record["source_id"])
                for record in source_records
                if record["language"] == "zh" and record["corpus_lane"] == "reject"
            ),
        },
    }
    batch_ids = sorted({_clean_text(record.get("acquisition_batch_id")) for record in source_records if _clean_text(record.get("acquisition_batch_id"))})
    for batch_id in batch_ids:
        splits[batch_id] = {
            "en": sorted(
                str(record["source_id"])
                for record in source_records
                if record["language"] == "en" and _clean_text(record.get("acquisition_batch_id")) == batch_id
            ),
            "zh": sorted(
                str(record["source_id"])
                for record in source_records
                if record["language"] == "zh" and _clean_text(record.get("acquisition_batch_id")) == batch_id
            ),
        }
    return splits


def _primary_selection_role(role_tags: list[str]) -> str:
    for role in PRIMARY_ROLE_ORDER:
        if role in role_tags:
            return role
    return "reserve"


def _choose_runtime_seed_rows(chapter_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chosen: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    sorted_rows = sorted(
        chapter_rows,
        key=lambda row: (
            -float(row.get("candidate_score", 0.0)),
            int(row.get("selection_priority", 9999)),
            int(row.get("chapter_number", 0)),
        ),
    )
    for row in sorted_rows:
        source_id = str(row["source_id"])
        if source_id in seen_sources:
            continue
        if int(row.get("sentence_count", 0)) < MIN_RUNTIME_SENTENCE_COUNT:
            continue
        chosen.append(dict(row))
        seen_sources.add(source_id)
    return chosen


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text:
            continue
        payload = json.loads(text)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scratch", action="store_true", help="Write a run-scoped scratch namespace instead of the live dataset ids.")
    parser.add_argument("--run-id", default="", help="Optional build run id. Scratch builds default to a generated timestamp.")
    parser.add_argument("--benchmark-mode", choices=BENCHMARK_MODE_VALUES, default=DEFAULT_BENCHMARK_MODE)
    parser.add_argument("--source-id", action="append", default=[], dest="source_ids")
    parser.add_argument("--chapter-case-id", action="append", default=[], dest="chapter_case_ids")
    parser.add_argument("--language", action="append", default=[], dest="languages")
    parser.add_argument("--limit-sources", type=int, default=0)
    parser.add_argument("--cases-per-chapter", type=int, default=0)
    parser.add_argument("--reserves-per-chapter", type=int, default=0)
    parser.add_argument("--feedback-dataset-id-en", default="")
    parser.add_argument("--feedback-dataset-id-zh", default="")
    parser.add_argument("--no-feedback", action="store_true")
    parser.add_argument("--tracked-override-manifest-path", default="")
    parser.add_argument("--no-tracked-overrides", action="store_true")
    parser.add_argument(
        "--no-bootstrap-catalog-if-missing",
        action="store_true",
        help="Do not auto-bootstrap the managed source catalog from existing state/library_sources files when the catalog is missing.",
    )
    return parser


def build_options_from_args(args: argparse.Namespace) -> SupplementBuildOptions:
    if args.no_feedback and (
        str(args.feedback_dataset_id_en).strip() or str(args.feedback_dataset_id_zh).strip()
    ):
        raise ValueError("Do not combine --no-feedback with explicit --feedback-dataset-id-* overrides.")
    if args.no_tracked_overrides and str(args.tracked_override_manifest_path).strip():
        raise ValueError(
            "Do not combine --no-tracked-overrides with --tracked-override-manifest-path."
        )

    benchmark_mode = _benchmark_mode(getattr(args, "benchmark_mode", DEFAULT_BENCHMARK_MODE))
    chapter_case_ids = _normalized_chapter_case_ids(tuple(getattr(args, "chapter_case_ids", ()) or ()))
    cases_per_chapter = int(getattr(args, "cases_per_chapter", 0) or 0)
    reserves_per_chapter = int(getattr(args, "reserves_per_chapter", 0) or 0)

    feedback_dataset_ids: dict[str, str] | None
    if args.no_feedback:
        feedback_dataset_ids = {}
    else:
        feedback_dataset_ids = dict(LEGACY_PRIVATE_LIBRARY_FEEDBACK_DATASET_IDS)
        if str(args.feedback_dataset_id_en).strip():
            feedback_dataset_ids["en"] = str(args.feedback_dataset_id_en).strip()
        if str(args.feedback_dataset_id_zh).strip():
            feedback_dataset_ids["zh"] = str(args.feedback_dataset_id_zh).strip()

    return SupplementBuildOptions(
        run_id=str(args.run_id).strip(),
        scratch=bool(args.scratch),
        benchmark_mode=benchmark_mode,
        source_ids=tuple(str(value).strip() for value in args.source_ids if str(value).strip()),
        chapter_case_ids=chapter_case_ids,
        languages=tuple(str(value).strip() for value in args.languages if str(value).strip()),
        limit_sources=int(args.limit_sources),
        cases_per_chapter=cases_per_chapter,
        reserves_per_chapter=reserves_per_chapter,
        feedback_dataset_ids=feedback_dataset_ids,
        tracked_override_manifest_path=str(args.tracked_override_manifest_path).strip(),
        use_tracked_overrides=not bool(args.no_tracked_overrides),
        bootstrap_catalog_if_missing=not bool(
            getattr(args, "no_bootstrap_catalog_if_missing", False)
        ),
    )


def resolve_build_config(
    options: SupplementBuildOptions,
    *,
    root: Path | None = None,
    manifest_root: Path | None = None,
    local_dataset_root: Path | None = None,
) -> SupplementBuildConfig:
    resolved_root = (root or ROOT).resolve()
    resolved_manifest_root = (manifest_root or MANIFEST_ROOT).resolve()
    resolved_local_dataset_root = (local_dataset_root or STATE_LOCAL_DATASET_ROOT).resolve()
    catalog_path = resolved_root / "state" / "dataset_build" / "source_catalog.json"
    if options.limit_sources < 0:
        raise ValueError("--limit-sources must be 0 or greater.")
    if options.cases_per_chapter < 0:
        raise ValueError("--cases-per-chapter must be 0 or greater.")
    if options.reserves_per_chapter < 0:
        raise ValueError("--reserves-per-chapter must be 0 or greater.")

    benchmark_mode = _benchmark_mode(options.benchmark_mode)
    chapter_case_ids = (
        _normalized_chapter_case_ids(options.chapter_case_ids)
        if options.chapter_case_ids
        else tuple(CLUSTERED_BENCHMARK_CHAPTER_CASE_IDS if benchmark_mode == CLUSTERED_BENCHMARK_MODE else ())
    )
    cases_per_chapter = (
        int(options.cases_per_chapter)
        if options.cases_per_chapter > 0
        else (CLUSTERED_CASES_PER_CHAPTER if benchmark_mode == CLUSTERED_BENCHMARK_MODE else 1)
    )
    reserves_per_chapter = (
        int(options.reserves_per_chapter)
        if options.reserves_per_chapter > 0
        else (CLUSTERED_RESERVES_PER_CHAPTER if benchmark_mode == CLUSTERED_BENCHMARK_MODE else 1)
    )
    target_profile_ids = (
        tuple(CLUSTERED_TARGET_PROFILE_ORDER)
        if benchmark_mode == CLUSTERED_BENCHMARK_MODE
        else tuple()
    )

    run_id = (
        _sanitize_run_id(options.run_id or default_run_id())
        if options.scratch
        else (_sanitize_run_id(options.run_id) if options.run_id else "")
    )
    ids = namespaced_build_ids(run_id, benchmark_mode) if options.scratch else live_build_ids(benchmark_mode)
    run_root = (
        resolved_root / "state" / "dataset_build" / "build_runs" / run_id
        if run_id
        else None
    )
    tracked_override_manifest_path: Path | None
    if not options.use_tracked_overrides:
        tracked_override_manifest_path = None
    elif options.tracked_override_manifest_path:
        tracked_override_manifest_path = Path(options.tracked_override_manifest_path).expanduser().resolve()
    else:
        tracked_override_manifest_path = resolved_manifest_root / "source_books" / f"{SOURCE_MANIFEST_ID}.json"

    return SupplementBuildConfig(
        root=resolved_root,
        run_id=run_id,
        scratch=bool(options.scratch),
        benchmark_mode=benchmark_mode,
        catalog_path=catalog_path,
        tracked_override_manifest_path=tracked_override_manifest_path,
        feedback_dataset_ids=(
            dict(LEGACY_PRIVATE_LIBRARY_FEEDBACK_DATASET_IDS)
            if options.feedback_dataset_ids is None
            else dict(options.feedback_dataset_ids)
        ),
        source_ids=tuple(dict.fromkeys(str(value).strip() for value in options.source_ids if str(value).strip())),
        chapter_case_ids=chapter_case_ids,
        languages=_normalized_language_tuple(options.languages),
        limit_sources=int(options.limit_sources),
        cases_per_chapter=cases_per_chapter,
        reserves_per_chapter=reserves_per_chapter,
        target_profile_ids=target_profile_ids,
        max_chapters_per_source=0 if chapter_case_ids else MAX_CHAPTERS_PER_SOURCE,
        manifest_root=(
            (run_root / "manifests").resolve()
            if options.scratch and run_root is not None
            else resolved_manifest_root
        ),
        dataset_build_artifact_root=(
            run_root.resolve()
            if options.scratch and run_root is not None
            else (resolved_root / "state" / "dataset_build").resolve()
        ),
        local_dataset_root=resolved_local_dataset_root,
        run_root=run_root.resolve() if run_root is not None else None,
        ids=ids,
        summary_json_path=(run_root / "build_summary.json").resolve() if run_root is not None else None,
        summary_md_path=(run_root / "build_summary.md").resolve() if run_root is not None else None,
        bootstrap_catalog_if_missing=bool(options.bootstrap_catalog_if_missing),
    )


def _relative_to_root(path: Path, *, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def filter_source_items(
    items: list[dict[str, Any]],
    *,
    source_ids: tuple[str, ...],
    chapter_case_ids: tuple[str, ...],
    languages: tuple[str, ...],
    limit_sources: int,
) -> list[dict[str, Any]]:
    available_source_ids = {
        str(item["spec"].source_id): item for item in items if "spec" in item
    }
    missing_source_ids = sorted(source_id for source_id in source_ids if source_id not in available_source_ids)
    if missing_source_ids:
        raise ValueError(f"Unknown --source-id values: {', '.join(missing_source_ids)}")

    allowed_source_ids = (
        {_chapter_source_id(chapter_case_id) for chapter_case_id in chapter_case_ids}
        if chapter_case_ids
        else set()
    )
    filtered = [
        item
        for item in items
        if (not source_ids or str(item["spec"].source_id) in source_ids)
        and (not allowed_source_ids or str(item["spec"].source_id) in allowed_source_ids)
        and (not languages or str(item["spec"].language) in languages)
    ]
    if limit_sources > 0:
        filtered = filtered[:limit_sources]
    if not filtered:
        raise ValueError("No managed-library sources matched the requested filters.")
    return filtered


def load_existing_private_library_excerpt_feedback(
    *,
    root: Path | None = None,
    dataset_ids: dict[str, str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    resolved_root = root or ROOT
    resolved_dataset_ids = dataset_ids if dataset_ids is not None else LEGACY_PRIVATE_LIBRARY_FEEDBACK_DATASET_IDS
    rows_by_language: dict[str, list[dict[str, Any]]] = {}
    for language in ("en", "zh"):
        dataset_id = str(resolved_dataset_ids.get(language, "")).strip()
        if not dataset_id:
            rows_by_language[language] = []
            continue
        dataset_path = resolved_root / "state" / "eval_local_datasets" / "excerpt_cases" / dataset_id / "cases.jsonl"
        rows_by_language[language] = _load_jsonl(dataset_path)
    return rows_by_language


def question_aligned_artifact_paths(
    *,
    root: Path | None = None,
    artifact_root: Path | None = None,
    scope_id: str = QUESTION_ALIGNED_SCOPE_ID,
    excerpt_dataset_ids: dict[str, str] | None = None,
) -> dict[str, Any]:
    resolved_root = root or ROOT
    resolved_artifact_root = artifact_root or (resolved_root / "state" / "dataset_build")
    dataset_ids = dict(excerpt_dataset_ids or QUESTION_ALIGNED_EXCERPT_DATASET_IDS)
    return {
        "target_profiles": resolved_artifact_root / "target_profiles" / f"{scope_id}.json",
        "opportunity_maps": {
            language: resolved_artifact_root / "opportunity_maps" / f"{dataset_id}.jsonl"
            for language, dataset_id in dataset_ids.items()
        },
        "candidate_cases": {
            language: resolved_artifact_root / "candidate_cases" / f"{dataset_id}.jsonl"
            for language, dataset_id in dataset_ids.items()
        },
        "reserve_cases": {
            language: resolved_artifact_root / "reserve_cases" / f"{dataset_id}.jsonl"
            for language, dataset_id in dataset_ids.items()
        },
        "adequacy_report": resolved_artifact_root / "adequacy_reports" / f"{scope_id}.json",
    }


def write_question_aligned_artifacts(
    question_aligned_scope: dict[str, Any],
    *,
    root: Path | None = None,
    artifact_root: Path | None = None,
    scope_id: str = QUESTION_ALIGNED_SCOPE_ID,
    excerpt_dataset_ids: dict[str, str] | None = None,
) -> dict[str, Any]:
    resolved_root = root or ROOT
    paths = question_aligned_artifact_paths(
        root=resolved_root,
        artifact_root=artifact_root,
        scope_id=scope_id,
        excerpt_dataset_ids=excerpt_dataset_ids,
    )
    write_json(
        paths["target_profiles"],
        {
            "scope_id": question_aligned_scope["scope_id"],
            "profiles": question_aligned_scope["target_profiles"],
        },
    )
    write_json(paths["adequacy_report"], question_aligned_scope["adequacy_report"])
    opportunity_cards = list(question_aligned_scope.get("opportunity_cards") or [])
    for language in ("en", "zh"):
        write_jsonl(
            paths["opportunity_maps"][language],
            [
                row
                for row in opportunity_cards
                if str(row.get("language_track", "")).strip() == language
            ],
        )
        write_jsonl(
            paths["candidate_cases"][language],
            question_aligned_scope["cases_by_language"].get(language, []),
        )
        write_jsonl(
            paths["reserve_cases"][language],
            question_aligned_scope["reserve_cases_by_language"].get(language, []),
        )
    return {
        "target_profiles": str(paths["target_profiles"].relative_to(resolved_root)),
        "adequacy_report": str(paths["adequacy_report"].relative_to(resolved_root)),
        "opportunity_maps": {
            language: str(path.relative_to(resolved_root))
            for language, path in paths["opportunity_maps"].items()
        },
        "candidate_cases": {
            language: str(path.relative_to(resolved_root))
            for language, path in paths["candidate_cases"].items()
        },
        "reserve_cases": {
            language: str(path.relative_to(resolved_root))
            for language, path in paths["reserve_cases"].items()
        },
    }


def _summary_counts(source_records: list[dict[str, Any]]) -> dict[str, Any]:
    language_counts = Counter(str(record["language"]) for record in source_records)
    lane_counts = Counter(str(record["corpus_lane"]) for record in source_records)
    batch_counts = Counter(str(record["acquisition_batch_id"]) for record in source_records)
    category_counts: Counter[str] = Counter()
    for record in source_records:
        for tag in list(record.get("type_tags") or []):
            category_counts[str(tag)] += 1
    return {
        "book_count_total": len(source_records),
        "language_counts": dict(sorted(language_counts.items())),
        "corpus_lane_counts": dict(sorted(lane_counts.items())),
        "acquisition_batch_counts": dict(sorted(batch_counts.items())),
        "type_tag_counts": dict(sorted(category_counts.items())),
    }


def ensure_source_catalog(config: SupplementBuildConfig) -> dict[str, Any] | None:
    if config.catalog_path.exists():
        return None
    if not config.bootstrap_catalog_if_missing:
        return None
    bootstrap_summary = run_library_source_bootstrap(
        SourceIntakePaths.from_root(config.root),
        dry_run=False,
        run_id=f"{config.run_id or default_run_id()}__bootstrap_sources",
    )
    return bootstrap_summary


def collect_source_build_state(config: SupplementBuildConfig) -> SupplementBuildState:
    items = load_private_library_source_items(
        root=config.root,
        catalog_path=config.catalog_path,
        tracked_manifest_path=config.tracked_override_manifest_path,
    )
    if not items:
        raise ValueError(
            "No private managed-library sources are available in the source catalog. "
            "Run make library-source-intake first, then retry the private-library supplement build."
        )
    items = filter_source_items(
        items,
        source_ids=config.source_ids,
        chapter_case_ids=config.chapter_case_ids,
        languages=config.languages,
        limit_sources=config.limit_sources,
    )

    source_records: list[dict[str, Any]] = []
    source_refs: list[dict[str, Any]] = []
    chapter_rows_by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    requested_chapter_case_ids = set(config.chapter_case_ids)
    found_chapter_case_ids: set[str] = set()

    for item in items:
        spec: CandidateSpec = item["spec"]
        source_path = Path(item["source_path"])
        if not source_path.exists():
            raise FileNotFoundError(source_path)

        relative_local_path = str(item["relative_local_path"])
        record = screen_source_book(
            spec=spec,
            local_path=source_path,
            relative_local_path=relative_local_path,
            acquisition_metadata={
                "download_url": None,
                "input_filename": item["origin_filename"],
                "acquisition_batch_id": item["acquisition_batch_id"],
            },
            selection_priority=spec.selection_priority,
        )
        record["storage_policy"] = "private-local"
        record["screening_status"] = "screened_private_library_v2"
        record["acquisition_batch_id"] = item["acquisition_batch_id"]
        record["origin_filename"] = item["origin_filename"]
        source_records.append(record)
        source_refs.append(
            {
                "source_id": record["source_id"],
                "relative_local_path": record["relative_local_path"],
                "sha256": record["sha256"],
                "file_size": record["file_size"],
                "acquisition_batch_id": item["acquisition_batch_id"],
            }
        )

        candidate_rows = list(record.get("candidate_chapters") or [])
        primary_role = _primary_selection_role(list(record.get("role_tags") or []))
        selected_rows_for_source: list[dict[str, Any]] = []
        for candidate in candidate_rows:
            row = chapter_row_from_candidate(record, candidate)
            if requested_chapter_case_ids and str(row["chapter_case_id"]) not in requested_chapter_case_ids:
                continue
            row["selection_status"] = "private_library_candidate_v2"
            row["selection_role"] = primary_role
            row["corpus_lane"] = str(record["corpus_lane"])
            row["acquisition_batch_id"] = item["acquisition_batch_id"]
            selected_rows_for_source.append(row)
            found_chapter_case_ids.add(str(row["chapter_case_id"]))
        if not requested_chapter_case_ids and config.max_chapters_per_source > 0:
            selected_rows_for_source = selected_rows_for_source[: config.max_chapters_per_source]
        chapter_rows_by_language[str(record["language"])].extend(selected_rows_for_source)

    if requested_chapter_case_ids:
        missing = sorted(requested_chapter_case_ids - found_chapter_case_ids)
        if missing:
            raise ValueError(f"Unknown --chapter-case-id values: {', '.join(missing)}")

    runtime_rows_by_language = {
        language: _choose_runtime_seed_rows(rows) for language, rows in chapter_rows_by_language.items()
    }
    return SupplementBuildState(
        source_records=source_records,
        source_refs=source_refs,
        chapter_rows_by_language=dict(chapter_rows_by_language),
        runtime_rows_by_language=runtime_rows_by_language,
    )


def write_manifest_bundle(
    config: SupplementBuildConfig,
    state: SupplementBuildState,
) -> ManifestBundleRefs:
    source_manifest_path = config.manifest_root / "source_books" / f"{config.ids.source_manifest_file_stem}.json"
    local_refs_manifest_path = config.manifest_root / "local_refs" / f"{config.ids.local_refs_manifest_file_stem}.json"
    corpora_manifest_path = config.manifest_root / "corpora" / f"{config.ids.corpus_manifest_file_stem}.json"
    splits_manifest_path = config.manifest_root / "splits" / f"{config.ids.splits_manifest_file_stem}.json"

    write_json(
        source_manifest_path,
        {
            "manifest_id": config.ids.source_manifest_id,
            "description": (
                "Run-scoped screening inventory for the managed private-library supplement scratch build."
                if config.scratch
                else "Tracked screening inventory for the combined private-library supplement built from the managed source catalog and canonical local source library."
            ),
            "summary": _summary_counts(state.source_records),
            "books": state.source_records,
        },
    )

    local_package_refs: list[dict[str, Any]] = []
    for family, tracks in config.ids.package_ids.items():
        for track, dataset_id in tracks.items():
            local_package_refs.append(
                {
                    "dataset_id": dataset_id,
                    "family": family,
                    "language_track": track,
                    "relative_local_path": _relative_to_root(
                        config.local_dataset_root / family / dataset_id,
                        root=config.root,
                    ),
                }
            )

    write_json(
        local_refs_manifest_path,
        {
            "manifest_id": config.ids.local_refs_manifest_id,
            "description": (
                "Local source-file and local-package references for the scratch private-library supplement build."
                if config.scratch
                else "Local source-file and local-package references for the combined private-library attentional_v2 supplement built from managed source-catalog inputs."
            ),
            "source_refs": state.source_refs,
            "local_dataset_packages": local_package_refs,
        },
    )

    write_json(
        corpora_manifest_path,
        {
            "manifest_id": config.ids.corpus_manifest_id,
            "description": (
                "Run-scoped bilingual private-library source corpus for attentional_v2 evaluation supplementation."
                if config.scratch
                else "Combined bilingual private-library source corpus for attentional_v2 evaluation supplementation, sourced from the managed local source catalog."
            ),
            "language_tracks": {
                "en": [record["source_id"] for record in state.source_records if record["language"] == "en"],
                "zh": [record["source_id"] for record in state.source_records if record["language"] == "zh"],
            },
        },
    )
    write_json(
        splits_manifest_path,
        {
            "manifest_id": config.ids.splits_manifest_id,
            "description": (
                "Split definitions for the scratch private-library supplement build."
                if config.scratch
                else "Split definitions for the combined private-library attentional_v2 supplement built from managed source-catalog inputs."
            ),
            "splits": build_private_library_splits(state.source_records),
        },
    )

    return ManifestBundleRefs(
        source_manifest_path=source_manifest_path,
        local_refs_manifest_path=local_refs_manifest_path,
        corpora_manifest_path=corpora_manifest_path,
        splits_manifest_path=splits_manifest_path,
        source_manifest_refs=[
            _relative_to_root(source_manifest_path, root=config.root),
            _relative_to_root(local_refs_manifest_path, root=config.root),
            _relative_to_root(corpora_manifest_path, root=config.root),
        ],
        split_refs=[_relative_to_root(splits_manifest_path, root=config.root)],
    )


def package_root(config: SupplementBuildConfig, family: str, dataset_id: str) -> Path:
    return config.local_dataset_root / family / dataset_id


def write_local_dataset_packages(
    config: SupplementBuildConfig,
    state: SupplementBuildState,
    *,
    question_aligned_scope: dict[str, Any],
    question_aligned_artifact_refs: dict[str, Any],
    manifest_bundle: ManifestBundleRefs,
    compatibility_rows: list[dict[str, Any]],
) -> None:
    package_ids = config.ids.package_ids
    en_chapter_dataset_id = package_ids["chapter_corpora"]["en"]
    zh_chapter_dataset_id = package_ids["chapter_corpora"]["zh"]
    en_runtime_dataset_id = package_ids["runtime_fixtures"]["en"]
    zh_runtime_dataset_id = package_ids["runtime_fixtures"]["zh"]
    en_excerpt_dataset_id = package_ids["excerpt_cases"]["en"]
    zh_excerpt_dataset_id = package_ids["excerpt_cases"]["zh"]
    compat_dataset_id = package_ids["compatibility_fixtures"]["shared"]
    excerpt_rows_by_language = question_aligned_scope["cases_by_language"]

    write_json(
        package_root(config, "chapter_corpora", en_chapter_dataset_id) / "manifest.json",
        dataset_manifest(
            dataset_id=en_chapter_dataset_id,
            family="chapter_corpora",
            language_track="en",
            description=(
                "English scratch chapter candidates derived from the managed local supplement build."
                if config.scratch
                else "English private-library chapter candidates derived from the combined user-supplied private book pool."
            ),
            primary_file="chapters.jsonl",
            source_manifest_refs=manifest_bundle.source_manifest_refs,
            split_refs=manifest_bundle.split_refs,
            storage_mode="local-only",
        ),
    )
    write_jsonl(
        package_root(config, "chapter_corpora", en_chapter_dataset_id) / "chapters.jsonl",
        state.chapter_rows_by_language.get("en", []),
    )
    write_json(
        package_root(config, "chapter_corpora", zh_chapter_dataset_id) / "manifest.json",
        dataset_manifest(
            dataset_id=zh_chapter_dataset_id,
            family="chapter_corpora",
            language_track="zh",
            description=(
                "Chinese scratch chapter candidates derived from the managed local supplement build."
                if config.scratch
                else "Chinese private-library chapter candidates derived from the combined user-supplied private book pool."
            ),
            primary_file="chapters.jsonl",
            source_manifest_refs=manifest_bundle.source_manifest_refs,
            split_refs=manifest_bundle.split_refs,
            storage_mode="local-only",
        ),
    )
    write_jsonl(
        package_root(config, "chapter_corpora", zh_chapter_dataset_id) / "chapters.jsonl",
        state.chapter_rows_by_language.get("zh", []),
    )

    write_json(
        package_root(config, "runtime_fixtures", en_runtime_dataset_id) / "manifest.json",
        dataset_manifest(
            dataset_id=en_runtime_dataset_id,
            family="runtime_fixtures",
            language_track="en",
            description=(
                "English runtime/resume fixtures derived from the scratch local supplement build."
                if config.scratch
                else "English runtime/resume fixtures derived from the combined private-library supplement."
            ),
            primary_file="fixtures.jsonl",
            source_manifest_refs=manifest_bundle.source_manifest_refs,
            split_refs=manifest_bundle.split_refs,
            storage_mode="local-only",
        ),
    )
    write_jsonl(
        package_root(config, "runtime_fixtures", en_runtime_dataset_id) / "fixtures.jsonl",
        make_runtime_fixtures(state.runtime_rows_by_language.get("en", [])),
    )
    write_json(
        package_root(config, "runtime_fixtures", zh_runtime_dataset_id) / "manifest.json",
        dataset_manifest(
            dataset_id=zh_runtime_dataset_id,
            family="runtime_fixtures",
            language_track="zh",
            description=(
                "Chinese runtime/resume fixtures derived from the scratch local supplement build."
                if config.scratch
                else "Chinese runtime/resume fixtures derived from the combined private-library supplement."
            ),
            primary_file="fixtures.jsonl",
            source_manifest_refs=manifest_bundle.source_manifest_refs,
            split_refs=manifest_bundle.split_refs,
            storage_mode="local-only",
        ),
    )
    write_jsonl(
        package_root(config, "runtime_fixtures", zh_runtime_dataset_id) / "fixtures.jsonl",
        make_runtime_fixtures(state.runtime_rows_by_language.get("zh", [])),
    )

    en_excerpt_manifest = {
        **dataset_manifest(
            dataset_id=en_excerpt_dataset_id,
            family="excerpt_cases",
            language_track="en",
            description=(
                "English question-aligned excerpt seed candidates derived from the scratch local supplement build."
                if config.scratch
                else "English question-aligned excerpt seed candidates derived from the combined private-library supplement and current review feedback."
            ),
            primary_file="cases.jsonl",
            source_manifest_refs=manifest_bundle.source_manifest_refs,
            split_refs=manifest_bundle.split_refs,
            storage_mode="local-only",
        ),
        "dataset_build_artifact_refs": [
            question_aligned_artifact_refs["target_profiles"],
            question_aligned_artifact_refs["adequacy_report"],
            question_aligned_artifact_refs["opportunity_maps"]["en"],
            question_aligned_artifact_refs["candidate_cases"]["en"],
            question_aligned_artifact_refs["reserve_cases"]["en"],
        ],
    }
    if config.feedback_dataset_ids.get("en"):
        en_excerpt_manifest["feedback_source_dataset_id"] = config.feedback_dataset_ids["en"]
    write_json(
        package_root(config, "excerpt_cases", en_excerpt_dataset_id) / "manifest.json",
        en_excerpt_manifest,
    )
    write_jsonl(
        package_root(config, "excerpt_cases", en_excerpt_dataset_id) / "cases.jsonl",
        excerpt_rows_by_language.get("en", []),
    )

    zh_excerpt_manifest = {
        **dataset_manifest(
            dataset_id=zh_excerpt_dataset_id,
            family="excerpt_cases",
            language_track="zh",
            description=(
                "Chinese question-aligned excerpt seed candidates derived from the scratch local supplement build."
                if config.scratch
                else "Chinese question-aligned excerpt seed candidates derived from the combined private-library supplement and current review feedback."
            ),
            primary_file="cases.jsonl",
            source_manifest_refs=manifest_bundle.source_manifest_refs,
            split_refs=manifest_bundle.split_refs,
            storage_mode="local-only",
        ),
        "dataset_build_artifact_refs": [
            question_aligned_artifact_refs["target_profiles"],
            question_aligned_artifact_refs["adequacy_report"],
            question_aligned_artifact_refs["opportunity_maps"]["zh"],
            question_aligned_artifact_refs["candidate_cases"]["zh"],
            question_aligned_artifact_refs["reserve_cases"]["zh"],
        ],
    }
    if config.feedback_dataset_ids.get("zh"):
        zh_excerpt_manifest["feedback_source_dataset_id"] = config.feedback_dataset_ids["zh"]
    write_json(
        package_root(config, "excerpt_cases", zh_excerpt_dataset_id) / "manifest.json",
        zh_excerpt_manifest,
    )
    write_jsonl(
        package_root(config, "excerpt_cases", zh_excerpt_dataset_id) / "cases.jsonl",
        excerpt_rows_by_language.get("zh", []),
    )

    write_json(
        package_root(config, "compatibility_fixtures", compat_dataset_id) / "manifest.json",
        dataset_manifest(
            dataset_id=compat_dataset_id,
            family="compatibility_fixtures",
            language_track="shared",
            description=(
                "Shared compatibility fixture specs derived from the scratch local supplement build."
                if config.scratch
                else "Shared compatibility fixture specs derived from the combined private-library supplement."
            ),
            primary_file="fixtures.jsonl",
            source_manifest_refs=manifest_bundle.source_manifest_refs,
            split_refs=manifest_bundle.split_refs,
            storage_mode="local-only",
        ),
    )
    write_jsonl(
        package_root(config, "compatibility_fixtures", compat_dataset_id) / "fixtures.jsonl",
        compatibility_rows,
    )


def build_summary_payload(
    config: SupplementBuildConfig,
    state: SupplementBuildState,
    *,
    bootstrap_summary: dict[str, Any] | None,
    question_aligned_scope: dict[str, Any],
    question_aligned_artifact_refs: dict[str, Any],
    manifest_bundle: ManifestBundleRefs,
    existing_excerpt_feedback: dict[str, list[dict[str, Any]]],
    compatibility_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "generated_at": utc_now(),
        "scratch": config.scratch,
        "run_id": config.run_id,
        "run_root": _relative_to_root(config.run_root, root=config.root) if config.run_root is not None else "",
        "benchmark_mode": config.benchmark_mode,
        "source_catalog_bootstrap": bootstrap_summary,
        "selected_source_ids": [str(record["source_id"]) for record in state.source_records],
        "selected_chapter_case_ids": list(config.chapter_case_ids),
        "selected_languages": sorted({str(record["language"]) for record in state.source_records}),
        "source_filters": {
            "source_ids": list(config.source_ids),
            "chapter_case_ids": list(config.chapter_case_ids),
            "languages": list(config.languages),
            "limit_sources": config.limit_sources,
        },
        "construction_targets": {
            "cases_per_chapter": config.cases_per_chapter,
            "reserves_per_chapter": config.reserves_per_chapter,
            "target_profile_ids": list(config.target_profile_ids),
        },
        "dataset_ids": _copy_package_ids(config.ids.package_ids),
        "feedback_dataset_ids": dict(sorted(config.feedback_dataset_ids.items())),
        "manifest_refs": {
            "source_books": _relative_to_root(manifest_bundle.source_manifest_path, root=config.root),
            "local_refs": _relative_to_root(manifest_bundle.local_refs_manifest_path, root=config.root),
            "corpora": _relative_to_root(manifest_bundle.corpora_manifest_path, root=config.root),
            "splits": _relative_to_root(manifest_bundle.splits_manifest_path, root=config.root),
        },
        "question_aligned_artifact_refs": question_aligned_artifact_refs,
        "books_total": len(state.source_records),
        "books_en": sum(1 for record in state.source_records if record["language"] == "en"),
        "books_zh": sum(1 for record in state.source_records if record["language"] == "zh"),
        "chapter_candidates_en": len(state.chapter_rows_by_language.get("en", [])),
        "chapter_candidates_zh": len(state.chapter_rows_by_language.get("zh", [])),
        "question_aligned_excerpt_cases_en": len(question_aligned_scope["cases_by_language"].get("en", [])),
        "question_aligned_excerpt_cases_zh": len(question_aligned_scope["cases_by_language"].get("zh", [])),
        "question_aligned_reserves_en": len(question_aligned_scope["reserve_cases_by_language"].get("en", [])),
        "question_aligned_reserves_zh": len(question_aligned_scope["reserve_cases_by_language"].get("zh", [])),
        "question_aligned_opportunities_en": len(
            [
                row
                for row in question_aligned_scope["opportunity_cards"]
                if str(row.get("language_track", "")).strip() == "en"
            ]
        ),
        "question_aligned_opportunities_zh": len(
            [
                row
                for row in question_aligned_scope["opportunity_cards"]
                if str(row.get("language_track", "")).strip() == "zh"
            ]
        ),
        "question_aligned_feedback_rows_en": len(existing_excerpt_feedback.get("en", [])),
        "question_aligned_feedback_rows_zh": len(existing_excerpt_feedback.get("zh", [])),
        "question_aligned_recommended_next_action": question_aligned_scope["adequacy_report"]["recommended_next_action"],
        "runtime_fixtures_en": len(make_runtime_fixtures(state.runtime_rows_by_language.get("en", []))),
        "runtime_fixtures_zh": len(make_runtime_fixtures(state.runtime_rows_by_language.get("zh", []))),
        "compatibility_fixtures_shared": len(compatibility_rows),
    }


def render_build_summary_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Private-Library Supplement Build Summary",
            "",
            f"- generated_at: `{summary['generated_at']}`",
            f"- scratch: `{summary['scratch']}`",
            f"- run_id: `{summary['run_id']}`",
            f"- run_root: `{summary['run_root']}`",
            f"- benchmark_mode: `{summary['benchmark_mode']}`",
            f"- source_catalog_bootstrap: `{json.dumps(summary['source_catalog_bootstrap'], ensure_ascii=False, sort_keys=True)}`",
            f"- selected_source_ids: `{', '.join(summary['selected_source_ids'])}`",
            f"- selected_chapter_case_ids: `{', '.join(summary['selected_chapter_case_ids'])}`",
            f"- selected_languages: `{', '.join(summary['selected_languages'])}`",
            f"- dataset_ids: `{json.dumps(summary['dataset_ids'], ensure_ascii=False, sort_keys=True)}`",
            f"- feedback_dataset_ids: `{json.dumps(summary['feedback_dataset_ids'], ensure_ascii=False, sort_keys=True)}`",
            f"- question_aligned_recommended_next_action: `{summary['question_aligned_recommended_next_action']}`",
            "",
            "## Counts",
            f"- books_total: `{summary['books_total']}`",
            f"- chapter_candidates_en: `{summary['chapter_candidates_en']}`",
            f"- chapter_candidates_zh: `{summary['chapter_candidates_zh']}`",
            f"- question_aligned_excerpt_cases_en: `{summary['question_aligned_excerpt_cases_en']}`",
            f"- question_aligned_excerpt_cases_zh: `{summary['question_aligned_excerpt_cases_zh']}`",
            f"- question_aligned_reserves_en: `{summary['question_aligned_reserves_en']}`",
            f"- question_aligned_reserves_zh: `{summary['question_aligned_reserves_zh']}`",
        ]
    )


def write_build_summary(config: SupplementBuildConfig, summary: dict[str, Any]) -> None:
    if config.summary_json_path is None or config.summary_md_path is None:
        return
    write_json(config.summary_json_path, summary)
    config.summary_md_path.parent.mkdir(parents=True, exist_ok=True)
    config.summary_md_path.write_text(
        render_build_summary_markdown(summary).rstrip() + "\n",
        encoding="utf-8",
    )


def build_private_library_supplement(
    options: SupplementBuildOptions | None = None,
    *,
    root: Path | None = None,
    manifest_root: Path | None = None,
    local_dataset_root: Path | None = None,
) -> dict[str, Any]:
    config = resolve_build_config(
        options or SupplementBuildOptions(),
        root=root,
        manifest_root=manifest_root,
        local_dataset_root=local_dataset_root,
    )
    bootstrap_summary = ensure_source_catalog(config)
    state = collect_source_build_state(config)
    existing_excerpt_feedback = load_existing_private_library_excerpt_feedback(
        root=config.root,
        dataset_ids=config.feedback_dataset_ids,
    )
    question_aligned_scope = build_question_aligned_excerpt_scope(
        chapter_rows_by_language=state.chapter_rows_by_language,
        source_index={str(record["source_id"]): record for record in state.source_records},
        existing_rows_by_language=existing_excerpt_feedback,
        dataset_ids_by_language=config.ids.package_ids["excerpt_cases"],
        root=config.root,
        document_loader=load_book_document,
        scope_id=config.ids.question_aligned_scope_id,
        cases_per_chapter=config.cases_per_chapter,
        reserves_per_chapter=config.reserves_per_chapter,
        target_profile_ids=config.target_profile_ids or None,
        selection_mode=(
            CLUSTERED_SELECTION_MODE
            if config.benchmark_mode == CLUSTERED_BENCHMARK_MODE
            else DEFAULT_BENCHMARK_MODE
        ),
    )
    question_aligned_artifact_refs = write_question_aligned_artifacts(
        question_aligned_scope,
        root=config.root,
        artifact_root=config.dataset_build_artifact_root,
        scope_id=config.ids.question_aligned_scope_id,
        excerpt_dataset_ids=config.ids.package_ids["excerpt_cases"],
    )
    compatibility_rows = make_compatibility_fixtures(
        state.runtime_rows_by_language.get("en", []) + state.runtime_rows_by_language.get("zh", [])
    )
    manifest_bundle = write_manifest_bundle(config, state)
    write_local_dataset_packages(
        config,
        state,
        question_aligned_scope=question_aligned_scope,
        question_aligned_artifact_refs=question_aligned_artifact_refs,
        manifest_bundle=manifest_bundle,
        compatibility_rows=compatibility_rows,
    )
    summary = build_summary_payload(
        config,
        state,
        bootstrap_summary=bootstrap_summary,
        question_aligned_scope=question_aligned_scope,
        question_aligned_artifact_refs=question_aligned_artifact_refs,
        manifest_bundle=manifest_bundle,
        existing_excerpt_feedback=existing_excerpt_feedback,
        compatibility_rows=compatibility_rows,
    )
    write_build_summary(config, summary)
    return summary


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = build_parser().parse_args([] if argv is None else argv)
    summary = build_private_library_supplement(build_options_from_args(args))
    print("Combined private-library supplement build complete.")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return summary


def cli(argv: list[str] | None = None) -> int:
    main(sys.argv[1:] if argv is None else argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
