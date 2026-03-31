"""Tests for the durable background job registry."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from src.reading_runtime.background_job_registry import (
    active_jobs_file,
    active_jobs_summary_file,
    archive_background_job,
    get_active_job,
    history_jobs_file,
    import_product_shadow_job,
    job_registry_dir,
    job_record_file,
    load_active_registry,
    load_job_record,
    refresh_background_jobs,
    upsert_background_job,
)


def test_background_job_registry_tracks_completed_job_and_writes_summary(tmp_path: Path) -> None:
    status_file = tmp_path / "run_state.json"
    status_file.write_text(json.dumps({"status": "completed"}), encoding="utf-8")
    expected_output = tmp_path / "summary" / "report.md"
    expected_output.parent.mkdir(parents=True, exist_ok=True)
    expected_output.write_text("ok", encoding="utf-8")

    record = upsert_background_job(
        root=tmp_path,
        job_id="bgjob_test_completed",
        task_ref="execution-tracker#chapter-rerun",
        lane="mechanism_eval",
        purpose="Full English chapter-core rerun",
        command="python eval/attentional_v2/run_chapter_comparison.py --pack en",
        cwd=str(tmp_path),
        status="running",
        pid=os.getpid(),
        run_dir=str(tmp_path / "eval_run"),
        status_file=str(status_file),
        expected_outputs=[str(expected_output)],
        check_command=f"{sys.executable} -c \"print('check-ok')\"",
        next_check_hint="Wait for summary report.",
        decision_if_success="Compare with previous English round1 report.",
        decision_if_failure="Return to narrower local-reading repair.",
    )

    refreshed = refresh_background_jobs(root=tmp_path, run_check_commands=True)
    assert refreshed
    observation = refreshed[0]["latest_observation"]
    assert refreshed[0]["status"] == "completed"
    assert observation["status_file_status"] == "completed"
    assert observation["check_result"]["ok"] is True
    assert observation["expected_outputs"][0]["exists"] is True
    assert job_record_file("bgjob_test_completed", tmp_path).exists()

    summary_text = active_jobs_summary_file(tmp_path).read_text(encoding="utf-8")
    assert "No active background jobs are currently registered." in summary_text
    assert "bgjob_test_completed" not in summary_text

    archived = archive_background_job(record["job_id"], root=tmp_path, archive_reason="finished")
    assert archived["archive_reason"] == "finished"
    assert get_active_job(record["job_id"], root=tmp_path) is None
    assert history_jobs_file(tmp_path).exists()
    history_lines = history_jobs_file(tmp_path).read_text(encoding="utf-8").splitlines()
    assert history_lines


def test_background_job_registry_marks_dead_running_job_abandoned(tmp_path: Path) -> None:
    upsert_background_job(
        root=tmp_path,
        job_id="bgjob_test_abandoned",
        task_ref="execution-tracker#private-library-audit",
        lane="dataset_growth",
        purpose="Pending excerpt packet audit",
        command="python eval/attentional_v2/run_case_design_audit.py --packet test",
        cwd=str(tmp_path),
        status="running",
        pid=999999,
        check_command="echo check",
    )

    refreshed = refresh_background_jobs(root=tmp_path, run_check_commands=False)
    assert refreshed[0]["status"] == "abandoned"

    registry = load_active_registry(tmp_path)
    assert registry["jobs"] == []
    assert active_jobs_file(tmp_path).exists()
    assert job_registry_dir(tmp_path).exists()


def test_background_job_registry_infers_completed_without_status_file_when_outputs_and_check_pass(tmp_path: Path) -> None:
    expected_output = tmp_path / "summary" / "report.md"
    expected_output.parent.mkdir(parents=True, exist_ok=True)
    expected_output.write_text("ok", encoding="utf-8")

    upsert_background_job(
        root=tmp_path,
        job_id="bgjob_test_inferred_complete",
        task_ref="execution-tracker#chapter-rerun",
        lane="mechanism_eval",
        purpose="Legacy lane-a style eval run",
        command="python eval/attentional_v2/run_chapter_comparison.py --pack en",
        cwd=str(tmp_path),
        status="running",
        pid=999999,
        expected_outputs=[str(expected_output)],
        check_command=f"{sys.executable} -c \"print('ok')\"",
    )

    refreshed = refresh_background_jobs(root=tmp_path, run_check_commands=True)

    assert refreshed[0]["status"] == "completed"
    assert refreshed[0]["latest_observation"]["expected_outputs"][0]["exists"] is True
    assert refreshed[0]["latest_observation"]["check_result"]["ok"] is True


def test_get_active_job_excludes_terminal_unarchived_records(tmp_path: Path) -> None:
    upsert_background_job(
        root=tmp_path,
        job_id="bgjob_test_terminal_hidden",
        task_ref="execution-tracker#chapter-rerun",
        lane="mechanism_eval",
        purpose="Completed eval run",
        command="python eval/attentional_v2/run_chapter_comparison.py --pack en",
        cwd=str(tmp_path),
        status="completed",
    )

    assert get_active_job("bgjob_test_terminal_hidden", root=tmp_path) is None
    assert load_active_registry(tmp_path)["jobs"] == []


def test_background_job_registry_imports_product_shadow_into_canonical_store(tmp_path: Path) -> None:
    shadow_path = tmp_path / "state" / "jobs" / "job-shadow.json"
    shadow_path.parent.mkdir(parents=True, exist_ok=True)
    shadow_path.write_text(
        json.dumps(
            {
                "job_id": "job-shadow",
                "status": "queued",
                "job_kind": "read",
                "upload_path": str(tmp_path / "state" / "uploads" / "job-shadow.epub"),
                "book_id": "demo-book",
                "created_at": "2026-03-07T00:00:00Z",
                "updated_at": "2026-03-07T00:00:00Z",
                "error": None,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    imported = import_product_shadow_job("job-shadow", root=tmp_path, sync_views=False)
    loaded = load_job_record("job-shadow", root=tmp_path)

    assert imported["domain"] == "product_runtime"
    assert imported["show_in_active_views"] is False
    assert loaded["book_id"] == "demo-book"
    assert job_record_file("job-shadow", tmp_path).exists()
