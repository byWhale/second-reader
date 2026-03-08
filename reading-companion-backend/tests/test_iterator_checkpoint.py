"""Tests for segment-level checkpoint recovery."""

from __future__ import annotations

import json
from pathlib import Path

from src.iterator_reader import iterator as iterator_module
from src.iterator_reader.storage import (
    activity_file,
    run_state_file,
    segment_checkpoint_file,
    structure_file,
)


def _rendered(segment_id: str, summary: str) -> dict:
    return {
        "segment_id": segment_id,
        "summary": summary,
        "verdict": "pass",
        "reactions": [
            {
                "type": "highlight",
                "anchor_quote": "Alpha",
                "content": "Looks important.",
                "search_results": [],
            }
        ],
        "reflection_summary": "Looks strong.",
        "reflection_reason_codes": [],
    }


def test_segment_checkpoint_resumes_remaining_segments(tmp_path, monkeypatch, capsys):
    """--continue should resume from unfinished segments inside an in-progress chapter."""
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
                "segments": [
                    {
                        "id": "1.1",
                        "summary": "Segment 1",
                        "tokens": 20,
                        "text": "Alpha beta",
                        "paragraph_start": 1,
                        "paragraph_end": 1,
                        "status": "pending",
                    },
                    {
                        "id": "1.2",
                        "summary": "Segment 2",
                        "tokens": 22,
                        "text": "Gamma delta",
                        "paragraph_start": 2,
                        "paragraph_end": 2,
                        "status": "pending",
                    },
                ],
            }
        ],
    }

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

    def fail_on_second_segment(state, progress=None):
        if state.get("segment_id") == "1.2":
            raise RuntimeError("boom")
        return _rendered("1.1", "Segment 1"), {"reflection": {"selectivity": 4, "association_quality": 4, "attribution_reasonableness": 4, "text_connection": 4, "depth": 4}, "budget": {"search_queries_remaining_in_chapter": 11}}

    monkeypatch.setattr(iterator_module, "run_reader_segment", fail_on_second_segment)

    try:
        iterator_module.read_book(book_path=Path("demo.epub"), continue_mode=False)
    except RuntimeError:
        pass

    checkpoint_path = segment_checkpoint_file(output_dir, structure["chapters"][0])
    assert checkpoint_path.exists()
    saved = json.loads(structure_file(output_dir).read_text(encoding="utf-8"))
    assert saved["chapters"][0]["status"] == "in_progress"
    assert saved["chapters"][0]["segments"][0]["status"] == "done"

    calls: list[str] = []

    def resume_only_pending(state, progress=None):
        calls.append(state.get("segment_id", ""))
        if progress:
            progress("⚡ 这里有个隐含前提...")
        return _rendered(state.get("segment_id", ""), state.get("segment_summary", "")), {"reflection": {"selectivity": 4, "association_quality": 4, "attribution_reasonableness": 4, "text_connection": 4, "depth": 4}, "budget": {"search_queries_remaining_in_chapter": 10}}

    monkeypatch.setattr(iterator_module, "run_reader_segment", resume_only_pending)
    iterator_module.read_book(book_path=Path("demo.epub"), continue_mode=True)

    captured = capsys.readouterr().out
    assert "检测到段级 checkpoint，恢复 1 个语义单元" in captured
    assert "checkpoint 恢复后继续从 1.2 开始处理" in captured
    assert "⚡ 这里有个隐含前提..." in captured

    assert calls == ["1.2"]
    assert not checkpoint_path.exists()
    saved_after = json.loads(structure_file(output_dir).read_text(encoding="utf-8"))
    run_state = json.loads(run_state_file(output_dir).read_text(encoding="utf-8"))
    activity = [
        json.loads(line)
        for line in activity_file(output_dir).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert saved_after["chapters"][0]["status"] == "done"
    assert saved_after["chapters"][0]["segments"][1]["status"] == "done"
    assert run_state["stage"] == "completed"
    assert "segment_started" in {item["type"] for item in activity}
    assert "chapter_completed" in {item["type"] for item in activity}
