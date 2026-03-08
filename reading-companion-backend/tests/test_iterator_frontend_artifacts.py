"""Tests for sequential frontend artifact generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.iterator_reader import iterator as iterator_module
from src.iterator_reader import parse as parse_module
from src.iterator_reader.frontend_artifacts import estimate_eta_seconds
from src.iterator_reader.storage import (
    activity_file,
    book_manifest_file,
    chapter_markdown_file,
    chapter_result_file,
    run_state_file,
)


def _structure(output_dir: Path) -> dict:
    return {
        "book": "Demo Book",
        "author": "Tester",
        "book_language": "en",
        "output_language": "en",
        "source_file": "demo.epub",
        "output_dir": str(output_dir),
        "chapters": [
            {
                "id": 1,
                "title": "Chapter 1",
                "chapter_number": 1,
                "status": "pending",
                "level": 1,
                "segments": [
                    {
                        "id": "1.1",
                        "segment_ref": "1.1",
                        "summary": "Segment 1",
                        "tokens": 20,
                        "text": "Alpha beta",
                        "paragraph_start": 1,
                        "paragraph_end": 1,
                        "status": "pending",
                        "locator": {
                            "href": "chapter-1.xhtml",
                            "start_cfi": "epubcfi(/6/2!/4/2)",
                            "end_cfi": "epubcfi(/6/2!/4/2)",
                            "paragraph_start": 1,
                            "paragraph_end": 1,
                        },
                        "paragraph_locators": [
                            {
                                "href": "chapter-1.xhtml",
                                "start_cfi": "epubcfi(/6/2!/4/2)",
                                "end_cfi": "epubcfi(/6/2!/4/2)",
                                "paragraph_index": 1,
                                "text": "Alpha beta",
                            }
                        ],
                    },
                    {
                        "id": "1.2",
                        "segment_ref": "1.2",
                        "summary": "Segment 2",
                        "tokens": 22,
                        "text": "Gamma delta",
                        "paragraph_start": 2,
                        "paragraph_end": 2,
                        "status": "pending",
                        "locator": {
                            "href": "chapter-1.xhtml",
                            "start_cfi": "epubcfi(/6/2!/4/4)",
                            "end_cfi": "epubcfi(/6/2!/4/4)",
                            "paragraph_start": 2,
                            "paragraph_end": 2,
                        },
                        "paragraph_locators": [
                            {
                                "href": "chapter-1.xhtml",
                                "start_cfi": "epubcfi(/6/2!/4/4)",
                                "end_cfi": "epubcfi(/6/2!/4/4)",
                                "paragraph_index": 2,
                                "text": "Gamma delta",
                            }
                        ],
                    },
                ],
            }
        ],
    }


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_parse_book_writes_frontend_bootstrap_artifacts(tmp_path, monkeypatch):
    """Parse stage should bootstrap manifest, ready state, and activity stream."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    structure = _structure(output_dir)

    monkeypatch.setattr(
        parse_module,
        "build_structure",
        lambda *args, **kwargs: (structure, output_dir),
    )

    parse_module.parse_book(Path("demo.epub"))

    manifest = _load_json(book_manifest_file(output_dir))
    run_state = _load_json(run_state_file(output_dir))
    activity = _load_jsonl(activity_file(output_dir))

    assert manifest["book"] == "Demo Book"
    assert manifest["book_id"] == "demo-book"
    assert manifest["source_asset"] == {"format": "epub", "file": "_assets/source.epub"}
    assert manifest["cover_image_url"] is None
    assert manifest["chapters"][0]["markdown_file"] == "ch01_deep_read.md"
    assert manifest["chapters"][0]["result_file"] == "ch01_deep_read.json"
    assert manifest["chapters"][0]["visible_reaction_count"] == 0
    assert run_state["stage"] == "ready"
    assert run_state["mode"] == "sequential"
    assert run_state["total_chapters"] == 1
    assert activity[-1]["type"] == "structure_ready"


def test_read_book_sequential_writes_frontend_artifacts(tmp_path, monkeypatch):
    """Sequential read should persist companion JSON, manifest, run state, and activity."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    structure = _structure(output_dir)

    monkeypatch.setattr(
        iterator_module,
        "ensure_structure_for_book",
        lambda *args, **kwargs: (structure, output_dir, False),
    )
    monkeypatch.setattr(
        iterator_module,
        "render_chapter_markdown",
        lambda chapter, segments, output_language, chapter_reflection=None: "# Chapter 1\n\nok\n",
    )
    monkeypatch.setattr(
        iterator_module,
        "run_chapter_reflection",
        lambda **kwargs: {
            "segment_repairs": [],
            "reaction_repairs": [],
            "chapter_insights": ["Arc"],
            "segment_quality_flags": [],
        },
    )
    monkeypatch.setattr(
        iterator_module,
        "apply_chapter_reflection_repairs",
        lambda segments, chapter_reflection, output_language: segments,
    )

    def fake_run_reader_segment(state, progress=None):
        if progress:
            progress("💡 先记下这句...")
        if state.get("segment_id") == "1.1":
            rendered = {
                "segment_id": "1.1",
                "segment_ref": "1.1",
                "summary": "Segment 1",
                "verdict": "pass",
                "reactions": [
                    {
                        "type": "highlight",
                        "anchor_quote": "Alpha",
                        "content": "Looks important.",
                        "search_results": [],
                    },
                    {
                        "type": "silent",
                        "content": "ignore me",
                        "search_results": [],
                    },
                    {
                        "type": "curious",
                        "anchor_quote": "Alpha",
                        "content": "Need more evidence.",
                        "search_query": "alpha evidence",
                        "search_results": [],
                    },
                ],
                "reflection_summary": "Looks strong.",
                "reflection_reason_codes": [],
                "quality_status": "strong",
            }
        else:
            rendered = {
                "segment_id": "1.2",
                "segment_ref": "1.2",
                "summary": "Segment 2",
                "verdict": "skip",
                "reactions": [],
                "reflection_summary": "Skip.",
                "reflection_reason_codes": ["LOW_SELECTIVITY"],
                "quality_status": "skipped",
                "skip_reason": "low_selectivity",
            }
        return rendered, {"budget": {"search_queries_remaining_in_chapter": 11}}

    monkeypatch.setattr(iterator_module, "run_reader_segment", fake_run_reader_segment)

    iterator_module.read_book(book_path=Path("demo.epub"), read_mode="sequential")

    chapter_result = _load_json(chapter_result_file(output_dir, structure["chapters"][0]))
    manifest = _load_json(book_manifest_file(output_dir))
    run_state = _load_json(run_state_file(output_dir))
    activity = _load_jsonl(activity_file(output_dir))
    markdown_path = chapter_markdown_file(output_dir, structure["chapters"][0])

    assert chapter_result["sections"][0]["segment_ref"] == "1.1"
    assert chapter_result["sections"][0]["original_text"] == "Alpha beta"
    assert chapter_result["sections"][0]["locator"]["href"] == "chapter-1.xhtml"
    assert chapter_result["chapter_reflection"]["chapter_insights"] == ["Arc"]
    assert all(reaction["type"] != "silent" for reaction in chapter_result["sections"][0]["reactions"])
    assert chapter_result["sections"][0]["reactions"][0]["reaction_id"]
    assert chapter_result["sections"][0]["reactions"][0]["target_locator"]["match_mode"] == "exact"
    assert chapter_result["sections"][1]["verdict"] == "skip"
    assert chapter_result["featured_reactions"]
    assert len(chapter_result["featured_reactions"]) <= 3
    assert chapter_result["visible_reaction_count"] == 2
    assert chapter_result["reaction_type_diversity"] == 2
    assert chapter_result["high_signal_reaction_count"] == 2
    assert chapter_result["ui_summary"]["kept_section_count"] == 1
    assert chapter_result["ui_summary"]["skipped_section_count"] == 1
    assert chapter_result["ui_summary"]["reaction_counts"] == {"curious": 1, "highlight": 1}
    assert manifest["chapters"][0]["status"] == "done"
    assert manifest["chapters"][0]["visible_reaction_count"] == 2
    assert manifest["chapters"][0]["reaction_type_diversity"] == 2
    assert manifest["chapters"][0]["high_signal_reaction_count"] == 2
    assert markdown_path.exists()
    assert run_state["stage"] == "completed"
    assert run_state["eta_seconds"] == 0
    assert {"structure_ready", "chapter_started", "segment_started", "segment_completed", "chapter_completed", "run_completed"} <= {
        item["type"] for item in activity
    }
    assert all(item.get("event_id") for item in activity)


def test_read_book_sequential_records_error_state(tmp_path, monkeypatch):
    """Sequential failures should surface through run_state and activity without swallowing the exception."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    structure = _structure(output_dir)

    monkeypatch.setattr(
        iterator_module,
        "ensure_structure_for_book",
        lambda *args, **kwargs: (structure, output_dir, False),
    )
    monkeypatch.setattr(
        iterator_module,
        "run_reader_segment",
        lambda state, progress=None: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="boom"):
        iterator_module.read_book(book_path=Path("demo.epub"), read_mode="sequential")

    run_state = _load_json(run_state_file(output_dir))
    activity = _load_jsonl(activity_file(output_dir))

    assert run_state["stage"] == "error"
    assert run_state["error"] == "boom"
    assert activity[-1]["type"] == "error"


def test_estimate_eta_seconds_stays_null_until_one_chapter_finishes():
    """ETA should remain null until there is at least one completed chapter."""
    assert estimate_eta_seconds([], 3) is None
    eta = estimate_eta_seconds([30.0], 2, current_total_segments=4, current_completed_segments=1)
    assert isinstance(eta, int)
    assert eta > 0
