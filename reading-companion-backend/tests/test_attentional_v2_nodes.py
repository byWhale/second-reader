"""Tests for the current attentional_v2 live node set."""

from __future__ import annotations

import json
from pathlib import Path

from src.attentional_v2 import nodes as nodes_module
from src.attentional_v2.nodes import (
    build_unitize_preview,
    navigate_detour_search,
    navigate_route,
    navigate_unitize,
    read_unit,
)
from src.attentional_v2.schemas import build_default_reader_policy
from src.attentional_v2.state_projection import STATE_PACKET_VERSION


def _sentence(
    sentence_id: str,
    text: str,
    *,
    sentence_index: int,
    paragraph_index: int,
    text_role: str = "body",
) -> dict[str, object]:
    return {
        "sentence_id": sentence_id,
        "sentence_index": sentence_index,
        "paragraph_index": paragraph_index,
        "text": text,
        "text_role": text_role,
    }


def _navigation_context() -> dict[str, object]:
    return {
        "packet_version": STATE_PACKET_VERSION,
        "session_continuity_capsule": {"recent_sentence_ids": ["c0-s9"]},
        "working_state_digest": {"open_questions": []},
        "chapter_reflective_frame": {"chapter_frames": []},
        "active_focus_digest": {"recent_moves": []},
        "concept_digest": [],
        "thread_digest": [],
        "anchor_bank_digest": {"active_anchors": []},
        "refs": [],
    }


def test_build_unitize_preview_stays_within_current_and_next_non_heading_paragraph():
    """Preview should start at the current sentence, finish the paragraph, then include one following body paragraph."""

    chapter_sentences = [
        _sentence("c1-s1", "Heading.", sentence_index=1, paragraph_index=1, text_role="section_heading"),
        _sentence("c1-s2", "Alpha.", sentence_index=2, paragraph_index=2),
        _sentence("c1-s3", "Beta.", sentence_index=3, paragraph_index=2),
        _sentence("c1-s4", "Gamma.", sentence_index=4, paragraph_index=3),
        _sentence("c1-s5", "Delta.", sentence_index=5, paragraph_index=4, text_role="section_heading"),
        _sentence("c1-s6", "Epsilon.", sentence_index=6, paragraph_index=5),
    ]

    preview, preview_range = build_unitize_preview(
        chapter_sentences=chapter_sentences,
        current_sentence_id="c1-s3",
    )

    assert [sentence["sentence_id"] for sentence in preview] == ["c1-s3", "c1-s4"]
    assert preview_range == {
        "start_sentence_id": "c1-s3",
        "end_sentence_id": "c1-s4",
    }


def test_navigate_unitize_writes_manifest_and_applies_sentence_cap(tmp_path: Path, monkeypatch):
    """Unitize should honor the prompt result, then clamp it to the emergency coverage ceiling."""

    captured: dict[str, str] = {}

    def fake_invoke_json(system_prompt: str, prompt: str, default: object) -> object:
        captured["system_prompt"] = system_prompt
        captured["prompt"] = prompt
        return {
            "start_sentence_id": "c1-s1",
            "end_sentence_id": "c1-s2",
            "boundary_type": "cross_paragraph_continuation",
            "evidence_sentence_ids": ["c1-s1", "c1-s2"],
            "reason": "The line clearly keeps running.",
            "continuation_pressure": True,
        }

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    reader_policy = build_default_reader_policy()
    reader_policy["unitize"]["max_coverage_unit_sentences"] = 1
    preview_sentences = [
        _sentence("c1-s1", "Alpha.", sentence_index=1, paragraph_index=1),
        _sentence("c1-s2", "Beta.", sentence_index=2, paragraph_index=1),
    ]

    decision = navigate_unitize(
        current_sentence=preview_sentences[0],
        preview_sentences=preview_sentences,
        navigation_context=_navigation_context(),
        reader_policy=reader_policy,
        output_language="en",
        output_dir=tmp_path,
    )

    manifest = json.loads((tmp_path / "_mechanisms" / "attentional_v2" / "internal" / "prompt_manifests" / "navigate_unitize.json").read_text(encoding="utf-8"))

    assert decision["start_sentence_id"] == "c1-s1"
    assert decision["end_sentence_id"] == "c1-s1"
    assert decision["preview_range"]["end_sentence_id"] == "c1-s2"
    assert decision["continuation_pressure"] is True
    assert "\"packet_version\": \"attentional_v2.state_packet.v1\"" in captured["prompt"]
    assert "weak structure cues, not automatic permission to cut a standalone unit" in captured["system_prompt"]
    assert manifest["prompt_version"] == "attentional_v2.navigate_unitize.v3"


def test_navigate_unitize_fallback_merges_heading_with_following_body(tmp_path: Path, monkeypatch):
    """Heading-only fallback should widen to heading plus the next body paragraph when available."""

    monkeypatch.setattr(
        nodes_module,
        "invoke_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            nodes_module.ReaderLLMError("temporary navigation failure", problem_code="network_blocked")
        ),
    )

    preview_sentences = [
        _sentence("c1-s1", "认识财富创造的原理", sentence_index=1, paragraph_index=1, text_role="section_heading"),
        _sentence("c1-s2", "能学会。", sentence_index=2, paragraph_index=2),
        _sentence("c1-s3", "而且值得学。", sentence_index=3, paragraph_index=2),
    ]

    decision = navigate_unitize(
        current_sentence=preview_sentences[0],
        preview_sentences=preview_sentences,
        navigation_context=_navigation_context(),
        reader_policy=build_default_reader_policy(),
        output_language="zh",
        output_dir=tmp_path,
    )

    assert decision["start_sentence_id"] == "c1-s1"
    assert decision["end_sentence_id"] == "c1-s3"
    assert decision["evidence_sentence_ids"] == ["c1-s1", "c1-s2", "c1-s3"]
    assert decision["reason"] == "unitize_fallback_heading_with_body"


def test_navigate_unitize_fallback_keeps_body_paragraph_behavior(tmp_path: Path, monkeypatch):
    """Ordinary body fallback should still stop at the current paragraph end."""

    monkeypatch.setattr(
        nodes_module,
        "invoke_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            nodes_module.ReaderLLMError("temporary navigation failure", problem_code="network_blocked")
        ),
    )

    preview_sentences = [
        _sentence("c1-s1", "Alpha.", sentence_index=1, paragraph_index=1),
        _sentence("c1-s2", "Beta.", sentence_index=2, paragraph_index=1),
        _sentence("c1-s3", "Gamma.", sentence_index=3, paragraph_index=2),
    ]

    decision = navigate_unitize(
        current_sentence=preview_sentences[0],
        preview_sentences=preview_sentences,
        navigation_context=_navigation_context(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
        output_dir=tmp_path,
    )

    assert decision["end_sentence_id"] == "c1-s2"
    assert decision["evidence_sentence_ids"] == ["c1-s1", "c1-s2"]
    assert decision["reason"] == "unitize_fallback_current_paragraph"


def test_navigate_unitize_fallback_allows_heading_only_when_no_body_follows(tmp_path: Path, monkeypatch):
    """Heading fallback may remain isolated when the preview does not contain a following body paragraph."""

    monkeypatch.setattr(
        nodes_module,
        "invoke_json",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            nodes_module.ReaderLLMError("temporary navigation failure", problem_code="network_blocked")
        ),
    )

    preview_sentences = [
        _sentence("c1-s1", "Chapter 2", sentence_index=1, paragraph_index=1, text_role="chapter_heading"),
    ]

    decision = navigate_unitize(
        current_sentence=preview_sentences[0],
        preview_sentences=preview_sentences,
        navigation_context=_navigation_context(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
        output_dir=tmp_path,
    )

    assert decision["end_sentence_id"] == "c1-s1"
    assert decision["evidence_sentence_ids"] == ["c1-s1"]
    assert decision["reason"] == "unitize_fallback_current_paragraph"


def test_navigate_detour_search_normalizes_invalid_land_into_defer(tmp_path: Path, monkeypatch):
    """Detour search should refuse to land outside the visible search space."""

    monkeypatch.setattr(
        nodes_module,
        "invoke_json",
        lambda *_args, **_kwargs: {
            "decision": "land_region",
            "reason": "Try a sentence that was not offered.",
            "start_sentence_id": "missing-s1",
            "end_sentence_id": "missing-s2",
        },
    )

    result = navigate_detour_search(
        search_scope={
            "scope_kind": "chapter_cards",
            "reason": "search earlier setup",
            "cards": [
                {
                    "start_sentence_id": "c1-s1",
                    "end_sentence_id": "c1-s2",
                    "card_summary": "Opening setup",
                }
            ],
        },
        detour_need={"reason": "Need the setup again.", "target_hint": "opening setup", "status": "open"},
        navigation_context={"packet_version": STATE_PACKET_VERSION},
        reader_policy=build_default_reader_policy(),
        output_language="en",
        output_dir=tmp_path,
    )

    assert result == {
        "decision": "defer_detour",
        "reason": "Try a sentence that was not offered.",
        "start_sentence_id": "",
        "end_sentence_id": "",
    }


def test_read_unit_filters_unanchored_surface_and_falls_back_from_legacy_move_hint(tmp_path: Path, monkeypatch):
    """Read should keep only unit-anchored surfaced reactions and derive pressure from legacy fallback fields."""

    captured: dict[str, str] = {}

    def fake_invoke_json(system_prompt: str, prompt: str, default: object) -> object:
        captured["system_prompt"] = system_prompt
        captured["prompt"] = prompt
        return {
            "local_understanding": "The line flips the frame.",
            "move_hint": "reframe",
            "surfaced_reactions": [
                {
                    "anchor_quote": "Alpha hinge.",
                    "content": "That phrase suddenly snaps the claim into place.",
                    "prior_link": {
                        "ref_ids": ["anchor:a-1"],
                        "relation": "callback",
                        "note": "It answers the earlier thread.",
                    },
                },
                {
                    "anchor_quote": "Quote outside unit",
                    "content": "This one should be dropped.",
                },
            ],
            "implicit_uptake": [
                {
                    "op": "append",
                    "target_store": "working_state",
                    "target_key": "q-1",
                    "payload": {"statement": "The frame just shifted."},
                }
            ],
        }

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    result = read_unit(
        current_unit_sentences=[
            _sentence("c1-s1", "Alpha hinge.", sentence_index=1, paragraph_index=1),
            _sentence("c1-s2", "Beta consequence.", sentence_index=2, paragraph_index=1),
        ],
        carry_forward_context={
            "packet_version": STATE_PACKET_VERSION,
            "refs": [
                {"ref_id": "anchor:a-1", "kind": "anchor"},
            ],
        },
        reader_policy=build_default_reader_policy(),
        output_language="en",
        output_dir=tmp_path,
    )

    manifest = json.loads((tmp_path / "_mechanisms" / "attentional_v2" / "internal" / "prompt_manifests" / "read_unit.json").read_text(encoding="utf-8"))

    assert result["unit_delta"] == "The line flips the frame."
    assert result["pressure_signals"] == {
        "continuation_pressure": False,
        "backward_pull": False,
        "frame_shift_pressure": True,
    }
    assert result["surfaced_reactions"] == [
        {
            "anchor_quote": "Alpha hinge.",
            "content": "That phrase suddenly snaps the claim into place.",
            "prior_link": {
                "ref_ids": ["anchor:a-1"],
                "relation": "callback",
                "note": "It answers the earlier thread.",
            },
            "outside_link": None,
            "search_intent": None,
        }
    ]
    assert result["implicit_uptake_ops"][0]["target_store"] == "working_state"
    assert "Keep proportion around thin structural units." in captured["system_prompt"]
    assert "Do not inflate a bare heading or structural cue" in captured["system_prompt"]
    assert manifest["prompt_version"] == "attentional_v2.read.v8"


def test_navigate_route_uses_pressure_signals_only():
    """Route decisions should be deterministic projections of the normalized read packet."""

    decision = navigate_route(
        read_result={
            "unit_delta": "This section wants to keep unfolding.",
            "pressure_signals": {
                "continuation_pressure": True,
                "backward_pull": False,
                "frame_shift_pressure": False,
            },
        }
    )

    assert decision == {
        "action": "continue",
        "reason": "This section wants to keep unfolding.",
        "close_current_unit": True,
        "target_anchor_id": "",
        "target_sentence_id": "",
    }
