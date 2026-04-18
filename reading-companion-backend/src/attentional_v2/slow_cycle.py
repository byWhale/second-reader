"""Phase 6 slow-cycle reasoning, durable reaction truth, and compatibility projection."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from src.iterator_reader.language import language_name
from src.iterator_reader.llm_utils import LLMTraceContext, invoke_json, llm_invocation_scope
from src.reading_core.book_document import BookChapter, ParagraphRecord

from .knowledge import apply_activation_operations
from .nodes import (
    _clean_text,
    _json_block,
    _normalize_reaction_candidate,
    _normalize_state_operations,
    _render_prompt,
    _structural_frame,
    _write_prompt_manifest,
)
from .prompts import ATTENTIONAL_V2_PROMPTS
from .schemas import (
    AnchorBankState,
    AnchorRecord,
    AnchoredReactionRecord,
    ChapterConsolidationResult,
    ConceptRegistryState,
    ExpressResult,
    KnowledgeActivationsState,
    OutsideLink,
    PriorLink,
    ReactionAnchor,
    ReactionCandidate,
    ReactionRecordsState,
    ReaderPolicy,
    ReconsolidationRecord,
    ReconsolidationRecordsState,
    ReconsolidationResult,
    ReflectiveItem,
    ReflectivePromotionCandidate,
    ReflectivePromotionResult,
    ReflectiveFramesState,
    SearchIntent,
    ThreadTraceState,
    WorkingPressureItem,
    WorkingState,
)
from .state_ops import (
    append_reaction_record,
    append_reconsolidation_record,
    apply_working_state_operations,
    replace_pressure_bucket,
    set_gate_state,
    supersede_reflective_item,
    upsert_anchor_record,
    upsert_reflective_item,
)
from .storage import chapter_result_compatibility_file, save_json


_FEATURED_PRIORITY = {
    "highlight": 0,
    "discern": 1,
    "association": 2,
    "retrospect": 3,
    "curious": 4,
}
_REFLECTIVE_BUCKETS = {
    "chapter_understandings",
    "book_level_frames",
    "durable_definitions",
    "stabilized_motifs",
    "resolved_questions_of_record",
    "chapter_end_notes",
}
_PRESSURE_BUCKETS = {
    "local_hypotheses",
    "local_questions",
    "local_tensions",
    "local_motifs",
}
_COMPAT_FAMILIES = {"highlight", "discern", "association", "retrospect", "curious", "silent"}


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_reaction_anchor(anchor: AnchorRecord | dict[str, object]) -> ReactionAnchor:
    """Project one retained anchor into the embedded durable-reaction anchor shape."""

    locator = anchor.get("locator")
    return {
        "anchor_id": _clean_text(anchor.get("anchor_id")),
        "sentence_start_id": _clean_text(anchor.get("sentence_start_id")),
        "sentence_end_id": _clean_text(anchor.get("sentence_end_id") or anchor.get("sentence_start_id")),
        "quote": _clean_text(anchor.get("quote")),
        "locator": dict(locator) if isinstance(locator, dict) else {},
    }


def _copy_prior_link(value: object) -> PriorLink | None:
    """Normalize one surfaced prior-link payload when present."""

    if not isinstance(value, Mapping):
        return None
    ref_ids = [_clean_text(item) for item in value.get("ref_ids", []) if _clean_text(item)]
    relation = _clean_text(value.get("relation"))
    note = _clean_text(value.get("note"))
    if not (ref_ids or relation or note):
        return None
    payload: PriorLink = {}
    if ref_ids:
        payload["ref_ids"] = ref_ids
    if relation:
        payload["relation"] = relation
    if note:
        payload["note"] = note
    return payload


def _copy_outside_link(value: object) -> OutsideLink | None:
    """Normalize one surfaced outside-link payload when present."""

    if not isinstance(value, Mapping):
        return None
    kind = _clean_text(value.get("kind"))
    label = _clean_text(value.get("label"))
    note = _clean_text(value.get("note"))
    if not (kind or label or note):
        return None
    payload: OutsideLink = {}
    if kind:
        payload["kind"] = kind
    if label:
        payload["label"] = label
    if note:
        payload["note"] = note
    return payload


def _copy_search_intent(value: object) -> SearchIntent | None:
    """Normalize one surfaced search-intent payload when present."""

    if not isinstance(value, Mapping):
        return None
    query = _clean_text(value.get("query"))
    rationale = _clean_text(value.get("rationale"))
    if not (query or rationale):
        return None
    payload: SearchIntent = {}
    if query:
        payload["query"] = query
    if rationale:
        payload["rationale"] = rationale
    return payload


def compat_reaction_family(payload: Mapping[str, object]) -> str:
    """Derive the legacy family label from one native persisted reaction shape."""

    if _copy_search_intent(payload.get("search_intent")) is not None:
        return "curious"
    if _copy_prior_link(payload.get("prior_link")) is not None:
        return "retrospect"
    if _copy_outside_link(payload.get("outside_link")) is not None:
        return "association"

    compat_family = _clean_text(payload.get("compat_family"))
    if compat_family == "silent":
        return "silent"
    if compat_family in _COMPAT_FAMILIES and compat_family != "silent":
        return compat_family

    explicit_type = _clean_text(payload.get("type"))
    if explicit_type == "silent":
        return "silent"
    if explicit_type in _COMPAT_FAMILIES and explicit_type != "silent":
        return explicit_type

    thought = _clean_text(payload.get("thought")) or _clean_text(payload.get("content"))
    anchor_quote = _clean_text(payload.get("anchor_quote"))
    if thought and len(thought) <= max(120, len(anchor_quote) + 60):
        return "highlight"
    if thought:
        return "discern"
    return "highlight"


def compat_search_query(payload: Mapping[str, object]) -> str:
    """Project the legacy search-query sidecar from native surfaced fields."""

    search_intent = _copy_search_intent(payload.get("search_intent"))
    if search_intent is not None:
        return _clean_text(search_intent.get("query"))
    return _clean_text(payload.get("search_query"))


def _legacy_search_intent_from_candidate(reaction: ReactionCandidate) -> SearchIntent | None:
    """Project a legacy curious payload into the native surfaced search-intent shape."""

    query = _clean_text(reaction.get("search_query"))
    if not query:
        return None
    return {
        "query": query,
        "rationale": "",
    }


def derive_reaction_id(
    *,
    chapter_ref: str,
    emitted_at_sentence_id: str,
    reaction_type: str,
    ordinal: int | None = None,
) -> str:
    """Build a deterministic durable-reaction id from chapter, sentence, and type."""

    parts = [
        "rx",
        _clean_text(chapter_ref).replace(" ", "_") or "chapter",
        _clean_text(emitted_at_sentence_id) or "sentence",
        _clean_text(reaction_type) or "reaction",
    ]
    if ordinal is not None and ordinal > 0:
        parts.append(str(int(ordinal)))
    return ":".join(parts)


def derive_reconsolidation_record_id(
    *,
    prior_reaction_id: str,
    later_sentence_id: str,
) -> str:
    """Build a deterministic reconsolidation-record id."""

    return f"rc:{_clean_text(prior_reaction_id)}:{_clean_text(later_sentence_id)}"


def build_reaction_record(
    *,
    reaction: ReactionCandidate,
    primary_anchor: AnchorRecord | dict[str, object],
    related_anchors: list[AnchorRecord | dict[str, object]] | None = None,
    chapter_id: int,
    chapter_ref: str,
    emitted_at_sentence_id: str,
    reaction_id: str | None = None,
    reconsolidation_record_id: str | None = None,
    supersedes_reaction_id: str | None = None,
    compatibility_section_ref: str | None = None,
    created_at: str | None = None,
    ordinal: int | None = None,
    record_source: str = "legacy_builder",
) -> AnchoredReactionRecord:
    """Build one mechanism-authored durable reaction record."""

    normalized_primary_anchor = build_reaction_anchor(primary_anchor)
    normalized_related = [build_reaction_anchor(anchor) for anchor in related_anchors or [] if isinstance(anchor, dict)]
    search_intent = _legacy_search_intent_from_candidate(reaction)
    compat_family = compat_reaction_family(
        {
            "type": _clean_text(reaction.get("type")),
            "content": _clean_text(reaction.get("content")),
            "anchor_quote": _clean_text(reaction.get("anchor_quote")),
            "search_intent": search_intent,
        }
    )
    return {
        "reaction_id": reaction_id
        or derive_reaction_id(
            chapter_ref=chapter_ref,
            emitted_at_sentence_id=emitted_at_sentence_id,
            reaction_type=compat_family,
            ordinal=ordinal,
        ),
        "chapter_id": int(chapter_id),
        "chapter_ref": _clean_text(chapter_ref),
        "emitted_at_sentence_id": _clean_text(emitted_at_sentence_id),
        "record_source": _clean_text(record_source) or "legacy_builder",
        "type": compat_family,  # type: ignore[typeddict-item]
        "compat_family": compat_family,  # type: ignore[typeddict-item]
        "thought": _clean_text(reaction.get("content")),
        "primary_anchor": normalized_primary_anchor,
        "related_anchors": normalized_related,
        "reconsolidation_record_id": _clean_text(reconsolidation_record_id),
        "supersedes_reaction_id": _clean_text(supersedes_reaction_id),
        "compatibility_section_ref": _clean_text(compatibility_section_ref),
        "prior_link": None,
        "outside_link": None,
        "search_intent": search_intent,
        "search_query": compat_search_query({"search_intent": search_intent, "search_query": reaction.get("search_query")}),
        "search_results": [
            dict(item)
            for item in reaction.get("search_results", [])
            if isinstance(item, dict)
        ]
        if isinstance(reaction.get("search_results"), list)
        else [],
        "created_at": created_at or _timestamp(),
    }


def build_reaction_record_from_express_result(
    *,
    express_result: ExpressResult,
    primary_anchor: AnchorRecord | dict[str, object],
    related_anchors: list[AnchorRecord | dict[str, object]] | None = None,
    chapter_id: int,
    chapter_ref: str,
    emitted_at_sentence_id: str,
    reaction_id: str | None = None,
    reconsolidation_record_id: str | None = None,
    supersedes_reaction_id: str | None = None,
    compatibility_section_ref: str | None = None,
    created_at: str | None = None,
    ordinal: int | None = None,
) -> AnchoredReactionRecord | None:
    """Build one native persisted reaction record directly from Express."""

    if _clean_text(express_result.get("decision")) != "emit":
        return None
    thought = _clean_text(express_result.get("content"))
    if not thought:
        return None

    normalized_primary_anchor = build_reaction_anchor(primary_anchor)
    normalized_related = [build_reaction_anchor(anchor) for anchor in related_anchors or [] if isinstance(anchor, dict)]
    prior_link = _copy_prior_link(express_result.get("prior_link"))
    outside_link = _copy_outside_link(express_result.get("outside_link"))
    search_intent = _copy_search_intent(express_result.get("search_intent"))
    compat_family = compat_reaction_family(
        {
            "content": thought,
            "anchor_quote": _clean_text(express_result.get("anchor_quote")) or _clean_text(normalized_primary_anchor.get("quote")),
            "prior_link": prior_link,
            "outside_link": outside_link,
            "search_intent": search_intent,
        }
    )

    return {
        "reaction_id": reaction_id
        or derive_reaction_id(
            chapter_ref=chapter_ref,
            emitted_at_sentence_id=emitted_at_sentence_id,
            reaction_type=compat_family,
            ordinal=ordinal,
        ),
        "chapter_id": int(chapter_id),
        "chapter_ref": _clean_text(chapter_ref),
        "emitted_at_sentence_id": _clean_text(emitted_at_sentence_id),
        "record_source": "express",
        "type": compat_family,  # type: ignore[typeddict-item]
        "compat_family": compat_family,  # type: ignore[typeddict-item]
        "thought": thought,
        "primary_anchor": normalized_primary_anchor,
        "related_anchors": normalized_related,
        "reconsolidation_record_id": _clean_text(reconsolidation_record_id),
        "supersedes_reaction_id": _clean_text(supersedes_reaction_id),
        "compatibility_section_ref": _clean_text(compatibility_section_ref),
        "prior_link": prior_link,
        "outside_link": outside_link,
        "search_intent": search_intent,
        "search_query": compat_search_query({"search_intent": search_intent}),
        "search_results": [],
        "created_at": created_at or _timestamp(),
    }


def reaction_records_for_chapter(
    state: ReactionRecordsState,
    *,
    chapter_ref: str,
) -> list[AnchoredReactionRecord]:
    """Return one chapter's durable visible reactions in persisted order."""

    return [
        dict(record)
        for record in state.get("records", [])
        if isinstance(record, dict) and _clean_text(record.get("chapter_ref")) == _clean_text(chapter_ref)
    ]


def _target_locator_from_anchor(anchor: ReactionAnchor | dict[str, object]) -> dict[str, object] | None:
    """Project one reaction anchor into the current target-locator shape."""

    locator = anchor.get("locator")
    if not isinstance(locator, dict):
        return None
    href = _clean_text(locator.get("href"))
    match_text = _clean_text(anchor.get("quote"))
    if not href or not match_text:
        return None
    return {
        "href": href,
        "start_cfi": locator.get("start_cfi"),
        "end_cfi": locator.get("end_cfi"),
        "match_text": match_text,
        "match_mode": "exact",
    }


def _compatibility_section_ref(
    record: AnchoredReactionRecord | dict[str, object],
    *,
    chapter_id: int,
) -> str:
    """Resolve the current temporary section-ref compatibility sidecar."""

    explicit = _clean_text(record.get("compatibility_section_ref"))
    if explicit:
        return explicit
    primary_anchor = record.get("primary_anchor")
    if isinstance(primary_anchor, dict):
        locator = primary_anchor.get("locator")
        if isinstance(locator, dict):
            paragraph_index = int(locator.get("paragraph_index", 0) or locator.get("paragraph_start", 0) or 0)
            if paragraph_index > 0:
                return f"{int(chapter_id)}.{paragraph_index}"
    return f"{int(chapter_id)}.1"


def _paragraph_locator(paragraph: ParagraphRecord | dict[str, object]) -> dict[str, object] | None:
    """Project one canonical paragraph into the current section-locator shape."""

    href = _clean_text(paragraph.get("href"))
    paragraph_index = int(paragraph.get("paragraph_index", 0) or 0)
    if not href or paragraph_index <= 0:
        return None
    return {
        "href": href,
        "start_cfi": paragraph.get("start_cfi"),
        "end_cfi": paragraph.get("end_cfi"),
        "paragraph_start": paragraph_index,
        "paragraph_end": paragraph_index,
    }


def _section_summary(record: AnchoredReactionRecord | dict[str, object], paragraph_index: int | None = None) -> str:
    """Build one compact temporary section summary for compatibility payloads."""

    thought = _clean_text(record.get("thought"))
    if thought:
        return thought[:160]
    if paragraph_index and paragraph_index > 0:
        return f"Anchored reactions around paragraph {paragraph_index}."
    return "Anchored reactions."


def project_chapter_result_compatibility(
    *,
    book_id: str,
    chapter: BookChapter | dict[str, object],
    reaction_records: list[AnchoredReactionRecord] | ReactionRecordsState,
    output_language: str,
    output_dir: Path | None = None,
    persist: bool = False,
) -> dict[str, object]:
    """Project mechanism-authored reactions into the current chapter_result-compatible shape."""

    chapter_id = int(chapter.get("id", 0) or 0)
    chapter_ref = _clean_text(chapter.get("reference") or chapter.get("chapter_ref") or f"Chapter {chapter_id}")
    chapter_title = _clean_text(chapter.get("title"))
    chapter_heading = dict(chapter.get("chapter_heading", {})) if isinstance(chapter.get("chapter_heading"), dict) else None
    paragraphs = [
        dict(paragraph)
        for paragraph in chapter.get("paragraphs", [])
        if isinstance(paragraph, dict)
    ]
    paragraphs_by_index = {
        int(paragraph.get("paragraph_index", 0) or 0): paragraph
        for paragraph in paragraphs
        if int(paragraph.get("paragraph_index", 0) or 0) > 0
    }

    records = (
        [dict(item) for item in reaction_records.get("records", []) if isinstance(item, dict)]
        if isinstance(reaction_records, dict) and "records" in reaction_records
        else [dict(item) for item in reaction_records if isinstance(item, dict)]
    )
    records = [
        record
        for record in records
        if _clean_text(record.get("chapter_ref")) == chapter_ref and compat_reaction_family(record) != "silent"
    ]

    section_groups: dict[str, dict[str, object]] = {}
    reaction_counts: Counter[str] = Counter()
    featured_candidates: list[dict[str, object]] = []

    for record in records:
        primary_anchor = record.get("primary_anchor")
        if not isinstance(primary_anchor, dict):
            continue
        section_ref = _compatibility_section_ref(record, chapter_id=chapter_id)
        paragraph_index = 0
        locator = primary_anchor.get("locator")
        if isinstance(locator, dict):
            paragraph_index = int(locator.get("paragraph_index", 0) or locator.get("paragraph_start", 0) or 0)
        paragraph = paragraphs_by_index.get(paragraph_index, {})
        section = section_groups.get(section_ref)
        if section is None:
            section = {
                "segment_id": f"compat:{section_ref}",
                "segment_ref": section_ref,
                "summary": _section_summary(record, paragraph_index=paragraph_index or None),
                "original_text": _clean_text(paragraph.get("text")),
                "verdict": "keep",
                "quality_status": "kept",
                "reflection_summary": "",
                "reflection_reason_codes": [],
                "reactions": [],
            }
            paragraph_locator = _paragraph_locator(paragraph)
            if paragraph_locator is not None:
                section["locator"] = paragraph_locator
            section_groups[section_ref] = section

        target_locator = _target_locator_from_anchor(primary_anchor)
        reaction_type = compat_reaction_family(record)
        reaction_card = {
            "reaction_id": _clean_text(record.get("reaction_id")),
            "type": reaction_type,
            "anchor_quote": _clean_text(primary_anchor.get("quote")),
            "content": _clean_text(record.get("thought")),
            "search_query": compat_search_query(record),
            "search_results": [
                dict(item)
                for item in record.get("search_results", [])
                if isinstance(item, dict)
            ]
            if isinstance(record.get("search_results"), list)
            else [],
            "primary_anchor": build_reaction_anchor(primary_anchor),
            "related_anchors": [
                build_reaction_anchor(anchor)
                for anchor in record.get("related_anchors", [])
                if isinstance(anchor, dict)
            ]
            if isinstance(record.get("related_anchors"), list)
            else [],
            "supersedes_reaction_id": _clean_text(record.get("supersedes_reaction_id")) or None,
        }
        if target_locator is not None:
            reaction_card["target_locator"] = target_locator
        section["reactions"].append(reaction_card)
        reaction_counts[reaction_type] += 1
        featured_candidates.append(
            {
                "reaction_id": _clean_text(record.get("reaction_id")),
                "type": reaction_type,
                "segment_ref": section_ref,
                "anchor_quote": _clean_text(primary_anchor.get("quote")),
                "content": _clean_text(record.get("thought")),
                "target_locator": target_locator or {},
                "primary_anchor": build_reaction_anchor(primary_anchor),
                "related_anchors": [
                    build_reaction_anchor(anchor)
                    for anchor in record.get("related_anchors", [])
                    if isinstance(anchor, dict)
                ]
                if isinstance(record.get("related_anchors"), list)
                else [],
                "supersedes_reaction_id": _clean_text(record.get("supersedes_reaction_id")) or None,
            }
        )

    sections = sorted(section_groups.values(), key=lambda item: str(item.get("segment_ref", "")))
    featured = sorted(
        featured_candidates,
        key=lambda item: (
            _FEATURED_PRIORITY.get(str(item.get("type", "")), 99),
            str(item.get("segment_ref", "")),
            str(item.get("reaction_id", "")),
        ),
    )[:3]
    payload = {
        "book_id": book_id,
        "chapter": {
            "id": chapter_id,
            "title": chapter_title,
            "reference": chapter_ref,
            "status": "completed",
        },
        "chapter_heading": chapter_heading,
        "output_language": output_language,
        "generated_at": _timestamp(),
        "sections": sections,
        "chapter_reflection": {},
        "featured_reactions": featured,
        "visible_reaction_count": sum(len(section.get("reactions", [])) for section in sections),
        "reaction_type_diversity": len(reaction_counts),
        "ui_summary": {
            "kept_section_count": len(sections),
            "skipped_section_count": 0,
            "reaction_counts": dict(sorted(reaction_counts.items())),
        },
    }
    if persist and output_dir is not None:
        save_json(chapter_result_compatibility_file(output_dir, chapter_id), payload)
    return payload


def _normalize_reflective_item(value: object, *, chapter_ref: str) -> ReflectiveItem | None:
    """Normalize one reflective item payload."""

    if not isinstance(value, dict):
        return None
    statement = _clean_text(value.get("statement"))
    if not statement:
        return None
    return {
        "item_id": _clean_text(value.get("item_id")),
        "statement": statement,
        "support_anchor_ids": [
            _clean_text(item)
            for item in value.get("support_anchor_ids", [])
            if _clean_text(item)
        ]
        if isinstance(value.get("support_anchor_ids"), list)
        else [],
        "confidence_band": _clean_text(value.get("confidence_band")) or "working",
        "promoted_from": _clean_text(value.get("promoted_from")) or "local_hypothesis",
        "status": _clean_text(value.get("status")) or "active",
        "chapter_ref": chapter_ref,
    }


def _normalize_reflective_promotion_candidate(value: object) -> ReflectivePromotionCandidate | None:
    """Normalize one promotion-candidate payload."""

    if not isinstance(value, dict):
        return None
    statement = _clean_text(value.get("statement"))
    if not statement:
        return None
    target_bucket = _clean_text(value.get("target_bucket")) or "chapter_understandings"
    if target_bucket not in _REFLECTIVE_BUCKETS:
        target_bucket = "chapter_understandings"
    return {
        "candidate_id": _clean_text(value.get("candidate_id")),
        "statement": statement,
        "support_anchor_ids": [
            _clean_text(item)
            for item in value.get("support_anchor_ids", [])
            if _clean_text(item)
        ]
        if isinstance(value.get("support_anchor_ids"), list)
        else [],
        "promoted_from": _clean_text(value.get("promoted_from")) or "chapter_sweep",
        "target_bucket": target_bucket,
        "rationale": _clean_text(value.get("rationale")),
    }


def _normalize_reflective_promotion_result(payload: object) -> ReflectivePromotionResult:
    """Normalize one reflective-promotion node payload."""

    if not isinstance(payload, dict):
        return {
            "decision": "withhold",
            "reason": "",
            "target_bucket": "chapter_understandings",
            "reflective_item": None,
            "supersede_bucket": "",
            "supersede_item_id": "",
            "state_operations": [],
        }

    target_bucket = _clean_text(payload.get("target_bucket")) or "chapter_understandings"
    if target_bucket not in _REFLECTIVE_BUCKETS:
        target_bucket = "chapter_understandings"
    decision = _clean_text(payload.get("decision")).lower()
    if decision not in {"promote", "withhold"}:
        decision = "withhold"
    reflective_item = _normalize_reflective_item(payload.get("reflective_item"), chapter_ref=_clean_text(payload.get("chapter_ref")))
    if decision == "promote" and reflective_item is None:
        decision = "withhold"
    supersede_bucket = _clean_text(payload.get("supersede_bucket"))
    if supersede_bucket and supersede_bucket not in _REFLECTIVE_BUCKETS:
        supersede_bucket = ""
    return {
        "decision": decision,  # type: ignore[typeddict-item]
        "reason": _clean_text(payload.get("reason")),
        "target_bucket": target_bucket,
        "reflective_item": reflective_item,
        "supersede_bucket": supersede_bucket,
        "supersede_item_id": _clean_text(payload.get("supersede_item_id")),
        "state_operations": _normalize_state_operations(payload.get("state_operations")),
    }


def reflective_promotion(
    *,
    candidate: ReflectivePromotionCandidate,
    current_reflective_state: ReflectiveFramesState,
    policy_snapshot: ReaderPolicy,
    output_language: str,
    chapter_ref: str,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
) -> ReflectivePromotionResult:
    """Run the reflective-promotion node."""

    prompts = ATTENTIONAL_V2_PROMPTS
    structural_frame = _structural_frame(
        book_title=book_title,
        author=author,
        chapter_title=chapter_title,
        output_language=output_language,
    )
    user_prompt = _render_prompt(
        prompts.reflective_promotion_prompt,
        structural_frame=_json_block(structural_frame),
        candidate=_json_block(candidate),
        current_reflective_state=_json_block(current_reflective_state),
        policy_snapshot=_json_block(policy_snapshot),
        output_language_name=language_name(output_language),
        chapter_ref=chapter_ref,
    )
    _write_prompt_manifest(
        output_dir,
        node_name="reflective_promotion",
        prompt_version=prompts.reflective_promotion_version,
        system_prompt=prompts.reflective_promotion_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )
    with llm_invocation_scope(
        trace_context=LLMTraceContext(stage="phase6", node="reflective_promotion")
    ):
        payload = invoke_json(prompts.reflective_promotion_system, user_prompt, default={})
    normalized = _normalize_reflective_promotion_result(payload)
    if normalized.get("reflective_item"):
        normalized["reflective_item"]["chapter_ref"] = chapter_ref
    return normalized


def apply_reflective_promotion(
    state: ReflectiveFramesState,
    result: ReflectivePromotionResult,
) -> ReflectiveFramesState:
    """Apply one normalized reflective-promotion result."""

    if str(result.get("decision", "") or "") != "promote":
        return state

    reflective_item = result.get("reflective_item")
    if not isinstance(reflective_item, dict):
        return state

    next_state = state
    supersede_bucket = _clean_text(result.get("supersede_bucket"))
    supersede_item_id = _clean_text(result.get("supersede_item_id"))
    if supersede_bucket and supersede_item_id:
        next_state = supersede_reflective_item(
            next_state,
            bucket=supersede_bucket,  # type: ignore[arg-type]
            item_id=supersede_item_id,
            superseded_by_item_id=_clean_text(reflective_item.get("item_id")),
        )
    target_bucket = _clean_text(result.get("target_bucket")) or "chapter_understandings"
    if target_bucket not in _REFLECTIVE_BUCKETS:
        target_bucket = "chapter_understandings"
    return upsert_reflective_item(
        next_state,
        bucket=target_bucket,  # type: ignore[arg-type]
        item=reflective_item,
    )


def _normalize_reconsolidation_record(
    payload: object,
    *,
    prior_reaction_id: str,
    new_reaction_id: str,
) -> ReconsolidationRecord | None:
    """Normalize one reconsolidation-record payload."""

    if not isinstance(payload, dict):
        return None
    change_kind = _clean_text(payload.get("change_kind"))
    what_changed = _clean_text(payload.get("what_changed"))
    rationale = _clean_text(payload.get("rationale"))
    if not any([change_kind, what_changed, rationale]):
        return None
    return {
        "record_id": _clean_text(payload.get("record_id")),
        "prior_reaction_id": prior_reaction_id,
        "new_reaction_id": new_reaction_id,
        "change_kind": change_kind or "reframed",
        "what_changed": what_changed,
        "rationale": rationale,
        "created_at": _timestamp(),
    }


def reconsolidation(
    *,
    earlier_reaction: AnchoredReactionRecord,
    earlier_anchor_context: list[dict[str, object]],
    later_anchor: AnchorRecord | dict[str, object],
    current_understanding_snapshot: dict[str, object],
    policy_snapshot: ReaderPolicy,
    output_language: str,
    chapter_id: int,
    chapter_ref: str,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
) -> ReconsolidationResult:
    """Run the reconsolidation node for one material later reinterpretation."""

    prompts = ATTENTIONAL_V2_PROMPTS
    structural_frame = _structural_frame(
        book_title=book_title,
        author=author,
        chapter_title=chapter_title,
        output_language=output_language,
    )
    later_anchor_payload = build_reaction_anchor(later_anchor)
    user_prompt = _render_prompt(
        prompts.reconsolidation_prompt,
        structural_frame=_json_block(structural_frame),
        earlier_reaction=_json_block(earlier_reaction),
        earlier_anchor_context=_json_block(earlier_anchor_context),
        later_anchor=_json_block(later_anchor_payload),
        current_understanding_snapshot=_json_block(current_understanding_snapshot),
        policy_snapshot=_json_block(policy_snapshot),
        output_language_name=language_name(output_language),
    )
    _write_prompt_manifest(
        output_dir,
        node_name="reconsolidation",
        prompt_version=prompts.reconsolidation_version,
        system_prompt=prompts.reconsolidation_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )
    with llm_invocation_scope(
        trace_context=LLMTraceContext(stage="phase6", node="reconsolidation")
    ):
        payload = invoke_json(prompts.reconsolidation_system, user_prompt, default={})
    if not isinstance(payload, dict):
        return {
            "decision": "keep_prior",
            "reason": "",
            "reconsolidation_record": None,
            "later_reaction": None,
            "state_updates": [],
        }

    decision = _clean_text(payload.get("decision")).lower()
    if decision not in {"reconsolidate", "keep_prior"}:
        decision = "keep_prior"

    later_candidate = _normalize_reaction_candidate(payload.get("later_reaction"))
    emitted_at_sentence_id = _clean_text(later_anchor_payload.get("sentence_end_id") or later_anchor_payload.get("sentence_start_id"))
    later_reaction: AnchoredReactionRecord | None = None
    reconsolidation_record: ReconsolidationRecord | None = None
    if decision == "reconsolidate" and later_candidate is not None and emitted_at_sentence_id:
        later_reaction_family = compat_reaction_family(later_candidate)
        new_reaction_id = derive_reaction_id(
            chapter_ref=chapter_ref,
            emitted_at_sentence_id=emitted_at_sentence_id,
            reaction_type=later_reaction_family,
        )
        raw_record = _normalize_reconsolidation_record(
            payload.get("reconsolidation_record"),
            prior_reaction_id=_clean_text(earlier_reaction.get("reaction_id")),
            new_reaction_id=new_reaction_id,
        )
        record_id = (
            _clean_text((raw_record or {}).get("record_id"))
            or derive_reconsolidation_record_id(
                prior_reaction_id=_clean_text(earlier_reaction.get("reaction_id")),
                later_sentence_id=emitted_at_sentence_id,
            )
        )
        later_reaction = build_reaction_record(
            reaction=later_candidate,
            primary_anchor=later_anchor,
            chapter_id=chapter_id,
            chapter_ref=chapter_ref,
            emitted_at_sentence_id=emitted_at_sentence_id,
            reconsolidation_record_id=record_id,
            supersedes_reaction_id=_clean_text(earlier_reaction.get("reaction_id")),
            compatibility_section_ref=_compatibility_section_ref(
                {"primary_anchor": later_anchor_payload},
                chapter_id=chapter_id,
            ),
        )
        reconsolidation_record = {
            **(raw_record or {}),
            "record_id": record_id,
            "prior_reaction_id": _clean_text(earlier_reaction.get("reaction_id")),
            "new_reaction_id": _clean_text(later_reaction.get("reaction_id")),
            "change_kind": _clean_text((raw_record or {}).get("change_kind")) or "reframed",
            "what_changed": _clean_text((raw_record or {}).get("what_changed")),
            "rationale": _clean_text((raw_record or {}).get("rationale")),
            "created_at": _timestamp(),
        }
    else:
        decision = "keep_prior"

    return {
        "decision": decision,  # type: ignore[typeddict-item]
        "reason": _clean_text(payload.get("reason")),
        "reconsolidation_record": reconsolidation_record,
        "later_reaction": later_reaction,
        "state_updates": _normalize_state_operations(payload.get("state_updates")),
    }


def apply_reconsolidation(
    reaction_records: ReactionRecordsState,
    reconsolidation_records: ReconsolidationRecordsState,
    result: ReconsolidationResult,
) -> tuple[ReactionRecordsState, ReconsolidationRecordsState]:
    """Persist one normalized reconsolidation result."""

    if str(result.get("decision", "") or "") != "reconsolidate":
        return reaction_records, reconsolidation_records

    later_reaction = result.get("later_reaction")
    reconsolidation_record = result.get("reconsolidation_record")
    if not isinstance(later_reaction, dict) or not isinstance(reconsolidation_record, dict):
        return reaction_records, reconsolidation_records

    return (
        append_reaction_record(reaction_records, later_reaction),
        append_reconsolidation_record(reconsolidation_records, reconsolidation_record),
    )


def _normalize_carry_forward_item(value: object) -> WorkingPressureItem | None:
    """Normalize one carry-forward pressure item."""

    if not isinstance(value, dict):
        return None
    statement = _clean_text(value.get("statement"))
    if not statement:
        return None
    bucket = _clean_text(value.get("bucket"))
    if bucket not in _PRESSURE_BUCKETS:
        kind = _clean_text(value.get("kind")).lower()
        if "question" in kind:
            bucket = "local_questions"
        elif "motif" in kind or "theme" in kind:
            bucket = "local_motifs"
        elif "tension" in kind or "ambigu" in kind or "contradiction" in kind:
            bucket = "local_tensions"
        else:
            bucket = "local_hypotheses"
    return {
        "item_id": _clean_text(value.get("item_id")),
        "bucket": bucket,
        "kind": _clean_text(value.get("kind")) or bucket.removeprefix("local_"),
        "statement": statement,
        "support_anchor_ids": [
            _clean_text(item)
            for item in value.get("support_anchor_ids", [])
            if _clean_text(item)
        ]
        if isinstance(value.get("support_anchor_ids"), list)
        else [],
        "status": _clean_text(value.get("status")) or "open",
    }


def _normalize_anchor_status_updates(value: object) -> list[dict[str, object]]:
    """Normalize chapter-end anchor status updates."""

    updates: list[dict[str, object]] = []
    if not isinstance(value, list):
        return updates
    for item in value:
        if not isinstance(item, dict):
            continue
        anchor_id = _clean_text(item.get("anchor_id"))
        if not anchor_id:
            continue
        updates.append(
            {
                "anchor_id": anchor_id,
                "status": _clean_text(item.get("status")) or "retained",
                "why_it_mattered": _clean_text(item.get("why_it_mattered")),
            }
        )
    return updates


def _normalize_chapter_consolidation_result(payload: object) -> ChapterConsolidationResult:
    """Normalize one chapter-consolidation node payload."""

    if not isinstance(payload, dict):
        return {
            "chapter_ref": "",
            "backward_sweep": [],
            "cooling_operations": [],
            "promotion_candidates": [],
            "anchor_status_updates": [],
            "knowledge_activation_updates": [],
            "cross_chapter_carry_forward": [],
            "chapter_summary_note": "",
            "optional_chapter_reaction": None,
        }

    carry_forward = [
        item
        for item in (_normalize_carry_forward_item(entry) for entry in payload.get("cross_chapter_carry_forward", []))
        if item is not None
    ]
    promotion_candidates = [
        item
        for item in (_normalize_reflective_promotion_candidate(entry) for entry in payload.get("promotion_candidates", []))
        if item is not None
    ]
    return {
        "chapter_ref": _clean_text(payload.get("chapter_ref")),
        "backward_sweep": list(payload.get("backward_sweep", [])) if isinstance(payload.get("backward_sweep"), list) else [],
        "cooling_operations": _normalize_state_operations(payload.get("cooling_operations")),
        "promotion_candidates": promotion_candidates,
        "anchor_status_updates": _normalize_anchor_status_updates(payload.get("anchor_status_updates")),
        "knowledge_activation_updates": _normalize_state_operations(payload.get("knowledge_activation_updates")),
        "cross_chapter_carry_forward": carry_forward,
        "chapter_summary_note": _clean_text(payload.get("chapter_summary_note")),
        "optional_chapter_reaction": _normalize_reaction_candidate(payload.get("optional_chapter_reaction")),
    }


def chapter_consolidation(
    *,
    chapter_ref: str,
    meaning_units_in_chapter: list[dict[str, object]],
    working_state_snapshot: WorkingState,
    anchor_bank_chapter_slice: list[dict[str, object]],
    reflective_frames_snapshot: ReflectiveFramesState,
    knowledge_activations_snapshot: KnowledgeActivationsState,
    persisted_reactions_in_chapter: list[AnchoredReactionRecord],
    policy_snapshot: ReaderPolicy,
    output_language: str,
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
) -> ChapterConsolidationResult:
    """Run the chapter-consolidation node."""

    prompts = ATTENTIONAL_V2_PROMPTS
    structural_frame = _structural_frame(
        book_title=book_title,
        author=author,
        chapter_title=chapter_title,
        output_language=output_language,
    )
    user_prompt = _render_prompt(
        prompts.chapter_consolidation_prompt,
        structural_frame=_json_block(structural_frame),
        chapter_ref=chapter_ref,
        meaning_units_in_chapter=_json_block(meaning_units_in_chapter),
        working_state_snapshot=_json_block(working_state_snapshot),
        anchor_bank_chapter_slice=_json_block(anchor_bank_chapter_slice),
        reflective_frames_snapshot=_json_block(reflective_frames_snapshot),
        knowledge_activations_snapshot=_json_block(knowledge_activations_snapshot),
        persisted_reactions_in_chapter=_json_block(persisted_reactions_in_chapter),
        policy_snapshot=_json_block(policy_snapshot),
        output_language_name=language_name(output_language),
    )
    _write_prompt_manifest(
        output_dir,
        node_name="chapter_consolidation",
        prompt_version=prompts.chapter_consolidation_version,
        system_prompt=prompts.chapter_consolidation_system,
        user_prompt=user_prompt,
        promptset_version=prompts.promptset_version,
    )
    with llm_invocation_scope(
        trace_context=LLMTraceContext(stage="phase6", node="chapter_consolidation")
    ):
        payload = invoke_json(prompts.chapter_consolidation_system, user_prompt, default={})
    normalized = _normalize_chapter_consolidation_result(payload)
    if not normalized.get("chapter_ref"):
        normalized["chapter_ref"] = chapter_ref
    return normalized


def apply_anchor_status_updates(
    anchor_bank: AnchorBankState,
    updates: list[dict[str, object]],
) -> AnchorBankState:
    """Apply chapter-end status updates to retained anchors."""

    next_state = anchor_bank
    anchors_by_id = {
        _clean_text(anchor.get("anchor_id")): dict(anchor)
        for anchor in anchor_bank.get("anchor_records", [])
        if isinstance(anchor, dict) and _clean_text(anchor.get("anchor_id"))
    }
    for update in updates:
        anchor_id = _clean_text(update.get("anchor_id"))
        if not anchor_id or anchor_id not in anchors_by_id:
            continue
        anchor = anchors_by_id[anchor_id]
        updated_anchor = {
            **anchor,
            "status": _clean_text(update.get("status")) or str(anchor.get("status", "") or "retained"),
            "why_it_mattered": _clean_text(update.get("why_it_mattered")) or str(anchor.get("why_it_mattered", "") or ""),
        }
        next_state = upsert_anchor_record(next_state, updated_anchor)
        anchors_by_id[anchor_id] = updated_anchor
    return next_state


def apply_cross_chapter_carry_forward(
    working_state: WorkingState,
    carry_forward: list[WorkingPressureItem],
) -> WorkingState:
    """Cool local pressure into a chapter-boundary carry-forward state."""

    next_state = working_state
    for bucket in _PRESSURE_BUCKETS:
        next_state = replace_pressure_bucket(next_state, bucket=bucket, items=[])
    bucketed: dict[str, list[WorkingPressureItem]] = defaultdict(list)
    for item in carry_forward:
        bucket = _clean_text(item.get("bucket")) or "local_hypotheses"
        if bucket not in _PRESSURE_BUCKETS:
            bucket = "local_hypotheses"
        bucketed[bucket].append(dict(item))
    for bucket, items in bucketed.items():
        next_state = replace_pressure_bucket(next_state, bucket=bucket, items=items)
    return set_gate_state(next_state, "watch" if carry_forward else "quiet")


def run_phase6_chapter_cycle(
    *,
    book_id: str,
    chapter: BookChapter | dict[str, object],
    meaning_units_in_chapter: list[dict[str, object]],
    chapter_end_anchor: AnchorRecord | dict[str, object],
    working_state: WorkingState,
    concept_registry: ConceptRegistryState,
    thread_trace: ThreadTraceState,
    reflective_frames: ReflectiveFramesState,
    anchor_bank: AnchorBankState,
    knowledge_activations: KnowledgeActivationsState,
    reaction_records: ReactionRecordsState,
    reader_policy: ReaderPolicy,
    output_language: str,
    output_dir: Path | None = None,
    persist_compatibility_projection: bool = False,
    book_title: str = "",
    author: str = "",
) -> dict[str, object]:
    """Run one chapter-end slow-cycle pass and return updated Phase 6 state."""

    chapter_ref = _clean_text(chapter.get("reference") or chapter.get("chapter_ref") or f"Chapter {int(chapter.get('id', 0) or 0)}")
    chapter_title = _clean_text(chapter.get("title"))
    persisted_reactions = reaction_records_for_chapter(reaction_records, chapter_ref=chapter_ref)
    chapter_anchor_ids = {
        _clean_text(record.get("primary_anchor", {}).get("anchor_id"))
        for record in persisted_reactions
        if isinstance(record.get("primary_anchor"), dict)
    }
    anchor_bank_chapter_slice = [
        dict(anchor)
        for anchor in anchor_bank.get("anchor_records", [])
        if isinstance(anchor, dict) and _clean_text(anchor.get("anchor_id")) in chapter_anchor_ids
    ]
    consolidation = chapter_consolidation(
        chapter_ref=chapter_ref,
        meaning_units_in_chapter=meaning_units_in_chapter,
        working_state_snapshot=working_state,
        anchor_bank_chapter_slice=anchor_bank_chapter_slice,
        reflective_frames_snapshot=reflective_frames,
        knowledge_activations_snapshot=knowledge_activations,
        persisted_reactions_in_chapter=persisted_reactions,
        policy_snapshot=reader_policy,
        output_language=output_language,
        output_dir=output_dir,
        book_title=book_title,
        author=author,
        chapter_title=chapter_title,
    )

    next_working_state = apply_working_state_operations(working_state, consolidation.get("cooling_operations", []))
    next_working_state = apply_cross_chapter_carry_forward(
        next_working_state,
        consolidation.get("cross_chapter_carry_forward", []),
    )
    next_anchor_bank = apply_anchor_status_updates(
        anchor_bank,
        consolidation.get("anchor_status_updates", []),
    )
    end_sentence_id = _clean_text(
        chapter_end_anchor.get("sentence_end_id") or chapter_end_anchor.get("sentence_start_id")
    )
    next_knowledge_activations = apply_activation_operations(
        knowledge_activations,
        consolidation.get("knowledge_activation_updates", []),
        current_sentence_id=end_sentence_id or _clean_text(chapter_end_anchor.get("sentence_start_id")) or "chapter-end",
        reader_policy=reader_policy,
    )

    next_reflective_frames = reflective_frames
    promotion_results: list[ReflectivePromotionResult] = []
    for candidate in consolidation.get("promotion_candidates", []):
        promotion_result = reflective_promotion(
            candidate=candidate,
            current_reflective_state=next_reflective_frames,
            policy_snapshot=reader_policy,
            output_language=output_language,
            chapter_ref=chapter_ref,
            output_dir=output_dir,
            book_title=book_title,
            author=author,
            chapter_title=chapter_title,
        )
        promotion_results.append(promotion_result)
        next_reflective_frames = apply_reflective_promotion(next_reflective_frames, promotion_result)

    next_reaction_records = reaction_records
    optional_reaction = consolidation.get("optional_chapter_reaction")
    if isinstance(optional_reaction, dict):
        next_reaction_records = append_reaction_record(
            next_reaction_records,
            build_reaction_record(
                reaction=optional_reaction,
                primary_anchor=chapter_end_anchor,
                chapter_id=int(chapter.get("id", 0) or 0),
                chapter_ref=chapter_ref,
                emitted_at_sentence_id=end_sentence_id or "chapter-end",
                compatibility_section_ref=_compatibility_section_ref(
                    {"primary_anchor": build_reaction_anchor(chapter_end_anchor)},
                    chapter_id=int(chapter.get("id", 0) or 0),
                ),
                ordinal=len(persisted_reactions) + 1,
            ),
        )

    compatibility_payload = project_chapter_result_compatibility(
        book_id=book_id,
        chapter=chapter,
        reaction_records=next_reaction_records,
        output_language=output_language,
        output_dir=output_dir,
        persist=persist_compatibility_projection,
    )

    return {
        "chapter_consolidation": consolidation,
        "promotion_results": promotion_results,
        "working_state": next_working_state,
        "concept_registry": concept_registry,
        "thread_trace": thread_trace,
        "anchor_bank": next_anchor_bank,
        "reflective_frames": next_reflective_frames,
        "knowledge_activations": next_knowledge_activations,
        "reaction_records": next_reaction_records,
        "compatibility_payload": compatibility_payload,
    }
