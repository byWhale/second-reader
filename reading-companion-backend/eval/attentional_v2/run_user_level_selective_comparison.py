"""Run the active note-aligned user-level selective benchmark."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import shutil
from typing import Any
import unicodedata

from eval.attentional_v2.llm_usage_summary import write_llm_usage_summary
from eval.attentional_v2.user_level_selective_v1 import DATASET_DIR, MANIFEST_PATH
from src.iterator_reader.llm_utils import ReaderLLMError, invoke_json, llm_invocation_scope
from src.reading_core.runtime_contracts import ReadRequest
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_mechanisms.iterator_v1 import IteratorV1Mechanism
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
    chapter_id: int
    chapter_title: str
    section_label: str
    raw_locator: str
    provenance: dict[str, Any]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _normalize_compare_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = "".join(character for character in text if unicodedata.category(character) != "Cf")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _compact_text(value: object) -> str:
    return re.sub(r"\s+", "", _normalize_compare_text(value))


def _char_ngrams(text: str, *, size: int = 4) -> set[str]:
    compact = _compact_text(text)
    if not compact:
        return set()
    if len(compact) <= size:
        return {compact}
    return {compact[index : index + size] for index in range(0, len(compact) - size + 1)}


def _overlap_ratio(left: str, right: str) -> float:
    left_ngrams = _char_ngrams(left)
    right_ngrams = _char_ngrams(right)
    if not left_ngrams or not right_ngrams:
        return 0.0
    return len(left_ngrams & right_ngrams) / float(min(len(left_ngrams), len(right_ngrams)))


def _candidate_overlap_score(*, note_case: NoteCase, candidate_text: str) -> tuple[float, list[str]]:
    methods: list[str] = []
    source_norm = _normalize_compare_text(note_case.source_span_text)
    candidate_norm = _normalize_compare_text(candidate_text)
    if not source_norm or not candidate_norm:
        return 0.0, methods
    if candidate_norm == source_norm:
        methods.append("exact")
        return 1.0, methods
    if candidate_norm in source_norm or source_norm in candidate_norm:
        methods.append("containment")
    note_norm = _normalize_compare_text(note_case.note_text)
    if note_norm and (candidate_norm in note_norm or note_norm in candidate_norm):
        methods.append("note_text_containment")
    overlap = _overlap_ratio(note_case.source_span_text, candidate_text)
    if overlap >= 0.2:
        methods.append("char_ngram_overlap")
    similarity = SequenceMatcher(a=_compact_text(note_case.source_span_text), b=_compact_text(candidate_text)).ratio()
    if similarity >= 0.35:
        methods.append("sequence_similarity")
    score = max(
        0.0,
        0.95 if "containment" in methods else 0.0,
        0.8 if "note_text_containment" in methods else 0.0,
        overlap,
        similarity,
    )
    return score, methods


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


def _visible_reaction_text(reaction: dict[str, Any]) -> str:
    return _clean_text(reaction.get("anchor_quote")) or _clean_text(reaction.get("content"))


def _reaction_candidates(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    reactions: list[dict[str, Any]] = []
    for index, item in enumerate(bundle.get("reactions") or []):
        if not isinstance(item, dict):
            continue
        visible_text = _visible_reaction_text(item)
        if not visible_text:
            continue
        reactions.append(
            {
                "reaction_id": _clean_text(item.get("reaction_id")) or f"reaction_{index + 1}",
                "type": _clean_text(item.get("type")),
                "section_ref": _clean_text(item.get("section_ref")),
                "anchor_quote": _clean_text(item.get("anchor_quote")),
                "content": _clean_text(item.get("content")),
                "visible_text": visible_text,
            }
        )
    return reactions


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

Use:
- focused_hit: the reaction clearly puts its attention on the note's source span or its exact idea
- incidental_cover: the reaction's quoted text happens to include or brush against the note, but the note is not the clear focus
- miss: the reaction does not genuinely cover the note
"""
    note_payload = {
        "note_case_id": note_case.note_case_id,
        "note_text": note_case.note_text,
        "source_span_text": note_case.source_span_text,
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
        float(result.get("candidate_score", 0.0) or 0.0),
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
        }

    bundle = dict(mechanism_payload.get("normalized_eval_bundle") or {})
    reactions = _reaction_candidates(bundle)
    source_span_norm = _normalize_compare_text(note_case.source_span_text)

    exact_hits = [
        reaction
        for reaction in reactions
        if _normalize_compare_text(reaction["visible_text"]) == source_span_norm
    ]
    if exact_hits:
        exact_reaction = min(exact_hits, key=lambda item: len(item["visible_text"]))
        return {
            "status": "completed",
            "label": "exact_match",
            "counts_for_recall": True,
            "best_reaction": exact_reaction,
            "judgment": {
                "label": "exact_match",
                "confidence": "high",
                "reason": "Visible reaction quote exactly matched the aligned note span.",
            },
            "candidate_reactions": [exact_reaction],
        }

    shortlisted: list[dict[str, Any]] = []
    for reaction in reactions:
        candidate_score, methods = _candidate_overlap_score(note_case=note_case, candidate_text=reaction["visible_text"])
        if candidate_score <= 0.0:
            continue
        candidate = dict(reaction)
        candidate["candidate_score"] = round(candidate_score, 3)
        candidate["candidate_methods"] = methods
        shortlisted.append(candidate)
    shortlisted.sort(key=lambda item: (-float(item["candidate_score"]), item["reaction_id"]))

    if not shortlisted:
        return {
            "status": "completed",
            "label": "miss",
            "counts_for_recall": False,
            "best_reaction": None,
            "judgment": _default_judgment(label="miss", reason="no_candidate_overlap"),
            "candidate_reactions": [],
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
        },
        "judgment": {
            "label": best["label"],
            "confidence": best["confidence"],
            "reason": best["reason"],
        },
        "candidate_reactions": evaluated_candidates[:6],
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
        },
    )

    segment_results: dict[str, dict[str, Any]] = {}
    for segment in segments:
        mechanism_payloads: dict[str, Any] = {}
        for mechanism_key in mechanism_keys:
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
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
