"""Tests for the first closed-loop benchmark-curation runner."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from eval.attentional_v2.run_closed_loop_benchmark_curation import (
    ClosedLoopPaths,
    build_parser,
    planned_stages,
    run_closed_loop,
)
from eval.attentional_v2.run_dataset_review_pipeline import SUMMARY_JSON_NAME as REPAIR_SUMMARY_JSON_NAME


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _module_name(command: list[str]) -> str:
    return command[command.index("-m") + 1]


def _arg_value(command: list[str], flag: str) -> str:
    return command[command.index(flag) + 1]


def _scratch_excerpt_dataset_id(language: str, run_id: str) -> str:
    return f"attentional_v2_private_library_excerpt_{language}_question_aligned_v1__scratch__{run_id}"


def _builder_runner_factory(root: Path):
    def builder_runner(options) -> dict[str, object]:
        dataset_ids = {
            "en": _scratch_excerpt_dataset_id("en", options.run_id),
            "zh": _scratch_excerpt_dataset_id("zh", options.run_id),
        }
        for language, dataset_id in dataset_ids.items():
            dataset_dir = root / "state" / "eval_local_datasets" / "excerpt_cases" / dataset_id
            _write_json(
                dataset_dir / "manifest.json",
                {
                    "dataset_id": dataset_id,
                    "family": "excerpt_cases",
                    "language_track": language,
                    "primary_file": "cases.jsonl",
                    "storage_mode": "local-only",
                },
            )
            _write_jsonl(
                dataset_dir / "cases.jsonl",
                [
                    {
                        "case_id": f"{language}_case_1",
                        "benchmark_status": "unset",
                        "review_status": "builder_curated",
                        "output_language": language,
                        "book_title": f"Book {language}",
                        "author": "Author",
                        "chapter_id": "1",
                        "chapter_title": "Chapter 1",
                        "question_ids": ["Q1"],
                        "phenomena": ["focus"],
                        "selection_reason": "Builder seed.",
                        "judge_focus": "Judge it.",
                        "excerpt_text": "Example excerpt.",
                    }
                ],
            )
        return {
            "scratch": bool(options.scratch),
            "run_id": options.run_id,
            "dataset_ids": {"excerpt_cases": dataset_ids},
        }

    return builder_runner


class FakeClosedLoopRunner:
    def __init__(self, root: Path, *, initial_import_status: str, create_variability_warning: bool = False) -> None:
        self.root = root
        self.initial_import_status = initial_import_status
        self.create_variability_warning = create_variability_warning
        self.calls: list[list[str]] = []

    def __call__(self, command: list[str], cwd: Path) -> None:
        assert cwd == self.root
        self.calls.append(command)
        module = _module_name(command)
        if module == "eval.attentional_v2.export_dataset_review_packet":
            dataset_id = _arg_value(command, "--dataset-id")
            packet_id = _arg_value(command, "--packet-id")
            packet_dir = self.root / "eval" / "review_packets" / "pending" / packet_id
            _write_json(
                packet_dir / "packet_manifest.json",
                {
                    "packet_id": packet_id,
                    "dataset_id": dataset_id,
                    "family": "excerpt_cases",
                    "storage_mode": "local-only",
                },
            )
            return
        if module == "eval.attentional_v2.run_case_design_audit":
            return
        if module == "eval.attentional_v2.auto_review_packet":
            packet_dir = Path(_arg_value(command, "--packet-dir"))
            packet_id = packet_dir.name
            base_summary = {
                "packet_id": packet_id,
                "run_id": f"{packet_id}__llm_review__demo_a",
                "review_policy": "llm_multi_prompt_adjudication_v1",
                "adjudication_contract_version": "packet_adjudication_rubric_v2",
                "adjudication_input_fingerprint": "same-packet-input",
                "action_counts": {"keep": 1},
            }
            _write_json(packet_dir / "llm_review_summary.json", base_summary)
            (packet_dir / "llm_review_report.md").write_text("# LLM Review\n", encoding="utf-8")
            _write_json(
                packet_dir / "llm_review_runs" / base_summary["run_id"] / "summary.json",
                base_summary,
            )
            _write_json(
                packet_dir / "llm_review_runs" / base_summary["run_id"] / "cases" / "demo_case.json",
                {
                    "case_id": "demo_case",
                    "adjudication_input_fingerprint": "same-case-input",
                    "source_row_fingerprint": "same-source",
                    "audit_row_fingerprint": "audit-a",
                    "normalized_review": {
                        "review__action": "keep",
                        "review__confidence": "high",
                        "review__problem_types": ["other"],
                    },
                    "provider_id": "MiniMax-M2.7-highspeed",
                    "selected_target_id": "MiniMax-M2.7-highspeed",
                    "selected_tier_id": "primary",
                    "key_slot_id": "primary",
                },
            )
            if self.create_variability_warning:
                varied_summary = {
                    **base_summary,
                    "run_id": f"{packet_id}__llm_review__demo_b",
                    "adjudication_input_fingerprint": "different-packet-input",
                    "action_counts": {"revise": 1},
                }
                _write_json(
                    packet_dir / "llm_review_runs" / varied_summary["run_id"] / "summary.json",
                    varied_summary,
                )
                _write_json(
                    packet_dir / "llm_review_runs" / varied_summary["run_id"] / "cases" / "demo_case.json",
                    {
                        "case_id": "demo_case",
                        "adjudication_input_fingerprint": "different-case-input",
                        "source_row_fingerprint": "same-source",
                        "audit_row_fingerprint": "audit-b",
                        "normalized_review": {
                            "review__action": "revise",
                            "review__confidence": "medium",
                            "review__problem_types": ["weak_excerpt"],
                        },
                        "provider_id": "MiniMax-M2.7-highspeed",
                        "selected_target_id": "MiniMax-M2.7-highspeed",
                        "selected_tier_id": "primary",
                        "key_slot_id": "primary",
                    },
                )
            return
        if module == "eval.attentional_v2.import_dataset_review_packet":
            packet_dir = Path(_arg_value(command, "--packet-dir"))
            packet_manifest = json.loads((packet_dir / "packet_manifest.json").read_text(encoding="utf-8"))
            dataset_id = str(packet_manifest["dataset_id"])
            dataset_path = (
                self.root / "state" / "eval_local_datasets" / "excerpt_cases" / dataset_id / "cases.jsonl"
            )
            rows = [
                json.loads(line)
                for line in dataset_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            rows[0]["benchmark_status"] = self.initial_import_status
            _write_jsonl(dataset_path, rows)
            _write_json(
                packet_dir / "import_summary.json",
                {
                    "packet_id": packet_manifest["packet_id"],
                    "action_counts": {"keep": 1, "revise": 0, "drop": 0, "unclear": 0},
                },
            )
            archive_dir = self.root / "eval" / "review_packets" / "archive" / packet_dir.name
            archive_dir.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(packet_dir), str(archive_dir))
            return
        if module == "eval.attentional_v2.run_dataset_review_pipeline":
            dataset_id = _arg_value(command, "--dataset-id")
            packet_id = _arg_value(command, "--packet-id")
            dataset_path = (
                self.root / "state" / "eval_local_datasets" / "excerpt_cases" / dataset_id / "cases.jsonl"
            )
            rows = [
                json.loads(line)
                for line in dataset_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            rows[0]["benchmark_status"] = "reviewed_active"
            _write_jsonl(dataset_path, rows)
            archive_dir = self.root / "eval" / "review_packets" / "archive" / packet_id
            _write_json(
                archive_dir / REPAIR_SUMMARY_JSON_NAME,
                {
                    "packet_id": packet_id,
                    "action_counts": {"keep": 0, "revise": 1, "drop": 0, "unclear": 0},
                },
            )
            return
        if module == "eval.attentional_v2.build_review_queue_summary":
            _write_json(
                self.root / "eval" / "review_packets" / "review_queue_summary.json",
                {"active_packet_count": 0, "packets": []},
            )
            (self.root / "eval" / "review_packets" / "review_queue_summary.md").write_text(
                "# Queue\n",
                encoding="utf-8",
            )
            return
        raise AssertionError(f"Unexpected command: {command}")


def test_planned_stages_skip_repair_by_default() -> None:
    assert planned_stages(None, None, include_repair=False) == [
        "construct_dataset",
        "export_review_packets",
        "audit_packets",
        "adjudicate_packets",
        "import_packets",
        "refresh_queue_summary",
        "final_summary",
    ]


def test_run_closed_loop_dry_run_reports_planned_command(tmp_path: Path) -> None:
    args = build_parser().parse_args(["--run-id", "demo", "--dry-run"])
    payload = run_closed_loop(args, paths=ClosedLoopPaths.from_root(tmp_path, "demo"))

    assert payload["status"] == "dry_run_ok"
    assert payload["run_id"] == "demo"
    assert payload["planned_stages"][-1] == "final_summary"
    assert "build_private_library_supplement" in payload["builder_command"]


def test_run_closed_loop_supports_partial_stage_ranges_without_final_summary(tmp_path: Path) -> None:
    args = build_parser().parse_args(
        ["--run-id", "demo_partial", "--through-stage", "export_review_packets"]
    )
    paths = ClosedLoopPaths.from_root(tmp_path, "demo_partial")
    runner = FakeClosedLoopRunner(tmp_path, initial_import_status="reviewed_active")

    payload = run_closed_loop(
        args,
        paths=paths,
        command_runner=runner,
        builder_runner=_builder_runner_factory(tmp_path),
    )

    assert payload["status"] == "ok"
    assert payload["executed_stages"] == ["construct_dataset", "export_review_packets"]
    assert payload["dataset_ids"]["en"] == _scratch_excerpt_dataset_id("en", "demo_partial")
    assert payload["initial_packet_ids_by_language"]["en"].endswith("__initial_review__demo_partial")
    assert not paths.summary_json.exists()


def test_run_closed_loop_full_happy_path_writes_summary(tmp_path: Path) -> None:
    args = build_parser().parse_args(["--run-id", "demo_full"])
    paths = ClosedLoopPaths.from_root(tmp_path, "demo_full")
    runner = FakeClosedLoopRunner(tmp_path, initial_import_status="reviewed_active")

    payload = run_closed_loop(
        args,
        paths=paths,
        command_runner=runner,
        builder_runner=_builder_runner_factory(tmp_path),
    )

    assert paths.summary_json.exists()
    summary = json.loads(paths.summary_json.read_text(encoding="utf-8"))
    assert payload["decision_bearing_followup_launched"] is False
    assert summary["executed_stages"][-1] == "final_summary"
    assert summary["post_import_benchmark_status_counts_by_language"]["en"]["reviewed_active"] == 1
    assert summary["post_import_benchmark_status_counts_by_language"]["zh"]["reviewed_active"] == 1
    assert summary["repair_packet_ids_by_language"] == {}
    assert summary["initial_adjudication_input_fingerprints_by_language"]["en"] == "same-packet-input"
    assert summary["variability_guard_triggered"] is False
    assert any(_module_name(command) == "eval.attentional_v2.export_dataset_review_packet" for command in runner.calls)


def test_run_closed_loop_repair_stage_invokes_dataset_review_pipeline_when_backlog_exists(
    tmp_path: Path,
) -> None:
    args = build_parser().parse_args(["--run-id", "demo_repair", "--repair-open-backlog"])
    paths = ClosedLoopPaths.from_root(tmp_path, "demo_repair")
    runner = FakeClosedLoopRunner(tmp_path, initial_import_status="needs_revision")

    payload = run_closed_loop(
        args,
        paths=paths,
        command_runner=runner,
        builder_runner=_builder_runner_factory(tmp_path),
    )

    assert payload["repair_packet_ids_by_language"]["en"].endswith("__repair__demo_repair")
    assert any(
        _module_name(command) == "eval.attentional_v2.run_dataset_review_pipeline"
        for command in runner.calls
    )
    assert payload["executed_stages"] == [
        "construct_dataset",
        "export_review_packets",
        "audit_packets",
        "adjudicate_packets",
        "import_packets",
        "repair_open_backlog",
        "refresh_queue_summary",
        "final_summary",
    ]
    assert payload["post_import_benchmark_status_counts_by_language"]["en"]["reviewed_active"] == 1


def test_run_closed_loop_resuming_final_summary_does_not_duplicate_stage_history(tmp_path: Path) -> None:
    paths = ClosedLoopPaths.from_root(tmp_path, "demo_resume")
    runner = FakeClosedLoopRunner(tmp_path, initial_import_status="reviewed_active")

    first_args = build_parser().parse_args(["--run-id", "demo_resume"])
    run_closed_loop(
        first_args,
        paths=paths,
        command_runner=runner,
        builder_runner=_builder_runner_factory(tmp_path),
    )

    resume_args = build_parser().parse_args(
        ["--run-id", "demo_resume", "--from-stage", "final_summary", "--through-stage", "final_summary"]
    )
    payload = run_closed_loop(
        resume_args,
        paths=paths,
        command_runner=runner,
        builder_runner=_builder_runner_factory(tmp_path),
    )

    assert payload["executed_stages"].count("final_summary") == 1


def test_run_closed_loop_surfaces_adjudication_variability_warning(tmp_path: Path) -> None:
    args = build_parser().parse_args(["--run-id", "demo_variability"])
    paths = ClosedLoopPaths.from_root(tmp_path, "demo_variability")
    runner = FakeClosedLoopRunner(tmp_path, initial_import_status="reviewed_active", create_variability_warning=True)

    payload = run_closed_loop(
        args,
        paths=paths,
        command_runner=runner,
        builder_runner=_builder_runner_factory(tmp_path),
    )

    assert payload["variability_guard_triggered"] is True
    assert payload["initial_adjudication_variability_warnings_by_language"]["en"][0]["drift_counts"]["action_drift"] == 1
    assert payload["initial_adjudication_variability_warnings_by_language"]["en"][0]["same_packet_input_fingerprint"] is False
