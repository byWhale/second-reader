"""Tests for attentional_v2 Phase 7 checkpointing and resume helpers."""

from __future__ import annotations

from pathlib import Path

from src.attentional_v2.resume import persist_reading_position, resume_from_checkpoint, write_full_checkpoint
from src.attentional_v2.schemas import build_empty_local_buffer
from src.attentional_v2.state_ops import close_local_meaning_unit, push_local_buffer_sentence
from src.attentional_v2.storage import (
    full_checkpoint_file,
    load_json,
    local_buffer_file,
    reaction_records_file,
    resume_metadata_file,
    save_json,
)
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_runtime.artifacts import checkpoint_summary_file, runtime_shell_file
from src.reading_runtime.shell_state import load_runtime_shell


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
            "mechanism_version": "attentional_v2-phase7",
            "updated_at": "2026-03-23T00:00:00Z",
            "records": [{"reaction_id": "rx-1"}],
        },
    )

    checkpoint = write_full_checkpoint(output_dir, checkpoint_id="cp-1", checkpoint_reason="unit_test")
    assert full_checkpoint_file(output_dir, "cp-1").exists()
    assert checkpoint["visible_reaction_ids"] == ["rx-1"]

    save_json(local_buffer_file(output_dir), build_empty_local_buffer())
    resumed = resume_from_checkpoint(output_dir, book_document=book_document, requested_resume_kind="warm_resume")

    shell = load_runtime_shell(runtime_shell_file(output_dir))
    assert shell["last_checkpoint_id"] == "cp-1"
    assert shell["cursor"]["sentence_id"] == "c1-s6"
    assert resumed["effective_resume_kind"] == "warm_resume"
    assert resumed["resume_window_sentence_ids"] == []
    assert resumed["local_buffer"]["current_sentence_id"] == "c1-s6"
    assert resumed["local_buffer"]["is_reconstructed"] is False
    assert load_json(resume_metadata_file(output_dir))["last_resume_status"] == "warm_restored"
    assert load_json(checkpoint_summary_file(output_dir, "cp-1"))["visible_reaction_ids"] == ["rx-1"]


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
