"""Skill and budget policy helpers for Reader runtime."""

from __future__ import annotations

from .models import BookAnalysisPolicy, BudgetPolicy, ReaderBudget, SkillPolicy, SkillProfileName


_SKILL_PRESETS: dict[SkillProfileName, SkillPolicy] = {
    "balanced": {
        "profile": "balanced",
        "enabled_reactions": ["highlight", "association", "curious", "discern", "connect_back", "silent"],
        "max_reactions_per_segment": 8,
        "max_curious_reactions": 2,
    },
    "analytical": {
        "profile": "analytical",
        "enabled_reactions": ["highlight", "association", "discern", "connect_back", "curious", "silent"],
        "max_reactions_per_segment": 7,
        "max_curious_reactions": 1,
    },
    "curious": {
        "profile": "curious",
        "enabled_reactions": ["highlight", "association", "curious", "discern", "connect_back", "silent"],
        "max_reactions_per_segment": 9,
        "max_curious_reactions": 3,
    },
    "quiet": {
        "profile": "quiet",
        "enabled_reactions": ["highlight", "association", "discern", "silent"],
        "max_reactions_per_segment": 4,
        "max_curious_reactions": 0,
    },
}


def resolve_skill_policy(profile: SkillProfileName) -> SkillPolicy:
    """Resolve one built-in skill preset."""
    preset = _SKILL_PRESETS.get(profile, _SKILL_PRESETS["balanced"])
    return {
        "profile": preset["profile"],
        "enabled_reactions": list(preset["enabled_reactions"]),
        "max_reactions_per_segment": int(preset["max_reactions_per_segment"]),
        "max_curious_reactions": int(preset["max_curious_reactions"]),
    }


def default_budget_policy() -> BudgetPolicy:
    """Return default execution budget policy."""
    return {
        "max_search_queries_per_segment": 2,
        "max_search_queries_per_chapter": 12,
        "segment_timeout_seconds": 120,
        "max_revisions": 2,
        "token_budget_ratio": 1.5,
        "slice_target_tokens": 420,
        "slice_max_tokens": 700,
        "slice_max_subsegments": 4,
    }


def default_book_analysis_policy() -> BookAnalysisPolicy:
    """Return default execution policy for book-level analysis mode."""
    return {
        "deep_target_ratio": 0.30,
        "min_deep_per_chapter": 1,
        "max_core_claims": 20,
        "max_web_queries": 18,
        "max_queries_per_claim": 2,
        "reuse_existing_notes": True,
    }


def chapter_budget(policy: BudgetPolicy) -> ReaderBudget:
    """Create a mutable chapter-level budget state."""
    return {
        "search_queries_remaining_in_chapter": max(0, int(policy.get("max_search_queries_per_chapter", 12))),
        "search_queries_remaining_in_segment": max(0, int(policy.get("max_search_queries_per_segment", 2))),
        "segment_timeout_seconds": max(1, int(policy.get("segment_timeout_seconds", 120))),
        "segment_timed_out": False,
        "early_stop": False,
        "token_budget_ratio": float(policy.get("token_budget_ratio", 1.5)),
        "slice_target_tokens": max(120, int(policy.get("slice_target_tokens", 420))),
        "slice_max_tokens": max(180, int(policy.get("slice_max_tokens", 700))),
        "slice_max_subsegments": max(1, int(policy.get("slice_max_subsegments", 4))),
        "work_units_remaining": 0,
    }


def segment_budget(chapter_budget_state: ReaderBudget, policy: BudgetPolicy) -> ReaderBudget:
    """Create one segment budget view from chapter budget."""
    return {
        "search_queries_remaining_in_chapter": max(
            0,
            int(chapter_budget_state.get("search_queries_remaining_in_chapter", 0)),
        ),
        "search_queries_remaining_in_segment": min(
            max(0, int(policy.get("max_search_queries_per_segment", 2))),
            max(0, int(chapter_budget_state.get("search_queries_remaining_in_chapter", 0))),
        ),
        "segment_timeout_seconds": max(1, int(policy.get("segment_timeout_seconds", 120))),
        "segment_timed_out": False,
        "early_stop": False,
        "token_budget_ratio": float(policy.get("token_budget_ratio", chapter_budget_state.get("token_budget_ratio", 1.5))),
        "slice_target_tokens": max(
            120,
            int(policy.get("slice_target_tokens", chapter_budget_state.get("slice_target_tokens", 420))),
        ),
        "slice_max_tokens": max(
            180,
            int(policy.get("slice_max_tokens", chapter_budget_state.get("slice_max_tokens", 700))),
        ),
        "slice_max_subsegments": max(
            1,
            int(policy.get("slice_max_subsegments", chapter_budget_state.get("slice_max_subsegments", 4))),
        ),
        "work_units_remaining": 0,
    }
