"""Tests for the attentional_v2 Phase 1 scaffold."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.attentional_v2.schemas import ATTENTIONAL_V2_MECHANISM_VERSION, ATTENTIONAL_V2_POLICY_VERSION, ATTENTIONAL_V2_SCHEMA_VERSION
from src.attentional_v2.storage import (
    ATTENTIONAL_V2_MECHANISM_KEY,
    anchor_memory_file,
    event_stream_file,
    knowledge_activations_file,
    local_buffer_file,
    local_continuity_file,
    move_history_file,
    reaction_records_file,
    reader_policy_file,
    reflective_summaries_file,
    reconsolidation_records_file,
    revisit_index_file,
    resume_metadata_file,
    survey_map_file,
    trigger_state_file,
    working_pressure_file,
)
from src.reading_core.runtime_contracts import ParseRequest, ReadRequest
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_runtime.artifacts import checkpoint_summary_file, mechanism_manifest_file, runtime_shell_file
from src.reading_runtime.shell_state import load_runtime_shell


def test_attentional_v2_initialization_writes_phase7_artifacts(tmp_path):
    """The Phase 1-7 scaffold should write the shared shell and private state files."""

    output_dir = tmp_path / "output" / "demo-book"

    result = AttentionalV2Mechanism().initialize_artifacts(output_dir)

    assert result["mechanism_key"] == ATTENTIONAL_V2_MECHANISM_KEY
    assert result["mechanism_version"] == ATTENTIONAL_V2_MECHANISM_VERSION
    assert result["policy_version"] == ATTENTIONAL_V2_POLICY_VERSION

    shell = load_runtime_shell(runtime_shell_file(output_dir))
    assert shell["mechanism_key"] == ATTENTIONAL_V2_MECHANISM_KEY
    assert shell["mechanism_version"] == ATTENTIONAL_V2_MECHANISM_VERSION
    assert shell["cursor"]["position_kind"] == "chapter"

    checkpoint = json.loads(checkpoint_summary_file(output_dir, "bootstrap").read_text(encoding="utf-8"))
    assert checkpoint["mechanism_key"] == ATTENTIONAL_V2_MECHANISM_KEY
    assert checkpoint["resume_kind"] == "warm_resume"

    manifest = json.loads(mechanism_manifest_file(output_dir, ATTENTIONAL_V2_MECHANISM_KEY).read_text(encoding="utf-8"))
    assert manifest["mechanism_key"] == ATTENTIONAL_V2_MECHANISM_KEY

    working_pressure = json.loads(working_pressure_file(output_dir).read_text(encoding="utf-8"))
    assert working_pressure["schema_version"] == ATTENTIONAL_V2_SCHEMA_VERSION
    assert working_pressure["gate_state"] == "quiet"

    local_buffer = json.loads(local_buffer_file(output_dir).read_text(encoding="utf-8"))
    assert local_buffer["recent_sentences"] == []
    assert local_buffer["recent_meaning_units"] == []

    trigger_state = json.loads(trigger_state_file(output_dir).read_text(encoding="utf-8"))
    assert trigger_state["output"] == "no_zoom"

    local_continuity = json.loads(local_continuity_file(output_dir).read_text(encoding="utf-8"))
    assert local_continuity["recent_sentence_ids"] == []

    anchor_memory = json.loads(anchor_memory_file(output_dir).read_text(encoding="utf-8"))
    assert anchor_memory["anchor_records"] == []

    reflective = json.loads(reflective_summaries_file(output_dir).read_text(encoding="utf-8"))
    assert reflective["chapter_understandings"] == []

    activations = json.loads(knowledge_activations_file(output_dir).read_text(encoding="utf-8"))
    assert activations["knowledge_use_mode"] == "book_grounded_only"
    assert activations["search_policy_mode"] == "no_search"

    moves = json.loads(move_history_file(output_dir).read_text(encoding="utf-8"))
    assert moves["moves"] == []

    reaction_records = json.loads(reaction_records_file(output_dir).read_text(encoding="utf-8"))
    assert reaction_records["records"] == []

    reconsolidation = json.loads(reconsolidation_records_file(output_dir).read_text(encoding="utf-8"))
    assert reconsolidation["records"] == []

    policy = json.loads(reader_policy_file(output_dir).read_text(encoding="utf-8"))
    assert policy["policy_version"] == ATTENTIONAL_V2_POLICY_VERSION
    assert policy["bridge"]["source_anchor_required"] is True
    assert policy["search"]["default_mode"] == "no_search"
    assert policy["resume"]["cold_resume_target_sentences"] == 8
    assert policy["resume"]["reconstitution_resume_max_sentences"] == 30

    resume_metadata = json.loads(resume_metadata_file(output_dir).read_text(encoding="utf-8"))
    assert resume_metadata["resume_available"] is False
    assert resume_metadata["default_resume_kind"] == "warm_resume"

    survey = json.loads(survey_map_file(output_dir).read_text(encoding="utf-8"))
    assert survey["status"] == "not_started"

    revisit = json.loads(revisit_index_file(output_dir).read_text(encoding="utf-8"))
    assert revisit["anchors"] == {}

    assert event_stream_file(output_dir).read_text(encoding="utf-8") == ""
    assert result["artifact_map"]["working_pressure"].endswith("working_pressure.json")


def test_attentional_v2_adapter_is_honest_about_phase7_scope():
    """The adapter should not claim parse/read behavior before later phases land."""

    mechanism = AttentionalV2Mechanism()

    with pytest.raises(NotImplementedError):
        mechanism.parse_book(ParseRequest(book_path=Path("demo.epub"), mechanism_key=ATTENTIONAL_V2_MECHANISM_KEY))

    with pytest.raises(NotImplementedError):
        mechanism.read_book(ReadRequest(book_path=Path("demo.epub"), mechanism_key=ATTENTIONAL_V2_MECHANISM_KEY))
