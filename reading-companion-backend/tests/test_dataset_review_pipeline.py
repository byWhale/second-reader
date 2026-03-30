"""Tests for the reusable dataset-review pipeline runner."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from eval.attentional_v2.run_dataset_review_pipeline import (
    STAGES,
    PipelinePaths,
    build_parser,
    requested_stages,
    resolve_resume_packet,
    run_pipeline,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _bootstrap_dataset(root: Path, *, dataset_id: str = "demo_dataset") -> Path:
    dataset_dir = root / "eval" / "datasets" / "excerpt_cases" / dataset_id
    dataset_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        dataset_dir / "manifest.json",
        {
            "dataset_id": dataset_id,
            "family": "excerpt_cases",
            "language_track": "en",
            "version": "1",
            "primary_file": "cases.jsonl",
        },
    )
    _write_jsonl(
        dataset_dir / "cases.jsonl",
        [
            {
                "case_id": "demo_case_1",
                "benchmark_status": "needs_revision",
                "review_status": "builder_curated",
                "book_title": "Demo Book",
                "author": "Demo Author",
                "chapter_id": "1",
                "chapter_title": "Demo Chapter",
                "question_ids": ["Q1"],
                "phenomena": ["focus"],
                "selection_reason": "Needs a cleanup pass.",
                "judge_focus": "Does the case stay anchored?",
                "excerpt_text": "Demo excerpt.",
            }
        ],
    )
    (root / "eval" / "review_packets" / "pending").mkdir(parents=True, exist_ok=True)
    (root / "eval" / "review_packets" / "archive").mkdir(parents=True, exist_ok=True)
    (root / "eval" / "runs" / "attentional_v2" / "case_audits").mkdir(parents=True, exist_ok=True)
    return dataset_dir


def _packet_manifest(root: Path, *, dataset_id: str, packet_id: str) -> dict[str, object]:
    return {
        "packet_id": packet_id,
        "packet_kind": "revision_replacement",
        "created_at": "2026-03-28T00:00:00Z",
        "dataset_id": dataset_id,
        "family": "excerpt_cases",
        "storage_mode": "tracked",
        "dataset_manifest_path": f"eval/datasets/excerpt_cases/{dataset_id}/manifest.json",
        "dataset_primary_file_path": f"eval/datasets/excerpt_cases/{dataset_id}/cases.jsonl",
        "selection_filters": {
            "statuses": ["needs_revision"],
            "limit": 0,
            "case_ids": ["demo_case_1"],
        },
        "case_count": 1,
        "status_counts": {"needs_revision": 1},
        "import_contract_version": "1",
    }


def _write_review_csv(packet_dir: Path, *, action: str = "") -> None:
    packet_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "case_id,dataset_id,family,storage_mode,language,benchmark_status,review_status,latest_review_action,latest_problem_types,latest_revised_bucket,latest_notes,book_title,author,chapter_id,chapter_title,question_ids,phenomena,selection_reason,judge_focus,excerpt_text,notes,review__action,review__confidence,review__problem_types,review__revised_bucket,review__revised_selection_reason,review__revised_judge_focus,review__notes",
        (
            "demo_case_1,demo_dataset,excerpt_cases,tracked,en,needs_revision,builder_curated,,,,Demo Book,Demo Author,1,Demo Chapter,Q1,focus,"
            "Needs a cleanup pass.,Does the case stay anchored?,Demo excerpt.,,"
            f"{action},high,weak_excerpt,,,,Approved by the fake runner."
        ),
    ]
    (packet_dir / "cases.review.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_pending_packet(root: Path, *, dataset_id: str, packet_id: str) -> Path:
    packet_dir = root / "eval" / "review_packets" / "pending" / packet_id
    packet_dir.mkdir(parents=True, exist_ok=True)
    _write_json(packet_dir / "packet_manifest.json", _packet_manifest(root, dataset_id=dataset_id, packet_id=packet_id))
    _write_review_csv(packet_dir)
    (packet_dir / "cases.preview.md").write_text("# Preview\n", encoding="utf-8")
    _write_jsonl(
        packet_dir / "cases.source.jsonl",
        [
            {
                "case_id": "demo_case_1",
                "benchmark_status": "needs_revision",
                "book_title": "Demo Book",
                "author": "Demo Author",
                "chapter_id": "1",
                "chapter_title": "Demo Chapter",
                "question_ids": ["Q1"],
                "phenomena": ["focus"],
                "selection_reason": "Needs a cleanup pass.",
                "judge_focus": "Does the case stay anchored?",
                "excerpt_text": "Demo excerpt.",
            }
        ],
    )
    (packet_dir / "README.md").write_text("# Packet\n", encoding="utf-8")
    return packet_dir


def _write_completed_audit(root: Path, *, packet_id: str) -> Path:
    run_dir = root / "eval" / "runs" / "attentional_v2" / "case_audits" / f"{packet_id}__20260328-000000"
    (run_dir / "summary").mkdir(parents=True, exist_ok=True)
    (run_dir / "cases").mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "run_state.json",
        {
            "packet_id": packet_id,
            "run_id": run_dir.name,
            "status": "completed",
            "case_count": 1,
            "completed_case_count": 1,
            "failed_case_count": 0,
        },
    )
    _write_json(
        run_dir / "summary" / "aggregate.json",
        {
            "status": "completed",
            "case_count": 1,
            "completed_case_count": 1,
            "failed_case_count": 0,
            "primary_decisions": {"revise": 1},
            "adversarial_risk_counts": {"medium": 1},
            "average_excerpt_strength": 2.0,
        },
    )
    (run_dir / "summary" / "report.md").write_text("# Audit\n", encoding="utf-8")
    _write_json(
        run_dir / "cases" / "demo_case_1.json",
        {
            "case_id": "demo_case_1",
            "status": "completed",
            "factual_audit": {"ok": True},
            "primary_review": {"decision": "revise"},
            "adversarial_review": {"risk_level": "medium"},
        },
    )
    return run_dir


def _write_failed_audit(root: Path, *, packet_id: str) -> Path:
    run_dir = root / "eval" / "runs" / "attentional_v2" / "case_audits" / f"{packet_id}__20260328-000001"
    (run_dir / "summary").mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "run_state.json",
        {
            "packet_id": packet_id,
            "run_id": run_dir.name,
            "status": "failed",
            "case_count": 1,
            "completed_case_count": 0,
            "failed_case_count": 1,
        },
    )
    _write_json(
        run_dir / "summary" / "aggregate.json",
        {
            "status": "failed",
            "case_count": 1,
            "completed_case_count": 0,
            "failed_case_count": 1,
            "primary_decisions": {},
            "adversarial_risk_counts": {},
            "average_excerpt_strength": 0.0,
        },
    )
    (run_dir / "summary" / "report.md").write_text("# Audit Failed\n", encoding="utf-8")
    return run_dir


def _write_adjudication_outputs(packet_dir: Path) -> None:
    _write_review_csv(packet_dir, action="keep")
    _write_json(
        packet_dir / "llm_review_summary.json",
        {
            "packet_id": packet_dir.name,
            "review_origin": "llm",
            "review_policy": "llm_multi_prompt_adjudication_v1",
            "case_count": 1,
            "action_counts": {"keep": 1},
        },
    )
    (packet_dir / "llm_review_report.md").write_text("# Adjudication\n", encoding="utf-8")
    manifest = json.loads((packet_dir / "packet_manifest.json").read_text(encoding="utf-8"))
    manifest["review_origin"] = "llm"
    manifest["review_policy"] = "llm_multi_prompt_adjudication_v1"
    (packet_dir / "packet_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _import_packet(root: Path, *, dataset_id: str, packet_dir: Path) -> Path:
    dataset_path = root / "eval" / "datasets" / "excerpt_cases" / dataset_id / "cases.jsonl"
    before_import = dataset_path.read_text(encoding="utf-8")
    (packet_dir / "dataset_before_import.jsonl").write_text(before_import, encoding="utf-8")
    dataset_rows = [json.loads(line) for line in before_import.splitlines() if line.strip()]
    dataset_rows[0]["benchmark_status"] = "reviewed_active"
    _write_jsonl(dataset_path, dataset_rows)
    _write_json(
        packet_dir / "import_summary.json",
        {
            "packet_id": packet_dir.name,
            "review_origin": "llm",
            "review_policy": "llm_multi_prompt_adjudication_v1",
            "reviewed_case_count": 1,
            "action_counts": {
                "drop": 0,
                "keep": 1,
                "revise": 0,
                "unclear": 0,
            },
        },
    )
    archive_dir = root / "eval" / "review_packets" / "archive" / packet_dir.name
    shutil.move(str(packet_dir), str(archive_dir))
    return archive_dir


def _write_queue_summary(root: Path) -> None:
    _write_json(
        root / "eval" / "review_packets" / "review_queue_summary.json",
        {
            "generated_at": "2026-03-28T00:00:00Z",
            "active_packet_count": 0,
            "packets": [],
        },
    )
    (root / "eval" / "review_packets" / "review_queue_summary.md").write_text("# Queue\n", encoding="utf-8")


def _command_module(command: list[str]) -> str:
    module_index = command.index("-m") + 1
    return command[module_index]


def _arg_value(command: list[str], flag: str) -> str:
    index = command.index(flag)
    return command[index + 1]


class FakePipelineRunner:
    def __init__(self, root: Path, *, dataset_id: str) -> None:
        self.root = root
        self.dataset_id = dataset_id
        self.calls: list[list[str]] = []

    def __call__(self, command: list[str], cwd: Path) -> None:
        assert cwd == self.root
        self.calls.append(command)
        module = _command_module(command)
        if module == "eval.attentional_v2.generate_revision_replacement_packet":
            packet_id = _arg_value(command, "--packet-id")
            _write_pending_packet(self.root, dataset_id=self.dataset_id, packet_id=packet_id)
            return
        if module == "eval.attentional_v2.run_case_design_audit":
            packet_dir = Path(_arg_value(command, "--packet-dir"))
            packet_id = json.loads((packet_dir / "packet_manifest.json").read_text(encoding="utf-8"))["packet_id"]
            _write_completed_audit(self.root, packet_id=str(packet_id))
            return
        if module == "eval.attentional_v2.auto_review_packet":
            packet_dir = Path(_arg_value(command, "--packet-dir"))
            _write_adjudication_outputs(packet_dir)
            return
        if module == "eval.attentional_v2.import_dataset_review_packet":
            packet_dir = Path(_arg_value(command, "--packet-dir"))
            _import_packet(self.root, dataset_id=self.dataset_id, packet_dir=packet_dir)
            return
        if module == "eval.attentional_v2.build_review_queue_summary":
            _write_queue_summary(self.root)
            return
        raise AssertionError(f"Unexpected command: {command}")


def test_requested_stages_rejects_invalid_range() -> None:
    with pytest.raises(ValueError, match="Invalid stage range"):
        requested_stages("adjudicate_packet", "audit_packet")


def test_resolve_resume_packet_supports_packet_id_and_packet_dir(tmp_path: Path) -> None:
    _bootstrap_dataset(tmp_path)
    packet_dir = _write_pending_packet(tmp_path, dataset_id="demo_dataset", packet_id="packet_resume")
    paths = PipelinePaths.from_root(tmp_path)

    packet_id_by_id, resolved_by_id = resolve_resume_packet(paths, packet_id="packet_resume", packet_dir="")
    packet_id_by_dir, resolved_by_dir = resolve_resume_packet(paths, packet_id="", packet_dir=str(packet_dir))

    assert packet_id_by_id == "packet_resume"
    assert resolved_by_id == packet_dir
    assert packet_id_by_dir == "packet_resume"
    assert resolved_by_dir == packet_dir


def test_dry_run_reports_planned_stages_without_mutating(tmp_path: Path) -> None:
    dataset_dir = _bootstrap_dataset(tmp_path)
    cases_before = (dataset_dir / "cases.jsonl").read_text(encoding="utf-8")
    args = build_parser().parse_args(
        [
            "--dataset-id",
            "demo_dataset",
            "--family",
            "excerpt_cases",
            "--storage-mode",
            "tracked",
            "--packet-id",
            "packet_dry_run",
            "--dry-run",
        ]
    )

    payload = run_pipeline(
        args,
        paths=PipelinePaths.from_root(tmp_path),
        command_runner=lambda _command, _cwd: (_ for _ in ()).throw(AssertionError("dry-run should not execute commands")),
    )

    assert payload["status"] == "dry_run_ok"
    assert payload["planned_stages"] == list(STAGES)
    assert not (tmp_path / "eval" / "review_packets" / "pending" / "packet_dry_run").exists()
    assert (dataset_dir / "cases.jsonl").read_text(encoding="utf-8") == cases_before


def test_full_happy_path_over_temp_fixture_tree(tmp_path: Path) -> None:
    _bootstrap_dataset(tmp_path)
    args = build_parser().parse_args(
        [
            "--dataset-id",
            "demo_dataset",
            "--family",
            "excerpt_cases",
            "--storage-mode",
            "tracked",
            "--packet-id",
            "packet_full_run",
        ]
    )
    runner = FakePipelineRunner(tmp_path, dataset_id="demo_dataset")

    payload = run_pipeline(args, paths=PipelinePaths.from_root(tmp_path), command_runner=runner)

    archive_dir = tmp_path / "eval" / "review_packets" / "archive" / "packet_full_run"
    assert payload["status"] == "ok"
    assert payload["executed_stages"] == list(STAGES)
    assert archive_dir.exists()
    assert (archive_dir / "dataset_review_pipeline_summary.json").exists()
    assert payload["action_counts"]["keep"] == 1
    assert payload["post_import_benchmark_status_counts"]["reviewed_active"] == 1
    assert payload["decision_bearing_followup_launched"] is False
    assert [_command_module(command) for command in runner.calls] == [
        "eval.attentional_v2.generate_revision_replacement_packet",
        "eval.attentional_v2.run_case_design_audit",
        "eval.attentional_v2.auto_review_packet",
        "eval.attentional_v2.import_dataset_review_packet",
        "eval.attentional_v2.build_review_queue_summary",
    ]


def test_resume_from_existing_pending_packet(tmp_path: Path) -> None:
    _bootstrap_dataset(tmp_path)
    _write_pending_packet(tmp_path, dataset_id="demo_dataset", packet_id="packet_resume")
    args = build_parser().parse_args(
        [
            "--dataset-id",
            "demo_dataset",
            "--family",
            "excerpt_cases",
            "--storage-mode",
            "tracked",
            "--packet-id",
            "packet_resume",
            "--from-stage",
            "audit_packet",
            "--through-stage",
            "final_summary",
        ]
    )
    runner = FakePipelineRunner(tmp_path, dataset_id="demo_dataset")

    payload = run_pipeline(args, paths=PipelinePaths.from_root(tmp_path), command_runner=runner)

    assert payload["status"] == "ok"
    assert payload["packet_id"] == "packet_resume"
    assert [_command_module(command) for command in runner.calls] == [
        "eval.attentional_v2.run_case_design_audit",
        "eval.attentional_v2.auto_review_packet",
        "eval.attentional_v2.import_dataset_review_packet",
        "eval.attentional_v2.build_review_queue_summary",
    ]


def test_adjudication_fails_without_completed_audit(tmp_path: Path) -> None:
    _bootstrap_dataset(tmp_path)
    _write_pending_packet(tmp_path, dataset_id="demo_dataset", packet_id="packet_needs_audit")
    args = build_parser().parse_args(
        [
            "--dataset-id",
            "demo_dataset",
            "--family",
            "excerpt_cases",
            "--storage-mode",
            "tracked",
            "--packet-id",
            "packet_needs_audit",
            "--from-stage",
            "adjudicate_packet",
            "--through-stage",
            "adjudicate_packet",
        ]
    )

    with pytest.raises(FileNotFoundError, match="completed case audit"):
        run_pipeline(
            args,
            paths=PipelinePaths.from_root(tmp_path),
            command_runner=lambda _command, _cwd: (_ for _ in ()).throw(AssertionError("command runner should not execute")),
        )


def test_failed_audit_does_not_satisfy_completed_audit_requirement(tmp_path: Path) -> None:
    _bootstrap_dataset(tmp_path)
    _write_pending_packet(tmp_path, dataset_id="demo_dataset", packet_id="packet_failed_audit")
    _write_failed_audit(tmp_path, packet_id="packet_failed_audit")
    args = build_parser().parse_args(
        [
            "--dataset-id",
            "demo_dataset",
            "--family",
            "excerpt_cases",
            "--storage-mode",
            "tracked",
            "--packet-id",
            "packet_failed_audit",
            "--from-stage",
            "adjudicate_packet",
            "--through-stage",
            "adjudicate_packet",
        ]
    )

    with pytest.raises(FileNotFoundError, match="completed case audit"):
        run_pipeline(
            args,
            paths=PipelinePaths.from_root(tmp_path),
            command_runner=lambda _command, _cwd: (_ for _ in ()).throw(AssertionError("command runner should not execute")),
        )


def test_import_fails_on_archive_collision(tmp_path: Path) -> None:
    _bootstrap_dataset(tmp_path)
    packet_dir = _write_pending_packet(tmp_path, dataset_id="demo_dataset", packet_id="packet_collision")
    _write_completed_audit(tmp_path, packet_id="packet_collision")
    _write_adjudication_outputs(packet_dir)
    archive_dir = tmp_path / "eval" / "review_packets" / "archive" / "packet_collision"
    archive_dir.mkdir(parents=True, exist_ok=True)
    args = build_parser().parse_args(
        [
            "--dataset-id",
            "demo_dataset",
            "--family",
            "excerpt_cases",
            "--storage-mode",
            "tracked",
            "--packet-dir",
            str(packet_dir),
            "--from-stage",
            "import_packet",
            "--through-stage",
            "import_packet",
        ]
    )

    with pytest.raises(FileExistsError, match="Archive packet already exists"):
        run_pipeline(
            args,
            paths=PipelinePaths.from_root(tmp_path),
            command_runner=lambda _command, _cwd: (_ for _ in ()).throw(AssertionError("command runner should not execute")),
        )


def test_make_dataset_review_pipeline_help_passthrough() -> None:
    workspace_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        ["make", "dataset-review-pipeline", "DATASET_REVIEW_PIPELINE_ARGS=--help"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "run the mechanical dataset-review packet pipeline end to end" in completed.stdout.lower()
