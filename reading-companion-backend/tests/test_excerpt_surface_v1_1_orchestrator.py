"""Tests for excerpt surface v1.1 judged promotion orchestration."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_orchestrator_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "orchestrate_excerpt_surface_v1_1_eval.py"
    spec = importlib.util.spec_from_file_location("excerpt_surface_v1_1_orchestrator", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_ensure_ready_judged_shards_launched_only_launches_ready_shards(monkeypatch, tmp_path: Path) -> None:
    module = _load_orchestrator_module()
    monkeypatch.setattr(module, "BACKEND_ROOT", tmp_path)

    launched_labels: list[str] = []
    monkeypatch.setattr(module, "get_job_record", lambda _job_id, root=None: None)
    monkeypatch.setattr(module, "run_command", lambda _args, *, label: launched_labels.append(label))
    monkeypatch.setattr(module, "_wait_for_job_record", lambda _job_id, timeout_seconds=5.0, poll_seconds=0.1: {"status": "running"})

    job_ids = module.ensure_ready_judged_shards_launched(ready_shard_ids={"shard_a", "shard_b", "shard_c"})

    assert job_ids == (
        "bgjob_excerpt_surface_v1_1_judged_shard_a_20260406",
        "bgjob_excerpt_surface_v1_1_judged_shard_b_20260406",
        "bgjob_excerpt_surface_v1_1_judged_shard_c_20260406",
    )
    assert launched_labels == [
        "launch judged shard_a",
        "launch judged shard_b",
        "launch judged shard_c",
    ]


def test_orchestrator_promotes_ready_shards_before_smoke_merge(monkeypatch, tmp_path: Path) -> None:
    module = _load_orchestrator_module()
    monkeypatch.setattr(module, "BACKEND_ROOT", tmp_path)
    monkeypatch.setattr(module, "summary_outputs_exist", lambda _run_id: False)

    smoke_polls = 0
    present_judged_jobs: set[str] = set()
    events: list[str] = []

    def fake_refresh_background_jobs(*, root, job_ids, run_check_commands=False, archive_terminal=False):
        nonlocal smoke_polls
        assert root == tmp_path
        assert not run_check_commands
        assert not archive_terminal
        if tuple(job_ids) == module.SMOKE_JOB_IDS:
            smoke_polls += 1
            if smoke_polls == 1:
                return [
                    {"job_id": module.SMOKE_JOB_IDS[0], "status": "completed"},
                    {"job_id": module.SMOKE_JOB_IDS[1], "status": "running"},
                ]
            return [
                {"job_id": module.SMOKE_JOB_IDS[0], "status": "completed"},
                {"job_id": module.SMOKE_JOB_IDS[1], "status": "completed"},
            ]
        assert set(job_ids) == present_judged_jobs
        return [{"job_id": job_id, "status": "completed"} for job_id in job_ids]

    def fake_unit_ready(_run_root, *, unit_key, mechanism_filter="both"):
        assert mechanism_filter == "both"
        if unit_key == "value_of_others_private_en__chapter_8":
            return smoke_polls >= 2
        return True

    def fake_get_job_record(job_id, root=None):
        assert root == tmp_path
        if job_id in present_judged_jobs:
            return {"job_id": job_id, "status": "running"}
        return None

    def fake_run_command(args, *, label):
        if label.startswith("launch judged "):
            job_id = args[args.index("--job-id") + 1]
            present_judged_jobs.add(job_id)
        events.append(label)

    monkeypatch.setattr(module, "refresh_background_jobs", fake_refresh_background_jobs)
    monkeypatch.setattr(module, "excerpt_unit_is_ready_for_judging", fake_unit_ready)
    monkeypatch.setattr(module, "get_job_record", fake_get_job_record)
    monkeypatch.setattr(module, "run_command", fake_run_command)
    monkeypatch.setattr(
        module,
        "_wait_for_job_record",
        lambda _job_id, timeout_seconds=5.0, poll_seconds=0.1: {"status": "running"},
    )
    monkeypatch.setattr(module, "merge_smoke", lambda: events.append("merge_smoke"))
    monkeypatch.setattr(module, "merge_judged", lambda: events.append("merge_judged"))
    monkeypatch.setattr(module.time, "sleep", lambda _seconds: None)

    assert module.orchestrate_excerpt_surface_v1_1_eval(poll_seconds=0) == 0

    assert events[:3] == [
        "launch judged shard_a",
        "launch judged shard_b",
        "launch judged shard_c",
    ]
    assert "merge_smoke" in events
    assert "launch judged shard_d" in events
    assert "merge_judged" in events
    assert events.index("merge_smoke") > events.index("launch judged shard_c")
    assert events.index("merge_judged") > events.index("merge_smoke")
