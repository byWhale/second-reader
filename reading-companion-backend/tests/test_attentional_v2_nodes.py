"""Tests for attentional_v2 Phase 4 interpretive nodes."""

from __future__ import annotations

import json

from src.attentional_v2 import nodes as nodes_module
from src.attentional_v2.nodes import controller_decision, run_phase4_local_cycle, zoom_read
from src.attentional_v2.schemas import (
    build_default_reader_policy,
    build_empty_anchor_memory,
    build_empty_knowledge_activations,
    build_empty_working_pressure,
)
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism


def _sentence(sentence_id: str, text: str, *, text_role: str = "body", sentence_index: int = 1) -> dict[str, object]:
    return {
        "sentence_id": sentence_id,
        "sentence_index": sentence_index,
        "paragraph_index": sentence_index,
        "text": text,
        "text_role": text_role,
    }


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
    assert manifest["prompt_version"] == "attentional_v2.zoom_read.v4"
    assert manifest["promptset_version"] == "attentional_v2-phase6-v4"


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


def test_run_phase4_local_cycle_considers_compact_local_anchor_for_reaction_emission(monkeypatch):
    """A compact phrase-level anchor should trigger a bounded reaction-emission check."""

    calls: list[str] = []

    def fake_invoke_json(system_prompt: str, prompt: str, default: object) -> object:
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
                "dominant_move": "advance",
                "proposed_state_operations": [],
                "bridge_candidates": [],
                "reaction_candidate": None,
                "unresolved_pressure_note": "",
            }
        if "controller-decision node" in system_prompt:
            calls.append("controller")
            return {
                "chosen_move": "advance",
                "reason": "the local phrase has been registered clearly enough",
                "target_anchor_id": "",
                "target_sentence_id": "",
            }
        if "reaction-emission gate" in system_prompt:
            calls.append("emit")
            assert "one very simple principle" in prompt
            assert '"compact_local_anchor": true' in prompt.lower()
            assert '"synthetic_local_candidate": true' in prompt.lower()
            return {
                "decision": "emit",
                "reason": "the compact phrase deserves a visible local note",
                "reaction": None,
            }
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

    assert calls == ["zoom", "closure", "controller", "emit"]
    assert result["reaction_result"]["decision"] == "emit"
    assert result["reaction_result"]["reaction"]["anchor_quote"] == "one very simple principle"
    assert result["reaction_result"]["reaction"]["type"] == "discern"
