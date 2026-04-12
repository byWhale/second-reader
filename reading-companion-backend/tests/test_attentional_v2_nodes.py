"""Tests for attentional_v2 Phase 4 interpretive nodes."""

from __future__ import annotations

import json

from src.attentional_v2 import nodes as nodes_module
from src.attentional_v2.nodes import (
    build_unitize_preview,
    controller_decision,
    meaning_unit_closure,
    navigate_unitize,
    run_phase4_local_cycle,
    select_local_cycle_span,
    zoom_read,
)
from src.attentional_v2.schemas import (
    build_default_reader_policy,
    build_empty_anchor_memory,
    build_empty_knowledge_activations,
    build_empty_working_pressure,
)
from src.iterator_reader.llm_utils import ReaderLLMError
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism


def _sentence(sentence_id: str, text: str, *, text_role: str = "body", sentence_index: int = 1) -> dict[str, object]:
    return {
        "sentence_id": sentence_id,
        "sentence_index": sentence_index,
        "paragraph_index": sentence_index,
        "text": text,
        "text_role": text_role,
    }


def test_build_unitize_preview_keeps_current_paragraph_remainder_plus_next_paragraph_only():
    """Phase A preview should stay within current paragraph remainder plus next paragraph."""

    chapter_sentences = [
        {"sentence_id": "c1-s1", "sentence_index": 1, "paragraph_index": 1, "text": "Para 1 first.", "text_role": "body"},
        {"sentence_id": "c1-s2", "sentence_index": 2, "paragraph_index": 1, "text": "Para 1 second.", "text_role": "body"},
        {"sentence_id": "c1-s3", "sentence_index": 3, "paragraph_index": 2, "text": "Para 2 first.", "text_role": "body"},
        {"sentence_id": "c1-s4", "sentence_index": 4, "paragraph_index": 2, "text": "Para 2 second.", "text_role": "body"},
        {"sentence_id": "c1-s5", "sentence_index": 5, "paragraph_index": 3, "text": "Section break.", "text_role": "section_heading"},
        {"sentence_id": "c1-s6", "sentence_index": 6, "paragraph_index": 4, "text": "Para 4 first.", "text_role": "body"},
    ]

    preview, preview_range = build_unitize_preview(
        chapter_sentences=chapter_sentences,
        current_sentence_id="c1-s2",
    )

    assert [sentence["sentence_id"] for sentence in preview] == ["c1-s2", "c1-s3", "c1-s4"]
    assert preview_range == {"start_sentence_id": "c1-s2", "end_sentence_id": "c1-s4"}


def test_navigate_unitize_marks_budget_cap_when_guardrail_hits(tmp_path, monkeypatch):
    """navigate_unitize should preserve continuation pressure when the emergency cap truncates the unit."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    reader_policy = build_default_reader_policy()
    reader_policy["unitize"] = {"max_coverage_unit_sentences": 2}

    preview_sentences = [
        {"sentence_id": "c1-s1", "sentence_index": 1, "paragraph_index": 1, "text": "One.", "text_role": "body"},
        {"sentence_id": "c1-s2", "sentence_index": 2, "paragraph_index": 1, "text": "Two.", "text_role": "body"},
        {"sentence_id": "c1-s3", "sentence_index": 3, "paragraph_index": 1, "text": "Three.", "text_role": "body"},
    ]

    monkeypatch.setattr(
        nodes_module,
        "invoke_json",
        lambda _system, _prompt, default: {
            "start_sentence_id": "c1-s1",
            "end_sentence_id": "c1-s3",
            "boundary_type": "paragraph_end",
            "evidence_sentence_ids": ["c1-s2", "c1-s3"],
            "reason": "the move keeps unfolding",
            "continuation_pressure": False,
        },
    )

    decision = navigate_unitize(
        current_sentence=preview_sentences[0],
        preview_sentences=preview_sentences,
        reader_policy=reader_policy,
        output_language="en",
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
    )

    assert decision["end_sentence_id"] == "c1-s2"
    assert decision["boundary_type"] == "budget_cap"
    assert decision["continuation_pressure"] is True
    assert decision["evidence_sentence_ids"] == ["c1-s1", "c1-s2"]


def test_zoom_read_writes_prompt_manifest_and_normalizes_payload(tmp_path, monkeypatch):
    """zoom_read should persist prompt manifests and normalize the LLM payload."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)

    def fake_invoke_json(_system: str, _prompt: str, default: object) -> object:
        return {
            "local_interpretation": "The sentence marks a real turn in the argument.",
            "anchor_quote": "However, value shifts here.",
            "pressure_updates": [
                {
                    "operation_type": "update",
                    "target_store": "working_pressure",
                    "item_id": "pressure-1",
                    "reason": "turn intensifies pressure",
                    "payload": {"kind": "turn"},
                }
            ],
            "activation_updates": [],
            "bridge_candidate": {
                "target_anchor_id": "a-1",
                "target_sentence_id": "c1-s1",
                "relation_type": "contrast",
                "why_now": "the new line turns against the earlier claim",
            },
            "consider_reaction_emission": True,
            "uncertainty_note": "The precise scope of the turn is still open.",
        }

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = zoom_read(
        focal_sentence=_sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        local_context_sentences=[_sentence("c1-s1", "Value looks stable at first.", sentence_index=1)],
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
    )

    manifest = json.loads(
        (output_dir / "_mechanisms" / "attentional_v2" / "internal" / "prompt_manifests" / "zoom_read.json").read_text(
            encoding="utf-8"
        )
    )

    assert result["local_interpretation"] == "The sentence marks a real turn in the argument."
    assert result["anchor_quote"] == "However, value shifts here."
    assert result["pressure_updates"][0]["operation_type"] == "update"
    assert result["bridge_candidate"]["target_anchor_id"] == "a-1"
    assert result["consider_reaction_emission"] is True
    assert manifest["prompt_version"] == "attentional_v2.zoom_read.v5"
    assert manifest["promptset_version"] == "attentional_v2-phase6-v12"


def test_zoom_read_prompt_includes_micro_selectivity_cues(tmp_path, monkeypatch):
    """zoom_read should surface compact analogy/marked-phrase cues in the prompt context."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    captured: dict[str, str] = {}

    def fake_invoke_json(_system: str, prompt: str, default: object) -> object:
        captured["prompt"] = prompt
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    zoom_read(
        focal_sentence=_sentence(
            "c1-s2",
            'The public feast felt "simple" as if the phrase itself ended the argument.',
            sentence_index=2,
        ),
        local_context_sentences=[_sentence("c1-s1", "The room kept praising the arrangement.", sentence_index=1)],
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
    )

    assert "analogy_image" in captured["prompt"]
    assert "marked_phrase" in captured["prompt"]


def test_zoom_read_prompt_includes_narrative_pressure_cues(tmp_path, monkeypatch):
    """zoom_read should surface actor-intention, social-pressure, and stakes cues in the prompt context."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    captured: dict[str, str] = {}

    def fake_invoke_json(_system: str, prompt: str, default: object) -> object:
        captured["prompt"] = prompt
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    zoom_read(
        focal_sentence=_sentence(
            "c1-s2",
            '"O Christian, will you send me back?" All that she may wish to have must come through a single channel and a single choice.',
            sentence_index=2,
        ),
        local_context_sentences=[
            _sentence(
                "c1-s1",
                "He was prepared to teach that the earth was either flat or round, according to the preference of a majority of his patrons.",
                sentence_index=1,
            )
        ],
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
    )

    assert "actor_intention" in captured["prompt"]
    assert "social_pressure" in captured["prompt"]
    assert "causal_stakes" in captured["prompt"]


def test_select_local_cycle_span_narrows_long_span_on_sharp_late_local_hinge():
    """A sharp late-local hinge should be analyzed through a bounded tail span instead of the whole open unit."""

    span = [
        _sentence("c19-s30", "欧洲的移民潮把很多人推向海外。", sentence_index=30),
        _sentence("c19-s31", "美国在中国华侨眼中是“金山”。", sentence_index=31),
        _sentence("c19-s32", "想发财的冒个险去捞一票，成则衣锦还乡，败则为异域之鬼。", sentence_index=32),
        _sentence("c19-s33", "不但去美国的这样，散布在南洋和欧洲的华侨们，多少都是这样的。", sentence_index=33),
        _sentence("c19-s34", "在他们，出外是个手段，不是目的；在国内走码头的山西帮、湖南帮，何尝不是如此？", sentence_index=34),
    ]

    narrowed = select_local_cycle_span(
        current_span_sentences=span,
        trigger_state={"output": "zoom_now", "gate_state": "hot", "signals": []},
    )

    assert [sentence["sentence_id"] for sentence in narrowed] == ["c19-s32", "c19-s33", "c19-s34"]


def test_controller_decision_refuses_bridge_without_candidates(monkeypatch):
    """Controller guardrails should fall back when the model asks to bridge without a real target."""

    monkeypatch.setattr(
        nodes_module,
        "invoke_json",
        lambda *_args, **_kwargs: {
            "chosen_move": "bridge",
            "reason": "the model wants a bridge even without a candidate",
            "target_anchor_id": "",
            "target_sentence_id": "",
        },
    )

    result = controller_decision(
        working_pressure=build_empty_working_pressure(),
        closure_result={
            "closure_decision": "close",
            "meaning_unit_summary": "A local claim has settled enough to move on.",
            "dominant_move": "advance",
            "proposed_state_operations": [],
            "bridge_candidates": [],
            "reaction_candidate": None,
            "unresolved_pressure_note": "",
        },
        bridge_candidates=[],
        gate_state="watch",
        reader_policy=build_default_reader_policy(),
        output_dir=None,
    )

    assert result["chosen_move"] == "advance"


def test_controller_decision_uses_fast_path_without_invoking_llm(monkeypatch):
    """Straightforward advance cases should skip the controller LLM entirely."""

    monkeypatch.setattr(
        nodes_module,
        "invoke_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("controller LLM should not be invoked")),
    )

    result = controller_decision(
        working_pressure=build_empty_working_pressure(),
        closure_result={
            "closure_decision": "close",
            "meaning_unit_summary": "The local point settles cleanly and can move on.",
            "dominant_move": "advance",
            "proposed_state_operations": [],
            "bridge_candidates": [],
            "reaction_candidate": None,
            "unresolved_pressure_note": "",
        },
        bridge_candidates=[],
        gate_state="watch",
        reader_policy=build_default_reader_policy(),
        output_dir=None,
    )

    assert result == {
        "chosen_move": "advance",
        "reason": "controller_fast_path",
        "target_anchor_id": "",
        "target_sentence_id": "",
    }


def test_meaning_unit_closure_includes_anchor_focus_and_backcheck_window(tmp_path, monkeypatch):
    """meaning_unit_closure should carry the local focus packet and tiny backcheck window into the prompt."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    captured: dict[str, str] = {}

    def fake_invoke_json(_system: str, prompt: str, default: object) -> object:
        captured["prompt"] = prompt
        return {
            "closure_decision": "close",
            "meaning_unit_summary": "The reversal stays on the bodily contradiction itself.",
            "anchor_focus": {
                "anchor_quote": "他的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
                "focus_sentence_id": "c15-s192",
                "focus_kind": "sentence",
                "source": "zoom_anchor",
            },
            "anchor_relation": {
                "relation_status": "anchored",
                "relation_to_focus": "The reading returns to the exact bodily contradiction instead of drifting to a saintly aura.",
                "current_focus_quote": "他的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
                "same_chapter_pressure_only": False,
                "local_backcheck_used": True,
                "can_emit_visible_reaction": True,
            },
            "dominant_move": "advance",
            "proposed_state_operations": [],
            "bridge_candidates": [],
            "reaction_candidate": None,
            "unresolved_pressure_note": "",
        }

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = meaning_unit_closure(
        current_span_sentences=[
            _sentence("c15-s191", "世尊的精辟法义则明了、简洁、易懂，不含任何古怪疯狂或荒谬的内容。", sentence_index=191),
            _sentence("c15-s192", "但悉达多的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。", sentence_index=192),
            _sentence("c15-s193", "自世尊佛陀步入涅槃，悉达多是唯一一位我见过的圣人，他让我感受到他的神圣！", sentence_index=193),
        ],
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        boundary_context={"gate_state": "hot"},
        reader_policy=build_default_reader_policy(),
        output_language="zh",
        output_dir=output_dir,
        book_title="悉达多",
        author="赫尔曼·黑塞",
        chapter_title="乔文达",
        zoom_result={
            "local_interpretation": "The local hinge is the contradiction between doctrine and embodied presence.",
            "anchor_quote": "他的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
            "anchor_focus": {
                "anchor_quote": "他的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
                "focus_sentence_id": "c15-s192",
                "focus_kind": "sentence",
                "source": "zoom_anchor",
            },
            "pressure_updates": [],
            "activation_updates": [],
            "bridge_candidate": None,
            "consider_reaction_emission": True,
            "uncertainty_note": "",
        },
    )

    assert '"anchor_focus"' in captured["prompt"]
    assert "Anchor backcheck window:" in captured["prompt"]
    assert result["anchor_relation"]["relation_status"] == "anchored"
    assert result["anchor_relation"]["local_backcheck_used"] is True


def test_run_phase4_local_cycle_holds_reaction_when_anchor_relation_is_unresolved(tmp_path, monkeypatch):
    """The local cycle should keep chapter-adjacent but anchor-unclear moments internal instead of surfacing them."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            return {
                "local_interpretation": "The chapter keeps circling holiness and aura.",
                "anchor_quote": "但悉达多的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": True,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The chapter keeps returning to a saintly aura that exceeds doctrine.",
                "anchor_focus": {
                    "anchor_quote": "但悉达多的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
                    "focus_sentence_id": "c15-s192",
                    "focus_kind": "sentence",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "related_but_unresolved",
                    "relation_to_focus": "This still feels important at the chapter level, but the exact bodily contradiction is not yet closed.",
                    "current_focus_quote": "但悉达多的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
                    "same_chapter_pressure_only": True,
                    "local_backcheck_used": True,
                    "can_emit_visible_reaction": False,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": {
                    "type": "discern",
                    "anchor_quote": "但悉达多的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
                    "content": "The aura of sanctity outruns the doctrinal frame.",
                    "related_anchor_quotes": [],
                    "search_query": "",
                    "search_results": [],
                },
                "unresolved_pressure_note": "The exact local reversal still needs another bounded pass.",
            }
        if "controller-decision node" in system_prompt:
            return {
                "chosen_move": "advance",
                "reason": "the model thinks it can move on",
                "target_anchor_id": "",
                "target_sentence_id": "",
            }
        if "reaction-emission gate" in system_prompt:
            raise AssertionError("reaction_emission should not run when anchor relation is unresolved")
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c15-s193", "自世尊佛陀步入涅槃，悉达多是唯一一位我见过的圣人，他让我感受到他的神圣！", sentence_index=193),
        current_span_sentences=[
            _sentence("c15-s191", "世尊的精辟法义则明了、简洁、易懂，不含任何古怪疯狂或荒谬的内容。", sentence_index=191),
            _sentence("c15-s192", "但悉达多的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。", sentence_index=192),
            _sentence("c15-s193", "自世尊佛陀步入涅槃，悉达多是唯一一位我见过的圣人，他让我感受到他的神圣！", sentence_index=193),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="zh",
        output_dir=output_dir,
        book_title="悉达多",
        author="赫尔曼·黑塞",
        chapter_title="乔文达",
        boundary_context={"gate_state": "hot"},
    )

    assert result["closure_result"]["closure_decision"] == "continue"
    assert result["closure_result"]["dominant_move"] == "dwell"
    assert result["closure_result"]["reaction_candidate"] is None
    assert result["reaction_result"] is None


def test_run_phase4_local_cycle_honors_node_handoff_and_reaction_gate(tmp_path, monkeypatch):
    """The Phase 4 cycle should call the nodes in order and emit an anchored reaction only when warranted."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            calls.append("zoom")
            return {
                "local_interpretation": "The line earns closer reading because it reverses the local expectation.",
                "anchor_quote": "However, value shifts here.",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": True,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The local span closes around a contrastive turn.",
                "anchor_focus": {
                    "anchor_quote": "However, value shifts here.",
                    "focus_sentence_id": "c1-s2",
                    "focus_kind": "sentence",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The turn sits in the exact reversal sentence instead of a broad chapter summary.",
                    "current_focus_quote": "However, value shifts here.",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": True,
                },
                "dominant_move": "bridge",
                "proposed_state_operations": [
                    {
                        "operation_type": "update",
                        "target_store": "working_pressure",
                        "item_id": "pressure-2",
                        "reason": "contrast became central",
                        "payload": {"kind": "contrast"},
                    }
                ],
                "bridge_candidates": [],
                "reaction_candidate": {
                    "type": "discern",
                    "anchor_quote": "However, value shifts here.",
                    "content": "The author quietly changes the frame rather than just extending the earlier claim.",
                    "related_anchor_quotes": ["Value looks stable at first."],
                    "search_query": "",
                    "search_results": [],
                },
                "unresolved_pressure_note": "The turn may require a callback.",
            }
        if "controller-decision node" in system_prompt:
            calls.append("controller")
            return {
                "chosen_move": "bridge",
                "reason": "the turn should be tested against the earlier frame",
                "target_anchor_id": "a-1",
                "target_sentence_id": "c1-s1",
            }
        if "reaction-emission gate" in system_prompt:
            calls.append("emit")
            return {
                "decision": "emit",
                "reason": "the moment is anchored and interpretively real",
                "reaction": {
                    "type": "discern",
                    "anchor_quote": "However, value shifts here.",
                    "content": "The author quietly changes the frame rather than just extending the earlier claim.",
                    "related_anchor_quotes": ["Value looks stable at first."],
                    "search_query": "",
                    "search_results": [],
                },
            }
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        current_span_sentences=[
            _sentence("c1-s1", "Value looks stable at first.", sentence_index=1),
            _sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        ],
        trigger_state={
            "output": "zoom_now",
            "gate_state": "hot",
        },
        working_pressure=build_empty_working_pressure(),
        anchor_memory={
            **build_empty_anchor_memory(),
            "anchor_records": [
                {
                    "anchor_id": "a-1",
                    "sentence_start_id": "c1-s1",
                    "sentence_end_id": "c1-s1",
                    "quote": "Value looks stable at first.",
                    "anchor_kind": "claim",
                    "status": "active",
                }
            ],
        },
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[
            {
                "candidate_kind": "anchor_memory",
                "target_anchor_id": "a-1",
                "target_sentence_id": "c1-s1",
                "retrieval_channel": "anchor_memory",
                "relation_type": "contrast",
                "score": 0.8,
                "why_now": "the new line reverses the earlier frame",
                "quote": "Value looks stable at first.",
            }
        ],
        output_language="en",
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    emit_manifest = output_dir / "_mechanisms" / "attentional_v2" / "internal" / "prompt_manifests" / "reaction_emission.json"

    assert calls == ["zoom", "closure", "controller", "emit"]
    assert result["zoom_result"]["anchor_quote"] == "However, value shifts here."
    assert result["closure_result"]["closure_decision"] == "close"
    assert result["closure_result"]["anchor_relation"]["relation_status"] == "anchored"
    assert result["controller_result"]["chosen_move"] == "bridge"
    assert result["reaction_result"]["decision"] == "emit"
    assert result["reaction_result"]["reaction"]["type"] == "discern"
    assert result["bridge_candidates"][0]["target_anchor_id"] == "a-1"
    assert emit_manifest.exists()


def test_run_phase4_local_cycle_passes_local_cues_into_reaction_emission(tmp_path, monkeypatch):
    """reaction_emission should receive local micro-selectivity context and the suggested reaction."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    seen_prompt: dict[str, str] = {}

    def fake_invoke_json(system_prompt: str, prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            return {
                "local_interpretation": 'The phrase "simple" is doing suspiciously heavy local work.',
                "anchor_quote": '"simple"',
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": True,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            return {
                "closure_decision": "close",
                "meaning_unit_summary": 'The sentence uses a marked phrase to flatten a contested point.',
                "anchor_focus": {
                    "anchor_quote": '"simple"',
                    "focus_sentence_id": "c1-s2",
                    "focus_kind": "phrase",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": 'The quoted word "simple" is the exact local hinge that needs surfacing.',
                    "current_focus_quote": '"simple"',
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": True,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": {
                    "type": "discern",
                    "anchor_quote": '"simple"',
                    "content": 'The quoted word pretends to settle a harder argument than it actually does.',
                    "related_anchor_quotes": [],
                    "search_query": "",
                    "search_results": [],
                },
                "unresolved_pressure_note": "",
            }
        if "controller-decision node" in system_prompt:
            return {
                "chosen_move": "advance",
                "reason": "the local point can move forward after surfacing the phrase pressure",
                "target_anchor_id": "",
                "target_sentence_id": "",
            }
        if "reaction-emission gate" in system_prompt:
            seen_prompt["prompt"] = prompt
            return {
                "decision": "emit",
                "reason": "the marked phrase deserves a precise visible reaction",
                "reaction": {
                    "type": "discern",
                    "anchor_quote": '"simple"',
                    "content": 'The quoted word pretends to settle a harder argument than it actually does.',
                    "related_anchor_quotes": [],
                    "search_query": "",
                    "search_results": [],
                },
            }
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence(
            "c1-s2",
            'The public feast felt "simple" as if the phrase itself ended the argument.',
            sentence_index=2,
        ),
        current_span_sentences=[
            _sentence("c1-s1", "The room kept praising the arrangement.", sentence_index=1),
            _sentence("c1-s2", 'The public feast felt "simple" as if the phrase itself ended the argument.', sentence_index=2),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    assert result["reaction_result"]["decision"] == "emit"
    assert result["reaction_result"]["reaction"]["type"] == "discern"
    assert "analogy_image" in seen_prompt["prompt"]
    assert "marked_phrase" in seen_prompt["prompt"]
    assert '"type": "discern"' in seen_prompt["prompt"]


def test_run_phase4_local_cycle_keeps_zoom_bridge_hints(monkeypatch):
    """The Phase 4 bridge pool should keep a valid zoom-level bridge hint."""

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            return {
                "local_interpretation": "The line explicitly points back to an earlier claim.",
                "anchor_quote": "However, value shifts here.",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {
                    "target_anchor_id": "",
                    "target_sentence_id": "c1-s1",
                    "relation_type": "contrast",
                    "why_now": "the sentence explicitly turns back toward the opening claim",
                },
                "consider_reaction_emission": False,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The local unit is closed but bridge-aware.",
                "anchor_focus": {
                    "anchor_quote": "However, value shifts here.",
                    "focus_sentence_id": "c1-s2",
                    "focus_kind": "sentence",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The local turn is already settled and can now look backward honestly.",
                    "current_focus_quote": "However, value shifts here.",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": False,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "",
            }
        if "controller-decision node" in system_prompt:
            return {
                "chosen_move": "bridge",
                "reason": "the callback should be tested against the earlier claim",
                "target_anchor_id": "",
                "target_sentence_id": "",
            }
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        current_span_sentences=[
            _sentence("c1-s1", "Value looks stable at first.", sentence_index=1),
            _sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=None,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    assert result["bridge_candidates"][0]["target_sentence_id"] == "c1-s1"
    assert result["controller_result"]["chosen_move"] == "bridge"
    assert result["controller_result"]["target_sentence_id"] == "c1-s1"


def test_run_phase4_local_cycle_skips_lazy_bridge_loader_without_bridge_pressure(monkeypatch):
    """Deterministic bridge retrieval should stay idle when the local moment has no bridge pressure."""

    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            calls.append("zoom")
            return {
                "local_interpretation": "The line deserves local attention but does not point backward.",
                "anchor_quote": "However, value shifts here.",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": False,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The local turn settles cleanly without bridge pull.",
                "anchor_focus": {
                    "anchor_quote": "However, value shifts here.",
                    "focus_sentence_id": "c1-s2",
                    "focus_kind": "sentence",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The local turn is specific and already closed on the focal sentence.",
                    "current_focus_quote": "However, value shifts here.",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": False,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "",
            }
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        current_span_sentences=[
            _sentence("c1-s1", "Value looks stable at first.", sentence_index=1),
            _sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        lazy_bridge_loader=lambda: (_ for _ in ()).throw(AssertionError("lazy bridge loader should stay idle")),
        output_language="en",
        output_dir=None,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
        boundary_context={"gate_state": "hot", "candidate_boundary": True, "callback_anchor_ids": []},
    )

    assert calls == ["zoom", "closure"]
    assert result["candidate_set"] is None
    assert result["bridge_candidates"] == []
    assert result["controller_result"]["reason"] == "controller_fast_path"


def test_run_phase4_local_cycle_materializes_lazy_bridge_candidates_once_when_pressure_present(monkeypatch):
    """Bridge pressure should materialize deterministic retrieval once and reuse it inside the local cycle."""

    calls: list[str] = []
    loader_calls: list[str] = []

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            calls.append("zoom")
            return {
                "local_interpretation": "The line points back toward an earlier anchor.",
                "anchor_quote": "However, value shifts here.",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": False,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The local turn stays bridge-aware.",
                "anchor_focus": {
                    "anchor_quote": "However, value shifts here.",
                    "focus_sentence_id": "c1-s2",
                    "focus_kind": "sentence",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The local turn is settled enough to justify a narrow backward check.",
                    "current_focus_quote": "However, value shifts here.",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": False,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "",
            }
        if "controller-decision node" in system_prompt:
            calls.append("controller")
            return {
                "chosen_move": "bridge",
                "reason": "the callback should be tested against the earlier anchor",
                "target_anchor_id": "",
                "target_sentence_id": "",
            }
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        current_span_sentences=[
            _sentence("c1-s1", "Value looks stable at first.", sentence_index=1),
            _sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        lazy_bridge_loader=lambda: (
            loader_calls.append("load") or {
                "current_sentence_id": "c1-s2",
                "memory_candidates": [],
                "lookback_candidates": [
                    {
                        "candidate_kind": "source_callback",
                        "sentence_id": "c1-s1",
                        "chapter_id": 1,
                        "chapter_title": "Chapter 1",
                        "text": "Value looks stable at first.",
                        "text_role": "body",
                        "locator": {},
                        "overlap_score": 3.5,
                        "retrieval_channel": "source_callback",
                        "relation_type": "callback",
                    }
                ],
            },
            [
                {
                    "candidate_kind": "source_callback",
                    "target_anchor_id": "",
                    "target_sentence_id": "c1-s1",
                    "retrieval_channel": "source_callback",
                    "relation_type": "callback",
                    "score": 3.5,
                    "why_now": "",
                    "quote": "Value looks stable at first.",
                }
            ],
        ),
        output_language="en",
        output_dir=None,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
        boundary_context={"gate_state": "hot", "candidate_boundary": True, "callback_anchor_ids": ["a-1"]},
    )

    assert calls == ["zoom", "closure", "controller"]
    assert loader_calls == ["load"]
    assert result["candidate_set"]["current_sentence_id"] == "c1-s2"
    assert result["bridge_candidates"][0]["target_sentence_id"] == "c1-s1"
    assert result["controller_result"]["chosen_move"] == "bridge"
    assert result["controller_result"]["target_sentence_id"] == "c1-s1"


def test_run_phase4_local_cycle_materializes_lazy_bridge_candidates_on_explicit_callback_cue(monkeypatch):
    """An explicit backward-looking cue should open deterministic bridge retrieval even without prior callback state."""

    loader_calls: list[str] = []
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        nodes_module,
        "zoom_read",
        lambda **_kwargs: {
            "local_interpretation": "The sentence explicitly turns back to the diver example.",
            "anchor_quote": "前面举了潜水员的例子",
            "anchor_focus": {
                "anchor_quote": "前面举了潜水员的例子",
                "focus_sentence_id": "c22-s40",
                "focus_kind": "phrase",
                "source": "zoom_anchor",
            },
            "pressure_updates": [],
            "activation_updates": [],
            "bridge_candidate": None,
            "consider_reaction_emission": False,
            "uncertainty_note": "",
        },
    )
    monkeypatch.setattr(
        nodes_module,
        "meaning_unit_closure",
        lambda **_kwargs: {
            "closure_decision": "close",
            "meaning_unit_summary": "The current sentence cashes out the earlier diver example into a reputation bridge.",
            "anchor_focus": {
                "anchor_quote": "前面举了潜水员的例子",
                "focus_sentence_id": "c22-s40",
                "focus_kind": "phrase",
                "source": "zoom_anchor",
            },
            "anchor_relation": {
                "relation_status": "anchored",
                "relation_to_focus": "The sentence names the earlier example directly and turns it into the current argument.",
                "current_focus_quote": "前面举了潜水员的例子",
                "same_chapter_pressure_only": False,
                "local_backcheck_used": False,
                "can_emit_visible_reaction": False,
            },
            "dominant_move": "advance",
            "proposed_state_operations": [],
            "bridge_candidates": [],
            "reaction_candidate": None,
            "unresolved_pressure_note": "",
        },
    )

    def fake_controller_decision(**kwargs):
        captured["bridge_candidates"] = kwargs["bridge_candidates"]
        return {
            "chosen_move": "bridge",
            "reason": "the explicit callback cue should test the earlier diver example",
            "target_anchor_id": "",
            "target_sentence_id": "c22-s18",
        }

    monkeypatch.setattr(nodes_module, "controller_decision", fake_controller_decision)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c22-s40", "前面举了潜水员的例子，由于你的潜水技能非常出色，知名度很高。", sentence_index=40),
        current_span_sentences=[
            _sentence("c22-s39", "我认为，赚钱很关键的一点就是知名度和信誉度。", sentence_index=39),
            _sentence("c22-s40", "前面举了潜水员的例子，由于你的潜水技能非常出色，知名度很高。", sentence_index=40),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot", "signals": []},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        lazy_bridge_loader=lambda: (
            loader_calls.append("load") or {
                "current_sentence_id": "c22-s40",
                "memory_candidates": [],
                "lookback_candidates": [
                    {
                        "candidate_kind": "source_callback",
                        "sentence_id": "c22-s18",
                        "chapter_id": 22,
                        "chapter_title": "如何获得运气",
                        "text": "例如，假设你是世界上最好的深海潜水员。",
                        "text_role": "body",
                        "locator": {},
                        "overlap_score": 4.0,
                        "retrieval_channel": "source_callback",
                        "relation_type": "callback",
                    }
                ],
            },
            [
                {
                    "candidate_kind": "source_callback",
                    "target_anchor_id": "",
                    "target_sentence_id": "c22-s18",
                    "retrieval_channel": "source_callback",
                    "relation_type": "callback",
                    "score": 4.0,
                    "why_now": "",
                    "quote": "例如，假设你是世界上最好的深海潜水员。",
                }
            ],
        ),
        output_language="zh",
        output_dir=None,
        book_title="纳瓦尔宝典",
        author="纳瓦尔",
        chapter_title="如何获得运气",
        boundary_context={"gate_state": "hot", "callback_anchor_ids": []},
    )

    assert loader_calls == ["load"]
    assert captured["bridge_candidates"][0]["target_sentence_id"] == "c22-s18"
    assert result["controller_result"]["chosen_move"] == "bridge"
    assert result["candidate_set"]["current_sentence_id"] == "c22-s40"


def test_run_phase4_local_cycle_force_closes_anchored_sharp_local_hinge(monkeypatch):
    """A bounded late-local hinge that is already anchored should close instead of being re-absorbed into a broad open span."""

    monkeypatch.setattr(
        nodes_module,
        "zoom_read",
        lambda **_kwargs: {
            "local_interpretation": "The sentence flips emigration from a goal into a means.",
            "anchor_quote": "出外是个手段，不是目的",
            "anchor_focus": {
                "anchor_quote": "出外是个手段，不是目的",
                "focus_sentence_id": "c19-s34",
                "focus_kind": "phrase",
                "source": "zoom_anchor",
            },
            "pressure_updates": [],
            "activation_updates": [],
            "bridge_candidate": None,
            "consider_reaction_emission": False,
            "uncertainty_note": "",
        },
    )
    monkeypatch.setattr(
        nodes_module,
        "meaning_unit_closure",
        lambda **_kwargs: {
            "closure_decision": "continue",
            "meaning_unit_summary": "The line makes a clean local distinction: going abroad is a means, not the end itself.",
            "anchor_focus": {
                "anchor_quote": "出外是个手段，不是目的",
                "focus_sentence_id": "c19-s34",
                "focus_kind": "phrase",
                "source": "zoom_anchor",
            },
            "anchor_relation": {
                "relation_status": "anchored",
                "relation_to_focus": "The distinction resolves directly on the phrase that reframes emigration.",
                "current_focus_quote": "出外是个手段，不是目的",
                "same_chapter_pressure_only": False,
                "local_backcheck_used": True,
                "can_emit_visible_reaction": True,
            },
            "dominant_move": "advance",
            "proposed_state_operations": [],
            "bridge_candidates": [],
            "reaction_candidate": {
                "type": "discern",
                "anchor_quote": "出外是个手段，不是目的",
                "content": "这句话把“出外”的位置压回工具层，不再把离乡本身当作终点。",
                "related_anchor_quotes": [],
                "search_query": "",
                "search_results": [],
            },
            "unresolved_pressure_note": "",
        },
    )
    monkeypatch.setattr(
        nodes_module,
        "reaction_emission",
        lambda **_kwargs: {
            "decision": "withhold",
            "reason": "not testing emission here",
            "reaction": None,
        },
    )

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c19-s34", "在他们，出外是个手段，不是目的；在国内走码头的山西帮、湖南帮，何尝不是如此？", sentence_index=34),
        current_span_sentences=[
            _sentence("c19-s32", "想发财的冒个险去捞一票，成则衣锦还乡，败则为异域之鬼。", sentence_index=32),
            _sentence("c19-s33", "不但去美国的这样，散布在南洋和欧洲的华侨们，多少都是这样的。", sentence_index=33),
            _sentence("c19-s34", "在他们，出外是个手段，不是目的；在国内走码头的山西帮、湖南帮，何尝不是如此？", sentence_index=34),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot", "signals": []},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="zh",
        output_dir=None,
        book_title="美国人的性格",
        author="费孝通",
        chapter_title="第十九章",
        boundary_context={"gate_state": "hot", "local_cycle_scope": "narrow_focus_tail"},
    )

    assert result["closure_result"]["closure_decision"] == "close"
    assert result["closure_result"]["reaction_candidate"]["anchor_quote"] == "出外是个手段，不是目的"


def test_run_phase4_local_cycle_force_closes_overlong_unresolved_narrow_tail(monkeypatch):
    """An overlong narrowed tail should close honestly instead of staying trapped inside a giant open span."""

    monkeypatch.setattr(
        nodes_module,
        "zoom_read",
        lambda **_kwargs: {
            "local_interpretation": "The text is still circling a bodily contradiction.",
            "anchor_quote": "他的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
            "anchor_focus": {
                "anchor_quote": "他的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
                "focus_sentence_id": "c15-s192",
                "focus_kind": "sentence",
                "source": "zoom_anchor",
            },
            "pressure_updates": [],
            "activation_updates": [],
            "bridge_candidate": None,
            "consider_reaction_emission": True,
            "uncertainty_note": "The precise relation is still not closing.",
        },
    )
    monkeypatch.setattr(
        nodes_module,
        "meaning_unit_closure",
        lambda **_kwargs: {
            "closure_decision": "continue",
            "meaning_unit_summary": "The chapter still feels charged, but the exact bodily hinge is not cleanly closed yet.",
            "anchor_focus": {
                "anchor_quote": "他的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
                "focus_sentence_id": "c15-s192",
                "focus_kind": "sentence",
                "source": "zoom_anchor",
            },
            "anchor_relation": {
                "relation_status": "related_but_unresolved",
                "relation_to_focus": "The local aura pressure is still nearby, but it has not settled back onto the exact bodily contradiction.",
                "current_focus_quote": "他的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。",
                "same_chapter_pressure_only": True,
                "local_backcheck_used": True,
                "can_emit_visible_reaction": False,
            },
            "dominant_move": "dwell",
            "proposed_state_operations": [],
            "bridge_candidates": [],
            "reaction_candidate": None,
            "unresolved_pressure_note": "Still not locally closed.",
        },
    )
    monkeypatch.setattr(
        nodes_module,
        "reaction_emission",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("reaction_emission should stay gated off")),
    )

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c15-s193", "自世尊佛陀步入涅槃，悉达多是唯一一位我见过的圣人，他让我感受到他的神圣！", sentence_index=193),
        current_span_sentences=[
            _sentence("c15-s191", "世尊的精辟法义则明了、简洁、易懂，不含任何古怪疯狂或荒谬的内容。", sentence_index=191),
            _sentence("c15-s192", "但悉达多的手脚,他的双眼、额头，他的微笑、问候和姿态却不同于他的思想。", sentence_index=192),
            _sentence("c15-s193", "自世尊佛陀步入涅槃，悉达多是唯一一位我见过的圣人，他让我感受到他的神圣！", sentence_index=193),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot", "signals": []},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="zh",
        output_dir=None,
        book_title="悉达多",
        author="赫尔曼·黑塞",
        chapter_title="乔文达",
        boundary_context={"gate_state": "hot", "local_cycle_scope": "narrow_focus_tail", "cadence_counter": 9},
    )

    assert result["closure_result"]["closure_decision"] == "close"
    assert result["closure_result"]["reaction_candidate"] is None
    assert result["reaction_result"] is None


def test_zoom_read_prompt_receives_local_textual_cues(monkeypatch):
    """Zoom prompt should include deterministic cue packets for local callback/distinction pressure."""

    captured_prompt: dict[str, str] = {}

    def fake_invoke_json(_system: str, prompt: str, default: object) -> object:
        captured_prompt["value"] = prompt
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    zoom_read(
        focal_sentence=_sentence("c1-s3", "因為這和伊先前听慣的“nganga”的哭聲大不同了，所以竟不知道這也是一种哭。", sentence_index=3),
        local_context_sentences=[
            _sentence("c1-s1", "忽而听到嗚嗚咽咽的聲音了。", sentence_index=1),
            _sentence("c1-s2", "卻見方板底下的小眼睛里含著兩粒眼淚。", sentence_index=2),
        ],
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        output_language="zh",
        output_dir=None,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
    )

    prompt_text = captured_prompt["value"]
    assert "Deterministic local textual cues" in prompt_text
    assert "recognition_gap" in prompt_text
    assert "distinction_cue" in prompt_text


def test_run_phase4_local_cycle_keeps_compact_local_anchor_bounded_without_zoom_gate(monkeypatch):
    """A compact anchor by itself should no longer open reaction emission."""

    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            calls.append("zoom")
            return {
                "local_interpretation": "The sentence turns on one compact principle phrase.",
                "anchor_quote": "one very simple principle",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": False,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "Mill compresses the turn into one compact principle phrase.",
                "anchor_focus": {
                    "anchor_quote": "one very simple principle",
                    "focus_sentence_id": "c1-s1",
                    "focus_kind": "phrase",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The compact phrase is already the locally settled hinge, but zoom kept the reaction gate closed.",
                    "current_focus_quote": "one very simple principle",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": False,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "",
            }
        if "reaction-emission gate" in system_prompt:
            raise AssertionError("reaction_emission should stay gated off")
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c1-s1", "This sentence turns on one very simple principle.", sentence_index=1),
        current_span_sentences=[
            _sentence("c1-s1", "This sentence turns on one very simple principle.", sentence_index=1),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=None,
        book_title="On Liberty",
        author="Mill",
        chapter_title="Chapter 1",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    assert calls == ["zoom", "closure"]
    assert result["reaction_result"] is None


def test_run_phase4_local_cycle_uses_pressure_cues_for_bounded_synthetic_candidate(monkeypatch):
    """Narrative pressure cues may synthesize one bounded reaction candidate when zoom explicitly opens the gate."""

    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            calls.append("zoom")
            return {
                "local_interpretation": "The plea turns the moment on another person's authority over whether the speaker stays or is returned.",
                "anchor_quote": '"O Christian, will you send me back?"',
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": True,
                "uncertainty_note": "The power relation is explicit but the outcome remains open.",
            }
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The question compresses dependence and vulnerability into one direct appeal.",
                "anchor_focus": {
                    "anchor_quote": '"O Christian, will you send me back?"',
                    "focus_sentence_id": "c1-s1",
                    "focus_kind": "sentence",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The plea itself is the local hinge, and the unresolved power relation stays visible right on that line.",
                    "current_focus_quote": '"O Christian, will you send me back?"',
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": True,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "The local pressure stays open because the addressee's answer determines whether the speaker is sent back.",
            }
        if "reaction-emission gate" in system_prompt:
            calls.append("emit")
            assert '"compact_local_anchor": false' in prompt.lower()
            assert '"synthetic_local_candidate": true' in prompt.lower()
            assert '"type": "curious"' in prompt
            return {
                "decision": "emit",
                "reason": "one bounded visible question is warranted",
                "reaction": None,
            }
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c1-s1", '"O Christian, will you send me back?"', sentence_index=1),
        current_span_sentences=[_sentence("c1-s1", '"O Christian, will you send me back?"', sentence_index=1)],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=None,
        book_title="Walden",
        author="Thoreau",
        chapter_title="Visitors",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    assert calls == ["zoom", "closure", "emit"]
    assert result["reaction_result"]["decision"] == "emit"
    assert result["reaction_result"]["reaction"]["type"] == "curious"
    assert result["reaction_result"]["reaction"]["anchor_quote"] == '"O Christian, will you send me back?"'


def test_run_phase4_local_cycle_keeps_pressure_cues_bounded_without_zoom_gate(monkeypatch):
    """Pressure cues alone should not force reaction emission when zoom keeps the gate closed."""

    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            calls.append("zoom")
            return {
                "local_interpretation": "The sentence frames truth as subordinate to audience demand.",
                "anchor_quote": "He was prepared to teach that the earth was either flat or round, according to the preference of a majority of his patrons.",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": False,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The line satirizes a teacher whose content bends to patron preference.",
                "anchor_focus": {
                    "anchor_quote": "preference of a majority of his patrons",
                    "focus_sentence_id": "c1-s1",
                    "focus_kind": "phrase",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The satire is still local and answerable to the patron-pressure phrase, but zoom never opened a visible reaction.",
                    "current_focus_quote": "preference of a majority of his patrons",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": False,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "",
            }
        if "reaction-emission gate" in system_prompt:
            raise AssertionError("reaction_emission should stay gated off")
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence(
            "c1-s1",
            "He was prepared to teach that the earth was either flat or round, according to the preference of a majority of his patrons.",
            sentence_index=1,
        ),
        current_span_sentences=[
            _sentence(
                "c1-s1",
                "He was prepared to teach that the earth was either flat or round, according to the preference of a majority of his patrons.",
                sentence_index=1,
            )
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=None,
        book_title="Up from Slavery",
        author="Booker T. Washington",
        chapter_title="The Reconstruction Period",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    assert calls == ["zoom", "closure"]
    assert result["reaction_result"] is None


def test_run_phase4_local_cycle_keeps_pressure_cues_bounded_without_zoom_gate(monkeypatch):
    """High-signal pressure cues should stay quiet when zoom never opens the reaction gate."""

    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The sentence turns a schooling mismatch into a concrete social consequence.",
                "anchor_focus": {
                    "anchor_quote": "went to the bad",
                    "focus_sentence_id": "c1-s1",
                    "focus_kind": "phrase",
                    "source": "focal_sentence",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The consequence phrase is locally clear, but the runner is only on the watch path here.",
                    "current_focus_quote": "went to the bad",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": False,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "",
            }
        if "reaction-emission gate" in system_prompt:
            raise AssertionError("reaction_emission should stay gated off")
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence(
            "c1-s1",
            "The result of this was in too many cases that the girls went to the bad.",
            sentence_index=1,
        ),
        current_span_sentences=[
            _sentence(
                "c1-s1",
                "The result of this was in too many cases that the girls went to the bad.",
                sentence_index=1,
            )
        ],
        trigger_state={"output": "monitor", "gate_state": "watch"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=None,
        book_title="Up from Slavery",
        author="Booker T. Washington",
        chapter_title="The Reconstruction Period",
        boundary_context={"gate_state": "watch", "candidate_boundary": True},
    )

    assert calls == ["closure"]
    assert result["zoom_result"] is None
    assert result["reaction_result"] is None


def test_run_phase4_local_cycle_uses_multi_cue_pressure_for_bounded_three_sentence_span(monkeypatch):
    """A slightly wider narrative-pressure span may emit once when unresolved multi-cue pressure stays live."""

    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            calls.append("zoom")
            return {
                "local_interpretation": "The choice keeps motive, outside pressure, and consequence in one unresolved frame.",
                "anchor_quote": "",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": True,
                "uncertainty_note": "The sentence cluster stays unresolved because the decision is still under pressure.",
            }
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The passage holds motive, patron pressure, and the likely cost together.",
                "anchor_focus": {
                    "anchor_quote": "preference of a majority of his patrons",
                    "focus_sentence_id": "c1-s2",
                    "focus_kind": "phrase",
                    "source": "focal_sentence",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The local hinge is the patron-pressure phrase, now widened by the neighboring motive and consequence sentences.",
                    "current_focus_quote": "preference of a majority of his patrons",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": True,
                    "can_emit_visible_reaction": True,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "The choice is still live because other people can still force the speaker's path.",
            }
        if "reaction-emission gate" in system_prompt:
            calls.append("emit")
            assert '"synthetic_local_candidate": true' in prompt.lower()
            assert '"type": "curious"' in prompt
            assert "He was prepared to teach" in prompt
            return {
                "decision": "emit",
                "reason": "the wider pressure span still warrants one bounded visible question",
                "reaction": None,
            }
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence(
            "c1-s2",
            "He was prepared to teach that the earth was either flat or round, according to the preference of a majority of his patrons.",
            sentence_index=2,
        ),
        current_span_sentences=[
            _sentence("c1-s1", "He wished to keep his place and felt that he could not enjoy losing it.", sentence_index=1),
            _sentence(
                "c1-s2",
                "He was prepared to teach that the earth was either flat or round, according to the preference of a majority of his patrons.",
                sentence_index=2,
            ),
            _sentence("c1-s3", "The result of this was that his students would be the ones to suffer for it.", sentence_index=3),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=None,
        book_title="Up from Slavery",
        author="Booker T. Washington",
        chapter_title="The Reconstruction Period",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    assert calls == ["zoom", "closure", "emit"]
    assert result["reaction_result"]["decision"] == "emit"
    assert result["reaction_result"]["reaction"]["type"] == "curious"
    assert result["reaction_result"]["reaction"]["anchor_quote"].startswith("He was prepared to teach")


def test_run_phase4_local_cycle_keeps_three_sentence_pressure_span_bounded_without_unresolved_note(monkeypatch):
    """A wider span still stays quiet when the unresolved narrative pressure is not explicitly live."""

    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            calls.append("zoom")
            return {
                "local_interpretation": "The passage registers outside pressure but already settles it locally.",
                "anchor_quote": "",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": False,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The social pressure is visible, but the passage has already settled the point.",
                "anchor_focus": {
                    "anchor_quote": "preference of a majority of his patrons",
                    "focus_sentence_id": "c1-s2",
                    "focus_kind": "phrase",
                    "source": "focal_sentence",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The local hinge is still the patron-pressure phrase, but the moment no longer needs surfacing.",
                    "current_focus_quote": "preference of a majority of his patrons",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": False,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "",
            }
        if "reaction-emission gate" in system_prompt:
            raise AssertionError("reaction_emission should stay gated off")
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence(
            "c1-s2",
            "He was prepared to teach that the earth was either flat or round, according to the preference of a majority of his patrons.",
            sentence_index=2,
        ),
        current_span_sentences=[
            _sentence("c1-s1", "He wished to keep his place and felt that he could not enjoy losing it.", sentence_index=1),
            _sentence(
                "c1-s2",
                "He was prepared to teach that the earth was either flat or round, according to the preference of a majority of his patrons.",
                sentence_index=2,
            ),
            _sentence("c1-s3", "He fulfilled his promise and the tension promptly closed there.", sentence_index=3),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=None,
        book_title="Up from Slavery",
        author="Booker T. Washington",
        chapter_title="The Reconstruction Period",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    assert calls == ["zoom", "closure"]
    assert result["reaction_result"] is None


def test_run_phase4_local_cycle_degrades_zoom_llm_error(monkeypatch):
    """A transient zoom_read LLM failure should not abort the whole Phase 4 cycle."""

    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            calls.append("zoom")
            raise ReaderLLMError("zoom unavailable", problem_code="network_blocked")
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The local turn still closes cleanly without zoom support.",
                "anchor_focus": {
                    "anchor_quote": "However, value shifts here.",
                    "focus_sentence_id": "c1-s2",
                    "focus_kind": "sentence",
                    "source": "focal_sentence",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "Even without zoom support, the local turn is still answerable to the focal sentence itself.",
                    "current_focus_quote": "However, value shifts here.",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": False,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "",
            }
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        current_span_sentences=[
            _sentence("c1-s1", "Value looks stable at first.", sentence_index=1),
            _sentence("c1-s2", "However, value shifts here.", sentence_index=2),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=None,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    assert calls == ["zoom", "closure"]
    assert result["zoom_result"] is None
    assert result["closure_result"]["closure_decision"] == "close"
    assert result["controller_result"]["chosen_move"] == "advance"
    assert result["controller_result"]["reason"] == "controller_fast_path"
    assert result["llm_fallbacks"] == [{"node": "zoom_read", "problem_code": "network_blocked"}]


def test_run_phase4_local_cycle_withholds_when_reaction_emission_llm_fails(monkeypatch):
    """A reaction-emission LLM failure should degrade to withhold rather than aborting the run."""

    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            calls.append("zoom")
            return {
                "local_interpretation": "The phrase carries unusually compressed pressure.",
                "anchor_quote": "single channel and a single choice",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": True,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            calls.append("closure")
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The sentence narrows many desires into one forced route.",
                "anchor_focus": {
                    "anchor_quote": "single channel and a single choice",
                    "focus_sentence_id": "c1-s1",
                    "focus_kind": "phrase",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The forced-route phrase is the exact local hinge that earns a visible reaction.",
                    "current_focus_quote": "single channel and a single choice",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": True,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": {
                    "type": "discern",
                    "anchor_quote": "single channel and a single choice",
                    "content": "The narrowing phrase is the local hinge.",
                    "related_anchor_quotes": [],
                    "search_query": "",
                    "search_results": [],
                },
                "unresolved_pressure_note": "",
            }
        if "reaction-emission gate" in system_prompt:
            calls.append("emit")
            raise ReaderLLMError("reaction emission unavailable", problem_code="network_blocked")
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence(
            "c1-s1",
            "But all that she may wish to have, all that she may wish to do, must come through a single channel and a single choice.",
            sentence_index=1,
        ),
        current_span_sentences=[
            _sentence(
                "c1-s1",
                "But all that she may wish to have, all that she may wish to do, must come through a single channel and a single choice.",
                sentence_index=1,
            ),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=None,
        book_title="Women and Economics",
        author="Gilman",
        chapter_title="Chapter 9",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    assert calls == ["zoom", "closure", "emit"]
    assert result["reaction_result"]["decision"] == "withhold"
    assert result["reaction_result"]["reaction"] is None
    assert result["llm_fallbacks"] == [{"node": "reaction_emission", "problem_code": "network_blocked"}]


def test_run_phase4_local_cycle_withholds_reaction_when_emitted_anchor_drifts_from_focus(monkeypatch):
    """A visible reaction should be withheld if it drifts off the current local focus quote."""

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "sentence-level zoom node" in system_prompt:
            return {
                "local_interpretation": "The sentence turns the scene on the exact phrase itself.",
                "anchor_quote": "single channel and a single choice",
                "pressure_updates": [],
                "activation_updates": [],
                "bridge_candidate": {},
                "consider_reaction_emission": True,
                "uncertainty_note": "",
            }
        if "meaning-unit closure node" in system_prompt:
            return {
                "closure_decision": "close",
                "meaning_unit_summary": "The line narrows many wishes into one forced route.",
                "anchor_focus": {
                    "anchor_quote": "single channel and a single choice",
                    "focus_sentence_id": "c1-s1",
                    "focus_kind": "phrase",
                    "source": "zoom_anchor",
                },
                "anchor_relation": {
                    "relation_status": "anchored",
                    "relation_to_focus": "The narrowing phrase is the exact local hinge.",
                    "current_focus_quote": "single channel and a single choice",
                    "same_chapter_pressure_only": False,
                    "local_backcheck_used": False,
                    "can_emit_visible_reaction": True,
                },
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": {
                    "type": "discern",
                    "anchor_quote": "single channel and a single choice",
                    "content": "The line forces desire through one route.",
                    "related_anchor_quotes": [],
                    "search_query": "",
                    "search_results": [],
                },
                "unresolved_pressure_note": "",
            }
        if "reaction-emission gate" in system_prompt:
            return {
                "decision": "emit",
                "reason": "the moment seems readable",
                "reaction": {
                    "type": "discern",
                    "anchor_quote": "the chapter generally turns inward",
                    "content": "A broader chapter theme seems to settle here.",
                    "related_anchor_quotes": [],
                    "search_query": "",
                    "search_results": [],
                },
            }
        return default

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = run_phase4_local_cycle(
        focal_sentence=_sentence(
            "c1-s1",
            "But all that she may wish to have, all that she may wish to do, must come through a single channel and a single choice.",
            sentence_index=1,
        ),
        current_span_sentences=[
            _sentence(
                "c1-s1",
                "But all that she may wish to have, all that she may wish to do, must come through a single channel and a single choice.",
                sentence_index=1,
            ),
        ],
        trigger_state={"output": "zoom_now", "gate_state": "hot"},
        working_pressure=build_empty_working_pressure(),
        anchor_memory=build_empty_anchor_memory(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        bridge_candidates=[],
        output_language="en",
        output_dir=None,
        book_title="Women and Economics",
        author="Gilman",
        chapter_title="Chapter 9",
        boundary_context={"gate_state": "hot", "candidate_boundary": True},
    )

    assert result["reaction_result"]["decision"] == "withhold"
    assert result["reaction_result"]["reason"] == "reaction_anchor_drifted_from_local_focus"
    assert result["reaction_result"]["reaction"] is None
