"""Run the formal excerpt-scale cross-mechanism comparison over the frozen benchmark."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from eval.common.taxonomy import DETERMINISTIC_METRICS, PAIRWISE_JUDGE, RUBRIC_JUDGE, normalize_methods, validate_target_slug
from src.iterator_reader.llm_utils import ReaderLLMError, eval_trace_context, invoke_json, llm_invocation_scope
from src.reading_core import BookDocument
from src.reading_core.runtime_contracts import ReadRequest
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_mechanisms.iterator_v1 import IteratorV1Mechanism
from src.reading_runtime.job_concurrency import resolve_worker_policy, submit_inherited_context
from src.reading_runtime.llm_registry import DEFAULT_EVAL_JUDGE_PROFILE_ID, DEFAULT_RUNTIME_PROFILE_ID
from src.reading_runtime.output_dir_overrides import override_output_dir
from src.reading_runtime.provisioning import ProvisionedBook, ensure_canonical_parse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_DIRS = (
    ROOT / "eval" / "datasets" / "excerpt_cases" / "attentional_v2_excerpt_en_curated_v2",
    ROOT / "eval" / "datasets" / "excerpt_cases" / "attentional_v2_excerpt_zh_curated_v2",
    ROOT / "state" / "eval_local_datasets" / "excerpt_cases" / "attentional_v2_private_library_excerpt_en_v2",
    ROOT / "state" / "eval_local_datasets" / "excerpt_cases" / "attentional_v2_private_library_excerpt_zh_v2",
)
DEFAULT_SOURCE_MANIFESTS = (
    ROOT / "eval" / "manifests" / "source_books" / "attentional_v2_public_benchmark_pool_v2.json",
    ROOT / "eval" / "manifests" / "local_refs" / "attentional_v2_private_library_v2.json",
)
DEFAULT_FORMAL_MANIFEST = ROOT / "eval" / "manifests" / "splits" / "attentional_v2_formal_benchmark_v1_draft.json"
DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_TARGET = validate_target_slug("excerpt_comparison")
DEFAULT_METHODS = normalize_methods([DETERMINISTIC_METRICS, PAIRWISE_JUDGE, RUBRIC_JUDGE])
DEFAULT_COMPARISON_TARGET = "attentional_v2 vs iterator_v1 on formal excerpt-scale reader-character and reader-value cases"
DEFAULT_USER_INTENT = (
    "Read as a thoughtful co-reader and notice meaningful turns, tensions, callbacks, definitions, and chapter-level development."
)
MECHANISM_KEYS = ("attentional_v2", "iterator_v1")
TARGET_SLICE_VALUES = ("selective_legibility", "insight_and_clarification", "both")
TARGET_FIELD_BY_SLICE = {
    "selective_legibility": "excerpt_core_frozen_now_draft",
    "insight_and_clarification": "excerpt_core_clarification_subset_frozen_draft",
}

SELECTIVE_SCORE_KEYS = (
    "text_groundedness",
    "selective_signal",
    "source_anchoring",
    "legibility_of_notice",
    "restraint_and_precision",
)
INSIGHT_SCORE_KEYS = (
    "distinction_or_definition",
    "tension_tracking",
    "clarifying_value",
    "bridge_or_context_use",
    "strong_reading_plus_knowledge",
)

TARGET_CONFIGS: dict[str, dict[str, Any]] = {
    "selective_legibility": {
        "label": "reader_character.selective_legibility",
        "score_keys": SELECTIVE_SCORE_KEYS,
        "system_prompt": """You are doing offline cross-mechanism reader evaluation.

Question family: `reader_character.selective_legibility`

Compare two mechanisms on the same excerpt case. Focus on whether the reader notices the right local thing and expresses that notice legibly.

Judge the visible reading behavior by:
- text groundedness
- selectivity
- source anchoring
- whether the why-now signal is legible
- whether the reaction stays restrained and precise instead of generic

Return JSON only.""",
        "user_prompt": """Excerpt case:
{case_json}

Attentional V2 local evidence:
{left_json}

Iterator V1 local evidence:
{right_json}

Return JSON:
{{
  "winner": "attentional_v2|iterator_v1|tie",
  "confidence": "high|medium|low",
  "scores": {{
    "attentional_v2": {{
      "text_groundedness": 1,
      "selective_signal": 1,
      "source_anchoring": 1,
      "legibility_of_notice": 1,
      "restraint_and_precision": 1
    }},
    "iterator_v1": {{
      "text_groundedness": 1,
      "selective_signal": 1,
      "source_anchoring": 1,
      "legibility_of_notice": 1,
      "restraint_and_precision": 1
    }}
  }},
  "reason": "3-6 sentences."
}}""",
    },
    "insight_and_clarification": {
        "label": "reader_value.insight_and_clarification",
        "score_keys": INSIGHT_SCORE_KEYS,
        "system_prompt": """You are doing offline cross-mechanism reader evaluation.

Question family: `reader_value.insight_and_clarification`

Compare two mechanisms on the same excerpt case. Focus on whether the reader produces clarifying value rather than merely reacting in the right place.

Judge the visible reading behavior by:
- whether it sharpens a distinction or definition when the case invites one
- whether it tracks a real tension honestly
- whether the output clarifies something meaningful
- whether any bridge or cross-span link is useful and disciplined
- whether the result feels enabled by strong reading plus broad knowledge rather than generic paraphrase

Return JSON only.""",
        "user_prompt": """Excerpt case:
{case_json}

Attentional V2 local evidence:
{left_json}

Iterator V1 local evidence:
{right_json}

Return JSON:
{{
  "winner": "attentional_v2|iterator_v1|tie",
  "confidence": "high|medium|low",
  "scores": {{
    "attentional_v2": {{
      "distinction_or_definition": 1,
      "tension_tracking": 1,
      "clarifying_value": 1,
      "bridge_or_context_use": 1,
      "strong_reading_plus_knowledge": 1
    }},
    "iterator_v1": {{
      "distinction_or_definition": 1,
      "tension_tracking": 1,
      "clarifying_value": 1,
      "bridge_or_context_use": 1,
      "strong_reading_plus_knowledge": 1
    }}
  }},
  "reason": "3-6 sentences."
}}""",
    },
}


@dataclass(frozen=True)
class ExcerptCase:
    case_id: str
    case_title: str
    split: str
    source_id: str
    book_title: str
    author: str
    output_language: str
    chapter_id: int
    chapter_title: str
    start_sentence_id: str
    end_sentence_id: str
    excerpt_text: str
    question_ids: list[str]
    phenomena: list[str]
    selection_reason: str
    judge_focus: str
    dataset_id: str
    dataset_version: str


@dataclass(frozen=True)
class ChapterUnit:
    source_id: str
    chapter_id: int
    output_language: str
    book_title: str
    author: str


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json_payload(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _normalize_compare_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = "".join(character for character in text if unicodedata.category(character) != "Cf")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def _load_cases(dataset_dir: Path) -> tuple[dict[str, Any], list[ExcerptCase]]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: list[ExcerptCase] = []
    with (dataset_dir / str(manifest["primary_file"])).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(
                ExcerptCase(
                    case_id=str(raw["case_id"]),
                    case_title=str(raw.get("case_title", raw["case_id"])),
                    split=str(raw.get("split", "")),
                    source_id=str(raw["source_id"]),
                    book_title=str(raw["book_title"]),
                    author=str(raw["author"]),
                    output_language=str(raw.get("output_language", "")),
                    chapter_id=int(raw["chapter_id"]),
                    chapter_title=str(raw.get("chapter_title", "")),
                    start_sentence_id=str(raw["start_sentence_id"]),
                    end_sentence_id=str(raw["end_sentence_id"]),
                    excerpt_text=str(raw["excerpt_text"]),
                    question_ids=[str(item) for item in raw.get("question_ids", [])],
                    phenomena=[str(item) for item in raw.get("phenomena", [])],
                    selection_reason=str(raw.get("selection_reason", "")),
                    judge_focus=str(raw.get("judge_focus", "")),
                    dataset_id=str(manifest["dataset_id"]),
                    dataset_version=str(manifest["version"]),
                )
            )
    return manifest, rows


def _load_source_index(manifest_paths: list[Path]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for manifest_path in manifest_paths:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
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
            relative_local_path = _clean_text(item.get("relative_local_path"))
            if source_id and relative_local_path:
                index[source_id] = dict(item)
    return index


def _load_formal_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _target_case_ids_from_manifest(formal_manifest: dict[str, Any], *, target_slice: str) -> dict[str, list[str]]:
    if target_slice not in TARGET_SLICE_VALUES:
        raise ValueError(f"unsupported target slice: {target_slice}")
    if target_slice == "both":
        requested = ("selective_legibility", "insight_and_clarification")
    else:
        requested = (target_slice,)
    target_case_ids: dict[str, list[str]] = {}
    for target_name in requested:
        split_name = TARGET_FIELD_BY_SLICE[target_name]
        split_payload = dict(formal_manifest.get("splits", {}).get(split_name) or {})
        all_case_ids = [str(item) for item in split_payload.get("all", []) if str(item).strip()]
        if not all_case_ids:
            raise ValueError(f"formal manifest split is empty: {split_name}")
        target_case_ids[target_name] = all_case_ids
    return target_case_ids


def _merge_case_id_order(target_case_ids: dict[str, list[str]]) -> list[str]:
    merged: list[str] = []
    for case_ids in target_case_ids.values():
        for case_id in case_ids:
            if case_id not in merged:
                merged.append(case_id)
    return merged


def _resolve_selected_cases(
    *,
    dataset_dirs: list[Path],
    selected_case_ids: list[str],
) -> tuple[list[dict[str, Any]], list[ExcerptCase], dict[str, ExcerptCase]]:
    manifests: list[dict[str, Any]] = []
    case_index: dict[str, ExcerptCase] = {}
    for dataset_dir in dataset_dirs:
        manifest, cases = _load_cases(dataset_dir)
        manifests.append(manifest)
        for case in cases:
            case_index.setdefault(case.case_id, case)
    resolved_cases: list[ExcerptCase] = []
    missing: list[str] = []
    for case_id in selected_case_ids:
        case = case_index.get(case_id)
        if case is None:
            missing.append(case_id)
            continue
        resolved_cases.append(case)
    if missing:
        raise ValueError(f"missing excerpt cases: {', '.join(sorted(missing))}")
    return manifests, resolved_cases, case_index


def _chapter_unit_key(source_id: str, chapter_id: int) -> str:
    return f"{source_id}__chapter_{chapter_id}"


def _find_span(document: BookDocument, case: ExcerptCase) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        if int(chapter.get("id", 0) or 0) != case.chapter_id:
            continue
        sentences = [item for item in chapter.get("sentences", []) if isinstance(item, dict)]
        by_id = {str(sentence.get("sentence_id", "")): index for index, sentence in enumerate(sentences)}
        if case.start_sentence_id not in by_id or case.end_sentence_id not in by_id:
            raise ValueError(f"case span not found in chapter: {case.case_id}")
        start = by_id[case.start_sentence_id]
        end = by_id[case.end_sentence_id]
        if end < start:
            raise ValueError(f"case span reversed: {case.case_id}")
        return chapter, sentences[start : end + 1]
    raise ValueError(f"chapter missing for case: {case.case_id}")


def _case_section_refs(span: list[dict[str, Any]], *, chapter_id: int) -> set[str]:
    refs: set[str] = set()
    for sentence in span:
        paragraph_index = int(sentence.get("paragraph_index", 0) or 0)
        if paragraph_index > 0:
            refs.add(f"{chapter_id}.{paragraph_index}")
    return refs


def _section_ref_chapter(section_ref: str) -> int | None:
    head, _, _tail = _clean_text(section_ref).partition(".")
    digits = "".join(character for character in head if character.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _text_match_score(candidate_text: str, *, case_excerpt_norm: str, sentence_norms: list[str]) -> tuple[int, list[str]]:
    normalized = _normalize_compare_text(candidate_text)
    if not normalized:
        return 0, []
    methods: list[str] = []
    score = 0
    if case_excerpt_norm and (normalized in case_excerpt_norm or case_excerpt_norm in normalized):
        methods.append("excerpt_text")
        score += 5
    for sentence_text in sentence_norms:
        if sentence_text and (normalized in sentence_text or sentence_text in normalized):
            if "sentence_text" not in methods:
                methods.append("sentence_text")
            score = max(score, 4)
            break
    return score, methods


def _match_entry(
    *,
    chapter_id: int,
    case_section_refs: set[str],
    case_excerpt_norm: str,
    sentence_norms: list[str],
    section_ref: str,
    candidate_text: str,
) -> tuple[int, list[str]]:
    methods: list[str] = []
    score = 0
    cleaned_section_ref = _clean_text(section_ref)
    if cleaned_section_ref:
        if cleaned_section_ref in case_section_refs:
            methods.append("section_ref_exact")
            score += 6
        elif _section_ref_chapter(cleaned_section_ref) == chapter_id:
            methods.append("section_ref_chapter")
            score += 2
    text_score, text_methods = _text_match_score(
        candidate_text,
        case_excerpt_norm=case_excerpt_norm,
        sentence_norms=sentence_norms,
    )
    for method in text_methods:
        if method not in methods:
            methods.append(method)
    score += text_score
    return score, methods


def _primary_match_method(match_method_counts: Counter[str]) -> str:
    if not match_method_counts:
        return "none"
    has_section_ref = bool(match_method_counts.get("section_ref_exact") or match_method_counts.get("section_ref_chapter"))
    has_anchor_or_excerpt = bool(match_method_counts.get("excerpt_text"))
    has_text_fallback = bool(match_method_counts.get("sentence_text"))
    if has_section_ref and has_anchor_or_excerpt:
        return "section_ref_plus_anchor_or_current_excerpt"
    if has_section_ref and has_text_fallback:
        return "section_ref_plus_normalized_text_fallback"
    if has_section_ref:
        return "section_ref"
    if has_anchor_or_excerpt:
        return "anchor_or_current_excerpt"
    if has_text_fallback:
        return "normalized_text_fallback"
    return "none"


def _extract_case_local_evidence(
    *,
    case: ExcerptCase,
    bundle: dict[str, Any],
    document: BookDocument,
) -> dict[str, Any]:
    chapter, span = _find_span(document, case)
    case_excerpt_norm = _normalize_compare_text(case.excerpt_text)
    sentence_norms = [_normalize_compare_text(sentence.get("text", "")) for sentence in span]
    section_refs = _case_section_refs(span, chapter_id=case.chapter_id)

    matched_reactions: list[dict[str, Any]] = []
    for item in bundle.get("reactions") or []:
        if not isinstance(item, dict):
            continue
        candidate_text = _clean_text(item.get("anchor_quote") or item.get("content"))
        score, methods = _match_entry(
            chapter_id=case.chapter_id,
            case_section_refs=section_refs,
            case_excerpt_norm=case_excerpt_norm,
            sentence_norms=sentence_norms,
            section_ref=_clean_text(item.get("section_ref")),
            candidate_text=candidate_text,
        )
        if score <= 0:
            continue
        matched_reactions.append(
            {
                "type": _clean_text(item.get("type")),
                "section_ref": _clean_text(item.get("section_ref")),
                "anchor_quote": _clean_text(item.get("anchor_quote"))[:240],
                "content": _clean_text(item.get("content"))[:320],
                "match_score": score,
                "match_methods": methods,
            }
        )

    matched_events: list[dict[str, Any]] = []
    for item in bundle.get("attention_events") or []:
        if not isinstance(item, dict):
            continue
        candidate_text = _clean_text(item.get("current_excerpt") or item.get("message"))
        score, methods = _match_entry(
            chapter_id=case.chapter_id,
            case_section_refs=section_refs,
            case_excerpt_norm=case_excerpt_norm,
            sentence_norms=sentence_norms,
            section_ref=_clean_text(item.get("section_ref")),
            candidate_text=candidate_text,
        )
        if score <= 0:
            continue
        matched_events.append(
            {
                "kind": _clean_text(item.get("kind")),
                "phase": _clean_text(item.get("phase")),
                "section_ref": _clean_text(item.get("section_ref")),
                "move_type": _clean_text(item.get("move_type")),
                "message": _clean_text(item.get("message"))[:240],
                "current_excerpt": _clean_text(item.get("current_excerpt"))[:240],
                "match_score": score,
                "match_methods": methods,
            }
        )

    matched_reactions.sort(key=lambda item: (-int(item["match_score"]), str(item["section_ref"]), str(item["type"])))
    matched_events.sort(key=lambda item: (-int(item["match_score"]), str(item["section_ref"]), str(item["kind"])))
    match_method_counts = Counter()
    for item in matched_reactions + matched_events:
        match_method_counts.update(str(method) for method in item.get("match_methods", []))
    return {
        "chapter_ref": _clean_text(chapter.get("title")) or f"Chapter {case.chapter_id}",
        "case_section_refs": sorted(section_refs),
        "matched_reaction_count": len(matched_reactions),
        "matched_attention_event_count": len(matched_events),
        "matched_reactions": matched_reactions[:6],
        "matched_attention_events": matched_events[:8],
        "match_method": _primary_match_method(match_method_counts),
        "match_method_counts": dict(match_method_counts),
        "chapter_output": dict((bundle.get("chapters") or [{}])[0]) if isinstance(bundle.get("chapters"), list) and bundle.get("chapters") else {},
        "memory_summaries": [str(item)[:280] for item in (bundle.get("memory_summaries") or [])[:3]],
    }


def _summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    chapter = {}
    chapters = bundle.get("chapters") or []
    if isinstance(chapters, list) and chapters:
        chapter = dict(chapters[0])
    reactions = []
    for item in bundle.get("reactions") or []:
        if not isinstance(item, dict):
            continue
        reactions.append(
            {
                "type": _clean_text(item.get("type")),
                "section_ref": _clean_text(item.get("section_ref")),
                "anchor_quote": _clean_text(item.get("anchor_quote"))[:180],
                "content": _clean_text(item.get("content"))[:240],
            }
        )
    attention_events = []
    for item in bundle.get("attention_events") or []:
        if not isinstance(item, dict):
            continue
        if _clean_text(item.get("kind")) in {"position", "checkpoint"}:
            continue
        attention_events.append(
            {
                "kind": _clean_text(item.get("kind")),
                "phase": _clean_text(item.get("phase")),
                "section_ref": _clean_text(item.get("section_ref")),
                "move_type": _clean_text(item.get("move_type")),
                "message": _clean_text(item.get("message"))[:180],
                "current_excerpt": _clean_text(item.get("current_excerpt"))[:180],
            }
        )
    return {
        "run_snapshot": dict(bundle.get("run_snapshot") or {}),
        "chapter_output": chapter,
        "reaction_count": len(reactions),
        "attention_event_count": len(attention_events),
        "reactions": reactions[:5],
        "attention_events": attention_events[:8],
        "memory_summaries": [str(item)[:280] for item in (bundle.get("memory_summaries") or [])[:4]],
    }


def _default_judgment(score_keys: tuple[str, ...], *, reason: str) -> dict[str, Any]:
    return {
        "winner": "tie",
        "confidence": "low",
        "scores": {
            "attentional_v2": {key: 0 for key in score_keys},
            "iterator_v1": {key: 0 for key in score_keys},
        },
        "reason": reason,
    }


def _normalize_judgment(payload: object, *, score_keys: tuple[str, ...], default_reason: str) -> dict[str, Any]:
    default = _default_judgment(score_keys, reason=default_reason)
    if not isinstance(payload, dict):
        return default
    winner = _clean_text(payload.get("winner")).lower()
    if winner not in {"attentional_v2", "iterator_v1", "tie"}:
        winner = "tie"
    confidence = _clean_text(payload.get("confidence")).lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
    normalized = _default_judgment(score_keys, reason=_clean_text(payload.get("reason")) or default_reason)
    normalized["winner"] = winner
    normalized["confidence"] = confidence
    scores = payload.get("scores")
    if isinstance(scores, dict):
        for side in ("attentional_v2", "iterator_v1"):
            side_scores = scores.get(side)
            if not isinstance(side_scores, dict):
                continue
            for key in score_keys:
                try:
                    value = int(side_scores.get(key))
                except (TypeError, ValueError):
                    value = 0
                normalized["scores"][side][key] = max(0, min(5, value))
    return normalized


@contextmanager
def _isolated_output_dir(output_dir: Path):
    with override_output_dir(output_dir):
        yield


def _unit_log_label(unit: ChapterUnit) -> str:
    return f"{unit.source_id}::chapter_{unit.chapter_id}"


def _log_unit_progress(unit: ChapterUnit, message: str) -> None:
    print(f"[unit {_unit_log_label(unit)}] {message}", flush=True)


def _log_case_progress(case: ExcerptCase, message: str) -> None:
    print(f"[case {case.case_id}] {message}", flush=True)


def _mechanism_failure_payload(mechanism_key: str, *, error: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "mechanism_key": mechanism_key,
        "mechanism_label": mechanism_key,
        "output_dir": "",
        "normalized_eval_bundle": {},
        "bundle_summary": {},
        "error": error,
    }


def _run_mechanism_for_unit(
    unit: ChapterUnit,
    source: dict[str, Any],
    *,
    mechanism_key: str,
    run_root: Path,
) -> dict[str, Any]:
    if mechanism_key == "attentional_v2":
        mechanism = AttentionalV2Mechanism()
    elif mechanism_key == "iterator_v1":
        mechanism = IteratorV1Mechanism()
    else:
        raise ValueError(f"unsupported mechanism: {mechanism_key}")

    book_path = ROOT / str(source["relative_local_path"])
    isolated_output_dir = run_root / "outputs" / _chapter_unit_key(unit.source_id, unit.chapter_id) / mechanism_key
    _log_unit_progress(unit, f"[mechanism-start] {mechanism_key}")
    shutil.rmtree(isolated_output_dir, ignore_errors=True)
    isolated_output_dir.parent.mkdir(parents=True, exist_ok=True)
    with _isolated_output_dir(isolated_output_dir):
        result = mechanism.read_book(
            ReadRequest(
                book_path=book_path,
                chapter_number=int(unit.chapter_id),
                continue_mode=False,
                user_intent=DEFAULT_USER_INTENT,
                language_mode=unit.output_language,
                task_mode="sequential",
                mechanism_key=mechanism_key,
                mechanism_config={"persist_normalized_eval_bundle": True},
            )
        )
    bundle = dict(result.normalized_eval_bundle or {})
    _json_dump(run_root / "bundles" / mechanism_key / f"{_chapter_unit_key(unit.source_id, unit.chapter_id)}.json", bundle)
    _log_unit_progress(unit, f"[mechanism-completed] {mechanism_key}")
    return {
        "status": "completed",
        "mechanism_key": mechanism_key,
        "mechanism_label": result.mechanism.label,
        "output_dir": str(result.output_dir),
        "normalized_eval_bundle": bundle,
        "bundle_summary": _summarize_bundle(bundle),
        "error": "",
    }


def _run_mechanism_worker(payload_path: Path, result_path: Path) -> int:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    unit = ChapterUnit(**dict(payload["unit"]))
    source = dict(payload["source"])
    result = _run_mechanism_for_unit(
        unit,
        source,
        mechanism_key=str(payload["mechanism_key"]),
        run_root=Path(str(payload["run_root"])),
    )
    _write_json_payload(result_path, result)
    return 0


def _run_unit_worker(payload_path: Path, result_path: Path) -> int:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    unit = ChapterUnit(**dict(payload["unit"]))
    source = dict(payload["source"])
    result = _run_chapter_unit(
        unit,
        source=source,
        run_root=Path(str(payload["run_root"])),
        mechanism_execution_mode=str(payload["mechanism_execution_mode"]),
    )
    _write_json_payload(result_path, result)
    return 0


def _run_payload_worker(payload_path: Path, result_path: Path) -> int:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    worker_kind = str(payload.get("worker_kind", "mechanism")).strip() or "mechanism"
    if worker_kind == "mechanism":
        return _run_mechanism_worker(payload_path, result_path)
    if worker_kind == "unit":
        return _run_unit_worker(payload_path, result_path)
    raise ValueError(f"unsupported worker kind: {worker_kind}")


def _run_mechanism_subprocess(
    unit: ChapterUnit,
    source: dict[str, Any],
    *,
    mechanism_key: str,
    run_root: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="excerpt-comparison-mechanism-worker-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        payload_path = temp_dir / "payload.json"
        result_path = temp_dir / "result.json"
        _write_json_payload(
            payload_path,
            {
                "worker_kind": "mechanism",
                "unit": asdict(unit),
                "source": source,
                "mechanism_key": mechanism_key,
                "run_root": str(run_root),
            },
        )
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker-payload",
            str(payload_path),
            "--worker-result",
            str(result_path),
        ]
        subprocess.run(command, cwd=str(ROOT), check=True)
        return json.loads(result_path.read_text(encoding="utf-8"))


def _run_unit_subprocess(
    unit: ChapterUnit,
    *,
    source: dict[str, Any],
    run_root: Path,
    mechanism_execution_mode: str,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="excerpt-comparison-unit-worker-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        payload_path = temp_dir / "payload.json"
        result_path = temp_dir / "result.json"
        _write_json_payload(
            payload_path,
            {
                "worker_kind": "unit",
                "unit": asdict(unit),
                "source": source,
                "run_root": str(run_root),
                "mechanism_execution_mode": mechanism_execution_mode,
            },
        )
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker-payload",
            str(payload_path),
            "--worker-result",
            str(result_path),
        ]
        subprocess.run(command, cwd=str(ROOT), check=True)
        return json.loads(result_path.read_text(encoding="utf-8"))


def _run_chapter_unit(
    unit: ChapterUnit,
    *,
    source: dict[str, Any],
    run_root: Path,
    mechanism_execution_mode: str,
) -> dict[str, Any]:
    if mechanism_execution_mode not in {"serial", "parallel"}:
        raise ValueError(f"unsupported mechanism execution mode: {mechanism_execution_mode}")

    def _run_one(mechanism_key: str) -> dict[str, Any]:
        try:
            return _run_mechanism_for_unit(unit, source, mechanism_key=mechanism_key, run_root=run_root)
        except Exception as exc:
            _log_unit_progress(unit, f"[mechanism-failed] {mechanism_key} error={exc}")
            return _mechanism_failure_payload(mechanism_key, error=str(exc))

    results: dict[str, dict[str, Any]] = {}
    if mechanism_execution_mode == "serial":
        for mechanism_key in MECHANISM_KEYS:
            results[mechanism_key] = _run_one(mechanism_key)
    else:
        with ThreadPoolExecutor(max_workers=len(MECHANISM_KEYS), thread_name_prefix="excerpt-mechanism") as executor:
            future_to_mechanism = {
                executor.submit(_run_mechanism_subprocess, unit, source, mechanism_key=mechanism_key, run_root=run_root): mechanism_key
                for mechanism_key in MECHANISM_KEYS
            }
            for future in as_completed(future_to_mechanism):
                mechanism_key = future_to_mechanism[future]
                try:
                    results[mechanism_key] = future.result()
                except Exception as exc:
                    results[mechanism_key] = _mechanism_failure_payload(mechanism_key, error=str(exc))
    return {
        "unit_key": _chapter_unit_key(unit.source_id, unit.chapter_id),
        "source_id": unit.source_id,
        "chapter_id": unit.chapter_id,
        "output_language": unit.output_language,
        "book_title": unit.book_title,
        "author": unit.author,
        "mechanisms": {mechanism_key: results[mechanism_key] for mechanism_key in MECHANISM_KEYS},
    }


def _judge_target(
    *,
    target_name: str,
    case: ExcerptCase,
    attentional: dict[str, Any],
    iterator: dict[str, Any],
    run_root: Path,
    judge_mode: str,
) -> dict[str, Any]:
    config = TARGET_CONFIGS[target_name]
    score_keys = tuple(config["score_keys"])
    if judge_mode == "none":
        judgment = _default_judgment(score_keys, reason="judge_disabled")
        _log_case_progress(case, f"[judge-skip] {target_name} winner={judgment['winner']}")
        return judgment
    if attentional.get("status") != "completed" or iterator.get("status") != "completed":
        judgment = _default_judgment(score_keys, reason="mechanism_unavailable")
        _log_case_progress(case, f"[judge-skip] {target_name} reason=mechanism_unavailable")
        return judgment

    _log_case_progress(case, f"[judge-start] {target_name}")
    try:
        with llm_invocation_scope(
            profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
            trace_context=eval_trace_context(
                run_root,
                eval_target=DEFAULT_TARGET,
                stage="excerpt_comparison",
                node=target_name,
            ),
        ):
            payload = invoke_json(
                str(config["system_prompt"]),
                str(config["user_prompt"]).format(
                    case_json=json.dumps(
                        {
                            "case_id": case.case_id,
                            "case_title": case.case_title,
                            "judge_focus": case.judge_focus,
                            "selection_reason": case.selection_reason,
                            "question_ids": case.question_ids,
                            "phenomena": case.phenomena,
                            "excerpt_text": case.excerpt_text,
                            "book_title": case.book_title,
                            "chapter_title": case.chapter_title,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    left_json=json.dumps(attentional["local_evidence"], ensure_ascii=False, indent=2),
                    right_json=json.dumps(iterator["local_evidence"], ensure_ascii=False, indent=2),
                ),
                _default_judgment(score_keys, reason="judge_unavailable"),
            )
    except ReaderLLMError:
        payload = {}
    except Exception:
        payload = {}
    judgment = _normalize_judgment(payload, score_keys=score_keys, default_reason="judge_unavailable")
    _log_case_progress(case, f"[judge-completed] {target_name} winner={judgment['winner']}")
    return judgment


def _judge_targets_for_case(
    *,
    case: ExcerptCase,
    case_targets: list[str],
    mechanisms: dict[str, dict[str, Any]],
    run_root: Path,
    judge_mode: str,
    judge_execution_mode: str,
) -> dict[str, dict[str, Any]]:
    if judge_execution_mode not in {"serial", "parallel"}:
        raise ValueError(f"unsupported judge execution mode: {judge_execution_mode}")
    if judge_execution_mode == "serial" or judge_mode == "none" or len(case_targets) <= 1:
        return {
            target_name: {
                "judgment": _judge_target(
                    target_name=target_name,
                    case=case,
                    attentional=mechanisms["attentional_v2"],
                    iterator=mechanisms["iterator_v1"],
                    run_root=run_root,
                    judge_mode=judge_mode,
                )
            }
            for target_name in case_targets
        }

    target_results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=len(case_targets), thread_name_prefix="excerpt-judge") as executor:
        future_to_target = {
            executor.submit(
                _judge_target,
                target_name=target_name,
                case=case,
                attentional=mechanisms["attentional_v2"],
                iterator=mechanisms["iterator_v1"],
                run_root=run_root,
                judge_mode=judge_mode,
            ): target_name
            for target_name in case_targets
        }
        for future in as_completed(future_to_target):
            target_name = future_to_target[future]
            try:
                judgment = future.result()
            except Exception:
                judgment = _default_judgment(tuple(TARGET_CONFIGS[target_name]["score_keys"]), reason="judge_unavailable")
            target_results[target_name] = {"judgment": judgment}
    return {target_name: target_results[target_name] for target_name in case_targets}


def _score_average(side_scores: dict[str, int]) -> float:
    values = [float(value) for value in side_scores.values()]
    return round(mean(values), 3) if values else 0.0


def _aggregate_target(case_results: list[dict[str, Any]], *, target_name: str) -> dict[str, Any]:
    scoped = [item for item in case_results if target_name in item["target_results"]]
    if not scoped:
        return {
            "case_count": 0,
            "winner_counts": {},
            "judge_unavailable_count": 0,
            "mechanism_failure_count": 0,
            "average_scores": {
                "attentional_v2": 0.0,
                "iterator_v1": 0.0,
            },
            "language_summaries": {},
        }

    winner_counts = Counter(item["target_results"][target_name]["judgment"]["winner"] for item in scoped)
    judge_unavailable_count = sum(
        1
        for item in scoped
        if item["target_results"][target_name]["judgment"]["reason"] in {"judge_unavailable", "mechanism_unavailable", "case_error"}
    )
    mechanism_failure_count = sum(
        1
        for item in scoped
        if any(
            mechanism_payload.get("status") != "completed"
            for mechanism_payload in item["mechanisms"].values()
        )
    )
    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in scoped:
        by_language[str(item["output_language"])].append(item)
    summary = {
        "case_count": len(scoped),
        "winner_counts": dict(winner_counts),
        "judge_unavailable_count": judge_unavailable_count,
        "mechanism_failure_count": mechanism_failure_count,
        "average_scores": {
            "attentional_v2": round(
                mean(_score_average(item["target_results"][target_name]["judgment"]["scores"]["attentional_v2"]) for item in scoped),
                3,
            ),
            "iterator_v1": round(
                mean(_score_average(item["target_results"][target_name]["judgment"]["scores"]["iterator_v1"]) for item in scoped),
                3,
            ),
        },
        "language_summaries": {},
    }
    for language, items in sorted(by_language.items()):
        language_winners = Counter(item["target_results"][target_name]["judgment"]["winner"] for item in items)
        summary["language_summaries"][language] = {
            "case_count": len(items),
            "winner_counts": dict(language_winners),
            "judge_unavailable_count": sum(
                1
                for item in items
                if item["target_results"][target_name]["judgment"]["reason"] in {"judge_unavailable", "mechanism_unavailable", "case_error"}
            ),
            "average_scores": {
                "attentional_v2": round(
                    mean(_score_average(item["target_results"][target_name]["judgment"]["scores"]["attentional_v2"]) for item in items),
                    3,
                ),
                "iterator_v1": round(
                    mean(_score_average(item["target_results"][target_name]["judgment"]["scores"]["iterator_v1"]) for item in items),
                    3,
                ),
            },
        }
    return summary


def _aggregate(case_results: list[dict[str, Any]], *, target_names: list[str]) -> dict[str, Any]:
    return {
        "case_count": len(case_results),
        "target_summaries": {
            target_name: _aggregate_target(case_results, target_name=target_name)
            for target_name in target_names
        },
    }


def _build_markdown_report(
    *,
    run_id: str,
    selected_cases: list[ExcerptCase],
    target_case_ids: dict[str, list[str]],
    aggregate: dict[str, Any],
    datasets: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# Excerpt Comparison")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("This report records the formal excerpt-scale cross-mechanism comparison between `attentional_v2` and `iterator_v1` on the frozen benchmark slice.")
    lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append(f"- Run ID: `{run_id}`")
    lines.append(f"- Target: `{DEFAULT_TARGET}`")
    lines.append(f"- Methods: `{', '.join(DEFAULT_METHODS)}`")
    lines.append(f"- Comparison target: {DEFAULT_COMPARISON_TARGET}")
    lines.append("")
    lines.append("## Datasets")
    lines.append("")
    for dataset in datasets:
        lines.append(f"- `{dataset['dataset_id']}` (language `{dataset['language_track']}`, version `{dataset['version']}`)")
    lines.append("")
    lines.append("## Selected Cases")
    lines.append("")
    for case in selected_cases:
        target_membership = [target_name for target_name, case_ids in target_case_ids.items() if case.case_id in case_ids]
        lines.append(f"- `{case.case_id}` (`{case.output_language}`, targets `{', '.join(target_membership)}`)")
    lines.append("")
    lines.append("## Aggregate Findings")
    lines.append("")
    for target_name, summary in aggregate["target_summaries"].items():
        lines.append(f"### `{target_name}`")
        lines.append(f"- Cases: `{summary['case_count']}`")
        lines.append(f"- Winner counts: `{json.dumps(summary['winner_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Judge unavailable count: `{summary['judge_unavailable_count']}`")
        lines.append(f"- Mechanism failure count: `{summary['mechanism_failure_count']}`")
        lines.append(f"- Average scores: `{json.dumps(summary['average_scores'], ensure_ascii=False, sort_keys=True)}`")
        for language, language_summary in summary["language_summaries"].items():
            lines.append(
                f"- `{language}`: `{json.dumps({'case_count': language_summary['case_count'], 'winner_counts': language_summary['winner_counts'], 'judge_unavailable_count': language_summary['judge_unavailable_count'], 'average_scores': language_summary['average_scores']}, ensure_ascii=False, sort_keys=True)}`"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _evaluate_case(
    case: ExcerptCase,
    *,
    case_targets: list[str],
    unit_result: dict[str, Any],
    document: BookDocument,
    run_root: Path,
    judge_mode: str,
    judge_execution_mode: str,
) -> dict[str, Any]:
    _log_case_progress(case, f"[case-start] judge_mode={judge_mode} judge_execution_mode={judge_execution_mode}")
    mechanisms: dict[str, dict[str, Any]] = {}
    for mechanism_key in MECHANISM_KEYS:
        mechanism_result = dict(unit_result["mechanisms"][mechanism_key])
        if mechanism_result.get("status") == "completed":
            local_evidence = _extract_case_local_evidence(
                case=case,
                bundle=dict(mechanism_result.get("normalized_eval_bundle") or {}),
                document=document,
            )
        else:
            local_evidence = {
                "error": _clean_text(mechanism_result.get("error")),
                "matched_reaction_count": 0,
                "matched_attention_event_count": 0,
                "matched_reactions": [],
                "matched_attention_events": [],
                "match_method_counts": {},
            }
        mechanisms[mechanism_key] = {
            "status": str(mechanism_result.get("status", "failed") or "failed"),
            "mechanism_label": _clean_text(mechanism_result.get("mechanism_label")) or mechanism_key,
            "output_dir": _clean_text(mechanism_result.get("output_dir")),
            "bundle_summary": dict(mechanism_result.get("bundle_summary") or {}),
            "local_evidence": local_evidence,
            "error": _clean_text(mechanism_result.get("error")),
        }
    target_results = _judge_targets_for_case(
        case=case,
        case_targets=case_targets,
        mechanisms=mechanisms,
        run_root=run_root,
        judge_mode=judge_mode,
        judge_execution_mode=judge_execution_mode,
    )
    _log_case_progress(case, "[case-completed]")
    return {
        "case_id": case.case_id,
        "case_title": case.case_title,
        "source_id": case.source_id,
        "chapter_id": case.chapter_id,
        "chapter_title": case.chapter_title,
        "book_title": case.book_title,
        "author": case.author,
        "output_language": case.output_language,
        "case_targets": case_targets,
        "mechanisms": mechanisms,
        "target_results": target_results,
    }


def _case_failure_result(
    case: ExcerptCase,
    *,
    case_targets: list[str],
    unit_result: dict[str, Any],
    error: str,
) -> dict[str, Any]:
    mechanisms: dict[str, dict[str, Any]] = {}
    for mechanism_key in MECHANISM_KEYS:
        mechanism_result = dict(unit_result.get("mechanisms", {}).get(mechanism_key) or {})
        mechanisms[mechanism_key] = {
            "status": str(mechanism_result.get("status", "failed") or "failed"),
            "mechanism_label": _clean_text(mechanism_result.get("mechanism_label")) or mechanism_key,
            "output_dir": _clean_text(mechanism_result.get("output_dir")),
            "bundle_summary": dict(mechanism_result.get("bundle_summary") or {}),
            "local_evidence": {
                "error": _clean_text(error),
                "match_method": "none",
                "matched_reaction_count": 0,
                "matched_attention_event_count": 0,
                "matched_reactions": [],
                "matched_attention_events": [],
                "match_method_counts": {},
            },
            "error": _clean_text(mechanism_result.get("error")),
        }
    target_results = {
        target_name: {
            "judgment": _default_judgment(tuple(TARGET_CONFIGS[target_name]["score_keys"]), reason="case_error")
        }
        for target_name in case_targets
    }
    return {
        "case_id": case.case_id,
        "case_title": case.case_title,
        "source_id": case.source_id,
        "chapter_id": case.chapter_id,
        "chapter_title": case.chapter_title,
        "book_title": case.book_title,
        "author": case.author,
        "output_language": case.output_language,
        "case_targets": case_targets,
        "mechanisms": mechanisms,
        "target_results": target_results,
        "case_error": _clean_text(error),
    }


def run_benchmark(
    *,
    dataset_dirs: list[Path],
    source_manifest_paths: list[Path],
    formal_manifest_path: Path,
    runs_root: Path,
    run_id: str | None = None,
    target_slice: str = "both",
    case_ids: list[str] | None = None,
    judge_mode: str = "llm",
    mechanism_execution_mode: str = "serial",
    judge_execution_mode: str = "serial",
    case_workers: int | None = None,
) -> dict[str, Any]:
    formal_manifest = _load_formal_manifest(formal_manifest_path)
    target_case_ids = _target_case_ids_from_manifest(formal_manifest, target_slice=target_slice)
    if case_ids:
        wanted = {case_id for case_id in case_ids}
        target_case_ids = {
            target_name: [case_id for case_id in ids if case_id in wanted]
            for target_name, ids in target_case_ids.items()
        }
    selected_case_ids = _merge_case_id_order(target_case_ids)
    if not selected_case_ids:
        raise ValueError("no excerpt cases selected")

    dataset_manifests, selected_cases, _case_index = _resolve_selected_cases(
        dataset_dirs=dataset_dirs,
        selected_case_ids=selected_case_ids,
    )
    selected_case_ids = [case.case_id for case in selected_cases]
    target_case_ids = {
        target_name: [case_id for case_id in ids if case_id in selected_case_ids]
        for target_name, ids in target_case_ids.items()
    }
    source_index = _load_source_index(source_manifest_paths)
    missing_sources = sorted({case.source_id for case in selected_cases if case.source_id not in source_index})
    if missing_sources:
        raise ValueError(f"missing source references: {', '.join(missing_sources)}")

    run_name = run_id or datetime.now(timezone.utc).strftime("attentional_v2_vs_iterator_v1_excerpt_comparison_%Y%m%d-%H%M%S")
    run_root = runs_root / run_name
    run_root.mkdir(parents=True, exist_ok=True)

    _json_dump(
        run_root / "dataset_manifest.json",
        {
            "target": DEFAULT_TARGET,
            "methods": DEFAULT_METHODS,
            "comparison_target": DEFAULT_COMPARISON_TARGET,
            "dataset_ids": [manifest["dataset_id"] for manifest in dataset_manifests],
            "selected_case_ids": selected_case_ids,
            "target_case_ids": target_case_ids,
            "source_manifest_paths": [str(path) for path in source_manifest_paths],
            "formal_manifest_path": str(formal_manifest_path),
            "judge_mode": judge_mode,
            "mechanism_execution_mode": mechanism_execution_mode,
            "judge_execution_mode": judge_execution_mode,
            "generated_at": _timestamp(),
        },
    )

    unit_index: dict[str, ChapterUnit] = {}
    cases_by_unit: dict[str, list[ExcerptCase]] = defaultdict(list)
    for case in selected_cases:
        unit_key = _chapter_unit_key(case.source_id, case.chapter_id)
        unit_index.setdefault(
            unit_key,
            ChapterUnit(
                source_id=case.source_id,
                chapter_id=case.chapter_id,
                output_language=case.output_language,
                book_title=case.book_title,
                author=case.author,
            ),
        )
        cases_by_unit[unit_key].append(case)
    units = [unit_index[key] for key in unit_index]

    per_worker_parallelism = 2 if mechanism_execution_mode == "parallel" else 1
    worker_policy = resolve_worker_policy(
        job_kind="excerpt_case_comparison",
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        task_count=len(units),
        per_worker_parallelism=per_worker_parallelism,
        explicit_max_workers=case_workers if case_workers and case_workers > 0 else None,
    )
    unit_runner = _run_unit_subprocess if worker_policy.worker_count > 1 else _run_chapter_unit

    unit_results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, worker_policy.worker_count), thread_name_prefix="excerpt-unit") as executor:
        future_to_unit: dict[Any, ChapterUnit] = {}
        for index, unit in enumerate(units, start=1):
            print(f"[submitted {index}/{len(units)}] {_unit_log_label(unit)}", flush=True)
            future = submit_inherited_context(
                executor,
                unit_runner,
                unit,
                source=source_index[unit.source_id],
                run_root=run_root,
                mechanism_execution_mode=mechanism_execution_mode,
            )
            future_to_unit[future] = unit
        for future in as_completed(future_to_unit):
            unit = future_to_unit[future]
            try:
                payload = future.result()
            except Exception as exc:
                payload = {
                    "unit_key": _chapter_unit_key(unit.source_id, unit.chapter_id),
                    "source_id": unit.source_id,
                    "chapter_id": unit.chapter_id,
                    "output_language": unit.output_language,
                    "book_title": unit.book_title,
                    "author": unit.author,
                    "mechanisms": {
                        mechanism_key: _mechanism_failure_payload(mechanism_key, error=str(exc))
                        for mechanism_key in MECHANISM_KEYS
                    },
                }
            unit_results[payload["unit_key"]] = payload
            _json_dump(run_root / "units" / f"{payload['unit_key']}.json", payload)
            print(f"[completed] {payload['unit_key']}", flush=True)

    provisioned_cache: dict[str, ProvisionedBook] = {}
    results_by_case_id: dict[str, dict[str, Any]] = {}
    for case in selected_cases:
        unit_key = _chapter_unit_key(case.source_id, case.chapter_id)
        if case.source_id not in provisioned_cache:
            provisioned_cache[case.source_id] = ensure_canonical_parse(
                ROOT / str(source_index[case.source_id]["relative_local_path"]),
                language_mode=case.output_language,
            )
        document = provisioned_cache[case.source_id].book_document
        if document is None:
            raise ValueError(f"missing provisioned book document for source: {case.source_id}")
        case_targets = [target_name for target_name, ids in target_case_ids.items() if case.case_id in ids]
        try:
            case_result = _evaluate_case(
                case,
                case_targets=case_targets,
                unit_result=unit_results[unit_key],
                document=document,
                run_root=run_root,
                judge_mode=judge_mode,
                judge_execution_mode=judge_execution_mode,
            )
        except Exception as exc:
            case_result = _case_failure_result(
                case,
                case_targets=case_targets,
                unit_result=unit_results[unit_key],
                error=f"{type(exc).__name__}: {exc}",
            )
        results_by_case_id[case.case_id] = case_result
        _json_dump(run_root / "cases" / f"{case.case_id}.json", case_result)

    case_results = [results_by_case_id[case.case_id] for case in selected_cases]
    target_names = list(target_case_ids.keys())
    aggregate = _aggregate(case_results, target_names=target_names)
    _json_dump(run_root / "summary" / "aggregate.json", aggregate)
    _jsonl_dump(run_root / "summary" / "case_results.jsonl", case_results)
    report_path = run_root / "summary" / "report.md"
    report_path.write_text(
        _build_markdown_report(
            run_id=run_name,
            selected_cases=selected_cases,
            target_case_ids=target_case_ids,
            aggregate=aggregate,
            datasets=dataset_manifests,
        ),
        encoding="utf-8",
    )
    return {
        "run_id": run_name,
        "run_root": str(run_root),
        "report_path": str(report_path),
        "aggregate": aggregate,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir",
        action="append",
        default=[],
        help="Excerpt dataset directory. Defaults to tracked EN/ZH curated v2 plus local EN/ZH reviewed v2.",
    )
    parser.add_argument(
        "--source-manifest",
        action="append",
        default=[],
        help="Source manifest path. Defaults to the tracked public benchmark pool plus private-library local refs.",
    )
    parser.add_argument("--formal-manifest", default=str(DEFAULT_FORMAL_MANIFEST))
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--target-slice", choices=TARGET_SLICE_VALUES, default="both")
    parser.add_argument("--judge-mode", choices=["llm", "none"], default="llm")
    parser.add_argument("--mechanism-execution-mode", choices=["serial", "parallel"], default="serial")
    parser.add_argument("--judge-execution-mode", choices=["serial", "parallel"], default="serial")
    parser.add_argument("--case-workers", type=int, default=0)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--case-ids", default="")
    parser.add_argument("--worker-payload", default="", help=argparse.SUPPRESS)
    parser.add_argument("--worker-result", default="", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.worker_payload:
        if not args.worker_result:
            raise ValueError("--worker-result is required when --worker-payload is set")
        return _run_payload_worker(Path(args.worker_payload).resolve(), Path(args.worker_result).resolve())
    dataset_dirs = [Path(item).resolve() for item in args.dataset_dir] if args.dataset_dir else list(DEFAULT_DATASET_DIRS)
    source_manifest_paths = [Path(item).resolve() for item in args.source_manifest] if args.source_manifest else list(DEFAULT_SOURCE_MANIFESTS)
    case_ids = [item.strip() for item in args.case_id if str(item).strip()]
    if args.case_ids:
        case_ids.extend([item.strip() for item in str(args.case_ids).split(",") if item.strip()])
    summary = run_benchmark(
        dataset_dirs=dataset_dirs,
        source_manifest_paths=source_manifest_paths,
        formal_manifest_path=Path(args.formal_manifest).resolve(),
        runs_root=Path(args.runs_root).resolve(),
        run_id=args.run_id or None,
        target_slice=args.target_slice,
        case_ids=case_ids or None,
        judge_mode=args.judge_mode,
        mechanism_execution_mode=args.mechanism_execution_mode,
        judge_execution_mode=args.judge_execution_mode,
        case_workers=args.case_workers or None,
    )
    print(json.dumps(summary["aggregate"], ensure_ascii=False, indent=2))
    print(f"run_root={summary['run_root']}")
    print(f"report_path={summary['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
