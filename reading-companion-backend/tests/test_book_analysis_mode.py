"""Tests for the book_analysis orchestration mode."""

from __future__ import annotations

import json
from pathlib import Path

from src.iterator_reader import book_analysis as book_analysis_module
from src.iterator_reader import iterator as iterator_module


def _demo_structure(output_dir: Path) -> dict:
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
            },
            {
                "id": 2,
                "title": "Chapter 2",
                "chapter_number": 2,
                "status": "pending",
                "level": 1,
                "segments": [
                    {
                        "id": "2.1",
                        "summary": "Segment 3",
                        "tokens": 24,
                        "text": "Theta iota",
                        "paragraph_start": 3,
                        "paragraph_end": 3,
                        "status": "pending",
                    },
                    {
                        "id": "2.2",
                        "summary": "Segment 4",
                        "tokens": 26,
                        "text": "Kappa lambda",
                        "paragraph_start": 4,
                        "paragraph_end": 4,
                        "status": "pending",
                    },
                ],
            },
        ],
    }


def test_read_book_book_analysis_mode_writes_report_and_artifacts(tmp_path, monkeypatch):
    """book_analysis mode should emit report plus all key intermediate artifacts."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    structure = _demo_structure(output_dir)

    def fake_invoke_json(_system: str, prompt: str, default: object) -> object:
        if "全书分析助手" in _system:
            segment_id = "1.1"
            for candidate in ["1.1", "1.2", "2.1", "2.2"]:
                if candidate in prompt:
                    segment_id = candidate
                    break
            return {
                "skim_summary": f"Skim {segment_id}",
                "candidate_claims": [f"Claim {segment_id}"],
                "importance_score": 4,
                "controversy_score": 3,
                "evidence_gap_score": 4 if segment_id in {"1.1", "2.1"} else 2,
                "intent_relevance_score": 4,
                "needs_deep_read": True,
                "reason": "high signal",
            }
        if "证据审校助手" in _system:
            return {"queries": ["demo verification query"]}
        return default

    monkeypatch.setattr(book_analysis_module, "invoke_json", fake_invoke_json)
    monkeypatch.setattr(book_analysis_module, "invoke_text", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        book_analysis_module,
        "_search",
        lambda query, max_results=3: [
            {
                "title": "Demo Source",
                "url": "https://example.com/source",
                "snippet": f"snippet for {query}",
                "score": 0.9,
            }
        ],
    )
    monkeypatch.setattr(
        book_analysis_module,
        "run_reader_segment_for_analysis",
        lambda state, progress=None: (
            {
                "segment_id": state.get("segment_id", ""),
                "summary": state.get("segment_summary", ""),
                "verdict": "pass",
                "reactions": [
                    {
                        "type": "highlight",
                        "anchor_quote": "Alpha",
                        "content": "Deep note",
                        "search_results": [],
                    }
                ],
                "reflection_summary": "Looks strong.",
                "reflection_reason_codes": [],
            },
            {"reflection": {"depth": 4}},
        ),
    )
    monkeypatch.setattr(
        iterator_module,
        "ensure_structure_for_book",
        lambda *args, **kwargs: (structure, output_dir, False),
    )

    iterator_module.read_book(
        book_path=Path("demo.epub"),
        read_mode="book_analysis",
    )

    assert (output_dir / "book_analysis.md").exists()
    assert (output_dir / "_analysis" / "analysis_plan.json").exists()
    assert (output_dir / "_analysis" / "segment_skim_cards.jsonl").exists()
    assert (output_dir / "_analysis" / "deep_targets.json").exists()
    assert (output_dir / "_analysis" / "deep_dossiers.json").exists()
    assert (output_dir / "_analysis" / "evidence_checks.jsonl").exists()
    assert (output_dir / "_analysis" / "analysis_trace.jsonl").exists()

    report = (output_dir / "book_analysis.md").read_text(encoding="utf-8")
    assert "# Book Analysis" in report
    assert "## Argument Backbone" in report
    assert "anchors" in report

    skim_lines = [
        line.strip()
        for line in (output_dir / "_analysis" / "segment_skim_cards.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(skim_lines) == 4

    evidence_lines = [
        line.strip()
        for line in (output_dir / "_analysis" / "evidence_checks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert evidence_lines
    first_evidence = json.loads(evidence_lines[0])
    assert first_evidence["hits"][0]["title"] == "Demo Source"
    assert first_evidence["hits"][0]["snippet"] == "snippet for demo verification query"
    assert first_evidence["hits"][0]["url"] == "https://example.com/source"


def test_book_analysis_deep_read_emits_single_line_progress(tmp_path, monkeypatch, capsys):
    """book_analysis deep-read path should print prefixed single-line progress."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    structure = _demo_structure(output_dir)
    structure["chapters"] = [structure["chapters"][0]]
    structure["chapters"][0]["segments"] = [structure["chapters"][0]["segments"][0]]

    def fake_invoke_json(system_prompt: str, _prompt: str, default: object) -> object:
        if "全书分析助手" in system_prompt:
            return {
                "skim_summary": "Skim 1.1",
                "candidate_claims": ["Claim 1.1"],
                "importance_score": 5,
                "controversy_score": 2,
                "evidence_gap_score": 2,
                "intent_relevance_score": 4,
                "needs_deep_read": True,
                "reason": "must deep read",
            }
        return default

    monkeypatch.setattr(book_analysis_module, "invoke_json", fake_invoke_json)
    monkeypatch.setattr(book_analysis_module, "invoke_text", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(book_analysis_module, "_search", lambda query, max_results=3: [])
    def fake_deep_read(state, progress=None):
        if progress:
            progress("💡 好几句都有感触...")
        return (
            {
                "segment_id": state.get("segment_id", ""),
                "summary": state.get("segment_summary", ""),
                "verdict": "pass",
                "reactions": [],
                "reflection_summary": "ok",
                "reflection_reason_codes": [],
            },
            {"reflection": {"depth": 3}},
        )

    monkeypatch.setattr(
        book_analysis_module,
        "run_reader_segment_for_analysis",
        fake_deep_read,
    )
    monkeypatch.setattr(
        iterator_module,
        "ensure_structure_for_book",
        lambda *args, **kwargs: (structure, output_dir, False),
    )

    iterator_module.read_book(
        book_path=Path("demo.epub"),
        read_mode="book_analysis",
        analysis_policy={
            "deep_target_ratio": 1.0,
            "min_deep_per_chapter": 1,
            "max_core_claims": 20,
            "max_web_queries": 0,
            "max_queries_per_claim": 2,
            "reuse_existing_notes": False,
        },
    )

    captured = capsys.readouterr().out
    assert "[book_analysis][1.1]" in captured
    assert "💡 好几句都有感触..." in captured


def test_book_analysis_reuses_existing_notes_when_enabled(tmp_path, monkeypatch):
    """If existing section notes are available, deep read should be reused."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    structure = _demo_structure(output_dir)
    structure["chapters"] = [structure["chapters"][0]]
    structure["chapters"][0]["segments"] = [structure["chapters"][0]["segments"][0]]
    structure["chapters"][0]["output_file"] = "ch01_deep_read.md"
    (output_dir / "ch01_deep_read.md").write_text(
        """# Chapter 1

## Section 1.1: Segment 1

💡 Highlight

> "Alpha"

This is an existing deep-read note with enough context to be reused.

---
""",
        encoding="utf-8",
    )

    def fake_invoke_json(system_prompt: str, prompt: str, default: object) -> object:
        if "全书分析助手" in system_prompt:
            return {
                "skim_summary": "Skim 1.1",
                "candidate_claims": ["Claim 1.1"],
                "importance_score": 5,
                "controversy_score": 2,
                "evidence_gap_score": 2,
                "intent_relevance_score": 4,
                "needs_deep_read": True,
                "reason": "must deep read",
            }
        return default

    monkeypatch.setattr(book_analysis_module, "invoke_json", fake_invoke_json)
    monkeypatch.setattr(book_analysis_module, "invoke_text", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        book_analysis_module,
        "_search",
        lambda query, max_results=3: [],
    )
    monkeypatch.setattr(
        book_analysis_module,
        "run_reader_segment_for_analysis",
        lambda state, progress=None: (_ for _ in ()).throw(RuntimeError("should not be called")),
    )
    monkeypatch.setattr(
        iterator_module,
        "ensure_structure_for_book",
        lambda *args, **kwargs: (structure, output_dir, False),
    )

    iterator_module.read_book(
        book_path=Path("demo.epub"),
        read_mode="book_analysis",
    )

    dossiers = json.loads((output_dir / "_analysis" / "deep_dossiers.json").read_text(encoding="utf-8"))
    assert dossiers["dossiers"][0]["reused"] is True
    assert "evidence_excerpt" not in dossiers["dossiers"][0]
    assert dossiers["dossiers"][0]["evidence_anchor"] == "1.1"
    assert dossiers["dossiers"][0]["source_links"] == []


def test_search_filters_low_quality_domains_and_prefers_high_trust(monkeypatch):
    """Search filtering should block low-quality domains and prefer high-trust sources."""

    class _FakeSearchTool:
        @staticmethod
        def invoke(_payload: dict) -> list[dict]:
            return [
                {
                    "title": "Forum opinion",
                    "url": "https://topic.reddit.com/thread",
                    "content": "noise",
                    "score": 0.99,
                },
                {
                    "title": "Personal blog",
                    "url": "https://amberbobamber.medium.com/post",
                    "content": "opinion",
                    "score": 0.95,
                },
                {
                    "title": "Journal result",
                    "url": "https://www.sciencedirect.com/science/article/pii/S0191886910003429",
                    "content": "study",
                    "score": 0.71,
                },
                {
                    "title": "Reference background",
                    "url": "https://en.wikipedia.org/wiki/Price_discovery",
                    "content": "encyclopedia",
                    "score": 0.69,
                },
                {
                    "title": "Generic site",
                    "url": "https://example.com/context",
                    "content": "neutral",
                    "score": 0.92,
                },
            ]

    monkeypatch.setattr(book_analysis_module, "search_web", _FakeSearchTool())

    hits = book_analysis_module._search("demo claim", max_results=2)
    urls = [item["url"] for item in hits]

    assert len(hits) == 2
    assert any("sciencedirect.com" in url for url in urls)
    assert any("wikipedia.org" in url for url in urls)
    assert all("reddit.com" not in url for url in urls)
    assert all("medium.com" not in url for url in urls)


def test_deep_targets_prioritize_segments_marked_for_deep_read(tmp_path, monkeypatch):
    """Segments marked needs_deep_read=true should outrank higher-scoring false positives."""
    output_dir = tmp_path / "output" / "demo-book"
    output_dir.mkdir(parents=True, exist_ok=True)
    structure = _demo_structure(output_dir)
    structure["chapters"] = [structure["chapters"][0]]
    structure["chapters"][0]["segments"] = [
        {
            "id": "1.1",
            "summary": "High score but skip",
            "tokens": 20,
            "text": "A",
            "paragraph_start": 1,
            "paragraph_end": 1,
            "status": "pending",
        },
        {
            "id": "1.2",
            "summary": "Deep target 1",
            "tokens": 20,
            "text": "B",
            "paragraph_start": 2,
            "paragraph_end": 2,
            "status": "pending",
        },
        {
            "id": "1.3",
            "summary": "Deep target 2",
            "tokens": 20,
            "text": "C",
            "paragraph_start": 3,
            "paragraph_end": 3,
            "status": "pending",
        },
    ]

    def fake_invoke_json(system_prompt: str, prompt: str, default: object) -> object:
        if "全书分析助手" in system_prompt:
            if "1.1" in prompt:
                return {
                    "skim_summary": "segment 1.1",
                    "candidate_claims": ["Claim 1.1"],
                    "importance_score": 5,
                    "controversy_score": 2,
                    "evidence_gap_score": 2,
                    "intent_relevance_score": 5,
                    "needs_deep_read": False,
                    "reason": "not worth deep read",
                }
            if "1.2" in prompt:
                return {
                    "skim_summary": "segment 1.2",
                    "candidate_claims": ["Claim 1.2"],
                    "importance_score": 4,
                    "controversy_score": 2,
                    "evidence_gap_score": 2,
                    "intent_relevance_score": 4,
                    "needs_deep_read": True,
                    "reason": "high-value thread",
                }
            return {
                "skim_summary": "segment 1.3",
                "candidate_claims": ["Claim 1.3"],
                "importance_score": 3,
                "controversy_score": 2,
                "evidence_gap_score": 2,
                "intent_relevance_score": 4,
                "needs_deep_read": True,
                "reason": "supporting evidence",
            }
        return default

    monkeypatch.setattr(book_analysis_module, "invoke_json", fake_invoke_json)
    monkeypatch.setattr(book_analysis_module, "invoke_text", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(book_analysis_module, "_search", lambda query, max_results=3: [])
    monkeypatch.setattr(
        book_analysis_module,
        "run_reader_segment_for_analysis",
        lambda state, progress=None: (
            {
                "segment_id": state.get("segment_id", ""),
                "summary": state.get("segment_summary", ""),
                "verdict": "pass",
                "reactions": [],
                "reflection_summary": "ok",
                "reflection_reason_codes": [],
            },
            {"reflection": {"depth": 3}},
        ),
    )
    monkeypatch.setattr(
        iterator_module,
        "ensure_structure_for_book",
        lambda *args, **kwargs: (structure, output_dir, False),
    )

    iterator_module.read_book(
        book_path=Path("demo.epub"),
        read_mode="book_analysis",
        analysis_policy={
            "deep_target_ratio": 0.5,
            "min_deep_per_chapter": 1,
            "max_core_claims": 20,
            "max_web_queries": 0,
            "max_queries_per_claim": 2,
            "reuse_existing_notes": False,
        },
    )

    deep_targets = json.loads((output_dir / "_analysis" / "deep_targets.json").read_text(encoding="utf-8"))
    selected_ids = {item["segment_id"] for item in deep_targets["targets"]}
    assert selected_ids == {"1.2", "1.3"}
