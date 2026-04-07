"""Prompt bundle for attentional_v2 Phase 4-6 interpretive nodes."""

from __future__ import annotations

from dataclasses import dataclass

from src.prompts.shared import LANGUAGE_OUTPUT_CONTRACT


ATTENTIONAL_V2_PROMPTSET_VERSION = "attentional_v2-phase6-v7"
ZOOM_READ_PROMPT_VERSION = "attentional_v2.zoom_read.v5"
MEANING_UNIT_CLOSURE_PROMPT_VERSION = "attentional_v2.meaning_unit_closure.v7"
CONTROLLER_DECISION_PROMPT_VERSION = "attentional_v2.controller_decision.v1"
REACTION_EMISSION_PROMPT_VERSION = "attentional_v2.reaction_emission.v5"
BRIDGE_RESOLUTION_PROMPT_VERSION = "attentional_v2.bridge_resolution.v3"
REFLECTIVE_PROMOTION_PROMPT_VERSION = "attentional_v2.reflective_promotion.v1"
RECONSOLIDATION_PROMPT_VERSION = "attentional_v2.reconsolidation.v1"
CHAPTER_CONSOLIDATION_PROMPT_VERSION = "attentional_v2.chapter_consolidation.v2"


@dataclass(frozen=True)
class AttentionalV2PromptSet:
    """Typed prompt bundle for attentional_v2 Phase 4-6 nodes."""

    language_output_contract: str
    promptset_version: str
    zoom_read_version: str
    zoom_read_system: str
    zoom_read_prompt: str
    meaning_unit_closure_version: str
    meaning_unit_closure_system: str
    meaning_unit_closure_prompt: str
    controller_decision_version: str
    controller_decision_system: str
    controller_decision_prompt: str
    reaction_emission_version: str
    reaction_emission_system: str
    reaction_emission_prompt: str
    bridge_resolution_version: str
    bridge_resolution_system: str
    bridge_resolution_prompt: str
    reflective_promotion_version: str
    reflective_promotion_system: str
    reflective_promotion_prompt: str
    reconsolidation_version: str
    reconsolidation_system: str
    reconsolidation_prompt: str
    chapter_consolidation_version: str
    chapter_consolidation_system: str
    chapter_consolidation_prompt: str


ATTENTIONAL_V2_PROMPTS = AttentionalV2PromptSet(
    language_output_contract=LANGUAGE_OUTPUT_CONTRACT,
    promptset_version=ATTENTIONAL_V2_PROMPTSET_VERSION,
    zoom_read_version=ZOOM_READ_PROMPT_VERSION,
    zoom_read_system="""You are the sentence-level zoom node for a text-grounded reading mechanism.

Your job is to examine one locally hot sentence with nearby already-read context.

Rules:
- Stay grounded in the provided sentence and nearby already-read context.
- Do not use future unseen text.
- Do not silently promote local observations into durable summaries.
- If the sentence or nearby context contains an explicit recall cue, prior-time cue, or recognition gap, name that exact cue instead of paraphrasing the scene generically.
- If the local pressure is a live distinction or contrast, state the exact distinction in text terms.
- If a compact analogy, metaphor, marked phrase, or loaded local wording is doing real work, name that exact phrase and why it matters locally.
- If deterministic local cues show actor intention, social pressure, or concrete causal stakes, name that exact local hinge instead of drifting into retrospective summary.
- Set `consider_reaction_emission` to true when the line earns one bounded visible reaction because a local motive, pressure, or stakes hinge is doing real work now.
- Only propose explicit state operations; do not assume hidden state mutation.
- Return JSON only.""",
    zoom_read_prompt="""Structural frame:
{structural_frame}

Focal sentence:
{focal_sentence}

Nearby already-read local context:
{local_context}

Working pressure:
{working_pressure}

Relevant anchors:
{anchor_context}

Live activations:
{activation_context}

Deterministic local textual cues:
{local_textual_cues}

Policy snapshot:
{policy_snapshot}

Output language contract:
"""
    + LANGUAGE_OUTPUT_CONTRACT
    + """

Return JSON:
{
  "local_interpretation": "<brief interpretation>",
  "anchor_quote": "<anchor-worthy phrase or sentence, copied from focal sentence when warranted>",
  "pressure_updates": [
    {
      "operation_type": "update",
      "target_store": "working_pressure",
      "item_id": "<stable or local id>",
      "reason": "<why>",
      "payload": {}
    }
  ],
  "activation_updates": [],
  "bridge_candidate": {
    "target_anchor_id": "<optional anchor id>",
    "target_sentence_id": "<optional sentence id>",
    "relation_type": "echo",
    "why_now": "<why or empty>"
  },
  "consider_reaction_emission": false,
  "uncertainty_note": "<brief note if ambiguity remains>"
}""",
    meaning_unit_closure_version=MEANING_UNIT_CLOSURE_PROMPT_VERSION,
    meaning_unit_closure_system="""You are the meaning-unit closure node for a text-grounded reading mechanism.

Your job is to decide whether the current local span should continue accumulating or close into one real interpretive move.

Rules:
- Closure must be earned, not forced.
- Preserve unresolved pressure when the text is still incomplete.
- Treat `anchor_focus` as the original local hinge that opened this reading moment.
- First decide how the current understanding relates to that local hinge before deciding whether the span is truly closed.
- If `boundary_context.local_cycle_scope` says `narrow_focus_tail`, treat this as a bounded repair pass on one sharp late-local hinge inside a larger open meaning unit.
- In that narrowed mode, either close the exact hinge or honestly keep it unresolved; do not dissolve it back into broad chapter paraphrase.
- Use the tiny `anchor_backcheck_window` only to re-check the local hinge; do not widen into chapter-level thematic summary.
- Close around the sharpest live distinction, callback cue, or explanatory pattern in the current span instead of flattening the span into generic scene summary.
- When deterministic local cues show a callback, recognition gap, or durable pattern, address that cue directly in the summary or unresolved note.
- When deterministic local cues show actor intention, social pressure, or concrete causal stakes, center the summary on that local motive/pressure/stakes hinge rather than broad retrospective framing.
- When deterministic local cues show a compact analogy, marked phrase, or loaded wording, prefer a short locally earned reaction candidate over a broad paraphrase.
- When a narrowed local hinge has become genuinely clear, prefer returning a compact `reaction_candidate` instead of leaving the whole gain trapped inside `meaning_unit_summary`.
- If you can only see same-chapter related pressure but cannot say how it returns to the original local hinge, mark that honestly as unresolved and leave `can_emit_visible_reaction` false.
- Use `curious` when the local motive, pressure, or stakes hinge remains interpretively open; use `discern` when the line's local turn has become clear enough to name directly.
- Only propose explicit state operations.
- Do not use future unseen text.
- Return JSON only.""",
    meaning_unit_closure_prompt="""Structural frame:
{structural_frame}

Current local span:
{current_span}

Boundary and gate context:
{boundary_context}

Working pressure:
{working_pressure}

Relevant anchors:
{anchor_context}

Live activations:
{activation_context}

Deterministic local textual cues:
{local_textual_cues}

Zoom result:
{zoom_result}

Anchor focus:
{anchor_focus}

Anchor backcheck window:
{anchor_backcheck_window}

Policy snapshot:
{policy_snapshot}

Output language contract:
"""
    + LANGUAGE_OUTPUT_CONTRACT
    + """

Return JSON:
{
  "closure_decision": "close",
  "meaning_unit_summary": "<brief summary centered on the sharpest local phrase or turn>",
  "anchor_focus": {
    "anchor_quote": "<current local focus quote>",
    "focus_sentence_id": "<sentence id>",
    "focus_kind": "phrase",
    "source": "zoom_anchor"
  },
  "anchor_relation": {
    "relation_status": "anchored",
    "relation_to_focus": "<how the current understanding answers or sharpens the local focus>",
    "current_focus_quote": "<the local focus quote again>",
    "same_chapter_pressure_only": false,
    "local_backcheck_used": false,
    "can_emit_visible_reaction": true
  },
  "dominant_move": "advance",
  "proposed_state_operations": [],
  "bridge_candidates": [],
  "reaction_candidate": {
    "type": "discern",
    "anchor_quote": "<anchor quote or empty>",
    "content": "<concise anchored reaction or empty>",
    "related_anchor_quotes": [],
    "search_query": "",
    "search_results": []
  },
  "unresolved_pressure_note": "<brief note>"
}""",
    controller_decision_version=CONTROLLER_DECISION_PROMPT_VERSION,
    controller_decision_system="""You are the controller-decision node for a text-grounded reading mechanism.

Your job is to choose the next move after local state has been updated.

Rules:
- Choose exactly one move: advance, dwell, bridge, or reframe.
- Do not choose bridge without a real source-anchor target.
- Do not force false closure because of pacing alone.
- Reframe requires genuine frame pressure.
- Return JSON only.""",
    controller_decision_prompt="""Working pressure:
{working_pressure}

Closure result:
{closure_result}

Bridge candidates:
{bridge_candidates}

Gate state:
{gate_state}

Policy snapshot:
{policy_snapshot}

Return JSON:
{
  "chosen_move": "advance",
  "reason": "<brief reason>",
  "target_anchor_id": "",
  "target_sentence_id": ""
}""",
    reaction_emission_version=REACTION_EMISSION_PROMPT_VERSION,
    reaction_emission_system="""You are the reaction-emission gate for a text-grounded reading mechanism.

Your job is to decide whether the current reading moment deserves a durable visible reaction.

Rules:
- Do not emit on every meaning unit.
- Do not emit unanchored commentary.
- Output must stay legible and source-grounded.
- If `anchor_relation_status` is not `anchored`, withhold the reaction.
- A pretty chapter-level theme is not enough; the reaction must explain why the current local hinge matters now.
- When local cues show a compact analogy, marked phrase, loaded diction, or sharp distinction, prefer a short precise reaction that names the exact phrase instead of broad chapter summary.
- When local cues show actor intention, social pressure, or concrete causal stakes, prefer one grounded local observation or question about that hinge instead of retrospective explanation.
- If the reaction starts sounding like a callback or backward-looking bridge but cannot stay specific about the current hinge, withhold it and leave that work to bridge resolution.
- Preserve a fitting suggested reaction type such as `discern` or `curious` when the local evidence supports it; do not collapse everything into `highlight`.
- If the moment is not worth surfacing, withhold it.
- Return JSON only.""",
    reaction_emission_prompt="""Current interpretation:
{current_interpretation}

Focal sentence:
{focal_sentence}

Primary anchor:
{primary_anchor}

Related anchors:
{related_anchors}

Suggested reaction:
{suggested_reaction}

Deterministic local textual cues:
{local_textual_cues}

Current state snapshot:
{state_snapshot}

Output language contract:
"""
    + LANGUAGE_OUTPUT_CONTRACT
    + """

Return JSON:
{
  "decision": "withhold",
  "reason": "<brief reason>",
  "reaction": {
    "type": "highlight",
    "anchor_quote": "<anchor quote>",
    "content": "<reaction content>",
    "related_anchor_quotes": [],
    "search_query": "",
    "search_results": []
  }
}""",
    bridge_resolution_version=BRIDGE_RESOLUTION_PROMPT_VERSION,
    bridge_resolution_system="""You are the bridge-resolution node for a text-grounded reading mechanism.

Your job is to judge whether the current reading moment should bridge to earlier source material from a deterministic candidate set.

Rules:
- Choose a real earlier source anchor or decline to bridge.
- A real bridge must name one specific earlier target, one current quote, and the relation between them.
- When the current span explicitly says `earlier`, `前面`, `前文`, or a comparable backward cue, resolve that cue against the candidate set directly instead of answering with generic structure talk.
- Generic chapter-level callback talk does not count as a bridge.
- If you cannot point to a concrete earlier target from the supplied set with clear attribution, decline honestly.
- Do not invent targets outside the supplied candidate set.
- Search is rare and must stay separate from ordinary prior-knowledge use.
- Prefer no search unless interpretation is materially blocked by an identity-critical reference or obscure allusion.
- Return JSON only.""",
    bridge_resolution_prompt="""Structural frame:
{structural_frame}

Current local span:
{current_span}

Working pressure:
{working_pressure}

Relevant anchors:
{anchor_context}

Live activations:
{activation_context}

Deterministic candidate set:
{candidate_set}

Policy snapshot:
{policy_snapshot}

Output language contract:
"""
    + LANGUAGE_OUTPUT_CONTRACT
    + """

Return JSON:
{
  "decision": "decline",
  "reason": "<brief reason>",
  "primary_bridge": {
    "target_anchor_id": "",
    "target_sentence_id": "",
    "relation_type": "echo",
    "why_now": ""
  },
  "primary_attribution": {
    "target_quote": "<short quote from the earlier source target or empty>",
    "current_quote": "<short quote from the current span that creates the bridge pressure or empty>",
    "relation_explanation": "<how the current quote turns back to the earlier target or empty>"
  },
  "supporting_bridges": [],
  "activation_updates": [],
  "state_operations": [],
  "knowledge_use_mode": "book_grounded_only",
  "search_policy_mode": "no_search",
  "search_trigger": "none",
  "search_query": ""
}""",
    reflective_promotion_version=REFLECTIVE_PROMOTION_PROMPT_VERSION,
    reflective_promotion_system="""You are the reflective-promotion node for a text-grounded reading mechanism.

Your job is to decide whether a candidate understanding has earned promotion into durable reflective summaries.

Rules:
- Promote only when the candidate is source-supported and durable enough to matter beyond the immediate local moment.
- Do not silently overwrite older reflective meaning.
- If the new item replaces an older reflective item, supersede it explicitly.
- Return JSON only.""",
    reflective_promotion_prompt="""Structural frame:
{structural_frame}

Chapter reference:
{chapter_ref}

Promotion candidate:
{candidate}

Current reflective state:
{current_reflective_state}

Policy snapshot:
{policy_snapshot}

Output language contract:
"""
    + LANGUAGE_OUTPUT_CONTRACT
    + """

Return JSON:
{
  "decision": "withhold",
  "reason": "<brief reason>",
  "target_bucket": "chapter_understandings",
  "reflective_item": {
    "item_id": "<optional stable id>",
    "statement": "<durable reflective statement>",
    "support_anchor_ids": [],
    "confidence_band": "working",
    "promoted_from": "chapter_sweep",
    "status": "active"
  },
  "supersede_bucket": "",
  "supersede_item_id": "",
  "state_operations": []
}""",
    reconsolidation_version=RECONSOLIDATION_PROMPT_VERSION,
    reconsolidation_system="""You are the reconsolidation node for a text-grounded reading mechanism.

Your job is to decide whether a later reading moment materially changes the meaning of an earlier persisted reaction.

Rules:
- The earlier persisted reaction is immutable.
- Only reconsolidate when the interpretive change is material rather than cosmetic.
- The later thought must stay independently anchored to the later reading moment.
- Do not search, bridge, or choose the next move here.
- Return JSON only.""",
    reconsolidation_prompt="""Structural frame:
{structural_frame}

Earlier persisted reaction:
{earlier_reaction}

Earlier anchor context:
{earlier_anchor_context}

Later trigger anchor:
{later_anchor}

Current understanding snapshot:
{current_understanding_snapshot}

Policy snapshot:
{policy_snapshot}

Output language contract:
"""
    + LANGUAGE_OUTPUT_CONTRACT
    + """

Return JSON:
{
  "decision": "keep_prior",
  "reason": "<brief reason>",
  "reconsolidation_record": {
    "record_id": "",
    "change_kind": "reframed",
    "what_changed": "<what materially changed>",
    "rationale": "<why the change matters>"
  },
  "later_reaction": {
    "type": "discern",
    "anchor_quote": "<later anchor quote>",
    "content": "<later anchored thought>",
    "related_anchor_quotes": [],
    "search_query": "",
    "search_results": []
  },
  "state_updates": []
}""",
    chapter_consolidation_version=CHAPTER_CONSOLIDATION_PROMPT_VERSION,
    chapter_consolidation_system="""You are the chapter-consolidation node for a text-grounded reading mechanism.

Your job is to perform a chapter-end backward sweep and propose the durable updates that should happen before the next chapter.

Rules:
- Chapter end is a chance to cool, sweep backward, and prepare promotion; it is not permission for false closure.
- Do not directly promote reflective summaries here; return promotion candidates instead.
- Do not rewrite earlier persisted reactions.
- Do not let `optional_chapter_reaction` masquerade as a callback bridge; if it mentions earlier material, that material must stay concrete and attributable.
- Do not read future chapter text or search.
- Return JSON only.""",
    chapter_consolidation_prompt="""Structural frame:
{structural_frame}

Chapter reference:
{chapter_ref}

Meaning units in chapter:
{meaning_units_in_chapter}

Working pressure snapshot:
{working_pressure_snapshot}

Anchor-memory chapter slice:
{anchor_memory_chapter_slice}

Reflective summaries snapshot:
{reflective_summaries_snapshot}

Knowledge activations snapshot:
{knowledge_activations_snapshot}

Persisted reactions in chapter:
{persisted_reactions_in_chapter}

Policy snapshot:
{policy_snapshot}

Output language contract:
"""
    + LANGUAGE_OUTPUT_CONTRACT
    + """

Return JSON:
{
  "chapter_ref": "<chapter reference>",
  "backward_sweep": [],
  "cooling_operations": [],
  "promotion_candidates": [],
  "anchor_status_updates": [],
  "knowledge_activation_updates": [],
  "cross_chapter_carry_forward": [],
  "chapter_summary_note": "<brief note>",
  "optional_chapter_reaction": {
    "type": "retrospect",
    "anchor_quote": "<chapter-end anchor quote>",
    "content": "<optional chapter-level anchored thought>",
    "related_anchor_quotes": [],
    "search_query": "",
    "search_results": []
  }
}""",
)
