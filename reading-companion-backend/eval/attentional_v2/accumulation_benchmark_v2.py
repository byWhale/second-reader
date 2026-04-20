"""Target-centered long-span accumulation benchmark v2 artifacts.

This module defines the v2 target-case schema and the draft/freeze dataset
artifacts that sit on top of the active user-level reading windows.

Unlike v1, v2 does not use bounded `EARLY / MID / LATE` probes as the active
case primitive. The case primitive is a target-centered long-range thread:
- one target span / target zone
- a variable number of upstream nodes
- expected integration at the target point
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from eval.attentional_v2.user_level_selective_v1 import DATASET_DIR as WINDOW_DATASET_DIR
from eval.attentional_v2.user_level_selective_v1 import DATASET_ID as WINDOW_DATASET_ID


ROOT = Path(__file__).resolve().parents[2]
TARGET_CASES_FAMILY = "accumulation_target_cases"
TARGET_CASE_DRAFT_DATASET_ID = "attentional_v2_accumulation_benchmark_v2_cases_draft"
TARGET_CASE_FROZEN_DATASET_ID = "attentional_v2_accumulation_benchmark_v2_cases_frozen"

TARGET_CASE_DRAFT_DATASET_DIR = (
    ROOT / "state" / "eval_local_datasets" / TARGET_CASES_FAMILY / TARGET_CASE_DRAFT_DATASET_ID
)
TARGET_CASE_FROZEN_DATASET_DIR = (
    ROOT / "state" / "eval_local_datasets" / TARGET_CASES_FAMILY / TARGET_CASE_FROZEN_DATASET_ID
)
DRAFT_MANIFEST_PATH = ROOT / "eval" / "manifests" / "splits" / "attentional_v2_accumulation_benchmark_v2_draft.json"

ACTIVE_QUESTION_FAMILY = "reader_character.coherent_accumulation"
THREAD_TYPES = {"叙事型故事脉络", "论证型论证线", "概念/区分澄清线"}
READY_FOR_FREEZE_STATUSES = {"approved_draft", "approved_for_freeze", "frozen"}


@dataclass(frozen=True)
class SpanSlice:
    coordinate_system: str
    segment_id: str
    paragraph_index: int
    char_start: int
    char_end: int
    text: str
    source_id: str = ""


@dataclass(frozen=True)
class SpanPoint:
    point_id: str
    label: str
    span_text: str
    span_slices: list[SpanSlice]


@dataclass(frozen=True)
class UpstreamNode:
    node_id: str
    label: str
    span_text: str
    span_slices: list[SpanSlice]
    summary: str = ""


@dataclass(frozen=True)
class TargetCase:
    case_id: str
    source_id: str
    book: str
    author: str
    output_language: str
    window_id: str
    thread_type: str
    target_span: SpanPoint
    upstream_nodes: list[UpstreamNode]
    expected_integration: str
    callback_eligible_spans: list[SpanPoint]
    non_goal_but_tempting_points: list[SpanPoint]
    long_range_rationale: str
    curation_status: str
    provenance: dict[str, Any]


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def _jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        if not rows:
            handle.write("\n")
            return
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _span_slice_from_raw(raw: dict[str, Any], *, owner: str) -> SpanSlice:
    coordinate_system = _clean_text(raw.get("coordinate_system")) or "segment_source_v1"
    if coordinate_system != "segment_source_v1":
        raise ValueError(f"{owner} slice must use segment_source_v1")
    segment_id = _clean_text(raw.get("segment_id"))
    if not segment_id:
        raise ValueError(f"{owner} slice missing segment_id")
    try:
        paragraph_index = int(raw.get("paragraph_index"))
        char_start = int(raw.get("char_start"))
        char_end = int(raw.get("char_end"))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{owner} slice has invalid numeric bounds") from exc
    if paragraph_index <= 0:
        raise ValueError(f"{owner} slice paragraph_index must be positive")
    if char_start < 0 or char_end <= char_start:
        raise ValueError(f"{owner} slice char bounds are invalid")
    return SpanSlice(
        coordinate_system=coordinate_system,
        segment_id=segment_id,
        paragraph_index=paragraph_index,
        char_start=char_start,
        char_end=char_end,
        text=_clean_text(raw.get("text")),
        source_id=_clean_text(raw.get("source_id")),
    )


def _span_point_from_raw(raw: dict[str, Any], *, owner: str) -> SpanPoint:
    point_id = _clean_text(raw.get("point_id")) or _clean_text(raw.get("span_id"))
    if not point_id:
        raise ValueError(f"{owner} missing point_id")
    label = _clean_text(raw.get("label")) or point_id
    span_text = _clean_text(raw.get("span_text"))
    span_slices_raw = raw.get("span_slices")
    if not isinstance(span_slices_raw, list) or not span_slices_raw:
        raise ValueError(f"{owner} must include non-empty span_slices")
    span_slices = [
        _span_slice_from_raw(dict(item), owner=f"{owner}:{point_id}")
        for item in span_slices_raw
        if isinstance(item, dict)
    ]
    if not span_slices:
        raise ValueError(f"{owner} must include at least one valid span slice")
    return SpanPoint(
        point_id=point_id,
        label=label,
        span_text=span_text,
        span_slices=span_slices,
    )


def _upstream_node_from_raw(raw: dict[str, Any], *, owner: str) -> UpstreamNode:
    node_id = _clean_text(raw.get("node_id"))
    if not node_id:
        raise ValueError(f"{owner} missing node_id")
    label = _clean_text(raw.get("label")) or node_id
    span_text = _clean_text(raw.get("span_text"))
    span_slices_raw = raw.get("span_slices")
    if not isinstance(span_slices_raw, list) or not span_slices_raw:
        raise ValueError(f"{owner}:{node_id} must include non-empty span_slices")
    span_slices = [
        _span_slice_from_raw(dict(item), owner=f"{owner}:{node_id}")
        for item in span_slices_raw
        if isinstance(item, dict)
    ]
    if not span_slices:
        raise ValueError(f"{owner}:{node_id} must include at least one valid span slice")
    return UpstreamNode(
        node_id=node_id,
        label=label,
        span_text=span_text,
        span_slices=span_slices,
        summary=_clean_text(raw.get("summary")),
    )


def target_case_from_row(raw: dict[str, Any]) -> TargetCase:
    case_id = _clean_text(raw.get("case_id"))
    if not case_id:
        raise ValueError("target case missing case_id")
    source_id = _clean_text(raw.get("source_id"))
    window_id = _clean_text(raw.get("window_id"))
    thread_type = _clean_text(raw.get("thread_type"))
    if not source_id or not window_id:
        raise ValueError(f"{case_id} missing source_id or window_id")
    if thread_type not in THREAD_TYPES:
        raise ValueError(f"{case_id} has unsupported thread_type: {thread_type or 'missing'}")

    target_span_raw = raw.get("target_span")
    if not isinstance(target_span_raw, dict):
        raise ValueError(f"{case_id} missing target_span")
    target_span = _span_point_from_raw(target_span_raw, owner=f"{case_id}:target_span")

    upstream_nodes_raw = raw.get("upstream_nodes")
    if not isinstance(upstream_nodes_raw, list) or len(upstream_nodes_raw) < 2:
        raise ValueError(f"{case_id} must include at least two upstream_nodes")
    upstream_nodes = [
        _upstream_node_from_raw(dict(item), owner=f"{case_id}:upstream_node")
        for item in upstream_nodes_raw
        if isinstance(item, dict)
    ]
    if len(upstream_nodes) < 2:
        raise ValueError(f"{case_id} must include at least two valid upstream_nodes")
    upstream_node_ids = {node.node_id for node in upstream_nodes}
    if len(upstream_node_ids) != len(upstream_nodes):
        raise ValueError(f"{case_id} has duplicate upstream node ids")

    callback_points = [
        _span_point_from_raw(dict(item), owner=f"{case_id}:callback_eligible_span")
        for item in raw.get("callback_eligible_spans", [])
        if isinstance(item, dict)
    ]
    tempting_points = [
        _span_point_from_raw(dict(item), owner=f"{case_id}:non_goal_but_tempting_point")
        for item in raw.get("non_goal_but_tempting_points", [])
        if isinstance(item, dict)
    ]

    expected_integration = _clean_text(raw.get("expected_integration"))
    long_range_rationale = _clean_text(raw.get("long_range_rationale"))
    curation_status = _clean_text(raw.get("curation_status"))
    if not expected_integration:
        raise ValueError(f"{case_id} missing expected_integration")
    if not long_range_rationale:
        raise ValueError(f"{case_id} missing long_range_rationale")
    if not curation_status:
        raise ValueError(f"{case_id} missing curation_status")

    return TargetCase(
        case_id=case_id,
        source_id=source_id,
        book=_clean_text(raw.get("book")),
        author=_clean_text(raw.get("author")),
        output_language=_clean_text(raw.get("output_language") or raw.get("language_track")),
        window_id=window_id,
        thread_type=thread_type,
        target_span=target_span,
        upstream_nodes=upstream_nodes,
        expected_integration=expected_integration,
        callback_eligible_spans=callback_points,
        non_goal_but_tempting_points=tempting_points,
        long_range_rationale=long_range_rationale,
        curation_status=curation_status,
        provenance=dict(raw.get("provenance") or {}),
    )


def target_case_to_row(case: TargetCase) -> dict[str, Any]:
    return asdict(case)


def _relative_to_root(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _active_window_manifest_payload() -> dict[str, Any]:
    return json.loads((WINDOW_DATASET_DIR / "manifest.json").read_text(encoding="utf-8"))


def build_draft_manifest_payload(case_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    normalized_rows = [target_case_to_row(target_case_from_row(dict(row))) for row in (case_rows or [])]
    window_manifest = _active_window_manifest_payload()
    case_ids = [str(row["case_id"]) for row in normalized_rows]
    frozen_ids = [
        str(row["case_id"])
        for row in normalized_rows
        if _clean_text(row.get("curation_status")) in READY_FOR_FREEZE_STATUSES
    ]
    by_thread_type: dict[str, list[str]] = {}
    for row in normalized_rows:
        by_thread_type.setdefault(str(row["thread_type"]), []).append(str(row["case_id"]))
    return {
        "manifest_id": "attentional_v2_accumulation_benchmark_v2_draft",
        "benchmark_family": "target_centered_long_span_accumulation_v2",
        "status": "draft",
        "version": "2026-04-18",
        "question_families": [ACTIVE_QUESTION_FAMILY],
        "active_design": "target_centered_long_span_accumulation_v2",
        "source_refs": {
            "user_level_dataset_roots": [_relative_to_root(WINDOW_DATASET_DIR)],
            "accumulation_target_case_datasets": [_relative_to_root(TARGET_CASE_DRAFT_DATASET_DIR)],
            "source_manifests": list(window_manifest.get("source_manifest_refs") or []),
        },
        "quota_status": {
            "window_substrate": {
                "dataset_id": WINDOW_DATASET_ID,
                "ready_now": int(window_manifest.get("segment_count") or 0),
            },
            "accumulation_target_cases": {
                "target_total": len(case_ids),
                "ready_now": len(case_ids),
                "freeze_ready": len(frozen_ids),
                "review_pending": max(0, len(case_ids) - len(frozen_ids)),
            },
        },
        "splits": {
            "accumulation_target_cases_draft": {
                "all": case_ids,
                "by_thread_type": by_thread_type,
            },
            "accumulation_target_cases_frozen": {
                "all": frozen_ids,
                "by_thread_type": {
                    thread_type: [case_id for case_id in case_ids_for_type if case_id in set(frozen_ids)]
                    for thread_type, case_ids_for_type in by_thread_type.items()
                },
            },
        },
        "notes": [
            "V2 reuses the active user-level reading windows as its substrate.",
            "Draft target cases remain review-gated and must be approved before freeze promotion.",
            "The historical bounded EARLY/MID/LATE accumulation benchmark v1 remains preserved as historical evidence only.",
        ],
    }


def freeze_target_case_rows(case_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows = [target_case_to_row(target_case_from_row(dict(row))) for row in case_rows]
    return [
        row
        for row in normalized_rows
        if _clean_text(row.get("curation_status")) in READY_FOR_FREEZE_STATUSES
    ]


def write_draft_target_case_dataset(
    case_rows: list[dict[str, Any]],
    *,
    dataset_dir: Path | None = None,
) -> dict[str, Any]:
    dataset_dir = dataset_dir or TARGET_CASE_DRAFT_DATASET_DIR
    normalized_rows = [target_case_to_row(target_case_from_row(dict(row))) for row in case_rows]
    _json_dump(
        dataset_dir / "manifest.json",
        {
            "dataset_id": TARGET_CASE_DRAFT_DATASET_ID,
            "family": TARGET_CASES_FAMILY,
            "status": "draft",
            "version": "2026-04-18",
            "primary_file": "cases.jsonl",
            "case_count": len(normalized_rows),
            "question_families": [ACTIVE_QUESTION_FAMILY],
            "window_substrate_dataset_id": WINDOW_DATASET_ID,
            "description": "Draft target-centered long-span accumulation v2 cases pending candidate review.",
        },
    )
    _jsonl_dump(dataset_dir / "cases.jsonl", normalized_rows)
    return {"dataset_dir": str(dataset_dir), "case_count": len(normalized_rows)}


def write_frozen_target_case_dataset(
    case_rows: list[dict[str, Any]],
    *,
    dataset_dir: Path | None = None,
) -> dict[str, Any]:
    dataset_dir = dataset_dir or TARGET_CASE_FROZEN_DATASET_DIR
    frozen_rows = freeze_target_case_rows(case_rows)
    _json_dump(
        dataset_dir / "manifest.json",
        {
            "dataset_id": TARGET_CASE_FROZEN_DATASET_ID,
            "family": TARGET_CASES_FAMILY,
            "status": "frozen",
            "version": "2026-04-18",
            "primary_file": "cases.jsonl",
            "case_count": len(frozen_rows),
            "question_families": [ACTIVE_QUESTION_FAMILY],
            "window_substrate_dataset_id": WINDOW_DATASET_ID,
            "description": "Frozen target-centered long-span accumulation v2 cases approved after candidate review.",
        },
    )
    _jsonl_dump(dataset_dir / "cases.jsonl", frozen_rows)
    return {"dataset_dir": str(dataset_dir), "case_count": len(frozen_rows)}


def write_draft_artifacts(case_rows: list[dict[str, Any]]) -> dict[str, Any]:
    dataset_summary = write_draft_target_case_dataset(case_rows)
    manifest_payload = build_draft_manifest_payload(case_rows)
    _json_dump(DRAFT_MANIFEST_PATH, manifest_payload)
    return {
        "case_count": dataset_summary["case_count"],
        "dataset_dir": dataset_summary["dataset_dir"],
        "draft_manifest_path": str(DRAFT_MANIFEST_PATH),
    }
