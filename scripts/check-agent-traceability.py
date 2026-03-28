#!/usr/bin/env python3
"""Warn when the agent-switching memory files drift out of sync."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


DEFAULT_ROOT_DIR = Path(__file__).resolve().parents[1]
CURRENT_STATE_PATH = Path("docs/current-state.md")
TASK_REGISTRY_PATH = Path("docs/tasks/registry.json")
ACTIVE_JOBS_PATH = Path("reading-companion-backend/state/job_registry/active_jobs.json")
DECISION_LOG_PATH = Path("docs/history/decision-log.md")
HANDOFF_PATH = Path("docs/agent-handoff.md")
SOURCE_OF_TRUTH_PATH = Path("docs/source-of-truth-map.md")

TASK_REQUIRED_FIELDS = (
    "id",
    "title",
    "status",
    "lane",
    "priority",
    "detail_ref",
    "truth_refs",
    "decision_refs",
    "job_refs",
    "acceptance_ref",
    "next_action",
    "blocked_by",
    "evidence_refs",
    "last_updated",
    "last_updated_by",
)
CURRENT_STATE_REQUIRED_FIELDS = (
    "updated_at",
    "last_updated_by",
    "active_task_ids",
    "blocked_task_ids",
    "active_job_ids",
    "open_decision_ids",
    "detail_refs",
    "truth_refs",
)
ALLOWED_STATUSES = {"active", "blocked", "queued", "waiting", "parked", "done", "cancelled"}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Warn when the agent-switching memory files drift out of sync."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_ROOT_DIR,
        help="Repository root to inspect. Defaults to the workspace root that contains this script.",
    )
    return parser.parse_args()


def _load_markdown_json_appendix(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    heading = "## Machine-Readable Appendix"
    if heading not in text:
        raise RuntimeError(f"Missing '{heading}' in {path}.")

    appendix_text = text.split(heading, 1)[1]
    match = re.search(r"```json\s*(\{.*?\})\s*```", appendix_text, flags=re.DOTALL)
    if not match:
        raise RuntimeError(f"Could not find a fenced JSON appendix in {path}.")
    return json.loads(match.group(1))


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _path_exists(repo_root: Path, ref: str) -> bool:
    ref = str(ref or "").strip()
    if not ref:
        return False
    if ref.startswith("http://") or ref.startswith("https://"):
        return True
    path_part = ref.split("#", 1)[0]
    target = Path(path_part)
    if not target.is_absolute():
        target = repo_root / target
    return target.exists()


def _parse_decision_ids(path: Path) -> tuple[set[str], set[str]]:
    decision_ids: set[str] = set()
    duplicates: set[str] = set()
    for match in re.finditer(r"^\*\*ID\*\*:\s*([A-Z0-9-]+)\s*$", path.read_text(encoding="utf-8"), re.MULTILINE):
        decision_id = match.group(1)
        if decision_id in decision_ids:
            duplicates.add(decision_id)
        decision_ids.add(decision_id)
    return decision_ids, duplicates


def _load_handoff_scratch_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^## Session Scratchpad\s*$", text, flags=re.MULTILINE)
    if not match:
        return []
    tail = text[match.end() :]
    next_heading = re.search(r"^##\s+", tail, flags=re.MULTILINE)
    section = tail[: next_heading.start()] if next_heading else tail
    lines = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("<!--") or line.endswith("-->"):
            continue
        lines.append(line)
    return lines


def _warning_message(warnings: list[str]) -> str:
    warning_lines = "\n".join(f"- {warning}" for warning in warnings)
    return "\n".join(
        [
            "warning: agent-switching traceability issues detected.",
            warning_lines,
            "Update docs/current-state.md, docs/tasks/registry.*, the job registry, or docs/agent-handoff.md so repo state stays recoverable without chat history.",
        ]
    )


def main() -> int:
    args = _parse_args()
    repo_root = args.repo_root.resolve()

    current_state_path = repo_root / CURRENT_STATE_PATH
    task_registry_path = repo_root / TASK_REGISTRY_PATH
    active_jobs_path = repo_root / ACTIVE_JOBS_PATH
    decision_log_path = repo_root / DECISION_LOG_PATH
    handoff_path = repo_root / HANDOFF_PATH
    source_of_truth_path = repo_root / SOURCE_OF_TRUTH_PATH

    current_state = _load_markdown_json_appendix(current_state_path)
    task_registry = _load_json(task_registry_path)
    active_jobs = _load_json(active_jobs_path)
    decision_ids, duplicate_decision_ids = _parse_decision_ids(decision_log_path)

    warnings: list[str] = []

    if not source_of_truth_path.exists():
        warnings.append("docs/source-of-truth-map.md is missing.")

    for field in CURRENT_STATE_REQUIRED_FIELDS:
        value = current_state.get(field)
        if value in (None, "", []):
            warnings.append(f"docs/current-state.md is missing required appendix field '{field}'.")

    tasks = task_registry.get("tasks")
    if not isinstance(tasks, list):
        raise RuntimeError(f"Expected 'tasks' list in {task_registry_path}.")
    if not task_registry.get("updated_at"):
        warnings.append("docs/tasks/registry.json is missing top-level 'updated_at'.")

    jobs = active_jobs.get("jobs")
    if not isinstance(jobs, list):
        raise RuntimeError(f"Expected 'jobs' list in {active_jobs_path}.")

    jobs_by_id = {
        str(job.get("job_id")): job for job in jobs if isinstance(job, dict) and str(job.get("job_id", "")).strip()
    }
    tasks_by_id: dict[str, dict[str, object]] = {}
    duplicate_task_ids: set[str] = set()

    for raw_task in tasks:
        if not isinstance(raw_task, dict):
            warnings.append("docs/tasks/registry.json contains a non-object task entry.")
            continue
        task = dict(raw_task)
        task_id = str(task.get("id", "")).strip()
        if task_id in tasks_by_id:
            duplicate_task_ids.add(task_id)
        if task_id:
            tasks_by_id[task_id] = task

    for duplicate_task_id in sorted(duplicate_task_ids):
        warnings.append(f"Duplicate task id '{duplicate_task_id}' found in docs/tasks/registry.json.")

    for task_id, task in tasks_by_id.items():
        for field in TASK_REQUIRED_FIELDS:
            value = task.get(field)
            if value in (None, ""):
                warnings.append(f"Task '{task_id}' is missing required field '{field}'.")
        status = str(task.get("status", "")).strip()
        if status not in ALLOWED_STATUSES:
            warnings.append(f"Task '{task_id}' uses unsupported status '{status}'.")

        for field in ("detail_ref", "acceptance_ref"):
            ref = str(task.get(field, "")).strip()
            if ref and not _path_exists(repo_root, ref):
                warnings.append(f"Task '{task_id}' points to missing path in '{field}': {ref}")

        for field in ("truth_refs", "evidence_refs"):
            refs = task.get(field, [])
            if not isinstance(refs, list):
                warnings.append(f"Task '{task_id}' field '{field}' must be a list.")
                continue
            for ref in refs:
                ref_text = str(ref).strip()
                if ref_text and not _path_exists(repo_root, ref_text):
                    warnings.append(f"Task '{task_id}' points to missing path in '{field}': {ref_text}")

        decision_refs = task.get("decision_refs", [])
        if not isinstance(decision_refs, list):
            warnings.append(f"Task '{task_id}' field 'decision_refs' must be a list.")
        else:
            for decision_ref in decision_refs:
                decision_text = str(decision_ref).strip()
                if decision_text and decision_text not in decision_ids:
                    warnings.append(f"Task '{task_id}' points to missing decision id '{decision_text}'.")

        job_refs = task.get("job_refs", [])
        if not isinstance(job_refs, list):
            warnings.append(f"Task '{task_id}' field 'job_refs' must be a list.")
        else:
            for job_ref in job_refs:
                job_text = str(job_ref).strip()
                if job_text and job_text not in jobs_by_id:
                    warnings.append(f"Task '{task_id}' points to unknown job id '{job_text}'.")

        if not str(task.get("last_updated", "")).strip():
            warnings.append(f"Task '{task_id}' is missing 'last_updated'.")
        if not str(task.get("last_updated_by", "")).strip():
            warnings.append(f"Task '{task_id}' is missing 'last_updated_by'.")

    for task_id, task in tasks_by_id.items():
        blockers = task.get("blocked_by", [])
        if not isinstance(blockers, list):
            warnings.append(f"Task '{task_id}' field 'blocked_by' must be a list.")
            continue
        for blocker in blockers:
            blocker_id = str(blocker).strip()
            if blocker_id and blocker_id not in tasks_by_id:
                warnings.append(f"Task '{task_id}' is blocked by unknown task id '{blocker_id}'.")

    active_task_ids = current_state.get("active_task_ids", [])
    if isinstance(active_task_ids, list):
        for task_id in active_task_ids:
            task_text = str(task_id).strip()
            task = tasks_by_id.get(task_text)
            if task is None:
                warnings.append(f"docs/current-state.md references unknown active task id '{task_text}'.")
                continue
            if str(task.get("status", "")).strip() not in {"active", "waiting"}:
                warnings.append(
                    f"docs/current-state.md lists '{task_text}' as active, but the task registry status is '{task.get('status', '')}'."
                )
    else:
        warnings.append("docs/current-state.md field 'active_task_ids' must be a list.")

    blocked_task_ids = current_state.get("blocked_task_ids", [])
    if isinstance(blocked_task_ids, list):
        for task_id in blocked_task_ids:
            task_text = str(task_id).strip()
            task = tasks_by_id.get(task_text)
            if task is None:
                warnings.append(f"docs/current-state.md references unknown blocked task id '{task_text}'.")
                continue
            if str(task.get("status", "")).strip() != "blocked":
                warnings.append(
                    f"docs/current-state.md lists '{task_text}' as blocked, but the task registry status is '{task.get('status', '')}'."
                )
    else:
        warnings.append("docs/current-state.md field 'blocked_task_ids' must be a list.")

    for field in ("detail_refs", "truth_refs"):
        refs = current_state.get(field, [])
        if not isinstance(refs, list):
            warnings.append(f"docs/current-state.md field '{field}' must be a list.")
            continue
        for ref in refs:
            ref_text = str(ref).strip()
            if ref_text and not _path_exists(repo_root, ref_text):
                warnings.append(f"docs/current-state.md points to missing path in '{field}': {ref_text}")

    active_job_ids = current_state.get("active_job_ids", [])
    if isinstance(active_job_ids, list):
        for job_id in active_job_ids:
            job_text = str(job_id).strip()
            job = jobs_by_id.get(job_text)
            if job is None:
                warnings.append(f"docs/current-state.md references unknown active job id '{job_text}'.")
                continue
            job_status = str(job.get("status", "")).strip()
            if job_status != "running":
                warnings.append(
                    f"docs/current-state.md lists job '{job_text}' as active, but the job registry status is '{job_status}'."
                )
    else:
        warnings.append("docs/current-state.md field 'active_job_ids' must be a list.")

    for duplicate_decision_id in sorted(duplicate_decision_ids):
        warnings.append(f"Duplicate decision id '{duplicate_decision_id}' found in docs/history/decision-log.md.")

    scratch_lines = _load_handoff_scratch_lines(handoff_path)
    allowed_scratch_lines = {
        "- Leave empty when no session-only notes are needed.",
        "- No session-only notes right now.",
        "- Move anything durable into docs/current-state.md or docs/tasks/registry.* before ending the task.",
        "- Move anything durable into `docs/current-state.md` or `docs/tasks/registry.*` before ending the task.",
    }
    unexpected_scratch = [line for line in scratch_lines if line not in allowed_scratch_lines]
    if unexpected_scratch:
        preview = "; ".join(unexpected_scratch[:3])
        warnings.append(
            "docs/agent-handoff.md still contains session scratch content that should be canonicalized or cleared: "
            f"{preview}"
        )

    if warnings:
        print(_warning_message(warnings))
    else:
        print("Agent traceability reminder: no issues detected.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
