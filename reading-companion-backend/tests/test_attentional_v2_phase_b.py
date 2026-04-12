"""Tests for attentional_v2 Phase B read-context integration."""

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


def test_read_unit_includes_carry_forward_and_supplemental_context_in_prompt(tmp_path, monkeypatch):
    """read_unit should render the exact unit plus bounded carry-forward and supplemental context."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    captured: dict[str, str] = {}

    def fake_invoke_json(_system: str, prompt: str, default: object) -> object:
        captured["prompt"] = prompt
        return {
            "local_understanding": "The second sentence sharpens the first one.",
            "move_hint": "bridge",
            "continuation_pressure": True,
            "implicit_uptake": [
                {
                    "operation_type": "update",
                    "target_store": "working_pressure",
                    "item_id": "pressure-1",
                    "reason": "keep the contrast alive",
                    "payload": {"kind": "question", "statement": "What changes here?"},
                }
            ],
            "anchor_evidence": [
                {
                    "sentence_id": "c1-s2",
                    "quote": "Beta sentence.",
                    "why_it_matters": "This is the local hinge.",
                }
            ],
            "prior_material_use": {
                "materially_used": True,
                "explanation": "The earlier anchor clarifies the shift.",
                "supporting_ref_ids": ["anchor:a-1", "lookback:sentence:c1-s1"],
            },
            "raw_reaction": {
                "type": "highlight",
                "anchor_quote": "Beta sentence.",
                "content": "This is where the move becomes visible.",
                "related_anchor_quotes": [],
                "search_query": "",
                "search_results": [],
            },
            "context_request": {
                "kind": "look_back",
                "reason": "Need the exact earlier wording.",
                "sentence_ids": ["c1-s1"],
                "anchor_ids": [],
            },
        }

    monkeypatch.setattr(nodes_module, "invoke_json", fake_invoke_json)

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
        carry_forward_context={
            "working_pressure_digest": {"gate_state": "watch", "pressure_snapshot": {}, "items": []},
            "reflective_digest": [],
            "anchor_digest": [
                {
                    "ref_id": "anchor:a-1",
                    "anchor_id": "a-1",
                    "quote": "Alpha sentence.",
                    "anchor_kind": "unit_evidence",
                    "status": "active",
                    "sentence_start_id": "c1-s1",
                    "sentence_end_id": "c1-s1",
                    "why_it_mattered": "It set up the contrast.",
                }
            ],
            "continuity_digest": {
                "recent_sentence_ids": ["c1-s1"],
                "recent_meaning_units": [["c1-s1"]],
                "recent_moves": [],
                "recent_reactions": [],
            },
            "refs": [
                {
                    "ref_id": "anchor:a-1",
                    "kind": "anchor",
                    "item_id": "a-1",
                    "summary": "Alpha sentence.",
                    "anchor_id": "a-1",
                    "sentence_id": "c1-s1",
                }
            ],
        },
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

    assert "\"sentence_id\": \"c1-s2\"" in captured["prompt"]
    assert "anchor:a-1" in captured["prompt"]
    assert "lookback:sentence:c1-s1" in captured["prompt"]
    assert manifest["prompt_version"] == "attentional_v2.read.v3"
    assert result["move_hint"] == "bridge"
    assert result["continuation_pressure"] is True
    assert result["prior_material_use"]["supporting_ref_ids"] == ["anchor:a-1", "lookback:sentence:c1-s1"]
    assert result["context_request"]["kind"] == "look_back"

    route = navigate_route(read_result=result)
    assert route["action"] == "bridge_back"
    assert route["target_anchor_id"] == "a-1"
    assert route["target_sentence_id"] == "c1-s1"
    assert route["persist_raw_reaction"] is True


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
    assert resolved["excerpts"][0]["excerpt_text"] == "Alpha sentence."
    assert resolved["excerpts"][1]["excerpt_text"] == "Alpha sentence."

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


def test_run_read_with_context_loop_replays_one_active_recall_pass_and_persists_audit(tmp_path, monkeypatch):
    """The runner should allow one bounded active-recall supplement and then reread once."""

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
        if kwargs.get("supplemental_context") is None:
            return {
                "local_understanding": "The unit is suggestive but still underspecified.",
                "move_hint": "advance",
                "continuation_pressure": False,
                "implicit_uptake": [],
                "anchor_evidence": [],
                "prior_material_use": {
                    "materially_used": False,
                    "explanation": "",
                    "supporting_ref_ids": [],
                },
                "raw_reaction": None,
                "context_request": {
                    "kind": "active_recall",
                    "reason": "Need the earlier anchor summary.",
                    "anchor_ids": ["a-1"],
                    "sentence_ids": [],
                },
            }
        supplemental_context = kwargs["supplemental_context"]
        return {
            "local_understanding": "The unit becomes clear once the earlier anchor is recalled.",
            "move_hint": "bridge",
            "continuation_pressure": False,
            "implicit_uptake": [],
            "anchor_evidence": [
                {
                    "sentence_id": "c1-s2",
                    "quote": "Beta sentence.",
                    "why_it_matters": "The local line now clearly links back.",
                }
            ],
            "prior_material_use": {
                "materially_used": True,
                "explanation": "The recalled anchor resolves the local move.",
                "supporting_ref_ids": [supplemental_context["refs"][0]["ref_id"]],
            },
            "raw_reaction": {
                "type": "highlight",
                "anchor_quote": "Beta sentence.",
                "content": "The bridge becomes visible after recall.",
                "related_anchor_quotes": [],
                "search_query": "",
                "search_results": [],
            },
            "context_request": None,
        }

    monkeypatch.setattr(runner_module, "read_unit", fake_read_unit)

    read_result, llm_fallbacks = runner_module._run_read_with_context_loop(
        chapter=chapter,
        book_document=book_document,
        chosen_unit_sentences=[chapter["sentences"][1]],
        unitize_decision={
            "start_sentence_id": "c1-s2",
            "end_sentence_id": "c1-s2",
            "preview_range": {"start_sentence_id": "c1-s2", "end_sentence_id": "c1-s2"},
            "boundary_type": "paragraph_end",
            "evidence_sentence_ids": ["c1-s2"],
            "reason": "phase-b-test",
            "continuation_pressure": False,
        },
        local_buffer=build_empty_local_buffer(),
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
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_id=1,
        chapter_ref="Chapter 1",
    )

    audit_line = json.loads(read_audit_file(output_dir).read_text(encoding="utf-8").strip())

    assert llm_fallbacks == []
    assert len(calls) == 2
    assert calls[0]["supplemental_context"] is None
    assert calls[1]["supplemental_context"]["kind"] == "active_recall"
    assert read_result["prior_material_use"]["materially_used"] is True
    assert audit_line["supplemental_satisfied"] is True
    assert audit_line["prior_material_use"]["materially_used"] is True


def test_run_read_with_context_loop_keeps_first_read_when_look_back_is_unsatisfied(tmp_path, monkeypatch):
    """An unresolved look-back request should not recurse and should preserve the first read packet."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    book_document = _book_document()
    chapter = book_document["chapters"][0]
    calls: list[dict[str, object]] = []
    empty_anchor_bank, empty_concept_registry, empty_thread_trace = migrate_anchor_memory_to_new_layers(build_empty_anchor_memory())
    empty_reflective_frames = migrate_reflective_summaries_to_frames(build_empty_reflective_summaries())

    first_read = {
        "local_understanding": "The unit remains locally readable without the missing excerpt.",
        "move_hint": "advance",
        "continuation_pressure": True,
        "implicit_uptake": [],
        "anchor_evidence": [
            {
                "sentence_id": "c1-s2",
                "quote": "Beta sentence.",
                "why_it_matters": "It keeps local pressure alive.",
            }
        ],
        "prior_material_use": {
            "materially_used": False,
            "explanation": "",
            "supporting_ref_ids": [],
        },
        "raw_reaction": None,
        "context_request": {
            "kind": "look_back",
            "reason": "Need a missing earlier excerpt.",
            "anchor_ids": ["missing-anchor"],
            "sentence_ids": [],
        },
    }

    def fake_read_unit(**kwargs):
        calls.append({"supplemental_context": kwargs.get("supplemental_context")})
        return first_read

    monkeypatch.setattr(runner_module, "read_unit", fake_read_unit)

    read_result, llm_fallbacks = runner_module._run_read_with_context_loop(
        chapter=chapter,
        book_document=book_document,
        chosen_unit_sentences=[chapter["sentences"][1]],
        unitize_decision={
            "start_sentence_id": "c1-s2",
            "end_sentence_id": "c1-s2",
            "preview_range": {"start_sentence_id": "c1-s2", "end_sentence_id": "c1-s2"},
            "boundary_type": "paragraph_end",
            "evidence_sentence_ids": ["c1-s2"],
            "reason": "phase-b-test",
            "continuation_pressure": True,
        },
        local_buffer=build_empty_local_buffer(),
        working_state=migrate_working_pressure_to_working_state(build_empty_working_pressure()),
        concept_registry=empty_concept_registry,
        thread_trace=empty_thread_trace,
        reflective_frames=empty_reflective_frames,
        anchor_bank=empty_anchor_bank,
        knowledge_activations=build_empty_knowledge_activations(),
        move_history=build_empty_move_history(),
        reaction_records=build_empty_reaction_records(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_id=1,
        chapter_ref="Chapter 1",
    )

    audit_line = json.loads(read_audit_file(output_dir).read_text(encoding="utf-8").strip())

    assert llm_fallbacks == []
    assert len(calls) == 1
    assert read_result is first_read
    assert audit_line["supplemental_satisfied"] is False
    assert audit_line["context_request"]["kind"] == "look_back"
