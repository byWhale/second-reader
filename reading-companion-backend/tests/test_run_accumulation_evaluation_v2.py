from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eval.attentional_v2 import run_accumulation_evaluation_v2 as accumulation_v2_runner


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _span_slice(*, segment_id: str, paragraph_index: int, char_start: int, char_end: int, text: str) -> dict[str, object]:
    return {
        "coordinate_system": "segment_source_v1",
        "segment_id": segment_id,
        "paragraph_index": paragraph_index,
        "char_start": char_start,
        "char_end": char_end,
        "text": text,
    }


def _span_point(point_id: str, *, segment_id: str, paragraph_index: int, char_start: int, char_end: int, text: str) -> dict[str, object]:
    return {
        "point_id": point_id,
        "label": point_id,
        "span_text": text,
        "span_slices": [
            _span_slice(
                segment_id=segment_id,
                paragraph_index=paragraph_index,
                char_start=char_start,
                char_end=char_end,
                text=text,
            )
        ],
    }


def _bootstrap_segment_dataset(tmp_path: Path) -> Path:
    dataset_dir = tmp_path / "segments"
    _write_json(
        dataset_dir / "manifest.json",
        {
            "dataset_id": "demo_segments",
            "family": "user_level_note_aligned_benchmark",
            "segments_file": "segments.jsonl",
            "segment_count": 1,
            "source_manifest_refs": ["state/dataset_build/demo_sources.json"],
        },
    )
    _write_jsonl(
        dataset_dir / "segments.jsonl",
        [
            {
                "segment_id": "segment_a",
                "source_id": "source_a",
                "book_title": "Book A",
                "author": "Author A",
                "language_track": "en",
                "start_sentence_id": "c1-s1",
                "end_sentence_id": "c1-s8",
                "source_chapter_ids": [1],
                "chapter_titles": ["Chapter 1"],
                "target_note_count": 20,
                "covered_note_count": 20,
                "termination_reason": "chapter_end_after_target_notes",
                "segment_source_path": "segment_sources/segment_a.txt",
            }
        ],
    )
    (dataset_dir / "segment_sources").mkdir(parents=True, exist_ok=True)
    (dataset_dir / "segment_sources" / "segment_a.txt").write_text("demo segment text", encoding="utf-8")
    return dataset_dir


def _bootstrap_case_dataset(tmp_path: Path) -> Path:
    dataset_dir = tmp_path / "cases"
    _write_json(
        dataset_dir / "manifest.json",
        {
            "dataset_id": "demo_cases",
            "family": "accumulation_target_cases",
            "primary_file": "cases.jsonl",
        },
    )
    _write_jsonl(
        dataset_dir / "cases.jsonl",
        [
            {
                "case_id": "case_a",
                "source_id": "source_a",
                "book": "Book A",
                "author": "Author A",
                "output_language": "en",
                "window_id": "segment_a",
                "thread_type": "叙事型故事脉络",
                "target_span": _span_point("target", segment_id="segment_a", paragraph_index=3, char_start=0, char_end=12, text="late target"),
                "upstream_nodes": [
                    {
                        "node_id": "u1",
                        "label": "u1",
                        "summary": "setup",
                        "span_text": "early setup",
                        "span_slices": [_span_slice(segment_id="segment_a", paragraph_index=1, char_start=0, char_end=11, text="early setup")],
                    },
                    {
                        "node_id": "u2",
                        "label": "u2",
                        "summary": "mid pressure",
                        "span_text": "mid pressure",
                        "span_slices": [_span_slice(segment_id="segment_a", paragraph_index=2, char_start=0, char_end=12, text="mid pressure")],
                    },
                ],
                "expected_integration": "At the target point, the reader should connect the late development back to the earlier setup and pressure.",
                "callback_eligible_spans": [
                    _span_point("cb1", segment_id="segment_a", paragraph_index=1, char_start=0, char_end=11, text="early setup")
                ],
                "non_goal_but_tempting_points": [
                    _span_point("tempting", segment_id="segment_a", paragraph_index=4, char_start=0, char_end=8, text="nearby text")
                ],
                "long_range_rationale": "The target depends on materially earlier setup and pressure.",
                "curation_status": "candidate_review_pending",
                "provenance": {"note": "test"},
            }
        ],
    )
    return dataset_dir


def _bootstrap_formal_manifest(tmp_path: Path, *, segment_dataset: Path, case_dataset: Path) -> Path:
    manifest_path = tmp_path / "formal_manifest.json"
    _write_json(
        manifest_path,
        {
            "source_refs": {
                "user_level_dataset_roots": [str(segment_dataset.resolve())],
                "accumulation_target_case_datasets": [str(case_dataset.resolve())],
            },
            "splits": {
                "accumulation_target_cases_draft": {"all": ["case_a"]},
                "accumulation_target_cases_frozen": {"all": []},
            },
        },
    )
    return manifest_path


def _reaction(*, reaction_id: str, paragraph_index: int, text: str, content: str) -> dict[str, object]:
    return {
        "reaction_id": reaction_id,
        "type": "discern",
        "section_ref": f"1.{paragraph_index}",
        "anchor_quote": text,
        "content": content,
        "target_locator": {
            "source_span_slices": [
                {
                    "segment_id": "segment_a",
                    "paragraph_index": paragraph_index,
                    "char_start": 0,
                    "char_end": len(text),
                    "text": text,
                }
            ]
        },
    }


def _bundle() -> dict[str, Any]:
    return {
        "reactions": [
            _reaction(reaction_id="r1", paragraph_index=1, text="early setup", content="noticed the setup"),
            _reaction(reaction_id="r2", paragraph_index=3, text="late target", content="this late turn depends on earlier setup"),
            _reaction(reaction_id="r3", paragraph_index=1, text="early setup", content="returned to the setup explicitly"),
            _reaction(reaction_id="r4", paragraph_index=4, text="after target", content="follow up reaction"),
        ],
        "attention_events": [
            {
                "kind": "thought",
                "phase": "thinking",
                "section_ref": "1.3",
                "move_type": "bridge",
                "message": "This connects back to the early setup.",
                "current_excerpt": "late target",
            }
        ],
        "memory_summaries": ["summary"],
    }


def test_prepare_selection_loads_segments_and_target_cases(tmp_path: Path) -> None:
    segment_dataset = _bootstrap_segment_dataset(tmp_path)
    case_dataset = _bootstrap_case_dataset(tmp_path)
    manifest_path = _bootstrap_formal_manifest(tmp_path, segment_dataset=segment_dataset, case_dataset=case_dataset)

    selection = accumulation_v2_runner._prepare_selection(formal_manifest_path=manifest_path)

    assert selection.dataset_dir == segment_dataset.resolve()
    assert [segment.segment_id for segment in selection.segments] == ["segment_a"]
    assert [case.case_id for case in selection.cases] == ["case_a"]


def test_build_target_evidence_bundle_collects_target_callbacks_and_followups() -> None:
    case = accumulation_v2_runner.target_case_from_row(
        {
            "case_id": "case_a",
            "source_id": "source_a",
            "book": "Book A",
            "author": "Author A",
            "output_language": "en",
            "window_id": "segment_a",
            "thread_type": "叙事型故事脉络",
            "target_span": _span_point("target", segment_id="segment_a", paragraph_index=3, char_start=0, char_end=11, text="late target"),
            "upstream_nodes": [
                {
                    "node_id": "u1",
                    "label": "u1",
                    "summary": "setup",
                    "span_text": "early setup",
                    "span_slices": [_span_slice(segment_id="segment_a", paragraph_index=1, char_start=0, char_end=11, text="early setup")],
                },
                {
                    "node_id": "u2",
                    "label": "u2",
                    "summary": "mid pressure",
                    "span_text": "mid pressure",
                    "span_slices": [_span_slice(segment_id="segment_a", paragraph_index=2, char_start=0, char_end=12, text="mid pressure")],
                },
            ],
            "expected_integration": "late depends on earlier setup",
            "callback_eligible_spans": [_span_point("cb1", segment_id="segment_a", paragraph_index=1, char_start=0, char_end=11, text="early setup")],
            "non_goal_but_tempting_points": [_span_point("tempting", segment_id="segment_a", paragraph_index=4, char_start=0, char_end=8, text="after target")],
            "long_range_rationale": "Later depends on earlier",
            "curation_status": "candidate_review_pending",
            "provenance": {},
        }
    )
    segment = accumulation_v2_runner.ReadingSegment(
        segment_id="segment_a",
        source_id="source_a",
        book_title="Book A",
        author="Author A",
        language_track="en",
        start_sentence_id="c1-s1",
        end_sentence_id="c1-s8",
        chapter_ids=[1],
        chapter_titles=["Chapter 1"],
        target_note_count=20,
        covered_note_count=20,
        termination_reason="chapter_end_after_target_notes",
        segment_source_path="segment_sources/segment_a.txt",
    )

    evidence = accumulation_v2_runner._build_target_evidence_bundle(case=case, segment=segment, bundle=_bundle())

    assert evidence.target_local_reactions[0]["reaction_id"] == "r2"
    assert any(item.get("matched_callback_point_id") == "cb1" for item in evidence.explicit_callback_actions)
    assert evidence.short_horizon_followups[0]["reaction_id"] == "r3"


def test_aggregate_results_uses_quality_then_callback_then_tie() -> None:
    case_payloads = [
        {
            "case_id": "case_a",
            "output_language": "en",
            "mechanism_results": {
                "attentional_v2": {"status": "completed", "judgment": {"quality_score": 4, "callback_score": 1, "thread_built": "built", "reason": "ok"}},
                "iterator_v1": {"status": "completed", "judgment": {"quality_score": 4, "callback_score": 0, "thread_built": "built", "reason": "ok"}},
            },
        },
        {
            "case_id": "case_b",
            "output_language": "en",
            "mechanism_results": {
                "attentional_v2": {"status": "completed", "judgment": {"quality_score": 3, "callback_score": 1, "thread_built": "partial", "reason": "ok"}},
                "iterator_v1": {"status": "completed", "judgment": {"quality_score": 5, "callback_score": 0, "thread_built": "built", "reason": "ok"}},
            },
        },
        {
            "case_id": "case_c",
            "output_language": "zh",
            "mechanism_results": {
                "attentional_v2": {"status": "completed", "judgment": {"quality_score": 4, "callback_score": 1, "thread_built": "built", "reason": "ok"}},
                "iterator_v1": {"status": "completed", "judgment": {"quality_score": 4, "callback_score": 1, "thread_built": "built", "reason": "ok"}},
            },
        },
    ]

    aggregate = accumulation_v2_runner._aggregate_results(case_payloads=case_payloads, mechanism_keys=("attentional_v2", "iterator_v1"))

    assert aggregate["derived_comparison"]["winner_counts"] == {"attentional_v2": 1, "iterator_v1": 1, "tie": 1}
    assert aggregate["derived_comparison"]["pairwise"]["winner_counts"] == {"attentional_v2": 1, "iterator_v1": 1, "tie": 1}


def test_run_accumulation_evaluation_v2_writes_absolute_results(tmp_path: Path, monkeypatch) -> None:
    segment_dataset = _bootstrap_segment_dataset(tmp_path)
    case_dataset = _bootstrap_case_dataset(tmp_path)
    manifest_path = _bootstrap_formal_manifest(tmp_path, segment_dataset=segment_dataset, case_dataset=case_dataset)
    runs_root = tmp_path / "runs"
    monkeypatch.setattr(accumulation_v2_runner, "DEFAULT_RUNS_ROOT", runs_root)

    def fake_run_mechanism_for_segment(*, segment, dataset_dir, mechanism_key, run_root):
        return {
            "status": "completed",
            "mechanism_key": mechanism_key,
            "mechanism_label": mechanism_key,
            "output_dir": str(run_root / "outputs" / segment.segment_id / mechanism_key),
            "normalized_eval_bundle": _bundle(),
            "bundle_summary": {"reaction_count": 4},
            "error": "",
        }

    def fake_judge_target_case(*, case, evidence_bundle, run_root, mechanism_key, judge_mode):
        return {
            "quality_score": 5 if mechanism_key == "attentional_v2" else 4,
            "callback_score": 2 if mechanism_key == "attentional_v2" else 1,
            "thread_built": "built",
            "reason": "fresh_rejudge",
        }

    monkeypatch.setattr(accumulation_v2_runner, "_run_mechanism_for_segment", fake_run_mechanism_for_segment)
    monkeypatch.setattr(accumulation_v2_runner, "_judge_target_case", fake_judge_target_case)

    summary = accumulation_v2_runner.run_accumulation_evaluation_v2(
        run_id="demo_v2_run",
        formal_manifest_path=manifest_path,
        mechanism_filter="both",
        judge_mode="llm",
    )

    assert summary["case_count"] == 1
    assert summary["aggregate"]["mechanisms"]["attentional_v2"]["average_quality_score"] == 5
    assert summary["aggregate"]["derived_comparison"]["winner_counts"] == {"attentional_v2": 1}
    case_result = json.loads((runs_root / "demo_v2_run" / "cases" / "case_a.json").read_text(encoding="utf-8"))
    assert case_result["mechanism_results"]["attentional_v2"]["judgment"]["reason"] == "fresh_rejudge"


def test_run_accumulation_evaluation_v2_reuses_existing_output_without_reading(
    tmp_path: Path, monkeypatch
) -> None:
    segment_dataset = _bootstrap_segment_dataset(tmp_path)
    case_dataset = _bootstrap_case_dataset(tmp_path)
    manifest_path = _bootstrap_formal_manifest(tmp_path, segment_dataset=segment_dataset, case_dataset=case_dataset)
    runs_root = tmp_path / "runs"
    reuse_output_dir = tmp_path / "old-output"
    monkeypatch.setattr(accumulation_v2_runner, "DEFAULT_RUNS_ROOT", runs_root)
    monkeypatch.setattr(
        accumulation_v2_runner,
        "_run_mechanism_for_segment",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("read_book should not be called")),
    )

    rebuilt_calls: list[Path] = []

    def _fake_rebuild(**kwargs):
        rebuilt_calls.append(kwargs["source_output_dir"])
        return {
            "status": "completed",
            "mechanism_key": kwargs["mechanism_key"],
            "mechanism_label": kwargs["mechanism_key"],
            "output_dir": str(kwargs["source_output_dir"]),
            "normalized_eval_bundle": _bundle(),
            "bundle_summary": {"reaction_count": 4},
            "error": "",
        }

    monkeypatch.setattr(accumulation_v2_runner, "_rebuild_mechanism_payload_from_output", _fake_rebuild)
    monkeypatch.setattr(
        accumulation_v2_runner,
        "_judge_target_case",
        lambda **_kwargs: {
            "quality_score": 4,
            "callback_score": 1,
            "thread_built": "built",
            "reason": "reused_output",
        },
    )

    summary = accumulation_v2_runner.run_accumulation_evaluation_v2(
        run_id="demo_v2_reuse",
        formal_manifest_path=manifest_path,
        mechanism_filter="attentional_v2",
        judge_mode="llm",
        segment_ids=["segment_a"],
        reuse_output_dir=reuse_output_dir,
    )

    assert summary["case_count"] == 1
    assert rebuilt_calls == [reuse_output_dir.resolve()]
    case_result = json.loads((runs_root / "demo_v2_reuse" / "cases" / "case_a.json").read_text(encoding="utf-8"))
    assert case_result["mechanism_results"]["attentional_v2"]["judgment"]["reason"] == "reused_output"
