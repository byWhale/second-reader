"""Run the active note-aligned user-level selective benchmark."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

from eval.attentional_v2.llm_usage_summary import write_llm_usage_summary
from eval.attentional_v2.user_level_selective_v1 import DATASET_DIR, MANIFEST_PATH
from src.attentional_v2.evaluation import build_normalized_eval_bundle as build_attentional_v2_normalized_eval_bundle
from src.iterator_reader.llm_utils import ReaderLLMError, invoke_json, llm_invocation_scope
from src.iterator_reader.storage import existing_structure_file, load_json as load_iterator_json, load_structure
from src.reading_core.runtime_contracts import ReadRequest
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_mechanisms.iterator_v1 import IteratorV1Mechanism, _normalized_eval_bundle as build_iterator_v1_normalized_eval_bundle
from src.reading_runtime.llm_gateway import eval_trace_context
from src.reading_runtime.llm_registry import DEFAULT_EVAL_JUDGE_PROFILE_ID
from src.reading_runtime.output_dir_overrides import override_output_dir


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_USER_INTENT = (
    "Read as a thoughtful co-reader and surface visible reactions when a user's highlighted note would clearly deserve notice."
)
DEFAULT_TARGET = "user_level_selective_comparison"
MECHANISM_KEYS = ("attentional_v2", "iterator_v1")
MECHANISM_FILTER_VALUES = ("attentional_v2", "iterator_v1", "both")
JUDGE_MODE_VALUES = ("llm", "none")
LABEL_PRIORITY = {
    "exact_match": 3,
    "focused_hit": 2,
    "incidental_cover": 1,
    "miss": 0,
}
CONFIDENCE_PRIORITY = {
    "high": 2,
    "medium": 1,
    "low": 0,
}
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
class NoteCase:
    note_case_id: str
    segment_id: str
    source_id: str
    book_title: str
    author: str
    language_track: str
    note_id: str
    note_text: str
    note_comment: str
    source_span_text: str
    source_sentence_ids: list[str]
    source_span_coordinate_system: str
    source_span_slices: list[dict[str, Any]]
    chapter_id: int
    chapter_title: str
    section_label: str
    raw_locator: str
    provenance: dict[str, Any]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _jsonl_load(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _resolve_dataset_dir(manifest_path: Path) -> Path:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    refs = dict(payload.get("source_refs") or {})
    roots = [Path(str(item)) for item in refs.get("user_level_dataset_roots") or []]
    if roots:
        root = roots[0]
        return root if root.is_absolute() else (ROOT / root).resolve()
    return DATASET_DIR.resolve()


def _load_segments(dataset_dir: Path) -> list[ReadingSegment]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = _jsonl_load(dataset_dir / str(manifest["segments_file"]))
    return [
        ReadingSegment(
            segment_id=str(row["segment_id"]),
            source_id=str(row["source_id"]),
            book_title=str(row["book_title"]),
            author=str(row.get("author", "")),
            language_track=str(row["language_track"]),
            start_sentence_id=str(row["start_sentence_id"]),
            end_sentence_id=str(row["end_sentence_id"]),
            chapter_ids=[int(item) for item in row.get("chapter_ids", [])],
            chapter_titles=[str(item) for item in row.get("chapter_titles", [])],
            target_note_count=int(row["target_note_count"]),
            covered_note_count=int(row["covered_note_count"]),
            termination_reason=str(row["termination_reason"]),
            segment_source_path=str(row["segment_source_path"]),
        )
        for row in rows
    ]


def _load_note_cases(dataset_dir: Path) -> list[NoteCase]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = _jsonl_load(dataset_dir / str(manifest["note_cases_file"]))
    return [
        NoteCase(
            note_case_id=str(row["note_case_id"]),
            segment_id=str(row["segment_id"]),
            source_id=str(row["source_id"]),
            book_title=str(row["book_title"]),
            author=str(row.get("author", "")),
            language_track=str(row["language_track"]),
            note_id=str(row["note_id"]),
            note_text=str(row["note_text"]),
            note_comment=str(row.get("note_comment", "")),
            source_span_text=str(row["source_span_text"]),
            source_sentence_ids=[str(item) for item in row.get("source_sentence_ids", [])],
            source_span_coordinate_system=str(row.get("source_span_coordinate_system") or "segment_source_v1"),
            source_span_slices=[
                dict(item)
                for item in row.get("source_span_slices", [])
                if isinstance(item, dict)
            ],
            chapter_id=int(row["chapter_id"]),
            chapter_title=str(row.get("chapter_title", "")),
            section_label=str(row.get("section_label", "")),
            raw_locator=str(row.get("raw_locator", "")),
            provenance=dict(row.get("provenance") or {}),
        )
        for row in rows
    ]


def _mechanism_keys_for_filter(mechanism_filter: str) -> tuple[str, ...]:
    if mechanism_filter not in MECHANISM_FILTER_VALUES:
        raise ValueError(f"unsupported mechanism filter: {mechanism_filter}")
    if mechanism_filter == "both":
        return MECHANISM_KEYS
    return (mechanism_filter,)


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
    reactions = [item for item in bundle.get("reactions") or [] if isinstance(item, dict)]
    return {
        "reaction_count": len(reactions),
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


def _run_state_status(output_dir: Path) -> str:
    run_state_path = output_dir / "_runtime" / "run_state.json"
    if not run_state_path.exists():
        return ""
    payload = load_iterator_json(run_state_path)
    return str(payload.get("status") or payload.get("stage") or "")


def _rebuild_mechanism_payload_from_output(
    *,
    segment: ReadingSegment,
    mechanism_key: str,
    source_output_dir: Path,
    run_root: Path,
) -> dict[str, Any]:
    """Rebuild one normalized eval bundle from an existing completed reading output."""

    if not source_output_dir.exists():
        raise FileNotFoundError(f"reuse output dir does not exist: {source_output_dir}")
    status = _run_state_status(source_output_dir)
    if status != "completed":
        raise RuntimeError(f"reuse output dir is not completed: {source_output_dir} status={status or 'missing'}")

    if mechanism_key == "attentional_v2":
        bundle = build_attentional_v2_normalized_eval_bundle(source_output_dir)
        mechanism_label = "Attentional V2 scaffold (Phase 1-8)"
    elif mechanism_key == "iterator_v1":
        structure = load_structure(existing_structure_file(source_output_dir))
        bundle = build_iterator_v1_normalized_eval_bundle(
            output_dir=source_output_dir,
            structure=structure,
            config_payload={"reuse_output_dir": str(source_output_dir), "segment_id": segment.segment_id},
        )
        mechanism_label = "Current Iterator-Reader implementation"
    else:
        raise ValueError(f"unsupported mechanism for reuse output: {mechanism_key}")

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


def _visible_reaction_text(reaction: dict[str, Any]) -> str:
    return _clean_text(reaction.get("anchor_quote")) or _clean_text(reaction.get("content"))


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


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


def _reaction_candidates(bundle: dict[str, Any], *, note_case: NoteCase) -> list[dict[str, Any]]:
    reactions_by_span: dict[tuple[tuple[str, int, int, int], ...], dict[str, Any]] = {}
    for index, item in enumerate(bundle.get("reactions") or []):
        if not isinstance(item, dict):
            continue
        visible_text = _visible_reaction_text(item)
        if not visible_text:
            continue
        source_slices, source_span_resolution = _reaction_source_span(
            item,
            segment_id=note_case.segment_id,
            source_id=note_case.source_id,
        )
        reaction_id = _clean_text(item.get("reaction_id")) or f"reaction_{index + 1}"
        if not source_slices:
            raise ValueError(
                f"Visible reaction {reaction_id} in segment {note_case.segment_id} has no usable source locator; "
                "user-level selective matching requires source-span locators."
            )
        span_key = tuple(sorted(_slice_key(source_slice) for source_slice in source_slices))
        candidate = reactions_by_span.get(span_key)
        if candidate is None:
            reactions_by_span[span_key] = {
                "reaction_id": reaction_id,
                "type": _clean_text(item.get("type")),
                "section_ref": _clean_text(item.get("section_ref")),
                "anchor_quote": _clean_text(item.get("anchor_quote")),
                "content": _clean_text(item.get("content")),
                "visible_text": visible_text,
                "source_span_slices": source_slices,
                "source_span_resolution": source_span_resolution,
                "duplicate_reaction_ids": [reaction_id],
                "duplicate_reaction_count": 1,
            }
            continue
        candidate["duplicate_reaction_ids"].append(reaction_id)
        candidate["duplicate_reaction_count"] = int(candidate.get("duplicate_reaction_count", 1) or 1) + 1
    return sorted(reactions_by_span.values(), key=lambda item: item["reaction_id"])


def _slices_equal(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> bool:
    return sorted(_slice_key(item) for item in left) == sorted(_slice_key(item) for item in right)


def _slice_contains(container: dict[str, Any], contained: dict[str, Any]) -> bool:
    if _clean_text(container.get("segment_id")) != _clean_text(contained.get("segment_id")):
        return False
    if int(container.get("paragraph_index", 0) or 0) != int(contained.get("paragraph_index", 0) or 0):
        return False
    return int(container.get("char_start", 0) or 0) <= int(contained.get("char_start", 0) or 0) and int(
        container.get("char_end", 0) or 0
    ) >= int(contained.get("char_end", 0) or 0)


def _slice_overlap_chars(left: dict[str, Any], right: dict[str, Any]) -> int:
    if _clean_text(left.get("segment_id")) != _clean_text(right.get("segment_id")):
        return 0
    if int(left.get("paragraph_index", 0) or 0) != int(right.get("paragraph_index", 0) or 0):
        return 0
    start = max(int(left.get("char_start", 0) or 0), int(right.get("char_start", 0) or 0))
    end = min(int(left.get("char_end", 0) or 0), int(right.get("char_end", 0) or 0))
    return max(0, end - start)


def _all_slices_contained(containers: list[dict[str, Any]], contained_items: list[dict[str, Any]]) -> bool:
    return all(any(_slice_contains(container, item) for container in containers) for item in contained_items)


def _source_span_relation(
    *,
    note_slices: list[dict[str, Any]],
    candidate_slices: list[dict[str, Any]],
) -> tuple[str, int, float]:
    if _slices_equal(note_slices, candidate_slices):
        note_chars = sum(int(item.get("char_end", 0) or 0) - int(item.get("char_start", 0) or 0) for item in note_slices)
        return "exact_same_span", note_chars, 1.0
    overlap_chars = sum(_slice_overlap_chars(note_slice, candidate_slice) for note_slice in note_slices for candidate_slice in candidate_slices)
    if overlap_chars <= 0:
        return "no_overlap", 0, 0.0
    note_chars = sum(max(0, int(item.get("char_end", 0) or 0) - int(item.get("char_start", 0) or 0)) for item in note_slices)
    coverage = overlap_chars / float(note_chars or 1)
    if _all_slices_contained(candidate_slices, note_slices):
        return "candidate_contains_note", overlap_chars, coverage
    if _all_slices_contained(note_slices, candidate_slices):
        return "note_contains_candidate", overlap_chars, coverage
    return "partial_overlap", overlap_chars, coverage


def _default_judgment(*, label: str, reason: str) -> dict[str, Any]:
    return {
        "label": label,
        "confidence": "low",
        "reason": reason,
    }


def _normalize_judgment(payload: object) -> dict[str, Any]:
    default = _default_judgment(label="miss", reason="judge_unavailable")
    if not isinstance(payload, dict):
        return default
    label = _clean_text(payload.get("label")).lower()
    if label not in {"focused_hit", "incidental_cover", "miss"}:
        label = "miss"
    confidence = _clean_text(payload.get("confidence")).lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
    return {
        "label": label,
        "confidence": confidence,
        "reason": _clean_text(payload.get("reason")) or default["reason"],
    }


def _judge_candidate_reaction(
    *,
    note_case: NoteCase,
    reaction: dict[str, Any],
    run_root: Path,
    mechanism_key: str,
    judge_mode: str,
) -> dict[str, Any]:
    if judge_mode == "none":
        return _default_judgment(label="miss", reason="judge_disabled")
    if judge_mode not in JUDGE_MODE_VALUES:
        raise ValueError(f"unsupported judge mode: {judge_mode}")
    system_prompt = """You are evaluating whether a visible reading reaction really covers a user's highlighted note.

Return JSON only.

The candidate was already selected by exact source-location overlap. Do not reward semantic similarity outside the overlapped source span.

Use:
- focused_hit: the overlapping source span covers the note's important content and the reaction is focused enough on that span
- incidental_cover: the reaction's quoted span intersects or contains the note, but the note is only incidental or the quote is too broad
- miss: the source overlap is too weak, too tangential, or does not genuinely cover the note's important content
"""
    note_payload = {
        "note_case_id": note_case.note_case_id,
        "note_text": note_case.note_text,
        "source_span_text": note_case.source_span_text,
        "source_span_slices": note_case.source_span_slices,
        "chapter_title": note_case.chapter_title,
        "section_label": note_case.section_label,
        "raw_locator": note_case.raw_locator,
    }
    reaction_payload = {
        "reaction_id": reaction["reaction_id"],
        "type": reaction["type"],
        "section_ref": reaction["section_ref"],
        "anchor_quote": reaction["anchor_quote"],
        "content": reaction["content"],
        "source_span_slices": reaction.get("source_span_slices", []),
        "source_span_resolution": reaction.get("source_span_resolution", ""),
        "overlap_relation": reaction.get("overlap_relation", ""),
        "overlap_coverage": reaction.get("overlap_coverage", 0.0),
        "duplicate_reaction_count": reaction.get("duplicate_reaction_count", 1),
    }
    base_user_prompt = (
        f"Highlighted note:\n{json.dumps(note_payload, ensure_ascii=False, indent=2)}\n\n"
        f"Visible reaction:\n{json.dumps(reaction_payload, ensure_ascii=False, indent=2)}\n\n"
        'Return JSON: {"label":"focused_hit|incidental_cover|miss","confidence":"high|medium|low","reason":"1-3 sentences."}'
    )
    payload: object = {}
    for user_prompt in (base_user_prompt, base_user_prompt + JUDGE_SCHEMA_RETRY_INSTRUCTION):
        try:
            with llm_invocation_scope(
                profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
                trace_context=eval_trace_context(
                    run_root,
                    eval_target=DEFAULT_TARGET,
                    stage="user_level_selective",
                    node="focused_note_match",
                    extra={
                        "note_case_id": note_case.note_case_id,
                        "mechanism_key": mechanism_key,
                        "reaction_id": reaction["reaction_id"],
                    },
                ),
            ):
                payload = invoke_json(system_prompt, user_prompt, _default_judgment(label="miss", reason="judge_unavailable"))
        except ReaderLLMError:
            payload = {}
        except Exception:
            payload = {}
        normalized = _normalize_judgment(payload)
        if normalized["reason"] != "judge_unavailable":
            return normalized
    return _normalize_judgment(payload)


def _ranked_result_key(result: dict[str, Any]) -> tuple[int, int, float]:
    return (
        LABEL_PRIORITY.get(str(result.get("label")), 0),
        CONFIDENCE_PRIORITY.get(str(result.get("confidence")), 0),
        float(result.get("overlap_coverage", 0.0) or 0.0),
    )


def evaluate_note_case_for_mechanism(
    *,
    note_case: NoteCase,
    mechanism_payload: dict[str, Any],
    mechanism_key: str,
    run_root: Path,
    judge_mode: str,
) -> dict[str, Any]:
    if mechanism_payload.get("status") != "completed":
        return {
            "status": "mechanism_unavailable",
            "label": "miss",
            "counts_for_recall": False,
            "best_reaction": None,
            "judgment": _default_judgment(label="miss", reason="mechanism_unavailable"),
            "candidate_reactions": [],
            "span_candidate_count": 0,
            "duplicate_reaction_count": 0,
        }

    bundle = dict(mechanism_payload.get("normalized_eval_bundle") or {})
    if note_case.source_span_coordinate_system != "segment_source_v1" or not note_case.source_span_slices:
        raise ValueError(f"Note case {note_case.note_case_id} is missing segment-source span slices")
    reactions = _reaction_candidates(bundle, note_case=note_case)

    exact_hits = [
        reaction
        for reaction in reactions
        if reaction.get("source_span_resolution") != "segment_fallback"
        and _slices_equal(note_case.source_span_slices, reaction["source_span_slices"])
    ]
    if exact_hits:
        exact_reaction = min(exact_hits, key=lambda item: (int(item.get("duplicate_reaction_count", 1) or 1), item["reaction_id"]))
        exact_reaction = dict(exact_reaction)
        exact_reaction["overlap_relation"] = "exact_same_span"
        exact_reaction["overlap_coverage"] = 1.0
        return {
            "status": "completed",
            "label": "exact_match",
            "counts_for_recall": True,
            "best_reaction": exact_reaction,
            "judgment": {
                "label": "exact_match",
                "confidence": "high",
                "reason": "Visible reaction source span exactly matched the aligned note span.",
            },
            "candidate_reactions": [exact_reaction],
            "span_candidate_count": len(exact_hits),
            "duplicate_reaction_count": sum(int(item.get("duplicate_reaction_count", 1) or 1) for item in exact_hits),
        }

    shortlisted: list[dict[str, Any]] = []
    for reaction in reactions:
        relation, overlap_chars, overlap_coverage = _source_span_relation(
            note_slices=note_case.source_span_slices,
            candidate_slices=reaction["source_span_slices"],
        )
        if relation == "no_overlap":
            continue
        candidate = dict(reaction)
        candidate["overlap_relation"] = relation
        candidate["overlap_chars"] = overlap_chars
        candidate["overlap_coverage"] = round(overlap_coverage, 4)
        shortlisted.append(candidate)
    shortlisted.sort(key=lambda item: (-float(item["overlap_coverage"]), item["reaction_id"]))

    if not shortlisted:
        return {
            "status": "completed",
            "label": "miss",
            "counts_for_recall": False,
            "best_reaction": None,
            "judgment": _default_judgment(label="miss", reason="no_candidate_source_span_overlap"),
            "candidate_reactions": [],
            "span_candidate_count": 0,
            "duplicate_reaction_count": 0,
        }

    evaluated_candidates: list[dict[str, Any]] = []
    for candidate in shortlisted:
        judgment = _judge_candidate_reaction(
            note_case=note_case,
            reaction=candidate,
            run_root=run_root,
            mechanism_key=mechanism_key,
            judge_mode=judge_mode,
        )
        payload = dict(candidate)
        payload.update(judgment)
        evaluated_candidates.append(payload)

    best = max(evaluated_candidates, key=_ranked_result_key)
    return {
        "status": "completed",
        "label": best["label"],
        "counts_for_recall": best["label"] in {"focused_hit"},
        "best_reaction": {
            "reaction_id": best["reaction_id"],
            "type": best["type"],
            "section_ref": best["section_ref"],
            "anchor_quote": best["anchor_quote"],
            "content": best["content"],
            "source_span_slices": best["source_span_slices"],
            "source_span_resolution": best.get("source_span_resolution", ""),
            "overlap_relation": best["overlap_relation"],
            "overlap_coverage": best["overlap_coverage"],
            "duplicate_reaction_count": best.get("duplicate_reaction_count", 1),
        },
        "judgment": {
            "label": best["label"],
            "confidence": best["confidence"],
            "reason": best["reason"],
        },
        "candidate_reactions": evaluated_candidates[:6],
        "span_candidate_count": len(shortlisted),
        "duplicate_reaction_count": sum(int(item.get("duplicate_reaction_count", 1) or 1) for item in shortlisted),
    }


def _segment_result_path(run_root: Path, segment_id: str) -> Path:
    return run_root / "segments" / f"{segment_id}.json"


def _note_case_result_path(run_root: Path, note_case_id: str) -> Path:
    return run_root / "note_cases" / f"{note_case_id}.json"


def _aggregate_results(
    *,
    note_case_payloads: list[dict[str, Any]],
    mechanism_keys: tuple[str, ...],
) -> dict[str, Any]:
    summary: dict[str, Any] = {"mechanisms": {}, "pairwise_delta": {}}
    for mechanism_key in mechanism_keys:
        scoped = [payload for payload in note_case_payloads if mechanism_key in payload["mechanism_results"]]
        label_counts = Counter(str(payload["mechanism_results"][mechanism_key]["label"]) for payload in scoped)
        by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for payload in scoped:
            by_source[str(payload["source_id"])].append(payload)
            by_language[str(payload["language_track"])].append(payload)
        mechanism_summary = {
            "note_case_count": len(scoped),
            "exact_match_count": label_counts.get("exact_match", 0),
            "focused_hit_count": label_counts.get("focused_hit", 0),
            "incidental_cover_count": label_counts.get("incidental_cover", 0),
            "miss_count": label_counts.get("miss", 0),
            "span_candidate_count": sum(
                int(payload["mechanism_results"][mechanism_key].get("span_candidate_count", 0) or 0)
                for payload in scoped
            ),
            "duplicate_reaction_count": sum(
                int(payload["mechanism_results"][mechanism_key].get("duplicate_reaction_count", 0) or 0)
                for payload in scoped
            ),
            "note_recall": round(
                (
                    label_counts.get("exact_match", 0) + label_counts.get("focused_hit", 0)
                )
                / float(len(scoped) or 1),
                4,
            ),
            "by_source": {},
            "by_language": {},
        }
        for source_id, items in sorted(by_source.items()):
            source_counts = Counter(str(item["mechanism_results"][mechanism_key]["label"]) for item in items)
            mechanism_summary["by_source"][source_id] = {
                "note_case_count": len(items),
                "note_recall": round(
                    (source_counts.get("exact_match", 0) + source_counts.get("focused_hit", 0)) / float(len(items) or 1),
                    4,
                ),
                "label_counts": dict(source_counts),
                "span_candidate_count": sum(
                    int(item["mechanism_results"][mechanism_key].get("span_candidate_count", 0) or 0)
                    for item in items
                ),
                "duplicate_reaction_count": sum(
                    int(item["mechanism_results"][mechanism_key].get("duplicate_reaction_count", 0) or 0)
                    for item in items
                ),
            }
        for language_track, items in sorted(by_language.items()):
            language_counts = Counter(str(item["mechanism_results"][mechanism_key]["label"]) for item in items)
            mechanism_summary["by_language"][language_track] = {
                "note_case_count": len(items),
                "note_recall": round(
                    (language_counts.get("exact_match", 0) + language_counts.get("focused_hit", 0))
                    / float(len(items) or 1),
                    4,
                ),
                "label_counts": dict(language_counts),
                "span_candidate_count": sum(
                    int(item["mechanism_results"][mechanism_key].get("span_candidate_count", 0) or 0)
                    for item in items
                ),
                "duplicate_reaction_count": sum(
                    int(item["mechanism_results"][mechanism_key].get("duplicate_reaction_count", 0) or 0)
                    for item in items
                ),
            }
        summary["mechanisms"][mechanism_key] = mechanism_summary

    if len(mechanism_keys) == 2:
        left_key, right_key = mechanism_keys
        left_recall = float(summary["mechanisms"][left_key]["note_recall"])
        right_recall = float(summary["mechanisms"][right_key]["note_recall"])
        summary["pairwise_delta"] = {
            "left_key": left_key,
            "right_key": right_key,
            "note_recall_delta": round(left_recall - right_recall, 4),
        }
    return summary


def _render_report(*, aggregate: dict[str, Any], run_id: str) -> str:
    lines = [f"# User-Level Selective Benchmark Summary: {run_id}", ""]
    for mechanism_key, payload in aggregate["mechanisms"].items():
        lines.extend(
            [
                f"## {mechanism_key}",
                f"- note cases: {payload['note_case_count']}",
                f"- note recall: {payload['note_recall']}",
                f"- exact match: {payload['exact_match_count']}",
                f"- focused hit: {payload['focused_hit_count']}",
                f"- incidental cover: {payload['incidental_cover_count']}",
                f"- miss: {payload['miss_count']}",
                f"- source-span candidates: {payload['span_candidate_count']}",
                f"- duplicate reactions across candidate spans: {payload['duplicate_reaction_count']}",
                "",
            ]
        )
    pairwise = dict(aggregate.get("pairwise_delta") or {})
    if pairwise:
        lines.extend(
            [
                "## Pairwise Delta",
                f"- {pairwise['left_key']} minus {pairwise['right_key']} note recall: {pairwise['note_recall_delta']}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def run_user_level_selective_comparison(
    *,
    run_id: str,
    manifest_path: Path = MANIFEST_PATH,
    mechanism_filter: str = "both",
    judge_mode: str = "llm",
    segment_ids: list[str] | None = None,
    note_case_ids: list[str] | None = None,
    reuse_output_dir: Path | None = None,
) -> dict[str, Any]:
    dataset_dir = _resolve_dataset_dir(manifest_path)
    segments = _load_segments(dataset_dir)
    note_cases = _load_note_cases(dataset_dir)
    if segment_ids:
        wanted_segments = set(segment_ids)
        segments = [segment for segment in segments if segment.segment_id in wanted_segments]
        note_cases = [note_case for note_case in note_cases if note_case.segment_id in wanted_segments]
    if note_case_ids:
        wanted_note_cases = set(note_case_ids)
        note_cases = [note_case for note_case in note_cases if note_case.note_case_id in wanted_note_cases]
        if not segment_ids:
            needed_segment_ids = {note_case.segment_id for note_case in note_cases}
            segments = [segment for segment in segments if segment.segment_id in needed_segment_ids]

    if not segments:
        raise ValueError("no reading segments selected")
    if not note_cases:
        raise ValueError("no note cases selected")

    run_root = DEFAULT_RUNS_ROOT / run_id
    run_root.mkdir(parents=True, exist_ok=True)
    mechanism_keys = _mechanism_keys_for_filter(mechanism_filter)
    reuse_output_dirs: dict[tuple[str, str], Path] = {}
    if reuse_output_dir is not None:
        if len(segments) != 1 or len(mechanism_keys) != 1:
            raise ValueError("--reuse-output-dir requires exactly one selected segment and one mechanism")
        reuse_output_dirs[(segments[0].segment_id, mechanism_keys[0])] = Path(reuse_output_dir)

    _json_dump(
        run_root / "meta" / "selection.json",
        {
            "generated_at": _timestamp(),
            "manifest_path": str(manifest_path),
            "dataset_dir": str(dataset_dir),
            "mechanism_keys": list(mechanism_keys),
            "judge_mode": judge_mode,
            "segment_ids": [segment.segment_id for segment in segments],
            "note_case_ids": [note_case.note_case_id for note_case in note_cases],
            "reuse_output_dir": str(reuse_output_dir) if reuse_output_dir is not None else "",
        },
    )

    segment_results: dict[str, dict[str, Any]] = {}
    for segment in segments:
        mechanism_payloads: dict[str, Any] = {}
        for mechanism_key in mechanism_keys:
            source_output_dir = reuse_output_dirs.get((segment.segment_id, mechanism_key))
            if source_output_dir is not None:
                mechanism_payloads[mechanism_key] = _rebuild_mechanism_payload_from_output(
                    segment=segment,
                    mechanism_key=mechanism_key,
                    source_output_dir=source_output_dir,
                    run_root=run_root,
                )
            else:
                mechanism_payloads[mechanism_key] = _run_mechanism_for_segment(
                    segment=segment,
                    dataset_dir=dataset_dir,
                    mechanism_key=mechanism_key,
                    run_root=run_root,
                )
        payload = {
            "segment": asdict(segment),
            "mechanisms": mechanism_payloads,
        }
        _json_dump(_segment_result_path(run_root, segment.segment_id), payload)
        segment_results[segment.segment_id] = payload

    note_case_payloads: list[dict[str, Any]] = []
    for note_case in note_cases:
        segment_payload = segment_results[note_case.segment_id]
        mechanism_results = {
            mechanism_key: evaluate_note_case_for_mechanism(
                note_case=note_case,
                mechanism_payload=dict(segment_payload["mechanisms"][mechanism_key]),
                mechanism_key=mechanism_key,
                run_root=run_root,
                judge_mode=judge_mode,
            )
            for mechanism_key in mechanism_keys
        }
        payload = {
            "note_case_id": note_case.note_case_id,
            "segment_id": note_case.segment_id,
            "source_id": note_case.source_id,
            "book_title": note_case.book_title,
            "language_track": note_case.language_track,
            "note_case": asdict(note_case),
            "mechanism_results": mechanism_results,
        }
        _json_dump(_note_case_result_path(run_root, note_case.note_case_id), payload)
        note_case_payloads.append(payload)

    aggregate = _aggregate_results(note_case_payloads=note_case_payloads, mechanism_keys=mechanism_keys)
    aggregate.update(
        {
            "run_id": run_id,
            "generated_at": _timestamp(),
            "manifest_path": str(manifest_path),
            "dataset_dir": str(dataset_dir),
            "segment_count": len(segments),
            "note_case_count": len(note_case_payloads),
        }
    )
    _json_dump(run_root / "summary" / "aggregate.json", aggregate)
    (run_root / "summary").mkdir(parents=True, exist_ok=True)
    (run_root / "summary" / "report.md").write_text(
        _render_report(aggregate=aggregate, run_id=run_id),
        encoding="utf-8",
    )
    write_llm_usage_summary(run_root, summary_path=run_root / "summary" / "llm_usage.json")
    return aggregate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=f"attentional_v2_user_level_selective_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--mechanism-filter", choices=MECHANISM_FILTER_VALUES, default="both")
    parser.add_argument("--judge-mode", choices=JUDGE_MODE_VALUES, default="llm")
    parser.add_argument("--segment-id", action="append", dest="segment_ids", default=[])
    parser.add_argument("--note-case-id", action="append", dest="note_case_ids", default=[])
    parser.add_argument("--reuse-output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_user_level_selective_comparison(
        run_id=str(args.run_id),
        manifest_path=Path(args.manifest_path).resolve(),
        mechanism_filter=str(args.mechanism_filter),
        judge_mode=str(args.judge_mode),
        segment_ids=[str(item) for item in args.segment_ids],
        note_case_ids=[str(item) for item in args.note_case_ids],
        reuse_output_dir=Path(args.reuse_output_dir).resolve() if args.reuse_output_dir else None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
