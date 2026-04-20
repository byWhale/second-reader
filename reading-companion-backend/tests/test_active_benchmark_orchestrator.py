from __future__ import annotations

import importlib.util
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
    )

    assert relaunched == ["bgjob_demo"]
    assert payload["status"] == "relaunched"
