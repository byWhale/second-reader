"""Tests for user-level selective note-recall matching."""

from __future__ import annotations

from pathlib import Path

from eval.attentional_v2 import run_user_level_selective_comparison as module


def _note_case(*, source_span_text: str, note_text: str = "note") -> module.NoteCase:
    return module.NoteCase(
        note_case_id="source_a__note_1",
        segment_id="source_a__segment_1",
        source_id="source_a",
        book_title="Book",
        author="Author",
        language_track="en",
        note_id="note_1",
        note_text=note_text,
        note_comment="",
        source_span_text=source_span_text,
        source_sentence_ids=["c1-s1"],
        chapter_id=1,
        chapter_title="Chapter 1",
        section_label="Section 1",
        raw_locator="1",
        provenance={},
    )


def _mechanism_payload(anchor_quote: str, *, content: str = "reaction") -> dict[str, object]:
    return {
        "status": "completed",
        "normalized_eval_bundle": {
            "reactions": [
                {
                    "reaction_id": "r1",
                    "type": "discern",
                    "section_ref": "1.1",
                    "anchor_quote": anchor_quote,
                    "content": content,
                }
            ]
        },
    }


def test_exact_match_counts_for_recall(tmp_path: Path) -> None:
    note_case = _note_case(source_span_text="Alpha hinge line.")
    result = module.evaluate_note_case_for_mechanism(
        note_case=note_case,
        mechanism_payload=_mechanism_payload("Alpha hinge line."),
        mechanism_key="attentional_v2",
        run_root=tmp_path,
        judge_mode="none",
    )

    assert result["label"] == "exact_match"
    assert result["counts_for_recall"] is True
    assert result["judgment"]["confidence"] == "high"


def test_non_exact_cover_does_not_auto_count_for_recall(tmp_path: Path) -> None:
    note_case = _note_case(source_span_text="Alpha hinge line.")
    result = module.evaluate_note_case_for_mechanism(
        note_case=note_case,
        mechanism_payload=_mechanism_payload("Alpha hinge line. Beta elaboration."),
        mechanism_key="attentional_v2",
        run_root=tmp_path,
        judge_mode="none",
    )

    assert result["label"] == "miss"
    assert result["counts_for_recall"] is False
    assert result["judgment"]["reason"] == "judge_disabled"


def test_focused_hit_counts_for_recall_when_judge_says_yes(tmp_path: Path, monkeypatch) -> None:
    note_case = _note_case(source_span_text="Alpha hinge line.")
    monkeypatch.setattr(
        module,
        "_judge_candidate_reaction",
        lambda **_kwargs: {
            "label": "focused_hit",
            "confidence": "high",
            "reason": "The reaction is clearly centered on the highlighted note.",
        },
    )

    result = module.evaluate_note_case_for_mechanism(
        note_case=note_case,
        mechanism_payload=_mechanism_payload("Alpha hinge line. Beta elaboration."),
        mechanism_key="attentional_v2",
        run_root=tmp_path,
        judge_mode="llm",
    )

    assert result["label"] == "focused_hit"
    assert result["counts_for_recall"] is True
    assert result["best_reaction"]["reaction_id"] == "r1"


def test_aggregate_results_counts_exact_and_focused_hits() -> None:
    aggregate = module._aggregate_results(
        note_case_payloads=[
            {
                "source_id": "source_a",
                "language_track": "en",
                "mechanism_results": {
                    "attentional_v2": {"label": "exact_match"},
                    "iterator_v1": {"label": "miss"},
                },
            },
            {
                "source_id": "source_a",
                "language_track": "en",
                "mechanism_results": {
                    "attentional_v2": {"label": "focused_hit"},
                    "iterator_v1": {"label": "incidental_cover"},
                },
            },
        ],
        mechanism_keys=("attentional_v2", "iterator_v1"),
    )

    assert aggregate["mechanisms"]["attentional_v2"]["note_recall"] == 1.0
    assert aggregate["mechanisms"]["attentional_v2"]["exact_match_count"] == 1
    assert aggregate["mechanisms"]["attentional_v2"]["focused_hit_count"] == 1
    assert aggregate["mechanisms"]["iterator_v1"]["note_recall"] == 0.0
    assert aggregate["mechanisms"]["iterator_v1"]["incidental_cover_count"] == 1
    assert aggregate["pairwise_delta"]["note_recall_delta"] == 1.0


def test_run_user_level_selective_comparison_filters_note_cases_to_selected_segments(
    tmp_path: Path, monkeypatch
) -> None:
    segment_a = module.ReadingSegment(
        segment_id="source_a__segment_1",
        source_id="source_a",
        book_title="Book A",
        author="Author",
        language_track="en",
        start_sentence_id="a1",
        end_sentence_id="a9",
        chapter_ids=[1],
        chapter_titles=["Chapter 1"],
        target_note_count=2,
        covered_note_count=2,
        termination_reason="chapter_end_after_target_notes",
        segment_source_path="segment_a.md",
    )
    segment_b = module.ReadingSegment(
        segment_id="source_b__segment_1",
        source_id="source_b",
        book_title="Book B",
        author="Author",
        language_track="en",
        start_sentence_id="b1",
        end_sentence_id="b9",
        chapter_ids=[1],
        chapter_titles=["Chapter 1"],
        target_note_count=2,
        covered_note_count=2,
        termination_reason="chapter_end_after_target_notes",
        segment_source_path="segment_b.md",
    )
    note_a = module.NoteCase(
        note_case_id="source_a__note_1",
        segment_id="source_a__segment_1",
        source_id="source_a",
        book_title="Book A",
        author="Author",
        language_track="en",
        note_id="note_a",
        note_text="note a",
        note_comment="",
        source_span_text="Alpha",
        source_sentence_ids=["a1"],
        chapter_id=1,
        chapter_title="Chapter 1",
        section_label="Section",
        raw_locator="1",
        provenance={},
    )
    note_b = module.NoteCase(
        note_case_id="source_b__note_1",
        segment_id="source_b__segment_1",
        source_id="source_b",
        book_title="Book B",
        author="Author",
        language_track="en",
        note_id="note_b",
        note_text="note b",
        note_comment="",
        source_span_text="Beta",
        source_sentence_ids=["b1"],
        chapter_id=1,
        chapter_title="Chapter 1",
        section_label="Section",
        raw_locator="1",
        provenance={},
    )

    monkeypatch.setattr(module, "_resolve_dataset_dir", lambda _manifest_path: tmp_path)
    monkeypatch.setattr(module, "_load_segments", lambda _dataset_dir: [segment_a, segment_b])
    monkeypatch.setattr(module, "_load_note_cases", lambda _dataset_dir: [note_a, note_b])
    monkeypatch.setattr(
        module,
        "_run_mechanism_for_segment",
        lambda **kwargs: {"status": "completed", "normalized_eval_bundle": {"reactions": []}},
    )
    monkeypatch.setattr(
        module,
        "evaluate_note_case_for_mechanism",
        lambda **kwargs: {
            "status": "completed",
            "label": "miss",
            "counts_for_recall": False,
            "best_reaction": None,
            "judgment": {"label": "miss", "confidence": "high", "reason": "test"},
            "candidate_reactions": [],
        },
    )
    monkeypatch.setattr(module, "write_llm_usage_summary", lambda *args, **kwargs: None)

    aggregate = module.run_user_level_selective_comparison(
        run_id="unit_test_segment_filter",
        manifest_path=tmp_path / "manifest.json",
        mechanism_filter="attentional_v2",
        judge_mode="none",
        segment_ids=["source_a__segment_1"],
    )

    assert aggregate["segment_count"] == 1
    assert aggregate["note_case_count"] == 1
    assert aggregate["mechanisms"]["attentional_v2"]["note_case_count"] == 1
