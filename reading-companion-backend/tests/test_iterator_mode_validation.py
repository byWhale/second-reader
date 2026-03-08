"""Tests for read-mode validation after removing legacy plan mode."""

from __future__ import annotations

from pathlib import Path

import pytest

import main as main_module
from src.iterator_reader import iterator as iterator_module


def test_read_book_rejects_removed_plan_mode(tmp_path, monkeypatch):
    """Programmatic read_book should reject the removed plan mode."""
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
                "id": 1,
                "title": "Chapter 1",
                "chapter_number": 1,
                "status": "pending",
                "level": 1,
                "segments": [],
            }
        ],
    }

    monkeypatch.setattr(
        iterator_module,
        "ensure_structure_for_book",
        lambda *args, **kwargs: (structure, output_dir, False),
    )

    with pytest.raises(ValueError, match='Unsupported read mode: "plan"'):
        iterator_module.read_book(
            book_path=Path("demo.epub"),
            read_mode="plan",  # type: ignore[arg-type]
        )


def test_cli_mode_choices_no_longer_include_plan(capsys):
    """CLI parser should reject --mode plan as an invalid choice."""
    parser = main_module.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["read", "demo.epub", "--mode", "plan"])

    captured = capsys.readouterr()
    assert "invalid choice" in captured.err
    assert "plan" in captured.err
