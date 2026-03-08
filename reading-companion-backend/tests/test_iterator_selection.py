"""Tests for chapter selection and output naming."""

from __future__ import annotations

from src.iterator_reader.iterator import _chapter_selection
from src.iterator_reader.storage import chapter_output_name, display_segment_id, segment_reference


def test_chapter_selection_prefers_human_chapter_number():
    """--chapter N should resolve to the visible chapter number, not internal id."""
    structure = {
        "chapters": [
            {"id": 10, "title": "Chapter 4", "chapter_number": 4, "status": "pending", "level": 1, "segments": []},
            {"id": 16, "title": "Chapter 10", "chapter_number": 10, "status": "pending", "level": 1, "segments": []},
        ]
    }

    selected = _chapter_selection(structure, chapter_number=10, continue_mode=False)

    assert len(selected) == 1
    assert selected[0]["title"] == "Chapter 10"


def test_chapter_output_name_uses_human_chapter_number():
    """Numbered chapters should write to filenames users expect."""
    chapter = {
        "id": 16,
        "title": "Chapter 10",
        "chapter_number": 10,
        "status": "pending",
        "level": 1,
        "segments": [],
    }

    assert chapter_output_name(chapter) == "ch10_deep_read.md"


def test_display_segment_id_uses_human_chapter_number():
    """Rendered segment ids should match the visible chapter number."""
    chapter = {
        "id": 16,
        "title": "Chapter 10",
        "chapter_number": 10,
        "status": "pending",
        "level": 1,
        "segments": [],
    }

    assert display_segment_id(chapter, "16.3") == "10.3"


def test_display_segment_id_hides_internal_prefix_for_non_numbered_sections():
    """Non-numbered chapters should use title prefix anchors instead of raw internal ids."""
    chapter = {
        "id": 6,
        "title": "Prologue",
        "status": "pending",
        "level": 1,
        "segments": [],
    }

    assert display_segment_id(chapter, "6.1") == "Prologue.1"


def test_segment_reference_falls_back_to_part_prefix_when_title_missing():
    """Missing titles should still get stable visible anchors."""
    chapter = {
        "id": 6,
        "title": "",
        "status": "pending",
        "level": 1,
        "segments": [],
    }

    assert segment_reference(chapter, "6.1") == "Part6.1"
