"""Tests for the generic registry wrapper launcher."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.reading_runtime.background_job_registry import load_job_record


def test_run_registered_job_marks_successful_command_completed(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    wrapper = backend_root / "scripts" / "run_registered_job.py"
    expected_output = tmp_path / "done.txt"

    command = [
        sys.executable,
        str(wrapper),
        "--root",
        str(tmp_path),
        "--job-id",
        "bgjob_wrapper_success",
        "--task-ref",
        "execution-tracker#wrapper-smoke",
        "--lane",
        "mechanism_eval",
        "--purpose",
        "Wrapper smoke test",
        "--cwd",
        str(tmp_path),
        "--expected-output",
        str(expected_output),
        "--",
        sys.executable,
        "-c",
        (
            "from pathlib import Path; "
            f"Path({str(expected_output)!r}).write_text('ok', encoding='utf-8'); "
            "print('done')"
        ),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["job_id"] == "bgjob_wrapper_success"
    record = load_job_record("bgjob_wrapper_success", root=tmp_path)
    assert record["status"] == "completed"
    assert expected_output.exists()
