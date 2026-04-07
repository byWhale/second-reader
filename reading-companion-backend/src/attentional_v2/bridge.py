"""Phase 5 bridge judgment and durable anchor-memory helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.iterator_reader.language import language_name
from src.iterator_reader.llm_utils import LLMTraceContext, invoke_json, llm_invocation_scope

from .knowledge import (
    apply_activation_operations,
    resolve_search_policy_mode,
    set_knowledge_use_mode,
    set_search_policy_mode,
)
from .nodes import (
    _activation_context,
    _anchor_context,
    _clean_text,
    _json_block,
    _normalize_bridge_candidate,
    _normalize_bridge_candidates,
    _normalize_state_operations,
    _render_prompt,
    _structural_frame,
    _write_prompt_manifest,
)
from .prompts import ATTENTIONAL_V2_PROMPTS
from .schemas import (
    AnchorMemoryState,
    AnchorRecord,
    AnchorRelation,
    BridgeAttribution,
    BridgeCandidate,
    BridgeResolutionResult,
    KnowledgeActivationsState,
    MoveHistoryState,
    ReaderPolicy,
    WorkingPressureState,
)
from .state_ops import (
    append_anchor_relation,
    append_move,
    apply_working_pressure_operations,
    upsert_anchor_record,
)

_ANCHOR_RELATION_TYPES = {
    "echo",
    "contrast",
    "cause",
    "support",
    "question_opened_by",
    "question_resolved_by",
    "callback",
}
_GENERIC_BRIDGE_MARKERS = (
    "earlier in the chapter",
    "earlier in this chapter",
    "earlier theme",
    "chapter theme",
    "chapter-level",
    "generic callback",
    "earlier point",
    "earlier idea",
    "本章",
    "前文主题",
    "结构",
    "章节层面",
    "泛泛",
    "大意",
)


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def derive_anchor_id(sentence_start_id: str, sentence_end_id: str | None = None) -> str:
    """Build a deterministic anchor id from a sentence span."""

    start_id = _clean_text(sentence_start_id)
    end_id = _clean_text(sentence_end_id) or start_id
    return f"anchor:{start_id}:{end_id}"


def build_anchor_record(
    *,
    sentence_start_id: str,
    sentence_end_id: str | None = None,
    quote: str,
    locator: dict[str, object] | None = None,
    anchor_kind: str,
    why_it_mattered: str,
    status: str = "active",
    anchor_id: str | None = None,
    linked_reaction_ids: list[str] | None = None,
    linked_activation_ids: list[str] | None = None,
) -> AnchorRecord:
    """Build one retained source anchor."""

    clean_start = _clean_text(sentence_start_id)
    clean_end = _clean_text(sentence_end_id) or clean_start
    return {
        "anchor_id": anchor_id or derive_anchor_id(clean_start, clean_end),
        "sentence_start_id": clean_start,
        "sentence_end_id": clean_end,
        "quote": _clean_text(quote),
        "locator": dict(locator or {}),
        "anchor_kind": _clean_text(anchor_kind) or "bridge_target",
        "why_it_mattered": _clean_text(why_it_mattered),
        "status": _clean_text(status) or "active",
        "linked_reaction_ids": list(linked_reaction_ids or []),
        "linked_activation_ids": list(linked_activation_ids or []),
    }


def candidate_pool_for_bridge_resolution(
    candidate_set: dict[str, object],
    *,
    max_supporting_candidates: int = 2,
) -> list[BridgeCandidate]:
    """Normalize the deterministic retrieval result into a bridge-judgment pool."""

    pool: list[BridgeCandidate] = []
    for candidate in candidate_set.get("memory_candidates", []):
        if not isinstance(candidate, dict):
            continue
        pool.append(
            {
                "candidate_kind": "anchor_memory",
                "target_anchor_id": _clean_text(candidate.get("anchor_id")),
                "target_sentence_id": _clean_text(candidate.get("sentence_end_id") or candidate.get("sentence_start_id")),
                "retrieval_channel": "anchor_memory",
                "relation_type": "echo",
                "score": float(candidate.get("overlap_score", 0) or 0.0),
                "why_now": "",
                "quote": _clean_text(candidate.get("quote")),
            }
        )
    for candidate in candidate_set.get("lookback_candidates", []):
        if not isinstance(candidate, dict):
            continue
        pool.append(
            {
                "candidate_kind": _clean_text(candidate.get("candidate_kind")) or "source_lookback",
                "target_anchor_id": "",
                "target_sentence_id": _clean_text(candidate.get("sentence_id")),
                "retrieval_channel": _clean_text(candidate.get("retrieval_channel")) or "source_lookback",
                "relation_type": _clean_text(candidate.get("relation_type")) or "echo",
                "score": float(candidate.get("overlap_score", 0) or 0.0),
                "why_now": "",
                "quote": _clean_text(candidate.get("text")),
                "locator": dict(candidate.get("locator", {})) if isinstance(candidate.get("locator"), dict) else {},
            }
        )
    pool.sort(
        key=lambda candidate: (
            -float(candidate.get("score", 0.0) or 0.0),
            _clean_text(candidate.get("target_anchor_id")),
            _clean_text(candidate.get("target_sentence_id")),
        )
    )
    return pool[: max(1, int(max_supporting_candidates) + 1)]


def _bridge_candidates_match(left: BridgeCandidate, right: BridgeCandidate) -> bool:
    """Decide whether two bridge candidates identify the same source target."""

    left_anchor = _clean_text(left.get("target_anchor_id"))
    right_anchor = _clean_text(right.get("target_anchor_id"))
    if left_anchor and right_anchor and left_anchor == right_anchor:
        return True
    left_sentence = _clean_text(left.get("target_sentence_id"))
    right_sentence = _clean_text(right.get("target_sentence_id"))
    if left_sentence and right_sentence and left_sentence == right_sentence:
        return True
    left_quote = _clean_text(left.get("quote"))
    right_quote = _clean_text(right.get("quote"))
    return bool(left_quote and right_quote and left_quote == right_quote)


def _select_candidate(
    requested: BridgeCandidate | None,
    candidate_pool: list[BridgeCandidate],
) -> BridgeCandidate | None:
    """Resolve one LLM-requested bridge target against the deterministic pool."""

    if requested is None:
        return None
    for candidate in candidate_pool:
        if _bridge_candidates_match(requested, candidate):
            relation_type = _clean_text(requested.get("relation_type")) or str(candidate.get("relation_type", "echo"))
            if relation_type not in _ANCHOR_RELATION_TYPES:
                relation_type = "echo"
            return {
                **candidate,
                "relation_type": relation_type,
                "why_now": _clean_text(requested.get("why_now")) or str(candidate.get("why_now", "") or ""),
            }
    return None


def _normalize_bridge_attribution(value: object) -> BridgeAttribution | None:
    """Normalize one explicit bridge-attribution packet."""

    if not isinstance(value, dict):
        return None
    target_quote = _clean_text(value.get("target_quote"))
    current_quote = _clean_text(value.get("current_quote"))
    relation_explanation = _clean_text(value.get("relation_explanation"))
    if not any((target_quote, current_quote, relation_explanation)):
        return None
    return {
        "target_quote": target_quote,
        "current_quote": current_quote,
        "relation_explanation": relation_explanation,
    }


def _quotes_align(left: str, right: str) -> bool:
    """Return whether two compact quotes clearly refer to the same textual target."""

    clean_left = _clean_text(left)
    clean_right = _clean_text(right)
    if not clean_left or not clean_right:
        return False
    return clean_left in clean_right or clean_right in clean_left


def _current_quote_is_grounded(
    *,
    current_quote: str,
    current_span_sentences: list[dict[str, object]],
) -> bool:
    """Return whether one claimed current quote actually appears in the current local span."""

    clean_current = _clean_text(current_quote)
    if not clean_current:
        return False
    return any(clean_current in _clean_text(sentence.get("text")) for sentence in current_span_sentences)


def _bridge_attribution_is_specific(
    attribution: BridgeAttribution | None,
    *,
    primary_bridge: BridgeCandidate | None,
    current_span_sentences: list[dict[str, object]],
) -> bool:
    """Return whether the bridge explanation names a concrete earlier target and local relation."""

    if attribution is None or primary_bridge is None:
        return False
    target_quote = _clean_text(attribution.get("target_quote"))
    current_quote = _clean_text(attribution.get("current_quote"))
    relation_explanation = _clean_text(attribution.get("relation_explanation"))
    if not target_quote or not current_quote or len(relation_explanation) < 10:
        return False
    if any(marker in relation_explanation.lower() for marker in _GENERIC_BRIDGE_MARKERS):
        return False
    candidate_quote = _clean_text(primary_bridge.get("quote"))
    if candidate_quote and not _quotes_align(target_quote, candidate_quote):
        return False
    if not _current_quote_is_grounded(current_quote=current_quote, current_span_sentences=current_span_sentences):
        return False
    return True


def _materialize_bridge_target(
    state: AnchorMemoryState,
    candidate: BridgeCandidate,
    *,
    linked_activation_ids: list[str] | None = None,
) -> tuple[AnchorMemoryState, BridgeCandidate]:
    """Ensure a bridge target has an anchor id before relation writes."""

    target_anchor_id = _clean_text(candidate.get("target_anchor_id"))
    if target_anchor_id:
        return state, candidate

    sentence_id = _clean_text(candidate.get("target_sentence_id"))
    if not sentence_id:
        return state, candidate
    anchor_record = build_anchor_record(
        sentence_start_id=sentence_id,
        sentence_end_id=sentence_id,
        quote=_clean_text(candidate.get("quote")),
        locator=dict(candidate.get("locator", {})) if isinstance(candidate.get("locator"), dict) else {},
        anchor_kind="bridge_target",
        why_it_mattered=_clean_text(candidate.get("why_now")) or "selected during bridge resolution",
        linked_activation_ids=linked_activation_ids,
    )
    next_state = upsert_anchor_record(state, anchor_record)
    return next_state, {
        **candidate,
        "target_anchor_id": str(anchor_record.get("anchor_id", "") or ""),
    }


def index_anchor_memory(
    state: AnchorMemoryState,
    *,
    anchor_id: str,
    motif_keys: list[str] | None = None,
    unresolved_reference_keys: list[str] | None = None,
    trace_targets: list[str] | None = None,
) -> AnchorMemoryState:
    """Update motif, unresolved-reference, and trace indexes for one anchor."""

    next_state = dict(state)
    touched = False

    if motif_keys:
        motif_index = {str(key): list(value) for key, value in state.get("motif_index", {}).items()}
        for key in motif_keys:
            clean_key = _clean_text(key).lower()
            if not clean_key:
                continue
            ids = [*motif_index.get(clean_key, [])]
            if anchor_id not in ids:
                ids.append(anchor_id)
            motif_index[clean_key] = ids
            touched = True
        next_state["motif_index"] = motif_index

    if unresolved_reference_keys:
        unresolved_index = {
            str(key): list(value)
            for key, value in state.get("unresolved_reference_index", {}).items()
        }
        for key in unresolved_reference_keys:
            clean_key = _clean_text(key).lower()
            if not clean_key:
                continue
            ids = [*unresolved_index.get(clean_key, [])]
            if anchor_id not in ids:
                ids.append(anchor_id)
            unresolved_index[clean_key] = ids
            touched = True
        next_state["unresolved_reference_index"] = unresolved_index

    if trace_targets:
        trace_links = {str(key): list(value) for key, value in state.get("trace_links", {}).items()}
        linked = [*trace_links.get(anchor_id, [])]
        for target in trace_targets:
            clean_target = _clean_text(target)
            if clean_target and clean_target not in linked:
                linked.append(clean_target)
                touched = True
        trace_links[anchor_id] = linked
        next_state["trace_links"] = trace_links

    if not touched:
        return state

    next_state["updated_at"] = _timestamp()
    return next_state  # type: ignore[return-value]


def bridge_resolution(
    *,
    current_span_sentences: list[dict[str, object]],
    candidate_set: dict[str, object],
    working_pressure: WorkingPressureState,
    anchor_memory: AnchorMemoryState,
    knowledge_activations: KnowledgeActivationsState,
    reader_policy: ReaderPolicy,
    output_language: str,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
) -> BridgeResolutionResult:
    """Run bridge judgment over a deterministic candidate set."""

    prompts = ATTENTIONAL_V2_PROMPTS
    candidate_pool = candidate_pool_for_bridge_resolution(
        candidate_set,
        max_supporting_candidates=int(reader_policy.get("bridge", {}).get("max_supporting_candidates", 2) or 2),
    )
    if not candidate_pool:
        return {
            "decision": "decline",
            "reason": "No deterministic source candidates are available.",
            "primary_bridge": None,
            "primary_attribution": None,
            "supporting_bridges": [],
            "activation_updates": [],
            "state_operations": [],
            "knowledge_use_mode": str(knowledge_activations.get("knowledge_use_mode", "book_grounded_only")),  # type: ignore[typeddict-item]
            "search_policy_mode": "no_search",
            "search_trigger": "none",
            "search_query": "",
        }

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
    user_prompt = _render_prompt(
        prompts.bridge_resolution_prompt,
        structural_frame=_json_block(structural_frame),
        current_span=_json_block(current_span),
        working_pressure=_json_block(working_pressure),
        anchor_context=_json_block(_anchor_context(anchor_memory)),
        activation_context=_json_block(_activation_context(knowledge_activations)),
        candidate_set=_json_block(candidate_pool),
        policy_snapshot=_json_block(reader_policy),
        output_language_name=language_name(output_language),
    )
    _write_prompt_manifest(
        output_dir,
        node_name="bridge_resolution",
        prompt_version=prompts.bridge_resolution_version,
        system_prompt=prompts.bridge_resolution_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )

    with llm_invocation_scope(
        trace_context=LLMTraceContext(stage="phase5", node="bridge_resolution")
    ):
        payload = invoke_json(prompts.bridge_resolution_system, user_prompt, default={})
    decision = _clean_text(payload.get("decision")).lower() if isinstance(payload, dict) else ""
    if decision not in {"bridge", "decline"}:
        decision = "decline"

    primary_requested = _normalize_bridge_candidate(payload.get("primary_bridge")) if isinstance(payload, dict) else None
    primary_bridge = _select_candidate(primary_requested, candidate_pool)
    primary_attribution = _normalize_bridge_attribution(payload.get("primary_attribution")) if isinstance(payload, dict) else None
    supporting_requested = _normalize_bridge_candidates(payload.get("supporting_bridges")) if isinstance(payload, dict) else []
    supporting_bridges = [
        candidate
        for candidate in (_select_candidate(item, candidate_pool) for item in supporting_requested)
        if candidate is not None and (primary_bridge is None or not _bridge_candidates_match(candidate, primary_bridge))
    ]

    if decision == "bridge" and (
        primary_bridge is None
        or not _bridge_attribution_is_specific(
            primary_attribution,
            primary_bridge=primary_bridge,
            current_span_sentences=current_span_sentences,
        )
    ):
        decision = "decline"
        primary_bridge = None
        primary_attribution = None
        supporting_bridges = []

    requested_search_mode = _clean_text(payload.get("search_policy_mode")) if isinstance(payload, dict) else ""
    requested_search_trigger = _clean_text(payload.get("search_trigger")) if isinstance(payload, dict) else ""
    search_trigger = (
        requested_search_trigger if requested_search_trigger in {"none", "identity_critical_reference", "blocking_allusion", "genuine_curiosity", "ornamental_curiosity"} else "none"
    )
    search_policy_mode = resolve_search_policy_mode(
        requested_search_mode or "no_search",
        search_trigger=search_trigger,  # type: ignore[arg-type]
        reading_can_continue=decision != "decline" or primary_bridge is not None,
        reader_policy=reader_policy,
    )

    knowledge_use_mode = _clean_text(payload.get("knowledge_use_mode")) if isinstance(payload, dict) else ""
    if knowledge_use_mode not in {"book_grounded_only", "book_grounded_plus_prior_knowledge"}:
        knowledge_use_mode = str(knowledge_activations.get("knowledge_use_mode", "book_grounded_only"))

    return {
        "decision": decision,  # type: ignore[typeddict-item]
        "reason": _clean_text(payload.get("reason")) if isinstance(payload, dict) else "",
        "primary_bridge": primary_bridge,
        "primary_attribution": primary_attribution,
        "supporting_bridges": supporting_bridges,
        "activation_updates": _normalize_state_operations(payload.get("activation_updates")) if isinstance(payload, dict) else [],
        "state_operations": _normalize_state_operations(payload.get("state_operations")) if isinstance(payload, dict) else [],
        "knowledge_use_mode": knowledge_use_mode,  # type: ignore[typeddict-item]
        "search_policy_mode": search_policy_mode,
        "search_trigger": search_trigger,  # type: ignore[typeddict-item]
        "search_query": _clean_text(payload.get("search_query")) if isinstance(payload, dict) else "",
    }


def apply_bridge_state_updates(
    anchor_memory: AnchorMemoryState,
    *,
    current_anchor: AnchorRecord,
    primary_bridge: BridgeCandidate | None,
    supporting_bridges: list[BridgeCandidate] | None = None,
    motif_keys: list[str] | None = None,
    unresolved_reference_keys: list[str] | None = None,
) -> tuple[AnchorMemoryState, BridgeCandidate | None]:
    """Persist retained anchors, typed relations, indexes, and trace links for one bridge moment."""

    next_state = upsert_anchor_record(anchor_memory, current_anchor)
    current_anchor_id = _clean_text(current_anchor.get("anchor_id"))
    trace_targets = list(current_anchor.get("linked_activation_ids", []))

    materialized_primary = primary_bridge
    if primary_bridge is not None:
        next_state, materialized_primary = _materialize_bridge_target(
            next_state,
            primary_bridge,
            linked_activation_ids=list(current_anchor.get("linked_activation_ids", [])),
        )
        target_anchor_id = _clean_text((materialized_primary or {}).get("target_anchor_id"))
        if current_anchor_id and target_anchor_id and current_anchor_id != target_anchor_id:
            relation_type = _clean_text((materialized_primary or {}).get("relation_type")) or "echo"
            if relation_type not in _ANCHOR_RELATION_TYPES:
                relation_type = "echo"
            relation: AnchorRelation = {
                "relation_id": f"rel:{current_anchor_id}:{relation_type}:{target_anchor_id}",
                "relation_type": relation_type,  # type: ignore[typeddict-item]
                "source_anchor_id": current_anchor_id,
                "target_anchor_id": target_anchor_id,
                "rationale": _clean_text((materialized_primary or {}).get("why_now")) or "bridge resolution linked the two anchors",
            }
            next_state = append_anchor_relation(next_state, relation)
            trace_targets.append(target_anchor_id)

    materialized_supports: list[str] = []
    for candidate in supporting_bridges or []:
        next_state, materialized = _materialize_bridge_target(
            next_state,
            candidate,
            linked_activation_ids=list(current_anchor.get("linked_activation_ids", [])),
        )
        support_anchor_id = _clean_text(materialized.get("target_anchor_id"))
        if support_anchor_id and support_anchor_id not in materialized_supports:
            materialized_supports.append(support_anchor_id)

    return (
        index_anchor_memory(
            next_state,
            anchor_id=current_anchor_id,
            motif_keys=motif_keys,
            unresolved_reference_keys=unresolved_reference_keys,
            trace_targets=[*trace_targets, *materialized_supports],
        ),
        materialized_primary,
    )


def run_phase5_bridge_cycle(
    *,
    current_span_sentences: list[dict[str, object]],
    candidate_set: dict[str, object],
    working_pressure: WorkingPressureState,
    anchor_memory: AnchorMemoryState,
    knowledge_activations: KnowledgeActivationsState,
    move_history: MoveHistoryState,
    reader_policy: ReaderPolicy,
    output_language: str,
    current_anchor: AnchorRecord | None = None,
    motif_keys: list[str] | None = None,
    unresolved_reference_keys: list[str] | None = None,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
) -> dict[str, object]:
    """Run Phase 5 bridge judgment plus the durable state writes it requires."""

    if not current_span_sentences:
        return {
            "bridge_result": {
                "decision": "decline",
                "reason": "No current span is available.",
                "primary_bridge": None,
                "primary_attribution": None,
                "supporting_bridges": [],
                "activation_updates": [],
                "state_operations": [],
                "knowledge_use_mode": str(knowledge_activations.get("knowledge_use_mode", "book_grounded_only")),
                "search_policy_mode": "no_search",
                "search_trigger": "none",
                "search_query": "",
            },
            "working_pressure": working_pressure,
            "anchor_memory": anchor_memory,
            "knowledge_activations": knowledge_activations,
            "move_history": move_history,
        }

    last_sentence = current_span_sentences[-1]
    source_sentence_id = _clean_text(last_sentence.get("sentence_id"))
    resolved_current_anchor = current_anchor or build_anchor_record(
        sentence_start_id=source_sentence_id,
        sentence_end_id=source_sentence_id,
        quote=_clean_text(last_sentence.get("text")),
        locator=dict(last_sentence.get("locator", {})) if isinstance(last_sentence.get("locator"), dict) else {},
        anchor_kind="current_focus",
        why_it_mattered="bridge-triggering current focus",
        linked_activation_ids=[
            str(activation.get("activation_id", "") or "")
            for activation in knowledge_activations.get("activations", [])
            if isinstance(activation, dict) and str(activation.get("status", "") or "") in {"plausible", "strong"}
        ],
    )

    bridge_result = bridge_resolution(
        current_span_sentences=current_span_sentences,
        candidate_set=candidate_set,
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

    next_knowledge = apply_activation_operations(
        knowledge_activations,
        bridge_result.get("activation_updates", []),
        current_sentence_id=source_sentence_id,
        reader_policy=reader_policy,
    )
    next_knowledge = set_knowledge_use_mode(
        next_knowledge,
        bridge_result.get("knowledge_use_mode", next_knowledge.get("knowledge_use_mode", "book_grounded_only")),  # type: ignore[arg-type]
    )
    next_knowledge = set_search_policy_mode(
        next_knowledge,
        bridge_result.get("search_policy_mode", next_knowledge.get("search_policy_mode", "no_search")),  # type: ignore[arg-type]
    )

    next_working_pressure = apply_working_pressure_operations(
        working_pressure,
        bridge_result.get("state_operations", []),
    )
    next_anchor_memory, materialized_primary = apply_bridge_state_updates(
        anchor_memory,
        current_anchor=resolved_current_anchor,
        primary_bridge=bridge_result.get("primary_bridge"),
        supporting_bridges=bridge_result.get("supporting_bridges", []),
        motif_keys=motif_keys,
        unresolved_reference_keys=unresolved_reference_keys,
    )

    next_move_history = move_history
    if bridge_result.get("decision") == "bridge" and materialized_primary is not None:
        next_move_history = append_move(
            move_history,
            {
                "move_id": f"move:{source_sentence_id}:bridge",
                "move_type": "bridge",
                "reason": _clean_text(bridge_result.get("reason")) or "bridge resolution selected an earlier anchor",
                "source_sentence_id": source_sentence_id,
                "target_anchor_id": _clean_text(materialized_primary.get("target_anchor_id")),
                "target_sentence_id": _clean_text(materialized_primary.get("target_sentence_id")),
                "created_at": _timestamp(),
            },
        )

    return {
        "bridge_result": {
            **bridge_result,
            "primary_bridge": materialized_primary,
        },
        "working_pressure": next_working_pressure,
        "anchor_memory": next_anchor_memory,
        "knowledge_activations": next_knowledge,
        "move_history": next_move_history,
    }
