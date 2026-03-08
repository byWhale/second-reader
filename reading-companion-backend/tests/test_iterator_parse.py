"""Tests for parse-stage structure generation."""

from __future__ import annotations

import json

from src.iterator_reader import parse as parse_module


def test_build_structure_persists_semantic_segments(tmp_path, monkeypatch):
    """build_structure should write structure.json with semantic segments."""
    book_path = tmp_path / "demo.epub"
    book_path.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(parse_module, "extract_book_metadata", lambda _: ("Demo Book", "Tester"))
    monkeypatch.setattr(parse_module, "detect_book_language", lambda *_args, **_kwargs: "en")
    monkeypatch.setattr(
        parse_module,
        "parse_ebook",
        lambda _: [
            {
                "title": "Chapter One",
                "content": "<p>Alpha</p><p>Beta</p>",
                "level": 1,
                "start_page": None,
                "end_page": None,
            }
        ],
    )
    monkeypatch.setattr(
        parse_module,
        "segment_chapter_semantically",
        lambda *args, **kwargs: [
            {
                "id": "1.1",
                "summary": "作者提出第一个判断",
                "tokens": 12,
                "text": kwargs["chapter_text"],
                "paragraph_start": 1,
                "paragraph_end": 1,
                "status": "pending",
            }
        ],
    )
    monkeypatch.setattr(
        parse_module,
        "resolve_output_dir",
        lambda *_args, **_kwargs: tmp_path / "output" / "demo-book",
    )

    structure, output_dir = parse_module.build_structure(book_path, language_mode="auto")

    assert structure["book"] == "Demo Book"
    assert structure["author"] == "Tester"
    assert structure["book_language"] == "en"
    assert structure["output_language"] == "en"
    assert structure["chapters"][0]["segments"][0]["summary"] == "作者提出第一个判断"

    saved = json.loads((output_dir / "structure.json").read_text(encoding="utf-8"))
    assert saved["chapters"][0]["status"] == "pending"
    assert saved["chapters"][0]["segments"][0]["id"] == "1.1"
    assert saved["chapters"][0]["segments"][0]["segment_ref"] == "Chapter_One.1"
    assert "locator" not in saved["chapters"][0]["segments"][0]
    assert saved["chapters"][0]["segments"][0]["paragraph_locators"][0]["start_cfi"] is None
    assert "Alpha" in saved["chapters"][0]["segments"][0]["paragraph_locators"][0]["text"]
    assert (output_dir / "_assets" / "source.epub").exists()

    structure_md = (output_dir / "structure.md").read_text(encoding="utf-8")
    assert "# Structure Overview: Demo Book" in structure_md
    assert "## Chapter One" in structure_md
    assert "### Section 1: 作者提出第一个判断" in structure_md


def test_build_structure_infers_human_chapter_number(tmp_path, monkeypatch):
    """Numeric chapter titles should get a human-facing chapter number."""
    book_path = tmp_path / "demo.epub"
    book_path.write_text("placeholder", encoding="utf-8")

    monkeypatch.setattr(parse_module, "extract_book_metadata", lambda _: ("Demo Book", "Tester"))
    monkeypatch.setattr(parse_module, "detect_book_language", lambda *_args, **_kwargs: "en")
    monkeypatch.setattr(
        parse_module,
        "parse_ebook",
        lambda _: [
            {
                "title": "Chapter 10",
                "content": "<p>Alpha</p><p>Beta</p>",
                "level": 1,
                "start_page": None,
                "end_page": None,
            }
        ],
    )
    monkeypatch.setattr(
        parse_module,
        "segment_chapter_semantically",
        lambda *args, **kwargs: [
            {
                "id": "1.1",
                "summary": "A segment",
                "tokens": 12,
                "text": kwargs["chapter_text"],
                "paragraph_start": 1,
                "paragraph_end": 1,
                "status": "pending",
            }
        ],
    )
    monkeypatch.setattr(
        parse_module,
        "resolve_output_dir",
        lambda *_args, **_kwargs: tmp_path / "output" / "demo-book",
    )

    structure, _output_dir = parse_module.build_structure(book_path, language_mode="auto")

    assert structure["chapters"][0]["chapter_number"] == 10
    assert structure["chapters"][0]["segments"][0]["segment_ref"] == "10.1"


def test_upgrade_structure_metadata_backfills_segment_ref(tmp_path):
    """Legacy structures without segment_ref should be upgraded in-place."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    structure = {
        "book": "Demo Book",
        "author": "Tester",
        "book_language": "en",
        "output_language": "en",
        "source_file": "demo.epub",
        "output_dir": str(output_dir),
        "chapters": [
            {
                "id": 6,
                "title": "Prologue",
                "status": "pending",
                "level": 1,
                "segments": [
                    {
                        "id": "6.1",
                        "summary": "A segment",
                        "tokens": 10,
                        "text": "Alpha",
                        "paragraph_start": 1,
                        "paragraph_end": 1,
                        "status": "pending",
                    }
                ],
            }
        ],
    }

    changed = parse_module._upgrade_structure_metadata(structure, output_dir)

    assert changed is True
    assert structure["chapters"][0]["segments"][0]["segment_ref"] == "Prologue.1"
    assert structure["chapters"][0]["segments"][0]["paragraph_locators"] == []
