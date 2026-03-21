"""Tests for the backend reading-mechanism scaffold."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import main as main_module
from src.iterator_reader.storage import activity_file, chapter_result_file, reader_memory_file, run_state_file, save_json
from src.reading_core.runtime_contracts import ReadRequest
from src.reading_core.storage import save_book_document
from src.reading_mechanisms import iterator_v1 as iterator_v1_module
from src.reading_mechanisms.iterator_v1 import IteratorV1Mechanism
from src.reading_runtime import available_mechanism_keys, default_mechanism_key, get_mechanism


def test_default_mechanism_registration_exposes_iterator_v1():
    """The scaffold should register the current iterator reader as the default."""

    assert "iterator_v1" in available_mechanism_keys()
    assert default_mechanism_key() == "iterator_v1"
    assert get_mechanism().key == "iterator_v1"
    assert get_mechanism("iterator_v1").label


def test_cli_mechanism_defaults_to_registered_default():
    """CLI parsing should expose the default mechanism without requiring a flag."""

    parser = main_module.build_parser()
    args = parser.parse_args(["read", "demo.epub"])

    assert args.mechanism == default_mechanism_key()


def test_cli_rejects_unknown_mechanism(capsys):
    """CLI parser should reject mechanisms that are not in the runtime registry."""

    parser = main_module.build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["read", "demo.epub", "--mechanism", "unknown_v9"])

    captured = capsys.readouterr()
    assert "invalid choice" in captured.err
    assert "unknown_v9" in captured.err


def test_shared_modules_do_not_import_iterator_reader_models_directly():
    """Shared runtime/library/search modules should depend on reading_core, not iterator models."""

    backend_root = Path(main_module.__file__).resolve().parent
    candidate_files = [
        backend_root / "src" / "reading_runtime" / "__init__.py",
        backend_root / "src" / "reading_runtime" / "mechanisms.py",
        backend_root / "src" / "library" / "models.py",
        backend_root / "src" / "library" / "user_marks.py",
        backend_root / "src" / "tools" / "search.py",
    ]

    for path in candidate_files:
        assert "src.iterator_reader.models" not in path.read_text(encoding="utf-8"), path


def test_iterator_v1_read_result_includes_normalized_eval_bundle(tmp_path, monkeypatch):
    """The iterator adapter should emit a normalized eval bundle from persisted artifacts."""

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
                "status": "done",
                "level": 1,
                "segments": [
                    {
                        "id": "1.1",
                        "segment_ref": "1.1",
                        "summary": "Opening move",
                        "tokens": 12,
                        "text": "Alpha",
                        "paragraph_start": 1,
                        "paragraph_end": 1,
                        "status": "done",
                    }
                ],
            }
        ],
    }
    save_book_document(
        output_dir / "public" / "book_document.json",
        {
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
                    "paragraphs": [
                        {
                            "paragraph_index": 1,
                            "text": "Alpha",
                            "block_tag": "p",
                            "heading_level": None,
                            "text_role": "body",
                        }
                    ],
                }
            ],
        },
    )
    save_json(
        run_state_file(output_dir),
        {
            "stage": "completed",
            "current_chapter_ref": "Chapter 1",
            "current_segment_ref": "1.1",
            "current_reading_activity": {"phase": "reflecting"},
            "resume_available": True,
            "last_checkpoint_at": "2026-03-21T00:00:00Z",
            "completed_chapters": 1,
            "total_chapters": 1,
        },
    )
    activity_path = activity_file(output_dir)
    activity_path.parent.mkdir(parents=True, exist_ok=True)
    activity_path.write_text(
        json.dumps(
            {
                "event_id": "evt-1",
                "timestamp": "2026-03-21T00:00:01Z",
                "stream": "mindstream",
                "kind": "thought",
                "message": "noticed a hinge sentence",
                "chapter_ref": "Chapter 1",
                "segment_ref": "1.1",
                "anchor_quote": "Alpha",
                "phase": "thinking",
                "thought_family": "discern",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    save_json(
        reader_memory_file(output_dir),
        {
            "book_arc_summary": "The book keeps returning to exchange and value.",
            "chapter_memory_summaries": [{"summary": "Chapter 1 frames the opening tension."}],
        },
    )
    save_json(
        chapter_result_file(output_dir, structure["chapters"][0]),
        {
            "book_title": "Demo Book",
            "chapter": {"id": 1, "reference": "Chapter 1"},
            "sections": [
                {
                    "segment_ref": "1.1",
                    "reactions": [
                        {
                            "reaction_id": "r-1",
                            "type": "highlight",
                            "anchor_quote": "Alpha",
                            "content": "This lands as the chapter's threshold line.",
                            "search_query": "",
                            "search_results": [],
                        }
                    ],
                }
            ],
            "featured_reactions": [{"reaction_id": "r-1"}],
            "ui_summary": {"kept_section_count": 1},
            "chapter_reflection": {"summary": "The chapter opens by defining its central pressure."},
        },
    )

    monkeypatch.setattr(
        iterator_v1_module,
        "iterator_read_book",
        lambda *args, **kwargs: (structure, output_dir, False),
    )

    result = IteratorV1Mechanism().read_book(
        ReadRequest(
            book_path=Path("demo.epub"),
            mechanism_key="iterator_v1",
            mechanism_config={},
        )
    )

    assert result.normalized_eval_bundle is not None
    assert result.normalized_eval_bundle["mechanism_key"] == "iterator_v1"
    assert result.normalized_eval_bundle["run_snapshot"]["current_section_ref"] == "1.1"
    assert result.normalized_eval_bundle["attention_events"][0]["event_id"] == "evt-1"
    assert result.normalized_eval_bundle["reactions"][0]["reaction_id"] == "r-1"
    assert result.normalized_eval_bundle["memory_summaries"]
