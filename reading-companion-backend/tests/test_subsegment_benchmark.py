"""Tests for the dedicated subsegment benchmark harness."""

from __future__ import annotations

import json
from pathlib import Path
import time

import pytest

from eval.common.taxonomy import (
    DETERMINISTIC_METRICS,
    DIRECT_QUALITY,
    LOCAL_IMPACT,
    PAIRWISE_JUDGE,
    TARGET_SUBSEGMENT_SEGMENTATION,
    normalize_method,
    normalize_scope,
    normalize_scopes,
    validate_target_slug,
)
from eval.subsegment.dataset import load_benchmark_dataset
from eval.subsegment.report import build_markdown_report
from eval.subsegment.run_benchmark import run_benchmark


def _write_dataset(tmp_path: Path) -> Path:
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    (dataset_dir / "manifest.json").write_text(
        json.dumps(
            {
                "dataset_id": "subsegment_benchmark_test",
                "version": "1",
                "description": "test dataset",
                "default_user_intent": "Read carefully.",
                "case_file": "cases.jsonl",
                "core_case_ids": ["core_case"],
                "audit_case_ids": ["audit_case"],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    cases = [
        {
            "case_id": "core_case",
            "split": "core",
            "source": {"kind": "fixture", "path": "fixture.json"},
            "book_title": "Fixture Book",
            "author": "Fixture Author",
            "output_language": "en",
            "chapter_title": "Chapter 1",
            "chapter_ref": "Chapter 1",
            "chapter_index": 1,
            "total_chapters": 1,
            "primary_role": "body",
            "role_tags": [],
            "role_confidence": "medium",
            "section_heading": "",
            "nearby_outline": [],
            "segment_id": "1.1",
            "segment_ref": "1.1",
            "segment_summary": "Core summary",
            "segment_text": "Alpha. Beta.",
            "tags": ["core"],
            "notes": "core case",
        },
        {
            "case_id": "audit_case",
            "split": "audit",
            "source": {"kind": "fixture", "path": "fixture.json"},
            "book_title": "Fixture Book",
            "author": "Fixture Author",
            "output_language": "en",
            "chapter_title": "Chapter 1",
            "chapter_ref": "Chapter 1",
            "chapter_index": 1,
            "total_chapters": 1,
            "primary_role": "body",
            "role_tags": [],
            "role_confidence": "medium",
            "section_heading": "",
            "nearby_outline": [],
            "segment_id": "1.2",
            "segment_ref": "1.2",
            "segment_summary": "Audit summary",
            "segment_text": "Gamma. Delta.",
            "tags": ["audit"],
            "notes": "audit case",
        },
    ]
    (dataset_dir / "cases.jsonl").write_text(
        "\n".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) for item in cases) + "\n",
        encoding="utf-8",
    )
    return dataset_dir


def _direct_plan_result(case_id: str, strategy: str) -> tuple[list[dict[str, object]], dict[str, object]]:
    if strategy == "heuristic_only":
        plan = [
            {"summary": "Heuristic part 1", "text": "Alpha.", "sentence_start": 1, "sentence_end": 1},
            {"summary": "Heuristic part 2", "text": "Beta.", "sentence_start": 2, "sentence_end": 2},
        ]
        planner_source = "fallback"
        diagnostics = {
            "strategy_requested": "heuristic_only",
            "planner_status": "forced_heuristic",
            "planner_failure_reason": "strategy_override",
            "validation_status": "not_run",
            "planner_payload": {},
            "materialized_unit_count": 2,
        }
    else:
        plan = [{"summary": "LLM unit", "text": "Alpha. Beta.", "sentence_start": 1, "sentence_end": 2}]
        planner_source = "llm"
        diagnostics = {
            "strategy_requested": "llm_primary",
            "planner_attempted": True,
            "planner_status": "ok",
            "planner_failure_reason": "",
            "validation_status": "ok",
            "planner_payload": {"units": []},
            "materialized_unit_count": 1,
        }
    final_state = {
        "segment_id": case_id,
        "subsegment_plan": plan,
        "subsegment_planner_source": planner_source,
        "subsegment_plan_diagnostics": diagnostics,
        "budget": {"segment_timed_out": False},
    }
    return plan, final_state


def test_validate_target_slug_accepts_snake_case():
    assert validate_target_slug(TARGET_SUBSEGMENT_SEGMENTATION) == TARGET_SUBSEGMENT_SEGMENTATION
    assert normalize_scope(DIRECT_QUALITY) == DIRECT_QUALITY
    assert normalize_method(PAIRWISE_JUDGE) == PAIRWISE_JUDGE
    assert normalize_scopes([DIRECT_QUALITY, LOCAL_IMPACT, DIRECT_QUALITY]) == [DIRECT_QUALITY, LOCAL_IMPACT]


def test_validate_target_slug_rejects_invalid_values():
    with pytest.raises(ValueError):
        validate_target_slug("Subsegment Segmentation")


def test_load_benchmark_dataset_reads_manifest_and_cases(tmp_path: Path):
    """The curated benchmark dataset should load split metadata and cases together."""
    dataset = load_benchmark_dataset(_write_dataset(tmp_path))

    assert dataset.dataset_id == "subsegment_benchmark_test"
    assert dataset.core_case_ids == ["core_case"]
    assert dataset.audit_case_ids == ["audit_case"]
    assert [case.case_id for case in dataset.cases] == ["core_case", "audit_case"]


def test_build_markdown_report_summarizes_scopes():
    """The checked-in benchmark report should expose the taxonomy fields and scope headings."""
    markdown = build_markdown_report(
        dataset_id="subsegment_benchmark_test",
        dataset_version="1",
        target=TARGET_SUBSEGMENT_SEGMENTATION,
        scopes=[DIRECT_QUALITY, LOCAL_IMPACT],
        methods=[DETERMINISTIC_METRICS, PAIRWISE_JUDGE],
        comparison_target="heuristic_only vs llm_primary",
        rubric_summary_by_scope={
            DIRECT_QUALITY: ["direct rubric"],
            LOCAL_IMPACT: ["impact rubric"],
        },
        aggregate={
            "case_count": 2,
            "core_case_count": 1,
            "audit_case_count": 1,
            "dataset_case_count": 2,
            "scope_metrics": {
                DIRECT_QUALITY: {
                    "case_count": 2,
                    "llm_fallback_rate": 0.5,
                    "llm_invalid_plan_rate": 0.0,
                    "llm_failure_rate": 0.0,
                    "heuristic_failure_rate": 0.0,
                    "heuristic_avg_unit_count": 2.0,
                    "llm_avg_unit_count": 1.5,
                },
                LOCAL_IMPACT: {
                    "case_count": 2,
                    "llm_fallback_rate": 0.0,
                    "llm_invalid_plan_rate": 0.0,
                    "llm_failure_rate": 0.0,
                    "heuristic_failure_rate": 0.0,
                    "heuristic_avg_unit_count": 2.0,
                    "llm_avg_unit_count": 1.5,
                },
            },
        },
        case_results=[
            {
                "case_id": "core_case",
                "segment_ref": "1.1",
                "scope_results": {
                    DIRECT_QUALITY: {"judgment": {"winner": "llm_primary", "reason": "better direct quality"}},
                    LOCAL_IMPACT: {"judgment": {"winner": "heuristic_only", "reason": "better local impact"}},
                },
            },
            {
                "case_id": "audit_case",
                "segment_ref": "1.2",
                "scope_results": {
                    DIRECT_QUALITY: {"judgment": {"winner": "heuristic_only", "reason": "better direct quality"}},
                    LOCAL_IMPACT: {"judgment": {"winner": "tie", "reason": "roughly equal"}},
                },
            },
        ],
    )

    assert "Target: `subsegment_segmentation`" in markdown
    assert "Scope: `direct_quality`, `local_impact`" in markdown
    assert "Method: `deterministic_metrics`, `pairwise_judge`" in markdown
    assert "## Direct Quality (subsegment slicing)" in markdown


def test_run_benchmark_preserves_case_order_when_parallel_workers_finish_out_of_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dataset_dir = _write_dataset(tmp_path)

    def fake_plan_reader_subsegments(state):  # noqa: ANN001
        strategy = state.get("subsegment_strategy_override") or "llm_primary"
        if state.get("segment_id") == "core_case" and strategy == "heuristic_only":
            time.sleep(0.15)
        return _direct_plan_result(state.get("segment_id", ""), strategy)

    monkeypatch.setattr("eval.subsegment.run_benchmark.plan_reader_subsegments", fake_plan_reader_subsegments)
    monkeypatch.setattr(
        "eval.subsegment.run_benchmark.judge_plan_pairwise",
        lambda **_: {"winner": "llm_primary", "reason": "ok"},
    )

    summary = run_benchmark(
        dataset_dir=dataset_dir,
        runs_root=tmp_path / "runs",
        include_local_impact=False,
    )

    assert [item["case_id"] for item in summary["case_results"]] == ["core_case", "audit_case"]


def test_run_benchmark_defaults_to_direct_quality_only(tmp_path: Path, monkeypatch):
    """Default runs should evaluate direct slicing quality without invoking full downstream reader execution."""
    dataset_dir = _write_dataset(tmp_path)
    runs_root = tmp_path / "runs"
    report_path = tmp_path / "report.md"

    def fake_plan_reader_subsegments(state):  # noqa: ANN001
        strategy = state.get("subsegment_strategy_override") or "llm_primary"
        return _direct_plan_result(state["segment_id"], str(strategy))

    def fail_run_reader_segment(state, progress=None):  # noqa: ANN001
        raise AssertionError("run_reader_segment should not be called for direct_quality-only runs")

    monkeypatch.setattr("eval.subsegment.run_benchmark.plan_reader_subsegments", fake_plan_reader_subsegments)
    monkeypatch.setattr("eval.subsegment.run_benchmark.run_reader_segment", fail_run_reader_segment)

    summary = run_benchmark(
        dataset_dir=dataset_dir,
        runs_root=runs_root,
        report_path=report_path,
        run_id="direct-only-run",
        judge_mode="llm",
        direct_judge=lambda **_kwargs: {"winner": "llm_primary", "reason": "better direct quality"},
    )

    run_root = Path(summary["run_root"])
    manifest = json.loads((run_root / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert summary["aggregate"]["target"] == TARGET_SUBSEGMENT_SEGMENTATION
    assert summary["aggregate"]["scopes"] == [DIRECT_QUALITY]
    assert summary["aggregate"]["methods"] == [DETERMINISTIC_METRICS, PAIRWISE_JUDGE]
    assert manifest["scopes"] == [DIRECT_QUALITY]
    assert (run_root / DIRECT_QUALITY / "plans" / "core_case.llm_primary.json").exists()
    assert (run_root / DIRECT_QUALITY / "judge" / "core_case.json").exists()
    assert not (run_root / LOCAL_IMPACT).exists()
    assert report_path.exists()
    assert not (tmp_path / "output").exists()
    assert not (tmp_path / "state").exists()


def test_run_benchmark_optional_local_impact_runs_downstream(tmp_path: Path, monkeypatch):
    """Local-impact runs should execute the section-level comparison path only when explicitly requested."""
    dataset_dir = _write_dataset(tmp_path)

    def fake_plan_reader_subsegments(state):  # noqa: ANN001
        strategy = state.get("subsegment_strategy_override") or "llm_primary"
        return _direct_plan_result(state["segment_id"], str(strategy))

    def fake_run_reader_segment(state, progress=None):  # noqa: ANN001
        strategy = state.get("subsegment_strategy_override") or "llm_primary"
        plan, final_state = _direct_plan_result(state["segment_id"], str(strategy))
        final_state["budget"] = {"segment_timed_out": False}
        rendered = {
            "segment_id": state["segment_id"],
            "summary": state["segment_summary"],
            "verdict": "pass",
            "reactions": [
                {
                    "type": "highlight",
                    "anchor_quote": plan[0]["text"],
                    "content": f"note::{strategy}",
                    "search_results": [],
                }
            ],
            "reflection_summary": f"summary::{strategy}",
            "reflection_reason_codes": ["OTHER"],
        }
        return rendered, final_state

    monkeypatch.setattr("eval.subsegment.run_benchmark.plan_reader_subsegments", fake_plan_reader_subsegments)
    monkeypatch.setattr("eval.subsegment.run_benchmark.run_reader_segment", fake_run_reader_segment)

    summary = run_benchmark(
        dataset_dir=dataset_dir,
        runs_root=tmp_path / "runs",
        report_path=tmp_path / "report.md",
        run_id="local-impact-run",
        judge_mode="llm",
        include_local_impact=True,
        direct_judge=lambda **_kwargs: {"winner": "llm_primary", "reason": "better direct quality"},
        local_impact_judge=lambda **_kwargs: {"winner": "llm_primary", "reason": "better local impact"},
    )

    run_root = Path(summary["run_root"])
    assert summary["aggregate"]["scopes"] == [DIRECT_QUALITY, LOCAL_IMPACT]
    assert (run_root / LOCAL_IMPACT / "sections" / "core_case.llm_primary.json").exists()
    assert (run_root / LOCAL_IMPACT / "judge" / "core_case.json").exists()


def test_run_benchmark_case_ids_override_order_and_limit(tmp_path: Path, monkeypatch):
    """Explicit case_ids should override split/limit selection and preserve the requested order."""
    dataset_dir = _write_dataset(tmp_path)

    def fake_plan_reader_subsegments(state):  # noqa: ANN001
        strategy = state.get("subsegment_strategy_override") or "llm_primary"
        return _direct_plan_result(state["segment_id"], str(strategy))

    monkeypatch.setattr("eval.subsegment.run_benchmark.plan_reader_subsegments", fake_plan_reader_subsegments)

    summary = run_benchmark(
        dataset_dir=dataset_dir,
        runs_root=tmp_path / "runs",
        run_id="case-order-run",
        report_path=tmp_path / "runs" / "case-order-run" / "summary" / "report.md",
        case_ids=["audit_case", "core_case"],
        core_only=True,
        limit=1,
        judge_mode="none",
    )

    assert summary["aggregate"]["selected_case_ids"] == ["audit_case", "core_case"]
    assert summary["aggregate"]["case_ids"] == ["audit_case", "core_case"]


def test_run_benchmark_case_ids_reject_unknown_ids(tmp_path: Path):
    """Explicit case selection should fail fast on unknown case ids."""
    dataset_dir = _write_dataset(tmp_path)

    with pytest.raises(ValueError, match="unknown benchmark case ids"):
        run_benchmark(
            dataset_dir=dataset_dir,
            runs_root=tmp_path / "runs",
            case_ids=["missing_case"],
            judge_mode="none",
        )


def test_run_benchmark_timeout_override_is_recorded(tmp_path: Path, monkeypatch):
    """The eval-only timeout override should flow into manifest and aggregate outputs."""
    dataset_dir = _write_dataset(tmp_path)

    def fake_plan_reader_subsegments(state):  # noqa: ANN001
        strategy = state.get("subsegment_strategy_override") or "llm_primary"
        _, final_state = _direct_plan_result(state["segment_id"], str(strategy))
        final_state["budget"] = {"segment_timed_out": False, "segment_timeout_seconds": 120}
        return final_state["subsegment_plan"], final_state

    monkeypatch.setattr("eval.subsegment.run_benchmark.plan_reader_subsegments", fake_plan_reader_subsegments)

    summary = run_benchmark(
        dataset_dir=dataset_dir,
        runs_root=tmp_path / "runs",
        run_id="timeout-run",
        segment_timeout_seconds=120,
        judge_mode="none",
    )

    run_root = Path(summary["run_root"])
    manifest = json.loads((run_root / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert manifest["segment_timeout_seconds"] == 120
    assert summary["aggregate"]["segment_timeout_seconds"] == 120


def test_run_benchmark_runtime_first_default_report_path(tmp_path: Path, monkeypatch):
    """Default report output should stay under the run directory summary path."""
    dataset_dir = _write_dataset(tmp_path)

    def fake_plan_reader_subsegments(state):  # noqa: ANN001
        strategy = state.get("subsegment_strategy_override") or "llm_primary"
        return _direct_plan_result(state["segment_id"], str(strategy))

    monkeypatch.setattr("eval.subsegment.run_benchmark.plan_reader_subsegments", fake_plan_reader_subsegments)

    summary = run_benchmark(
        dataset_dir=dataset_dir,
        runs_root=tmp_path / "runs",
        run_id="runtime-first-run",
        judge_mode="none",
    )

    assert summary["report_path"].endswith("runtime-first-run/summary/report.md")
    assert Path(summary["report_path"]).exists()


def test_run_benchmark_scope_selection_can_run_local_impact_only(tmp_path: Path, monkeypatch):
    """Explicit scope selection should allow a clean local-impact-only run."""
    dataset_dir = _write_dataset(tmp_path)

    def fake_run_reader_segment(state, progress=None):  # noqa: ANN001
        strategy = state.get("subsegment_strategy_override") or "llm_primary"
        plan, final_state = _direct_plan_result(state["segment_id"], str(strategy))
        final_state["budget"] = {"segment_timed_out": False}
        rendered = {
            "segment_id": state["segment_id"],
            "summary": state["segment_summary"],
            "verdict": "pass",
            "reactions": [
                {
                    "type": "highlight",
                    "anchor_quote": plan[0]["text"],
                    "content": f"note::{strategy}",
                    "search_results": [],
                }
            ],
            "reflection_summary": f"summary::{strategy}",
            "reflection_reason_codes": ["OTHER"],
        }
        return rendered, final_state

    def fail_plan_reader_subsegments(state):  # noqa: ANN001
        raise AssertionError("plan_reader_subsegments should not be called for local_impact-only runs")

    monkeypatch.setattr("eval.subsegment.run_benchmark.run_reader_segment", fake_run_reader_segment)
    monkeypatch.setattr("eval.subsegment.run_benchmark.plan_reader_subsegments", fail_plan_reader_subsegments)

    summary = run_benchmark(
        dataset_dir=dataset_dir,
        runs_root=tmp_path / "runs",
        run_id="local-only-run",
        scopes=[LOCAL_IMPACT],
        judge_mode="none",
    )

    run_root = Path(summary["run_root"])
    assert summary["aggregate"]["scopes"] == [LOCAL_IMPACT]
    assert not (run_root / DIRECT_QUALITY).exists()
    assert (run_root / LOCAL_IMPACT / "sections" / "core_case.llm_primary.json").exists()


def test_run_benchmark_records_invalid_plan_fallback(tmp_path: Path, monkeypatch):
    """The harness should preserve invalid-plan fallback evidence in direct-quality artifacts."""
    dataset_dir = _write_dataset(tmp_path)

    def fake_plan_reader_subsegments(state):  # noqa: ANN001
        strategy = state.get("subsegment_strategy_override") or "llm_primary"
        diagnostics = {
            "strategy_requested": strategy,
            "planner_attempted": strategy == "llm_primary",
            "planner_status": "ok" if strategy == "llm_primary" else "forced_heuristic",
            "planner_failure_reason": "invalid_reading_move" if strategy == "llm_primary" else "strategy_override",
            "validation_status": "invalid_reading_move" if strategy == "llm_primary" else "not_run",
            "planner_payload": {"units": []},
            "materialized_unit_count": 2,
        }
        final_state = {
            "segment_id": state["segment_id"],
            "subsegment_plan": [{"summary": "Fallback", "text": "Alpha."}, {"summary": "Fallback", "text": "Beta."}],
            "subsegment_planner_source": "fallback",
            "subsegment_plan_diagnostics": diagnostics,
            "budget": {"segment_timed_out": False},
        }
        return final_state["subsegment_plan"], final_state

    monkeypatch.setattr("eval.subsegment.run_benchmark.plan_reader_subsegments", fake_plan_reader_subsegments)

    summary = run_benchmark(
        dataset_dir=dataset_dir,
        runs_root=tmp_path / "runs",
        report_path=tmp_path / "report.md",
        run_id="invalid-plan-run",
        judge_mode="none",
    )

    assert summary["aggregate"]["scope_metrics"][DIRECT_QUALITY]["llm_invalid_plan_rate"] == 1.0
