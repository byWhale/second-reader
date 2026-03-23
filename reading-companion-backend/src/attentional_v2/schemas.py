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
    pressure_updates: list[StateOperation]
    activation_updates: list[StateOperation]
    bridge_candidate: BridgeCandidate | None
    consider_reaction_emission: bool
    uncertainty_note: str


class MeaningUnitClosureResult(TypedDict, total=False):
    """Structured result from meaning-unit closure."""

    closure_decision: ClosureDecision
    meaning_unit_summary: str
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


class BridgeResolutionResult(TypedDict, total=False):
    """Structured bridge-judgment result over deterministic candidate retrieval."""

    decision: BridgeResolutionDecision
    reason: str
    primary_bridge: BridgeCandidate | None
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
    gate: dict[str, object]
    controller: dict[str, object]
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
    trigger_state: TriggerState
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
        "gate": {"default_state": "quiet"},
        "controller": {"default_move": "advance", "allow_bridge_without_anchor": False},
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
