"""Stable reader-mechanism spec used by documentation drift checks."""

from __future__ import annotations

from typing import get_args

from .models import CurrentReadingPhase, ReactionType
from .policy import default_budget_policy


_SELECTION_PIPELINE = ("book", "chapter", "section", "subsegment")
_PERSISTED_UNIT_LABELS = {
    "chapter": "chapter",
    "semantic_unit": "section",
    "backend_internal_alias": "segment",
}
_RUNTIME_ATTENTION_UNIT = "subsegment"
_SEGMENT_EXECUTION_MODE = "single_pass"
_READER_LOOP_NODES = ("read", "think", "express", "search", "fuse", "reflect")
_READER_PROMPT_NODES = ("subsegment_plan", "think", "express", "reflect")
_MEMORY_PACKET_SECTIONS = (
    "book_arc_summary",
    "open_threads",
    "findings",
    "salience_ledger",
    "recent_segment_flow",
    "chapter_memory_summaries",
)
_ATTENTION_CONTEXT_PRIORITY = ("search_query", "current_excerpt")
_SUBSEGMENT_DENSITY_TRIGGER_GTE = 3.2


def _literal_values(literal_type: object) -> list[str]:
    """Return the ordered values declared for one Literal type."""
    return [str(value) for value in get_args(literal_type)]


def _subsegment_slicing_defaults() -> dict[str, float | int]:
    """Return the stable default knobs for runtime subsegment slicing."""
    budget = default_budget_policy()
    return {
        "planner_mode": "llm_primary",
        "fallback_mode": "heuristic_sentence_boundary",
        "safety_cap_role": "absolute_cap",
        "slice_target_tokens": int(budget["slice_target_tokens"]),
        "slice_max_tokens": int(budget["slice_max_tokens"]),
        "slice_max_subsegments": int(budget["slice_max_subsegments"]),
        "density_trigger_gte": _SUBSEGMENT_DENSITY_TRIGGER_GTE,
    }


def _search_budget_defaults() -> dict[str, int]:
    """Return the stable default search budget knobs for one run."""
    budget = default_budget_policy()
    return {
        "max_search_queries_per_segment": int(budget["max_search_queries_per_segment"]),
        "max_search_queries_per_chapter": int(budget["max_search_queries_per_chapter"]),
    }


READER_MECHANISM_SPEC = {
    "selection_pipeline": list(_SELECTION_PIPELINE),
    "persisted_unit_labels": dict(_PERSISTED_UNIT_LABELS),
    "runtime_attention_unit": _RUNTIME_ATTENTION_UNIT,
    "segment_execution_mode": _SEGMENT_EXECUTION_MODE,
    "reader_loop_nodes": list(_READER_LOOP_NODES),
    "reader_prompt_nodes": list(_READER_PROMPT_NODES),
    "live_activity_phases": _literal_values(CurrentReadingPhase),
    "internal_reaction_types": _literal_values(ReactionType),
    "memory_packet_sections": list(_MEMORY_PACKET_SECTIONS),
    "attention_context_priority": list(_ATTENTION_CONTEXT_PRIORITY),
    "subsegment_slicing_defaults": _subsegment_slicing_defaults(),
    "search_budget_defaults": _search_budget_defaults(),
}
