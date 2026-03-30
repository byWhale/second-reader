"""Helpers for inspecting case-audit run state."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


RUN_STATE_FILE = "run_state.json"
SUMMARY_DIR = "summary"
AGGREGATE_FILE = "aggregate.json"
REPORT_FILE = "report.md"
PARTIAL_AGGREGATE_FILE = "aggregate.partial.json"
PARTIAL_REPORT_FILE = "report.partial.md"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def process_is_alive(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def inspect_case_audit_run(run_dir: Path) -> dict[str, Any]:
    run_state_path = run_dir / RUN_STATE_FILE
    aggregate_path = run_dir / SUMMARY_DIR / AGGREGATE_FILE
    report_path = run_dir / SUMMARY_DIR / REPORT_FILE
    partial_aggregate_path = run_dir / SUMMARY_DIR / PARTIAL_AGGREGATE_FILE
    partial_report_path = run_dir / SUMMARY_DIR / PARTIAL_REPORT_FILE

    run_state: dict[str, Any] = {}
    if run_state_path.exists():
        run_state = load_json(run_state_path)

    aggregate: dict[str, Any] = {}
    if aggregate_path.exists():
        aggregate = load_json(aggregate_path)

    status = str(run_state.get("status", "")).strip().lower()
    aggregate_status = str(aggregate.get("status", "")).strip().lower()
    if aggregate_path.exists():
        if aggregate_status in {"failed", "incomplete"}:
            effective_status = aggregate_status
        else:
            effective_status = "completed"
    elif status == "running":
        pid = run_state.get("pid")
        effective_status = "running" if process_is_alive(pid if isinstance(pid, int) else None) else "incomplete"
    elif status in {"failed", "incomplete"}:
        effective_status = status
    elif run_state:
        effective_status = status or "unknown"
    else:
        effective_status = "unknown"

    progress = {
        "case_count": int(run_state.get("case_count", aggregate.get("case_count", 0)) or 0),
        "completed_case_count": int(run_state.get("completed_case_count", aggregate.get("completed_case_count", 0)) or 0),
        "failed_case_count": int(run_state.get("failed_case_count", aggregate.get("failed_case_count", 0)) or 0),
        "queued_case_count": int(run_state.get("queued_case_count", 0) or 0),
        "running_case_count": int(run_state.get("running_case_count", 0) or 0),
    }

    return {
        "run_id": run_dir.name,
        "run_dir": str(run_dir),
        "status": effective_status,
        "raw_status": status or "unknown",
        "run_state_path": str(run_state_path) if run_state_path.exists() else "",
        "aggregate_path": str(aggregate_path) if aggregate_path.exists() else "",
        "report_path": str(report_path) if report_path.exists() else "",
        "partial_aggregate_path": str(partial_aggregate_path) if partial_aggregate_path.exists() else "",
        "partial_report_path": str(partial_report_path) if partial_report_path.exists() else "",
        "run_state": run_state,
        "aggregate": aggregate,
        "progress": progress,
    }


def latest_case_audit_run(packet_id: str, runs_root: Path, *, require_completed: bool) -> dict[str, Any] | None:
    matching_dirs = sorted(path for path in runs_root.iterdir() if path.is_dir() and path.name.startswith(f"{packet_id}__"))
    if not matching_dirs:
        return None
    inspected = [inspect_case_audit_run(path) for path in matching_dirs]
    if require_completed:
        for item in reversed(inspected):
            if item["status"] == "completed" and item["aggregate_path"]:
                return item
        return None
    return inspected[-1]
