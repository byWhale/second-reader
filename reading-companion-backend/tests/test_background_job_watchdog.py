from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.reading_runtime import background_job_registry as registry
from scripts.run_registered_job import _final_command


def _backend_root(tmp_path: Path) -> Path:
    root = tmp_path / "backend"
    root.mkdir()
    return root


def test_failed_recoverable_job_stays_in_active_registry(tmp_path: Path) -> None:
    root = _backend_root(tmp_path)
    log_file = root / "state" / "job_registry" / "logs" / "job.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("provider timed out or interrupted\n", encoding="utf-8")

    registry.upsert_background_job(
        job_id="bgjob_test_watchdog_active",
        root=root,
        task_ref="TASK-TEST",
        lane="dataset_platform",
        purpose="Verify active-view retention for recoverable failed jobs.",
        command="python fake.py",
        cwd=str(root),
        log_file=str(log_file),
        status="failed",
        ended_at="2026-04-15T00:00:00Z",
        error="ReaderLLMError: timed out or interrupted",
        auto_recovery_mode="recoverable",
        auto_recovery_interval_seconds=300,
    )

    active_jobs = registry.list_active_jobs(root)
    assert [job["job_id"] for job in active_jobs] == ["bgjob_test_watchdog_active"]


def test_recover_background_jobs_relaunches_due_job(monkeypatch, tmp_path: Path) -> None:
    root = _backend_root(tmp_path)
    log_file = root / "state" / "job_registry" / "logs" / "job.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.write_text("quota cooldown remains active\n", encoding="utf-8")

    registry.upsert_background_job(
        job_id="bgjob_test_watchdog_relaunch",
        root=root,
        task_ref="TASK-TEST",
        lane="dataset_platform",
        purpose="Verify watchdog relaunches due recoverable jobs.",
        command="python fake.py",
        cwd=str(root),
        log_file=str(log_file),
        status="failed",
        ended_at="2026-04-15T00:00:00Z",
        error="quota cooldown remains active",
        auto_recovery_mode="recoverable",
        auto_recovery_interval_seconds=300,
    )

    relaunched: list[str] = []

    def _fake_relaunch(job_id: str, *, root: Path | None = None, reason: str = "auto_recovery") -> dict[str, object]:
        relaunched.append(f"{job_id}:{reason}")
        return {"job_id": job_id, "launcher_pid": 12345, "relaunch_count": 1}

    monkeypatch.setattr(registry, "relaunch_background_job", _fake_relaunch)

    actions = registry.recover_background_jobs(
        root=root,
        now=datetime(2026, 4, 15, 0, 10, tzinfo=timezone.utc),
    )

    assert relaunched == ["bgjob_test_watchdog_relaunch:watchdog:recoverable_failure"]
    assert actions == [
        {
            "job_id": "bgjob_test_watchdog_relaunch",
            "action": "relaunched",
            "mode": "recoverable",
            "reason": "recoverable_failure",
            "launcher_pid": 12345,
            "relaunch_count": 1,
        }
    ]


def test_final_command_supports_shell_command() -> None:
    command, stored = _final_command([], shell_command="echo hello")
    assert command[1:] == ["-lc", "echo hello"]
    assert stored == "echo hello"
