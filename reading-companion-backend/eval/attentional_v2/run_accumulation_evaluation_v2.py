"""Run target-centered long-span accumulation evaluation v2."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
from statistics import mean
from typing import Any

from eval.attentional_v2.accumulation_benchmark_v2 import (
    ACTIVE_QUESTION_FAMILY,
    DRAFT_MANIFEST_PATH,
    ROOT,
    TARGET_CASE_DRAFT_DATASET_DIR,
    SpanPoint,
    SpanSlice,
    TargetCase,
    UpstreamNode,
    WINDOW_DATASET_DIR,
    target_case_from_row,
)
from eval.attentional_v2.completed_output_reuse import rebuild_normalized_bundle_from_completed_output
from eval.attentional_v2.llm_usage_summary import write_llm_usage_summary
from src.iterator_reader.llm_utils import ReaderLLMError, invoke_json, llm_invocation_scope
from src.reading_core.runtime_contracts import ReadRequest
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_mechanisms.iterator_v1 import IteratorV1Mechanism
from src.reading_runtime.llm_gateway import eval_trace_context
from src.reading_runtime.llm_registry import DEFAULT_EVAL_JUDGE_PROFILE_ID
from src.reading_runtime.output_dir_overrides import override_output_dir


DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_TARGET = "accumulation_evaluation_v2"
DEFAULT_USER_INTENT = (
    "Read as a thoughtful co-reader and keep long-range narrative or argumentative threads alive until they matter again."
)
MECHANISM_KEYS = ("attentional_v2", "iterator_v1")
MECHANISM_FILTER_VALUES = ("attentional_v2", "iterator_v1", "both")
JUDGE_MODE_VALUES = ("llm", "none")
CALLBACK_MOVE_TYPES = {"bridge", "callback", "return", "look_back", "revisit", "compare"}
JUDGE_SCHEMA_RETRY_INSTRUCTION = (
    "\n\nReminder: return exactly one JSON object matching the requested schema. "
    "Do not wrap it in markdown fences or nest it under another key."
)


@dataclass(frozen=True)
class ReadingSegment:
    segment_id: str
    source_id: str
    book_title: str
    author: str
    language_track: str
    start_sentence_id: str
    end_sentence_id: str
    chapter_ids: list[int]
    chapter_titles: list[str]
    target_note_count: int
    covered_note_count: int
    termination_reason: str
    segment_source_path: str


@dataclass(frozen=True)
class AccumulationV2Selection:
    dataset_dir: Path
    dataset_manifest: dict[str, Any]
    case_dataset_manifests: list[dict[str, Any]]
    segments: list[ReadingSegment]
    cases: list[TargetCase]
    selected_case_ids: list[str]
    cases_by_window: dict[str, list[TargetCase]]
    formal_manifest_path: Path


@dataclass(frozen=True)
class TargetEvidenceBundle:
    case_id: str
    segment_id: str
    target_ref: dict[str, Any]
    upstream_refs: list[dict[str, Any]]
    expected_integration: str
    target_local_reactions: list[dict[str, Any]]
    explicit_callback_actions: list[dict[str, Any]]
    short_horizon_followups: list[dict[str, Any]]
    non_goal_but_tempting_points: list[dict[str, Any]]


@dataclass(frozen=True)
class AbsoluteAccumulationJudgeResult:
    quality_score: int
    callback_score: int
    thread_built: str
    reason: str


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _normalize_compare_text(value: object) -> str:
    return re.sub(r"\s+", " ", _clean_text(value)).strip().lower()


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _jsonl_load(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _resolve_path(path_text: str) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate.resolve()
    return (ROOT / candidate).resolve()


def _load_formal_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _resolve_dataset_dir(formal_manifest: dict[str, Any]) -> Path:
    refs = dict(formal_manifest.get("source_refs") or {})
    roots = [_resolve_path(str(item)) for item in refs.get("user_level_dataset_roots") or []]
    if roots:
        return roots[0]
    return WINDOW_DATASET_DIR.resolve()


def _target_case_dataset_dirs_from_manifest(formal_manifest: dict[str, Any]) -> list[Path]:
    refs = dict(formal_manifest.get("source_refs") or {})
    resolved = [_resolve_path(str(item)) for item in refs.get("accumulation_target_case_datasets") or []]
    return resolved or [TARGET_CASE_DRAFT_DATASET_DIR.resolve()]


def _selected_case_ids_from_manifest(formal_manifest: dict[str, Any]) -> list[str]:
    splits = dict(formal_manifest.get("splits") or {})
    for split_name in ("accumulation_target_cases_draft", "accumulation_target_cases_frozen"):
        payload = dict(splits.get(split_name) or {})
        all_ids = [str(item) for item in payload.get("all", []) if _clean_text(item)]
        if all_ids:
            return all_ids
    return []


def _load_segments(dataset_dir: Path) -> tuple[dict[str, Any], list[ReadingSegment]]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = _jsonl_load(dataset_dir / str(manifest["segments_file"]))
    segments = [
        ReadingSegment(
            segment_id=str(row["segment_id"]),
            source_id=str(row["source_id"]),
            book_title=str(row["book_title"]),
            author=str(row.get("author", "")),
            language_track=str(row.get("language_track") or row.get("output_language") or ""),
            start_sentence_id=str(row["start_sentence_id"]),
            end_sentence_id=str(row["end_sentence_id"]),
            chapter_ids=[int(item) for item in row.get("source_chapter_ids", row.get("chapter_ids", []))],
            chapter_titles=[str(item) for item in row.get("chapter_titles", [])],
            target_note_count=int(row.get("target_note_count") or 0),
            covered_note_count=int(row.get("covered_note_count") or 0),
            termination_reason=str(row.get("termination_reason") or ""),
            segment_source_path=str(row["segment_source_path"]),
        )
        for row in rows
    ]
    return manifest, segments


def _load_cases(dataset_dir: Path) -> tuple[dict[str, Any], list[TargetCase]]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = _jsonl_load(dataset_dir / str(manifest["primary_file"]))
    return manifest, [target_case_from_row(dict(row)) for row in rows]


def _prepare_selection(
    *,
    formal_manifest_path: Path,
    case_ids: list[str] | None = None,
) -> AccumulationV2Selection:
    formal_manifest = _load_formal_manifest(formal_manifest_path)
    dataset_dir = _resolve_dataset_dir(formal_manifest)
    dataset_manifest, segments = _load_segments(dataset_dir)
    segment_index = {segment.segment_id: segment for segment in segments}

    selected_case_ids = case_ids or _selected_case_ids_from_manifest(formal_manifest)
    case_dataset_manifests: list[dict[str, Any]] = []
    case_index: dict[str, TargetCase] = {}
    for case_dataset_dir in _target_case_dataset_dirs_from_manifest(formal_manifest):
        manifest, cases = _load_cases(case_dataset_dir)
        case_dataset_manifests.append(manifest)
        for case in cases:
            case_index.setdefault(case.case_id, case)

    selected_cases: list[TargetCase] = []
    if selected_case_ids:
        missing = [case_id for case_id in selected_case_ids if case_id not in case_index]
        if missing:
            raise ValueError(f"missing target cases: {', '.join(sorted(missing))}")
        selected_cases = [case_index[case_id] for case_id in selected_case_ids]
    else:
        selected_cases = list(case_index.values())
        selected_case_ids = [case.case_id for case in selected_cases]

    if not selected_cases:
        raise ValueError("no target cases selected")

    missing_windows = sorted({case.window_id for case in selected_cases if case.window_id not in segment_index})
    if missing_windows:
        raise ValueError(f"missing reading segments for target cases: {', '.join(missing_windows)}")

    cases_by_window: dict[str, list[TargetCase]] = defaultdict(list)
    for case in selected_cases:
        cases_by_window[case.window_id].append(case)
    selected_segments = [segment_index[window_id] for window_id in cases_by_window]
    return AccumulationV2Selection(
        dataset_dir=dataset_dir,
        dataset_manifest=dataset_manifest,
        case_dataset_manifests=case_dataset_manifests,
        segments=selected_segments,
        cases=selected_cases,
        selected_case_ids=selected_case_ids,
        cases_by_window=dict(cases_by_window),
        formal_manifest_path=formal_manifest_path,
    )


def _mechanism_keys_for_filter(mechanism_filter: str) -> tuple[str, ...]:
    if mechanism_filter not in MECHANISM_FILTER_VALUES:
        raise ValueError(f"unsupported mechanism filter: {mechanism_filter}")
    return MECHANISM_KEYS if mechanism_filter == "both" else (mechanism_filter,)


@contextmanager
def _isolated_output_dir(output_dir: Path):
    with override_output_dir(output_dir):
        yield


def _mechanism_for_key(mechanism_key: str):
    if mechanism_key == "attentional_v2":
        return AttentionalV2Mechanism()
    if mechanism_key == "iterator_v1":
        return IteratorV1Mechanism()
    raise ValueError(f"unsupported mechanism: {mechanism_key}")


def _bundle_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    reactions = [dict(item) for item in bundle.get("reactions") or [] if isinstance(item, dict)]
    attention_events = [
        dict(item)
        for item in bundle.get("attention_events") or []
        if isinstance(item, dict) and _clean_text(item.get("kind")) not in {"position", "checkpoint"}
    ]
    return {
        "reaction_count": len(reactions),
        "attention_event_count": len(attention_events),
        "reactions": [
            {
                "reaction_id": _clean_text(item.get("reaction_id")),
                "type": _clean_text(item.get("type")),
                "section_ref": _clean_text(item.get("section_ref")),
                "anchor_quote": _clean_text(item.get("anchor_quote"))[:180],
                "content": _clean_text(item.get("content"))[:240],
            }
            for item in reactions[:5]
        ],
        "attention_events": [
            {
                "kind": _clean_text(item.get("kind")),
                "phase": _clean_text(item.get("phase")),
                "section_ref": _clean_text(item.get("section_ref")),
                "move_type": _clean_text(item.get("move_type")),
                "message": _clean_text(item.get("message"))[:180],
                "current_excerpt": _clean_text(item.get("current_excerpt"))[:180],
            }
            for item in attention_events[:5]
        ],
        "memory_summaries": [str(item)[:200] for item in (bundle.get("memory_summaries") or [])[:3]],
    }


def _run_mechanism_for_segment(
    *,
    segment: ReadingSegment,
    dataset_dir: Path,
    mechanism_key: str,
    run_root: Path,
) -> dict[str, Any]:
    mechanism = _mechanism_for_key(mechanism_key)
    segment_path = dataset_dir / segment.segment_source_path
    output_dir = run_root / "outputs" / segment.segment_id / mechanism_key
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with _isolated_output_dir(output_dir):
        result = mechanism.read_book(
            ReadRequest(
                book_path=segment_path,
                chapter_number=1,
                continue_mode=False,
                user_intent=DEFAULT_USER_INTENT,
                language_mode=segment.language_track,
                task_mode="sequential",
                mechanism_key=mechanism_key,
                mechanism_config={"persist_normalized_eval_bundle": True},
            )
        )
    bundle = dict(result.normalized_eval_bundle or {})
    return {
        "status": "completed",
        "mechanism_key": mechanism_key,
        "mechanism_label": result.mechanism.label,
        "output_dir": str(result.output_dir),
        "normalized_eval_bundle": bundle,
        "bundle_summary": _bundle_summary(bundle),
        "error": "",
    }


def _rebuild_mechanism_payload_from_output(
    *,
    segment: ReadingSegment,
    mechanism_key: str,
    source_output_dir: Path,
    run_root: Path,
) -> dict[str, Any]:
    rebuilt = rebuild_normalized_bundle_from_completed_output(
        mechanism_key=mechanism_key,
        source_output_dir=source_output_dir,
        segment_id=segment.segment_id,
    )
    bundle = dict(rebuilt["normalized_eval_bundle"])
    mechanism_label = str(rebuilt["mechanism_label"])
    rebuilt_path = run_root / "rebuilt_bundles" / segment.segment_id / mechanism_key / "normalized_eval_bundle.json"
    _json_dump(rebuilt_path, bundle)
    return {
        "status": "completed",
        "mechanism_key": mechanism_key,
        "mechanism_label": mechanism_label,
        "output_dir": str(source_output_dir),
        "source_output_dir": str(source_output_dir),
        "rebuilt_bundle_path": str(rebuilt_path),
        "normalized_eval_bundle": bundle,
        "bundle_summary": _bundle_summary(bundle),
        "error": "",
    }


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _visible_reaction_text(reaction: dict[str, Any]) -> str:
    return _clean_text(reaction.get("anchor_quote")) or _clean_text(reaction.get("content"))


def _locator_to_slice(
    locator: dict[str, Any],
    *,
    segment_id: str,
    source_id: str,
    text: str = "",
) -> dict[str, Any] | None:
    paragraph_index = _int_or_none(locator.get("paragraph_index") or locator.get("paragraph_start"))
    char_start = _int_or_none(locator.get("char_start"))
    char_end = _int_or_none(locator.get("char_end"))
    if paragraph_index is None or char_start is None or char_end is None:
        return None
    if paragraph_index <= 0 or char_start < 0 or char_end <= char_start:
        return None
    return {
        "coordinate_system": "segment_source_v1",
        "segment_id": segment_id,
        "source_id": source_id,
        "paragraph_index": paragraph_index,
        "char_start": char_start,
        "char_end": char_end,
        "text": text,
    }


def _locator_source_span_slices(
    locator: dict[str, Any],
    *,
    segment_id: str,
    source_id: str,
) -> list[dict[str, Any]]:
    raw_slices = locator.get("source_span_slices")
    if not isinstance(raw_slices, list):
        return []
    slices: list[dict[str, Any]] = []
    for item in raw_slices:
        if not isinstance(item, dict):
            continue
        paragraph_index = _int_or_none(item.get("paragraph_index"))
        char_start = _int_or_none(item.get("char_start"))
        char_end = _int_or_none(item.get("char_end"))
        if paragraph_index is None or char_start is None or char_end is None:
            continue
        if paragraph_index <= 0 or char_start < 0 or char_end <= char_start:
            continue
        slices.append(
            {
                "coordinate_system": "segment_source_v1",
                "segment_id": _clean_text(item.get("segment_id")) or segment_id,
                "source_id": _clean_text(item.get("source_id")) or source_id,
                "paragraph_index": paragraph_index,
                "char_start": char_start,
                "char_end": char_end,
                "text": _clean_text(item.get("text")),
            }
        )
    return slices


def _reaction_source_span(
    reaction: dict[str, Any],
    *,
    segment_id: str,
    source_id: str,
) -> tuple[list[dict[str, Any]], str]:
    visible_text = _visible_reaction_text(reaction)
    direct_locator = reaction.get("target_locator")
    if isinstance(direct_locator, dict):
        direct_source_slices = _locator_source_span_slices(
            direct_locator,
            segment_id=segment_id,
            source_id=source_id,
        )
        if direct_source_slices:
            return direct_source_slices, _clean_text(direct_locator.get("source_span_resolution")) or _clean_text(
                direct_locator.get("match_mode")
            ) or "source_span_slices"
        direct_slice = _locator_to_slice(
            direct_locator,
            segment_id=segment_id,
            source_id=source_id,
            text=visible_text,
        )
        if direct_slice is not None:
            return [direct_slice], _clean_text(direct_locator.get("match_mode")) or "char_locator"
    primary_anchor = reaction.get("primary_anchor")
    if isinstance(primary_anchor, dict):
        anchor_locator = primary_anchor.get("locator")
        if isinstance(anchor_locator, dict):
            anchor_slice = _locator_to_slice(
                anchor_locator,
                segment_id=segment_id,
                source_id=source_id,
                text=_clean_text(primary_anchor.get("quote")) or visible_text,
            )
            if anchor_slice is not None:
                return [anchor_slice], "primary_anchor"
    return [], ""


def _slice_key(slice_payload: dict[str, Any]) -> tuple[str, int, int, int]:
    return (
        _clean_text(slice_payload.get("segment_id")),
        int(slice_payload.get("paragraph_index", 0) or 0),
        int(slice_payload.get("char_start", 0) or 0),
        int(slice_payload.get("char_end", 0) or 0),
    )


def _slice_overlap_chars(left: dict[str, Any], right: dict[str, Any]) -> int:
    if _clean_text(left.get("segment_id")) != _clean_text(right.get("segment_id")):
        return 0
    if int(left.get("paragraph_index", 0) or 0) != int(right.get("paragraph_index", 0) or 0):
        return 0
    start = max(int(left.get("char_start", 0) or 0), int(right.get("char_start", 0) or 0))
    end = min(int(left.get("char_end", 0) or 0), int(right.get("char_end", 0) or 0))
    return max(0, end - start)


def _source_span_relation(
    *,
    target_slices: list[dict[str, Any]],
    candidate_slices: list[dict[str, Any]],
) -> tuple[str, int, float]:
    overlap_chars = sum(
        _slice_overlap_chars(target_slice, candidate_slice)
        for target_slice in target_slices
        for candidate_slice in candidate_slices
    )
    if overlap_chars <= 0:
        return "no_overlap", 0, 0.0
    target_chars = sum(
        max(0, int(item.get("char_end", 0) or 0) - int(item.get("char_start", 0) or 0))
        for item in target_slices
    )
    coverage = overlap_chars / float(target_chars or 1)
    return "overlap", overlap_chars, coverage


def _point_to_payload(point: SpanPoint | UpstreamNode) -> dict[str, Any]:
    return asdict(point)


def _callback_points_for_case(case: TargetCase) -> list[SpanPoint]:
    if case.callback_eligible_spans:
        return list(case.callback_eligible_spans)
    return [
        SpanPoint(
            point_id=node.node_id,
            label=node.label,
            span_text=node.span_text,
            span_slices=list(node.span_slices),
        )
        for node in case.upstream_nodes
    ]


def _reaction_payloads(bundle: dict[str, Any], *, segment: ReadingSegment) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for index, item in enumerate(bundle.get("reactions") or []):
        if not isinstance(item, dict):
            continue
        visible_text = _visible_reaction_text(item)
        if not visible_text:
            continue
        source_slices, source_span_resolution = _reaction_source_span(
            item,
            segment_id=segment.segment_id,
            source_id=segment.source_id,
        )
        payloads.append(
            {
                "order_index": index,
                "reaction_id": _clean_text(item.get("reaction_id")) or f"reaction_{index + 1}",
                "type": _clean_text(item.get("type")),
                "section_ref": _clean_text(item.get("section_ref")),
                "anchor_quote": _clean_text(item.get("anchor_quote")),
                "content": _clean_text(item.get("content")),
                "visible_text": visible_text,
                "source_span_slices": source_slices,
                "source_span_resolution": source_span_resolution,
            }
        )
    return payloads


def _attention_event_payloads(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for index, item in enumerate(bundle.get("attention_events") or []):
        if not isinstance(item, dict):
            continue
        if _clean_text(item.get("kind")) in {"position", "checkpoint"}:
            continue
        payloads.append(
            {
                "order_index": index,
                "kind": _clean_text(item.get("kind")),
                "phase": _clean_text(item.get("phase")),
                "section_ref": _clean_text(item.get("section_ref")),
                "move_type": _clean_text(item.get("move_type")).lower(),
                "message": _clean_text(item.get("message")),
                "current_excerpt": _clean_text(item.get("current_excerpt")),
            }
        )
    return payloads


def _text_mentions_point(text: str, point: SpanPoint | UpstreamNode) -> bool:
    candidate = _normalize_compare_text(text)
    point_text = _normalize_compare_text(point.span_text)
    if not candidate or not point_text:
        return False
    return point_text in candidate or candidate in point_text


def _build_target_evidence_bundle(
    *,
    case: TargetCase,
    segment: ReadingSegment,
    bundle: dict[str, Any],
) -> TargetEvidenceBundle:
    reaction_payloads = _reaction_payloads(bundle, segment=segment)
    attention_payloads = _attention_event_payloads(bundle)
    target_slices = [asdict(item) for item in case.target_span.span_slices]

    target_local_reactions: list[dict[str, Any]] = []
    for reaction in reaction_payloads:
        if not reaction["source_span_slices"]:
            continue
        relation, overlap_chars, overlap_coverage = _source_span_relation(
            target_slices=target_slices,
            candidate_slices=reaction["source_span_slices"],
        )
        if relation == "no_overlap":
            continue
        payload = dict(reaction)
        payload["overlap_relation"] = relation
        payload["overlap_chars"] = overlap_chars
        payload["overlap_coverage"] = round(overlap_coverage, 4)
        target_local_reactions.append(payload)
    target_local_reactions.sort(key=lambda item: (-float(item["overlap_coverage"]), int(item["order_index"])))
    target_local_reactions = target_local_reactions[:6]

    callback_points = _callback_points_for_case(case)
    latest_target_index = max((int(item["order_index"]) for item in target_local_reactions), default=-1)
    explicit_callback_actions: list[dict[str, Any]] = []
    seen_callback_ids: set[tuple[str, str]] = set()

    for reaction in reaction_payloads:
        if latest_target_index >= 0 and int(reaction["order_index"]) < latest_target_index:
            continue
        if not reaction["source_span_slices"]:
            continue
        matched_point: SpanPoint | None = None
        for point in callback_points:
            relation, overlap_chars, overlap_coverage = _source_span_relation(
                target_slices=[asdict(item) for item in point.span_slices],
                candidate_slices=reaction["source_span_slices"],
            )
            if relation != "no_overlap":
                payload = dict(reaction)
                payload["matched_callback_point_id"] = point.point_id
                payload["matched_callback_label"] = point.label
                payload["overlap_chars"] = overlap_chars
                payload["overlap_coverage"] = round(overlap_coverage, 4)
                key = ("reaction", payload["reaction_id"])
                if key not in seen_callback_ids:
                    explicit_callback_actions.append(payload)
                    seen_callback_ids.add(key)
                matched_point = point
                break
        if matched_point is not None and len(explicit_callback_actions) >= 6:
            break

    for event in attention_payloads:
        if event["move_type"] not in CALLBACK_MOVE_TYPES and not any(
            _text_mentions_point(event["message"], point) or _text_mentions_point(event["current_excerpt"], point)
            for point in callback_points
        ):
            continue
        matched_point = next(
            (
                point
                for point in callback_points
                if _text_mentions_point(event["message"], point) or _text_mentions_point(event["current_excerpt"], point)
            ),
            None,
        )
        payload = dict(event)
        payload["matched_callback_point_id"] = matched_point.point_id if matched_point else ""
        payload["matched_callback_label"] = matched_point.label if matched_point else ""
        key = ("event", f"{event['order_index']}:{event['move_type']}:{event['section_ref']}")
        if key in seen_callback_ids:
            continue
        explicit_callback_actions.append(payload)
        seen_callback_ids.add(key)
        if len(explicit_callback_actions) >= 6:
            break

    short_horizon_followups: list[dict[str, Any]] = []
    if latest_target_index >= 0:
        for reaction in reaction_payloads:
            if int(reaction["order_index"]) <= latest_target_index:
                continue
            short_horizon_followups.append(
                {
                    "reaction_id": reaction["reaction_id"],
                    "type": reaction["type"],
                    "section_ref": reaction["section_ref"],
                    "anchor_quote": reaction["anchor_quote"],
                    "content": reaction["content"],
                }
            )
            if len(short_horizon_followups) >= 3:
                break

    return TargetEvidenceBundle(
        case_id=case.case_id,
        segment_id=segment.segment_id,
        target_ref=_point_to_payload(case.target_span),
        upstream_refs=[_point_to_payload(node) for node in case.upstream_nodes],
        expected_integration=case.expected_integration,
        target_local_reactions=target_local_reactions,
        explicit_callback_actions=explicit_callback_actions,
        short_horizon_followups=short_horizon_followups,
        non_goal_but_tempting_points=[_point_to_payload(point) for point in case.non_goal_but_tempting_points],
    )


def _default_judgment(*, reason: str) -> dict[str, Any]:
    return {
        "quality_score": 1,
        "callback_score": 0,
        "thread_built": "not_built",
        "reason": reason,
    }


def _normalize_judgment(payload: object, *, default_reason: str) -> dict[str, Any]:
    default = _default_judgment(reason=default_reason)
    if not isinstance(payload, dict):
        return default
    try:
        quality_score = int(payload.get("quality_score"))
    except (TypeError, ValueError):
        quality_score = default["quality_score"]
    try:
        callback_score = int(payload.get("callback_score"))
    except (TypeError, ValueError):
        callback_score = default["callback_score"]
    thread_built = _clean_text(payload.get("thread_built")).lower()
    if thread_built not in {"built", "partial", "not_built"}:
        thread_built = default["thread_built"]

    return {
        "quality_score": min(5, max(1, quality_score)),
        "callback_score": min(2, max(0, callback_score)),
        "thread_built": thread_built,
        "reason": _clean_text(payload.get("reason")) or default["reason"],
    }


def _judgment_needs_retry(payload: object, *, normalized: dict[str, Any], default_reason: str) -> bool:
    if not isinstance(payload, dict):
        return True
    if normalized["reason"] == default_reason:
        return True
    if not _clean_text(payload.get("reason")):
        return True
    return False


def _judge_target_case(
    *,
    case: TargetCase,
    evidence_bundle: TargetEvidenceBundle,
    run_root: Path,
    mechanism_key: str,
    judge_mode: str,
) -> dict[str, Any]:
    if judge_mode == "none":
        return _default_judgment(reason="judge_disabled")
    if judge_mode not in JUDGE_MODE_VALUES:
        raise ValueError(f"unsupported judge mode: {judge_mode}")

    system_prompt = """You are doing offline single-mechanism reader evaluation.

Question family: `reader_character.coherent_accumulation`

Judge one mechanism on one target-centered long-span case.

The core question is:
- At the target point, did the reader successfully build the prepared long-range thread?

Main scoring:
- `quality_score` (1-5) is the primary score
- `callback_score` (0-2) is a secondary bonus score for relevant explicit callback behavior

Use:
- `thread_built = built` when the target-point reaction clearly reconstructs the prepared thread
- `thread_built = partial` when it captures only part of the thread
- `thread_built = not_built` when it misses or distorts the prepared thread

Return JSON only.""";
    case_payload = {
        "case_id": case.case_id,
        "thread_type": case.thread_type,
        "target_span": asdict(case.target_span),
        "upstream_nodes": [asdict(node) for node in case.upstream_nodes],
        "expected_integration": case.expected_integration,
        "long_range_rationale": case.long_range_rationale,
    }
    evidence_payload = asdict(evidence_bundle)
    base_user_prompt = (
        f"Target-centered case:\n{json.dumps(case_payload, ensure_ascii=False, indent=2)}\n\n"
        f"Mechanism evidence bundle:\n{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}\n\n"
        'Return JSON: {"quality_score":1,"callback_score":0,"thread_built":"built|partial|not_built","reason":"3-6 sentences."}'
    )
    payload: object = {}
    normalized = _default_judgment(reason="judge_unavailable")
    for user_prompt in (base_user_prompt, base_user_prompt + JUDGE_SCHEMA_RETRY_INSTRUCTION):
        try:
            with llm_invocation_scope(
                profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
                trace_context=eval_trace_context(
                    run_root,
                    eval_target=DEFAULT_TARGET,
                    stage="accumulation_v2_absolute_judge",
                    node="coherent_accumulation",
                    extra={"case_id": case.case_id, "mechanism_key": mechanism_key},
                ),
            ):
                payload = invoke_json(system_prompt, user_prompt, _default_judgment(reason="judge_unavailable"))
        except ReaderLLMError:
            payload = {}
        except Exception:
            payload = {}
        normalized = _normalize_judgment(payload, default_reason="judge_unavailable")
        if _judgment_needs_retry(payload, normalized=normalized, default_reason="judge_unavailable"):
            continue
        break
    return normalized


def _segment_result_path(run_root: Path, segment_id: str) -> Path:
    return run_root / "segments" / f"{segment_id}.json"


def _case_result_path(run_root: Path, case_id: str) -> Path:
    return run_root / "cases" / f"{case_id}.json"


def _case_error_result(case: TargetCase, *, mechanism_keys: tuple[str, ...], error: str) -> dict[str, Any]:
    mechanism_results: dict[str, Any] = {}
    for mechanism_key in mechanism_keys:
        mechanism_results[mechanism_key] = {
            "status": "case_error",
            "mechanism_label": mechanism_key,
            "output_dir": "",
            "bundle_summary": {},
            "target_evidence_bundle": {},
            "judgment": _default_judgment(reason="case_error"),
            "error": error,
        }
    return {
        "case_id": case.case_id,
        "window_id": case.window_id,
        "source_id": case.source_id,
        "book": case.book,
        "author": case.author,
        "output_language": case.output_language,
        "thread_type": case.thread_type,
        "mechanism_results": mechanism_results,
        "case_error": error,
    }


def _evaluate_case(
    *,
    case: TargetCase,
    segment: ReadingSegment,
    segment_payload: dict[str, Any],
    mechanism_keys: tuple[str, ...],
    run_root: Path,
    judge_mode: str,
) -> dict[str, Any]:
    mechanism_results: dict[str, Any] = {}
    for mechanism_key in mechanism_keys:
        mechanism_payload = dict((segment_payload.get("mechanisms") or {}).get(mechanism_key) or {})
        status = _clean_text(mechanism_payload.get("status")) or "failed"
        if status != "completed":
            mechanism_results[mechanism_key] = {
                "status": status,
                "mechanism_label": _clean_text(mechanism_payload.get("mechanism_label")) or mechanism_key,
                "output_dir": _clean_text(mechanism_payload.get("output_dir")),
                "bundle_summary": dict(mechanism_payload.get("bundle_summary") or {}),
                "target_evidence_bundle": {},
                "judgment": _default_judgment(reason="mechanism_unavailable"),
                "error": _clean_text(mechanism_payload.get("error")),
            }
            continue
        evidence_bundle = _build_target_evidence_bundle(
            case=case,
            segment=segment,
            bundle=dict(mechanism_payload.get("normalized_eval_bundle") or {}),
        )
        mechanism_results[mechanism_key] = {
            "status": status,
            "mechanism_label": _clean_text(mechanism_payload.get("mechanism_label")) or mechanism_key,
            "output_dir": _clean_text(mechanism_payload.get("output_dir")),
            "bundle_summary": dict(mechanism_payload.get("bundle_summary") or {}),
            "target_evidence_bundle": asdict(evidence_bundle),
            "judgment": _judge_target_case(
                case=case,
                evidence_bundle=evidence_bundle,
                run_root=run_root,
                mechanism_key=mechanism_key,
                judge_mode=judge_mode,
            ),
            "error": _clean_text(mechanism_payload.get("error")),
        }
    return {
        "case_id": case.case_id,
        "window_id": case.window_id,
        "source_id": case.source_id,
        "book": case.book,
        "author": case.author,
        "output_language": case.output_language,
        "thread_type": case.thread_type,
        "mechanism_results": mechanism_results,
    }


def _comparison_tuple(payload: dict[str, Any]) -> tuple[int, int]:
    judgment = dict(payload.get("judgment") or {})
    return int(judgment.get("quality_score", 1) or 1), int(judgment.get("callback_score", 0) or 0)


def _build_case_comparison(case_payload: dict[str, Any], *, mechanism_keys: tuple[str, ...]) -> dict[str, Any]:
    eligible: dict[str, tuple[int, int]] = {}
    for mechanism_key in mechanism_keys:
        payload = dict((case_payload.get("mechanism_results") or {}).get(mechanism_key) or {})
        reason = _clean_text(dict(payload.get("judgment") or {}).get("reason"))
        if payload.get("status") != "completed" or reason in {"judge_unavailable", "mechanism_unavailable", "case_error", "judge_disabled"}:
            continue
        eligible[mechanism_key] = _comparison_tuple(payload)
    if not eligible:
        return {"winner": "unavailable", "winners": [], "quality_score": 0, "callback_score": 0}
    best_tuple = max(eligible.values())
    winners = sorted([mechanism_key for mechanism_key, score_tuple in eligible.items() if score_tuple == best_tuple])
    if len(winners) == 1:
        return {
            "winner": winners[0],
            "winners": winners,
            "quality_score": best_tuple[0],
            "callback_score": best_tuple[1],
        }
    return {
        "winner": "tie",
        "winners": winners,
        "quality_score": best_tuple[0],
        "callback_score": best_tuple[1],
    }


def _aggregate_results(
    *,
    case_payloads: list[dict[str, Any]],
    mechanism_keys: tuple[str, ...],
) -> dict[str, Any]:
    aggregate: dict[str, Any] = {"mechanisms": {}, "derived_comparison": {}}
    for mechanism_key in mechanism_keys:
        scoped = [payload for payload in case_payloads if mechanism_key in payload["mechanism_results"]]
        if not scoped:
            aggregate["mechanisms"][mechanism_key] = {
                "case_count": 0,
                "average_quality_score": 0.0,
                "average_callback_score": 0.0,
                "thread_built_counts": {},
                "judge_unavailable_count": 0,
                "mechanism_unavailable_count": 0,
                "by_language": {},
            }
            continue
        judgments = [dict(payload["mechanism_results"][mechanism_key]["judgment"]) for payload in scoped]
        by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for payload in scoped:
            by_language[str(payload["output_language"])].append(payload)
        aggregate["mechanisms"][mechanism_key] = {
            "case_count": len(scoped),
            "average_quality_score": round(mean(int(item.get("quality_score", 1) or 1) for item in judgments), 3),
            "average_callback_score": round(mean(int(item.get("callback_score", 0) or 0) for item in judgments), 3),
            "thread_built_counts": dict(Counter(str(item.get("thread_built")) for item in judgments)),
            "judge_unavailable_count": sum(1 for item in judgments if _clean_text(item.get("reason")) == "judge_unavailable"),
            "mechanism_unavailable_count": sum(
                1 for payload in scoped if payload["mechanism_results"][mechanism_key]["status"] != "completed"
            ),
            "by_language": {
                language: {
                    "case_count": len(items),
                    "average_quality_score": round(
                        mean(
                            int(items_for_language["mechanism_results"][mechanism_key]["judgment"].get("quality_score", 1) or 1)
                            for items_for_language in items
                        ),
                        3,
                    ),
                    "average_callback_score": round(
                        mean(
                            int(items_for_language["mechanism_results"][mechanism_key]["judgment"].get("callback_score", 0) or 0)
                            for items_for_language in items
                        ),
                        3,
                    ),
                }
                for language, items in sorted(by_language.items())
            },
        }

    comparisons = [_build_case_comparison(payload, mechanism_keys=mechanism_keys) for payload in case_payloads]
    aggregate["derived_comparison"] = {
        "case_count": len(case_payloads),
        "winner_counts": dict(Counter(str(item.get("winner")) for item in comparisons)),
        "comparison_rule": "quality_score_then_callback_score_then_tie",
    }
    if len(mechanism_keys) == 2:
        left_key, right_key = mechanism_keys
        pairwise = Counter()
        for item in comparisons:
            winner = str(item.get("winner"))
            if winner == left_key:
                pairwise[left_key] += 1
            elif winner == right_key:
                pairwise[right_key] += 1
            elif winner == "tie":
                pairwise["tie"] += 1
            else:
                pairwise["unavailable"] += 1
        aggregate["derived_comparison"]["pairwise"] = {
            "left_key": left_key,
            "right_key": right_key,
            "winner_counts": dict(pairwise),
        }
    return aggregate


def _render_report(
    *,
    run_id: str,
    selection: AccumulationV2Selection,
    aggregate: dict[str, Any],
    mechanism_keys: tuple[str, ...],
) -> str:
    lines = [f"# Accumulation Evaluation V2: {run_id}", ""]
    lines.extend(
        [
            "## Method",
            f"- Active question family: `{ACTIVE_QUESTION_FAMILY}`",
            "- Method shape: `target-centered long-span accumulation v2`",
            "- Historical bounded `EARLY / MID / LATE` v1 remains preserved as historical evidence only.",
            "",
            "## Selection",
            f"- Reading segments: `{len(selection.segments)}`",
            f"- Target cases: `{len(selection.cases)}`",
            f"- Mechanisms: `{', '.join(mechanism_keys)}`",
            "",
        ]
    )
    for mechanism_key in mechanism_keys:
        payload = aggregate["mechanisms"][mechanism_key]
        lines.extend(
            [
                f"## {mechanism_key}",
                f"- case count: `{payload['case_count']}`",
                f"- average quality score: `{payload['average_quality_score']}`",
                f"- average callback score: `{payload['average_callback_score']}`",
                f"- thread built counts: `{json.dumps(payload['thread_built_counts'], ensure_ascii=False, sort_keys=True)}`",
                f"- judge unavailable count: `{payload['judge_unavailable_count']}`",
                f"- mechanism unavailable count: `{payload['mechanism_unavailable_count']}`",
                "",
            ]
        )
    lines.extend(
        [
            "## Derived Comparison",
            f"- winner counts: `{json.dumps(aggregate['derived_comparison']['winner_counts'], ensure_ascii=False, sort_keys=True)}`",
            f"- rule: `{aggregate['derived_comparison']['comparison_rule']}`",
            "",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def run_accumulation_evaluation_v2(
    *,
    run_id: str,
    formal_manifest_path: Path = DRAFT_MANIFEST_PATH,
    mechanism_filter: str = "both",
    judge_mode: str = "llm",
    segment_ids: list[str] | None = None,
    case_ids: list[str] | None = None,
    reuse_output_dir: Path | None = None,
) -> dict[str, Any]:
    selection = _prepare_selection(formal_manifest_path=formal_manifest_path, case_ids=case_ids)
    if segment_ids:
        wanted = set(segment_ids)
        selection_segments = [segment for segment in selection.segments if segment.segment_id in wanted]
        if not selection_segments:
            raise ValueError("no reading segments selected")
        selection_cases = [case for case in selection.cases if case.window_id in wanted]
        selection = AccumulationV2Selection(
            dataset_dir=selection.dataset_dir,
            dataset_manifest=selection.dataset_manifest,
            case_dataset_manifests=selection.case_dataset_manifests,
            segments=selection_segments,
            cases=selection_cases,
            selected_case_ids=[case.case_id for case in selection_cases],
            cases_by_window={window_id: cases for window_id, cases in selection.cases_by_window.items() if window_id in wanted},
            formal_manifest_path=selection.formal_manifest_path,
        )
    if not selection.cases:
        raise ValueError("no target cases selected after filtering")

    mechanism_keys = _mechanism_keys_for_filter(mechanism_filter)
    if reuse_output_dir is not None and (len(selection.segments) != 1 or len(mechanism_keys) != 1):
        raise ValueError("--reuse-output-dir requires exactly one selected segment and one mechanism")
    run_root = DEFAULT_RUNS_ROOT / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    _json_dump(
        run_root / "meta" / "selection.json",
        {
            "generated_at": _timestamp(),
            "formal_manifest_path": str(selection.formal_manifest_path),
            "dataset_dir": str(selection.dataset_dir),
            "segment_ids": [segment.segment_id for segment in selection.segments],
            "case_ids": [case.case_id for case in selection.cases],
            "mechanism_keys": list(mechanism_keys),
            "judge_mode": judge_mode,
            "reuse_output_dir": str(reuse_output_dir or ""),
        },
    )

    segment_results: dict[str, dict[str, Any]] = {}
    for segment in selection.segments:
        mechanisms: dict[str, Any] = {}
        for mechanism_key in mechanism_keys:
            try:
                if reuse_output_dir is not None:
                    payload = _rebuild_mechanism_payload_from_output(
                        segment=segment,
                        mechanism_key=mechanism_key,
                        source_output_dir=Path(reuse_output_dir).resolve(),
                        run_root=run_root,
                    )
                else:
                    payload = _run_mechanism_for_segment(
                        segment=segment,
                        dataset_dir=selection.dataset_dir,
                        mechanism_key=mechanism_key,
                        run_root=run_root,
                    )
            except Exception as exc:
                payload = {
                    "status": "failed",
                    "mechanism_key": mechanism_key,
                    "mechanism_label": mechanism_key,
                    "output_dir": "",
                    "normalized_eval_bundle": {},
                    "bundle_summary": {},
                    "error": f"{type(exc).__name__}: {exc}",
                }
            mechanisms[mechanism_key] = payload
        segment_payload = {
            "segment_id": segment.segment_id,
            "source_id": segment.source_id,
            "book_title": segment.book_title,
            "author": segment.author,
            "output_language": segment.language_track,
            "mechanisms": mechanisms,
        }
        segment_results[segment.segment_id] = segment_payload
        _json_dump(_segment_result_path(run_root, segment.segment_id), segment_payload)

    segment_index = {segment.segment_id: segment for segment in selection.segments}
    case_payloads: list[dict[str, Any]] = []
    for case in selection.cases:
        segment = segment_index.get(case.window_id)
        if segment is None:
            case_payload = _case_error_result(case, mechanism_keys=mechanism_keys, error="missing_segment")
        else:
            try:
                case_payload = _evaluate_case(
                    case=case,
                    segment=segment,
                    segment_payload=segment_results[segment.segment_id],
                    mechanism_keys=mechanism_keys,
                    run_root=run_root,
                    judge_mode=judge_mode,
                )
            except Exception as exc:
                case_payload = _case_error_result(
                    case,
                    mechanism_keys=mechanism_keys,
                    error=f"{type(exc).__name__}: {exc}",
                )
        _json_dump(_case_result_path(run_root, case.case_id), case_payload)
        case_payloads.append(case_payload)

    aggregate = _aggregate_results(case_payloads=case_payloads, mechanism_keys=mechanism_keys)
    _json_dump(run_root / "summary" / "aggregate.json", aggregate)
    _jsonl_dump(run_root / "summary" / "case_results.jsonl", case_payloads)
    report_path = run_root / "summary" / "report.md"
    report_path.write_text(
        _render_report(run_id=run_id, selection=selection, aggregate=aggregate, mechanism_keys=mechanism_keys),
        encoding="utf-8",
    )
    write_llm_usage_summary(run_root, summary_path=run_root / "summary" / "llm_usage.json")
    return {
        "run_id": run_id,
        "run_root": str(run_root),
        "segment_count": len(selection.segments),
        "case_count": len(selection.cases),
        "mechanism_keys": list(mechanism_keys),
        "aggregate": aggregate,
        "report_path": str(report_path),
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--manifest-path", type=Path, default=DRAFT_MANIFEST_PATH)
    parser.add_argument("--mechanism-filter", choices=MECHANISM_FILTER_VALUES, default="both")
    parser.add_argument("--judge-mode", choices=JUDGE_MODE_VALUES, default="llm")
    parser.add_argument("--segment-id", action="append", dest="segment_ids", default=[])
    parser.add_argument("--case-id", action="append", dest="case_ids", default=[])
    parser.add_argument("--reuse-output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    run_accumulation_evaluation_v2(
        run_id=str(args.run_id),
        formal_manifest_path=Path(args.manifest_path),
        mechanism_filter=str(args.mechanism_filter),
        judge_mode=str(args.judge_mode),
        segment_ids=[str(item) for item in args.segment_ids],
        case_ids=[str(item) for item in args.case_ids],
        reuse_output_dir=Path(args.reuse_output_dir).resolve() if args.reuse_output_dir else None,
    )


if __name__ == "__main__":
    main()
