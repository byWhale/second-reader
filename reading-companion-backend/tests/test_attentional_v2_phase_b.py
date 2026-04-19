"""Tests for attentional_v2 read-contract helpers after the F1 cutover."""

from __future__ import annotations

import json

from src.attentional_v2 import nodes as nodes_module
from src.attentional_v2 import runner as runner_module
from src.attentional_v2.nodes import navigate_route, read_unit
from src.attentional_v2.read_context import build_carry_forward_context, resolve_context_request
from src.attentional_v2.schemas import (
    build_default_reader_policy,
    build_empty_anchor_memory,
    build_empty_knowledge_activations,
    build_empty_local_buffer,
    build_empty_move_history,
    build_empty_reaction_records,
    build_empty_reflective_summaries,
    build_empty_working_pressure,
)
from src.attentional_v2.state_migration import (
    migrate_anchor_memory_to_new_layers,
    migrate_reflective_summaries_to_frames,
    migrate_working_pressure_to_working_state,
)
from src.attentional_v2.storage import read_audit_file
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism


def _book_document() -> dict[str, object]:
    return {
        "metadata": {
            "book": "Demo Book",
            "author": "Tester",
            "book_language": "en",
            "output_language": "en",
        },
        "chapters": [
            {
                "id": 1,
                "title": "Chapter 1",
                "reference": "Chapter 1",
                "sentences": [
                    {
                        "sentence_id": "c1-s1",
                        "sentence_index": 1,
                        "paragraph_index": 1,
                        "text": "Alpha sentence.",
                        "text_role": "body",
                    },
                    {
                        "sentence_id": "c1-s2",
                        "sentence_index": 2,
                        "paragraph_index": 1,
                        "text": "Beta sentence.",
                        "text_role": "body",
                    },
                ],
            }
        ],
    }


def _anchor_record(anchor_id: str, sentence_id: str, quote: str) -> dict[str, object]:
    return {
        "anchor_id": anchor_id,
        "sentence_start_id": sentence_id,
        "sentence_end_id": sentence_id,
        "quote": quote,
        "anchor_kind": "unit_evidence",
        "why_it_mattered": "Earlier line remained relevant.",
        "status": "active",
        "locator": {},
        "created_at": "2026-04-12T00:00:00Z",
        "updated_at": "2026-04-12T00:00:00Z",
        "times_referenced": 0,
        "source_passage_id": "",
        "tags": [],
    }


def test_read_unit_projects_compact_packet_and_returns_f1_surface_contract(tmp_path, monkeypatch):
    """read_unit should render the compact prompt packet and return the new F1 fields."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    captured: dict[str, str] = {}

    def fake_invoke_json(_system: str, prompt: str, default: object) -> object:
        captured["prompt"] = prompt
        return {
            "unit_delta": "The second sentence sharpens the first one.",
            "pressure_signals": {
                "continuation_pressure": True,
                "backward_pull": True,
                "frame_shift_pressure": False,
            },
            "surfaced_reactions": [
                {
                    "anchor_quote": "Beta sentence.",
                    "content": "This is where the move becomes visible.",
                    "prior_link": {
                        "ref_ids": ["anchor:a-1", "lookback:sentence:c1-s1"],
                        "relation": "callback",
                        "note": "The earlier anchor clarifies the shift.",
                    },
                }
            ],
            "implicit_uptake_ops": [
                {
                    "op": "update",
                    "target_store": "working_state",
                    "target_key": "pressure-1",
                    "payload": {
                        "kind": "question",
                        "statement": "What changes here?",
                    },
                }
            ],
            "detour_need": {
                "reason": "Need the exact earlier wording.",
                "target_hint": "the earlier promise line",
                "status": "open",
            },
        }

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

    local_buffer = build_empty_local_buffer()
    local_buffer["recent_sentences"] = [
        {
            "sentence_id": "c1-s1",
            "sentence_index": 1,
            "paragraph_index": 1,
            "text": "Alpha sentence.",
            "text_role": "body",
        }
    ]
    local_buffer["recent_meaning_units"] = [["c1-s1"]]

    working_pressure = build_empty_working_pressure()
    working_pressure["gate_state"] = "watch"
    working_pressure["local_questions"] = [
        {
            "item_id": "pressure-1",
            "bucket": "local_questions",
            "kind": "question",
            "statement": "Why does the chapter turn here?",
            "support_anchor_ids": [],
            "status": "open",
        }
    ]

    anchor_memory = build_empty_anchor_memory()
    anchor_memory["anchor_records"] = [_anchor_record("a-1", "c1-s1", "Alpha sentence.")]
    anchor_memory["motif_index"] = {"promise": ["a-1"]}
    anchor_memory["trace_links"] = {"a-1": ["a-1"]}

    reflective_summaries = build_empty_reflective_summaries()
    reflective_summaries["chapter_understandings"] = [
        {
            "item_id": "frame-1",
            "statement": "The chapter is opening a practical dilemma.",
            "chapter_ref": "Chapter 1",
            "confidence_band": "working",
            "support_anchor_ids": ["a-1"],
        }
    ]

    move_history = build_empty_move_history()
    move_history["moves"] = [
        {
            "move_id": "move-1",
            "move_type": "advance",
            "reason": "follow the opening claim",
            "source_sentence_id": "c1-s1",
            "target_anchor_id": "",
            "target_sentence_id": "",
        }
    ]

    reaction_records = build_empty_reaction_records()
    reaction_records["records"] = [
        {
            "reaction_id": "reaction-1",
            "type": "highlight",
            "thought": "The first line already carries pressure.",
            "emitted_at_sentence_id": "c1-s1",
            "primary_anchor": {"anchor_id": "a-1", "quote": "Alpha sentence."},
        }
    ]

    carry_forward = build_carry_forward_context(
        chapter_ref="Chapter 1",
        current_unit_sentence_ids=["c1-s2"],
        local_buffer=local_buffer,
        working_pressure=working_pressure,
        anchor_memory=anchor_memory,
        reflective_summaries=reflective_summaries,
        move_history=move_history,
        reaction_records=reaction_records,
    )

    result = read_unit(
        current_unit_sentences=[
            {
                "sentence_id": "c1-s2",
                "sentence_index": 2,
                "paragraph_index": 1,
                "text": "Beta sentence.",
                "text_role": "body",
            }
        ],
        carry_forward_context=carry_forward,
        reader_policy=build_default_reader_policy(),
        output_language="en",
        supplemental_context={
            "kind": "look_back",
            "reason": "Need the exact wording.",
            "refs": [
                {
                    "ref_id": "lookback:sentence:c1-s1",
                    "kind": "look_back_excerpt",
                    "item_id": "c1-s1",
                    "summary": "Alpha sentence.",
                    "sentence_id": "c1-s1",
                }
            ],
            "excerpts": [
                {
                    "ref_id": "lookback:sentence:c1-s1",
                    "source_kind": "sentence",
                    "sentence_ids": ["c1-s1"],
                    "chapter_ref": "Chapter 1",
                    "excerpt_text": "Alpha sentence.",
                }
            ],
        },
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
    )

    manifest = json.loads(
        (output_dir / "_mechanisms" / "attentional_v2" / "internal" / "prompt_manifests" / "read_unit.json").read_text(
            encoding="utf-8"
        )
    )

    assert "\"packet_version\": \"attentional_v2.state_packet.v1\"" in captured["prompt"]
    assert "\"active_items\"" in captured["prompt"]
    assert "\"concept_key\": \"promise\"" in captured["prompt"]
    assert "\"earlier_excerpts\"" in captured["prompt"]
    assert "\"working_pressure_digest\"" not in captured["prompt"]
    assert "\"refs\": [" not in captured["prompt"]
    assert "\"anchor_bank_digest\"" not in captured["prompt"]
    assert manifest["prompt_version"] == "attentional_v2.read.v8"
    assert result["unit_delta"] == "The second sentence sharpens the first one."
    assert result["pressure_signals"] == {
        "continuation_pressure": True,
        "backward_pull": True,
        "frame_shift_pressure": False,
    }
    assert result["surfaced_reactions"][0]["anchor_quote"] == "Beta sentence."
    assert result["surfaced_reactions"][0]["prior_link"]["ref_ids"] == ["anchor:a-1", "lookback:sentence:c1-s1"]
    assert result["implicit_uptake_ops"][0]["op"] == "update"
    assert result["implicit_uptake_ops"][0]["target_store"] == "working_state"
    assert result["detour_need"]["status"] == "open"

    route = navigate_route(read_result=result)
    assert route["action"] == "bridge_back"
    assert route["target_anchor_id"] == ""
    assert route["target_sentence_id"] == ""


def test_resolve_context_request_returns_exact_look_back_excerpt_and_none_when_unresolved():
    """look_back should resolve exact earlier source text only when explicit refs can be satisfied."""

    book_document = _book_document()
    anchor_memory = build_empty_anchor_memory()
    anchor_memory["anchor_records"].append(_anchor_record("a-1", "c1-s1", "Alpha sentence."))
    anchor_bank, concept_registry, thread_trace = migrate_anchor_memory_to_new_layers(anchor_memory)
    reflective_frames = migrate_reflective_summaries_to_frames(build_empty_reflective_summaries())
    carry_forward = build_carry_forward_context(
        chapter_ref="Chapter 1",
        current_unit_sentence_ids=["c1-s2"],
        local_buffer=build_empty_local_buffer(),
        working_pressure=build_empty_working_pressure(),
        anchor_memory=anchor_memory,
        reflective_summaries=build_empty_reflective_summaries(),
        move_history=build_empty_move_history(),
        reaction_records=build_empty_reaction_records(),
    )

    resolved = resolve_context_request(
        context_request={
            "kind": "look_back",
            "reason": "Need the earlier line verbatim.",
            "anchor_ids": ["a-1"],
            "sentence_ids": ["c1-s1"],
        },
        carry_forward_context=carry_forward,
        book_document=book_document,
        chapter_ref="Chapter 1",
        anchor_bank=anchor_bank,
        concept_registry=concept_registry,
        thread_trace=thread_trace,
        reflective_frames=reflective_frames,
        move_history=build_empty_move_history(),
        reaction_records=build_empty_reaction_records(),
    )

    assert resolved is not None
    assert resolved["kind"] == "look_back"
    assert len(resolved["excerpts"]) == 1
    assert resolved["excerpts"][0]["excerpt_text"] == "Alpha sentence."

    unresolved = resolve_context_request(
        context_request={
            "kind": "look_back",
            "reason": "Need a missing excerpt.",
            "anchor_ids": ["missing-anchor"],
            "sentence_ids": ["missing-sentence"],
        },
        carry_forward_context=carry_forward,
        book_document=book_document,
        chapter_ref="Chapter 1",
        anchor_bank=anchor_bank,
        concept_registry=concept_registry,
        thread_trace=thread_trace,
        reflective_frames=reflective_frames,
        move_history=build_empty_move_history(),
        reaction_records=build_empty_reaction_records(),
    )

    assert unresolved is None


def test_resolve_context_request_active_recall_surfaces_concepts_and_threads():
    """active_recall should expose bounded concept/thread material from the new primary layers."""

    anchor_memory = build_empty_anchor_memory()
    anchor_memory["anchor_records"] = [
        _anchor_record("a-1", "c1-s1", "Alpha sentence."),
        _anchor_record("a-2", "c1-s2", "Beta sentence."),
    ]
    anchor_memory["motif_index"] = {"promise": ["a-1", "a-2"]}
    anchor_memory["unresolved_reference_index"] = {"promise": ["a-2"]}
    anchor_memory["trace_links"] = {"a-1": ["a-2"]}
    anchor_bank, concept_registry, thread_trace = migrate_anchor_memory_to_new_layers(anchor_memory)
    reflective_frames = migrate_reflective_summaries_to_frames(build_empty_reflective_summaries())

    carry_forward = build_carry_forward_context(
        chapter_ref="Chapter 1",
        current_unit_sentence_ids=["c1-s2"],
        local_buffer=build_empty_local_buffer(),
        working_pressure=build_empty_working_pressure(),
        anchor_memory=anchor_memory,
        reflective_summaries=build_empty_reflective_summaries(),
        move_history=build_empty_move_history(),
        reaction_records=build_empty_reaction_records(),
    )

    resolved = resolve_context_request(
        context_request={
            "kind": "active_recall",
            "reason": "Need more prior structure.",
            "anchor_ids": [],
            "sentence_ids": [],
        },
        carry_forward_context=carry_forward,
        book_document=_book_document(),
        chapter_ref="Chapter 1",
        anchor_bank=anchor_bank,
        concept_registry=concept_registry,
        thread_trace=thread_trace,
        reflective_frames=reflective_frames,
        move_history=build_empty_move_history(),
        reaction_records=build_empty_reaction_records(),
        current_unit_sentence_ids=["c1-s2"],
    )

    assert resolved is not None
    assert resolved["kind"] == "active_recall"
    assert resolved["concepts"][0]["concept_key"] == "promise"
    assert resolved["threads"][0]["thread_key"]
    assert any(ref["kind"] == "concept" for ref in resolved["refs"])
    assert any(ref["kind"] == "thread" for ref in resolved["refs"])


def test_run_read_with_context_loop_reads_once_and_persists_f1_audit(tmp_path, monkeypatch):
    """The F1 live helper should read once and persist the new audit shape."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    book_document = _book_document()
    chapter = book_document["chapters"][0]
    anchor_memory = build_empty_anchor_memory()
    anchor_memory["anchor_records"].append(_anchor_record("a-1", "c1-s1", "Alpha sentence."))
    anchor_bank, concept_registry, thread_trace = migrate_anchor_memory_to_new_layers(anchor_memory)
    reflective_frames = migrate_reflective_summaries_to_frames(build_empty_reflective_summaries())
    calls: list[dict[str, object]] = []

    def fake_read_unit(**kwargs):
        calls.append(
            {
                "unit_sentence_ids": [sentence["sentence_id"] for sentence in kwargs["current_unit_sentences"]],
                "supplemental_context": kwargs.get("supplemental_context"),
            }
        )
        return {
            "unit_delta": "The unit becomes legible immediately.",
            "pressure_signals": {
                "continuation_pressure": False,
                "backward_pull": False,
                "frame_shift_pressure": False,
            },
            "surfaced_reactions": [
                {
                    "anchor_quote": "Beta sentence.",
                    "content": "The bridge is clear without a second pass.",
                }
            ],
            "implicit_uptake_ops": [
                {
                    "op": "append",
                    "target_store": "working_state",
                    "target_key": "pressure-1",
                    "payload": {"kind": "question", "statement": "What changes here?"},
                }
            ],
            "detour_need": {
                "reason": "A later detour may still help compare the earlier line.",
                "target_hint": "the opening sentence",
                "status": "open",
            },
        }

    monkeypatch.setattr(runner_module, "read_unit", fake_read_unit)

    read_result, llm_fallbacks = runner_module._run_read_with_context_loop(
        chapter=chapter,
        chosen_unit_sentences=[chapter["sentences"][1]],
        unitize_decision={
            "start_sentence_id": "c1-s2",
            "end_sentence_id": "c1-s2",
            "preview_range": {"start_sentence_id": "c1-s2", "end_sentence_id": "c1-s2"},
            "boundary_type": "paragraph_end",
            "evidence_sentence_ids": ["c1-s2"],
            "reason": "phase-f1-test",
            "continuation_pressure": False,
        },
        local_buffer=build_empty_local_buffer(),
        continuation_capsule={},
        working_state=migrate_working_pressure_to_working_state(build_empty_working_pressure()),
        concept_registry=concept_registry,
        thread_trace=thread_trace,
        reflective_frames=reflective_frames,
        anchor_bank=anchor_bank,
        knowledge_activations=build_empty_knowledge_activations(),
        move_history=build_empty_move_history(),
        reaction_records=build_empty_reaction_records(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
        detour_context=None,
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_id=1,
        chapter_ref="Chapter 1",
    )

    audit_line = json.loads(read_audit_file(output_dir).read_text(encoding="utf-8").strip())

    assert llm_fallbacks == []
    assert len(calls) == 1
    assert calls[0]["supplemental_context"] is None
    assert read_result["surfaced_reactions"][0]["anchor_quote"] == "Beta sentence."
    assert read_result["implicit_uptake_ops"][0]["op"] == "append"
    assert read_result["detour_need"]["status"] == "open"
    assert audit_line["stop_reason"] == "read_complete"
    assert audit_line["surfaced_reaction_count"] == 1
    assert audit_line["surfaced_reactions"][0]["anchor_quote"] == "Beta sentence."
    assert audit_line["detour_need"]["target_hint"] == "the opening sentence"
    assert audit_line["supplemental_satisfied"] is False
