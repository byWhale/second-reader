from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "orchestrate_active_benchmark_eval.py"
SPEC = importlib.util.spec_from_file_location("active_benchmark_orchestrator", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
orchestrator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = orchestrator
SPEC.loader.exec_module(orchestrator)


def test_shell_command_for_python_quotes_script_and_args() -> None:
    command = orchestrator._shell_command_for_python(
        Path("/tmp/demo script.py"),
        ["--run-id", "demo run", "--target-id", "MiniMax-M2.7-personal"],
    )

    assert "'/tmp/demo script.py'" in command
    assert "'demo run'" in command


def test_ensure_child_job_running_launches_when_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(orchestrator, "_job_status", lambda _job_id: None)
    launches: list[str] = []

    def _fake_launch(**kwargs):
        launches.append(kwargs["job_id"])
        return {"status": "launched", "job_id": kwargs["job_id"]}

    monkeypatch.setattr(orchestrator, "_launch_child_job", _fake_launch)

    payload = orchestrator._ensure_child_job_running(
        job_id="bgjob_demo",
        task_ref="TASK-USER-LEVEL-SELECTIVE-V1",
        purpose="demo",
        command_text="python demo.py",
        run_dir=tmp_path / "run",
        expected_outputs=[tmp_path / "run" / "summary" / "aggregate.json"],
        aggregate_path=tmp_path / "run" / "summary" / "aggregate.json",
        report_path=tmp_path / "run" / "summary" / "report.md",
        mechanism_keys=("attentional_v2", "iterator_v1"),
        count_key="note_case_count",
    )

    assert launches == ["bgjob_demo"]
    assert payload["status"] == "launched"


def test_ensure_child_job_running_relaunches_failed_job(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(orchestrator, "_job_status", lambda _job_id: {"status": "failed"})
    relaunched: list[str] = []
    monkeypatch.setattr(
        orchestrator,
        "relaunch_background_job",
        lambda job_id, **kwargs: relaunched.append(job_id) or {"status": "relaunched", "job_id": job_id},
    )

    payload = orchestrator._ensure_child_job_running(
        job_id="bgjob_demo",
        task_ref="TASK-ACCUMULATION-BENCHMARK-V2",
        purpose="demo",
        command_text="python demo.py",
        run_dir=tmp_path / "run",
        expected_outputs=[tmp_path / "run" / "summary" / "aggregate.json"],
        aggregate_path=tmp_path / "run" / "summary" / "aggregate.json",
        report_path=tmp_path / "run" / "summary" / "report.md",
        mechanism_keys=("attentional_v2", "iterator_v1"),
        count_key="case_count",
    )

    assert relaunched == ["bgjob_demo"]
    assert payload["status"] == "relaunched"


def test_wait_for_child_registration_tolerates_launcher_race(monkeypatch) -> None:
    calls = {"count": 0}

    def _fake_job_status(_job_id: str):
        calls["count"] += 1
        if calls["count"] < 3:
            return None
        return {"status": "running"}

    sleeps: list[int] = []
    monotonic_values = iter([0.0, 0.2, 0.4, 0.6])
    monkeypatch.setattr(orchestrator, "_job_status", _fake_job_status)
    monkeypatch.setattr(orchestrator.time, "sleep", lambda seconds: sleeps.append(int(seconds)))
    monkeypatch.setattr(orchestrator.time, "monotonic", lambda: next(monotonic_values))

    record = orchestrator._wait_for_child_registration(
        "bgjob_demo",
        label="excerpt",
        grace_seconds=5,
    )

    assert record == {"status": "running"}
    assert sleeps == [1, 1]


def test_main_launches_accumulation_before_excerpt_completion(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(orchestrator, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(orchestrator, "_render_report", lambda **kwargs: "# demo\n")
    call_order: list[str] = []

    def _fake_ensure_child_job_running(*, job_id, **kwargs):
        call_order.append(f"ensure:{job_id}")
        return {"status": "launched", "job_id": job_id}

    def _fake_wait_for_child_registration(job_id: str, *, label: str, grace_seconds: int):
        call_order.append(f"register:{job_id}")
        return {"status": "running"}

    def _fake_wait_for_child_job(job_id: str, *, label: str, poll_seconds: int, status_path: Path, **_kwargs):
        call_order.append(f"wait:{job_id}")
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text("{}\n", encoding="utf-8")
        return {"status": "completed", "job_id": job_id}

    monkeypatch.setattr(orchestrator, "_ensure_child_job_running", _fake_ensure_child_job_running)
    monkeypatch.setattr(orchestrator, "_wait_for_child_registration", _fake_wait_for_child_registration)
    monkeypatch.setattr(orchestrator, "_wait_for_child_job", _fake_wait_for_child_job)

    argv = [
        "orchestrate_active_benchmark_eval.py",
        "--run-id",
        "parent_run",
        "--excerpt-run-id",
        "excerpt_run",
        "--accumulation-run-id",
        "accumulation_run",
        "--excerpt-job-id",
        "excerpt_job",
        "--accumulation-job-id",
        "accumulation_job",
    ]
    monkeypatch.setattr(sys, "argv", argv)

    assert orchestrator.main() == 0
    assert call_order[:4] == [
        "ensure:excerpt_job",
        "register:excerpt_job",
        "ensure:accumulation_job",
        "register:accumulation_job",
    ]
    assert call_order[4:] == [
        "wait:excerpt_job",
        "wait:accumulation_job",
    ]


def test_update_catalog_records_parent_bundle(monkeypatch, tmp_path: Path) -> None:
    upserts: list[dict] = []
    monkeypatch.setattr(orchestrator, "build_entry", lambda **kwargs: {"entry": kwargs})
    monkeypatch.setattr(orchestrator, "upsert_catalog_entry", lambda entry: upserts.append(entry))
    excerpt_aggregate = tmp_path / "excerpt" / "summary" / "aggregate.json"
    accumulation_aggregate = tmp_path / "accumulation" / "summary" / "aggregate.json"
    excerpt_aggregate.parent.mkdir(parents=True)
    accumulation_aggregate.parent.mkdir(parents=True)
    excerpt_aggregate.write_text(
        json.dumps(
            {
                "mechanisms": {
                    "attentional_v2": {"note_recall": 0.35},
                    "iterator_v1": {"note_recall": 0.12},
                }
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    accumulation_aggregate.write_text(
        json.dumps(
            {
                "mechanisms": {
                    "attentional_v2": {"average_quality_score": 2.58},
                    "iterator_v1": {"average_quality_score": 3.08},
                }
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    orchestrator._update_catalog_or_warn(
        run_id="parent_run",
        run_root=tmp_path / "parent_run",
        summary_payload={
            "excerpt": {
                "job_id": "excerpt_job",
                "aggregate_path": str(excerpt_aggregate),
            },
            "accumulation": {
                "job_id": "accumulation_job",
                "aggregate_path": str(accumulation_aggregate),
            },
        },
    )

    assert len(upserts) == 1
    assert upserts[0]["entry"]["surface"] == "active_benchmark_bundle"
    assert upserts[0]["entry"]["job_ids"] == ["excerpt_job", "accumulation_job"]
    assert "0.35" in upserts[0]["entry"]["one_line_conclusion"]
