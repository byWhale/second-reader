"""Ingest manually provided source books into the managed local source library.

Phase 1 of the dataset-platform work is a managed source intake layer:
- operator drops books into `state/library_inbox/`
- this CLI copies them into canonical paths under `state/library_sources/`
- lightweight source records are persisted in `state/dataset_build/source_catalog.json`
- per-run summaries are written under `state/dataset_build/source_intake_runs/`

This intentionally stops before parse/screen/build. Later dataset-platform stages
should consume the catalog and drive screening, target-case mining, review, and
iterative rebuild from there.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from src.iterator_reader.language import detect_book_language
from src.iterator_reader.parse import extract_plain_text
from src.parsers import parse_ebook


ROOT = Path(__file__).resolve().parents[2]
STATE_ROOT = ROOT / "state"
LIBRARY_INBOX_ROOT = STATE_ROOT / "library_inbox"
LIBRARY_SOURCE_ROOT = STATE_ROOT / "library_sources"
DATASET_BUILD_ROOT = STATE_ROOT / "dataset_build"
SOURCE_CATALOG_PATH = DATASET_BUILD_ROOT / "source_catalog.json"
SOURCE_CATALOG_MD_PATH = DATASET_BUILD_ROOT / "source_catalog.md"
SOURCE_INTAKE_RUNS_ROOT = DATASET_BUILD_ROOT / "source_intake_runs"

LANGUAGE_CHOICES = ("en", "zh")
VISIBILITY_CHOICES = ("public", "private")
SUPPORTED_SOURCE_SUFFIXES = {".epub"}
SOURCE_METADATA_SUFFIX = ".source.json"
CATALOG_VERSION = 1


@dataclass(frozen=True)
class SourceIntakePaths:
    root: Path
    state_root: Path
    library_inbox_root: Path
    library_source_root: Path
    dataset_build_root: Path
    source_catalog_path: Path
    source_catalog_md_path: Path
    source_intake_runs_root: Path

    @classmethod
    def from_root(cls, root: Path) -> "SourceIntakePaths":
        resolved = root.expanduser().resolve()
        state_root = resolved / "state"
        dataset_build_root = state_root / "dataset_build"
        return cls(
            root=resolved,
            state_root=state_root,
            library_inbox_root=state_root / "library_inbox",
            library_source_root=state_root / "library_sources",
            dataset_build_root=dataset_build_root,
            source_catalog_path=dataset_build_root / "source_catalog.json",
            source_catalog_md_path=dataset_build_root / "source_catalog.md",
            source_intake_runs_root=dataset_build_root / "source_intake_runs",
        )


@dataclass(frozen=True)
class InboxSource:
    source_path: Path
    relative_path: Path
    batch_id: str
    metadata_path: Path | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = re.split(r"[|,]", value)
    elif isinstance(value, list):
        items = [str(item) for item in value]
    else:
        items = [str(value)]
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = _clean_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)
    return cleaned


def _metadata_path_for(source_path: Path) -> Path:
    return source_path.with_suffix(SOURCE_METADATA_SUFFIX)


def _sanitize_filename_stem(value: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", _clean_text(value), flags=re.UNICODE)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._-")
    return cleaned.casefold()


def _sanitize_identifier(value: str) -> str:
    cleaned = _sanitize_filename_stem(value)
    cleaned = cleaned.replace("-", "_")
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def _guess_title_from_filename(path: Path) -> str:
    stem = path.stem
    guessed = stem.replace("_", " ").replace("-", " ")
    guessed = re.sub(r"\s+", " ", guessed).strip()
    return guessed or stem


def _batch_id_for(relative_path: Path) -> str:
    if len(relative_path.parts) <= 1:
        return ""
    return "/".join(relative_path.parts[:-1])


def _existing_record_by_sha(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for record in records:
        sha = _clean_text(record.get("sha256"))
        if sha:
            indexed[sha] = record
    return indexed


def _catalog_sort_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _clean_text(record.get("language")),
        _clean_text(record.get("source_id")),
        _clean_text(record.get("visibility")),
    )


def load_catalog(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "version": CATALOG_VERSION,
            "updated_at": "",
            "record_count": 0,
            "records": [],
        }
    payload = load_json(path)
    payload.setdefault("version", CATALOG_VERSION)
    payload.setdefault("updated_at", "")
    payload.setdefault("record_count", len(payload.get("records", [])))
    payload.setdefault("records", [])
    return payload


def _read_source_metadata(source: InboxSource) -> tuple[dict[str, Any], str]:
    if source.metadata_path is None or not source.metadata_path.exists():
        return ({}, "inferred")
    payload = load_json(source.metadata_path)
    return (payload, "sidecar")


def _normalize_language(value: Any) -> str:
    lowered = _clean_text(value).lower()
    if lowered.startswith("zh"):
        return "zh"
    if lowered.startswith("en"):
        return "en"
    raise ValueError(f"Unsupported language override for {value!r}; expected en or zh")


def _normalize_visibility(value: Any) -> str:
    lowered = _clean_text(value).lower()
    if not lowered:
        return "private"
    if lowered in VISIBILITY_CHOICES:
        return lowered
    raise ValueError(f"Unsupported visibility override for {value!r}; expected public or private")


def _sample_source_text(path: Path) -> str:
    if path.suffix.lower() == ".epub":
        try:
            chapters = parse_ebook(str(path))
        except Exception:
            return ""
        samples: list[str] = []
        total_chars = 0
        for chapter in chapters[:3]:
            text = extract_plain_text(str(chapter.get("content", "")))
            if not text:
                continue
            clipped = text[:600]
            samples.append(clipped)
            total_chars += len(clipped)
            if total_chars >= 1500:
                break
        return "\n".join(samples)
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:1500]
    except Exception:
        return ""


def _resolve_source_language(source_path: Path, metadata: dict[str, Any]) -> str:
    override = metadata.get("language")
    if _clean_text(override):
        return _normalize_language(override)
    detected = detect_book_language(source_path, sample_text=_sample_source_text(source_path))
    if detected in LANGUAGE_CHOICES:
        return detected
    raise ValueError(f"Could not resolve supported language for {source_path}")


def _normalize_metadata(source: InboxSource) -> dict[str, Any]:
    payload, metadata_source = _read_source_metadata(source)
    title = _clean_text(payload.get("title")) or _guess_title_from_filename(source.source_path)
    canonical_filename = _clean_text(payload.get("canonical_filename"))
    preferred_stem = _sanitize_filename_stem(Path(canonical_filename).stem if canonical_filename else title)
    if not preferred_stem:
        preferred_stem = _sanitize_filename_stem(source.source_path.stem) or f"source_{sha256_file(source.source_path)[:8]}"
    preferred_suffix = Path(canonical_filename).suffix.lower() if canonical_filename else source.source_path.suffix.lower()
    language = _resolve_source_language(source.source_path, payload)
    visibility = _normalize_visibility(payload.get("visibility"))
    source_id = _clean_text(payload.get("source_id"))
    if not source_id:
        source_id = f"{_sanitize_identifier(preferred_stem) or 'source'}_{language}"
    return {
        "source_id": source_id,
        "title": title,
        "author": _clean_text(payload.get("author")),
        "language": language,
        "visibility": visibility,
        "canonical_stem": preferred_stem,
        "canonical_suffix": preferred_suffix or source.source_path.suffix.lower(),
        "type_tags": _normalize_list(payload.get("type_tags")),
        "role_tags": _normalize_list(payload.get("role_tags")),
        "notes": _normalize_list(payload.get("notes")),
        "selection_priority": int(payload.get("selection_priority", 9999) or 9999),
        "origin": _clean_text(payload.get("origin")) or "manual_library_inbox",
        "metadata_source": metadata_source,
    }


def discover_inbox_sources(
    paths: SourceIntakePaths,
    *,
    limit: int = 0,
) -> tuple[list[InboxSource], list[dict[str, Any]]]:
    discovered: list[InboxSource] = []
    skipped: list[dict[str, Any]] = []
    if not paths.library_inbox_root.exists():
        return discovered, skipped

    for candidate in sorted(path for path in paths.library_inbox_root.rglob("*") if path.is_file()):
        if candidate.name.endswith(SOURCE_METADATA_SUFFIX):
            continue
        relative_path = candidate.relative_to(paths.library_inbox_root)
        if candidate.suffix.lower() not in SUPPORTED_SOURCE_SUFFIXES:
            skipped.append(
                {
                    "status": "skipped_unsupported_extension",
                    "source_path": str(candidate),
                    "reason": f"supported extensions: {sorted(SUPPORTED_SOURCE_SUFFIXES)}",
                }
            )
            continue
        metadata_path = _metadata_path_for(candidate)
        discovered.append(
            InboxSource(
                source_path=candidate,
                relative_path=relative_path,
                batch_id=_batch_id_for(relative_path),
                metadata_path=metadata_path if metadata_path.exists() else None,
            )
        )
        if limit > 0 and len(discovered) >= limit:
            break
    return discovered, skipped


def _destination_relative_path(
    *,
    language: str,
    visibility: str,
    canonical_stem: str,
    suffix: str,
) -> Path:
    # Visibility is now compatibility metadata only; canonical managed copies
    # live in one language-rooted source tree regardless of distribution status.
    filename = f"{canonical_stem}{suffix}"
    return Path(language) / filename


def _resolve_destination_path(paths: SourceIntakePaths, relative_path: Path, source_sha: str) -> Path:
    destination = paths.library_source_root / relative_path
    if not destination.exists():
        return destination
    if destination.is_file() and sha256_file(destination) == source_sha:
        return destination
    suffix = destination.suffix
    stem = destination.stem
    candidate = destination.with_name(f"{stem}_{source_sha[:8]}{suffix}")
    if not candidate.exists():
        return candidate
    if candidate.is_file() and sha256_file(candidate) == source_sha:
        return candidate
    raise FileExistsError(f"Could not allocate canonical destination for {relative_path}")


def _merge_record(existing: dict[str, Any], candidate: dict[str, Any], *, seen_at: str, inbox_relative_path: str, batch_id: str) -> bool:
    updated = False
    existing_metadata_source = _clean_text(existing.get("metadata_source"))
    candidate_metadata_source = _clean_text(candidate.get("metadata_source"))
    for field in ("title", "author"):
        candidate_value = _clean_text(candidate.get(field))
        if not candidate_value:
            continue
        if candidate_metadata_source == "sidecar" and _clean_text(existing.get(field)) != candidate_value:
            existing[field] = candidate[field]
            updated = True
            continue
        if not _clean_text(existing.get(field)):
            existing[field] = candidate[field]
            updated = True
            continue
    if candidate_metadata_source == "sidecar" and existing_metadata_source != "sidecar":
        existing["metadata_source"] = "sidecar"
        updated = True
    if candidate.get("source_id") and _clean_text(existing.get("source_id")) != _clean_text(candidate.get("source_id")):
        if not _clean_text(existing.get("source_id")):
            existing["source_id"] = candidate["source_id"]
            updated = True
    for field in ("type_tags", "role_tags", "notes"):
        merged = list(existing.get(field) or [])
        for item in candidate.get(field) or []:
            if item not in merged:
                merged.append(item)
        if merged != list(existing.get(field) or []):
            existing[field] = merged
            updated = True
    existing_paths = list(existing.get("inbox_relative_paths") or [])
    if inbox_relative_path not in existing_paths:
        existing_paths.append(inbox_relative_path)
        existing["inbox_relative_paths"] = existing_paths
        updated = True
    batch_ids = list(existing.get("ingest_batch_ids") or [])
    if batch_id and batch_id not in batch_ids:
        batch_ids.append(batch_id)
        existing["ingest_batch_ids"] = batch_ids
        updated = True
    seen_count = int(existing.get("seen_count", 1) or 1) + 1
    existing["seen_count"] = seen_count
    existing["last_seen_at"] = seen_at
    return updated


def render_catalog_markdown(catalog: dict[str, Any]) -> str:
    records = list(catalog.get("records") or [])
    language_counts = Counter(_clean_text(record.get("language")) or "unknown" for record in records)
    lines = [
        "# Source Catalog",
        "",
        f"- updated_at: `{catalog.get('updated_at', '')}`",
        f"- record_count: `{len(records)}`",
        f"- language_counts: `{json.dumps(dict(sorted(language_counts.items())), ensure_ascii=False)}`",
        "- visibility is retained only as compatibility metadata and is not a primary intake or build axis.",
        "",
        "## Records",
        "",
    ]
    for record in sorted(records, key=_catalog_sort_key):
        lines.extend(
            [
                f"- `{record.get('source_id', '')}`",
                f"  - title: `{record.get('title', '')}`",
                f"  - author: `{record.get('author', '')}`",
                f"  - language: `{record.get('language', '')}`",
                f"  - relative_local_path: `{record.get('relative_local_path', '')}`",
                f"  - original_filename: `{record.get('original_filename', '')}`",
                f"  - sha256: `{record.get('sha256', '')}`",
                f"  - parse_status: `{record.get('parse_status', '')}`",
                f"  - screening_status: `{record.get('screening_status', '')}`",
                f"  - packaging_status: `{record.get('packaging_status', '')}`",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_run_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Source Intake Run `{summary.get('run_id', '')}`",
        "",
        f"- generated_at: `{summary.get('generated_at', '')}`",
        f"- candidate_count: `{summary.get('candidate_count', 0)}`",
        f"- ingested_count: `{summary.get('ingested_count', 0)}`",
        f"- existing_count: `{summary.get('existing_count', 0)}`",
        f"- skipped_count: `{summary.get('skipped_count', 0)}`",
        "",
        "## Results",
        "",
    ]
    for result in summary.get("results", []):
        lines.append(
            f"- `{result.get('status', '')}` `{result.get('source_id', result.get('source_path', ''))}`"
        )
    return "\n".join(lines).rstrip() + "\n"


def run_source_intake(
    paths: SourceIntakePaths,
    *,
    language: str | None = None,
    visibility: str | None = None,
    limit: int = 0,
    dry_run: bool = False,
    run_id: str | None = None,
) -> dict[str, Any]:
    catalog = load_catalog(paths.source_catalog_path)
    records = list(catalog.get("records") or [])
    by_sha = _existing_record_by_sha(records)

    discovered, skipped = discover_inbox_sources(paths)
    generated_at = utc_now()
    run_id = run_id or default_run_id()

    results: list[dict[str, Any]] = []
    ingested_count = 0
    existing_count = 0
    candidate_count = 0

    for source in discovered:
        metadata = _normalize_metadata(source)
        resolved_language = str(metadata["language"])
        resolved_visibility = str(metadata["visibility"])
        if language and resolved_language != language:
            continue
        if visibility and resolved_visibility != visibility:
            continue
        if limit > 0 and candidate_count >= limit:
            break
        candidate_count += 1
        source_sha = sha256_file(source.source_path)
        inbox_relative_path = str(source.relative_path)
        existing = by_sha.get(source_sha)
        if existing is not None:
            _merge_record(
                existing,
                metadata,
                seen_at=generated_at,
                inbox_relative_path=inbox_relative_path,
                batch_id=source.batch_id,
            )
            results.append(
                {
                    "status": "already_cataloged",
                    "source_id": existing.get("source_id", ""),
                    "source_path": str(source.source_path),
                    "relative_local_path": existing.get("relative_local_path", ""),
                    "sha256": source_sha,
                }
            )
            existing_count += 1
            continue

        relative_destination = _destination_relative_path(
            language=resolved_language,
            visibility=resolved_visibility,
            canonical_stem=metadata["canonical_stem"],
            suffix=metadata["canonical_suffix"],
        )
        destination = _resolve_destination_path(paths, relative_destination, source_sha)
        relative_local_path = str(destination.relative_to(paths.root))

        record = {
            "source_id": metadata["source_id"],
            "title": metadata["title"],
            "author": metadata["author"],
            "language": resolved_language,
            "visibility": resolved_visibility,
            "origin": metadata["origin"],
            "relative_local_path": relative_local_path,
            "original_filename": source.source_path.name,
            "inbox_relative_paths": [inbox_relative_path],
            "ingest_batch_ids": [source.batch_id] if source.batch_id else [],
            "metadata_source": metadata["metadata_source"],
            "selection_priority": metadata["selection_priority"],
            "type_tags": metadata["type_tags"],
            "role_tags": metadata["role_tags"],
            "notes": metadata["notes"],
            "sha256": source_sha,
            "file_size": source.source_path.stat().st_size,
            "file_extension": source.source_path.suffix.lower(),
            "first_seen_at": generated_at,
            "last_seen_at": generated_at,
            "seen_count": 1,
            "parse_status": "not_started",
            "screening_status": "not_started",
            "packaging_status": "not_started",
            "acquisition": {
                "kind": "manual_library_inbox",
                "input_filename": source.source_path.name,
                "inbox_relative_path": inbox_relative_path,
                "ingest_batch_id": source.batch_id,
            },
        }
        results.append(
            {
                "status": "planned" if dry_run else "ingested",
                "source_id": record["source_id"],
                "source_path": str(source.source_path),
                "relative_local_path": relative_local_path,
                "sha256": source_sha,
            }
        )
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source.source_path, destination)
            records.append(record)
            by_sha[source_sha] = record
        ingested_count += 1

    results.extend(skipped)
    results.sort(key=lambda item: (_clean_text(item.get("status")), _clean_text(item.get("source_id", item.get("source_path")))))

    summary = {
        "run_id": run_id,
        "generated_at": generated_at,
        "dry_run": dry_run,
        "candidate_count": candidate_count,
        "ingested_count": ingested_count,
        "existing_count": existing_count,
        "skipped_count": len(skipped),
        "results": results,
    }

    if dry_run:
        return summary

    records.sort(key=_catalog_sort_key)
    catalog["updated_at"] = generated_at
    catalog["record_count"] = len(records)
    catalog["records"] = records
    write_json(paths.source_catalog_path, catalog)
    write_markdown(paths.source_catalog_md_path, render_catalog_markdown(catalog))
    write_json(paths.source_intake_runs_root / f"{run_id}.json", summary)
    write_markdown(paths.source_intake_runs_root / f"{run_id}.md", render_run_summary_markdown(summary))
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--language", choices=LANGUAGE_CHOICES)
    parser.add_argument(
        "--visibility",
        choices=VISIBILITY_CHOICES,
        help="Optional compatibility-only filter over resolved visibility metadata.",
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--run-id")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    paths = SourceIntakePaths.from_root(args.root)
    summary = run_source_intake(
        paths,
        language=args.language,
        visibility=args.visibility,
        limit=args.limit,
        dry_run=args.dry_run,
        run_id=args.run_id,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
