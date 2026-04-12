"""Tests for the attentional_v2 Phase 1 scaffold."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.attentional_v2 import runner as runner_module
from src.attentional_v2.slow_cycle import project_chapter_result_compatibility
from src.attentional_v2.schemas import ATTENTIONAL_V2_MECHANISM_VERSION, ATTENTIONAL_V2_POLICY_VERSION, ATTENTIONAL_V2_SCHEMA_VERSION
from src.attentional_v2.storage import (
    ATTENTIONAL_V2_MECHANISM_KEY,
    anchor_memory_file,
    chapter_result_compatibility_file,
    event_stream_file,
    knowledge_activations_file,
    local_buffer_file,
    local_continuity_file,
    move_history_file,
    reaction_records_file,
    reader_policy_file,
    read_audit_file,
    reflective_summaries_file,
    reconsolidation_records_file,
    revisit_index_file,
    resume_metadata_file,
    survey_map_file,
    trigger_state_file,
    unitization_audit_file,
    working_pressure_file,
)
from src.reading_core.runtime_contracts import ParseRequest, ReadRequest
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_runtime.provisioning import ProvisionedBook
from src.reading_runtime.artifacts import checkpoint_summary_file, mechanism_manifest_file, runtime_shell_file
from src.reading_runtime.shell_state import load_runtime_shell


def _fixture_epub() -> Path:
    """Return the tracked EPUB fixture used for live runner tests."""

    return Path(__file__).resolve().parent / "fixtures" / "e2e_runtime" / "sample-upload.epub"


def _provisioned_book() -> ProvisionedBook:
    """Return a lightweight shared parsed-book fixture for attentional runner tests."""

    book_document = {
        "metadata": {
            "book": "Demo Book",
            "author": "Tester",
            "book_language": "en",
            "output_language": "en",
            "source_file": str(_fixture_epub()),
        },
        "chapters": [
            {
                "id": 1,
                "title": "Chapter 1",
                "chapter_number": 1,
                "reference": "Chapter 1",
                "paragraphs": [
                    {
                        "paragraph_index": 1,
                        "text": "Alpha sentence. Beta sentence.",
                        "href": "chapter-1.xhtml",
                        "start_cfi": "/6/2[chap01]!/4/2/1:0",
                        "end_cfi": "/6/2[chap01]!/4/2/1:24",
                        "text_role": "body",
                    }
                ],
                "sentences": [
                    {
                        "sentence_id": "c1-s1",
                        "sentence_index": 1,
                        "paragraph_index": 1,
                        "text": "Alpha sentence.",
                        "text_role": "body",
                        "locator": {
                            "href": "chapter-1.xhtml",
                            "paragraph_index": 1,
                            "paragraph_start": 1,
                            "paragraph_end": 1,
                            "char_start": 0,
                            "char_end": 15,
                            "start_cfi": "/6/2[chap01]!/4/2/1:0",
                            "end_cfi": "/6/2[chap01]!/4/2/1:15",
                        },
                    },
                    {
                        "sentence_id": "c1-s2",
                        "sentence_index": 2,
                        "paragraph_index": 1,
                        "text": "Beta sentence.",
                        "text_role": "body",
                        "locator": {
                            "href": "chapter-1.xhtml",
                            "paragraph_index": 1,
                            "paragraph_start": 1,
                            "paragraph_end": 1,
                            "char_start": 16,
                            "char_end": 30,
                            "start_cfi": "/6/2[chap01]!/4/2/1:16",
                            "end_cfi": "/6/2[chap01]!/4/2/1:30",
                        },
                    },
                ],
            }
        ],
    }
    return ProvisionedBook(
        book_path=_fixture_epub(),
        title="Demo Book",
        author="Tester",
        book_language="en",
        output_language="en",
        output_dir=Path("output/demo-book"),
        raw_chapters=None,
        book_document=book_document,
    )


def test_attentional_v2_initialization_writes_phase8_artifacts(tmp_path):
    """The Phase 1-8 scaffold should write the shared shell and private state files."""

    output_dir = tmp_path / "output" / "demo-book"

    result = AttentionalV2Mechanism().initialize_artifacts(output_dir)

    assert result["mechanism_key"] == ATTENTIONAL_V2_MECHANISM_KEY
    assert result["mechanism_version"] == ATTENTIONAL_V2_MECHANISM_VERSION
    assert result["policy_version"] == ATTENTIONAL_V2_POLICY_VERSION

    shell = load_runtime_shell(runtime_shell_file(output_dir))
    assert shell["mechanism_key"] == ATTENTIONAL_V2_MECHANISM_KEY
    assert shell["mechanism_version"] == ATTENTIONAL_V2_MECHANISM_VERSION
    assert shell["observability_mode"] == "standard"
    assert shell["cursor"]["position_kind"] == "chapter"

    checkpoint = json.loads(checkpoint_summary_file(output_dir, "bootstrap").read_text(encoding="utf-8"))
    assert checkpoint["mechanism_key"] == ATTENTIONAL_V2_MECHANISM_KEY
    assert checkpoint["observability_mode"] == "standard"
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
    assert policy["unitize"]["max_coverage_unit_sentences"] == 12
    assert policy["bridge"]["source_anchor_required"] is True
    assert policy["search"]["default_mode"] == "no_search"
    assert policy["resume"]["cold_resume_target_sentences"] == 8
    assert policy["resume"]["reconstitution_resume_max_sentences"] == 30
    assert policy["logging"]["observability_mode"] == "standard"
    assert policy["logging"]["debug_event_stream"] is False

    resume_metadata = json.loads(resume_metadata_file(output_dir).read_text(encoding="utf-8"))
    assert resume_metadata["resume_available"] is False
    assert resume_metadata["default_resume_kind"] == "warm_resume"

    survey = json.loads(survey_map_file(output_dir).read_text(encoding="utf-8"))
    assert survey["status"] == "not_started"

    revisit = json.loads(revisit_index_file(output_dir).read_text(encoding="utf-8"))
    assert revisit["anchors"] == {}

    assert event_stream_file(output_dir).read_text(encoding="utf-8") == ""
    assert result["artifact_map"]["working_pressure"].endswith("working_pressure.json")


def test_attentional_v2_parse_book_creates_ready_artifacts_without_iterator_structure(tmp_path, monkeypatch):
    """The live parse path should build canonical attentional artifacts without iterator structure."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner_module, "ensure_canonical_parse", lambda *args, **kwargs: _provisioned_book())
    mechanism = AttentionalV2Mechanism()
    result = mechanism.parse_book(
        ParseRequest(
            book_path=_fixture_epub(),
            mechanism_key=ATTENTIONAL_V2_MECHANISM_KEY,
        )
    )

    assert result.book_document["chapters"]
    assert result.mechanism_artifact is not None
    assert result.mechanism_artifact["artifact_map"]["survey_map"].endswith("survey_map.json")
    assert survey_map_file(result.output_dir).exists()
    assert not (result.output_dir / "_mechanisms" / "iterator_v1" / "derived" / "structure.json").exists()
    shell = load_runtime_shell(runtime_shell_file(result.output_dir))
    assert shell["mechanism_key"] == ATTENTIONAL_V2_MECHANISM_KEY
    assert json.loads((result.output_dir / "public" / "book_manifest.json").read_text(encoding="utf-8"))["chapters"]


def test_attentional_v2_read_book_runs_live_loop_and_persists_compatibility_results(tmp_path, monkeypatch):
    """The live runner should persist unitization/read audits, reactions, and compatibility payloads."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner_module, "ensure_canonical_parse", lambda *args, **kwargs: _provisioned_book())
    captured_unit_reads: list[list[str]] = []
    captured_carry_forward_contexts: list[dict[str, object]] = []

    def fake_read_unit(**kwargs):
        current_unit_sentences = kwargs["current_unit_sentences"]
        focal_sentence = current_unit_sentences[-1]
        anchor_quote = str(focal_sentence.get("text", "") or "").strip()[:80]
        captured_unit_reads.append([str(sentence.get("sentence_id")) for sentence in current_unit_sentences])
        captured_carry_forward_contexts.append(dict(kwargs["carry_forward_context"]))
        return {
            "local_understanding": f"Meaning unit around {anchor_quote[:24]}",
            "move_hint": "advance",
            "continuation_pressure": False,
            "implicit_uptake": [],
            "anchor_evidence": [
                {
                    "sentence_id": str(focal_sentence.get("sentence_id")),
                    "quote": anchor_quote,
                    "why_it_matters": "The focal line became legible during the formal read.",
                }
            ],
            "prior_material_use": {
                "materially_used": False,
                "explanation": "",
                "supporting_ref_ids": [],
            },
            "raw_reaction": {
                "type": "highlight",
                "anchor_quote": anchor_quote,
                "content": f"Noted: {anchor_quote[:40]}",
                "related_anchor_quotes": [],
                "search_query": "",
                "search_results": [],
            },
            "context_request": None,
        }

    def fake_phase6_chapter_cycle(**kwargs):
        compatibility_payload = project_chapter_result_compatibility(
            book_id=kwargs["book_id"],
            chapter=kwargs["chapter"],
            reaction_records=kwargs["reaction_records"],
            output_language=kwargs["output_language"],
            output_dir=kwargs["output_dir"],
            persist=True,
        )
        return {
            "chapter_consolidation": {"chapter_ref": kwargs["chapter"].get("reference", "")},
            "promotion_results": [],
            "working_pressure": kwargs["working_pressure"],
            "anchor_memory": kwargs["anchor_memory"],
            "reflective_summaries": kwargs["reflective_summaries"],
            "knowledge_activations": kwargs["knowledge_activations"],
            "reaction_records": kwargs["reaction_records"],
            "compatibility_payload": compatibility_payload,
        }

    def fake_process_sentence_intake(sentence, *, local_buffer, working_pressure, anchor_memory, window_size=6, cadence_limit=4):
        next_buffer = {
            **local_buffer,
            "current_sentence_id": sentence["sentence_id"],
            "current_sentence_index": sentence["sentence_index"],
            "recent_sentences": [*local_buffer.get("recent_sentences", []), dict(sentence)][-window_size:],
            "open_meaning_unit_sentence_ids": [sentence["sentence_id"]],
            "seen_sentence_ids": [*local_buffer.get("seen_sentence_ids", []), sentence["sentence_id"]],
        }
        return next_buffer, {
            "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
            "mechanism_version": ATTENTIONAL_V2_MECHANISM_VERSION,
            "current_sentence_id": sentence["sentence_id"],
            "output": "zoom_now",
            "gate_state": "hot",
            "signals": [],
            "cadence_counter": 1,
            "callback_anchor_ids": [],
        }

    monkeypatch.setattr(
        runner_module,
        "navigate_unitize",
        lambda *, current_sentence, preview_sentences, **_kwargs: {
            "start_sentence_id": current_sentence["sentence_id"],
            "end_sentence_id": current_sentence["sentence_id"],
            "preview_range": {
                "start_sentence_id": preview_sentences[0]["sentence_id"],
                "end_sentence_id": preview_sentences[-1]["sentence_id"],
            },
            "boundary_type": "paragraph_end",
            "evidence_sentence_ids": [current_sentence["sentence_id"]],
            "reason": "test_unitize_single_sentence",
            "continuation_pressure": False,
        },
    )
    monkeypatch.setattr(runner_module, "process_sentence_intake", fake_process_sentence_intake)
    monkeypatch.setattr(runner_module, "read_unit", fake_read_unit)
    monkeypatch.setattr(runner_module, "run_phase6_chapter_cycle", fake_phase6_chapter_cycle)

    mechanism = AttentionalV2Mechanism()
    result = mechanism.read_book(
        ReadRequest(
            book_path=_fixture_epub(),
            mechanism_key=ATTENTIONAL_V2_MECHANISM_KEY,
            mechanism_config={},
        )
    )

    assert result.normalized_eval_bundle is not None
    assert result.normalized_eval_bundle["mechanism_key"] == ATTENTIONAL_V2_MECHANISM_KEY
    chapter_payload = json.loads(chapter_result_compatibility_file(result.output_dir, 1).read_text(encoding="utf-8"))
    unitize_lines = unitization_audit_file(result.output_dir).read_text(encoding="utf-8").strip().splitlines()
    read_audit_lines = read_audit_file(result.output_dir).read_text(encoding="utf-8").strip().splitlines()
    read_audits = [json.loads(line) for line in read_audit_lines]
    assert chapter_payload["visible_reaction_count"] >= 1
    assert captured_unit_reads == [["c1-s1"], ["c1-s2"]]
    assert captured_carry_forward_contexts[0]["continuity_digest"]["recent_reactions"] == []
    assert captured_carry_forward_contexts[1]["continuity_digest"]["recent_reactions"]
    assert len(unitize_lines) == 2
    assert len(read_audit_lines) == 2
    assert all(audit["raw_reaction_present"] is True for audit in read_audits)
    assert read_audits[1]["carry_forward_ref_ids"]
    shell = load_runtime_shell(runtime_shell_file(result.output_dir))
    assert shell["mechanism_key"] == ATTENTIONAL_V2_MECHANISM_KEY
    assert shell["status"] == "completed"
    assert shell["last_checkpoint_id"] == "chapter-001"
    manifest = json.loads((result.output_dir / "public" / "book_manifest.json").read_text(encoding="utf-8"))
    chapter_manifest = manifest["chapters"][0]
    assert chapter_manifest["result_file"] == "_mechanisms/attentional_v2/derived/chapter_result_compatibility/chapter-001.json"
    assert chapter_manifest["visible_reaction_count"] >= 1
    assert chapter_manifest["reaction_type_diversity"] >= 1


def test_attentional_v2_read_book_tolerates_missing_reaction_payload(tmp_path, monkeypatch):
    """The live runner should tolerate a read result with no raw reaction payload."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner_module, "ensure_canonical_parse", lambda *args, **kwargs: _provisioned_book())

    def fake_read_unit(**kwargs):
        focal_sentence = kwargs["current_unit_sentences"][-1]
        anchor_quote = str(focal_sentence.get("text", "") or "").strip()[:80]
        return {
            "local_understanding": f"Meaning unit around {anchor_quote[:24]}",
            "move_hint": "advance",
            "continuation_pressure": False,
            "implicit_uptake": [],
            "anchor_evidence": [
                {
                    "sentence_id": str(focal_sentence.get("sentence_id")),
                    "quote": anchor_quote,
                    "why_it_matters": "The line was read, but it did not warrant a surfaced reaction.",
                }
            ],
            "prior_material_use": {
                "materially_used": False,
                "explanation": "",
                "supporting_ref_ids": [],
            },
            "raw_reaction": None,
            "context_request": None,
        }

    def fake_phase6_chapter_cycle(**kwargs):
        compatibility_payload = project_chapter_result_compatibility(
            book_id=kwargs["book_id"],
            chapter=kwargs["chapter"],
            reaction_records=kwargs["reaction_records"],
            output_language=kwargs["output_language"],
            output_dir=kwargs["output_dir"],
            persist=True,
        )
        return {
            "chapter_consolidation": {"chapter_ref": kwargs["chapter"].get("reference", "")},
            "promotion_results": [],
            "working_pressure": kwargs["working_pressure"],
            "anchor_memory": kwargs["anchor_memory"],
            "reflective_summaries": kwargs["reflective_summaries"],
            "knowledge_activations": kwargs["knowledge_activations"],
            "reaction_records": kwargs["reaction_records"],
            "compatibility_payload": compatibility_payload,
        }

    def fake_process_sentence_intake(sentence, *, local_buffer, working_pressure, anchor_memory, window_size=6, cadence_limit=4):
        next_buffer = {
            **local_buffer,
            "current_sentence_id": sentence["sentence_id"],
            "current_sentence_index": sentence["sentence_index"],
            "recent_sentences": [*local_buffer.get("recent_sentences", []), dict(sentence)][-window_size:],
            "open_meaning_unit_sentence_ids": [sentence["sentence_id"]],
            "seen_sentence_ids": [*local_buffer.get("seen_sentence_ids", []), sentence["sentence_id"]],
        }
        return next_buffer, {
            "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
            "mechanism_version": ATTENTIONAL_V2_MECHANISM_VERSION,
            "current_sentence_id": sentence["sentence_id"],
            "output": "zoom_now",
            "gate_state": "hot",
            "signals": [],
            "cadence_counter": 1,
            "callback_anchor_ids": [],
        }

    monkeypatch.setattr(
        runner_module,
        "navigate_unitize",
        lambda *, current_sentence, preview_sentences, **_kwargs: {
            "start_sentence_id": current_sentence["sentence_id"],
            "end_sentence_id": current_sentence["sentence_id"],
            "preview_range": {
                "start_sentence_id": preview_sentences[0]["sentence_id"],
                "end_sentence_id": preview_sentences[-1]["sentence_id"],
            },
            "boundary_type": "paragraph_end",
            "evidence_sentence_ids": [current_sentence["sentence_id"]],
            "reason": "test_unitize_single_sentence",
            "continuation_pressure": False,
        },
    )
    monkeypatch.setattr(runner_module, "process_sentence_intake", fake_process_sentence_intake)
    monkeypatch.setattr(runner_module, "read_unit", fake_read_unit)
    monkeypatch.setattr(runner_module, "run_phase6_chapter_cycle", fake_phase6_chapter_cycle)

    mechanism = AttentionalV2Mechanism()
    result = mechanism.read_book(
        ReadRequest(
            book_path=_fixture_epub(),
            mechanism_key=ATTENTIONAL_V2_MECHANISM_KEY,
            mechanism_config={},
        )
    )

    assert result.normalized_eval_bundle is not None
    chapter_payload = json.loads(chapter_result_compatibility_file(result.output_dir, 1).read_text(encoding="utf-8"))
    assert chapter_payload["visible_reaction_count"] == 0
    reaction_records = json.loads(reaction_records_file(result.output_dir).read_text(encoding="utf-8"))
    assert reaction_records["records"] == []
    shell = load_runtime_shell(runtime_shell_file(result.output_dir))
    assert shell["status"] == "completed"


def test_attentional_v2_read_book_still_runs_formal_read_for_monitor_path(tmp_path, monkeypatch):
    """Monitor-path sentences should still enter one formal unitized read in Phase A."""

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(runner_module, "ensure_canonical_parse", lambda *args, **kwargs: _provisioned_book())

    def fake_phase6_chapter_cycle(**kwargs):
        compatibility_payload = project_chapter_result_compatibility(
            book_id=kwargs["book_id"],
            chapter=kwargs["chapter"],
            reaction_records=kwargs["reaction_records"],
            output_language=kwargs["output_language"],
            output_dir=kwargs["output_dir"],
            persist=True,
        )
        return {
            "chapter_consolidation": {"chapter_ref": kwargs["chapter"].get("reference", "")},
            "promotion_results": [],
            "working_pressure": kwargs["working_pressure"],
            "anchor_memory": kwargs["anchor_memory"],
            "reflective_summaries": kwargs["reflective_summaries"],
            "knowledge_activations": kwargs["knowledge_activations"],
            "reaction_records": kwargs["reaction_records"],
            "compatibility_payload": compatibility_payload,
        }

    def fake_process_sentence_intake(sentence, *, local_buffer, working_pressure, anchor_memory, window_size=6, cadence_limit=4):
        next_buffer = {
            **local_buffer,
            "current_sentence_id": sentence["sentence_id"],
            "current_sentence_index": sentence["sentence_index"],
            "recent_sentences": [*local_buffer.get("recent_sentences", []), dict(sentence)][-window_size:],
            "open_meaning_unit_sentence_ids": [sentence["sentence_id"]],
            "seen_sentence_ids": [*local_buffer.get("seen_sentence_ids", []), sentence["sentence_id"]],
        }
        return next_buffer, {
            "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
            "mechanism_version": ATTENTIONAL_V2_MECHANISM_VERSION,
            "current_sentence_id": sentence["sentence_id"],
            "output": "monitor",
            "gate_state": "watch",
            "signals": [],
            "cadence_counter": 1,
            "callback_anchor_ids": [],
        }

    read_calls: list[list[str]] = []

    def fake_read_unit(**kwargs):
        read_calls.append(
            [
                str(sentence.get("sentence_id"))
                for sentence in kwargs["current_unit_sentences"]
            ]
        )
        return {
            "local_understanding": "monitor path still got read",
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
            "context_request": None,
        }

    monkeypatch.setattr(
        runner_module,
        "navigate_unitize",
        lambda *, current_sentence, preview_sentences, **_kwargs: {
            "start_sentence_id": current_sentence["sentence_id"],
            "end_sentence_id": current_sentence["sentence_id"],
            "preview_range": {
                "start_sentence_id": preview_sentences[0]["sentence_id"],
                "end_sentence_id": preview_sentences[-1]["sentence_id"],
            },
            "boundary_type": "paragraph_end",
            "evidence_sentence_ids": [current_sentence["sentence_id"]],
            "reason": "monitor path single sentence",
            "continuation_pressure": False,
        },
    )
    monkeypatch.setattr(runner_module, "process_sentence_intake", fake_process_sentence_intake)
    monkeypatch.setattr(runner_module, "read_unit", fake_read_unit)
    monkeypatch.setattr(runner_module, "run_phase6_chapter_cycle", fake_phase6_chapter_cycle)

    mechanism = AttentionalV2Mechanism()
    result = mechanism.read_book(
        ReadRequest(
            book_path=_fixture_epub(),
            mechanism_key=ATTENTIONAL_V2_MECHANISM_KEY,
            mechanism_config={},
        )
    )

    local_buffer = json.loads(local_buffer_file(result.output_dir).read_text(encoding="utf-8"))
    trigger_state = json.loads(trigger_state_file(result.output_dir).read_text(encoding="utf-8"))
    chapter_payload = json.loads(chapter_result_compatibility_file(result.output_dir, 1).read_text(encoding="utf-8"))
    shell = load_runtime_shell(runtime_shell_file(result.output_dir))

    assert local_buffer["current_sentence_id"] == "c1-s2"
    assert trigger_state["output"] == "monitor"
    assert chapter_payload["visible_reaction_count"] == 0
    assert shell["status"] == "completed"
    assert read_calls == [["c1-s1"], ["c1-s2"]]


def test_attentional_v2_rejects_book_analysis_mode(tmp_path, monkeypatch):
    """The live runner should fail fast on book_analysis mode in this slice."""

    monkeypatch.chdir(tmp_path)
    mechanism = AttentionalV2Mechanism()

    with pytest.raises(ValueError, match=r"does not support .*book_analysis mode"):
        mechanism.read_book(
            ReadRequest(
                book_path=_fixture_epub(),
                mechanism_key=ATTENTIONAL_V2_MECHANISM_KEY,
                task_mode="book_analysis",
            )
        )
