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
from .state_projection import build_read_prompt_packet
from .schemas import (
    AnchorBankState,
    AnchorMemoryState,
    BridgeCandidate,
    CarryForwardContext,
    DetourNeed,
    DetourSearchResult,
    KnowledgeActivationsState,
    MoveType,
    NavigationContext,
    NavigateRouteDecision,
    OutsideLink,
    PressureSignals,
    PreviewRange,
    PriorLink,
    ReactionCandidate,
    ReactionType,
    ReadUnitResult,
    ReaderPolicy,
    SearchIntent,
    StateOperation,
    SurfacedReaction,
    UnitizeBoundaryType,
    UnitizeDecision,
    WorkingState,
)
from .storage import append_jsonl, prompt_manifest_file, save_json, unitization_audit_file


_REACTION_TYPES: set[ReactionType] = {
    "highlight",
    "association",
    "curious",
    "discern",
    "retrospect",
    "silent",
}
_MOVE_TYPES: set[MoveType] = {"advance", "dwell", "bridge", "reframe"}
_ROUTE_ACTIONS = {"commit", "continue", "bridge_back", "reframe"}
_OUTSIDE_LINK_KINDS = {"work", "person", "concept", "history", "analogy", "other"}
_UNITIZE_BOUNDARY_TYPES: set[UnitizeBoundaryType] = {
    "paragraph_end",
    "intra_paragraph_semantic_close",
    "cross_paragraph_continuation",
    "section_end",
    "budget_cap",
}
_STATE_OPERATION_TYPES = {
    "append",
    "update",
    "close",
    "link",
    "create",
    "cool",
    "drop",
    "retain_anchor",
    "link_anchors",
    "promote",
    "supersede",
    "reactivate",
}
_DETOUR_STATUSES = {"open", "resolved", "abandoned"}
_DETOUR_SEARCH_DECISIONS = {"narrow_scope", "land_region", "defer_detour"}


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


def _anchor_context(anchor_memory: AnchorMemoryState | AnchorBankState, *, limit: int = 4) -> list[dict[str, object]]:
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


def _find_sentence_for_anchor_quote(
    sentences: list[dict[str, object]],
    *,
    anchor_quote: str,
) -> dict[str, object] | None:
    """Return the first sentence that contains the current local anchor quote."""

    cleaned_anchor = _clean_text(anchor_quote)
    if not cleaned_anchor:
        return None
    for sentence in sentences:
        text = _clean_text(sentence.get("text"))
        if cleaned_anchor and cleaned_anchor in text:
            return sentence
    return None


def _quotes_share_local_focus(left: str, right: str) -> bool:
    """Return whether two compact quotes clearly point at the same local hinge."""

    cleaned_left = _clean_text(left)
    cleaned_right = _clean_text(right)
    if not cleaned_left or not cleaned_right:
        return False
    return cleaned_left in cleaned_right or cleaned_right in cleaned_left


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


def _sentence_id(sentence: dict[str, object]) -> str:
    """Return the normalized sentence id for one sentence-like mapping."""

    return _clean_text(sentence.get("sentence_id"))


def _sentence_paragraph_index(sentence: dict[str, object]) -> int:
    """Return the best-effort paragraph index for one sentence-like mapping."""

    locator = sentence.get("locator")
    if isinstance(locator, dict):
        paragraph_index = int(locator.get("paragraph_index", 0) or locator.get("paragraph_start", 0) or 0)
        if paragraph_index > 0:
            return paragraph_index
    return int(sentence.get("paragraph_index", 0) or 0)


def _sentences_by_paragraph(
    sentences: list[dict[str, object]],
) -> list[tuple[int, list[dict[str, object]]]]:
    """Return ordered paragraph buckets for one chapter sentence list."""

    paragraphs: list[tuple[int, list[dict[str, object]]]] = []
    for sentence in sentences:
        paragraph_index = _sentence_paragraph_index(sentence)
        if paragraphs and paragraphs[-1][0] == paragraph_index:
            paragraphs[-1][1].append(sentence)
            continue
        paragraphs.append((paragraph_index, [sentence]))
    return paragraphs


def build_unitize_preview(
    *,
    chapter_sentences: list[dict[str, object]],
    current_sentence_id: str,
) -> tuple[list[dict[str, object]], PreviewRange]:
    """Return the fixed Phase A preview window for unitization.

    Phase A preview is intentionally narrow:
    - current paragraph remainder
    - plus the next paragraph in the same section only

    Since the canonical substrate does not expose stable section ids, "same section"
    is approximated conservatively by refusing to cross into a heading paragraph.
    """

    ordered = [dict(sentence) for sentence in chapter_sentences if isinstance(sentence, dict)]
    if not ordered:
        return [], {"start_sentence_id": "", "end_sentence_id": ""}

    current_index = next(
        (index for index, sentence in enumerate(ordered) if _sentence_id(sentence) == _clean_text(current_sentence_id)),
        -1,
    )
    if current_index < 0:
        return [], {"start_sentence_id": "", "end_sentence_id": ""}

    paragraphs = _sentences_by_paragraph(ordered)
    current_paragraph_position = next(
        (index for index, (_paragraph_index, bucket) in enumerate(paragraphs) if any(_sentence_id(item) == _clean_text(current_sentence_id) for item in bucket)),
        -1,
    )
    if current_paragraph_position < 0:
        return [], {"start_sentence_id": "", "end_sentence_id": ""}

    current_paragraph = paragraphs[current_paragraph_position][1]
    current_offset = next(
        (index for index, sentence in enumerate(current_paragraph) if _sentence_id(sentence) == _clean_text(current_sentence_id)),
        0,
    )
    preview_sentences = [dict(sentence) for sentence in current_paragraph[current_offset:]]

    if current_paragraph_position + 1 < len(paragraphs):
        next_paragraph = paragraphs[current_paragraph_position + 1][1]
        next_is_heading = any(
            _clean_text(sentence.get("text_role")) in {"section_heading", "chapter_heading"}
            for sentence in next_paragraph
        )
        if not next_is_heading:
            preview_sentences.extend(dict(sentence) for sentence in next_paragraph)

    if not preview_sentences:
        preview_sentences = [dict(ordered[current_index])]

    return preview_sentences, {
        "start_sentence_id": _sentence_id(preview_sentences[0]),
        "end_sentence_id": _sentence_id(preview_sentences[-1]),
    }


def _current_paragraph_end_sentence_id(preview_sentences: list[dict[str, object]]) -> str:
    """Return the sentence id at the end of the current paragraph preview slice."""

    if not preview_sentences:
        return ""
    first_paragraph_index = _sentence_paragraph_index(preview_sentences[0])
    current_paragraph = [
        sentence
        for sentence in preview_sentences
        if _sentence_paragraph_index(sentence) == first_paragraph_index
    ]
    if not current_paragraph:
        return _sentence_id(preview_sentences[-1])
    return _sentence_id(current_paragraph[-1])


def _paragraph_sentences_from_preview(
    preview_sentences: list[dict[str, object]],
) -> list[list[dict[str, object]]]:
    """Return ordered paragraph buckets from one preview slice."""

    return [bucket for _paragraph_index, bucket in _sentences_by_paragraph(preview_sentences)]


def _is_heading_paragraph(paragraph_sentences: list[dict[str, object]]) -> bool:
    """Return whether one preview paragraph is entirely heading-like."""

    if not paragraph_sentences:
        return False
    roles = {_clean_text(sentence.get("text_role")) for sentence in paragraph_sentences}
    return bool(roles) and roles.issubset({"chapter_heading", "section_heading"})


def _has_body_sentence(paragraph_sentences: list[dict[str, object]]) -> bool:
    """Return whether one preview paragraph contains body text."""

    return any(_clean_text(sentence.get("text_role")) == "body" for sentence in paragraph_sentences)


def _normalize_unitize_boundary_type(value: object) -> UnitizeBoundaryType:
    """Normalize one unitize boundary type with a conservative fallback."""

    normalized = _clean_text(value).lower().replace("-", "_")
    if normalized in _UNITIZE_BOUNDARY_TYPES:
        return normalized  # type: ignore[return-value]
    return "paragraph_end"


def _apply_unitize_guardrail(
    decision: UnitizeDecision,
    *,
    preview_sentences: list[dict[str, object]],
    reader_policy: ReaderPolicy,
) -> UnitizeDecision:
    """Clamp a semantic unitize choice to Phase A's emergency sentence ceiling."""

    if not preview_sentences:
        return decision
    max_sentences = int(reader_policy.get("unitize", {}).get("max_coverage_unit_sentences", 12) or 12)
    if max_sentences <= 0:
        max_sentences = 12

    preview_ids = [_sentence_id(sentence) for sentence in preview_sentences if _sentence_id(sentence)]
    preview_start = preview_ids[0]
    preview_end = preview_ids[-1]
    chosen_end = _clean_text(decision.get("end_sentence_id")) or _current_paragraph_end_sentence_id(preview_sentences) or preview_end
    if chosen_end not in preview_ids:
        chosen_end = _current_paragraph_end_sentence_id(preview_sentences) or preview_end

    end_index = preview_ids.index(chosen_end)
    if end_index + 1 > max_sentences:
        bounded_end = preview_sentences[max_sentences - 1]
        bounded_ids = preview_ids[:max_sentences]
        return {
            **decision,
            "start_sentence_id": preview_start,
            "end_sentence_id": _sentence_id(bounded_end),
            "preview_range": {
                "start_sentence_id": preview_start,
                "end_sentence_id": preview_end,
            },
            "boundary_type": "budget_cap",
            "evidence_sentence_ids": bounded_ids,
            "continuation_pressure": True,
            "reason": _clean_text(decision.get("reason")) or "unitize_budget_cap",
        }

    evidence_sentence_ids = [
        sentence_id
        for sentence_id in decision.get("evidence_sentence_ids", [])
        if sentence_id in preview_ids[: end_index + 1]
    ]
    if not evidence_sentence_ids:
        evidence_sentence_ids = preview_ids[: end_index + 1]
    return {
        **decision,
        "start_sentence_id": preview_start,
        "end_sentence_id": chosen_end,
        "preview_range": {
            "start_sentence_id": preview_start,
            "end_sentence_id": preview_end,
        },
        "boundary_type": _normalize_unitize_boundary_type(decision.get("boundary_type")),
        "evidence_sentence_ids": evidence_sentence_ids,
        "continuation_pressure": bool(decision.get("continuation_pressure")),
        "reason": _clean_text(decision.get("reason")),
    }


def _fallback_unitize_decision(preview_sentences: list[dict[str, object]]) -> UnitizeDecision:
    """Return a deterministic paragraph-bounded fallback decision."""

    if not preview_sentences:
        return {
            "start_sentence_id": "",
            "end_sentence_id": "",
            "preview_range": {"start_sentence_id": "", "end_sentence_id": ""},
            "boundary_type": "paragraph_end",
            "evidence_sentence_ids": [],
            "reason": "unitize_fallback_empty_preview",
            "continuation_pressure": False,
        }
    paragraph_end_sentence_id = _current_paragraph_end_sentence_id(preview_sentences) or _sentence_id(preview_sentences[-1])
    preview_ids = [_sentence_id(sentence) for sentence in preview_sentences if _sentence_id(sentence)]
    fallback_reason = "unitize_fallback_current_paragraph"

    preview_paragraphs = _paragraph_sentences_from_preview(preview_sentences)
    if len(preview_paragraphs) >= 2:
        first_paragraph = preview_paragraphs[0]
        second_paragraph = preview_paragraphs[1]
        if _is_heading_paragraph(first_paragraph) and _has_body_sentence(second_paragraph):
            paragraph_end_sentence_id = _sentence_id(second_paragraph[-1]) or paragraph_end_sentence_id
            fallback_reason = "unitize_fallback_heading_with_body"

    end_index = preview_ids.index(paragraph_end_sentence_id) if paragraph_end_sentence_id in preview_ids else len(preview_ids) - 1
    return {
        "start_sentence_id": _sentence_id(preview_sentences[0]),
        "end_sentence_id": paragraph_end_sentence_id,
        "preview_range": {
            "start_sentence_id": _sentence_id(preview_sentences[0]),
            "end_sentence_id": _sentence_id(preview_sentences[-1]),
        },
        "boundary_type": "paragraph_end",
        "evidence_sentence_ids": preview_ids[: end_index + 1],
        "reason": fallback_reason,
        "continuation_pressure": False,
    }


def persist_unitization_audit(
    output_dir: Path | None,
    *,
    chapter_id: int,
    chapter_ref: str,
    unitize_decision: UnitizeDecision,
) -> None:
    """Append one mechanism-private unitization audit record."""

    if output_dir is None:
        return
    append_jsonl(
        unitization_audit_file(output_dir),
        {
            "recorded_at": _timestamp(),
            "chapter_id": chapter_id,
            "chapter_ref": chapter_ref,
            "unitize_decision": dict(unitize_decision),
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
        operation_type = _clean_text(item.get("op") or item.get("operation_type")).lower().replace("-", "_")
        if operation_type not in _STATE_OPERATION_TYPES:
            continue
        payload = item.get("payload")
        target_key = _clean_text(item.get("target_key") or item.get("item_id"))
        operations.append(
            {
                "op": operation_type,  # type: ignore[typeddict-item]
                "operation_type": operation_type,  # type: ignore[typeddict-item]
                "target_store": _clean_text(item.get("target_store")) or "working_state",
                "target_key": target_key,
                "item_id": target_key,
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


def _normalize_pressure_signals(value: object) -> PressureSignals:
    """Normalize one local post-read pressure packet."""

    if not isinstance(value, dict):
        return {
            "continuation_pressure": False,
            "backward_pull": False,
            "frame_shift_pressure": False,
        }
    return {
        "continuation_pressure": bool(value.get("continuation_pressure")),
        "backward_pull": bool(value.get("backward_pull")),
        "frame_shift_pressure": bool(value.get("frame_shift_pressure")),
    }


def _derive_pressure_signals_from_legacy_fields(
    *,
    move_hint: str,
    continuation_pressure: bool,
) -> PressureSignals:
    """Derive pressure signals from the legacy route-oriented read fields."""

    normalized_move = _clean_text(move_hint).lower().replace("-", "_")
    return {
        "continuation_pressure": bool(continuation_pressure),
        "backward_pull": normalized_move == "bridge",
        "frame_shift_pressure": normalized_move == "reframe",
    }


def _normalize_prior_link(
    value: object,
    *,
    allowed_ref_ids: set[str],
) -> PriorLink | None:
    """Normalize one explicit surfaced prior-link packet."""

    if not isinstance(value, dict):
        return None
    ref_ids = [
        ref_id
        for ref_id in (
            _clean_text(item)
            for item in value.get("ref_ids", [])
            if isinstance(value.get("ref_ids"), list)
        )
        if ref_id and (not allowed_ref_ids or ref_id in allowed_ref_ids)
    ]
    relation = _clean_text(value.get("relation"))
    note = _clean_text(value.get("note"))
    if not ref_ids:
        return None
    return {
        "ref_ids": ref_ids[:4],
        "relation": relation,
        "note": note,
    }


def _normalize_outside_link(value: object) -> OutsideLink | None:
    """Normalize one explicit surfaced outside-reference packet."""

    if not isinstance(value, dict):
        return None
    kind = _clean_text(value.get("kind")).lower()
    label = _clean_text(value.get("label"))
    note = _clean_text(value.get("note"))
    if not label:
        return None
    if kind not in _OUTSIDE_LINK_KINDS:
        kind = "other"
    return {
        "kind": kind,
        "label": label,
        "note": note,
    }


def _normalize_search_intent(value: object) -> SearchIntent | None:
    """Normalize one explicit surfaced search-intent packet."""

    if not isinstance(value, dict):
        return None
    query = _clean_text(value.get("query"))
    rationale = _clean_text(value.get("rationale"))
    if not query:
        return None
    return {
        "query": query,
        "rationale": rationale,
    }


def _normalize_surfaced_reaction(
    value: object,
    *,
    current_unit_texts: list[str],
    allowed_ref_ids: set[str],
) -> SurfacedReaction | None:
    """Normalize one surfaced read-owned reaction."""

    if not isinstance(value, dict):
        return None
    anchor_quote = _clean_text(value.get("anchor_quote"))
    content = _clean_text(value.get("content"))
    if not anchor_quote or not content:
        return None
    if current_unit_texts and not any(anchor_quote in text for text in current_unit_texts):
        return None
    return {
        "anchor_quote": anchor_quote,
        "content": content,
        "prior_link": _normalize_prior_link(value.get("prior_link"), allowed_ref_ids=allowed_ref_ids),
        "outside_link": _normalize_outside_link(value.get("outside_link")),
        "search_intent": _normalize_search_intent(value.get("search_intent")),
    }


def _normalize_surfaced_reactions(
    value: object,
    *,
    current_unit_texts: list[str],
    allowed_ref_ids: set[str],
) -> list[SurfacedReaction]:
    """Normalize the surfaced reactions emitted directly by the read step."""

    reactions: list[SurfacedReaction] = []
    if not isinstance(value, list):
        return reactions
    for item in value:
        normalized = _normalize_surfaced_reaction(
            item,
            current_unit_texts=current_unit_texts,
            allowed_ref_ids=allowed_ref_ids,
        )
        if normalized is not None:
            reactions.append(normalized)
    return reactions


def _normalize_detour_need(value: object) -> DetourNeed | None:
    """Normalize one optional detour-need request."""

    if not isinstance(value, dict):
        return None
    reason = _clean_text(value.get("reason"))
    target_hint = _clean_text(value.get("target_hint"))
    status = _clean_text(value.get("status")).lower().replace("-", "_")
    if status not in _DETOUR_STATUSES:
        status = "open"
    if not any((reason, target_hint)):
        return None
    result: DetourNeed = {
        "reason": reason,
        "target_hint": target_hint,
        "status": status,  # type: ignore[typeddict-item]
    }
    return result


def _normalize_detour_search_result(
    value: object,
    *,
    allowed_sentence_ids: set[str],
) -> DetourSearchResult:
    """Normalize one detour-search result against the currently visible search space."""

    if not isinstance(value, dict):
        return {
            "decision": "defer_detour",
            "reason": "",
            "start_sentence_id": "",
            "end_sentence_id": "",
        }
    decision = _clean_text(value.get("decision")).lower().replace("-", "_")
    if decision not in _DETOUR_SEARCH_DECISIONS:
        decision = "defer_detour"
    start_sentence_id = _clean_text(value.get("start_sentence_id"))
    end_sentence_id = _clean_text(value.get("end_sentence_id"))
    if decision != "defer_detour":
        if start_sentence_id not in allowed_sentence_ids or end_sentence_id not in allowed_sentence_ids:
            decision = "defer_detour"
            start_sentence_id = ""
            end_sentence_id = ""
    return {
        "decision": decision,  # type: ignore[typeddict-item]
        "reason": _clean_text(value.get("reason")),
        "start_sentence_id": start_sentence_id,
        "end_sentence_id": end_sentence_id,
    }


def _fallback_read_unit_result(
    *,
    current_unit_sentences: list[dict[str, object]],
    continuation_pressure: bool = False,
    reason: str = "",
) -> ReadUnitResult:
    """Return one conservative fallback read result."""

    return {
        "unit_delta": _clean_text(reason),
        "pressure_signals": {
            "continuation_pressure": bool(continuation_pressure),
            "backward_pull": False,
            "frame_shift_pressure": False,
        },
        "surfaced_reactions": [],
        "implicit_uptake_ops": [],
        "detour_need": None,
    }


def navigate_unitize(
    *,
    current_sentence: dict[str, object],
    preview_sentences: list[dict[str, object]],
    navigation_context: NavigationContext | None = None,
    reader_policy: ReaderPolicy,
    output_language: str,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
) -> UnitizeDecision:
    """Choose the next exact coverage unit inside the fixed Phase A preview window."""

    fallback = _fallback_unitize_decision(preview_sentences)
    prompts = ATTENTIONAL_V2_PROMPTS
    structural_frame = _structural_frame(
        book_title=book_title,
        author=author,
        chapter_title=chapter_title,
        output_language=output_language,
    )
    preview_range = {
        "start_sentence_id": _sentence_id(preview_sentences[0]) if preview_sentences else "",
        "end_sentence_id": _sentence_id(preview_sentences[-1]) if preview_sentences else "",
    }
    user_prompt = _render_prompt(
        prompts.navigate_unitize_prompt,
        structural_frame=_json_block(structural_frame),
        current_sentence=_json_block(
            {
                "sentence_id": _sentence_id(current_sentence),
                "text": _clean_text(current_sentence.get("text")),
                "text_role": _clean_text(current_sentence.get("text_role")),
                "paragraph_index": _sentence_paragraph_index(current_sentence),
            }
        ),
        preview_range=_json_block(preview_range),
        preview_sentences=_json_block(
            [
                {
                    "sentence_id": _sentence_id(sentence),
                    "text": _clean_text(sentence.get("text")),
                    "text_role": _clean_text(sentence.get("text_role")),
                    "paragraph_index": _sentence_paragraph_index(sentence),
                }
                for sentence in preview_sentences
            ]
        ),
        navigation_context=_json_block(dict(navigation_context or {})),
        policy_snapshot=_json_block(reader_policy),
        output_language_name=language_name(output_language),
    )
    _write_prompt_manifest(
        output_dir,
        node_name="navigate_unitize",
        prompt_version=prompts.navigate_unitize_version,
        system_prompt=prompts.navigate_unitize_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )

    try:
        with llm_invocation_scope(trace_context=LLMTraceContext(stage="phase4", node="navigate_unitize")):
            payload = invoke_json(prompts.navigate_unitize_system, user_prompt, default={})
        decision: UnitizeDecision = {
            "start_sentence_id": _clean_text(payload.get("start_sentence_id")) if isinstance(payload, dict) else "",
            "end_sentence_id": _clean_text(payload.get("end_sentence_id")) if isinstance(payload, dict) else "",
            "preview_range": {
                "start_sentence_id": preview_range["start_sentence_id"],
                "end_sentence_id": preview_range["end_sentence_id"],
            },
            "boundary_type": _normalize_unitize_boundary_type(payload.get("boundary_type") if isinstance(payload, dict) else ""),
            "evidence_sentence_ids": [
                _clean_text(item)
                for item in payload.get("evidence_sentence_ids", [])
                if _clean_text(item)
            ] if isinstance(payload, dict) and isinstance(payload.get("evidence_sentence_ids"), list) else [],
            "reason": _clean_text(payload.get("reason")) if isinstance(payload, dict) else "",
            "continuation_pressure": bool(payload.get("continuation_pressure")) if isinstance(payload, dict) else False,
        }
    except ReaderLLMError:
        decision = fallback

    return _apply_unitize_guardrail(
        {
            **fallback,
            **decision,
        },
        preview_sentences=preview_sentences,
        reader_policy=reader_policy,
    )


def navigate_detour_search(
    *,
    search_scope: dict[str, object],
    detour_need: DetourNeed,
    navigation_context: NavigationContext | None = None,
    reader_policy: ReaderPolicy,
    output_language: str,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
) -> DetourSearchResult:
    """Run one bounded detour-search step over a structured search scope."""

    prompts = ATTENTIONAL_V2_PROMPTS
    structural_frame = _structural_frame(
        book_title=book_title,
        author=author,
        chapter_title=chapter_title,
        output_language=output_language,
    )
    cards = [
        dict(card)
        for card in search_scope.get("cards", [])
        if isinstance(card, dict)
    ]
    allowed_sentence_ids = {
        _clean_text(card.get(key))
        for card in cards
        for key in ("start_sentence_id", "end_sentence_id")
        if _clean_text(card.get(key))
    }
    user_prompt = _render_prompt(
        prompts.navigate_detour_search_prompt,
        structural_frame=_json_block(structural_frame),
        detour_need=_json_block(dict(detour_need)),
        search_scope=_json_block(
            {
                "scope_kind": _clean_text(search_scope.get("scope_kind")),
                "reason": _clean_text(search_scope.get("reason")),
                "cards": cards,
            }
        ),
        navigation_context=_json_block(dict(navigation_context or {})),
        policy_snapshot=_json_block(reader_policy),
        output_language_name=language_name(output_language),
    )
    _write_prompt_manifest(
        output_dir,
        node_name="navigate_detour_search",
        prompt_version=prompts.navigate_detour_search_version,
        system_prompt=prompts.navigate_detour_search_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )

    try:
        with llm_invocation_scope(trace_context=LLMTraceContext(stage="phase4", node="navigate_detour_search")):
            payload = invoke_json(prompts.navigate_detour_search_system, user_prompt, default={})
        return _normalize_detour_search_result(payload, allowed_sentence_ids=allowed_sentence_ids)
    except ReaderLLMError:
        return {
            "decision": "defer_detour",
            "reason": "detour_search_llm_error",
            "start_sentence_id": "",
            "end_sentence_id": "",
        }


def _route_targets_from_ref_ids(
    supporting_ref_ids: list[str],
) -> tuple[str, str]:
    """Extract one best-effort route target from supporting context refs."""

    target_anchor_id = ""
    target_sentence_id = ""
    for ref_id in supporting_ref_ids:
        cleaned = _clean_text(ref_id)
        if cleaned.startswith("anchor:") and not target_anchor_id:
            target_anchor_id = cleaned.split("anchor:", 1)[1]
        elif cleaned.startswith("lookback:anchor:") and not target_anchor_id:
            target_anchor_id = cleaned.split("lookback:anchor:", 1)[1]
        elif cleaned.startswith("lookback:sentence:") and not target_sentence_id:
            target_sentence_id = cleaned.split("lookback:sentence:", 1)[1]
        elif cleaned.startswith("sentence:") and not target_sentence_id:
            target_sentence_id = cleaned.split("sentence:", 1)[1]
    return target_anchor_id, target_sentence_id


def read_unit(
    *,
    current_unit_sentences: list[dict[str, object]],
    carry_forward_context: CarryForwardContext,
    reader_policy: ReaderPolicy,
    output_language: str,
    supplemental_context: dict[str, object] | None = None,
    detour_context: dict[str, object] | None = None,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
) -> ReadUnitResult:
    """Run the authoritative formal read for one chosen unit."""

    prompts = ATTENTIONAL_V2_PROMPTS
    prompt_packet = build_read_prompt_packet(
        carry_forward_context=carry_forward_context,
        supplemental_context=supplemental_context,
        detour_context=detour_context,
    )
    structural_frame = _structural_frame(
        book_title=book_title,
        author=author,
        chapter_title=chapter_title,
        output_language=output_language,
    )
    user_prompt = _render_prompt(
        prompts.read_unit_prompt,
        structural_frame=_json_block(structural_frame),
        current_unit=_json_block(
            [
                {
                    "sentence_id": _clean_text(sentence.get("sentence_id")),
                    "text": _clean_text(sentence.get("text")),
                    "text_role": _clean_text(sentence.get("text_role")),
                }
                for sentence in current_unit_sentences
            ]
        ),
        carry_forward_context=_json_block(prompt_packet),
        supplemental_context=_json_block(dict(prompt_packet.get("selective_carry", {}))),
        policy_snapshot=_json_block(reader_policy),
        output_language_name=language_name(output_language),
    )
    _write_prompt_manifest(
        output_dir,
        node_name="read_unit",
        prompt_version=prompts.read_unit_version,
        system_prompt=prompts.read_unit_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )
    with llm_invocation_scope(trace_context=LLMTraceContext(stage="phase4", node="read_unit")):
        payload = invoke_json(prompts.read_unit_system, user_prompt, default={})

    current_unit_texts = [
        _clean_text(sentence.get("text"))
        for sentence in current_unit_sentences
        if _clean_text(sentence.get("text"))
    ]
    allowed_ref_ids = {
        _clean_text(ref.get("ref_id"))
        for ref in carry_forward_context.get("refs", [])
        if isinstance(ref, dict) and _clean_text(ref.get("ref_id"))
    }
    if isinstance(supplemental_context, dict):
        allowed_ref_ids.update(
            _clean_text(ref.get("ref_id"))
            for ref in supplemental_context.get("refs", [])
            if isinstance(ref, dict) and _clean_text(ref.get("ref_id"))
        )
        allowed_ref_ids.update(
            _clean_text(excerpt.get("ref_id"))
            for excerpt in supplemental_context.get("excerpts", [])
            if isinstance(excerpt, dict) and _clean_text(excerpt.get("ref_id"))
        )

    pressure_signals = _normalize_pressure_signals(payload.get("pressure_signals")) if isinstance(payload, dict) else {}
    if not any(pressure_signals.values()):
        legacy_move_hint = _clean_text(payload.get("move_hint") if isinstance(payload, dict) else "").lower().replace("-", "_")
        if legacy_move_hint not in _MOVE_TYPES:
            legacy_move_hint = "advance"
        legacy_continuation_pressure = bool(payload.get("continuation_pressure")) if isinstance(payload, dict) else False
        pressure_signals = _derive_pressure_signals_from_legacy_fields(
            move_hint=legacy_move_hint,
            continuation_pressure=legacy_continuation_pressure,
        )
    surfaced_reactions = _normalize_surfaced_reactions(
        payload.get("surfaced_reactions") if isinstance(payload, dict) else None,
        current_unit_texts=current_unit_texts,
        allowed_ref_ids=allowed_ref_ids,
    )
    unit_delta = _clean_text(payload.get("unit_delta")) if isinstance(payload, dict) else ""
    if not unit_delta:
        unit_delta = _clean_text(payload.get("local_understanding")) if isinstance(payload, dict) else ""
    result: ReadUnitResult = {
        "unit_delta": unit_delta,
        "pressure_signals": pressure_signals,
        "surfaced_reactions": surfaced_reactions,
        "implicit_uptake_ops": _normalize_state_operations(
            payload.get("implicit_uptake_ops")
            if isinstance(payload, dict)
            else None
        )
        or _normalize_state_operations(
            payload.get("implicit_uptake")
            if isinstance(payload, dict)
            else None
        ),
        "detour_need": _normalize_detour_need(payload.get("detour_need")) if isinstance(payload, dict) else None,
    }
    return result


def navigate_route(
    *,
    read_result: ReadUnitResult,
) -> NavigateRouteDecision:
    """Normalize the next-step route from the authoritative read packet."""

    action = "commit"
    pressure_signals = dict(read_result.get("pressure_signals") or {})
    if bool(pressure_signals.get("backward_pull")):
        action = "bridge_back"
    elif bool(pressure_signals.get("frame_shift_pressure")):
        action = "reframe"
    elif bool(pressure_signals.get("continuation_pressure")):
        action = "continue"
    if action not in _ROUTE_ACTIONS:
        action = "commit"
    return {
        "action": action,  # type: ignore[typeddict-item]
        "reason": _clean_text(read_result.get("unit_delta")),
        "close_current_unit": True,
        "target_anchor_id": "",
        "target_sentence_id": "",
    }
