"""Tests for runtime skill/budget policy helpers."""

from __future__ import annotations

from src.iterator_reader.policy import (
    chapter_budget,
    default_book_analysis_policy,
    default_budget_policy,
    resolve_skill_policy,
    segment_budget,
)


def test_resolve_skill_policy_quiet_disables_curious():
    """Quiet profile should disable curiosity reactions."""
    policy = resolve_skill_policy("quiet")

    assert policy["profile"] == "quiet"
    assert "curious" not in policy["enabled_reactions"]
    assert policy["max_curious_reactions"] == 0


def test_segment_budget_is_clamped_by_remaining_chapter_budget():
    """Segment budget should not exceed chapter-level remaining quota."""
    chapter_state = chapter_budget(
        {
            "max_search_queries_per_segment": 3,
            "max_search_queries_per_chapter": 1,
            "segment_timeout_seconds": 120,
            "max_revisions": 2,
        }
    )

    seg = segment_budget(chapter_state, default_budget_policy())

    assert seg["search_queries_remaining_in_chapter"] == 1
    assert seg["search_queries_remaining_in_segment"] == 1


def test_default_budget_policy_exposes_token_and_slicing_controls():
    """Default policy should include token-driven depth and slicing knobs."""
    policy = default_budget_policy()

    assert policy["token_budget_ratio"] == 1.5
    assert policy["slice_target_tokens"] == 420
    assert policy["slice_max_tokens"] == 700
    assert policy["slice_max_subsegments"] == 4


def test_default_book_analysis_policy_exposes_plan_execute_knobs():
    """Book-analysis policy should expose selection and evidence budgets."""
    policy = default_book_analysis_policy()

    assert policy["deep_target_ratio"] == 0.30
    assert policy["min_deep_per_chapter"] == 1
    assert policy["max_core_claims"] == 20
    assert policy["max_web_queries"] == 18
    assert policy["max_queries_per_claim"] == 2
    assert policy["reuse_existing_notes"] is True
