"""Phase 1 state schemas for the attentional_v2 reading mechanism."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, TypedDict

from src.reading_core.book_document import TextLocator


GateState = Literal["quiet", "watch", "hot", "must_evaluate"]
TriggerDecision = Literal["no_zoom", "monitor", "zoom_now"]
MoveType = Literal["advance", "dwell", "bridge", "reframe"]
KnowledgeUseMode = Literal["book_grounded_only", "book_grounded_plus_prior_knowledge"]
SearchPolicyMode = Literal["no_search", "defer_search", "search_now"]
ActivationStatus = Literal["weak", "plausible", "strong", "rejected", "dropped"]
AnchorRelationType = Literal["echo", "contrast", "cause", "support", "question_opened_by", "question_resolved_by", "callback"]

ATTENTIONAL_V2_SCHEMA_VERSION = 1
ATTENTIONAL_V2_MECHANISM_VERSION = "attentional_v2-phase1"
ATTENTIONAL_V2_POLICY_VERSION = "attentional_v2-policy-phase1"


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


class WorkingPressureItem(TypedDict, total=False):
    """One hot local item carried in the current pressure state."""

    item_id: str
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


class ReconsolidationRecord(TypedDict, total=False):
    """Append-only record of later reinterpretation linked to earlier thought."""

    record_id: str
    prior_reaction_id: str
    new_reaction_id: str
    rationale: str
    created_at: str


class ReconsolidationRecordsState(TypedDict, total=False):
    """Append-only ledger of reconsolidation events."""

    schema_version: int
    mechanism_version: str
    updated_at: str
    records: list[ReconsolidationRecord]


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
    logging: dict[str, object]


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
        "search_policy_mode": "defer_search",
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
        "knowledge": {"default_mode": "book_grounded_only"},
        "search": {"default_mode": "defer_search"},
        "bridge": {"source_anchor_required": True},
        "resume": {"default_mode": "warm_resume"},
        "logging": {"event_stream": True, "checkpoint_summaries": True},
    }
