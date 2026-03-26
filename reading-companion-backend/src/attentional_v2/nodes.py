"""Phase 4 interpretive nodes for attentional_v2."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from src.iterator_reader.language import language_name
from src.iterator_reader.llm_utils import LLMTraceContext, invoke_json, llm_invocation_scope

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


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    """Normalize one free-text value."""

    return re.sub(r"\s+", " ", str(value or "")).strip()


def _json_block(value: object) -> str:
    """Render one prompt context block as stable JSON."""

    return json.dumps(value, ensure_ascii=False, indent=2)


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
    """Extract small deterministic cue packets for callback/distinction/pattern pressure."""

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
    return cues


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
    primary_anchor: str,
    related_anchors: list[str],
    state_snapshot: dict[str, object],
    output_language: str,
    output_dir: Path | None = None,
    suggested_reaction: ReactionCandidate | None = None,
) -> ReactionEmissionResult:
    """Run the reaction-emission gate."""

    prompts = ATTENTIONAL_V2_PROMPTS
    user_prompt = _render_prompt(
        prompts.reaction_emission_prompt,
        current_interpretation=current_interpretation,
        primary_anchor=primary_anchor,
        related_anchors=_json_block(related_anchors),
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
    output_language: str,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
    boundary_context: dict[str, object] | None = None,
) -> dict[str, object]:
    """Run the Phase 4 node handoff for one local reading moment."""

    local_context = current_span_sentences[:-1] if len(current_span_sentences) > 1 else []
    zoom_result: ZoomReadResult | None = None
    if str(trigger_state.get("output", "no_zoom")) == "zoom_now":
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
    merged_bridge_candidates = []
    zoom_bridge_candidate = (zoom_result or {}).get("bridge_candidate") if zoom_result else None
    if zoom_bridge_candidate:
        merged_bridge_candidates.append(zoom_bridge_candidate)
    merged_bridge_candidates.extend(closure_result.get("bridge_candidates", []))
    merged_bridge_candidates.extend(bridge_candidates)
    controller_result = controller_decision(
        working_pressure=working_pressure,
        closure_result=closure_result,
        bridge_candidates=merged_bridge_candidates,
        gate_state=str(trigger_state.get("gate_state", "quiet")),  # type: ignore[arg-type]
        reader_policy=reader_policy,
        output_dir=output_dir,
    )

    reaction_result: ReactionEmissionResult | None = None
    suggested_reaction = closure_result.get("reaction_candidate")
    should_consider_reaction = bool(suggested_reaction) or bool(zoom_result and zoom_result.get("consider_reaction_emission"))
    if should_consider_reaction:
        reaction_result = reaction_emission(
            current_interpretation=_clean_text(
                (zoom_result or {}).get("local_interpretation") or closure_result.get("meaning_unit_summary")
            ),
            primary_anchor=_clean_text(
                (suggested_reaction or {}).get("anchor_quote") or (zoom_result or {}).get("anchor_quote")
            ),
            related_anchors=list((suggested_reaction or {}).get("related_anchor_quotes", [])),
            state_snapshot={
                "trigger_output": str(trigger_state.get("output", "no_zoom")),
                "closure_decision": str(closure_result.get("closure_decision", "continue")),
                "chosen_move": str(controller_result.get("chosen_move", "advance")),
            },
            output_language=output_language,
            output_dir=output_dir,
            suggested_reaction=suggested_reaction,
        )

    return {
        "zoom_result": zoom_result,
        "closure_result": closure_result,
        "controller_result": controller_result,
        "reaction_result": reaction_result,
        "bridge_candidates": merged_bridge_candidates,
    }
