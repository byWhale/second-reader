"""Tests for attentional_v2 Phase 7 checkpointing and resume helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.attentional_v2.resume import persist_reading_position, resume_from_checkpoint, write_full_checkpoint
from src.attentional_v2.schemas import (
    build_empty_anchor_memory,
    build_empty_local_buffer,
    build_empty_reflective_summaries,
    build_empty_working_pressure,
)
from src.attentional_v2.state_ops import close_local_meaning_unit, push_local_buffer_sentence
from src.attentional_v2.storage import (
    anchor_bank_file,
    concept_registry_file,
    continuation_capsule_file,
    event_stream_file,
    full_checkpoint_file,
    load_json,
    local_buffer_file,
    reaction_records_file,
    reader_policy_file,
    reflective_frames_file,
    resume_metadata_file,
    runtime_dir,
    save_json,
    thread_trace_file,
    trigger_state_file,
    working_state_file,
)
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_runtime.artifacts import activity_file, checkpoint_summary_file, runtime_shell_file
from src.reading_runtime.shell_state import load_runtime_shell, save_runtime_shell


def _make_book_document(total_sentences: int) -> dict[str, object]:
    """Build one compact shared parsed-book document with a single sentence inventory."""

    paragraphs: list[dict[str, object]] = []
    sentences: list[dict[str, object]] = []
    for sentence_index in range(1, total_sentences + 1):
        text = f"Sentence {sentence_index}."
        paragraph = {
            "href": "chapter-1.xhtml",
            "start_cfi": None,
            "end_cfi": None,
            "paragraph_index": sentence_index,
            "text": text,
            "block_tag": "p",
            "heading_level": None,
            "text_role": "body",
            "item_id": f"p-{sentence_index}",
            "spine_index": 1,
        }
        sentence = {
            "sentence_id": f"c1-s{sentence_index}",
            "sentence_index": sentence_index,
            "sentence_in_paragraph": 1,
            "paragraph_index": sentence_index,
            "text": text,
            "text_role": "body",
            "locator": {
                "href": "chapter-1.xhtml",
                "paragraph_index": sentence_index,
                "paragraph_start": sentence_index,
                "paragraph_end": sentence_index,
                "char_start": 0,
                "char_end": len(text),
            },
        }
        paragraphs.append(paragraph)
        sentences.append(sentence)

    return {
        "metadata": {
            "book": "Demo Book",
            "author": "Tester",
            "book_language": "en",
            "output_language": "en",
            "source_file": "demo.epub",
        },
        "chapters": [
            {
                "id": 1,
                "title": "Chapter 1",
                "chapter_number": 1,
                "level": 1,
                "item_id": "ch-1",
                "href": "chapter-1.xhtml",
                "spine_index": 1,
                "chapter_heading": {"text": "Chapter 1", "locator": {"href": "chapter-1.xhtml", "paragraph_index": 1}},
                "paragraphs": paragraphs,
                "sentences": sentences,
            }
        ],
    }


def _build_buffer(*, total_sentences: int, closed_breaks: list[int]) -> dict[str, object]:
    """Build one local buffer with deterministic meaning-unit boundaries."""

    state = build_empty_local_buffer()
    for sentence_index in range(1, total_sentences + 1):
        state = push_local_buffer_sentence(
            state,
            {
                "sentence_id": f"c1-s{sentence_index}",
                "sentence_index": sentence_index,
                "paragraph_index": sentence_index,
                "text": f"Sentence {sentence_index}.",
                "text_role": "body",
            },
            window_size=max(6, total_sentences),
        )
        if sentence_index in closed_breaks:
            state = close_local_meaning_unit(state)
    return state


def test_checkpoint_and_warm_resume_restore_exact_hot_state(tmp_path: Path):
    """Warm resume should restore the checkpointed hot state without rereading source sentences."""

    output_dir = tmp_path / "output" / "demo-book"
    mechanism = AttentionalV2Mechanism()
    mechanism.initialize_artifacts(output_dir)
    book_document = _make_book_document(6)
    local_buffer = _build_buffer(total_sentences=6, closed_breaks=[3])
    persist_reading_position(
        output_dir,
        chapter_id=1,
        chapter_ref="Chapter 1",
        local_buffer=local_buffer,
        status="deep_reading",
        phase="reading",
    )
    save_json(
        reaction_records_file(output_dir),
        {
            "schema_version": 1,
            "mechanism_version": "attentional_v2-phase8",
            "updated_at": "2026-03-23T00:00:00Z",
            "records": [{"reaction_id": "rx-1"}],
        },
    )

    checkpoint = write_full_checkpoint(output_dir, checkpoint_id="cp-1", checkpoint_reason="unit_test")
    assert full_checkpoint_file(output_dir, "cp-1").exists()
    assert checkpoint["visible_reaction_ids"] == ["rx-1"]
    assert checkpoint["continuation_capsule"]["chapter_ref"] == "Chapter 1"
    assert continuation_capsule_file(output_dir).exists()

    save_json(local_buffer_file(output_dir), build_empty_local_buffer())
    resumed = resume_from_checkpoint(output_dir, book_document=book_document, requested_resume_kind="warm_resume")

    shell = load_runtime_shell(runtime_shell_file(output_dir))
    assert shell["last_checkpoint_id"] == "cp-1"
    assert shell["cursor"]["sentence_id"] == "c1-s6"
    assert resumed["effective_resume_kind"] == "warm_resume"
    assert resumed["continuation_capsule_status"] == "available"
    assert resumed["resume_window_sentence_ids"] == []
    assert resumed["local_buffer"]["current_sentence_id"] == "c1-s6"
    assert resumed["local_buffer"]["is_reconstructed"] is False
    assert load_json(resume_metadata_file(output_dir))["last_resume_status"] == "warm_restored"
    assert load_json(checkpoint_summary_file(output_dir, "cp-1"))["visible_reaction_ids"] == ["rx-1"]
    activity_events = [
        json.loads(line)
        for line in activity_file(output_dir).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [event["type"] for event in activity_events] == ["checkpoint.saved", "resume.restored"]
    assert activity_events[0]["reading_locus"]["sentence_end_id"] == "c1-s6"
    assert activity_events[1]["last_resume_kind"] == "warm_resume"
    assert event_stream_file(output_dir).read_text(encoding="utf-8") == ""


def test_persist_reading_position_recreates_missing_runtime_shell(tmp_path: Path):
    """Persist should recreate the thin runtime shell if a local eval run deleted it."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    runtime_shell_file(output_dir).unlink()

    local_buffer = _build_buffer(total_sentences=6, closed_breaks=[3])
    persist_reading_position(
        output_dir,
        chapter_id=1,
        chapter_ref="Chapter 1",
        local_buffer=local_buffer,
        status="running",
        phase="reading",
    )

    shell = load_runtime_shell(runtime_shell_file(output_dir))
    assert shell["mechanism_key"] == "attentional_v2"
    assert shell["status"] == "running"
    assert shell["phase"] == "reading"
    assert shell["cursor"]["sentence_id"] == "c1-s6"


def test_persist_reading_position_preserves_detour_state(tmp_path: Path):
    """Persisting position should carry detour state through local continuity snapshots."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    local_buffer = _build_buffer(total_sentences=6, closed_breaks=[3])

    persisted = persist_reading_position(
        output_dir,
        chapter_id=1,
        chapter_ref="Chapter 1",
        local_buffer=local_buffer,
        local_continuity={
            "mainline_cursor": {
                "position_kind": "sentence",
                "chapter_id": 1,
                "chapter_ref": "Chapter 1",
                "sentence_id": "c1-s6",
            },
            "active_detour_id": "detour:1:c1-s6:1",
            "active_detour_need": {
                "reason": "Need to revisit the earlier setup.",
                "target_hint": "the opening setup",
                "status": "open",
            },
            "detour_trace": [
                {
                    "detour_id": "detour:1:c1-s6:1",
                    "origin_cursor": {
                        "position_kind": "sentence",
                        "chapter_id": 1,
                        "chapter_ref": "Chapter 1",
                        "sentence_id": "c1-s6",
                    },
                    "origin_target_hint": "the opening setup",
                    "status": "open",
                }
            ],
        },
    )

    continuity = persisted["local_continuity"]
    assert continuity["active_detour_id"] == "detour:1:c1-s6:1"
    assert continuity["active_detour_need"]["target_hint"] == "the opening setup"
    assert continuity["detour_trace"][0]["status"] == "open"


def test_cold_resume_expands_to_open_meaning_unit_start(tmp_path: Path):
    """Cold resume should backfill to the start of the current open meaning unit when needed."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    book_document = _make_book_document(16)
    local_buffer = _build_buffer(total_sentences=16, closed_breaks=[4, 6])
    persist_reading_position(output_dir, chapter_id=1, chapter_ref="Chapter 1", local_buffer=local_buffer)
    write_full_checkpoint(output_dir, checkpoint_id="cp-1", checkpoint_reason="cold_resume_fixture")

    resumed = resume_from_checkpoint(output_dir, book_document=book_document, requested_resume_kind="cold_resume")

    assert resumed["effective_resume_kind"] == "cold_resume"
    assert resumed["resume_window_sentence_ids"] == [f"c1-s{sentence_index}" for sentence_index in range(7, 17)]
    assert resumed["local_buffer"]["is_reconstructed"] is True
    assert resumed["local_continuity"]["last_resume_kind"] == "cold_resume"
    assert resumed["trigger_state"]["output"] == "no_zoom"


def test_reconstitution_resume_uses_recent_meaning_units_with_cap(tmp_path: Path):
    """Reconstitution resume should expand across recent meaning units without exceeding the hard cap."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    book_document = _make_book_document(50)
    local_buffer = _build_buffer(total_sentences=50, closed_breaks=[10, 20, 30, 40])
    persist_reading_position(output_dir, chapter_id=1, chapter_ref="Chapter 1", local_buffer=local_buffer)
    write_full_checkpoint(output_dir, checkpoint_id="cp-1", checkpoint_reason="reconstitution_fixture")

    resumed = resume_from_checkpoint(output_dir, book_document=book_document, requested_resume_kind="reconstitution_resume")

    assert resumed["effective_resume_kind"] == "reconstitution_resume"
    assert resumed["resume_window_sentence_ids"] == [f"c1-s{sentence_index}" for sentence_index in range(21, 51)]
    assert len(resumed["resume_window_sentence_ids"]) == 30
    assert resumed["local_buffer"]["is_reconstructed"] is True


def test_persist_reading_position_recreates_missing_runtime_shell(tmp_path: Path):
    """Persisting position should recover the thin runtime shell when it is absent."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    runtime_shell_file(output_dir).unlink()
    local_buffer = _build_buffer(total_sentences=6, closed_breaks=[3])

    persist_reading_position(output_dir, chapter_id=1, chapter_ref="Chapter 1", local_buffer=local_buffer)

    shell = load_runtime_shell(runtime_shell_file(output_dir))
    assert shell["mechanism_key"] == "attentional_v2"
    assert shell["cursor"]["sentence_id"] == "c1-s6"
    assert shell["status"] == "initialized"
    assert shell["phase"] == "preparing"


def test_incompatible_checkpoint_falls_back_to_live_warm_resume(tmp_path: Path):
    """Compatibility failure should fall back to live-state warm resume rather than fake a cold reconstruction."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    book_document = _make_book_document(12)
    local_buffer = _build_buffer(total_sentences=12, closed_breaks=[4, 8])
    persist_reading_position(output_dir, chapter_id=1, chapter_ref="Chapter 1", local_buffer=local_buffer)
    write_full_checkpoint(output_dir, checkpoint_id="cp-1", checkpoint_reason="compatibility_fixture")

    checkpoint = load_json(full_checkpoint_file(output_dir, "cp-1"))
    checkpoint["mechanism_version"] = "attentional_v2-phase0"
    save_json(full_checkpoint_file(output_dir, "cp-1"), checkpoint)

    resumed = resume_from_checkpoint(output_dir, book_document=book_document, requested_resume_kind="cold_resume")

    assert resumed["compatibility_status"] == "fallback_to_live_state"
    assert "mechanism_version_mismatch" in resumed["compatibility_issues"]
    assert resumed["effective_resume_kind"] == "warm_resume"
    assert resumed["local_buffer"]["is_reconstructed"] is False


def test_resume_rejects_legacy_runtime_and_old_checkpoint_shapes(tmp_path: Path):
    """Old-format runtime/checkpoint state should fail fast after the Phase C.4 retirement."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    book_document = _make_book_document(6)
    local_buffer = _build_buffer(total_sentences=6, closed_breaks=[3])
    persist_reading_position(output_dir, chapter_id=1, chapter_ref="Chapter 1", local_buffer=local_buffer)

    legacy_working_pressure = build_empty_working_pressure()
    legacy_working_pressure["local_questions"] = [
        {
            "item_id": "q-1",
            "kind": "question",
            "statement": "What is still unresolved?",
            "status": "open",
            "support_anchor_ids": ["a-1"],
        }
    ]
    legacy_anchor_memory = build_empty_anchor_memory()
    legacy_anchor_memory["anchor_records"] = [
        {
            "anchor_id": "a-1",
            "sentence_start_id": "c1-s1",
            "sentence_end_id": "c1-s1",
            "quote": "Sentence 1.",
            "anchor_kind": "unit_evidence",
            "why_it_mattered": "legacy checkpoint seed",
            "status": "active",
            "locator": {},
        }
    ]
    legacy_anchor_memory["motif_index"] = {"sentence": ["a-1"]}
    legacy_reflective = build_empty_reflective_summaries()
    legacy_reflective["chapter_understandings"] = [
        {
            "item_id": "frame-1",
            "statement": "Legacy reflective frame.",
            "chapter_ref": "Chapter 1",
            "confidence_band": "working",
            "support_anchor_ids": ["a-1"],
        }
    ]

    for path in (
        working_state_file(output_dir),
        concept_registry_file(output_dir),
        thread_trace_file(output_dir),
        reflective_frames_file(output_dir),
        anchor_bank_file(output_dir),
    ):
        path.unlink(missing_ok=True)

    save_json(runtime_dir(output_dir) / "working_pressure.json", legacy_working_pressure)
    save_json(runtime_dir(output_dir) / "anchor_memory.json", legacy_anchor_memory)
    save_json(runtime_dir(output_dir) / "reflective_summaries.json", legacy_reflective)

    shell = load_runtime_shell(runtime_shell_file(output_dir))
    legacy_checkpoint = {
        "schema_version": 1,
        "mechanism_version": shell.get("mechanism_version"),
        "policy_version": shell.get("policy_version"),
        "checkpoint_id": "legacy-cp",
        "created_at": "2026-04-12T00:00:00Z",
        "checkpoint_reason": "legacy_test",
        "resume_kind": "warm_resume",
        "cursor": dict(shell.get("cursor", {})),
        "active_artifact_refs": {},
        "visible_reaction_ids": [],
        "local_buffer": load_json(local_buffer_file(output_dir)),
        "local_continuity": load_json(runtime_dir(output_dir) / "local_continuity.json"),
        "trigger_state": load_json(trigger_state_file(output_dir)),
        "working_pressure": legacy_working_pressure,
        "anchor_memory": legacy_anchor_memory,
        "reflective_summaries": legacy_reflective,
        "knowledge_activations": load_json(runtime_dir(output_dir) / "knowledge_activations.json"),
        "move_history": load_json(runtime_dir(output_dir) / "move_history.json"),
        "reaction_records": load_json(reaction_records_file(output_dir)),
        "reconsolidation_records": load_json(runtime_dir(output_dir) / "reconsolidation_records.json"),
        "reader_policy": load_json(reader_policy_file(output_dir)),
        "resume_metadata": load_json(resume_metadata_file(output_dir)),
    }
    save_json(full_checkpoint_file(output_dir, "legacy-cp"), legacy_checkpoint)
    shell["last_checkpoint_id"] = "legacy-cp"
    save_runtime_shell(runtime_shell_file(output_dir), shell)

    with pytest.raises(
        RuntimeError,
        match=r"Pre-Phase C\.3 attentional_v2 (runtime state is|checkpoints are) no longer supported",
    ):
        resume_from_checkpoint(output_dir, book_document=book_document, requested_resume_kind="warm_resume")


def test_debug_observability_writes_internal_diagnostics_events(tmp_path: Path):
    """Debug mode should keep shared activity thin while also writing internal diagnostics events."""

    output_dir = tmp_path / "output" / "demo-book"
    AttentionalV2Mechanism().initialize_artifacts(output_dir)
    policy = load_json(reader_policy_file(output_dir))
    policy["logging"]["observability_mode"] = "debug"
    save_json(reader_policy_file(output_dir), policy)

    book_document = _make_book_document(8)
    local_buffer = _build_buffer(total_sentences=8, closed_breaks=[4])
    persist_reading_position(output_dir, chapter_id=1, chapter_ref="Chapter 1", local_buffer=local_buffer)
    write_full_checkpoint(output_dir, checkpoint_id="cp-debug", checkpoint_reason="debug_fixture")
    resume_from_checkpoint(output_dir, book_document=book_document, requested_resume_kind="cold_resume")

    debug_events = [
        json.loads(line)
        for line in event_stream_file(output_dir).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [event["event_type"] for event in debug_events] == ["checkpoint.saved", "resume.restored"]
    assert debug_events[0]["observability_mode"] == "debug"
    assert debug_events[0]["payload"]["state_counts"]["reaction_count"] == 0
    assert debug_events[1]["payload"]["effective_resume_kind"] == "cold_resume"

    shell = load_runtime_shell(runtime_shell_file(output_dir))
    checkpoint_summary = load_json(checkpoint_summary_file(output_dir, "cp-debug"))
    assert shell["observability_mode"] == "debug"
    assert checkpoint_summary["observability_mode"] == "debug"
