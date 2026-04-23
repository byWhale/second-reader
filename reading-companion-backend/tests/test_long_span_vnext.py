from __future__ import annotations

import json
from pathlib import Path

from eval.attentional_v2 import run_long_span_vnext as runner
from src.attentional_v2.benchmark_probes import (
    is_memory_quality_probe_export_complete,
    load_memory_quality_probe_export,
    persist_due_memory_quality_probe_snapshots,
)
from src.attentional_v2.schemas import (
    build_empty_anchor_bank,
    build_empty_concept_registry,
    build_empty_local_buffer,
    build_empty_local_continuity,
    build_empty_move_history,
    build_empty_reaction_records,
    build_empty_reflective_frames,
    build_empty_thread_trace,
    build_empty_working_state,
)
from src.attentional_v2.storage import initialize_artifact_tree, memory_quality_probe_export_file


def _window() -> runner.ReadingWindow:
    return runner.ReadingWindow(
        segment_id="segment_a",
        source_id="source_a",
        book_title="Book A",
        author="Author A",
        language_track="en",
        start_sentence_id="c1-s1",
        end_sentence_id="c1-s5",
        source_chapter_ids=[1],
        chapter_titles=["Chapter 1"],
        target_note_count=20,
        covered_note_count=20,
        termination_reason="chapter_end_after_target_notes",
        segment_source_path="segment_sources/segment_a.txt",
    )


def _window_b() -> runner.ReadingWindow:
    return runner.ReadingWindow(
        segment_id="segment_b",
        source_id="source_b",
        book_title="Book B",
        author="Author B",
        language_track="en",
        start_sentence_id="c2-s1",
        end_sentence_id="c2-s5",
        source_chapter_ids=[2],
        chapter_titles=["Chapter 2"],
        target_note_count=20,
        covered_note_count=20,
        termination_reason="chapter_end_after_target_notes",
        segment_source_path="segment_sources/segment_b.txt",
    )


def _write_dataset(dataset_dir: Path, windows: list[runner.ReadingWindow], source_text_by_segment: dict[str, str]) -> None:
    (dataset_dir / "segment_sources").mkdir(parents=True, exist_ok=True)
    (dataset_dir / "manifest.json").write_text(json.dumps({"segments_file": "segments.jsonl"}), encoding="utf-8")
    with (dataset_dir / "segments.jsonl").open("w", encoding="utf-8") as handle:
        for window in windows:
            handle.write(json.dumps(runner.asdict(window), ensure_ascii=False) + "\n")
            (dataset_dir / window.segment_source_path).write_text(
                source_text_by_segment.get(window.segment_id, "Alpha. Beta."),
                encoding="utf-8",
            )


def _write_reuse_shard(
    *,
    reuse_root: Path,
    dataset_dir: Path,
    window: runner.ReadingWindow,
    mechanism_key: str = "iterator_v1",
) -> Path:
    shard_dir = reuse_root / "shards" / f"{window.source_id}__{mechanism_key}"
    (shard_dir / "meta").mkdir(parents=True, exist_ok=True)
    (shard_dir / "meta" / "selection.json").write_text(
        json.dumps(
            {
                "dataset_dir": str(dataset_dir),
                "segment_ids": [window.segment_id],
                "mechanism_keys": [mechanism_key],
            }
        ),
        encoding="utf-8",
    )
    output_dir = shard_dir / "outputs" / window.segment_id / mechanism_key
    (output_dir / "_runtime").mkdir(parents=True, exist_ok=True)
    (output_dir / "_runtime" / "run_state.json").write_text(json.dumps({"status": "completed"}), encoding="utf-8")
    return output_dir


def _book_document() -> dict[str, object]:
    return {
        "metadata": {"book": "Book A"},
        "chapters": [
            {
                "id": 1,
                "title": "Chapter 1",
                "paragraphs": [
                    {"paragraph_index": 1, "text": "Alpha. Beta."},
                    {"paragraph_index": 2, "text": "Gamma. Delta."},
                ],
                "sentences": [
                    {
                        "sentence_id": "c1-s1",
                        "paragraph_index": 1,
                        "text": "Alpha.",
                        "locator": {"paragraph_index": 1, "char_end": 6},
                    },
                    {
                        "sentence_id": "c1-s2",
                        "paragraph_index": 1,
                        "text": "Beta.",
                        "locator": {"paragraph_index": 1, "char_end": 12},
                    },
                    {
                        "sentence_id": "c1-s3",
                        "paragraph_index": 2,
                        "text": "Gamma.",
                        "locator": {"paragraph_index": 2, "char_end": 6},
                    },
                    {
                        "sentence_id": "c1-s4",
                        "paragraph_index": 2,
                        "text": "Delta.",
                        "locator": {"paragraph_index": 2, "char_end": 13},
                    },
                ],
            }
        ],
    }


def test_persist_due_memory_quality_probe_snapshots_emits_once_per_threshold(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    initialize_artifact_tree(output_dir)

    local_buffer = build_empty_local_buffer()
    local_buffer["recent_sentences"] = [
        {"sentence_id": "c1-s1"},
        {"sentence_id": "c1-s2"},
        {"sentence_id": "c1-s3"},
        {"sentence_id": "c1-s4"},
    ]
    local_buffer["recent_meaning_units"] = [["c1-s1", "c1-s2"], ["c1-s3", "c1-s4"]]
    local_continuity = build_empty_local_continuity()
    local_continuity["chapter_ref"] = "Chapter 1"
    local_continuity["current_sentence_id"] = "c1-s4"
    local_continuity["reading_queue_stage"] = "mainline"

    settings = {
        "enabled": True,
        "segment_id": "segment_a",
        "source_id": "source_a",
        "book_title": "Book A",
        "language_track": "en",
        "threshold_ratios": [0.2, 0.4, 0.6, 0.8, 1.0],
    }
    ordered_sentence_ids = ["c1-s1", "c1-s2", "c1-s3", "c1-s4", "c1-s5"]

    first = persist_due_memory_quality_probe_snapshots(
        output_dir=output_dir,
        settings=settings,
        ordered_sentence_ids=ordered_sentence_ids,
        actual_sentence_id="c1-s4",
        chapter_ref="Chapter 1",
        local_buffer=local_buffer,
        local_continuity=local_continuity,
        working_state=build_empty_working_state(),
        concept_registry=build_empty_concept_registry(),
        thread_trace=build_empty_thread_trace(),
        reflective_frames=build_empty_reflective_frames(),
        anchor_bank=build_empty_anchor_bank(),
        move_history=build_empty_move_history(),
        reaction_records=build_empty_reaction_records(),
    )

    assert len(first) == 4
    payload = load_memory_quality_probe_export(output_dir)
    assert len(payload["snapshots"]) == 4

    second = persist_due_memory_quality_probe_snapshots(
        output_dir=output_dir,
        settings=settings,
        ordered_sentence_ids=ordered_sentence_ids,
        actual_sentence_id="c1-s4",
        chapter_ref="Chapter 1",
        local_buffer=local_buffer,
        local_continuity=local_continuity,
        working_state=build_empty_working_state(),
        concept_registry=build_empty_concept_registry(),
        thread_trace=build_empty_thread_trace(),
        reflective_frames=build_empty_reflective_frames(),
        anchor_bank=build_empty_anchor_bank(),
        move_history=build_empty_move_history(),
        reaction_records=build_empty_reaction_records(),
    )
    assert second == []

    final = persist_due_memory_quality_probe_snapshots(
        output_dir=output_dir,
        settings=settings,
        ordered_sentence_ids=ordered_sentence_ids,
        actual_sentence_id="c1-s5",
        chapter_ref="Chapter 1",
        local_buffer=local_buffer,
        local_continuity=local_continuity,
        working_state=build_empty_working_state(),
        concept_registry=build_empty_concept_registry(),
        thread_trace=build_empty_thread_trace(),
        reflective_frames=build_empty_reflective_frames(),
        anchor_bank=build_empty_anchor_bank(),
        move_history=build_empty_move_history(),
        reaction_records=build_empty_reaction_records(),
    )
    assert len(final) == 1
    assert is_memory_quality_probe_export_complete(output_dir)


def test_build_read_so_far_source_text_cuts_at_capture_sentence() -> None:
    source_text = runner.build_read_so_far_source_text(_book_document(), "c1-s3")
    assert "Alpha. Beta." in source_text
    assert "Gamma." in source_text
    assert "Delta." not in source_text


def test_ensure_window_output_reuses_completed_v2_with_probe_export(tmp_path: Path, monkeypatch) -> None:
    run_root = tmp_path / "run"
    window = _window()
    dataset_dir = tmp_path / "dataset"
    (dataset_dir / "segment_sources").mkdir(parents=True, exist_ok=True)
    (dataset_dir / window.segment_source_path).write_text("demo", encoding="utf-8")

    output_dir = run_root / "outputs" / window.segment_id / "attentional_v2"
    (output_dir / "_runtime").mkdir(parents=True, exist_ok=True)
    (output_dir / "_runtime" / "run_state.json").write_text(json.dumps({"status": "completed"}), encoding="utf-8")
    memory_quality_probe_export_file(output_dir).parent.mkdir(parents=True, exist_ok=True)
    memory_quality_probe_export_file(output_dir).write_text(
        json.dumps(
            {
                "probe_targets": [{"probe_index": index} for index in range(1, 6)],
                "snapshots": [{"probe_index": index} for index in range(1, 6)],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        runner,
        "rebuild_normalized_bundle_from_completed_output",
        lambda **_: {
            "mechanism_label": "Attentional V2 scaffold (Phase 1-8)",
            "normalized_eval_bundle": {"reactions": [], "memory_summaries": []},
        },
    )

    class _ShouldNotRun:
        def read_book(self, request):  # pragma: no cover - guard path
            raise AssertionError("read_book should not run when reuse succeeds")

    monkeypatch.setattr(runner, "_mechanism_for_key", lambda mechanism_key: _ShouldNotRun())

    payload = runner.ensure_window_output(
        window=window,
        dataset_dir=dataset_dir,
        mechanism_key="attentional_v2",
        run_root=run_root,
        require_probe_export=True,
    )

    assert payload["status"] == "completed"
    assert payload["run_mode"] == "reuse_completed"


def test_ensure_window_output_with_retries_retries_provider_overload(tmp_path: Path, monkeypatch) -> None:
    run_root = tmp_path / "run"
    window = _window()
    dataset_dir = tmp_path / "dataset"
    output_dir = run_root / "outputs" / window.segment_id / "iterator_v1"
    (output_dir / "_runtime").mkdir(parents=True, exist_ok=True)
    (output_dir / "_runtime" / "run_state.json").write_text(
        json.dumps({"status": "error", "error": "overloaded_error (529)"}),
        encoding="utf-8",
    )
    attempts = {"count": 0}

    def _fake_ensure_window_output(**kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise RuntimeError("Error code: 529 - overloaded_error")
        return {
            "status": "completed",
            "mechanism_key": kwargs["mechanism_key"],
            "output_dir": str(output_dir),
            "normalized_eval_bundle": {"reactions": [], "memory_summaries": []},
        }

    monkeypatch.setattr(runner, "ensure_window_output", _fake_ensure_window_output)

    payload = runner.ensure_window_output_with_retries(
        window=window,
        dataset_dir=dataset_dir,
        mechanism_key="iterator_v1",
        run_root=run_root,
        require_probe_export=False,
        max_attempts=2,
        retry_sleep_seconds=0,
    )

    assert attempts["count"] == 2
    assert payload["status"] == "completed"
    assert payload["output_attempt"] == 2


def test_find_reaction_reuse_output_accepts_matching_v1_window(tmp_path: Path, monkeypatch) -> None:
    window = _window()
    current_dataset = tmp_path / "current_dataset"
    reuse_dataset = tmp_path / "reuse_dataset"
    reuse_root = tmp_path / "reuse_run"
    _write_dataset(current_dataset, [window], {window.segment_id: "Alpha. Beta."})
    _write_dataset(reuse_dataset, [window], {window.segment_id: "Alpha. Beta."})
    reuse_output_dir = _write_reuse_shard(reuse_root=reuse_root, dataset_dir=reuse_dataset, window=window)

    monkeypatch.setattr(
        runner,
        "rebuild_normalized_bundle_from_completed_output",
        lambda **_: {
            "mechanism_label": "Current Iterator-Reader implementation",
            "normalized_eval_bundle": {"reactions": [], "memory_summaries": []},
        },
    )

    payload = runner.find_reaction_reuse_output(
        current_dataset_dir=current_dataset,
        window=window,
        mechanism_key="iterator_v1",
        reuse_run_root=reuse_root,
    )

    assert payload is not None
    assert payload["status"] == "completed"
    assert payload["run_mode"] == "reuse_reaction_output"
    assert payload["output_dir"] == str(reuse_output_dir)
    assert payload["reuse_validation"]["reason"] == "matched"


def test_find_reaction_reuse_output_rejects_changed_window_source(tmp_path: Path) -> None:
    window = _window()
    current_dataset = tmp_path / "current_dataset"
    reuse_dataset = tmp_path / "reuse_dataset"
    reuse_root = tmp_path / "reuse_run"
    _write_dataset(current_dataset, [window], {window.segment_id: "Alpha. Beta. Current."})
    _write_dataset(reuse_dataset, [window], {window.segment_id: "Alpha. Beta. Old."})
    _write_reuse_shard(reuse_root=reuse_root, dataset_dir=reuse_dataset, window=window)

    payload = runner.find_reaction_reuse_output(
        current_dataset_dir=current_dataset,
        window=window,
        mechanism_key="iterator_v1",
        reuse_run_root=reuse_root,
    )

    assert payload is not None
    assert payload["status"] == "rejected"
    assert payload["validation"]["reason"] == "source_text_sha256_mismatch"


def test_run_long_span_vnext_writes_separated_memory_and_reaction_outputs(tmp_path: Path, monkeypatch) -> None:
    run_root = tmp_path / "run"
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    window = _window()
    output_dir_v2 = run_root / "outputs" / window.segment_id / "attentional_v2"
    output_dir_v1 = run_root / "outputs" / window.segment_id / "iterator_v1"
    (output_dir_v2 / "public").mkdir(parents=True, exist_ok=True)
    (output_dir_v1 / "public").mkdir(parents=True, exist_ok=True)
    (output_dir_v2 / "public" / "book_document.json").write_text(json.dumps(_book_document()), encoding="utf-8")
    memory_quality_probe_export_file(output_dir_v2).parent.mkdir(parents=True, exist_ok=True)
    memory_quality_probe_export_file(output_dir_v2).write_text(
        json.dumps(
            {
                "snapshots": [
                    {
                        "probe_index": 1,
                        "threshold_ratio": 0.2,
                        "capture_sentence_id": "c1-s2",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(runner, "_resolve_dataset_dir", lambda manifest_path: dataset_dir)
    monkeypatch.setattr(runner, "_load_windows", lambda dataset_dir: [window])
    monkeypatch.setattr(
        runner,
        "ensure_window_output_with_retries",
        lambda **kwargs: {
            "status": "completed",
            "mechanism_key": kwargs["mechanism_key"],
            "mechanism_label": kwargs["mechanism_key"],
            "output_dir": str(output_dir_v2 if kwargs["mechanism_key"] == "attentional_v2" else output_dir_v1),
            "normalized_eval_bundle": {
                "reactions": [
                    {
                        "reaction_id": f"{kwargs['mechanism_key']}-r1",
                        "type": "highlight",
                        "section_ref": "1.1",
                        "anchor_quote": "Anchor",
                        "content": "Reaction content",
                    }
                ],
                "memory_summaries": [],
            },
            "run_mode": "reuse_completed",
        },
    )
    monkeypatch.setattr(
        runner,
        "judge_memory_quality_probe",
        lambda **kwargs: {
            "salience_score": 4,
            "mainline_fidelity_score": 4,
            "organization_score": 3,
            "fidelity_score": 4,
            "overall_memory_quality_score": 4,
            "reason": "Retained the mainline clearly.",
        },
    )
    monkeypatch.setattr(
        runner,
        "audit_window_reactions",
        lambda **kwargs: [
            {
                "reaction_id": f"{kwargs['mechanism_key']}-r1",
                "label": "grounded_callback" if kwargs["mechanism_key"] == "attentional_v2" else "local_only",
                "reason": "classified in test",
            }
        ],
    )
    monkeypatch.setattr(runner, "write_llm_usage_summary", lambda run_root: None)

    aggregate = runner.run_long_span_vnext(
        run_root=run_root,
        manifest_path=tmp_path / "unused.json",
        judge_mode="llm",
        workers=2,
    )

    assert aggregate["memory_quality"]["mechanism_key"] == "attentional_v2"
    assert set(aggregate["reaction_audit"]["mechanisms"].keys()) == {"attentional_v2", "iterator_v1"}
    report = (run_root / "summary" / "report.md").read_text(encoding="utf-8")
    assert "## Memory Quality (V2 only)" in report
    assert "## Reaction Audit" in report


def test_run_long_span_vnext_reuses_v1_for_unchanged_windows_only(tmp_path: Path, monkeypatch) -> None:
    run_root = tmp_path / "run"
    current_dataset = tmp_path / "current_dataset"
    reuse_dataset = tmp_path / "reuse_dataset"
    reuse_root = tmp_path / "reuse_run"
    window_a = _window()
    window_b = _window_b()
    _write_dataset(
        current_dataset,
        [window_a, window_b],
        {
            window_a.segment_id: "Alpha. Beta.",
            window_b.segment_id: "Current Book B.",
        },
    )
    _write_dataset(
        reuse_dataset,
        [window_a, window_b],
        {
            window_a.segment_id: "Alpha. Beta.",
            window_b.segment_id: "Old Book B.",
        },
    )
    _write_reuse_shard(reuse_root=reuse_root, dataset_dir=reuse_dataset, window=window_a)
    _write_reuse_shard(reuse_root=reuse_root, dataset_dir=reuse_dataset, window=window_b)

    monkeypatch.setattr(runner, "_resolve_dataset_dir", lambda manifest_path: current_dataset)
    monkeypatch.setattr(runner, "_load_windows", lambda dataset_dir: [window_a, window_b] if dataset_dir == current_dataset else [window_a, window_b])
    monkeypatch.setattr(
        runner,
        "rebuild_normalized_bundle_from_completed_output",
        lambda **kwargs: {
            "mechanism_label": kwargs["mechanism_key"],
            "normalized_eval_bundle": {
                "reactions": [
                    {
                        "reaction_id": f"{kwargs['mechanism_key']}-{kwargs['segment_id']}-r1",
                        "type": "highlight",
                        "section_ref": "1.1",
                        "anchor_quote": "Anchor",
                        "content": "Reaction content",
                    }
                ],
                "memory_summaries": [],
            },
        },
    )

    fresh_calls: list[tuple[str, str]] = []

    def _fake_ensure_window_output_with_retries(**kwargs):
        window = kwargs["window"]
        mechanism_key = kwargs["mechanism_key"]
        fresh_calls.append((window.segment_id, mechanism_key))
        output_dir = run_root / "outputs" / window.segment_id / mechanism_key
        (output_dir / "public").mkdir(parents=True, exist_ok=True)
        (output_dir / "public" / "book_document.json").write_text(json.dumps(_book_document()), encoding="utf-8")
        if mechanism_key == "attentional_v2":
            memory_quality_probe_export_file(output_dir).parent.mkdir(parents=True, exist_ok=True)
            memory_quality_probe_export_file(output_dir).write_text(
                json.dumps(
                    {
                        "snapshots": [
                            {
                                "probe_index": 1,
                                "threshold_ratio": 0.2,
                                "capture_sentence_id": "c1-s2",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
        return {
            "status": "completed",
            "mechanism_key": mechanism_key,
            "mechanism_label": mechanism_key,
            "output_dir": str(output_dir),
            "normalized_eval_bundle": {
                "reactions": [
                    {
                        "reaction_id": f"{mechanism_key}-{window.segment_id}-fresh-r1",
                        "type": "highlight",
                        "section_ref": "1.1",
                        "anchor_quote": "Anchor",
                        "content": "Reaction content",
                    }
                ],
                "memory_summaries": [],
            },
            "run_mode": "fresh",
        }

    monkeypatch.setattr(runner, "ensure_window_output_with_retries", _fake_ensure_window_output_with_retries)
    monkeypatch.setattr(
        runner,
        "judge_memory_quality_probe",
        lambda **kwargs: {
            "salience_score": 4,
            "mainline_fidelity_score": 4,
            "organization_score": 3,
            "fidelity_score": 4,
            "overall_memory_quality_score": 4,
            "reason": "Retained the mainline clearly.",
        },
    )
    monkeypatch.setattr(
        runner,
        "audit_window_reactions",
        lambda **kwargs: [
            {
                "reaction_id": reaction["reaction_id"],
                "label": "local_only",
                "reason": "classified in test",
            }
            for reaction in kwargs["normalized_bundle"].get("reactions", [])
        ],
    )
    monkeypatch.setattr(runner, "write_llm_usage_summary", lambda run_root: None)

    aggregate = runner.run_long_span_vnext(
        run_root=run_root,
        manifest_path=tmp_path / "unused.json",
        judge_mode="llm",
        workers=4,
        reaction_reuse_run_root=reuse_root,
    )

    assert ("segment_a", "iterator_v1") not in fresh_calls
    assert ("segment_b", "iterator_v1") in fresh_calls
    assert ("segment_a", "attentional_v2") in fresh_calls
    assert ("segment_b", "attentional_v2") in fresh_calls
    assert aggregate["output_modes"]["segment_a:iterator_v1"] == "reuse_reaction_output"
    assert aggregate["output_modes"]["segment_b:iterator_v1"] == "fresh"
    sourcing = json.loads((run_root / "meta" / "output_sourcing.json").read_text(encoding="utf-8"))
    assert sourcing["fresh_task_count"] == 3
