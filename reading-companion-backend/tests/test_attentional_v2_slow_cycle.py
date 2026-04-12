"""Tests for attentional_v2 Phase 6 slow-cycle helpers."""

from __future__ import annotations

import json

from src.attentional_v2 import slow_cycle as slow_cycle_module
from src.attentional_v2.schemas import (
    build_default_reader_policy,
    build_empty_anchor_memory,
    build_empty_knowledge_activations,
    build_empty_reaction_records,
    build_empty_reflective_summaries,
    build_empty_working_pressure,
)
from src.attentional_v2.slow_cycle import (
    apply_reconsolidation,
    build_reaction_record,
    project_chapter_result_compatibility,
    reconsolidation,
    run_phase6_chapter_cycle,
)
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism


def _chapter() -> dict[str, object]:
    return {
        "id": 1,
        "title": "Opening Frame",
        "reference": "Chapter 1",
        "chapter_heading": {
            "label": "Chapter 1",
            "title": "Opening Frame",
            "subtitle": "",
            "text": "Chapter 1 Opening Frame",
        },
        "paragraphs": [
            {
                "href": "chapter-1.xhtml",
                "start_cfi": "/6/2[chapter1]!/4/2/2",
                "end_cfi": "/6/2[chapter1]!/4/2/10",
                "paragraph_index": 1,
                "text": "Markets begin as relations among people.",
                "text_role": "body",
            },
            {
                "href": "chapter-1.xhtml",
                "start_cfi": "/6/2[chapter1]!/4/4/2",
                "end_cfi": "/6/2[chapter1]!/4/4/12",
                "paragraph_index": 2,
                "text": "Later the author narrows what counts as value.",
                "text_role": "body",
            },
        ],
    }


def _anchor(anchor_id: str, sentence_id: str, quote: str, paragraph_index: int) -> dict[str, object]:
    return {
        "anchor_id": anchor_id,
        "sentence_start_id": sentence_id,
        "sentence_end_id": sentence_id,
        "quote": quote,
        "locator": {
            "href": "chapter-1.xhtml",
            "start_cfi": f"/6/2[chapter1]!/4/{paragraph_index * 2}/2",
            "end_cfi": f"/6/2[chapter1]!/4/{paragraph_index * 2}/12",
            "paragraph_index": paragraph_index,
            "paragraph_start": paragraph_index,
            "paragraph_end": paragraph_index,
            "char_start": 0,
            "char_end": len(quote),
        },
    }


def test_project_chapter_result_compatibility_groups_reactions_by_paragraph(tmp_path):
    """Compatibility projection should preserve original thoughts while filling current chapter-result fields."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)

    records = build_empty_reaction_records()
    records["records"] = [
        build_reaction_record(
            reaction={
                "type": "highlight",
                "anchor_quote": "Markets begin as relations among people.",
                "content": "The opening sentence grounds value in social relation.",
                "related_anchor_quotes": [],
                "search_query": "",
                "search_results": [],
            },
            primary_anchor=_anchor("a-1", "c1-s1", "Markets begin as relations among people.", 1),
            chapter_id=1,
            chapter_ref="Chapter 1",
            emitted_at_sentence_id="c1-s1",
        ),
        build_reaction_record(
            reaction={
                "type": "discern",
                "anchor_quote": "Later the author narrows what counts as value.",
                "content": "The later sentence tightens the frame instead of merely extending it.",
                "related_anchor_quotes": [],
                "search_query": "",
                "search_results": [],
            },
            primary_anchor=_anchor("a-2", "c1-s2", "Later the author narrows what counts as value.", 2),
            chapter_id=1,
            chapter_ref="Chapter 1",
            emitted_at_sentence_id="c1-s2",
        ),
    ]

    payload = project_chapter_result_compatibility(
        book_id="demo-book",
        chapter=_chapter(),
        reaction_records=records,
        output_language="en",
        output_dir=output_dir,
        persist=True,
    )

    compatibility_path = (
        output_dir
        / "_mechanisms"
        / "attentional_v2"
        / "derived"
        / "chapter_result_compatibility"
        / "chapter-001.json"
    )

    assert payload["visible_reaction_count"] == 2
    assert payload["reaction_type_diversity"] == 2
    assert payload["sections"][0]["segment_ref"] == "1.1"
    assert payload["sections"][1]["segment_ref"] == "1.2"
    assert payload["sections"][0]["reactions"][0]["target_locator"]["match_mode"] == "exact"
    assert payload["sections"][0]["reactions"][0]["primary_anchor"]["quote"] == "Markets begin as relations among people."
    assert payload["featured_reactions"][0]["reaction_id"]
    assert payload["featured_reactions"][0]["primary_anchor"]["sentence_start_id"] == "c1-s1"
    assert compatibility_path.exists()


def test_reconsolidation_appends_later_reaction_without_mutating_earlier_one(monkeypatch):
    """Reconsolidation should append a linked later reaction instead of rewriting the earlier reaction."""

    earlier_reaction = build_reaction_record(
        reaction={
            "type": "highlight",
            "anchor_quote": "Markets begin as relations among people.",
            "content": "The opening sentence grounds value in social relation.",
            "related_anchor_quotes": [],
            "search_query": "",
            "search_results": [],
        },
        primary_anchor=_anchor("a-1", "c1-s1", "Markets begin as relations among people.", 1),
        chapter_id=1,
        chapter_ref="Chapter 1",
        emitted_at_sentence_id="c1-s1",
    )

    monkeypatch.setattr(
        slow_cycle_module,
        "invoke_json",
        lambda *_args, **_kwargs: {
            "decision": "reconsolidate",
            "reason": "The later sentence materially narrows the earlier claim.",
            "reconsolidation_record": {
                "change_kind": "tightened",
                "what_changed": "Value is now framed as narrower than the opening suggested.",
                "rationale": "The later sentence rules out the broader reading.",
            },
            "later_reaction": {
                "type": "discern",
                "anchor_quote": "Later the author narrows what counts as value.",
                "content": "The later sentence makes the earlier claim narrower than it first appeared.",
                "related_anchor_quotes": ["Markets begin as relations among people."],
                "search_query": "",
                "search_results": [],
            },
            "state_updates": [],
        },
    )

    result = reconsolidation(
        earlier_reaction=earlier_reaction,
        earlier_anchor_context=[earlier_reaction["primary_anchor"]],
        later_anchor=_anchor("a-2", "c1-s2", "Later the author narrows what counts as value.", 2),
        current_understanding_snapshot={"chapter_frame": "value is being narrowed"},
        policy_snapshot=build_default_reader_policy(),
        output_language="en",
        chapter_id=1,
        chapter_ref="Chapter 1",
    )

    next_reactions, next_reconsolidations = apply_reconsolidation(
        build_empty_reaction_records(),
        {"schema_version": 1, "mechanism_version": "attentional_v2-phase8", "updated_at": "now", "records": []},
        result,
    )

    assert result["decision"] == "reconsolidate"
    assert result["reconsolidation_record"]["prior_reaction_id"] == earlier_reaction["reaction_id"]
    assert result["later_reaction"]["supersedes_reaction_id"] == earlier_reaction["reaction_id"]
    assert earlier_reaction["thought"] == "The opening sentence grounds value in social relation."
    assert next_reactions["records"][0]["reaction_id"] == result["later_reaction"]["reaction_id"]
    assert next_reconsolidations["records"][0]["new_reaction_id"] == result["later_reaction"]["reaction_id"]


def test_run_phase6_chapter_cycle_applies_cooling_promotion_and_optional_reaction(tmp_path, monkeypatch):
    """The Phase 6 chapter cycle should cool pressure, promote reflective meaning, and persist a chapter reaction."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "chapter-consolidation node" in system_prompt:
            return {
                "chapter_ref": "Chapter 1",
                "backward_sweep": [{"anchor_id": "a-1", "why": "the opening line became the chapter spine"}],
                "cooling_operations": [
                    {
                        "operation_type": "drop",
                        "target_store": "working_pressure",
                        "item_id": "h-1",
                        "reason": "local heat ends with the chapter",
                        "payload": {"bucket": "local_hypotheses"},
                    }
                ],
                "promotion_candidates": [
                    {
                        "candidate_id": "pc-1",
                        "statement": "The chapter frames value as social before narrowing it.",
                        "support_anchor_ids": ["a-1", "a-2"],
                        "promoted_from": "chapter_sweep",
                        "target_bucket": "chapter_understandings",
                        "rationale": "It survived the backward sweep and chapter-end check.",
                    }
                ],
                "anchor_status_updates": [
                    {"anchor_id": "a-1", "status": "retained", "why_it_mattered": "became the chapter spine"}
                ],
                "knowledge_activation_updates": [],
                "cross_chapter_carry_forward": [
                    {
                        "item_id": "q-1",
                        "bucket": "local_questions",
                        "kind": "question",
                        "statement": "How narrow will the later book make value?",
                        "support_anchor_ids": ["a-2"],
                        "status": "open",
                    }
                ],
                "chapter_summary_note": "The chapter narrows its own opening frame.",
                "optional_chapter_reaction": {
                    "type": "retrospect",
                    "anchor_quote": "Later the author narrows what counts as value.",
                    "content": "By chapter end, the opening social frame has been deliberately narrowed.",
                    "related_anchor_quotes": ["Markets begin as relations among people."],
                    "search_query": "",
                    "search_results": [],
                },
            }
        if "reflective-promotion node" in system_prompt:
            return {
                "decision": "promote",
                "reason": "The statement is chapter-durable and well supported.",
                "target_bucket": "chapter_understandings",
                "reflective_item": {
                    "item_id": "ru-1",
                    "statement": "The chapter frames value as social before narrowing it.",
                    "support_anchor_ids": ["a-1", "a-2"],
                    "confidence_band": "stable",
                    "promoted_from": "chapter_sweep",
                    "status": "active",
                },
                "supersede_bucket": "",
                "supersede_item_id": "",
                "state_operations": [],
                "chapter_ref": "Chapter 1",
            }
        return default

    monkeypatch.setattr(slow_cycle_module, "invoke_json", fake_invoke_json)

    result = run_phase6_chapter_cycle(
        book_id="demo-book",
        chapter=_chapter(),
        meaning_units_in_chapter=[
            {"sentence_ids": ["c1-s1"], "summary": "social opening"},
            {"sentence_ids": ["c1-s2"], "summary": "narrowing turn"},
        ],
        chapter_end_anchor=_anchor("a-2", "c1-s2", "Later the author narrows what counts as value.", 2),
        working_pressure={
            **build_empty_working_pressure(),
            "local_hypotheses": [
                {
                    "item_id": "h-1",
                    "bucket": "local_hypotheses",
                    "kind": "hypothesis",
                    "statement": "Value is purely social.",
                    "support_anchor_ids": ["a-1"],
                    "status": "active",
                }
            ],
        },
        anchor_memory={
            **build_empty_anchor_memory(),
            "anchor_records": [
                {
                    **_anchor("a-1", "c1-s1", "Markets begin as relations among people.", 1),
                    "anchor_kind": "claim",
                    "why_it_mattered": "opening frame",
                    "status": "active",
                }
            ],
        },
        reflective_summaries=build_empty_reflective_summaries(),
        knowledge_activations=build_empty_knowledge_activations(),
        reaction_records=build_empty_reaction_records(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
        output_dir=output_dir,
        persist_compatibility_projection=True,
        book_title="Demo Book",
        author="Tester",
    )

    chapter_manifest = json.loads(
        (output_dir / "_mechanisms" / "attentional_v2" / "internal" / "prompt_manifests" / "chapter_consolidation.json").read_text(
            encoding="utf-8"
        )
    )
    promotion_manifest = json.loads(
        (output_dir / "_mechanisms" / "attentional_v2" / "internal" / "prompt_manifests" / "reflective_promotion.json").read_text(
            encoding="utf-8"
        )
    )

    assert result["chapter_consolidation"]["chapter_summary_note"] == "The chapter narrows its own opening frame."
    assert result["working_pressure"]["local_hypotheses"] == []
    assert result["working_pressure"]["local_questions"][0]["item_id"] == "q-1"
    assert result["reflective_summaries"]["chapter_understandings"][0]["item_id"] == "ru-1"
    assert result["reaction_records"]["records"][0]["type"] == "retrospect"
    assert result["compatibility_payload"]["visible_reaction_count"] == 1
    assert chapter_manifest["prompt_version"] == "attentional_v2.chapter_consolidation.v2"
    assert promotion_manifest["prompt_version"] == "attentional_v2.reflective_promotion.v1"
