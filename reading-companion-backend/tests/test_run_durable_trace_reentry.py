"""Tests for durable-trace and re-entry orchestration."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from eval.attentional_v2 import run_durable_trace_reentry as durable_trace


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _bootstrap_datasets(tmp_path: Path) -> tuple[Path, Path, Path, list[str]]:
    chapter_dir = tmp_path / "chapter_dataset"
    runtime_dir = tmp_path / "runtime_dataset"
    _write_json(
        chapter_dir / "manifest.json",
        {
            "dataset_id": "demo_chapter_dataset",
            "version": "1",
            "primary_file": "chapters.jsonl",
        },
    )
    _write_jsonl(
        chapter_dir / "chapters.jsonl",
        [
            {
                "chapter_case_id": "case_a",
                "source_id": "source_a",
                "book_title": "Book A",
                "author": "Author A",
                "language_track": "en",
                "type_tags": ["argumentative"],
                "role_tags": ["argumentative"],
                "output_dir": "output/book-a",
                "chapter_id": 10,
                "chapter_title": "Chapter 10",
                "sentence_count": 50,
                "paragraph_count": 8,
                "candidate_position_bucket": "middle",
                "candidate_score": 6.5,
                "selection_status": "selected_v2",
                "selection_priority": 4,
                "selection_role": "argumentative",
            },
            {
                "chapter_case_id": "case_b",
                "source_id": "source_b",
                "book_title": "Book B",
                "author": "Author B",
                "language_track": "zh",
                "type_tags": ["narrative_reflective"],
                "role_tags": ["narrative_reflective"],
                "output_dir": "output/book-b",
                "chapter_id": 11,
                "chapter_title": "Chapter 11",
                "sentence_count": 70,
                "paragraph_count": 9,
                "candidate_position_bucket": "middle",
                "candidate_score": 6.2,
                "selection_status": "selected_v2",
                "selection_priority": 5,
                "selection_role": "narrative_reflective",
            },
        ],
    )
    _write_json(
        runtime_dir / "manifest.json",
        {
            "dataset_id": "demo_runtime_dataset",
            "version": "1",
            "primary_file": "fixtures.jsonl",
        },
    )
    _write_jsonl(
        runtime_dir / "fixtures.jsonl",
        [
            {
                "fixture_id": "case_a__warm",
                "source_id": "source_a",
                "language_track": "en",
                "chapter_case_id": "case_a",
                "selection_role": "argumentative",
                "resume_kind": "warm",
                "target_sentence_index": 12,
            },
            {
                "fixture_id": "case_a__cold",
                "source_id": "source_a",
                "language_track": "en",
                "chapter_case_id": "case_a",
                "selection_role": "argumentative",
                "resume_kind": "cold",
                "target_sentence_index": 24,
            },
            {
                "fixture_id": "case_b__reconstitution",
                "source_id": "source_b",
                "language_track": "zh",
                "chapter_case_id": "case_b",
                "selection_role": "narrative_reflective",
                "resume_kind": "reconstitution",
                "target_sentence_index": 36,
            },
        ],
    )
    source_manifest = tmp_path / "source_manifest.json"
    _write_json(
        source_manifest,
        {
            "books": [
                {"source_id": "source_a", "relative_local_path": "state/library_sources/source_a.epub"},
                {"source_id": "source_b", "relative_local_path": "state/library_sources/source_b.epub"},
            ]
        },
    )
    return chapter_dir, runtime_dir, source_manifest, ["case_a", "case_b"]


def _case_result(case: durable_trace.ChapterCase) -> dict[str, Any]:
    return {
        "chapter_case_id": case.chapter_case_id,
        "language_track": case.language_track,
        "selection_role": case.selection_role,
        "book_title": case.book_title,
        "author": case.author,
        "source_id": case.source_id,
        "chapter_id": case.chapter_id,
        "chapter_title": case.chapter_title,
        "runtime_fixture_ids": [f"{case.chapter_case_id}__warm"],
        "mechanisms": {
            "attentional_v2": {
                "mechanism_label": "Attentional V2",
                "output_dir": f"/tmp/{case.chapter_case_id}/attentional_v2",
                "bundle_summary": {"reaction_count": 3},
            },
            "iterator_v1": {
                "mechanism_label": "Iterator V1",
                "output_dir": f"/tmp/{case.chapter_case_id}/iterator_v1",
                "bundle_summary": {"reaction_count": 2},
            },
        },
        "durable_trace": {
            "winner": "attentional_v2",
            "confidence": "medium",
            "scores": {
                "attentional_v2": {
                    "anchor_traceability": 4,
                    "reaction_reusability": 4,
                    "memory_carryover": 4,
                    "return_path_clarity": 4,
                    "later_value": 4,
                },
                "iterator_v1": {
                    "anchor_traceability": 3,
                    "reaction_reusability": 3,
                    "memory_carryover": 3,
                    "return_path_clarity": 3,
                    "later_value": 3,
                },
            },
            "reason": "Attentional left the stronger trail.",
        },
        "reentry_audits": {
            "warm": {
                "requested_resume_kind": "warm_resume",
                "effective_resume_kind": "warm_resume",
                "compatibility_status": "compatible",
                "compatibility_issues": [],
                "checkpoint_id": "cp-1",
                "resume_window_sentence_count": 0,
                "reconstructed_hot_state": False,
                "current_sentence_id": "c1-s10",
                "span_start_sentence_id": "",
                "span_end_sentence_id": "",
                "target_sentence_index": 12,
            }
        },
    }


def test_run_benchmark_uses_case_subprocess_for_parallel_case_workers(monkeypatch, tmp_path: Path) -> None:
    chapter_dir, runtime_dir, source_manifest, case_ids = _bootstrap_datasets(tmp_path)
    monkeypatch.setattr(durable_trace, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=2))
    dispatched: list[str] = []

    def fake_run_case_subprocess(
        case: durable_trace.ChapterCase,
        *,
        source: dict[str, Any],
        run_root: Path,
        judge_mode: str,
        runtime_fixtures: list[durable_trace.RuntimeFixture],
    ) -> dict[str, Any]:
        assert source["source_id"] == case.source_id
        assert run_root.parent == tmp_path / "runs"
        assert judge_mode == "none"
        assert runtime_fixtures
        dispatched.append(case.chapter_case_id)
        return _case_result(case)

    monkeypatch.setattr(durable_trace, "_run_case_subprocess", fake_run_case_subprocess)
    monkeypatch.setattr(
        durable_trace,
        "_evaluate_case",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("_evaluate_case should not run in-process")),
    )

    summary = durable_trace.run_benchmark(
        chapter_dataset_dirs=[chapter_dir],
        runtime_fixture_dirs=[runtime_dir],
        source_manifest_path=source_manifest,
        runs_root=tmp_path / "runs",
        run_id="demo_durable_parallel",
        judge_mode="none",
        case_ids=case_ids,
        case_workers=2,
    )

    assert set(dispatched) == set(case_ids)
    run_root = Path(summary["run_root"])
    assert (run_root / "cases" / "case_a.json").exists()
    assert (run_root / "cases" / "case_b.json").exists()
    assert (run_root / "summary" / "aggregate.json").exists()
    assert (run_root / "summary" / "report.md").exists()


def test_run_benchmark_keeps_single_worker_case_eval_in_process(monkeypatch, tmp_path: Path) -> None:
    chapter_dir, runtime_dir, source_manifest, case_ids = _bootstrap_datasets(tmp_path)
    monkeypatch.setattr(durable_trace, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))
    evaluated: list[str] = []

    def fake_evaluate_case(
        case: durable_trace.ChapterCase,
        *,
        source: dict[str, Any],
        run_root: Path,
        judge_mode: str,
        runtime_fixtures: list[durable_trace.RuntimeFixture],
    ) -> dict[str, Any]:
        assert source["source_id"] == case.source_id
        assert run_root.parent == tmp_path / "runs"
        assert judge_mode == "none"
        assert runtime_fixtures
        evaluated.append(case.chapter_case_id)
        return _case_result(case)

    monkeypatch.setattr(durable_trace, "_evaluate_case", fake_evaluate_case)
    monkeypatch.setattr(
        durable_trace,
        "_run_case_subprocess",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("_run_case_subprocess should not be used")),
    )

    summary = durable_trace.run_benchmark(
        chapter_dataset_dirs=[chapter_dir],
        runtime_fixture_dirs=[runtime_dir],
        source_manifest_path=source_manifest,
        runs_root=tmp_path / "runs",
        run_id="demo_durable_serial",
        judge_mode="none",
        case_ids=case_ids,
        case_workers=1,
    )

    assert evaluated == case_ids
    run_root = Path(summary["run_root"])
    assert (run_root / "cases" / "case_a.json").exists()
    assert (run_root / "cases" / "case_b.json").exists()


def test_run_benchmark_records_parallel_case_failures_without_aborting(monkeypatch, tmp_path: Path) -> None:
    chapter_dir, runtime_dir, source_manifest, case_ids = _bootstrap_datasets(tmp_path)
    monkeypatch.setattr(durable_trace, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=2))

    def fake_run_case_subprocess(
        case: durable_trace.ChapterCase,
        *,
        source: dict[str, Any],
        run_root: Path,
        judge_mode: str,
        runtime_fixtures: list[durable_trace.RuntimeFixture],
    ) -> dict[str, Any]:
        assert source["source_id"] == case.source_id
        assert run_root.parent == tmp_path / "runs"
        assert judge_mode == "none"
        assert runtime_fixtures
        if case.chapter_case_id == "case_b":
            raise RuntimeError("worker exploded")
        return _case_result(case)

    monkeypatch.setattr(durable_trace, "_run_case_subprocess", fake_run_case_subprocess)

    summary = durable_trace.run_benchmark(
        chapter_dataset_dirs=[chapter_dir],
        runtime_fixture_dirs=[runtime_dir],
        source_manifest_path=source_manifest,
        runs_root=tmp_path / "runs",
        run_id="demo_durable_failure_isolation",
        judge_mode="none",
        case_ids=case_ids,
        case_workers=2,
    )

    aggregate = summary["aggregate"]
    assert aggregate["case_count"] == 2
    assert aggregate["evaluated_case_count"] == 1
    assert aggregate["failed_case_count"] == 1
    assert aggregate["failed_case_ids"] == ["case_b"]
    assert aggregate["case_status_counts"] == {"completed": 1, "runner_error": 1}
    assert aggregate["durable_trace_summary"]["winner_counts"] == {"attentional_v2": 1}
    failed_case = json.loads((Path(summary["run_root"]) / "cases" / "case_b.json").read_text(encoding="utf-8"))
    assert failed_case["case_status"] == "runner_error"
    assert failed_case["case_error"] == "RuntimeError: worker exploded"
    assert failed_case["durable_trace"]["reason"] == "RuntimeError: worker exploded"


def test_aggregate_reports_durable_trace_and_reentry_summaries(tmp_path: Path) -> None:
    chapter_dir, runtime_dir, source_manifest, _ = _bootstrap_datasets(tmp_path)
    manifest = json.loads((chapter_dir / "chapters.jsonl").read_text(encoding="utf-8").splitlines()[0])
    case = durable_trace.ChapterCase(
        chapter_case_id=str(manifest["chapter_case_id"]),
        source_id=str(manifest["source_id"]),
        book_title=str(manifest["book_title"]),
        author=str(manifest["author"]),
        language_track=str(manifest["language_track"]),
        type_tags=[str(item) for item in manifest["type_tags"]],
        role_tags=[str(item) for item in manifest["role_tags"]],
        output_dir=str(manifest["output_dir"]),
        chapter_id=int(manifest["chapter_id"]),
        chapter_title=str(manifest["chapter_title"]),
        sentence_count=int(manifest["sentence_count"]),
        paragraph_count=int(manifest["paragraph_count"]),
        candidate_position_bucket=str(manifest["candidate_position_bucket"]),
        candidate_score=float(manifest["candidate_score"]),
        selection_status=str(manifest["selection_status"]),
        selection_priority=int(manifest["selection_priority"]),
        selection_role=str(manifest["selection_role"]),
        dataset_id="demo_dataset",
        dataset_version="1",
    )

    aggregate = durable_trace._aggregate([_case_result(case)])

    assert aggregate["case_count"] == 1
    assert aggregate["durable_trace_summary"]["winner_counts"]["attentional_v2"] == 1
    assert aggregate["reentry_summary"]["warm"]["compatibility_status_counts"]["compatible"] == 1


def test_run_benchmark_keeps_partial_summary_when_one_case_fails(monkeypatch, tmp_path: Path) -> None:
    chapter_dir, runtime_dir, source_manifest, case_ids = _bootstrap_datasets(tmp_path)
    monkeypatch.setattr(durable_trace, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))

    def fake_evaluate_case(
        case: durable_trace.ChapterCase,
        *,
        source: dict[str, Any],
        run_root: Path,
        judge_mode: str,
        runtime_fixtures: list[durable_trace.RuntimeFixture],
    ) -> dict[str, Any]:
        assert source["source_id"] == case.source_id
        assert run_root.parent == tmp_path / "runs"
        assert judge_mode == "none"
        assert runtime_fixtures
        if case.chapter_case_id == "case_b":
            raise RuntimeError("boom on case_b")
        return _case_result(case)

    monkeypatch.setattr(durable_trace, "_evaluate_case", fake_evaluate_case)
    monkeypatch.setattr(
        durable_trace,
        "_run_case_subprocess",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("_run_case_subprocess should not be used")),
    )

    summary = durable_trace.run_benchmark(
        chapter_dataset_dirs=[chapter_dir],
        runtime_fixture_dirs=[runtime_dir],
        source_manifest_path=source_manifest,
        runs_root=tmp_path / "runs",
        run_id="demo_durable_partial_failure",
        judge_mode="none",
        case_ids=case_ids,
        case_workers=1,
    )

    run_root = Path(summary["run_root"])
    case_b_payload = json.loads((run_root / "cases" / "case_b.json").read_text(encoding="utf-8"))

    assert summary["aggregate"]["case_count"] == 2
    assert summary["aggregate"]["evaluated_case_count"] == 1
    assert summary["aggregate"]["failed_case_count"] == 1
    assert summary["aggregate"]["failed_case_ids"] == ["case_b"]
    assert case_b_payload["case_status"] == "runner_error"
    assert "boom on case_b" in case_b_payload["case_error"]
    assert (run_root / "summary" / "aggregate.json").exists()
    assert (run_root / "summary" / "report.md").exists()
