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
    CarryForwardContext,
    AnchorFocus,
    AnchorRelationAssessment,
    BridgeCandidate,
    ClosureDecision,
    ContextRequest,
    ControllerDecisionResult,
    GateState,
    KnowledgeActivationsState,
    MeaningUnitClosureResult,
    MoveType,
    NavigateRouteDecision,
    PriorMaterialUse,
    PreviewRange,
    ReactionCandidate,
    ReactionEmissionDecision,
    ReactionEmissionResult,
    ReactionType,
    ReadAnchorEvidence,
    ReadUnitResult,
    ReaderPolicy,
    StateOperation,
    TriggerState,
    UnitizeBoundaryType,
    UnitizeDecision,
    WorkingPressureState,
    ZoomReadResult,
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
_CONTEXT_REQUEST_KINDS = {"active_recall", "look_back"}
_UNITIZE_BOUNDARY_TYPES: set[UnitizeBoundaryType] = {
    "paragraph_end",
    "intra_paragraph_semantic_close",
    "cross_paragraph_continuation",
    "section_end",
    "budget_cap",
}
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
_ANCHOR_FOCUS_KINDS = {"phrase", "sentence", "span"}
_ANCHOR_RELATION_STATUSES = {"anchored", "related_but_unresolved", "unclear"}
_SYNTHETIC_REACTION_CUE_TYPES = {
    "marked_phrase",
    "loaded_wording",
    "analogy_image",
    "distinction_cue",
    "actor_intention",
    "social_pressure",
    "causal_stakes",
}
_SHARP_LOCAL_FOCUS_CUE_TYPES = {
    "callback_cue",
    "distinction_cue",
    "marked_phrase",
    "loaded_wording",
    "analogy_image",
}
_SHARP_LOCAL_TRIGGER_SIGNAL_KINDS = {
    "callback_activation",
    "definition_or_distinction",
    "discourse_turn",
    "sentence_role_shift",
}
_NARROW_TAIL_FORCE_CLOSE_CADENCE = 8
_CALLBACK_MARKERS = (
    "as noted earlier",
    "as mentioned earlier",
    "earlier example",
    "since that day",
    "from that day",
    "when they were young",
    "earlier",
    "previously",
    "remember",
    "recall",
    "above",
    "當年",
    "当年",
    "自從",
    "自从",
    "那日",
    "前面",
    "前文",
    "上文",
    "之前",
    "此前",
    "前述",
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


def _cue_types(local_textual_cues: list[dict[str, str]]) -> set[str]:
    """Return the distinct cue types present in one local cue packet."""

    return {
        _clean_text(cue.get("cue_type"))
        for cue in local_textual_cues
        if isinstance(cue, dict) and _clean_text(cue.get("cue_type"))
    }


def _trigger_signal_kinds(trigger_state: TriggerState) -> set[str]:
    """Return the distinct trigger signal kinds present on the current reading moment."""

    return {
        _clean_text(signal.get("signal_kind"))
        for signal in trigger_state.get("signals", [])
        if isinstance(signal, dict) and _clean_text(signal.get("signal_kind"))
    }


def select_local_cycle_span(
    *,
    current_span_sentences: list[dict[str, object]],
    trigger_state: TriggerState,
    max_focus_sentences: int = 3,
) -> list[dict[str, object]]:
    """Return the span that the local cycle should actually reason over.

    When a long open meaning unit contains one sharp late-local hinge, we narrow the
    analysis span to the tail window so the hinge does not get swallowed back into a
    much broader local accumulation.
    """

    if len(current_span_sentences) <= max(1, int(max_focus_sentences)):
        return current_span_sentences
    tail_span = current_span_sentences[-max(1, int(max_focus_sentences)) :]
    tail_cues = _local_textual_cues(tail_span)
    if _cue_types(tail_cues) & _SHARP_LOCAL_FOCUS_CUE_TYPES:
        return tail_span
    if _trigger_signal_kinds(trigger_state) & _SHARP_LOCAL_TRIGGER_SIGNAL_KINDS:
        return tail_span
    return current_span_sentences


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


def _build_anchor_focus(
    *,
    anchor_quote: str,
    fallback_sentence: dict[str, object],
    current_span_sentences: list[dict[str, object]] | None = None,
    source: str,
) -> AnchorFocus | None:
    """Build a compact local-focus packet that later nodes can stay answerable to."""

    cleaned_anchor = _clean_text(anchor_quote)
    span = current_span_sentences or [fallback_sentence]
    focus_sentence = _find_sentence_for_anchor_quote(span, anchor_quote=cleaned_anchor) or fallback_sentence
    focus_text = _clean_text(focus_sentence.get("text"))
    if not cleaned_anchor:
        cleaned_anchor = focus_text[:180]
    if not cleaned_anchor:
        return None
    focus_kind = "phrase"
    if cleaned_anchor == focus_text:
        focus_kind = "sentence"
    return {
        "anchor_quote": cleaned_anchor,
        "focus_sentence_id": _clean_text(focus_sentence.get("sentence_id")),
        "focus_kind": focus_kind,
        "source": source,
    }


def _anchor_backcheck_window(
    current_span_sentences: list[dict[str, object]],
    *,
    anchor_focus: AnchorFocus | None,
) -> list[dict[str, object]]:
    """Return a tiny local re-check window around the active local hinge."""

    if not current_span_sentences:
        return []
    focus_sentence_id = _clean_text((anchor_focus or {}).get("focus_sentence_id"))
    focus_index = len(current_span_sentences) - 1
    if focus_sentence_id:
        for index, sentence in enumerate(current_span_sentences):
            if _clean_text(sentence.get("sentence_id")) == focus_sentence_id:
                focus_index = index
                break
    start = max(0, focus_index - 1)
    end = min(len(current_span_sentences), focus_index + 2)
    return [
        {
            "sentence_id": _clean_text(sentence.get("sentence_id")),
            "text": _clean_text(sentence.get("text")),
            "text_role": _clean_text(sentence.get("text_role")),
        }
        for sentence in current_span_sentences[start:end]
    ]


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


def _normalize_anchor_focus(value: object, *, fallback: AnchorFocus | None = None) -> AnchorFocus | None:
    """Normalize one local-focus packet, falling back to the deterministic packet when needed."""

    if not isinstance(value, dict):
        return fallback
    anchor_quote = _clean_text(value.get("anchor_quote")) or _clean_text((fallback or {}).get("anchor_quote"))
    focus_sentence_id = _clean_text(value.get("focus_sentence_id")) or _clean_text((fallback or {}).get("focus_sentence_id"))
    focus_kind = _clean_text(value.get("focus_kind")) or _clean_text((fallback or {}).get("focus_kind")) or "phrase"
    if focus_kind not in _ANCHOR_FOCUS_KINDS:
        focus_kind = _clean_text((fallback or {}).get("focus_kind")) or "phrase"
    source = _clean_text(value.get("source")) or _clean_text((fallback or {}).get("source")) or "zoom_anchor"
    if not anchor_quote:
        return fallback
    return {
        "anchor_quote": anchor_quote,
        "focus_sentence_id": focus_sentence_id,
        "focus_kind": focus_kind,
        "source": source,
    }


def _normalize_anchor_relation(value: object, *, anchor_focus: AnchorFocus | None) -> AnchorRelationAssessment | None:
    """Normalize one closure-time relation-to-anchor assessment."""

    if not isinstance(value, dict):
        return None
    relation_status = _clean_text(value.get("relation_status")) or "unclear"
    if relation_status not in _ANCHOR_RELATION_STATUSES:
        relation_status = "unclear"
    current_focus_quote = _clean_text(value.get("current_focus_quote")) or _clean_text((anchor_focus or {}).get("anchor_quote"))
    relation_to_focus = _clean_text(value.get("relation_to_focus"))
    same_chapter_pressure_only = bool(value.get("same_chapter_pressure_only"))
    local_backcheck_used = bool(value.get("local_backcheck_used"))
    can_emit_visible_reaction = bool(value.get("can_emit_visible_reaction"))
    if relation_status != "anchored":
        can_emit_visible_reaction = False
    if not current_focus_quote and anchor_focus is None:
        return None
    return {
        "relation_status": relation_status,
        "relation_to_focus": relation_to_focus,
        "current_focus_quote": current_focus_quote,
        "same_chapter_pressure_only": same_chapter_pressure_only,
        "local_backcheck_used": local_backcheck_used,
        "can_emit_visible_reaction": can_emit_visible_reaction,
    }


def _anchor_relation_allows_visible_reaction(anchor_relation: AnchorRelationAssessment | None) -> bool:
    """Return whether the current local reading moment is specific enough to surface visibly."""

    if anchor_relation is None:
        return False
    return (
        _clean_text(anchor_relation.get("relation_status")) == "anchored"
        and bool(anchor_relation.get("can_emit_visible_reaction"))
    )


def _should_hold_local_closure(
    *,
    anchor_relation: AnchorRelationAssessment | None,
    closure_result: MeaningUnitClosureResult,
    current_span_sentences: list[dict[str, object]],
    local_textual_cues: list[dict[str, str]],
) -> bool:
    """Return whether a narrow late-local hinge should stay unresolved for one more local pass."""

    if anchor_relation is None:
        return False
    relation_status = _clean_text(anchor_relation.get("relation_status"))
    if relation_status == "anchored":
        return False
    if len(current_span_sentences) > 3:
        return False
    cue_types = {str(item.get("cue_type", "") or "") for item in local_textual_cues if isinstance(item, dict)}
    if cue_types & {"distinction_cue", "marked_phrase", "loaded_wording", "analogy_image"}:
        return True
    return bool(closure_result.get("reaction_candidate"))


def _should_force_close_local_hinge(
    *,
    anchor_relation: AnchorRelationAssessment | None,
    closure_result: MeaningUnitClosureResult,
    current_span_sentences: list[dict[str, object]],
    local_textual_cues: list[dict[str, str]],
) -> bool:
    """Return whether a bounded local-hinge pass should close instead of re-expanding."""

    if _clean_text(closure_result.get("closure_decision")) == "close":
        return False
    if len(current_span_sentences) > 3:
        return False
    if not _anchor_relation_allows_visible_reaction(anchor_relation):
        return False
    if bool((anchor_relation or {}).get("same_chapter_pressure_only")):
        return False
    cue_types = _cue_types(local_textual_cues)
    if not cue_types & _SHARP_LOCAL_FOCUS_CUE_TYPES:
        return False
    return bool(_clean_text(closure_result.get("meaning_unit_summary")) or closure_result.get("reaction_candidate"))


def _should_force_close_overlong_narrow_tail(
    *,
    boundary_context: dict[str, object] | None,
    anchor_relation: AnchorRelationAssessment | None,
    closure_result: MeaningUnitClosureResult,
    local_textual_cues: list[dict[str, str]],
) -> bool:
    """Return whether an overlong narrowed tail should close honestly instead of dragging on."""

    if _clean_text((boundary_context or {}).get("local_cycle_scope")) != "narrow_focus_tail":
        return False
    try:
        cadence_counter = int((boundary_context or {}).get("cadence_counter", 0) or 0)
    except (TypeError, ValueError):
        cadence_counter = 0
    if cadence_counter < _NARROW_TAIL_FORCE_CLOSE_CADENCE:
        return False
    if _clean_text(closure_result.get("closure_decision")) == "close":
        return False
    if _anchor_relation_allows_visible_reaction(anchor_relation):
        return False
    return True


def _micro_selective_reaction_candidate(
    *,
    zoom_result: ZoomReadResult | None,
    closure_result: MeaningUnitClosureResult,
    local_textual_cues: list[dict[str, str]],
    focal_text: str,
) -> ReactionCandidate | None:
    """Build one bounded synthetic local reaction candidate when the phrase-level pressure is clear."""

    if not _anchor_relation_allows_visible_reaction(closure_result.get("anchor_relation")):
        return None
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


def _align_reaction_candidate_to_anchor_focus(
    reaction_candidate: ReactionCandidate | None,
    *,
    anchor_focus: AnchorFocus | None,
) -> ReactionCandidate | None:
    """Keep a visible candidate answerable to the same local focus packet."""

    if reaction_candidate is None:
        return None
    focus_quote = _clean_text((anchor_focus or {}).get("anchor_quote"))
    if not focus_quote:
        return reaction_candidate
    candidate_anchor = _clean_text(reaction_candidate.get("anchor_quote"))
    if candidate_anchor and _quotes_share_local_focus(candidate_anchor, focus_quote):
        return reaction_candidate
    return {
        **reaction_candidate,
        "anchor_quote": focus_quote,
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
        "reason": "unitize_fallback_current_paragraph",
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


def _normalize_read_anchor_evidence(
    value: object,
    *,
    allowed_sentence_ids: set[str],
) -> list[ReadAnchorEvidence]:
    """Normalize one list of read-anchor evidence packets."""

    evidence: list[ReadAnchorEvidence] = []
    if not isinstance(value, list):
        return evidence
    for item in value:
        if not isinstance(item, dict):
            continue
        sentence_id = _clean_text(item.get("sentence_id"))
        quote = _clean_text(item.get("quote"))
        why_it_matters = _clean_text(item.get("why_it_matters"))
        if not sentence_id or sentence_id not in allowed_sentence_ids or not quote:
            continue
        evidence.append(
            {
                "sentence_id": sentence_id,
                "quote": quote,
                "why_it_matters": why_it_matters,
            }
        )
    return evidence


def _normalize_prior_material_use(
    value: object,
    *,
    allowed_ref_ids: set[str],
) -> PriorMaterialUse:
    """Normalize one prior-material-use packet against visible context refs."""

    if not isinstance(value, dict):
        return {
            "materially_used": False,
            "explanation": "",
            "supporting_ref_ids": [],
        }
    materially_used = bool(value.get("materially_used"))
    explanation = _clean_text(value.get("explanation"))
    supporting_ref_ids = [
        ref_id
        for ref_id in (
            _clean_text(item)
            for item in value.get("supporting_ref_ids", [])
            if isinstance(value.get("supporting_ref_ids"), list)
        )
        if ref_id and (not allowed_ref_ids or ref_id in allowed_ref_ids)
    ]
    if not materially_used:
        explanation = ""
        supporting_ref_ids = []
    return {
        "materially_used": materially_used,
        "explanation": explanation,
        "supporting_ref_ids": supporting_ref_ids[:4],
    }


def _normalize_context_request(value: object) -> ContextRequest | None:
    """Normalize one bounded supplemental-context request."""

    if not isinstance(value, dict):
        return None
    kind = _clean_text(value.get("kind")).lower().replace("-", "_")
    if kind not in _CONTEXT_REQUEST_KINDS:
        return None
    return {
        "kind": kind,  # type: ignore[typeddict-item]
        "reason": _clean_text(value.get("reason")),
        "anchor_ids": [
            _clean_text(item)
            for item in value.get("anchor_ids", [])
            if isinstance(value.get("anchor_ids"), list) and _clean_text(item)
        ][:4],
        "sentence_ids": [
            _clean_text(item)
            for item in value.get("sentence_ids", [])
            if isinstance(value.get("sentence_ids"), list) and _clean_text(item)
        ][:4],
    }


def _fallback_read_unit_result(
    *,
    current_unit_sentences: list[dict[str, object]],
    continuation_pressure: bool = False,
    reason: str = "",
) -> ReadUnitResult:
    """Return one conservative fallback read result."""

    fallback_sentence = current_unit_sentences[-1] if current_unit_sentences else {}
    sentence_id = _clean_text(fallback_sentence.get("sentence_id"))
    sentence_text = _clean_text(fallback_sentence.get("text"))
    anchor_evidence = (
        [
            {
                "sentence_id": sentence_id,
                "quote": sentence_text[:240],
                "why_it_matters": reason or "read_unit_fallback",
            }
        ]
        if sentence_id and sentence_text
        else []
    )
    return {
        "local_understanding": "",
        "move_hint": "advance",
        "continuation_pressure": bool(continuation_pressure),
        "implicit_uptake": [],
        "anchor_evidence": anchor_evidence,
        "prior_material_use": {
            "materially_used": False,
            "explanation": "",
            "supporting_ref_ids": [],
        },
        "raw_reaction": None,
        "context_request": None,
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
    local_textual_cues: list[dict[str, str]] | None = None,
) -> bool:
    """Return whether the current local moment warrants deterministic bridge retrieval."""

    callback_anchor_ids = [
        _clean_text(item)
        for item in (boundary_context or {}).get("callback_anchor_ids", [])
        if _clean_text(item)
    ] if isinstance((boundary_context or {}).get("callback_anchor_ids"), list) else []
    cue_types = _cue_types(local_textual_cues or [])
    return any(
        (
            bool(callback_anchor_ids),
            bool((zoom_result or {}).get("bridge_candidate")),
            bool(closure_result.get("bridge_candidates")),
            str(closure_result.get("dominant_move", "") or "") == "bridge",
            "callback_cue" in cue_types,
        )
    )


def navigate_unitize(
    *,
    current_sentence: dict[str, object],
    preview_sentences: list[dict[str, object]],
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
    output_dir: Path | None = None,
    book_title: str = "",
    author: str = "",
    chapter_title: str = "",
) -> ReadUnitResult:
    """Run the authoritative formal read for one chosen unit."""

    prompts = ATTENTIONAL_V2_PROMPTS
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
        carry_forward_context=_json_block(carry_forward_context),
        supplemental_context=_json_block(dict(supplemental_context or {})),
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

    allowed_sentence_ids = {
        _clean_text(sentence.get("sentence_id"))
        for sentence in current_unit_sentences
        if _clean_text(sentence.get("sentence_id"))
    }
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

    move_hint = _clean_text(payload.get("move_hint") if isinstance(payload, dict) else "").lower().replace("-", "_")
    if move_hint not in _MOVE_TYPES:
        move_hint = "advance"
    anchor_evidence = _normalize_read_anchor_evidence(
        payload.get("anchor_evidence") if isinstance(payload, dict) else None,
        allowed_sentence_ids=allowed_sentence_ids,
    )
    raw_reaction = _normalize_reaction_candidate(payload.get("raw_reaction")) if isinstance(payload, dict) else None
    if not anchor_evidence and raw_reaction is not None:
        raw_anchor_quote = _clean_text(raw_reaction.get("anchor_quote"))
        for sentence in current_unit_sentences:
            sentence_id = _clean_text(sentence.get("sentence_id"))
            sentence_text = _clean_text(sentence.get("text"))
            if raw_anchor_quote and sentence_id and raw_anchor_quote in sentence_text:
                anchor_evidence = [
                    {
                        "sentence_id": sentence_id,
                        "quote": raw_anchor_quote,
                        "why_it_matters": _clean_text(payload.get("local_understanding")) if isinstance(payload, dict) else "",
                    }
                ]
                break
    result: ReadUnitResult = {
        "local_understanding": _clean_text(payload.get("local_understanding")) if isinstance(payload, dict) else "",
        "move_hint": move_hint,  # type: ignore[typeddict-item]
        "continuation_pressure": bool(payload.get("continuation_pressure")) if isinstance(payload, dict) else False,
        "implicit_uptake": _normalize_state_operations(payload.get("implicit_uptake")) if isinstance(payload, dict) else [],
        "anchor_evidence": anchor_evidence,
        "prior_material_use": _normalize_prior_material_use(
            payload.get("prior_material_use") if isinstance(payload, dict) else None,
            allowed_ref_ids=allowed_ref_ids,
        ),
        "raw_reaction": raw_reaction,
        "context_request": _normalize_context_request(payload.get("context_request")) if isinstance(payload, dict) else None,
    }
    return result


def navigate_route(
    *,
    read_result: ReadUnitResult,
) -> NavigateRouteDecision:
    """Normalize the next-step route from the authoritative read packet."""

    move_hint = _clean_text(read_result.get("move_hint")).lower().replace("-", "_")
    action = "commit"
    if move_hint == "bridge":
        action = "bridge_back"
    elif move_hint == "reframe":
        action = "reframe"
    elif bool(read_result.get("continuation_pressure")):
        action = "continue"
    if action not in _ROUTE_ACTIONS:
        action = "commit"
    prior_material_use = dict(read_result.get("prior_material_use") or {})
    target_anchor_id, target_sentence_id = _route_targets_from_ref_ids(
        [
            _clean_text(ref_id)
            for ref_id in prior_material_use.get("supporting_ref_ids", [])
            if isinstance(prior_material_use.get("supporting_ref_ids"), list) and _clean_text(ref_id)
        ]
    )
    return {
        "action": action,  # type: ignore[typeddict-item]
        "reason": _clean_text(prior_material_use.get("explanation")) or _clean_text(read_result.get("local_understanding")),
        "close_current_unit": True,
        "target_anchor_id": target_anchor_id,
        "target_sentence_id": target_sentence_id,
        "persist_raw_reaction": bool(read_result.get("raw_reaction")),
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
    anchor_focus = _build_anchor_focus(
        anchor_quote=anchor_quote,
        fallback_sentence=focal_sentence,
        current_span_sentences=[*local_context_sentences, focal_sentence],
        source="zoom_anchor" if anchor_quote else "focal_sentence",
    )
    bridge_candidate = _normalize_bridge_candidate(payload.get("bridge_candidate")) if isinstance(payload, dict) else None
    return {
        "local_interpretation": _clean_text(payload.get("local_interpretation")) if isinstance(payload, dict) else "",
        "anchor_quote": anchor_quote,
        "anchor_focus": anchor_focus,
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
    fallback_anchor_focus = _normalize_anchor_focus(
        (zoom_result or {}).get("anchor_focus"),
        fallback=_build_anchor_focus(
            anchor_quote=_clean_text((zoom_result or {}).get("anchor_quote")),
            fallback_sentence=current_span_sentences[-1] if current_span_sentences else {},
            current_span_sentences=current_span_sentences,
            source="zoom_anchor" if _clean_text((zoom_result or {}).get("anchor_quote")) else "focal_sentence",
        ),
    )
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
        anchor_focus=_json_block(dict(fallback_anchor_focus or {})),
        anchor_backcheck_window=_json_block(
            _anchor_backcheck_window(current_span_sentences, anchor_focus=fallback_anchor_focus)
        ),
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
    anchor_focus = _normalize_anchor_focus(
        payload.get("anchor_focus") if isinstance(payload, dict) else None,
        fallback=fallback_anchor_focus,
    )
    anchor_relation = _normalize_anchor_relation(
        payload.get("anchor_relation") if isinstance(payload, dict) else None,
        anchor_focus=anchor_focus,
    )
    return {
        "closure_decision": closure_decision,  # type: ignore[typeddict-item]
        "meaning_unit_summary": _clean_text(payload.get("meaning_unit_summary")) if isinstance(payload, dict) else "",
        "anchor_focus": anchor_focus,
        "anchor_relation": anchor_relation,
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
            "anchor_focus": _normalize_anchor_focus((zoom_result or {}).get("anchor_focus"), fallback=None),
            "anchor_relation": None,
            "dominant_move": "advance",
            "proposed_state_operations": [],
            "bridge_candidates": [],
            "reaction_candidate": None,
            "unresolved_pressure_note": "meaning_unit_closure_unavailable",
        }
    closure_local_cues = _local_textual_cues(current_span_sentences)
    if _should_force_close_overlong_narrow_tail(
        boundary_context=boundary_context,
        anchor_relation=closure_result.get("anchor_relation"),
        closure_result=closure_result,
        local_textual_cues=closure_local_cues,
    ):
        unresolved_note = _clean_text(closure_result.get("unresolved_pressure_note"))
        closure_result = {
            **closure_result,
            "closure_decision": "close",
            "reaction_candidate": None,
            "unresolved_pressure_note": unresolved_note or "local_focus_did_not_close_before_tail_guardrail",
        }
    elif _should_hold_local_closure(
        anchor_relation=closure_result.get("anchor_relation"),
        closure_result=closure_result,
        current_span_sentences=current_span_sentences,
        local_textual_cues=closure_local_cues,
    ):
        unresolved_note = _clean_text(closure_result.get("unresolved_pressure_note"))
        closure_result = {
            **closure_result,
            "closure_decision": "continue",
            "dominant_move": "dwell",
            "reaction_candidate": None,
            "unresolved_pressure_note": unresolved_note or "local_anchor_backcheck_pending",
        }
    elif not _anchor_relation_allows_visible_reaction(closure_result.get("anchor_relation")):
        closure_result = {
            **closure_result,
            "reaction_candidate": None,
        }
    elif _should_force_close_local_hinge(
        anchor_relation=closure_result.get("anchor_relation"),
        closure_result=closure_result,
        current_span_sentences=current_span_sentences,
        local_textual_cues=closure_local_cues,
    ):
        closure_result = {
            **closure_result,
            "closure_decision": "close",
        }
    lazy_bridge_candidates: list[BridgeCandidate] = []
    if _bridge_pressure_present(
        boundary_context=boundary_context,
        zoom_result=zoom_result,
        closure_result=closure_result,
        local_textual_cues=closure_local_cues,
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
    closure_anchor_focus = _normalize_anchor_focus(
        closure_result.get("anchor_focus"),
        fallback=_normalize_anchor_focus((zoom_result or {}).get("anchor_focus"), fallback=None),
    )
    suggested_reaction = closure_result.get("reaction_candidate")
    compact_local_anchor = bool(
        zoom_result
        and len(current_span_sentences) <= 2
        and _has_compact_local_anchor(
            anchor_quote=_clean_text((zoom_result or {}).get("anchor_quote")),
            focal_text=_clean_text(focal_sentence.get("text")),
        )
    )
    reaction_local_cues = closure_local_cues
    effective_suggested_reaction = suggested_reaction or _micro_selective_reaction_candidate(
        zoom_result=zoom_result,
        closure_result=closure_result,
        local_textual_cues=reaction_local_cues,
        focal_text=_clean_text(focal_sentence.get("text")),
    )
    effective_suggested_reaction = _align_reaction_candidate_to_anchor_focus(
        effective_suggested_reaction,
        anchor_focus=closure_anchor_focus,
    )
    should_consider_reaction = (
        _anchor_relation_allows_visible_reaction(closure_result.get("anchor_relation"))
        and (
        bool(suggested_reaction)
        or bool(
            zoom_result
            and zoom_result.get("consider_reaction_emission")
            and effective_suggested_reaction
        )
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
                    "anchor_focus_quote": _clean_text((closure_anchor_focus or {}).get("anchor_quote")),
                    "anchor_relation_status": _clean_text((closure_result.get("anchor_relation") or {}).get("relation_status")),
                    "anchor_relation_note": _clean_text((closure_result.get("anchor_relation") or {}).get("relation_to_focus")),
                    "same_chapter_pressure_only": bool((closure_result.get("anchor_relation") or {}).get("same_chapter_pressure_only")),
                    "local_cycle_scope": _clean_text((boundary_context or {}).get("local_cycle_scope")),
                },
                output_language=output_language,
                output_dir=output_dir,
            )
            emitted_reaction = reaction_result.get("reaction") if isinstance(reaction_result.get("reaction"), dict) else None
            focus_quote = _clean_text((closure_anchor_focus or {}).get("anchor_quote"))
            emitted_anchor = _clean_text((emitted_reaction or {}).get("anchor_quote"))
            if (
                reaction_result.get("decision") == "emit"
                and focus_quote
                and emitted_anchor
                and not _quotes_share_local_focus(emitted_anchor, focus_quote)
            ):
                reaction_result = {
                    "decision": "withhold",
                    "reason": "reaction_anchor_drifted_from_local_focus",
                    "reaction": None,
                }
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
