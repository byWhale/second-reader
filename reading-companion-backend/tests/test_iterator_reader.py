"""Tests for Reader loop helpers."""

from __future__ import annotations

from src.iterator_reader.reader import (
    _compact_segments_for_chapter_reflection,
    _normalize_source_clause,
    _apply_skill_policy,
    apply_chapter_reflection_repairs,
    create_reader_state,
    express_node,
    express_progress_message,
    fuse_curious_results_node,
    read_node,
    reflect_node,
    reflect_progress_message,
    run_chapter_reflection,
    run_reader_segment,
    search_if_curious_node,
    search_progress_message,
    think_node,
    update_memory,
)


def test_update_memory_tracks_reaction_findings_and_questions():
    """Reader memory should keep useful carry-over context."""
    memory = {
        "prior_segment_summaries": [],
        "notable_findings": [],
        "open_threads": [],
        "highlighted_quotes": [],
    }
    segment = {
        "segment_id": "2.3",
        "summary": "作者开始暴露自己论证的隐藏前提",
        "verdict": "pass",
        "reactions": [
            {
                "type": "highlight",
                "anchor_quote": "Dependence is part of moral growth.",
                "content": "作者把依赖理解成道德成长的一部分，而不是软弱。",
                "search_results": [],
            },
            {
                "type": "curious",
                "content": "这种依赖何时会滑向操控？",
                "search_query": "when does dependence become manipulation in relationships",
                "search_results": [],
            },
        ],
        "reflection_summary": "",
    }

    updated = update_memory(memory, segment)

    assert updated["prior_segment_summaries"] == ["2.3: 作者开始暴露自己论证的隐藏前提"]
    assert updated["notable_findings"] == [
        "Dependence is part of moral growth. 作者把依赖理解成道德成长的一部分，而不是软弱。"
    ]
    assert updated["open_threads"] == [
        "这种依赖何时会滑向操控？"
    ]
    assert updated["highlighted_quotes"] == [
        "Dependence is part of moral growth."
    ]


def test_update_memory_prefers_segment_ref_prefix():
    """Visible segment refs should be used in running memory summaries."""
    memory = {
        "prior_segment_summaries": [],
        "notable_findings": [],
        "open_threads": [],
        "highlighted_quotes": [],
    }
    segment = {
        "segment_id": "9.5",
        "segment_ref": "3.5",
        "summary": "A mapped summary",
        "verdict": "pass",
        "reactions": [],
        "reflection_summary": "",
    }

    updated = update_memory(memory, segment)

    assert updated["prior_segment_summaries"] == ["3.5: A mapped summary"]


def test_search_if_curious_only_uses_curious_reactions_and_caps_at_two(monkeypatch):
    """Curiosity search should ignore other reaction types and stop at two queries."""
    calls = []

    def fake_invoke(query: str, max_results: int = 3) -> list[dict]:
        calls.append(query)
        return [
            {
                "title": f"Result for {query}",
                "url": f'https://example.com/{len(calls)}',
                "content": "A compact snippet",
                "score": 0.9,
            }
        ]

    monkeypatch.setattr(
        "src.iterator_reader.reader._invoke_curiosity_search",
        fake_invoke,
    )

    state = {
        "reactions": [
            {"type": "highlight", "content": "先记住这一句", "search_results": []},
            {
                "type": "curious",
                "content": "我想知道 approach-avoidance conflict 的经典定义",
                "search_query": "approach-avoidance conflict definition",
                "search_results": [],
            },
            {
                "type": "association",
                "content": "这像是把欲望和厌恶绑在一起",
                "search_results": [],
            },
            {
                "type": "curious",
                "content": "我想知道这个概念最早来自谁",
                "search_query": "approach-avoidance conflict history",
                "search_results": [],
            },
            {
                "type": "curious",
                "content": "我还想知道它在治疗里怎么用",
                "search_query": "approach-avoidance conflict therapy",
                "search_results": [],
            },
        ]
    }

    updated = search_if_curious_node(state)

    assert calls == [
        "approach-avoidance conflict definition",
        "approach-avoidance conflict history",
    ]
    assert len(updated["search_results"]) == 2
    assert updated["reactions"][0]["search_results"] == []
    assert updated["reactions"][1]["search_results"][0]["title"] == "Result for approach-avoidance conflict definition"
    assert updated["reactions"][3]["search_results"][0]["title"] == "Result for approach-avoidance conflict history"
    assert updated["reactions"][4]["search_results"] == []


def test_reflect_node_skips_when_no_active_reactions():
    """Reflect should short-circuit to skip when the reader stays silent."""
    state = {
        "output_language": "en",
        "reactions": [
            {"type": "silent", "content": "Nothing here feels worth saying.", "search_results": []}
        ],
    }

    updated = reflect_node(state)

    assert updated["reflection"]["verdict"] == "skip"
    assert updated["reflection"]["summary"] == "No reaction here feels worth keeping."
    assert updated["reflection"]["reason_codes"] == ["OTHER"]
    assert updated["reflection"]["target_reaction_indexes"] == []


def test_reflect_node_keeps_structured_reason_codes_and_targets(monkeypatch):
    """Reflect should preserve normalized reason codes and target indexes."""
    monkeypatch.setattr(
        "src.iterator_reader.reader.invoke_json",
        lambda *_args, **_kwargs: {
            "verdict": "revise",
            "summary": "Connection is thin.",
            "selectivity": 3,
            "association_quality": 2,
            "attribution_reasonableness": 3,
            "text_connection": 2,
            "depth": 2,
            "reason_codes": ["WEAK_TEXT_CONNECTION", "low_depth", "UNKNOWN_CODE"],
            "target_reaction_indexes": [1, 5, -1],
            "issues": ["retrospect is vague"],
            "revision_instruction": "Tighten the callback with one concrete earlier quote.",
        },
    )
    state = {
        "chapter_title": "Chapter 2",
        "segment_id": "2.3",
        "segment_summary": "A turning point",
        "segment_text": "Alpha beta gamma",
        "output_language": "en",
        "reactions": [
            {"type": "highlight", "content": "Keep this.", "search_results": []},
            {"type": "retrospect", "content": "This echoes earlier.", "search_results": []},
        ],
        "revision_count": 0,
        "max_revisions": 2,
    }

    updated = reflect_node(state)

    assert updated["reflection"]["verdict"] == "revise"
    assert updated["reflection"]["reason_codes"] == [
        "WEAK_TEXT_CONNECTION",
        "LOW_DEPTH",
    ]
    assert updated["reflection"]["target_reaction_indexes"] == [1]


def test_think_node_passes_visible_segment_ref_to_prompt(monkeypatch):
    """Think prompt should use user-facing segment refs rather than internal ids."""
    captured = {"prompt": ""}

    def fake_invoke_json(_system: str, prompt: str, default: object) -> dict:
        captured["prompt"] = prompt
        return {
            "should_express": False,
            "selected_excerpt": "",
            "reason": "",
            "connections": [],
            "curiosities": [],
            "curiosity_potential": 3,
        }

    monkeypatch.setattr("src.iterator_reader.reader.invoke_json", fake_invoke_json)
    state = create_reader_state(
        chapter_title="Chapter 3",
        segment_id="9.5",
        segment_ref="3.5",
        segment_summary="Mapped summary",
        segment_text="Alpha beta",
        memory={
            "prior_segment_summaries": [],
            "notable_findings": [],
            "open_threads": [],
            "highlighted_quotes": [],
        },
        output_language="en",
    )

    think_node(state)

    assert "语义单元：3.5 / Mapped summary" in captured["prompt"]
    assert "语义单元：9.5" not in captured["prompt"]


def test_think_node_normalizes_selected_excerpt_to_self_contained_clause(monkeypatch):
    """Think output should normalize dangling excerpts before later stages consume them."""
    monkeypatch.setattr(
        "src.iterator_reader.reader.invoke_json",
        lambda *_args, **_kwargs: {
            "should_express": True,
            "selected_excerpt": "there is no culture in which it doesn't exist",
            "reason": "Worth keeping.",
            "connections": [],
            "curiosities": [],
            "curiosity_potential": 3,
        },
    )
    state = create_reader_state(
        chapter_title="Chapter 1",
        segment_id="1.6",
        segment_summary="valuation rules",
        segment_text=(
            "Now, all these evaluations influence valuation in constant and predictable ways. "
            "This tendency is universal: there is no culture in which it doesn’t exist."
        ),
        memory={
            "prior_segment_summaries": [],
            "notable_findings": [],
            "open_threads": [],
            "highlighted_quotes": [],
        },
        output_language="en",
    )

    updated = think_node(state)

    assert updated["thought"]["selected_excerpt"] == "This tendency is universal: there is no culture in which it doesn’t exist."


def test_express_node_normalizes_anchor_quote_to_self_contained_clause(monkeypatch):
    """Express output should normalize dangling anchor quotes from model payloads."""
    monkeypatch.setattr(
        "src.iterator_reader.reader.invoke_json",
        lambda *_args, **_kwargs: {
            "reactions": [
                {
                    "type": "highlight",
                    "anchor_quote": "there is no culture in which it doesn't exist",
                    "content": "A strong universality claim.",
                }
            ]
        },
    )
    state = create_reader_state(
        chapter_title="Chapter 1",
        segment_id="1.6",
        segment_summary="valuation rules",
        segment_text=(
            "Now, all these evaluations influence valuation in constant and predictable ways. "
            "This tendency is universal: there is no culture in which it doesn’t exist."
        ),
        memory={
            "prior_segment_summaries": [],
            "notable_findings": [],
            "open_threads": [],
            "highlighted_quotes": [],
        },
        output_language="en",
    )
    state["thought"] = {
        "should_express": True,
        "selected_excerpt": "",
        "reason": "Worth keeping.",
        "connections": [],
        "curiosities": [],
        "curiosity_potential": 3,
    }

    updated = express_node(state)

    assert updated["reactions"][0]["anchor_quote"] == "This tendency is universal: there is no culture in which it doesn’t exist."


def test_normalize_source_clause_expands_to_nearest_self_contained_clause():
    """Dangling right-hand fragments should expand to the nearest readable clause."""
    segment_text = (
        "Now, all these evaluations influence valuation in constant and predictable ways. "
        "This tendency is universal: there is no culture in which it doesn’t exist. "
        "This is because the principles of valuation are like the principles of logic."
    )

    normalized = _normalize_source_clause(segment_text, "there is no culture in which it doesn't exist")

    assert normalized == "This tendency is universal: there is no culture in which it doesn’t exist."


def test_normalize_source_clause_keeps_existing_self_contained_clause():
    """Already-readable clauses should stay unchanged."""
    segment_text = (
        "This tendency is universal: there is no culture in which it doesn’t exist. "
        "This is because the principles of valuation are like the principles of logic."
    )

    normalized = _normalize_source_clause(
        segment_text,
        "This tendency is universal: there is no culture in which it doesn’t exist.",
    )

    assert normalized == "This tendency is universal: there is no culture in which it doesn’t exist."


def test_normalize_source_clause_keeps_raw_quote_when_source_match_is_unreliable():
    """Unreliable recovery should preserve the original model quote instead of deleting it."""
    segment_text = "People value reliable partners more than chaotic partners."

    normalized = _normalize_source_clause(segment_text, "value coefficient predicts everything")

    assert normalized == "value coefficient predicts everything"


def test_fuse_curious_results_rewrites_curiosity_after_search(monkeypatch):
    """Curious reactions should absorb search findings into their own note."""
    calls = []

    def fake_invoke_json(system_prompt: str, user_prompt: str, default: object) -> dict:
        calls.append((system_prompt, user_prompt))
        return {
            "content": "查了一圈后，我更倾向于把它看成关系伦理里的依赖责任，而不只是抽象的成长修辞。只是这些材料还不足以说明作者是否真的在沿用 care ethics 的框架。"
        }

    monkeypatch.setattr("src.iterator_reader.reader.invoke_json", fake_invoke_json)

    state = {
        "chapter_title": "Chapter 1",
        "segment_id": "1.1",
        "segment_summary": "Dependence and growth",
        "output_language": "zh",
        "reactions": [
            {
                "type": "curious",
                "anchor_quote": "dependence can be formative",
                "content": "我想再查一下 care ethics 如何处理依赖与成长。",
                "search_query": "care ethics dependence moral growth",
                "search_results": [
                    {
                        "title": "Internet Encyclopedia of Philosophy",
                        "url": "https://iep.utm.edu/care-ethics/",
                        "snippet": "Care ethics emphasizes relationships and dependency.",
                        "score": 0.92,
                    }
                ],
            },
            {
                "type": "highlight",
                "content": "先把这句留下来。",
                "search_results": [],
            },
        ],
    }

    updated = fuse_curious_results_node(state)

    assert len(calls) == 1
    assert updated["reactions"][0]["content"].startswith("查了一圈后")
    assert updated["reactions"][0]["search_query"] == "care ethics dependence moral growth"
    assert updated["reactions"][0]["search_results"][0]["title"] == "Internet Encyclopedia of Philosophy"
    assert updated["reactions"][0]["search_results"][0]["snippet"] == "Care ethics emphasizes relationships and dependency."
    assert updated["reactions"][1]["content"] == "先把这句留下来。"


def test_fuse_keeps_non_target_language_search_hits_unchanged(monkeypatch):
    """Search hits should stay original while fused reasoning follows output language."""
    monkeypatch.setattr(
        "src.iterator_reader.reader.invoke_json",
        lambda *_args, **_kwargs: {"content": "After checking sources, I read this as a norm conflict, not a direct contradiction."},
    )
    state = {
        "chapter_title": "Chapter 2",
        "segment_id": "2.1",
        "segment_summary": "Norm conflict",
        "output_language": "en",
        "reactions": [
            {
                "type": "curious",
                "anchor_quote": "norm conflict",
                "content": "Need more context.",
                "search_query": "norm conflict relationship ethics",
                "search_results": [
                    {
                        "title": "规范冲突的社会学解释",
                        "url": "https://example.cn/norm-conflict",
                        "snippet": "规范冲突通常来自角色期待的重叠。",
                        "score": 0.88,
                    }
                ],
            }
        ],
    }

    updated = fuse_curious_results_node(state)

    fused = updated["reactions"][0]
    assert fused["content"].startswith("After checking sources")
    assert fused["search_results"][0]["title"] == "规范冲突的社会学解释"
    assert fused["search_results"][0]["snippet"] == "规范冲突通常来自角色期待的重叠。"
    assert fused["search_results"][0]["url"] == "https://example.cn/norm-conflict"


def test_progress_messages_follow_actual_reactions(monkeypatch):
    """Status lines should reflect the concrete reactions and search queries."""
    monkeypatch.setattr("src.iterator_reader.reader.random.choice", lambda choices: choices[0])

    state = {
        "reactions": [
            {
                "type": "retrospect",
                "content": "这和前面第 3 章的观点呼应了，作者其实在补前面的洞。",
                "search_results": [],
            },
            {
                "type": "curious",
                "content": "我想查一下 social exchange theory",
                "search_query": "social exchange theory origin",
                "search_results": [],
            },
        ]
    }

    assert express_progress_message(state).startswith("🔗 这和前面第 3 章的观点呼应了")
    assert search_progress_message(state) == "🔎 搜索: social exchange theory origin"
    assert reflect_progress_message({"verdict": "pass"}) == "这段想法还行，继续"


def test_express_progress_mentions_discern_and_silence():
    """Express-stage status should surface discern and silent-only cases."""
    discern_state = {
        "reactions": [
            {
                "type": "discern",
                "content": "这里有个隐含前提，作者默认市场和关系共享同一套价值标准。",
                "search_results": [],
            }
        ]
    }
    silent_state = {
        "reactions": [
            {
                "type": "silent",
                "content": "这段主要在过渡。",
                "search_results": [],
            }
        ]
    }

    assert express_progress_message(discern_state).startswith("⚡ 这里有个隐含前提")
    assert express_progress_message(silent_state) == "🤫 这段是过渡，安静读过"


def test_apply_skill_policy_can_disable_curious_reactions():
    """Skill profile should be able to switch off curious reactions."""
    reactions = [
        {"type": "highlight", "content": "Keep this.", "search_results": []},
        {"type": "curious", "content": "Need search.", "search_query": "query", "search_results": []},
    ]
    skill_policy = {
        "profile": "quiet",
        "enabled_reactions": ["highlight", "association", "discern", "silent"],
        "max_reactions_per_segment": 4,
        "max_curious_reactions": 0,
    }
    budget = {
        "search_queries_remaining_in_chapter": 3,
        "search_queries_remaining_in_segment": 2,
        "segment_timeout_seconds": 60,
        "segment_timed_out": False,
        "early_stop": False,
    }

    filtered = _apply_skill_policy(reactions, skill_policy, budget)

    assert len(filtered) == 1
    assert filtered[0]["type"] == "highlight"


def test_search_if_curious_respects_budget_quota(monkeypatch):
    """Curiosity search should respect segment/chapter quotas from budget state."""
    calls = []

    def fake_invoke(query: str, max_results: int = 3) -> list[dict]:
        calls.append(query)
        return [{"title": query, "url": "https://example.com", "content": "snippet", "score": 0.7}]

    monkeypatch.setattr("src.iterator_reader.reader._invoke_curiosity_search", fake_invoke)
    state = {
        "reactions": [
            {"type": "curious", "search_query": "q1", "content": "q1", "search_results": []},
            {"type": "curious", "search_query": "q2", "content": "q2", "search_results": []},
        ],
        "budget": {
            "search_queries_remaining_in_chapter": 1,
            "search_queries_remaining_in_segment": 2,
            "segment_timeout_seconds": 60,
            "segment_timed_out": False,
            "early_stop": False,
        },
    }

    updated = search_if_curious_node(state)

    assert calls == ["q1"]
    assert len(updated["search_results"]) == 1
    assert updated["budget"]["search_queries_remaining_in_chapter"] == 0
    assert updated["budget"]["search_queries_remaining_in_segment"] == 1


def test_run_reader_segment_early_stop_avoids_express(monkeypatch):
    """When Think says not to express, the segment should stop early."""
    state = create_reader_state(
        chapter_title="Chapter 1",
        segment_id="1.1",
        segment_summary="summary",
        segment_text="Alpha beta",
        memory={
            "prior_segment_summaries": [],
            "notable_findings": [],
            "open_threads": [],
            "highlighted_quotes": [],
        },
        output_language="en",
    )
    state["thought"] = None

    monkeypatch.setattr(
        "src.iterator_reader.reader.think_node",
        lambda _state: {
            "thought": {
                "should_express": False,
                "selected_excerpt": "Alpha",
                "reason": "Skip this segment.",
                "connections": [],
                "curiosities": [],
            }
        },
    )
    monkeypatch.setattr("src.iterator_reader.reader.express_node", lambda _state: (_ for _ in ()).throw(RuntimeError("should not run")))

    rendered, final_state = run_reader_segment(state)

    assert rendered["verdict"] == "skip"
    assert final_state["budget"]["early_stop"] is True


def test_run_reader_segment_early_stop_emits_silent_progress(monkeypatch):
    """Think-driven silence should still emit one progress status line."""
    state = create_reader_state(
        chapter_title="Chapter 1",
        segment_id="1.1",
        segment_summary="summary",
        segment_text="Alpha beta",
        memory={
            "prior_segment_summaries": [],
            "notable_findings": [],
            "open_threads": [],
            "highlighted_quotes": [],
        },
        output_language="en",
    )
    monkeypatch.setattr(
        "src.iterator_reader.reader.think_node",
        lambda _state: {
            "thought": {
                "should_express": False,
                "selected_excerpt": "Alpha",
                "reason": "Skip this segment.",
                "connections": [],
                "curiosities": [],
            }
        },
    )

    messages: list[object] = []
    run_reader_segment(state, progress=messages.append)

    assert any("安静读过" in (message.get("message", "") if isinstance(message, dict) else str(message)) for message in messages)


def test_run_reader_segment_timeout_degrades_to_skip(monkeypatch):
    """Timeout budget should degrade one segment to skip for stability."""
    state = create_reader_state(
        chapter_title="Chapter 1",
        segment_id="1.2",
        segment_summary="summary",
        segment_text="Alpha beta",
        memory={
            "prior_segment_summaries": [],
            "notable_findings": [],
            "open_threads": [],
            "highlighted_quotes": [],
        },
        output_language="en",
        budget={
            "search_queries_remaining_in_chapter": 2,
            "search_queries_remaining_in_segment": 1,
            "segment_timeout_seconds": 1,
            "segment_timed_out": False,
            "early_stop": False,
        },
    )

    timestamps = iter([0.0, 2.0, 2.0, 2.0])
    monkeypatch.setattr("src.iterator_reader.reader.time.monotonic", lambda: next(timestamps))
    monkeypatch.setattr(
        "src.iterator_reader.reader.think_node",
        lambda _state: {
            "thought": {
                "should_express": True,
                "selected_excerpt": "Alpha",
                "reason": "Keep going",
                "connections": [],
                "curiosities": [],
            }
        },
    )
    monkeypatch.setattr("src.iterator_reader.reader.express_node", lambda _state: {"reactions": []})

    rendered, final_state = run_reader_segment(state)

    assert rendered["verdict"] == "skip"
    assert final_state["budget"]["segment_timed_out"] is True


def test_run_reader_segment_timeout_keeps_best_effort_reactions(monkeypatch):
    """When budget is tight, existing reactions should be preserved instead of dropped."""
    state = create_reader_state(
        chapter_title="Chapter 1",
        segment_id="1.3",
        segment_summary="summary",
        segment_text="Alpha beta " * 80,
        memory={
            "prior_segment_summaries": [],
            "notable_findings": [],
            "open_threads": [],
            "highlighted_quotes": [],
        },
        output_language="en",
        budget={
            "search_queries_remaining_in_chapter": 2,
            "search_queries_remaining_in_segment": 1,
            "segment_timeout_seconds": 1,
            "segment_timed_out": False,
            "early_stop": False,
            "token_budget_ratio": 1.5,
            "slice_target_tokens": 420,
            "slice_max_tokens": 700,
            "slice_max_subsegments": 4,
            "work_units_remaining": 0,
        },
    )

    timestamps = iter([0.0, 0.2, 1.6, 1.6, 1.6, 1.6, 1.6])
    monkeypatch.setattr("src.iterator_reader.reader.time.monotonic", lambda: next(timestamps))
    monkeypatch.setattr(
        "src.iterator_reader.reader.think_node",
        lambda _state: {
            "thought": {
                "should_express": True,
                "selected_excerpt": "Alpha",
                "reason": "Keep this one.",
                "connections": [],
                "curiosities": [],
                "curiosity_potential": 4,
            }
        },
    )
    monkeypatch.setattr(
        "src.iterator_reader.reader.express_node",
        lambda _state: {
            "reactions": [
                {
                    "type": "highlight",
                    "anchor_quote": "Alpha",
                    "content": "Keep this note",
                    "search_results": [],
                }
            ],
            "search_results": [],
            "reflection": None,
        },
    )
    monkeypatch.setattr("src.iterator_reader.reader.search_if_curious_node", lambda _state: {"reactions": _state.get("reactions", []), "search_results": [], "budget": _state.get("budget", {})})

    rendered, final_state = run_reader_segment(state)

    assert rendered["verdict"] == "pass"
    assert len(rendered["reactions"]) >= 1
    assert final_state["budget"]["segment_timed_out"] is True


def test_run_reader_segment_dynamic_slicing_merges_into_single_segment(monkeypatch):
    """Long dense text should be processed via sub-segments but merged into one final section."""
    long_text = "However, this is a dense argument with numbers 1 2 3. " * 120
    state = create_reader_state(
        chapter_title="Chapter 1",
        segment_id="1.4",
        segment_summary="dense-summary",
        segment_text=long_text,
        memory={
            "prior_segment_summaries": [],
            "notable_findings": [],
            "open_threads": [],
            "highlighted_quotes": [],
        },
        output_language="en",
        budget={
            "search_queries_remaining_in_chapter": 0,
            "search_queries_remaining_in_segment": 0,
            "segment_timeout_seconds": 120,
            "segment_timed_out": False,
            "early_stop": False,
            "token_budget_ratio": 1.5,
            "slice_target_tokens": 180,
            "slice_max_tokens": 260,
            "slice_max_subsegments": 4,
            "work_units_remaining": 0,
        },
    )

    monkeypatch.setattr(
        "src.iterator_reader.reader.think_node",
        lambda _state: {
            "thought": {
                "should_express": True,
                "selected_excerpt": "However, this is a dense argument.",
                "reason": "Worth keeping.",
                "connections": [],
                "curiosities": [],
                "curiosity_potential": 2,
            }
        },
    )
    monkeypatch.setattr(
        "src.iterator_reader.reader.express_node",
        lambda _state: {
            "reactions": [
                {
                    "type": "association",
                    "anchor_quote": _state.get("segment_summary", ""),
                    "content": f'obs::{_state.get("segment_summary", "")}',
                    "search_results": [],
                }
            ],
            "search_results": [],
            "reflection": None,
        },
    )
    monkeypatch.setattr(
        "src.iterator_reader.reader.reflect_node",
        lambda _state: {
            "reflection": {
                "verdict": "pass",
                "summary": "ok",
                "selectivity": 4,
                "association_quality": 4,
                "attribution_reasonableness": 4,
                "text_connection": 4,
                "depth": 4,
                "issues": [],
                "reason_codes": ["OTHER"],
                "target_reaction_indexes": [],
                "revision_instruction": "",
            },
            "revision_instruction": "",
        },
    )

    rendered, _final_state = run_reader_segment(state)

    assert rendered["segment_id"] == "1.4"
    assert rendered["verdict"] == "pass"
    assert len(rendered["reactions"]) >= 2


def test_compact_segments_for_chapter_reflection_keeps_full_clause_quotes():
    """Chapter reflection inputs should not hard-truncate quotes into half-sentences."""
    segments = [
        {
            "segment_id": "1.6",
            "summary": "valuation rules",
            "verdict": "pass",
            "reactions": [
                {
                    "type": "highlight",
                    "anchor_quote": "This tendency is universal: there is no culture in which it doesn’t exist.",
                    "content": "A strong universality claim.",
                    "search_results": [],
                }
            ],
            "reflection_summary": "ok",
            "reflection_reason_codes": [],
        }
    ]

    compact = _compact_segments_for_chapter_reflection(segments)

    assert compact[0]["reactions"][0]["anchor_quote"] == "This tendency is universal: there is no culture in which it doesn’t exist."


def test_run_chapter_reflection_normalizes_and_backfills_quality_flags(monkeypatch):
    """Chapter reflection should keep valid repairs and backfill quality flags per segment."""
    segments = [
        {
            "segment_id": "3.1",
            "summary": "alpha",
            "verdict": "pass",
            "reactions": [{"type": "highlight", "content": "a", "search_results": []}],
            "reflection_summary": "ok",
            "reflection_reason_codes": [],
            "quality_status": "acceptable",
        },
        {
            "segment_id": "3.2",
            "summary": "beta",
            "verdict": "skip",
            "reactions": [],
            "reflection_summary": "skip",
            "reflection_reason_codes": ["LOW_SELECTIVITY"],
            "quality_status": "skipped",
            "skip_reason": "low_selectivity",
        },
        {
            "segment_id": "3.3",
            "summary": "gamma",
            "verdict": "pass",
            "reactions": [{"type": "association", "content": "c", "search_results": []}],
            "reflection_summary": "ok",
            "reflection_reason_codes": [],
            "quality_status": "weak",
        },
    ]

    monkeypatch.setattr(
        "src.iterator_reader.reader.invoke_json",
        lambda *_args, **_kwargs: {
            "segment_repairs": [
                {"segment_id": "3.2", "note": "Recover one concrete observation."},
                {"segment_id": "9.9", "note": "invalid"},
            ],
            "reaction_repairs": [
                {"segment_id": "3.1", "reaction_index": 0, "note": "Tighten attribution."},
                {"segment_id": "3.1", "reaction_index": -1, "note": "invalid"},
            ],
            "chapter_insights": ["Too short"],
            "segment_quality_flags": [
                {"segment_id": "3.1", "quality_status": "strong", "reason": "anchored"},
            ],
        },
    )

    reflection = run_chapter_reflection(
        chapter_title="Chapter 3",
        user_intent=None,
        segments=segments,
        output_language="en",
    )

    assert reflection["segment_repairs"] == [
        {"segment_id": "3.2", "note": "Recover one concrete observation."}
    ]
    assert reflection["reaction_repairs"] == [
        {
            "segment_id": "3.1",
            "reaction_index": 0,
            "note": "Tighten attribution.",
        }
    ]
    assert reflection["chapter_insights"] == []
    quality_by_id = {
        item["segment_id"]: item["quality_status"]
        for item in reflection["segment_quality_flags"]
    }
    assert quality_by_id["3.1"] == "strong"
    assert quality_by_id["3.2"] == "skipped"
    assert quality_by_id["3.3"] in {"acceptable", "weak"}


def test_apply_chapter_reflection_repairs_preserves_public_reactions_and_quality_flags():
    """Chapter reflection should stay internal while still updating quality metadata."""
    segments = [
        {
            "segment_id": "4.1",
            "summary": "skipped segment",
            "verdict": "skip",
            "reactions": [],
            "reflection_summary": "skip",
            "reflection_reason_codes": ["LOW_SELECTIVITY"],
            "quality_status": "skipped",
            "skip_reason": "low_selectivity",
        },
        {
            "segment_id": "4.2",
            "summary": "pass segment",
            "verdict": "pass",
            "reactions": [
                {
                    "type": "association",
                    "content": "Base thought",
                    "search_results": [],
                }
            ],
            "reflection_summary": "ok",
            "reflection_reason_codes": [],
            "quality_status": "acceptable",
        },
    ]
    chapter_reflection = {
        "segment_repairs": [
            {"segment_id": "4.1", "note": "This part frames the chapter's moral premise."}
        ],
        "reaction_repairs": [
            {"segment_id": "4.2", "reaction_index": 0, "note": "Name the hidden assumption explicitly."}
        ],
        "chapter_insights": ["Insight 1", "Insight 2"],
        "segment_quality_flags": [
            {"segment_id": "4.1", "quality_status": "acceptable", "reason": "recovered"},
            {"segment_id": "4.2", "quality_status": "strong", "reason": "deep enough"},
        ],
    }

    patched = apply_chapter_reflection_repairs(
        segments=segments,
        chapter_reflection=chapter_reflection,
        output_language="en",
    )

    assert patched[0]["verdict"] == "skip"
    assert patched[0]["quality_status"] == "acceptable"
    assert patched[0]["reactions"] == []
    assert patched[1]["quality_status"] == "strong"
    assert patched[1]["reactions"][0]["content"] == "Base thought"
