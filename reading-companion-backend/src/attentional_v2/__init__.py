"""Phase 1 scaffold for the attentional_v2 reading mechanism."""

from .schemas import (
    ATTENTIONAL_V2_MECHANISM_VERSION,
    ATTENTIONAL_V2_POLICY_VERSION,
    ATTENTIONAL_V2_SCHEMA_VERSION,
    build_default_reader_policy,
    build_empty_anchor_memory,
    build_empty_knowledge_activations,
    build_empty_move_history,
    build_empty_reconsolidation_records,
    build_empty_reflective_summaries,
    build_empty_working_pressure,
)
from .storage import ATTENTIONAL_V2_MECHANISM_KEY, artifact_map, initialize_artifact_tree

__all__ = [
    "ATTENTIONAL_V2_MECHANISM_KEY",
    "ATTENTIONAL_V2_MECHANISM_VERSION",
    "ATTENTIONAL_V2_POLICY_VERSION",
    "ATTENTIONAL_V2_SCHEMA_VERSION",
    "artifact_map",
    "build_default_reader_policy",
    "build_empty_anchor_memory",
    "build_empty_knowledge_activations",
    "build_empty_move_history",
    "build_empty_reconsolidation_records",
    "build_empty_reflective_summaries",
    "build_empty_working_pressure",
    "initialize_artifact_tree",
]
