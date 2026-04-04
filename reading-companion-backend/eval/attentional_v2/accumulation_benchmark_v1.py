"""Deterministic long-span benchmark artifacts for split-surface evaluation.

This module intentionally optimizes for a runnable, bounded v1:
- exactly 6 windows
- deterministic probe generation from existing reviewed excerpt rows + notes anchors
- draft/freeze-capable local datasets plus a tracked draft manifest

It does not claim to solve the full long-span review stack. Probe review automation
remains an explicit follow-up lane.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from src.reading_runtime.provisioning import ensure_canonical_parse


ROOT = Path(__file__).resolve().parents[2]

WINDOW_CASES_FAMILY = "window_cases"
ACCUMULATION_PROBES_FAMILY = "accumulation_probes"

WINDOW_DATASET_ID = "attentional_v2_accumulation_benchmark_v1_window_cases"
PROBE_DRAFT_DATASET_ID = "attentional_v2_accumulation_benchmark_v1_probes_draft"
PROBE_FROZEN_DATASET_ID = "attentional_v2_accumulation_benchmark_v1_probes_frozen_draft"

WINDOW_DATASET_DIR = ROOT / "state" / "eval_local_datasets" / WINDOW_CASES_FAMILY / WINDOW_DATASET_ID
PROBE_DRAFT_DATASET_DIR = ROOT / "state" / "eval_local_datasets" / ACCUMULATION_PROBES_FAMILY / PROBE_DRAFT_DATASET_ID
PROBE_FROZEN_DATASET_DIR = ROOT / "state" / "eval_local_datasets" / ACCUMULATION_PROBES_FAMILY / PROBE_FROZEN_DATASET_ID

DRAFT_MANIFEST_PATH = ROOT / "eval" / "manifests" / "splits" / "attentional_v2_accumulation_benchmark_v1_draft.json"

CLUSTERED_SOURCE_MANIFESTS = (
    ROOT / "eval" / "manifests" / "source_books" / "attentional_v2_clustered_benchmark_v1_source_books.json",
    ROOT / "eval" / "manifests" / "local_refs" / "attentional_v2_clustered_benchmark_v1_local_refs.json",
)
NOTES_GUIDED_SOURCE_MANIFESTS = (
    ROOT
    / "state"
    / "dataset_build"
    / "build_runs"
    / "human_notes_guided_dataset_v1_20260404"
    / "manifests"
    / "source_books"
    / "attentional_v2_human_notes_guided_dataset_v1_source_books__scratch__human_notes_guided_dataset_v1_20260404.json",
    ROOT
    / "state"
    / "dataset_build"
    / "build_runs"
    / "human_notes_guided_dataset_v1_20260404"
    / "manifests"
    / "local_refs"
    / "attentional_v2_human_notes_guided_dataset_v1_local_refs__scratch__human_notes_guided_dataset_v1_20260404.json",
)
SOURCE_MANIFEST_PATHS = (*CLUSTERED_SOURCE_MANIFESTS, *NOTES_GUIDED_SOURCE_MANIFESTS)

REVIEWED_EXCERPT_DATASET_DIRS = (
    ROOT / "state" / "eval_local_datasets" / "excerpt_cases" / "attentional_v2_clustered_benchmark_v1_excerpt_en",
    ROOT / "state" / "eval_local_datasets" / "excerpt_cases" / "attentional_v2_clustered_benchmark_v1_excerpt_zh",
    ROOT
    / "state"
    / "eval_local_datasets"
    / "excerpt_cases"
    / "attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404",
    ROOT
    / "state"
    / "eval_local_datasets"
    / "excerpt_cases"
    / "attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_complete_20260404",
)

NOTES_CATALOG_PATH = ROOT / "state" / "dataset_build" / "library_notes_catalog.json"

CLUSTERED_CHAPTER_DATASET_DIRS = (
    ROOT / "state" / "eval_local_datasets" / "chapter_corpora" / "attentional_v2_clustered_benchmark_v1_chapters_en",
    ROOT / "state" / "eval_local_datasets" / "chapter_corpora" / "attentional_v2_clustered_benchmark_v1_chapters_zh",
)

WINDOW_SPECS: tuple[dict[str, Any], ...] = (
    {
        "window_case_id": "supremacy_private_en__13",
        "source_id": "supremacy_private_en",
        "language_track": "en",
        "chapter_ids": ["13"],
        "chapter_case_ids": ["supremacy_private_en__13"],
        "origin_line": "clustered_benchmark_v1",
    },
    {
        "window_case_id": "steve_jobs_private_en__17",
        "source_id": "steve_jobs_private_en",
        "language_track": "en",
        "chapter_ids": ["17"],
        "chapter_case_ids": ["steve_jobs_private_en__17"],
        "origin_line": "clustered_benchmark_v1",
    },
    {
        "window_case_id": "zouchu_weiyi_zhenliguan_private_zh__14",
        "source_id": "zouchu_weiyi_zhenliguan_private_zh",
        "language_track": "zh",
        "chapter_ids": ["14"],
        "chapter_case_ids": ["zouchu_weiyi_zhenliguan_private_zh__14"],
        "origin_line": "clustered_benchmark_v1",
    },
    {
        "window_case_id": "xidaduo_private_zh__15",
        "source_id": "xidaduo_private_zh",
        "language_track": "zh",
        "chapter_ids": ["15"],
        "chapter_case_ids": ["xidaduo_private_zh__15"],
        "origin_line": "human_notes_guided_dataset_v1",
    },
    {
        "window_case_id": "nawaer_baodian_private_zh__wealth",
        "source_id": "nawaer_baodian_private_zh",
        "language_track": "zh",
        "chapter_ids": ["12", "13"],
        "chapter_case_ids": ["nawaer_baodian_private_zh__12", "nawaer_baodian_private_zh__13"],
        "origin_line": "human_notes_guided_dataset_v1",
        "window_label": "Wealth cluster",
    },
    {
        "window_case_id": "nawaer_baodian_private_zh__judgment",
        "source_id": "nawaer_baodian_private_zh",
        "language_track": "zh",
        "chapter_ids": ["22", "23", "24"],
        "chapter_case_ids": [
            "nawaer_baodian_private_zh__22",
            "nawaer_baodian_private_zh__23",
            "nawaer_baodian_private_zh__24",
        ],
        "origin_line": "human_notes_guided_dataset_v1",
        "window_label": "Judgment cluster",
    },
)

VALUE_TARGET_PROFILE_IDS = {"distinction_definition", "tension_reversal", "callback_bridge"}

BUILDER_LIMITATIONS = (
    "Probe review automation is intentionally deferred in this minimal implementation.",
    "Draft probes are deterministic and traceable, but they are not yet passed through a dedicated long-span review packet lane.",
    "The tracked draft manifest is immediately runnable for harness work; later freeze promotion should prefer reviewed probes when they exist.",
)


@dataclass(frozen=True)
class ExcerptSupport:
    case_id: str
    source_id: str
    chapter_id: str
    anchor_sentence_index: int
    start_sentence_id: str
    end_sentence_id: str
    excerpt_text: str
    target_profile_id: str
    selection_reason: str
    judge_focus: str
    benchmark_status: str
    book_title: str
    author: str
    output_language: str


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _clean_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _sentence_index(sentence_id: object) -> int:
    match = re.search(r"-s(\d+)$", str(sentence_id or ""))
    return int(match.group(1)) if match else 0


def _chapter_ids_are_contiguous(chapter_ids: list[str]) -> bool:
    values = [int(item) for item in chapter_ids if str(item).isdigit()]
    if len(values) <= 1:
        return True
    return all(current == previous + 1 for previous, current in zip(values, values[1:]))


def _source_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for manifest_path in SOURCE_MANIFEST_PATHS:
        payload = _load_json(manifest_path)
        if isinstance(payload.get("books"), list):
            entries = payload["books"]
        elif isinstance(payload.get("source_refs"), list):
            entries = payload["source_refs"]
        else:
            entries = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            source_id = _clean_text(item.get("source_id"))
            if not source_id:
                continue
            existing = index.get(source_id, {})
            merged = {**existing, **item}
            index[source_id] = merged
    return index


def _clustered_chapter_rows() -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for dataset_dir in CLUSTERED_CHAPTER_DATASET_DIRS:
        manifest = _load_json(dataset_dir / "manifest.json")
        for row in _load_jsonl(dataset_dir / str(manifest["primary_file"])):
            chapter_case_id = _clean_text(row.get("chapter_case_id"))
            if chapter_case_id:
                rows[chapter_case_id] = dict(row)
    return rows


def _notes_catalog() -> dict[str, Any]:
    return _load_json(NOTES_CATALOG_PATH)


def _notes_entries_for(source_id: str, *, chapter_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in _notes_catalog().get("entries", []):
        if not isinstance(entry, dict):
            continue
        if _clean_text(entry.get("linked_source_id")) != source_id:
            continue
        if _clean_text(entry.get("matched_chapter_id")) != chapter_id:
            continue
        span = dict(entry.get("matched_sentence_span") or {})
        if not _clean_text(span.get("start_sentence_id")) or not _clean_text(span.get("end_sentence_id")):
            continue
        rows.append(dict(entry))
    rows.sort(
        key=lambda item: (
            -float(item.get("alignment_confidence", 0.0) or 0.0),
            _clean_text(item.get("entry_id")),
        )
    )
    return rows


def _reviewed_excerpt_supports() -> dict[tuple[str, str], list[ExcerptSupport]]:
    grouped: dict[tuple[str, str], list[ExcerptSupport]] = defaultdict(list)
    for dataset_dir in REVIEWED_EXCERPT_DATASET_DIRS:
        manifest = _load_json(dataset_dir / "manifest.json")
        for raw in _load_jsonl(dataset_dir / str(manifest["primary_file"])):
            if _clean_text(raw.get("benchmark_status")) != "reviewed_active":
                continue
            support = ExcerptSupport(
                case_id=_clean_text(raw.get("case_id")),
                source_id=_clean_text(raw.get("source_id")),
                chapter_id=_clean_text(raw.get("chapter_id")),
                anchor_sentence_index=int(raw.get("anchor_sentence_index", 0) or 0),
                start_sentence_id=_clean_text(raw.get("start_sentence_id")),
                end_sentence_id=_clean_text(raw.get("end_sentence_id")),
                excerpt_text=_clean_text(raw.get("excerpt_text")),
                target_profile_id=_clean_text(raw.get("target_profile_id")),
                selection_reason=_clean_text(raw.get("selection_reason")),
                judge_focus=_clean_text(raw.get("judge_focus")),
                benchmark_status=_clean_text(raw.get("benchmark_status")),
                book_title=_clean_text(raw.get("book_title")),
                author=_clean_text(raw.get("author")),
                output_language=_clean_text(raw.get("output_language")),
            )
            grouped[(support.source_id, support.chapter_id)].append(support)
    for rows in grouped.values():
        rows.sort(key=lambda item: (item.anchor_sentence_index, item.case_id))
    return grouped


def _window_spec(window_case_id: str) -> dict[str, Any]:
    for spec in WINDOW_SPECS:
        if spec["window_case_id"] == window_case_id:
            return dict(spec)
    raise KeyError(window_case_id)


def _book_document_for(source_id: str, *, language_track: str, source_index: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], Any]:
    source = dict(source_index[source_id])
    book_path = ROOT / str(source["relative_local_path"])
    provisioned = ensure_canonical_parse(book_path, language_mode=language_track)
    if provisioned.book_document is None:
        raise RuntimeError(f"Missing canonical parse for {source_id}")
    return source, provisioned


def build_window_rows(root: Path | None = None) -> list[dict[str, Any]]:
    _ = root  # Reserved for future non-default roots.
    source_index = _source_index()
    clustered_rows = _clustered_chapter_rows()
    window_rows: list[dict[str, Any]] = []
    for spec in WINDOW_SPECS:
        source, provisioned = _book_document_for(
            spec["source_id"],
            language_track=str(spec["language_track"]),
            source_index=source_index,
        )
        chapter_map = {
            _clean_text(chapter.get("id")): dict(chapter)
            for chapter in provisioned.book_document.get("chapters", [])
            if isinstance(chapter, dict)
        }
        chapter_titles: list[str] = []
        sentence_count_total = 0
        for chapter_id in spec["chapter_ids"]:
            chapter = chapter_map.get(chapter_id)
            if chapter is None:
                raise ValueError(f"Missing chapter {chapter_id} for {spec['window_case_id']}")
            chapter_titles.append(_clean_text(chapter.get("title")))
            sentence_count_total += len([item for item in chapter.get("sentences", []) if isinstance(item, dict)])
        clustered_row = clustered_rows.get(spec["chapter_case_ids"][0], {})
        row = {
            "window_case_id": spec["window_case_id"],
            "source_id": spec["source_id"],
            "book_title": provisioned.title,
            "author": provisioned.author,
            "language_track": spec["language_track"],
            "output_language": spec["language_track"],
            "window_kind": "cross_chapter" if len(spec["chapter_ids"]) > 1 else "single_chapter",
            "chapter_ids": list(spec["chapter_ids"]),
            "chapter_case_ids": list(spec["chapter_case_ids"]),
            "chapter_titles": chapter_titles,
            "window_title": _clean_text(spec.get("window_label")) or " / ".join(chapter_titles),
            "selection_group_id": spec["window_case_id"],
            "selection_group_label": _clean_text(spec.get("window_label")) or " / ".join(chapter_titles),
            "sentence_count_total": sentence_count_total,
            "sentence_count": sentence_count_total,
            "origin_line": spec["origin_line"],
            "benchmark_line": spec["origin_line"],
            "selection_role": _clean_text(clustered_row.get("selection_role")) or "long_span_window",
            "selection_status": _clean_text(clustered_row.get("selection_status")) or "bounded_long_span_window_v1",
            "contiguous_chapters": _chapter_ids_are_contiguous(list(spec["chapter_ids"])),
            "cross_chapter_window": (
                {
                    "start_chapter_id": spec["chapter_ids"][0],
                    "end_chapter_id": spec["chapter_ids"][-1],
                    "start_chapter_case_id": spec["chapter_case_ids"][0],
                    "end_chapter_case_id": spec["chapter_case_ids"][-1],
                    "summary": _clean_text(spec.get("window_label")),
                }
                if len(spec["chapter_ids"]) > 1
                else None
            ),
            "relative_local_path": _clean_text(source.get("relative_local_path")),
        }
        window_rows.append(row)
    return window_rows


def _excerpt_anchor(case: ExcerptSupport, *, stage: str, chapter_order: int) -> dict[str, Any]:
    return {
        "anchor_id": f"excerpt::{case.case_id}",
        "stage": stage,
        "anchor_kind": "excerpt_case",
        "source_ref_id": case.case_id,
        "source_case_id": case.case_id,
        "chapter_id": case.chapter_id,
        "chapter_order": chapter_order,
        "start_sentence_id": case.start_sentence_id,
        "end_sentence_id": case.end_sentence_id,
        "anchor_sentence_index": case.anchor_sentence_index,
        "excerpt_text": case.excerpt_text,
        "target_profile_id": case.target_profile_id,
        "selection_reason": case.selection_reason,
        "judge_focus": case.judge_focus,
    }


def _note_anchor(entry: dict[str, Any], *, stage: str, chapter_order: int) -> dict[str, Any]:
    span = dict(entry.get("matched_sentence_span") or {})
    entry_id = _clean_text(entry.get("entry_id"))
    return {
        "anchor_id": f"note::{entry_id}",
        "stage": stage,
        "anchor_kind": "note_entry",
        "source_ref_id": entry_id,
        "source_case_id": "",
        "chapter_id": _clean_text(entry.get("matched_chapter_id")),
        "chapter_order": chapter_order,
        "start_sentence_id": _clean_text(span.get("start_sentence_id")),
        "end_sentence_id": _clean_text(span.get("end_sentence_id")),
        "anchor_sentence_index": _sentence_index(span.get("start_sentence_id")),
        "excerpt_text": _clean_text(entry.get("quote")),
        "target_profile_id": "",
        "selection_reason": _clean_text(entry.get("note")),
        "judge_focus": "",
        "alignment_confidence": float(entry.get("alignment_confidence", 0.0) or 0.0),
    }


def _dedupe_probe_anchor_sets(candidates: list[list[dict[str, Any]]]) -> list[list[dict[str, Any]]]:
    unique: list[list[dict[str, Any]]] = []
    seen: set[tuple[str, ...]] = set()
    for anchors in candidates:
        key = tuple(_clean_text(anchor.get("source_ref_id")) for anchor in anchors if _clean_text(anchor.get("source_ref_id")))
        if len(key) < 2 or key in seen:
            continue
        seen.add(key)
        unique.append(anchors)
    return unique


def _single_window_probe_anchors(window_row: dict[str, Any], rows: list[ExcerptSupport]) -> list[list[dict[str, Any]]]:
    chapter_id = _clean_text(window_row["chapter_ids"][0])
    chapter_order = 0
    ordered = sorted(rows, key=lambda item: (item.anchor_sentence_index, item.case_id))
    if len(ordered) < 2:
        raise ValueError(f"Need at least two reviewed excerpt supports for {window_row['window_case_id']}")
    positions = [
        [0, len(ordered) // 2, len(ordered) - 1],
        [0, len(ordered) - 1],
        [max(0, len(ordered) // 3), len(ordered) - 1],
        [0, max(1, len(ordered) // 2)],
        [1 if len(ordered) > 2 else 0, len(ordered) - 1],
    ]
    candidates: list[list[dict[str, Any]]] = []
    for position_list in positions:
        anchors: list[dict[str, Any]] = []
        stage_labels = ("early", "mid", "late")
        for offset, raw_index in enumerate(position_list):
            case = ordered[min(raw_index, len(ordered) - 1)]
            stage = stage_labels[min(offset, len(stage_labels) - 1)]
            anchors.append(_excerpt_anchor(case, stage=stage, chapter_order=chapter_order))
        candidates.append(anchors)
    unique = _dedupe_probe_anchor_sets(candidates)
    return unique[:3]


def _cross_window_probe_anchors(
    window_row: dict[str, Any],
    support_index: dict[tuple[str, str], list[ExcerptSupport]],
) -> list[list[dict[str, Any]]]:
    source_id = _clean_text(window_row["source_id"])
    chapter_ids = [str(item) for item in window_row["chapter_ids"]]
    opening_excerpt = list(support_index.get((source_id, chapter_ids[0]), []))
    final_excerpt = list(support_index.get((source_id, chapter_ids[-1]), []))
    opening_notes = _notes_entries_for(source_id, chapter_id=chapter_ids[0])
    final_notes = _notes_entries_for(source_id, chapter_id=chapter_ids[-1])
    middle_anchor_candidates: list[dict[str, Any]] = []
    for chapter_order, chapter_id in enumerate(chapter_ids[1:-1], start=1):
        for case in support_index.get((source_id, chapter_id), [])[:2]:
            middle_anchor_candidates.append(_excerpt_anchor(case, stage="mid", chapter_order=chapter_order))
        if not middle_anchor_candidates:
            for entry in _notes_entries_for(source_id, chapter_id=chapter_id)[:2]:
                middle_anchor_candidates.append(_note_anchor(entry, stage="mid", chapter_order=chapter_order))

    early_pool = [
        *[_excerpt_anchor(case, stage="early", chapter_order=0) for case in opening_excerpt[:3]],
        *[_note_anchor(entry, stage="early", chapter_order=0) for entry in opening_notes[:3]],
    ]
    late_pool = [
        *[
            _excerpt_anchor(case, stage="late", chapter_order=len(chapter_ids) - 1)
            for case in final_excerpt[:3]
        ],
        *[
            _note_anchor(entry, stage="late", chapter_order=len(chapter_ids) - 1)
            for entry in final_notes[:3]
        ],
    ]
    if not early_pool or not late_pool:
        raise ValueError(f"Need opening and final anchors for {window_row['window_case_id']}")

    candidates: list[list[dict[str, Any]]] = []
    for index in range(3):
        anchors = [early_pool[min(index, len(early_pool) - 1)]]
        if middle_anchor_candidates:
            anchors.append(middle_anchor_candidates[min(index, len(middle_anchor_candidates) - 1)])
        anchors.append(late_pool[min(index, len(late_pool) - 1)])
        candidates.append(anchors)
    candidates.append([early_pool[0], late_pool[0]])
    unique = _dedupe_probe_anchor_sets(candidates)
    return unique[:3]


def _probe_type(anchors: list[dict[str, Any]]) -> str:
    chapter_ids = {_clean_text(anchor.get("chapter_id")) for anchor in anchors}
    if len(chapter_ids) > 1:
        return "cross_chapter_carryover"
    if len(anchors) >= 3:
        return "single_chapter_full_span"
    return "single_chapter_carryover"


def _probe_selection_reason(window_row: dict[str, Any], anchors: list[dict[str, Any]]) -> str:
    anchor_labels = [f"{anchor['stage']}@chapter{anchor['chapter_id']}" for anchor in anchors]
    return (
        f"Bounded long-span probe selected from {window_row['window_case_id']} using "
        f"{', '.join(anchor_labels)}. It is intended to test whether earlier material is "
        f"carried forward coherently rather than being re-reacted to in isolation."
    )


def _probe_judge_focus(window_row: dict[str, Any], anchors: list[dict[str, Any]]) -> str:
    chapter_span = f"chapters {'-'.join(window_row['chapter_ids'])}"
    return (
        f"Does the reader show coherent accumulation across {chapter_span}, especially at the later "
        f"anchor(s), by carrying forward earlier material in a text-grounded way? When the window "
        f"invites clarification, does the later output sharpen the earlier idea rather than merely paraphrase it?"
    )


def _probe_excerpt_text(anchors: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"{str(anchor['stage']).upper()} ({anchor['chapter_id']}): {_clean_text(anchor['excerpt_text'])}"
        for anchor in anchors
    )


def _support_case_ids(anchors: list[dict[str, Any]]) -> list[str]:
    return [_clean_text(anchor.get("source_case_id")) for anchor in anchors if _clean_text(anchor.get("source_case_id"))]


def _note_entry_ids(anchors: list[dict[str, Any]]) -> list[str]:
    return [_clean_text(anchor.get("source_ref_id")) for anchor in anchors if _clean_text(anchor.get("anchor_kind")) == "note_entry"]


def build_probe_rows(root: Path | None = None) -> list[dict[str, Any]]:
    _ = root
    window_rows = build_window_rows()
    support_index = _reviewed_excerpt_supports()
    probe_rows: list[dict[str, Any]] = []
    for window_row in window_rows:
        source_id = _clean_text(window_row["source_id"])
        chapter_ids = [str(item) for item in window_row["chapter_ids"]]
        if len(chapter_ids) == 1:
            support_rows = list(support_index.get((source_id, chapter_ids[0]), []))
            anchor_sets = _single_window_probe_anchors(window_row, support_rows)
        else:
            anchor_sets = _cross_window_probe_anchors(window_row, support_index)
        for index, anchors in enumerate(anchor_sets, start=1):
            probe_type = _probe_type(anchors)
            probe_id = f"{window_row['window_case_id']}__probe_{index}"
            serves_reader_value = any(
                _clean_text(anchor.get("target_profile_id")) in VALUE_TARGET_PROFILE_IDS
                or _clean_text(anchor.get("anchor_kind")) == "note_entry"
                for anchor in anchors
            )
            probe_rows.append(
                {
                    "probe_id": probe_id,
                    "case_id": probe_id,
                    "window_case_id": window_row["window_case_id"],
                    "source_id": source_id,
                    "book_title": window_row["book_title"],
                    "author": window_row["author"],
                    "language_track": window_row["language_track"],
                    "output_language": window_row["output_language"],
                    "window_kind": window_row["window_kind"],
                    "chapter_ids": chapter_ids,
                    "chapter_case_ids": list(window_row["chapter_case_ids"]),
                    "probe_type": probe_type,
                    "question_ids": ["EQ-CM-003", "EQ-CM-004", "EQ-AV2-004"],
                    "phenomena": [
                        "coherent_accumulation",
                        "memory_carryover",
                        "bounded_long_span",
                        "insight_and_clarification" if serves_reader_value else "local_only",
                    ],
                    "selection_reason": _probe_selection_reason(window_row, anchors),
                    "judge_focus": _probe_judge_focus(window_row, anchors),
                    "excerpt_text": _probe_excerpt_text(anchors),
                    "prior_context_text": _clean_text(anchors[0]["excerpt_text"]),
                    "anchor_refs": anchors,
                    "support_excerpt_case_ids": _support_case_ids(anchors),
                    "note_provenance": _note_entry_ids(anchors),
                    "target_axes": [
                        "reader_character.coherent_accumulation",
                        "reader_value.insight_and_clarification",
                    ]
                    if serves_reader_value
                    else ["reader_character.coherent_accumulation"],
                    "serves_reader_value": serves_reader_value,
                    "construction_priority": float(len(_support_case_ids(anchors)) + (0.5 if serves_reader_value else 0.0)),
                    "judgeability_score": float(2 + len(anchors)),
                    "benchmark_status": "builder_curated",
                    "review_status": "builder_curated",
                    "curation_status": "builder_curated_v1",
                    "window_probe_rank": index,
                    "notes": "Deterministic v1 long-span draft probe built from reviewed excerpt supports and/or notes anchors.",
                }
            )
    probe_rows.sort(key=lambda row: (_clean_text(row.get("window_case_id")), int(row.get("window_probe_rank", 0) or 0), _clean_text(row.get("probe_id"))))
    return probe_rows


def _window_manifest() -> dict[str, Any]:
    return {
        "dataset_id": WINDOW_DATASET_ID,
        "family": WINDOW_CASES_FAMILY,
        "language_track": "bilingual",
        "version": "1",
        "description": "Bounded long-span window cases for attentional_v2 accumulation benchmark v1.",
        "primary_file": "windows.jsonl",
        "question_ids": ["EQ-CM-003", "EQ-CM-004", "EQ-AV2-004"],
        "source_manifest_refs": [str(path.relative_to(ROOT)) for path in SOURCE_MANIFEST_PATHS],
        "storage_mode": "local-only",
        "window_count": 6,
    }


def _probe_manifest(dataset_id: str, *, row_count: int, description: str) -> dict[str, Any]:
    return {
        "dataset_id": dataset_id,
        "family": ACCUMULATION_PROBES_FAMILY,
        "language_track": "bilingual",
        "version": "1",
        "description": description,
        "primary_file": "probes.jsonl",
        "question_ids": ["EQ-CM-003", "EQ-CM-004", "EQ-AV2-004"],
        "source_manifest_refs": [str(path.relative_to(ROOT)) for path in SOURCE_MANIFEST_PATHS],
        "storage_mode": "local-only",
        "row_count": row_count,
    }


def build_draft_manifest_payload() -> dict[str, Any]:
    window_rows = build_window_rows()
    probe_rows = build_probe_rows()
    insight_ids = [row["probe_id"] for row in probe_rows if bool(row.get("serves_reader_value"))]
    return {
        "manifest_id": "attentional_v2_accumulation_benchmark_v1_draft",
        "description": "Bounded long-span/window draft manifest for split-surface coherent accumulation evaluation.",
        "targets": [
            "reader_character.coherent_accumulation",
            "reader_value.insight_and_clarification",
        ],
        "benchmark_shape": {
            "kind": "long_span_window",
            "window_case_target_total": 6,
            "accumulation_probe_target_total": len(probe_rows),
        },
        "builder_limitations": list(BUILDER_LIMITATIONS),
        "source_refs": {
            "source_manifests": [str(path.relative_to(ROOT)) for path in SOURCE_MANIFEST_PATHS],
            "window_case_datasets": [str(WINDOW_DATASET_DIR.relative_to(ROOT))],
            "accumulation_probe_datasets": [str(PROBE_DRAFT_DATASET_DIR.relative_to(ROOT))],
        },
        "quota_status": {
            "window_cases": {"target_total": 6, "ready_now": len(window_rows), "gap": max(0, 6 - len(window_rows))},
            "accumulation_probes": {
                "target_total": 18,
                "ready_now": len(probe_rows),
                "gap": max(0, 18 - len(probe_rows)),
            },
            "insight_and_clarification_subset": {
                "target_total": len(insight_ids),
                "ready_now": len(insight_ids),
                "gap": 0,
            },
        },
        "splits": {
            "accumulation_window_core_draft": {
                "all": [row["window_case_id"] for row in window_rows],
            },
            "accumulation_probes_frozen_draft": {
                "all": [row["probe_id"] for row in probe_rows],
            },
            "accumulation_probe_core_draft": {
                "by_window": {
                    row["window_case_id"]: [probe["probe_id"] for probe in probe_rows if probe["window_case_id"] == row["window_case_id"]]
                    for row in window_rows
                },
                "all": [row["probe_id"] for row in probe_rows],
            },
            "insight_and_clarification_subset_frozen_draft": {
                "all": insight_ids,
            },
            "insight_and_clarification_subset_draft": {
                "all": insight_ids,
            },
        },
    }


def write_draft_artifacts(root: Path | None = None) -> dict[str, Any]:
    _ = root
    window_rows = build_window_rows()
    probe_rows = build_probe_rows()
    WINDOW_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    PROBE_DRAFT_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    _json_dump(WINDOW_DATASET_DIR / "manifest.json", _window_manifest())
    _jsonl_dump(WINDOW_DATASET_DIR / "windows.jsonl", window_rows)
    _json_dump(
        PROBE_DRAFT_DATASET_DIR / "manifest.json",
        _probe_manifest(
            PROBE_DRAFT_DATASET_ID,
            row_count=len(probe_rows),
            description="Deterministic draft probes for attentional_v2 accumulation benchmark v1.",
        ),
    )
    _jsonl_dump(PROBE_DRAFT_DATASET_DIR / "probes.jsonl", probe_rows)
    draft_manifest = build_draft_manifest_payload()
    _json_dump(DRAFT_MANIFEST_PATH, draft_manifest)
    return {
        "window_dataset_dir": str(WINDOW_DATASET_DIR),
        "probe_dataset_dir": str(PROBE_DRAFT_DATASET_DIR),
        "draft_manifest_path": str(DRAFT_MANIFEST_PATH),
        "window_count": len(window_rows),
        "probe_count": len(probe_rows),
    }


def freeze_probe_rows(probe_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in probe_rows:
        grouped[_clean_text(row.get("window_case_id"))].append(dict(row))

    frozen_rows: list[dict[str, Any]] = []
    saturation: dict[str, Any] = {}
    for window_case_id, rows in grouped.items():
        reviewed = [row for row in rows if _clean_text(row.get("benchmark_status")) == "reviewed_active"]
        eligible = reviewed or rows
        eligible.sort(key=lambda row: (int(row.get("window_probe_rank", 999) or 999), _clean_text(row.get("probe_id"))))
        selected = eligible[:3]
        for row in selected:
            row["freeze_metadata"] = {
                "frozen_from_dataset_id": PROBE_DRAFT_DATASET_ID,
                "freeze_role": "primary",
                "freeze_reason": "reviewed_active" if reviewed else "builder_curated_fallback",
            }
            frozen_rows.append(row)
        saturation[window_case_id] = {
            "eligible_count": len(eligible),
            "selected_count": len(selected),
            "used_reviewed_rows": bool(reviewed),
            "saturation_reason": "" if len(selected) >= 2 else "insufficient_probe_rows",
        }
    frozen_rows.sort(key=lambda row: (_clean_text(row.get("window_case_id")), int(row.get("window_probe_rank", 0) or 0)))
    return frozen_rows, saturation


def write_frozen_probe_dataset(root: Path | None = None) -> dict[str, Any]:
    _ = root
    draft_manifest = _load_json(PROBE_DRAFT_DATASET_DIR / "manifest.json")
    probe_rows = _load_jsonl(PROBE_DRAFT_DATASET_DIR / str(draft_manifest["primary_file"]))
    frozen_rows, saturation = freeze_probe_rows(probe_rows)
    PROBE_FROZEN_DATASET_DIR.mkdir(parents=True, exist_ok=True)
    _json_dump(
        PROBE_FROZEN_DATASET_DIR / "manifest.json",
        _probe_manifest(
            PROBE_FROZEN_DATASET_ID,
            row_count=len(frozen_rows),
            description="Frozen-draft long-span probes for attentional_v2 accumulation benchmark v1.",
        ),
    )
    _jsonl_dump(PROBE_FROZEN_DATASET_DIR / "probes.jsonl", frozen_rows)
    draft_manifest = build_draft_manifest_payload()
    draft_manifest["source_refs"]["accumulation_probe_datasets"] = [str(PROBE_FROZEN_DATASET_DIR.relative_to(ROOT))]
    draft_manifest["quota_status"]["accumulation_probes"]["ready_now"] = len(frozen_rows)
    draft_manifest["quota_status"]["accumulation_probes"]["gap"] = max(0, 18 - len(frozen_rows))
    frozen_probe_ids = [row["probe_id"] for row in frozen_rows]
    frozen_insight_ids = [row["probe_id"] for row in frozen_rows if bool(row.get("serves_reader_value"))]
    draft_manifest["splits"]["accumulation_probes_frozen_draft"] = {"all": frozen_probe_ids}
    draft_manifest["splits"]["insight_and_clarification_subset_frozen_draft"] = {"all": frozen_insight_ids}
    _json_dump(DRAFT_MANIFEST_PATH, draft_manifest)
    return {
        "probe_dataset_dir": str(PROBE_FROZEN_DATASET_DIR),
        "probe_count": len(frozen_rows),
        "saturation": saturation,
        "draft_manifest_path": str(DRAFT_MANIFEST_PATH),
    }
