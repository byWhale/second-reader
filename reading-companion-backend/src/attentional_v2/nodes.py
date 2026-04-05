"""Phase 4 interpretive nodes for attentional_v2."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src.iterator_reader.language import language_name
from src.iterator_reader.llm_utils import LLMTraceContext, ReaderLLMError, invoke_json, llm_invocation_scope

from .prompts import ATTENTIONAL_V2_PROMPTS
from .schemas import (
    AnchorMemoryState,
    BridgeCandidate,
    ClosureDecision,
    ControllerDecisionResult,
    GateState,
    KnowledgeActivationsState,
    MeaningUnitClosureResult,
    MoveType,
    ReactionCandidate,
    ReactionEmissionDecision,
    ReactionEmissionResult,
    ReactionType,
    ReaderPolicy,
    StateOperation,
    TriggerState,
    WorkingPressureState,
    ZoomReadResult,
)
from .storage import prompt_manifest_file, save_json


_REACTION_TYPES: set[ReactionType] = {
    "highlight",
    "association",
    "curious",
    "discern",
    "retrospect",
    "silent",
}
_MOVE_TYPES: set[MoveType] = {"advance", "dwell", "bridge", "reframe"}
_STATE_OPERATION_TYPES = {
    "create",
    "update",
    "cool",
    "drop",
    "retain_anchor",
    "link_anchors",
    "promote",
    "supersede",
    "reactivate",
}
_CLOSURE_DECISIONS: set[ClosureDecision] = {"continue", "close"}
_EMISSION_DECISIONS: set[ReactionEmissionDecision] = {"emit", "withhold"}
_SYNTHETIC_REACTION_CUE_TYPES = {
    "marked_phrase",
    "loaded_wording",
    "analogy_image",
    "distinction_cue",
    "actor_intention",
    "social_pressure",
    "causal_stakes",
}
_CALLBACK_MARKERS = (
    "since that day",
    "from that day",
    "when they were young",
    "earlier",
    "previously",
    "remember",
    "recall",
    "當年",
    "当年",
    "自從",
    "自从",
    "那日",
    "先前",
    "從前",
    "从前",
    "記得",
    "记得",
)
_DISTINCTION_MARKERS = (
    "different",
    "differs",
    "instead",
    "rather than",
    "however",
    "in contrast",
    "不同",
    "大不同",
    "不是",
    "而是",
    "却",
    "卻",
)
_RECOGNITION_GAP_MARKERS = (
    "did not know",
    "didn't know",
    "could not tell",
    "不知道",
    "不知",
    "未識",
    "未识",
)
_DURABLE_PATTERN_MARKERS = (
    "again and again",
    "repeatedly",
    "always",
    "habitually",
    "換來換去",
    "换来换去",
    "無恆性",
    "无恆性",
    "无恒性",
    "心思太活",
    "不能按部就班",
)
_ACTOR_INTENTION_MARKERS = (
    "prepared to",
    "wished",
    "have often wished",
    "hope of securing",
    "decided to",
    "ready enough to",
    "came very near",
    "i often thought",
    "wanted the",
    "felt that he could not",
    "love society",
    "my business called me thither",
)
_SOCIAL_PRESSURE_MARKERS = (
    "preference of a majority",
    "majority of his patrons",
    "majority of their patrons",
    "protection of the law",
    "federal officials",
    "government",
    "master",
    "patrons",
    "o christian",
    "send me back",
    "not possible to do so much good in my position",
    "follow the beaten track",
)
_CAUSAL_STAKES_MARKERS = (
    "the result of this was",
    "went to the bad",
    "would be the one to suffer",
    "kept from doing so",
    "must come through",
    "single channel",
    "single choice",
    "permitted to",
    "debt",
    "obligation",
    "could not enjoy",
    "fulfilled his promise",
    "solid and never deceptive foundation",
    "send me back",
)
_ANALOGY_IMAGE_MARKERS = (
    "like",
    "as if",
    "as though",
    "像",
    "好像",
    "仿佛",
)
_LOADED_LOCAL_WORDING_MARKERS = (
    "bloodsucker",
    "bar-room",
    "delegate",
    "delegates",
    "tenant",
    "tenants",
    "paradox",
    "simple principle",
    "craze",
    "反寫的s",
    "反写的s",
)
_MARKED_PHRASE_RE = re.compile(r"[\"'“”‘’][^\"'“”‘’]{2,80}[\"'“”‘’]")


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    """Normalize one free-text value."""

    return re.sub(r"\s+", " ", str(value or "")).strip()


def _json_block(value: object) -> str:
    """Render one prompt context block as stable JSON."""

    return json.dumps(value, ensure_ascii=False, indent=2)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    """Return whether any deterministic marker appears in the normalized text."""

    return any(marker in text for marker in markers)


def _render_prompt(template: str, **replacements: str) -> str:
    """Render one prompt template without treating JSON braces as format fields."""

    rendered = template
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{key}}}", value)
    return rendered


def _structural_frame(
    *,
    book_title: str,
    author: str,
    chapter_title: str,
    output_language: str,
) -> dict[str, object]:
    """Build the shared structural frame for node prompts."""

    return {
        "book_title": book_title,
        "author": author,
        "chapter_title": chapter_title,
        "output_language": output_language,
    }


def _anchor_context(anchor_memory: AnchorMemoryState, *, limit: int = 4) -> list[dict[str, object]]:
    """Build a compact anchor context packet."""

    context: list[dict[str, object]] = []
    for anchor in anchor_memory.get("anchor_records", [])[:limit]:
        if not isinstance(anchor, dict):
            continue
        context.append(
            {
                "anchor_id": str(anchor.get("anchor_id", "") or ""),
                "quote": str(anchor.get("quote", "") or ""),
                "anchor_kind": str(anchor.get("anchor_kind", "") or ""),
                "status": str(anchor.get("status", "") or ""),
            }
        )
    return context


def _activation_context(activations: KnowledgeActivationsState, *, limit: int = 4) -> list[dict[str, object]]:
    """Build a compact activation context packet."""

    context: list[dict[str, object]] = []
    for activation in activations.get("activations", [])[:limit]:
        if not isinstance(activation, dict):
            continue
        context.append(
            {
                "activation_id": str(activation.get("activation_id", "") or ""),
                "source_candidate": str(activation.get("source_candidate", "") or ""),
                "reading_warrant": str(activation.get("reading_warrant", "") or ""),
                "status": str(activation.get("status", "") or ""),
            }
        )
    return context


def _local_textual_cues(
    current_span_sentences: list[dict[str, object]],
    *,
    limit: int = 6,
) -> list[dict[str, str]]:
    """Extract small deterministic cue packets for callback/distinction/pattern/micro-selectivity pressure."""

    cues: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for sentence in current_span_sentences:
        sentence_id = _clean_text(sentence.get("sentence_id"))
        text = _clean_text(sentence.get("text"))
        if not sentence_id or not text:
            continue
        lowered = text.lower()

        def add_cue(cue_type: str, reason: str) -> None:
            key = (sentence_id, cue_type)
            if key in seen or len(cues) >= limit:
                return
            seen.add(key)
            cues.append(
                {
                    "sentence_id": sentence_id,
                    "cue_type": cue_type,
                    "evidence": text[:180],
                    "reason": reason,
                }
            )

        if any(marker in lowered for marker in _CALLBACK_MARKERS):
            add_cue("callback_cue", "sentence contains an explicit backward-looking or prior-time marker")
        if any(marker in lowered for marker in _DISTINCTION_MARKERS):
            add_cue("distinction_cue", "sentence contains explicit contrast or difference language")
        if any(marker in lowered for marker in _RECOGNITION_GAP_MARKERS):
            add_cue("recognition_gap", "sentence contains an explicit failure-to-recognize cue")
        if any(marker in lowered for marker in _DURABLE_PATTERN_MARKERS):
            add_cue("durable_pattern", "sentence contains repeated-behavior or character-pattern evidence")
        if _contains_any(lowered, _ACTOR_INTENTION_MARKERS):
            add_cue("actor_intention", "sentence contains an explicit wish, motive, or stated intention")
        if _contains_any(lowered, _SOCIAL_PRESSURE_MARKERS):
            add_cue("social_pressure", "sentence contains approval, authority, or plea pressure from other people")
        if _contains_any(lowered, _CAUSAL_STAKES_MARKERS):
            add_cue("causal_stakes", "sentence contains concrete dependency, obligation, or consequence language")
        if any(marker in lowered for marker in _ANALOGY_IMAGE_MARKERS):
            add_cue("analogy_image", "sentence uses a compact analogy, comparison, or image-bearing turn")
        if _MARKED_PHRASE_RE.search(text):
            add_cue("marked_phrase", "sentence contains a marked phrase or quoted term that may deserve exact local attention")
        if any(marker in lowered for marker in _LOADED_LOCAL_WORDING_MARKERS):
            add_cue("loaded_wording", "sentence contains unusually loaded or locally sharp wording that may deserve exact phrase-level attention")
    return cues


def _cue_anchor_quote(local_textual_cues: list[dict[str, str]], *, focal_text: str) -> str:
    """Choose one bounded fallback anchor when local pressure is clear but zoom returned no compact phrase."""

    cleaned_focal = _clean_text(focal_text)
    if cleaned_focal and len(cleaned_focal) <= 180:
        return cleaned_focal
    for cue in local_textual_cues:
        if not isinstance(cue, dict):
            continue
        evidence = _clean_text(cue.get("evidence"))
        if evidence and len(evidence) <= 180:
            return evidence
    return cleaned_focal[:180]


def _has_compact_local_anchor(*, anchor_quote: str, focal_text: str) -> bool:
    """Return whether a phrase-level anchor is compact enough to justify a bounded extra emission check."""

    cleaned_anchor = _clean_text(anchor_quote)
    cleaned_focal = _clean_text(focal_text)
    if not cleaned_anchor or not cleaned_focal:
        return False
    if cleaned_anchor == cleaned_focal:
        return False
    if len(cleaned_anchor) >= len(cleaned_focal):
        return False
    return len(cleaned_anchor) <= max(18, int(len(cleaned_focal) * 0.75))


def _micro_selective_reaction_candidate(
    *,
    zoom_result: ZoomReadResult | None,
    closure_result: MeaningUnitClosureResult,
    local_textual_cues: list[dict[str, str]],
    focal_text: str,
) -> ReactionCandidate | None:
    """Build one bounded synthetic local reaction candidate when the phrase-level pressure is clear."""

    unresolved_pressure_note = _clean_text(closure_result.get("unresolved_pressure_note"))
    cue_types = {str(item.get("cue_type", "") or "") for item in local_textual_cues if isinstance(item, dict)}
    high_signal_cues = cue_types & _SYNTHETIC_REACTION_CUE_TYPES
    if not bool((zoom_result or {}).get("consider_reaction_emission")) or not high_signal_cues:
        return None
    anchor_quote = _clean_text((zoom_result or {}).get("anchor_quote"))
    if not anchor_quote:
        anchor_quote = _cue_anchor_quote(local_textual_cues, focal_text=focal_text)
    content = _clean_text((zoom_result or {}).get("local_interpretation")) or _clean_text(closure_result.get("meaning_unit_summary"))
    if not anchor_quote or not content:
        return None
    reaction_type: ReactionType = "highlight"
    if high_signal_cues & {"actor_intention", "social_pressure", "causal_stakes"}:
        reaction_type = "curious"
        content = (
            unresolved_pressure_note
            or _clean_text((zoom_result or {}).get("uncertainty_note"))
            or content
        )
    elif high_signal_cues & {"analogy_image", "marked_phrase", "loaded_wording", "distinction_cue"}:
        reaction_type = "discern"
    return {
        "type": reaction_type,
        "anchor_quote": anchor_quote,
        "content": content,
        "related_anchor_quotes": [],
        "search_query": "",
        "search_results": [],
    }


def _write_prompt_manifest(
    output_dir: Path | None,
    *,
    node_name: str,
    prompt_version: str,
    system_prompt: str,
    user_prompt: str,
    promptset_version: str,
) -> None:
    """Persist one node-level prompt manifest when an output directory is available."""

    if output_dir is None:
        return
    save_json(
        prompt_manifest_file(output_dir, node_name),
        {
            "node_name": node_name,
            "prompt_version": prompt_version,
            "promptset_version": promptset_version,
            "generated_at": _timestamp(),
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        },
    )


def _normalize_state_operations(value: object) -> list[StateOperation]:
    """Normalize a list of explicit state operations."""

    operations: list[StateOperation] = []
    if not isinstance(value, list):
        return operations
    for item in value:
        if not isinstance(item, dict):
            continue
        operation_type = _clean_text(item.get("operation_type")).lower().replace("-", "_")
        if operation_type not in _STATE_OPERATION_TYPES:
            continue
        payload = item.get("payload")
        operations.append(
            {
                "operation_type": operation_type,  # type: ignore[typeddict-item]
                "target_store": _clean_text(item.get("target_store")) or "working_pressure",
                "item_id": _clean_text(item.get("item_id")),
                "reason": _clean_text(item.get("reason")),
                "payload": dict(payload) if isinstance(payload, dict) else {},
            }
        )
    return operations


def _normalize_bridge_candidate(value: object) -> BridgeCandidate | None:
    """Normalize one optional bridge candidate."""

    if not isinstance(value, dict):
        return None
    target_anchor_id = _clean_text(value.get("target_anchor_id"))
    target_sentence_id = _clean_text(value.get("target_sentence_id"))
    quote = _clean_text(value.get("quote"))
    if not any([target_anchor_id, target_sentence_id, quote]):
        return None
    relation_type = _clean_text(value.get("relation_type")) or "echo"
    raw_score = value.get("score")
    try:
        score = float(raw_score) if raw_score is not None else 0.0
    except (TypeError, ValueError):
        score = 0.0
    return {
        "candidate_kind": _clean_text(value.get("candidate_kind")) or "llm_hint",
        "target_anchor_id": target_anchor_id,
        "target_sentence_id": target_sentence_id,
        "retrieval_channel": _clean_text(value.get("retrieval_channel")) or "llm_hint",
        "relation_type": relation_type,
        "score": score,
        "why_now": _clean_text(value.get("why_now")),
        "quote": quote,
    }


def _normalize_bridge_candidates(value: object) -> list[BridgeCandidate]:
    """Normalize a list of bridge candidates."""

    candidates: list[BridgeCandidate] = []
    if not isinstance(value, list):
        return candidates
    for item in value:
        candidate = _normalize_bridge_candidate(item)
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _normalize_reaction_candidate(value: object) -> ReactionCandidate | None:
    """Normalize one optional anchored reaction payload."""

    if not isinstance(value, dict):
        return None
    reaction_type = _clean_text(value.get("type")).lower()
    if reaction_type not in _REACTION_TYPES:
        return None
    anchor_quote = _clean_text(value.get("anchor_quote"))
    content = _clean_text(value.get("content"))
    if reaction_type != "silent" and (not anchor_quote or not content):
        return None
    related_anchor_quotes = [
        _clean_text(item)
        for item in value.get("related_anchor_quotes", [])
        if _clean_text(item)
    ] if isinstance(value.get("related_anchor_quotes"), list) else []
    search_results = [dict(item) for item in value.get("search_results", []) if isinstance(item, dict)] if isinstance(value.get("search_results"), list) else []
    return {
        "type": reaction_type,  # type: ignore[typeddict-item]
        "anchor_quote": anchor_quote,
        "content": content,
        "related_anchor_quotes": related_anchor_quotes,
        "search_query": _clean_text(value.get("search_query")),
        "search_results": search_results,
    }


def _has_reframe_pressure(working_pressure: WorkingPressureState) -> bool:
    """Return whether the current pressure snapshot is explicitly asking for a reframe."""

    return bool(working_pressure.get("pressure_snapshot", {}).get("reframe_pressure_present"))


def _controller_fast_path_result(
    closure_result: MeaningUnitClosureResult,
) -> ControllerDecisionResult | None:
    """Return a deterministic controller outcome when the local move is unambiguous."""

    dominant_move = str(closure_result.get("dominant_move", "advance") or "advance")
    if dominant_move != "advance":
        return None
    return {
        "chosen_move": "advance",
        "reason": "controller_fast_path",
        "target_anchor_id": "",
        "target_sentence_id": "",
    }


def _bridge_pressure_present(
    *,
    boundary_context: dict[str, object] | None,
    zoom_result: ZoomReadResult | None,
    closure_result: MeaningUnitClosureResult,
) -> bool:
    """Return whether the current local moment warrants deterministic bridge retrieval."""

    callback_anchor_ids = [
        _clean_text(item)
        for item in (boundary_context or {}).get("callback_anchor_ids", [])
        if _clean_text(item)
    ] if isinstance((boundary_context or {}).get("callback_anchor_ids"), list) else []
    return any(
        (
            bool(callback_anchor_ids),
            bool((zoom_result or {}).get("bridge_candidate")),
            bool(closure_result.get("bridge_candidates")),
            str(closure_result.get("dominant_move", "") or "") == "bridge",
        )
    )


def zoom_read(
    *,
    focal_sentence: dict[str, object],
    local_context_sentences: list[dict[str, object]],
    working_pressure: WorkingPressureState,
    anchor_memory: AnchorMemoryState,
    knowledge_activations: KnowledgeActivationsState,
    reader_policy: ReaderPolicy,
    output_language: str,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
) -> ZoomReadResult:
    """Run the sentence-level zoom node."""

    prompts = ATTENTIONAL_V2_PROMPTS
    focal_text = _clean_text(focal_sentence.get("text"))
    local_textual_cues = _local_textual_cues([*local_context_sentences, focal_sentence])
    structural_frame = _structural_frame(
        book_title=book_title,
        author=author,
        chapter_title=chapter_title,
        output_language=output_language,
    )
    user_prompt = _render_prompt(
        prompts.zoom_read_prompt,
        structural_frame=_json_block(structural_frame),
        focal_sentence=_json_block(
            {
                "sentence_id": _clean_text(focal_sentence.get("sentence_id")),
                "text": focal_text,
                "text_role": _clean_text(focal_sentence.get("text_role")),
            }
        ),
        local_context=_json_block(
            [
                {
                    "sentence_id": _clean_text(sentence.get("sentence_id")),
                    "text": _clean_text(sentence.get("text")),
                    "text_role": _clean_text(sentence.get("text_role")),
                }
                for sentence in local_context_sentences
            ]
        ),
        working_pressure=_json_block(working_pressure),
        anchor_context=_json_block(_anchor_context(anchor_memory)),
        activation_context=_json_block(_activation_context(knowledge_activations)),
        local_textual_cues=_json_block(local_textual_cues),
        policy_snapshot=_json_block(reader_policy),
        output_language_name=language_name(output_language),
    )
    _write_prompt_manifest(
        output_dir,
        node_name="zoom_read",
        prompt_version=prompts.zoom_read_version,
        system_prompt=prompts.zoom_read_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )
    with llm_invocation_scope(trace_context=LLMTraceContext(stage="phase4", node="zoom_read")):
        payload = invoke_json(prompts.zoom_read_system, user_prompt, default={})
    anchor_quote = _clean_text(payload.get("anchor_quote")) if isinstance(payload, dict) else ""
    if anchor_quote and anchor_quote not in focal_text:
        anchor_quote = ""
    bridge_candidate = _normalize_bridge_candidate(payload.get("bridge_candidate")) if isinstance(payload, dict) else None
    return {
        "local_interpretation": _clean_text(payload.get("local_interpretation")) if isinstance(payload, dict) else "",
        "anchor_quote": anchor_quote,
        "pressure_updates": _normalize_state_operations(payload.get("pressure_updates")) if isinstance(payload, dict) else [],
        "activation_updates": _normalize_state_operations(payload.get("activation_updates")) if isinstance(payload, dict) else [],
        "bridge_candidate": bridge_candidate,
        "consider_reaction_emission": bool(payload.get("consider_reaction_emission")) if isinstance(payload, dict) else False,
        "uncertainty_note": _clean_text(payload.get("uncertainty_note")) if isinstance(payload, dict) else "",
    }


def meaning_unit_closure(
    *,
    current_span_sentences: list[dict[str, object]],
    working_pressure: WorkingPressureState,
    anchor_memory: AnchorMemoryState,
    knowledge_activations: KnowledgeActivationsState,
    boundary_context: dict[str, object] | None,
    reader_policy: ReaderPolicy,
    output_language: str,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
    zoom_result: ZoomReadResult | None = None,
) -> MeaningUnitClosureResult:
    """Run the meaning-unit closure node."""

    prompts = ATTENTIONAL_V2_PROMPTS
    structural_frame = _structural_frame(
        book_title=book_title,
        author=author,
        chapter_title=chapter_title,
        output_language=output_language,
    )
    current_span = [
        {
            "sentence_id": _clean_text(sentence.get("sentence_id")),
            "text": _clean_text(sentence.get("text")),
            "text_role": _clean_text(sentence.get("text_role")),
        }
        for sentence in current_span_sentences
    ]
    local_textual_cues = _local_textual_cues(current_span_sentences)
    user_prompt = _render_prompt(
        prompts.meaning_unit_closure_prompt,
        structural_frame=_json_block(structural_frame),
        current_span=_json_block(current_span),
        boundary_context=_json_block(dict(boundary_context or {})),
        working_pressure=_json_block(working_pressure),
        anchor_context=_json_block(_anchor_context(anchor_memory)),
        activation_context=_json_block(_activation_context(knowledge_activations)),
        local_textual_cues=_json_block(local_textual_cues),
        zoom_result=_json_block(dict(zoom_result or {})),
        policy_snapshot=_json_block(reader_policy),
        output_language_name=language_name(output_language),
    )
    _write_prompt_manifest(
        output_dir,
        node_name="meaning_unit_closure",
        prompt_version=prompts.meaning_unit_closure_version,
        system_prompt=prompts.meaning_unit_closure_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )
    with llm_invocation_scope(
        trace_context=LLMTraceContext(stage="phase4", node="meaning_unit_closure")
    ):
        payload = invoke_json(prompts.meaning_unit_closure_system, user_prompt, default={})
    closure_decision = _clean_text(payload.get("closure_decision")).lower() if isinstance(payload, dict) else ""
    if closure_decision not in _CLOSURE_DECISIONS:
        closure_decision = "continue"
    dominant_move = _clean_text(payload.get("dominant_move")).lower().replace("-", "_") if isinstance(payload, dict) else ""
    if dominant_move not in _MOVE_TYPES:
        dominant_move = "advance"
    return {
        "closure_decision": closure_decision,  # type: ignore[typeddict-item]
        "meaning_unit_summary": _clean_text(payload.get("meaning_unit_summary")) if isinstance(payload, dict) else "",
        "dominant_move": dominant_move,  # type: ignore[typeddict-item]
        "proposed_state_operations": _normalize_state_operations(payload.get("proposed_state_operations")) if isinstance(payload, dict) else [],
        "bridge_candidates": _normalize_bridge_candidates(payload.get("bridge_candidates")) if isinstance(payload, dict) else [],
        "reaction_candidate": _normalize_reaction_candidate(payload.get("reaction_candidate")) if isinstance(payload, dict) else None,
        "unresolved_pressure_note": _clean_text(payload.get("unresolved_pressure_note")) if isinstance(payload, dict) else "",
    }


def controller_decision(
    *,
    working_pressure: WorkingPressureState,
    closure_result: MeaningUnitClosureResult,
    bridge_candidates: list[BridgeCandidate],
    gate_state: GateState,
    reader_policy: ReaderPolicy,
    output_dir: Path | None = None,
) -> ControllerDecisionResult:
    """Run the controller decision node with guardrails."""

    fast_path = None
    if not bridge_candidates and not _has_reframe_pressure(working_pressure):
        fast_path = _controller_fast_path_result(closure_result)
    if fast_path is not None:
        return fast_path

    prompts = ATTENTIONAL_V2_PROMPTS
    user_prompt = _render_prompt(
        prompts.controller_decision_prompt,
        working_pressure=_json_block(working_pressure),
        closure_result=_json_block(closure_result),
        bridge_candidates=_json_block(bridge_candidates),
        gate_state=gate_state,
        policy_snapshot=_json_block(reader_policy),
    )
    _write_prompt_manifest(
        output_dir,
        node_name="controller_decision",
        prompt_version=prompts.controller_decision_version,
        system_prompt=prompts.controller_decision_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )
    with llm_invocation_scope(
        trace_context=LLMTraceContext(stage="phase4", node="controller_decision")
    ):
        payload = invoke_json(prompts.controller_decision_system, user_prompt, default={})
    chosen_move = _clean_text(payload.get("chosen_move")).lower().replace("-", "_") if isinstance(payload, dict) else ""
    if chosen_move not in _MOVE_TYPES:
        chosen_move = str(closure_result.get("dominant_move", "advance"))
    target_anchor_id = _clean_text(payload.get("target_anchor_id")) if isinstance(payload, dict) else ""
    target_sentence_id = _clean_text(payload.get("target_sentence_id")) if isinstance(payload, dict) else ""

    if chosen_move == "bridge":
        if not bridge_candidates:
            chosen_move = str(reader_policy.get("controller", {}).get("default_move", "advance"))
            target_anchor_id = ""
            target_sentence_id = ""
        elif not target_anchor_id and not target_sentence_id:
            primary = bridge_candidates[0]
            target_anchor_id = _clean_text(primary.get("target_anchor_id"))
            target_sentence_id = _clean_text(primary.get("target_sentence_id"))

    if chosen_move == "reframe" and not bool(working_pressure.get("pressure_snapshot", {}).get("reframe_pressure_present")):
        chosen_move = str(closure_result.get("dominant_move", "advance"))
        target_anchor_id = ""
        target_sentence_id = ""

    return {
        "chosen_move": chosen_move,  # type: ignore[typeddict-item]
        "reason": _clean_text(payload.get("reason")) if isinstance(payload, dict) else "",
        "target_anchor_id": target_anchor_id,
        "target_sentence_id": target_sentence_id,
    }


def reaction_emission(
    *,
    current_interpretation: str,
    focal_sentence: str,
    primary_anchor: str,
    related_anchors: list[str],
    suggested_reaction: ReactionCandidate | None,
    local_textual_cues: list[dict[str, str]],
    state_snapshot: dict[str, object],
    output_language: str,
    output_dir: Path | None = None,
) -> ReactionEmissionResult:
    """Run the reaction-emission gate."""

    prompts = ATTENTIONAL_V2_PROMPTS
    user_prompt = _render_prompt(
        prompts.reaction_emission_prompt,
        current_interpretation=current_interpretation,
        focal_sentence=focal_sentence,
        primary_anchor=primary_anchor,
        related_anchors=_json_block(related_anchors),
        suggested_reaction=_json_block(dict(suggested_reaction or {})),
        local_textual_cues=_json_block(local_textual_cues),
        state_snapshot=_json_block(state_snapshot),
        output_language_name=language_name(output_language),
    )
    _write_prompt_manifest(
        output_dir,
        node_name="reaction_emission",
        prompt_version=prompts.reaction_emission_version,
        system_prompt=prompts.reaction_emission_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )
    with llm_invocation_scope(
        trace_context=LLMTraceContext(stage="phase4", node="reaction_emission")
    ):
        payload = invoke_json(prompts.reaction_emission_system, user_prompt, default={})
    decision = _clean_text(payload.get("decision")).lower() if isinstance(payload, dict) else ""
    if decision not in _EMISSION_DECISIONS:
        decision = "withhold"
    reaction = _normalize_reaction_candidate(payload.get("reaction")) if isinstance(payload, dict) else None
    if reaction is None and suggested_reaction is not None:
        reaction = suggested_reaction
    if decision == "emit" and reaction is None:
        decision = "withhold"
    if reaction is not None and not reaction.get("anchor_quote"):
        decision = "withhold"
        reaction = None
    return {
        "decision": decision,  # type: ignore[typeddict-item]
        "reason": _clean_text(payload.get("reason")) if isinstance(payload, dict) else "",
        "reaction": reaction,
    }


def run_phase4_local_cycle(
    *,
    focal_sentence: dict[str, object],
    current_span_sentences: list[dict[str, object]],
    trigger_state: TriggerState,
    working_pressure: WorkingPressureState,
    anchor_memory: AnchorMemoryState,
    knowledge_activations: KnowledgeActivationsState,
    reader_policy: ReaderPolicy,
    bridge_candidates: list[BridgeCandidate],
    lazy_bridge_loader: Callable[[], tuple[dict[str, object], list[BridgeCandidate]]] | None = None,
    output_language: str,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
    boundary_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Run one local interpretive cycle for one reading moment.

    `phase4` in the helper name is a historical implementation-stage label.
    The live runtime concept here is the local interpretive loop:
    `zoom_read -> meaning_unit_closure -> controller_decision -> optional reaction_emission`.
    """

    local_context = current_span_sentences[:-1] if len(current_span_sentences) > 1 else []
    zoom_result: ZoomReadResult | None = None
    candidate_set: dict[str, object] | None = None
    llm_fallbacks: list[dict[str, str]] = []
    if str(trigger_state.get("output", "no_zoom")) == "zoom_now":
        try:
            zoom_result = zoom_read(
                focal_sentence=focal_sentence,
                local_context_sentences=local_context,
                working_pressure=working_pressure,
                anchor_memory=anchor_memory,
                knowledge_activations=knowledge_activations,
                reader_policy=reader_policy,
                output_language=output_language,
                output_dir=output_dir,
                book_title=book_title,
                author=author,
                chapter_title=chapter_title,
            )
        except ReaderLLMError as exc:
            llm_fallbacks.append({"node": "zoom_read", "problem_code": exc.problem_code})
            zoom_result = None

    try:
        closure_result = meaning_unit_closure(
            current_span_sentences=current_span_sentences,
            working_pressure=working_pressure,
            anchor_memory=anchor_memory,
            knowledge_activations=knowledge_activations,
            boundary_context=boundary_context,
            reader_policy=reader_policy,
            output_language=output_language,
            output_dir=output_dir,
            book_title=book_title,
            author=author,
            chapter_title=chapter_title,
            zoom_result=zoom_result,
        )
    except ReaderLLMError as exc:
        llm_fallbacks.append({"node": "meaning_unit_closure", "problem_code": exc.problem_code})
        closure_result = {
            "closure_decision": "continue",
            "meaning_unit_summary": "",
            "dominant_move": "advance",
            "proposed_state_operations": [],
            "bridge_candidates": [],
            "reaction_candidate": None,
            "unresolved_pressure_note": "meaning_unit_closure_unavailable",
        }
    lazy_bridge_candidates: list[BridgeCandidate] = []
    if _bridge_pressure_present(
        boundary_context=boundary_context,
        zoom_result=zoom_result,
        closure_result=closure_result,
    ) and lazy_bridge_loader is not None:
        candidate_set, lazy_bridge_candidates = lazy_bridge_loader()
    merged_bridge_candidates = []
    zoom_bridge_candidate = (zoom_result or {}).get("bridge_candidate") if zoom_result else None
    if zoom_bridge_candidate:
        merged_bridge_candidates.append(zoom_bridge_candidate)
    merged_bridge_candidates.extend(closure_result.get("bridge_candidates", []))
    merged_bridge_candidates.extend(bridge_candidates)
    merged_bridge_candidates.extend(lazy_bridge_candidates)
    try:
        controller_result = controller_decision(
            working_pressure=working_pressure,
            closure_result=closure_result,
            bridge_candidates=merged_bridge_candidates,
            gate_state=str(trigger_state.get("gate_state", "quiet")),  # type: ignore[arg-type]
            reader_policy=reader_policy,
            output_dir=output_dir,
        )
    except ReaderLLMError as exc:
        llm_fallbacks.append({"node": "controller_decision", "problem_code": exc.problem_code})
        controller_result = {
            "chosen_move": str(closure_result.get("dominant_move", "advance")) or "advance",
            "reason": "controller_unavailable",
            "target_anchor_id": "",
            "target_sentence_id": "",
        }
    if _clean_text(controller_result.get("chosen_move")) == "bridge" and candidate_set is None and lazy_bridge_loader is not None:
        candidate_set, lazy_bridge_candidates = lazy_bridge_loader()
        for candidate in lazy_bridge_candidates:
            if candidate not in merged_bridge_candidates:
                merged_bridge_candidates.append(candidate)

    reaction_result: ReactionEmissionResult | None = None
    suggested_reaction = closure_result.get("reaction_candidate")
    compact_local_anchor = bool(
        zoom_result
        and len(current_span_sentences) <= 2
        and _has_compact_local_anchor(
            anchor_quote=_clean_text((zoom_result or {}).get("anchor_quote")),
            focal_text=_clean_text(focal_sentence.get("text")),
        )
    )
    reaction_local_cues = _local_textual_cues(current_span_sentences)
    effective_suggested_reaction = suggested_reaction or _micro_selective_reaction_candidate(
        zoom_result=zoom_result,
        closure_result=closure_result,
        local_textual_cues=reaction_local_cues,
        focal_text=_clean_text(focal_sentence.get("text")),
    )
    should_consider_reaction = (
        bool(suggested_reaction)
        or bool(
            zoom_result
            and zoom_result.get("consider_reaction_emission")
            and effective_suggested_reaction
        )
    )
    if should_consider_reaction:
        try:
            reaction_result = reaction_emission(
                current_interpretation=_clean_text(
                    (zoom_result or {}).get("local_interpretation") or closure_result.get("meaning_unit_summary")
                ),
                focal_sentence=_clean_text(focal_sentence.get("text")),
                primary_anchor=_clean_text(
                    (effective_suggested_reaction or {}).get("anchor_quote") or (zoom_result or {}).get("anchor_quote")
                ),
                related_anchors=list((effective_suggested_reaction or {}).get("related_anchor_quotes", [])),
                suggested_reaction=effective_suggested_reaction,
                local_textual_cues=reaction_local_cues,
                state_snapshot={
                    "trigger_output": str(trigger_state.get("output", "no_zoom")),
                    "closure_decision": str(closure_result.get("closure_decision", "continue")),
                    "chosen_move": str(controller_result.get("chosen_move", "advance")),
                    "compact_local_anchor": compact_local_anchor,
                    "synthetic_local_candidate": bool(effective_suggested_reaction and not suggested_reaction),
                },
                output_language=output_language,
                output_dir=output_dir,
            )
        except ReaderLLMError as exc:
            llm_fallbacks.append({"node": "reaction_emission", "problem_code": exc.problem_code})
            reaction_result = {
                "decision": "withhold",
                "reason": "reaction_emission_unavailable",
                "reaction": None,
            }

    return {
        "zoom_result": zoom_result,
        "closure_result": closure_result,
        "controller_result": controller_result,
        "reaction_result": reaction_result,
        "bridge_candidates": merged_bridge_candidates,
        "candidate_set": candidate_set,
        "llm_fallbacks": llm_fallbacks,
    }
