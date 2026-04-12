"""Phase 1 state schemas for the attentional_v2 reading mechanism."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, TypedDict

from src.reading_core.book_document import TextLocator, TextRole
from src.reading_core.normalized_outputs import ReactionType, SearchHit
from src.reading_core.runtime_contracts import ObservabilityMode, ResumeKind, RuntimeArtifactRefs, SharedRunCursor


GateState = Literal["quiet", "watch", "hot", "must_evaluate"]
TriggerDecision = Literal["no_zoom", "monitor", "zoom_now"]
MoveType = Literal["advance", "dwell", "bridge", "reframe"]
UnitizeBoundaryType = Literal[
    "paragraph_end",
    "intra_paragraph_semantic_close",
    "cross_paragraph_continuation",
    "section_end",
    "budget_cap",
]
RouteAction = Literal["commit", "continue", "bridge_back", "reframe"]
ContextRequestKind = Literal["active_recall", "look_back"]
StateOperationType = Literal["create", "update", "cool", "drop", "retain_anchor", "link_anchors", "promote", "supersede", "reactivate"]
ClosureDecision = Literal["continue", "close"]
ReactionEmissionDecision = Literal["emit", "withhold"]
BridgeResolutionDecision = Literal["bridge", "decline"]
ReflectivePromotionDecision = Literal["promote", "withhold"]
ReconsolidationDecision = Literal["reconsolidate", "keep_prior"]
KnowledgeUseMode = Literal["book_grounded_only", "book_grounded_plus_prior_knowledge"]
SearchPolicyMode = Literal["no_search", "defer_search", "search_now"]
SearchTrigger = Literal["none", "identity_critical_reference", "blocking_allusion", "genuine_curiosity", "ornamental_curiosity"]
ActivationStatus = Literal["weak", "plausible", "strong", "rejected", "dropped"]
AnchorRelationType = Literal["echo", "contrast", "cause", "support", "question_opened_by", "question_resolved_by", "callback"]
AnchorFocusKind = Literal["phrase", "sentence", "span"]
AnchorRelationStatus = Literal["anchored", "related_but_unresolved", "unclear"]
TriggerFamily = Literal["integrity", "salience", "knowledge_risk"]
TriggerSignalKind = Literal[
    "discourse_turn",
    "definition_or_distinction",
    "claim_pressure",
    "sentence_role_shift",
    "local_cohesion_drop",
    "callback_activation",
    "pressure_update_proxy",
    "cadence_guardrail",
]

ATTENTIONAL_V2_SCHEMA_VERSION = 1
ATTENTIONAL_V2_MECHANISM_VERSION = "attentional_v2-phase8"
ATTENTIONAL_V2_POLICY_VERSION = "attentional_v2-policy-phase8"


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class WorkingPressureItem(TypedDict, total=False):
    """One hot local item carried in the current pressure state."""

    item_id: str
    bucket: str
    kind: str
    statement: str
    support_anchor_ids: list[str]
    status: str


class PressureSnapshot(TypedDict, total=False):
    """Controller-facing summary of the current local interpretive state."""

    dominant_pressure_kind: str
    dominant_pressure_strength: str
    interpretive_temperature: str
    local_clarity: str
    bridge_pull_present: bool
    reframe_pressure_present: bool


class WorkingPressureState(TypedDict, total=False):
    """Hot local state that governs whether the mechanism should escalate."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    gate_state: GateState
    local_hypotheses: list[WorkingPressureItem]
    local_questions: list[WorkingPressureItem]
    local_tensions: list[WorkingPressureItem]
    local_motifs: list[WorkingPressureItem]
    pressure_snapshot: PressureSnapshot


class WorkingState(WorkingPressureState, total=False):
    """Primary hot state after the Phase C.3 direct migration."""


class LocalBufferSentence(TypedDict, total=False):
    """One recently seen sentence carried in the rolling local buffer."""

    sentence_id: str
    sentence_index: int
    paragraph_index: int
    text: str
    text_role: TextRole


class LocalBufferState(TypedDict, total=False):
    """Current rolling sentence buffer and open local meaning-unit span."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    current_sentence_id: str
    current_sentence_index: int
    recent_sentences: list[LocalBufferSentence]
    open_meaning_unit_sentence_ids: list[str]
    recent_meaning_units: list[list[str]]
    seen_sentence_ids: list[str]
    last_meaning_unit_closed_at_sentence_id: str
    is_reconstructed: bool
    reconstructed_from_checkpoint_id: str | None
    last_resume_kind: ResumeKind | None


class LocalContinuityState(TypedDict, total=False):
    """Compact continuity envelope persisted separately from the heavier local buffer."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    chapter_id: int | None
    chapter_ref: str
    current_sentence_id: str
    current_sentence_index: int
    recent_sentence_ids: list[str]
    open_meaning_unit_sentence_ids: list[str]
    recent_meaning_units: list[list[str]]
    last_meaning_unit_closed_at_sentence_id: str
    is_reconstructed: bool
    reconstructed_from_checkpoint_id: str | None
    last_resume_kind: ResumeKind | None


class TriggerSignal(TypedDict, total=False):
    """One cheap trigger signal emitted by the always-on ensemble."""

    signal_id: str
    signal_kind: TriggerSignalKind
    family: TriggerFamily
    sentence_id: str
    evidence: str
    strength: str


class TriggerState(TypedDict, total=False):
    """Current trigger ensemble output and supporting cheap evidence."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    current_sentence_id: str
    output: TriggerDecision
    gate_state: GateState
    signals: list[TriggerSignal]
    cadence_counter: int
    callback_anchor_ids: list[str]


class PreviewRange(TypedDict, total=False):
    """One bounded preview range exposed to the unitization node."""

    start_sentence_id: str
    end_sentence_id: str


class UnitizeDecision(TypedDict, total=False):
    """One prompt-led coverage-unit selection for the next formal read."""

    start_sentence_id: str
    end_sentence_id: str
    preview_range: PreviewRange
    boundary_type: UnitizeBoundaryType
    evidence_sentence_ids: list[str]
    reason: str
    continuation_pressure: bool


class CarryForwardRef(TypedDict, total=False):
    """One bounded carry-forward reference exposed to the read node."""

    ref_id: str
    kind: str
    item_id: str
    summary: str
    sentence_id: str
    anchor_id: str
    reaction_id: str
    move_id: str


class SessionContinuityCapsule(TypedDict, total=False):
    """Small session-continuity capsule that should stay cheap to reload every unit."""

    recent_sentence_ids: list[str]
    recent_meaning_units: list[list[str]]
    recent_moves: list[dict[str, object]]
    recent_reactions: list[dict[str, object]]


class RehydrationEntry(TypedDict, total=False):
    """One explicit rehydration entrypoint retained for later continuity recovery."""

    entry_id: str
    anchor_id: str
    sentence_start_id: str
    sentence_end_id: str
    concept_key: str
    thread_key: str
    why_rehydrate: str


class ContinuationCapsule(TypedDict, total=False):
    """Persisted continuity seed used to restart carried context after pauses or resume."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    chapter_ref: str
    current_sentence_id: str
    session_continuity_capsule: SessionContinuityCapsule
    working_state_digest: "WorkingStateDigest"
    chapter_reflective_frame: "ReflectiveFrameDigest"
    active_focus_digest: "ActiveFocusDigest"
    concept_digest: list["ConceptDigestItem"]
    thread_digest: list["ThreadDigestItem"]
    anchor_bank_digest: "AnchorBankDigest"
    refs: list["CarryForwardRef"]
    rehydration_entrypoints: list[RehydrationEntry]


class WorkingStateDigest(TypedDict, total=False):
    """Prompt-facing digest of the current hot working state."""

    gate_state: str
    pressure_snapshot: dict[str, object]
    hot_items: list[dict[str, object]]
    open_questions: list[dict[str, object]]
    live_tensions: list[dict[str, object]]
    live_hypotheses: list[dict[str, object]]
    live_motifs: list[dict[str, object]]


class ReflectiveFrameDigest(TypedDict, total=False):
    """Bounded reflective frame packet for the current chapter/book."""

    chapter_frames: list[dict[str, object]]
    book_frames: list[dict[str, object]]
    durable_definitions: list[dict[str, object]]


class ActiveFocusDigest(TypedDict, total=False):
    """Small digest of what is currently active across local questions, moves, and reactions."""

    open_questions: list[dict[str, object]]
    live_tensions: list[dict[str, object]]
    live_hypotheses: list[dict[str, object]]
    recent_moves: list[dict[str, object]]
    recent_reactions: list[dict[str, object]]


class AnchorBankDigest(TypedDict, total=False):
    """Prompt-facing digest of currently useful source-grounded anchors."""

    active_anchors: list[dict[str, object]]


class ConceptDigestItem(TypedDict, total=False):
    """One small concept-level digest entry derived from current state indexes."""

    ref_id: str
    concept_key: str
    concept_type: str
    linked_anchor_ids: list[str]
    sample_quotes: list[str]
    rationale: str


class ThreadDigestItem(TypedDict, total=False):
    """One small thread-level digest entry derived from current state indexes."""

    ref_id: str
    thread_key: str
    thread_type: str
    source_anchor_id: str
    linked_anchor_ids: list[str]
    sample_quotes: list[str]
    rationale: str


class CarryForwardContext(TypedDict, total=False):
    """Small stable continuity packet passed into every formal read."""

    packet_version: str
    continuation_capsule: ContinuationCapsule
    session_continuity_capsule: SessionContinuityCapsule
    working_state_digest: WorkingStateDigest
    chapter_reflective_frame: ReflectiveFrameDigest
    active_focus_digest: ActiveFocusDigest
    concept_digest: list[ConceptDigestItem]
    thread_digest: list[ThreadDigestItem]
    anchor_bank_digest: AnchorBankDigest
    working_pressure_digest: dict[str, object]
    reflective_digest: list[dict[str, object]]
    anchor_digest: list[dict[str, object]]
    continuity_digest: dict[str, object]
    refs: list[CarryForwardRef]


class NavigationContext(TypedDict, total=False):
    """Small navigation packet used by navigate.unitize before the unit is chosen."""

    packet_version: str
    continuation_capsule: ContinuationCapsule
    watch_state: dict[str, object]
    session_continuity_capsule: SessionContinuityCapsule
    working_state_digest: WorkingStateDigest
    chapter_reflective_frame: ReflectiveFrameDigest
    active_focus_digest: ActiveFocusDigest
    concept_digest: list[ConceptDigestItem]
    thread_digest: list[ThreadDigestItem]
    anchor_bank_digest: AnchorBankDigest
    refs: list[CarryForwardRef]


class PriorMaterialUse(TypedDict, total=False):
    """Observation of whether prior material materially informed the current read."""

    materially_used: bool
    explanation: str
    supporting_ref_ids: list[str]


class ContextRequest(TypedDict, total=False):
    """Optional request for one bounded supplemental-context pass."""

    kind: ContextRequestKind
    reason: str
    anchor_ids: list[str]
    sentence_ids: list[str]


class ReadAnchorEvidence(TypedDict, total=False):
    """One exact unit-local anchor cited by the read step."""

    sentence_id: str
    quote: str
    why_it_matters: str


class ReadUnitResult(TypedDict, total=False):
    """Authoritative formal-read packet for one chosen coverage unit."""

    local_understanding: str
    move_hint: MoveType
    continuation_pressure: bool
    implicit_uptake: list[StateOperation]
    anchor_evidence: list[ReadAnchorEvidence]
    prior_material_use: PriorMaterialUse
    raw_reaction: ReactionCandidate | None
    context_request: ContextRequest | None


class StateOperation(TypedDict, total=False):
    """One explicit state mutation proposed by a Phase 4 node."""

    operation_type: StateOperationType
    target_store: str
    item_id: str
    reason: str
    payload: dict[str, object]


class BridgeCandidate(TypedDict, total=False):
    """One bridge candidate record passed to later bridge judgment."""

    candidate_kind: str
    target_anchor_id: str
    target_sentence_id: str
    retrieval_channel: str
    relation_type: AnchorRelationType | str
    score: float
    why_now: str
    quote: str
    locator: TextLocator


class ReactionCandidate(TypedDict, total=False):
    """One candidate anchored reaction proposed before emission gating."""

    type: ReactionType
    anchor_quote: str
    content: str
    related_anchor_quotes: list[str]
    search_query: str
    search_results: list[SearchHit]


class AnchorFocus(TypedDict, total=False):
    """One compact local-focus packet carried across the local interpretive loop."""

    anchor_quote: str
    focus_sentence_id: str
    focus_kind: AnchorFocusKind | str
    source: str


class AnchorRelationAssessment(TypedDict, total=False):
    """How the current interpretation relates back to the original local focus."""

    relation_status: AnchorRelationStatus | str
    relation_to_focus: str
    current_focus_quote: str
    same_chapter_pressure_only: bool
    local_backcheck_used: bool
    can_emit_visible_reaction: bool


class BridgeAttribution(TypedDict, total=False):
    """Explicit source-grounded explanation for one accepted bridge."""

    target_quote: str
    current_quote: str
    relation_explanation: str


class ReactionAnchor(TypedDict, total=False):
    """One persisted source anchor embedded directly into a durable visible reaction."""

    anchor_id: str
    sentence_start_id: str
    sentence_end_id: str
    quote: str
    locator: TextLocator


class AnchoredReactionRecord(TypedDict, total=False):
    """Mechanism-authored durable visible thought with source-preserving anchors."""

    reaction_id: str
    chapter_id: int
    chapter_ref: str
    emitted_at_sentence_id: str
    type: ReactionType
    thought: str
    primary_anchor: ReactionAnchor
    related_anchors: list[ReactionAnchor]
    reconsolidation_record_id: str
    supersedes_reaction_id: str
    compatibility_section_ref: str
    search_query: str
    search_results: list[SearchHit]
    created_at: str


class ZoomReadResult(TypedDict, total=False):
    """Structured result from the sentence-level zoom node."""

    local_interpretation: str
    anchor_quote: str
    anchor_focus: AnchorFocus | None
    pressure_updates: list[StateOperation]
    activation_updates: list[StateOperation]
    bridge_candidate: BridgeCandidate | None
    consider_reaction_emission: bool
    uncertainty_note: str


class MeaningUnitClosureResult(TypedDict, total=False):
    """Structured result from meaning-unit closure."""

    closure_decision: ClosureDecision
    meaning_unit_summary: str
    anchor_focus: AnchorFocus | None
    anchor_relation: AnchorRelationAssessment | None
    dominant_move: MoveType
    proposed_state_operations: list[StateOperation]
    bridge_candidates: list[BridgeCandidate]
    reaction_candidate: ReactionCandidate | None
    unresolved_pressure_note: str


class ControllerDecisionResult(TypedDict, total=False):
    """Structured controller routing decision."""

    chosen_move: MoveType
    reason: str
    target_anchor_id: str
    target_sentence_id: str


class NavigateRouteDecision(TypedDict, total=False):
    """Normalized next-step routing result for one exact chosen coverage unit."""

    action: RouteAction
    reason: str
    close_current_unit: bool
    target_anchor_id: str
    target_sentence_id: str
    persist_raw_reaction: bool


class BridgeResolutionResult(TypedDict, total=False):
    """Structured bridge-judgment result over deterministic candidate retrieval."""

    decision: BridgeResolutionDecision
    reason: str
    primary_bridge: BridgeCandidate | None
    primary_attribution: BridgeAttribution | None
    supporting_bridges: list[BridgeCandidate]
    activation_updates: list[StateOperation]
    state_operations: list[StateOperation]
    knowledge_use_mode: KnowledgeUseMode
    search_policy_mode: SearchPolicyMode
    search_trigger: SearchTrigger
    search_query: str


class ReactionEmissionResult(TypedDict, total=False):
    """Anchored visible-reaction emission decision."""

    decision: ReactionEmissionDecision
    reason: str
    reaction: ReactionCandidate | None


class AnchorRecord(TypedDict, total=False):
    """One source-grounded anchor retained for later bridge or recall use."""

    anchor_id: str
    sentence_start_id: str
    sentence_end_id: str
    quote: str
    locator: TextLocator
    anchor_kind: str
    why_it_mattered: str
    status: str
    linked_reaction_ids: list[str]
    linked_activation_ids: list[str]


class AnchorRelation(TypedDict, total=False):
    """One typed relation between retained anchors."""

    relation_id: str
    relation_type: AnchorRelationType
    source_anchor_id: str
    target_anchor_id: str
    rationale: str


class AnchorBankState(TypedDict, total=False):
    """Primary source-grounded evidence store after the Phase C.3 migration."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    anchor_records: list[AnchorRecord]
    anchor_relations: list[AnchorRelation]


class AnchorMemoryState(TypedDict, total=False):
    """Retrieval-facing earlier state for bridge and callback behavior."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    anchor_records: list[AnchorRecord]
    anchor_relations: list[AnchorRelation]
    motif_index: dict[str, list[str]]
    unresolved_reference_index: dict[str, list[str]]
    trace_links: dict[str, list[str]]


class ConceptRegistryEntry(TypedDict, total=False):
    """One durable concept/object-memory entry."""

    concept_key: str
    concept_type: str
    status: str
    summary: str
    support_anchor_ids: list[str]
    linked_thread_ids: list[str]
    last_touched_sentence_id: str


class ConceptRegistryState(TypedDict, total=False):
    """Primary durable object-memory layer."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    entries: list[ConceptRegistryEntry]


class ThreadTraceEntry(TypedDict, total=False):
    """One durable trace/line entry."""

    thread_key: str
    thread_type: str
    status: str
    summary: str
    support_anchor_ids: list[str]
    linked_concept_keys: list[str]
    last_touched_sentence_id: str
    source_anchor_id: str
    target_anchor_ids: list[str]


class ThreadTraceState(TypedDict, total=False):
    """Primary durable trace/line layer."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    entries: list[ThreadTraceEntry]


class ReflectiveItem(TypedDict, total=False):
    """One promoted reflective understanding retained across local hot state."""

    item_id: str
    statement: str
    support_anchor_ids: list[str]
    confidence_band: str
    promoted_from: str
    status: str
    superseded_by_item_id: str
    chapter_ref: str


class ReflectivePromotionCandidate(TypedDict, total=False):
    """One candidate statement that may earn promotion into reflective summaries."""

    candidate_id: str
    statement: str
    support_anchor_ids: list[str]
    promoted_from: str
    target_bucket: str
    rationale: str


class ReflectivePromotionResult(TypedDict, total=False):
    """Structured result from the reflective-promotion node."""

    decision: ReflectivePromotionDecision
    reason: str
    target_bucket: str
    reflective_item: ReflectiveItem | None
    supersede_bucket: str
    supersede_item_id: str
    state_operations: list[StateOperation]


class ReflectiveSummariesState(TypedDict, total=False):
    """Slower durable understanding promoted from local reading state."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    chapter_understandings: list[ReflectiveItem]
    book_level_frames: list[ReflectiveItem]
    durable_definitions: list[ReflectiveItem]
    stabilized_motifs: list[ReflectiveItem]
    resolved_questions_of_record: list[ReflectiveItem]
    chapter_end_notes: list[ReflectiveItem]


class ReflectiveFramesState(ReflectiveSummariesState, total=False):
    """Primary slower reflective layer after the Phase C.3 migration."""


class KnowledgeActivation(TypedDict, total=False):
    """One activated piece of prior knowledge with separate warrant tracking."""

    activation_id: str
    trigger_anchor_id: str
    activation_type: str
    source_candidate: str
    recognition_confidence: str
    reading_warrant: str
    role_assessment: str
    evidence_hints: list[str]
    evidence_rationale: str
    support_anchor_ids: list[str]
    conflict_anchor_ids: list[str]
    introduced_at_sentence_id: str
    last_touched_sentence_id: str
    status: ActivationStatus


class KnowledgeActivationsState(TypedDict, total=False):
    """Knowledge-activation ledger plus current use-policy mode."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    knowledge_use_mode: KnowledgeUseMode
    search_policy_mode: SearchPolicyMode
    activations: list[KnowledgeActivation]


class MoveRecord(TypedDict, total=False):
    """One recorded controller move."""

    move_id: str
    move_type: MoveType
    reason: str
    source_sentence_id: str
    target_anchor_id: str
    target_sentence_id: str
    created_at: str


class MoveHistoryState(TypedDict, total=False):
    """Ordered controller move history."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    moves: list[MoveRecord]


class ReactionRecordsState(TypedDict, total=False):
    """Append-only mechanism-owned durable reaction history."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    records: list[AnchoredReactionRecord]


class ReconsolidationRecord(TypedDict, total=False):
    """Append-only record of later reinterpretation linked to earlier thought."""

    record_id: str
    prior_reaction_id: str
    new_reaction_id: str
    change_kind: str
    what_changed: str
    rationale: str
    created_at: str


class ReconsolidationRecordsState(TypedDict, total=False):
    """Append-only ledger of reconsolidation events."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    records: list[ReconsolidationRecord]


class ReconsolidationResult(TypedDict, total=False):
    """Structured result from the reconsolidation node."""

    decision: ReconsolidationDecision
    reason: str
    reconsolidation_record: ReconsolidationRecord | None
    later_reaction: AnchoredReactionRecord | None
    state_updates: list[StateOperation]


class ChapterConsolidationResult(TypedDict, total=False):
    """Structured chapter-end sweep and carry-forward result."""

    chapter_ref: str
    backward_sweep: list[dict[str, object]]
    cooling_operations: list[StateOperation]
    promotion_candidates: list[ReflectivePromotionCandidate]
    anchor_status_updates: list[dict[str, object]]
    knowledge_activation_updates: list[StateOperation]
    cross_chapter_carry_forward: list[WorkingPressureItem]
    chapter_summary_note: str
    optional_chapter_reaction: ReactionCandidate | None


class LoggingPolicy(TypedDict, total=False):
    """Versioned observability policy for standard vs debug persistence."""

    observability_mode: ObservabilityMode
    event_stream: bool
    checkpoint_summaries: bool
    debug_event_stream: bool
    debug_checkpoint_diagnostics: bool


class ReaderPolicy(TypedDict, total=False):
    """Versioned mechanism policy kept separate from ontology-bearing state."""

    schema_version: int
    mechanism_version: str
    policy_version: str
    updated_at: str
    unitize: dict[str, object]
    gate: dict[str, object]
    controller: dict[str, object]
    read: dict[str, object]
    knowledge: dict[str, object]
    search: dict[str, object]
    bridge: dict[str, object]
    resume: dict[str, object]
    logging: LoggingPolicy


class ResumeMetadataState(TypedDict, total=False):
    """Mechanism-private metadata about checkpointing, reconstruction, and last resume behavior."""

    schema_version: int
    mechanism_version: str
    policy_version: str
    updated_at: str
    resume_available: bool
    default_resume_kind: ResumeKind
    last_checkpoint_id: str | None
    last_checkpoint_at: str | None
    last_resume_kind: ResumeKind | None
    last_resume_at: str | None
    last_resume_checkpoint_id: str | None
    last_resume_status: str
    last_resume_reason: str
    last_resume_window_sentence_ids: list[str]
    reconstructed_hot_state: bool


class FullCheckpointState(TypedDict, total=False):
    """Mechanism-owned full checkpoint used for warm, cold, and reconstitution resume."""

    schema_version: int
    mechanism_version: str
    policy_version: str
    checkpoint_id: str
    created_at: str
    checkpoint_reason: str
    resume_kind: ResumeKind
    cursor: SharedRunCursor
    active_artifact_refs: RuntimeArtifactRefs
    visible_reaction_ids: list[str]
    local_buffer: LocalBufferState
    local_continuity: LocalContinuityState
    continuation_capsule: ContinuationCapsule
    trigger_state: TriggerState
    working_state: WorkingState
    concept_registry: ConceptRegistryState
    thread_trace: ThreadTraceState
    reflective_frames: ReflectiveFramesState
    anchor_bank: AnchorBankState
    working_pressure: WorkingPressureState
    anchor_memory: AnchorMemoryState
    reflective_summaries: ReflectiveSummariesState
    knowledge_activations: KnowledgeActivationsState
    move_history: MoveHistoryState
    reaction_records: ReactionRecordsState
    reconsolidation_records: ReconsolidationRecordsState
    reader_policy: ReaderPolicy
    resume_metadata: ResumeMetadataState


def build_empty_working_pressure(*, mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION) -> WorkingPressureState:
    """Return the default hot local state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "gate_state": "quiet",
        "local_hypotheses": [],
        "local_questions": [],
        "local_tensions": [],
        "local_motifs": [],
        "pressure_snapshot": {
            "dominant_pressure_kind": "",
            "dominant_pressure_strength": "low",
            "interpretive_temperature": "cool",
            "local_clarity": "unknown",
            "bridge_pull_present": False,
            "reframe_pressure_present": False,
        },
    }


def build_empty_working_state(*, mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION) -> WorkingState:
    """Return the default primary hot state."""

    return build_empty_working_pressure(mechanism_version=mechanism_version)


def build_empty_local_buffer(*, mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION) -> LocalBufferState:
    """Return the default local buffer state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "current_sentence_id": "",
        "current_sentence_index": 0,
        "recent_sentences": [],
        "open_meaning_unit_sentence_ids": [],
        "recent_meaning_units": [],
        "seen_sentence_ids": [],
        "last_meaning_unit_closed_at_sentence_id": "",
        "is_reconstructed": False,
        "reconstructed_from_checkpoint_id": None,
        "last_resume_kind": None,
    }


def build_empty_local_continuity(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> LocalContinuityState:
    """Return the compact continuity envelope used by Phase 7 checkpointing and resume."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "chapter_id": None,
        "chapter_ref": "",
        "current_sentence_id": "",
        "current_sentence_index": 0,
        "recent_sentence_ids": [],
        "open_meaning_unit_sentence_ids": [],
        "recent_meaning_units": [],
        "last_meaning_unit_closed_at_sentence_id": "",
        "is_reconstructed": False,
        "reconstructed_from_checkpoint_id": None,
        "last_resume_kind": None,
    }


def build_empty_continuation_capsule(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> ContinuationCapsule:
    """Return the default persisted continuation capsule."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "chapter_ref": "",
        "current_sentence_id": "",
        "session_continuity_capsule": {
            "recent_sentence_ids": [],
            "recent_meaning_units": [],
            "recent_moves": [],
            "recent_reactions": [],
        },
        "working_state_digest": {
            "gate_state": "",
            "pressure_snapshot": {},
            "hot_items": [],
            "open_questions": [],
            "live_tensions": [],
            "live_hypotheses": [],
            "live_motifs": [],
        },
        "chapter_reflective_frame": {
            "chapter_frames": [],
            "book_frames": [],
            "durable_definitions": [],
        },
        "active_focus_digest": {
            "open_questions": [],
            "live_tensions": [],
            "live_hypotheses": [],
            "recent_moves": [],
            "recent_reactions": [],
        },
        "concept_digest": [],
        "thread_digest": [],
        "anchor_bank_digest": {"active_anchors": []},
        "refs": [],
        "rehydration_entrypoints": [],
    }


def build_empty_trigger_state(*, mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION) -> TriggerState:
    """Return the default trigger state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "current_sentence_id": "",
        "output": "no_zoom",
        "gate_state": "quiet",
        "signals": [],
        "cadence_counter": 0,
        "callback_anchor_ids": [],
    }


def build_empty_anchor_memory(*, mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION) -> AnchorMemoryState:
    """Return the default anchor-memory state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "anchor_records": [],
        "anchor_relations": [],
        "motif_index": {},
        "unresolved_reference_index": {},
        "trace_links": {},
    }


def build_empty_anchor_bank(*, mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION) -> AnchorBankState:
    """Return the default primary anchor-bank state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "anchor_records": [],
        "anchor_relations": [],
    }


def build_empty_concept_registry(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> ConceptRegistryState:
    """Return the default concept-registry state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "entries": [],
    }


def build_empty_thread_trace(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> ThreadTraceState:
    """Return the default thread-trace state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "entries": [],
    }


def build_empty_reflective_summaries(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> ReflectiveSummariesState:
    """Return the default reflective-summary state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "chapter_understandings": [],
        "book_level_frames": [],
        "durable_definitions": [],
        "stabilized_motifs": [],
        "resolved_questions_of_record": [],
        "chapter_end_notes": [],
    }


def build_empty_reflective_frames(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> ReflectiveFramesState:
    """Return the default reflective-frames state."""

    return build_empty_reflective_summaries(mechanism_version=mechanism_version)


def build_empty_knowledge_activations(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> KnowledgeActivationsState:
    """Return the default knowledge-activation state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "knowledge_use_mode": "book_grounded_only",
        "search_policy_mode": "no_search",
        "activations": [],
    }


def build_empty_move_history(*, mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION) -> MoveHistoryState:
    """Return the default move-history state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "moves": [],
    }


def build_empty_reaction_records(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> ReactionRecordsState:
    """Return the default durable anchored-reaction state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "records": [],
    }


def build_empty_reconsolidation_records(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
) -> ReconsolidationRecordsState:
    """Return the default reconsolidation state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "updated_at": _timestamp(),
        "records": [],
    }


def build_default_reader_policy(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
    policy_version: str = ATTENTIONAL_V2_POLICY_VERSION,
) -> ReaderPolicy:
    """Return the default versioned reader policy."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "policy_version": policy_version,
        "updated_at": _timestamp(),
        "unitize": {
            "max_coverage_unit_sentences": 12,
        },
        "gate": {"default_state": "quiet"},
        "controller": {"default_move": "advance", "allow_bridge_without_anchor": False},
        "read": {
            "supplemental_context_budget": 4,
            "supplemental_context_emergency_cap": 4,
            "look_back_max_sentences": 8,
        },
        "knowledge": {
            "default_mode": "book_grounded_only",
            "allow_prior_knowledge_when_warranted": True,
        },
        "search": {
            "default_mode": "no_search",
            "allow_search_now": True,
            "rare_search_posture": True,
            "defer_curiosity_by_default": True,
        },
        "bridge": {"source_anchor_required": True, "max_supporting_candidates": 2},
        "resume": {
            "default_mode": "warm_resume",
            "cold_resume_target_sentences": 8,
            "cold_resume_max_sentences": 12,
            "reconstitution_resume_target_sentences": 24,
            "reconstitution_resume_max_sentences": 30,
            "reconstitution_resume_target_meaning_units": 3,
            "chapter_local_only": True,
            "checkpoint_summary_required": True,
        },
        "logging": {
            "observability_mode": "standard",
            "event_stream": True,
            "checkpoint_summaries": True,
            "debug_event_stream": False,
            "debug_checkpoint_diagnostics": False,
        },
    }


def build_empty_resume_metadata(
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
    policy_version: str = ATTENTIONAL_V2_POLICY_VERSION,
) -> ResumeMetadataState:
    """Return the default resume metadata state."""

    return {
        "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
        "mechanism_version": mechanism_version,
        "policy_version": policy_version,
        "updated_at": _timestamp(),
        "resume_available": False,
        "default_resume_kind": "warm_resume",
        "last_checkpoint_id": None,
        "last_checkpoint_at": None,
        "last_resume_kind": None,
        "last_resume_at": None,
        "last_resume_checkpoint_id": None,
        "last_resume_status": "not_started",
        "last_resume_reason": "",
        "last_resume_window_sentence_ids": [],
        "reconstructed_hot_state": False,
    }
