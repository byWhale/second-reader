"""Tests for attentional_v2 Phase 5 bridge judgment and state updates."""

from __future__ import annotations

import json

from src.attentional_v2 import bridge as bridge_module
from src.attentional_v2.bridge import bridge_resolution, run_phase5_bridge_cycle
from src.attentional_v2.retrieval import generate_candidate_set
from src.attentional_v2.schemas import (
    build_default_reader_policy,
    build_empty_anchor_bank,
    build_empty_concept_registry,
    build_empty_knowledge_activations,
    build_empty_move_history,
    build_empty_thread_trace,
    build_empty_working_state,
)
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism


def _sentence(sentence_id: str, text: str, *, sentence_index: int) -> dict[str, object]:
    return {
        "sentence_id": sentence_id,
        "sentence_index": sentence_index,
        "paragraph_index": sentence_index,
        "text": text,
        "text_role": "body",
        "locator": {
            "paragraph_index": sentence_index,
            "paragraph_start": sentence_index,
            "paragraph_end": sentence_index,
            "char_start": 0,
            "char_end": len(text),
        },
    }


def _candidate_set() -> dict[str, object]:
    return {
        "current_sentence_id": "c1-s3",
        "memory_candidates": [
            {
                "candidate_kind": "anchor_bank",
                "anchor_id": "a-1",
                "sentence_start_id": "c1-s1",
                "sentence_end_id": "c1-s1",
                "quote": "Value first appears in relation.",
                "overlap_score": 3,
            }
        ],
        "lookback_candidates": [
            {
                "candidate_kind": "source_lookback",
                "sentence_id": "c1-s2",
                "chapter_id": 1,
                "chapter_title": "Chapter 1",
                "text": "The frame turns toward exchange.",
                "text_role": "body",
                "locator": {
                    "paragraph_index": 2,
                    "paragraph_start": 2,
                    "paragraph_end": 2,
                    "char_start": 0,
                    "char_end": 31,
                },
                "overlap_score": 2,
            }
        ],
    }


def test_bridge_resolution_writes_manifest_and_keeps_search_rare(tmp_path, monkeypatch):
    """Bridge judgment should stay inside the candidate set and downgrade non-blocking search."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)

    def fake_invoke_json(_system: str, _prompt: str, default: object) -> object:
        return {
            "decision": "bridge",
            "reason": "the earlier relation frame should be tested directly",
            "primary_bridge": {
                "target_anchor_id": "a-1",
                "target_sentence_id": "c1-s1",
                "relation_type": "contrast",
                "why_now": "the current line flips the earlier relation",
                "quote": "Value first appears in relation.",
            },
            "primary_attribution": {
                "target_quote": "Value first appears in relation.",
                "current_quote": "Now the relation begins to invert.",
                "relation_explanation": "The current line inverts the earlier relation frame instead of merely repeating it.",
            },
            "supporting_bridges": [
                {
                    "target_sentence_id": "c1-s2",
                    "relation_type": "support",
                    "why_now": "the middle sentence already started the turn",
                }
            ],
            "activation_updates": [],
            "state_operations": [],
            "knowledge_use_mode": "book_grounded_plus_prior_knowledge",
            "search_policy_mode": "search_now",
            "search_trigger": "genuine_curiosity",
            "search_query": "exchange theory relation frame",
        }

    monkeypatch.setattr(bridge_module, "invoke_json", fake_invoke_json)

    result = bridge_resolution(
        current_span_sentences=[
            _sentence("c1-s2", "The frame turns toward exchange.", sentence_index=2),
            _sentence("c1-s3", "Now the relation begins to invert.", sentence_index=3),
        ],
        candidate_set=_candidate_set(),
        working_state=build_empty_working_state(),
        anchor_bank={
            **build_empty_anchor_bank(),
            "anchor_records": [
                {
                    "anchor_id": "a-1",
                    "sentence_start_id": "c1-s1",
                    "sentence_end_id": "c1-s1",
                    "quote": "Value first appears in relation.",
                    "anchor_kind": "claim",
                    "status": "active",
                }
            ],
        },
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
        output_dir=output_dir,
        book_title="Demo Book",
        author="Tester",
        chapter_title="Chapter 1",
    )

    manifest = json.loads(
        (output_dir / "_mechanisms" / "attentional_v2" / "internal" / "prompt_manifests" / "bridge_resolution.json").read_text(
            encoding="utf-8"
        )
    )

    assert result["decision"] == "bridge"
    assert result["primary_bridge"]["target_anchor_id"] == "a-1"
    assert result["primary_attribution"]["target_quote"] == "Value first appears in relation."
    assert result["supporting_bridges"][0]["target_sentence_id"] == "c1-s2"
    assert result["search_policy_mode"] == "defer_search"
    assert manifest["prompt_version"] == "attentional_v2.bridge_resolution.v5"
    assert manifest["promptset_version"] == "attentional_v2-phase6-v12"


def test_bridge_resolution_declines_generic_bridge_without_specific_attribution(monkeypatch):
    """Bridge judgment should decline when it cannot name the specific earlier target and local relation honestly."""

    def fake_invoke_json(_system: str, _prompt: str, default: object) -> object:
        return {
            "decision": "bridge",
            "reason": "the chapter generally returns to an earlier theme",
            "primary_bridge": {
                "target_anchor_id": "a-1",
                "target_sentence_id": "c1-s1",
                "relation_type": "callback",
                "why_now": "this feels like a chapter-level callback",
            },
            "primary_attribution": {
                "target_quote": "",
                "current_quote": "",
                "relation_explanation": "The chapter generally returns to an earlier theme.",
            },
            "supporting_bridges": [],
            "activation_updates": [],
            "state_operations": [],
            "knowledge_use_mode": "book_grounded_only",
            "search_policy_mode": "no_search",
            "search_trigger": "none",
            "search_query": "",
        }

    monkeypatch.setattr(bridge_module, "invoke_json", fake_invoke_json)

    result = bridge_resolution(
        current_span_sentences=[
            _sentence("c1-s2", "The frame turns toward exchange.", sentence_index=2),
            _sentence("c1-s3", "Now the relation begins to invert.", sentence_index=3),
        ],
        candidate_set=_candidate_set(),
        working_state=build_empty_working_state(),
        anchor_bank=build_empty_anchor_bank(),
        knowledge_activations=build_empty_knowledge_activations(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
    )

    assert result["decision"] == "decline"
    assert result["primary_bridge"] is None
    assert result["primary_attribution"] is None


def test_generate_candidate_set_treats_qianmian_as_explicit_callback_marker():
    """Chinese backward-looking cues like `前面` should unlock source-callback retrieval beyond the local window."""

    document = {
        "chapters": [
            {
                "id": 1,
                "title": "Chapter 1",
                "sentences": [
                    _sentence("c1-s1", "先讲一个总论。", sentence_index=1),
                    _sentence("c1-s2", "例如，假设你是世界上最好的深海潜水员。", sentence_index=2),
                    *[
                        _sentence(f"c1-s{index}", f"这是中间的铺垫句 {index}。", sentence_index=index)
                        for index in range(3, 20)
                    ],
                    _sentence("c1-s20", "前面举了潜水员的例子，现在要把这个例子转回信誉与机会。", sentence_index=20),
                ],
            }
        ]
    }

    result = generate_candidate_set(
        document,
        current_sentence_id="c1-s20",
        current_text="前面举了潜水员的例子，现在要把这个例子转回信誉与机会。",
        anchor_bank=build_empty_anchor_bank(),
    )

    assert any(
        candidate.get("candidate_kind") == "source_callback" and candidate.get("sentence_id") == "c1-s2"
        for candidate in result["lookback_candidates"]
    )


def test_run_phase5_bridge_cycle_materializes_anchor_state(monkeypatch):
    """The Phase 5 helper should turn bridge judgment into durable anchor and move state."""

    def fake_invoke_json(_system: str, _prompt: str, default: object) -> object:
        return {
            "decision": "bridge",
            "reason": "the current line sharpens the earlier relation frame",
            "primary_bridge": {
                "target_sentence_id": "c1-s2",
                "relation_type": "callback",
                "why_now": "the phrase returns with a sharper claim",
                "quote": "The frame turns toward exchange.",
            },
            "primary_attribution": {
                "target_quote": "The frame turns toward exchange.",
                "current_quote": "Now the relation begins to invert.",
                "relation_explanation": "The later line sharpens the earlier exchange frame into an inversion.",
            },
            "supporting_bridges": [],
            "activation_updates": [
                {
                    "operation_type": "create",
                    "target_store": "knowledge_activations",
                    "item_id": "k-1",
                    "reason": "the bridge activates prior context",
                    "payload": {
                        "trigger_anchor_id": "anchor:c1-s3:c1-s3",
                        "activation_type": "prior_frame",
                        "source_candidate": "exchange theory",
                        "recognition_confidence": "plausible",
                        "reading_warrant": "the callback keeps turning on exchange language",
                        "role_assessment": "background lens",
                        "evidence_hints": ["exchange", "relation"],
                        "evidence_rationale": "the callback is text-earned",
                        "support_anchor_ids": ["anchor:c1-s3:c1-s3"],
                        "conflict_anchor_ids": [],
                        "status": "plausible",
                    },
                }
            ],
            "state_operations": [
                {
                    "operation_type": "create",
                    "target_store": "working_state",
                    "item_id": "motif-1",
                    "reason": "relation has become a live motif",
                    "payload": {
                        "bucket": "local_motifs",
                        "kind": "motif",
                        "statement": "relation / exchange remains live",
                        "support_anchor_ids": ["anchor:c1-s3:c1-s3"],
                        "status": "active",
                    },
                }
            ],
            "knowledge_use_mode": "book_grounded_plus_prior_knowledge",
            "search_policy_mode": "no_search",
            "search_trigger": "none",
            "search_query": "",
        }

    monkeypatch.setattr(bridge_module, "invoke_json", fake_invoke_json)

    result = run_phase5_bridge_cycle(
        current_span_sentences=[
            _sentence("c1-s2", "The frame turns toward exchange.", sentence_index=2),
            _sentence("c1-s3", "Now the relation begins to invert.", sentence_index=3),
        ],
        candidate_set=_candidate_set(),
        working_state=build_empty_working_state(),
        concept_registry=build_empty_concept_registry(),
        thread_trace=build_empty_thread_trace(),
        anchor_bank=build_empty_anchor_bank(),
        knowledge_activations=build_empty_knowledge_activations(),
        move_history=build_empty_move_history(),
        reader_policy=build_default_reader_policy(),
        output_language="en",
        motif_keys=["relation"],
        unresolved_reference_keys=["value shift"],
    )

    current_anchor_id = "anchor:c1-s3:c1-s3"

    assert result["bridge_result"]["decision"] == "bridge"
    assert result["knowledge_activations"]["knowledge_use_mode"] == "book_grounded_plus_prior_knowledge"
    assert result["knowledge_activations"]["search_policy_mode"] == "no_search"
    assert result["working_state"]["local_motifs"][0]["item_id"] == "motif-1"
    assert len(result["anchor_bank"]["anchor_records"]) == 2
    assert result["anchor_bank"]["anchor_relations"][0]["relation_type"] == "callback"
    assert {entry["concept_key"] for entry in result["concept_registry"]["entries"]} == {"relation", "value shift"}
    assert result["thread_trace"]["entries"][0]["thread_key"] == f"trace:{current_anchor_id}"
    assert result["move_history"]["moves"][0]["move_type"] == "bridge"
    assert result["move_history"]["moves"][0]["target_anchor_id"] == "anchor:c1-s2:c1-s2"
