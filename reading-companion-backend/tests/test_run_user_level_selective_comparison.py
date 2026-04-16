"""Tests for user-level selective note-recall matching."""

from __future__ import annotations

from pathlib import Path

from eval.attentional_v2 import run_user_level_selective_comparison as module


def _slice(*, start: int = 0, end: int = 17, paragraph_index: int = 1, text: str = "Alpha hinge line.") -> dict[str, object]:
    return {
        "coordinate_system": "segment_source_v1",
        "segment_id": "source_a__segment_1",
        "source_id": "source_a",
        "paragraph_index": paragraph_index,
        "char_start": start,
        "char_end": end,
        "text": text,
    }


def _note_case(*, source_span_text: str, note_text: str = "note", span: dict[str, object] | None = None) -> module.NoteCase:
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
        source_span_coordinate_system="segment_source_v1",
        source_span_slices=[dict(span or _slice(text=source_span_text, end=len(source_span_text)))],
        chapter_id=1,
        chapter_title="Chapter 1",
        section_label="Section 1",
        raw_locator="1",
        provenance={},
    )


def _mechanism_payload(
    anchor_quote: str,
    *,
    content: str = "reaction",
    locator: dict[str, object] | None = None,
) -> dict[str, object]:
    target_locator = locator if locator is not None else {"paragraph_index": 1, "char_start": 0, "char_end": len(anchor_quote)}
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
                    "target_locator": target_locator,
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
        mechanism_payload=_mechanism_payload(
            "Alpha hinge line. Beta elaboration.",
            locator={"paragraph_index": 1, "char_start": 0, "char_end": 35},
        ),
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
        mechanism_payload=_mechanism_payload(
            "Alpha hinge line. Beta elaboration.",
            locator={"paragraph_index": 1, "char_start": 0, "char_end": 35},
        ),
        mechanism_key="attentional_v2",
        run_root=tmp_path,
        judge_mode="llm",
    )

    assert result["label"] == "focused_hit"
    assert result["counts_for_recall"] is True
    assert result["best_reaction"]["reaction_id"] == "r1"


def test_target_locator_source_span_slices_take_priority(tmp_path: Path) -> None:
    note_case = _note_case(source_span_text="Alpha hinge line.")
    result = module.evaluate_note_case_for_mechanism(
        note_case=note_case,
        mechanism_payload=_mechanism_payload(
            "different visible quote",
            locator={
                "match_text": "different visible quote",
                "match_mode": "exact",
                "source_span_resolution": "exact",
                "source_span_slices": [_slice(text="Alpha hinge line.", end=len("Alpha hinge line."))],
            },
        ),
        mechanism_key="iterator_v1",
        run_root=tmp_path,
        judge_mode="none",
    )

    assert result["label"] == "exact_match"


def test_segment_fallback_span_never_auto_counts_as_exact(tmp_path: Path) -> None:
    note_case = _note_case(source_span_text="Alpha hinge line.")
    result = module.evaluate_note_case_for_mechanism(
        note_case=note_case,
        mechanism_payload=_mechanism_payload(
            "Alpha hinge line.",
            locator={
                "match_text": "Alpha hinge line.",
                "match_mode": "segment_fallback",
                "source_span_resolution": "segment_fallback",
                "source_span_slices": [_slice(text="Alpha hinge line.", end=len("Alpha hinge line."))],
            },
        ),
        mechanism_key="iterator_v1",
        run_root=tmp_path,
        judge_mode="none",
    )

    assert result["label"] == "miss"
    assert result["judgment"]["reason"] == "judge_disabled"
    assert result["candidate_reactions"][0]["source_span_resolution"] == "segment_fallback"


def test_textually_similar_reaction_without_source_overlap_is_not_a_candidate(tmp_path: Path) -> None:
    note_case = _note_case(source_span_text="Alpha hinge line.")
    result = module.evaluate_note_case_for_mechanism(
        note_case=note_case,
        mechanism_payload=_mechanism_payload(
            "Alpha hinge line.",
            locator={"paragraph_index": 9, "char_start": 0, "char_end": 17},
        ),
        mechanism_key="attentional_v2",
        run_root=tmp_path,
        judge_mode="none",
    )

    assert result["label"] == "miss"
    assert result["judgment"]["reason"] == "no_candidate_source_span_overlap"
    assert result["candidate_reactions"] == []


def test_visible_reaction_without_locator_fails_contract(tmp_path: Path) -> None:
    note_case = _note_case(source_span_text="Alpha hinge line.")
    try:
        module.evaluate_note_case_for_mechanism(
            note_case=note_case,
            mechanism_payload=_mechanism_payload("Alpha hinge line.", locator={}),
            mechanism_key="attentional_v2",
            run_root=tmp_path,
            judge_mode="none",
        )
    except ValueError as exc:
        assert "has no usable source locator" in str(exc)
    else:
        raise AssertionError("missing locator should fail user-level selective matching")


def test_duplicate_reactions_on_same_span_are_deduped_before_judge(tmp_path: Path, monkeypatch) -> None:
    note_case = _note_case(source_span_text="Alpha hinge line.")
    judge_calls = []

    def fake_judge(**kwargs):
        judge_calls.append(kwargs["reaction"]["reaction_id"])
        return {
            "label": "focused_hit",
            "confidence": "high",
            "reason": "The one source span is focused enough.",
        }

    monkeypatch.setattr(module, "_judge_candidate_reaction", fake_judge)
    result = module.evaluate_note_case_for_mechanism(
        note_case=note_case,
        mechanism_payload={
            "status": "completed",
            "normalized_eval_bundle": {
                "reactions": [
                    {
                        "reaction_id": "r1",
                        "type": "discern",
                        "section_ref": "1.1",
                        "anchor_quote": "Alpha hinge line. Beta.",
                        "content": "reaction",
                        "target_locator": {"paragraph_index": 1, "char_start": 0, "char_end": 24},
                    },
                    {
                        "reaction_id": "r2",
                        "type": "curious",
                        "section_ref": "1.1",
                        "anchor_quote": "Alpha hinge line. Beta.",
                        "content": "another reaction",
                        "target_locator": {"paragraph_index": 1, "char_start": 0, "char_end": 24},
                    },
                ]
            },
        },
        mechanism_key="attentional_v2",
        run_root=tmp_path,
        judge_mode="llm",
    )

    assert judge_calls == ["r1"]
    assert result["span_candidate_count"] == 1
    assert result["duplicate_reaction_count"] == 2
    assert result["candidate_reactions"][0]["duplicate_reaction_ids"] == ["r1", "r2"]


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
        source_span_coordinate_system="segment_source_v1",
        source_span_slices=[
            {
                "coordinate_system": "segment_source_v1",
                "segment_id": "source_a__segment_1",
                "source_id": "source_a",
                "paragraph_index": 1,
                "char_start": 0,
                "char_end": 5,
                "text": "Alpha",
            }
        ],
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
        source_span_coordinate_system="segment_source_v1",
        source_span_slices=[
            {
                "coordinate_system": "segment_source_v1",
                "segment_id": "source_b__segment_1",
                "source_id": "source_b",
                "paragraph_index": 1,
                "char_start": 0,
                "char_end": 4,
                "text": "Beta",
            }
        ],
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


def test_run_user_level_selective_comparison_reuses_existing_output_without_reading(
    tmp_path: Path, monkeypatch
) -> None:
    segment = module.ReadingSegment(
        segment_id="source_a__segment_1",
        source_id="source_a",
        book_title="Book A",
        author="Author",
        language_track="en",
        start_sentence_id="a1",
        end_sentence_id="a9",
        chapter_ids=[1],
        chapter_titles=["Chapter 1"],
        target_note_count=1,
        covered_note_count=1,
        termination_reason="chapter_end_after_target_notes",
        segment_source_path="segment_a.md",
    )
    note_case = _note_case(source_span_text="Alpha hinge line.")
    reuse_output_dir = tmp_path / "old-output"

    monkeypatch.setattr(module, "_resolve_dataset_dir", lambda _manifest_path: tmp_path)
    monkeypatch.setattr(module, "_load_segments", lambda _dataset_dir: [segment])
    monkeypatch.setattr(module, "_load_note_cases", lambda _dataset_dir: [note_case])
    monkeypatch.setattr(
        module,
        "_run_mechanism_for_segment",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("read_book should not be called")),
    )

    rebuilt_calls: list[Path] = []

    def _fake_rebuild(**kwargs):
        rebuilt_calls.append(kwargs["source_output_dir"])
        return {"status": "completed", "normalized_eval_bundle": {"reactions": []}}

    monkeypatch.setattr(module, "_rebuild_mechanism_payload_from_output", _fake_rebuild)
    monkeypatch.setattr(module, "write_llm_usage_summary", lambda *args, **kwargs: None)

    aggregate = module.run_user_level_selective_comparison(
        run_id="unit_test_reuse_output",
        manifest_path=tmp_path / "manifest.json",
        mechanism_filter="attentional_v2",
        judge_mode="none",
        segment_ids=["source_a__segment_1"],
        reuse_output_dir=reuse_output_dir,
    )

    assert aggregate["segment_count"] == 1
    assert rebuilt_calls == [reuse_output_dir]
