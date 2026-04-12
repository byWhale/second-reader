"""Tests for attentional_v2 Phase C.3 state migration helpers."""

from __future__ import annotations

from src.attentional_v2.schemas import build_empty_anchor_memory
from src.attentional_v2.state_migration import migrate_anchor_memory_to_new_layers, project_legacy_anchor_memory


def _anchor(anchor_id: str, sentence_id: str, quote: str) -> dict[str, object]:
    return {
        "anchor_id": anchor_id,
        "sentence_start_id": sentence_id,
        "sentence_end_id": sentence_id,
        "quote": quote,
        "anchor_kind": "unit_evidence",
        "why_it_mattered": "migration test",
        "status": "active",
        "locator": {},
    }


def test_migrate_anchor_memory_to_new_layers_derives_primary_semantic_layers():
    """Legacy anchor memory should deterministically expand into the new primary semantic layers."""

    anchor_memory = build_empty_anchor_memory()
    anchor_memory["anchor_records"] = [
        _anchor("a-1", "c1-s1", "Alpha sentence."),
        _anchor("a-2", "c1-s2", "Beta sentence."),
    ]
    anchor_memory["anchor_relations"] = [
        {
            "relation_id": "rel-1",
            "relation_type": "echo",
            "source_anchor_id": "a-1",
            "target_anchor_id": "a-2",
            "rationale": "beta echoes alpha",
        }
    ]
    anchor_memory["motif_index"] = {"promise": ["a-1", "a-2"]}
    anchor_memory["unresolved_reference_index"] = {"promise": ["a-2"], "missing name": ["a-2"]}
    anchor_memory["trace_links"] = {"a-1": ["a-2"]}

    anchor_bank, concept_registry, thread_trace = migrate_anchor_memory_to_new_layers(anchor_memory)

    assert [anchor["anchor_id"] for anchor in anchor_bank["anchor_records"]] == ["a-1", "a-2"]
    assert anchor_bank["anchor_relations"][0]["relation_id"] == "rel-1"
    assert any(entry["concept_key"] == "promise" and entry["status"] == "open" for entry in concept_registry["entries"])
    assert any(entry["concept_key"] == "missing name" for entry in concept_registry["entries"])
    assert any(entry["thread_type"] == "trace_link" for entry in thread_trace["entries"])
    assert any(entry["thread_type"] == "open_reference" for entry in thread_trace["entries"])

    projected = project_legacy_anchor_memory(anchor_bank, concept_registry, thread_trace)
    assert set(projected["motif_index"]["promise"]) == {"a-1", "a-2"}
    assert set(projected["unresolved_reference_index"]["promise"]).issubset({"a-1", "a-2"})
    assert projected["trace_links"]["a-1"] == ["a-2"]
