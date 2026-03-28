#!/usr/bin/env python3
"""Print a canonical onboarding brief for agent switching."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_ROOT_DIR = Path(__file__).resolve().parents[1]
CURRENT_STATE_PATH = Path("docs/current-state.md")
TASK_REGISTRY_PATH = Path("docs/tasks/registry.json")
ACTIVE_JOBS_PATH = Path("reading-companion-backend/state/job_registry/active_jobs.json")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print the canonical agent-switching context.")
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
    appendix = text.split(heading, 1)[1]
    start = appendix.find("```json")
    end = appendix.find("```", start + 1)
    if start == -1 or end == -1:
        raise RuntimeError(f"Could not find JSON appendix in {path}.")
    return json.loads(appendix[start + len("```json") : end].strip())


def _load_markdown_sections(path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            current_heading = line[3:].strip()
            sections[current_heading] = []
            continue
        if current_heading is not None:
            sections[current_heading].append(line)
    return sections


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_git(repo_root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.rstrip() for line in result.stdout.splitlines()]


def _print_section(title: str, lines: list[str]) -> None:
    content = [line for line in lines if line.strip()]
    if not content:
        return
    print(f"{title}:")
    for line in content:
        print(f"  {line}")
    print()


def main() -> int:
    args = _parse_args()
    repo_root = args.repo_root.resolve()

    current_state_path = repo_root / CURRENT_STATE_PATH
    task_registry_path = repo_root / TASK_REGISTRY_PATH
    active_jobs_path = repo_root / ACTIVE_JOBS_PATH

    current_state_meta = _load_markdown_json_appendix(current_state_path)
    current_state_sections = _load_markdown_sections(current_state_path)
    task_registry = _load_json(task_registry_path)
    active_jobs = _load_json(active_jobs_path)

    tasks = task_registry.get("tasks", [])
    if not isinstance(tasks, list):
        raise RuntimeError(f"Expected 'tasks' list in {task_registry_path}.")
    tasks_by_id = {
        str(task.get("id")): task for task in tasks if isinstance(task, dict) and str(task.get("id", "")).strip()
    }

    jobs = active_jobs.get("jobs", [])
    if not isinstance(jobs, list):
        raise RuntimeError(f"Expected 'jobs' list in {active_jobs_path}.")
    jobs_by_id = {
        str(job.get("job_id")): job for job in jobs if isinstance(job, dict) and str(job.get("job_id", "")).strip()
    }

    branch = _run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")[0]
    status_lines = [line for line in _run_git(repo_root, "status", "--short") if line.strip()]

    print("Agent Context")
    print(f"Repo root: {repo_root}")
    print(f"Current-state updated: {current_state_meta.get('updated_at', '')}")
    print(f"Current-state last_updated_by: {current_state_meta.get('last_updated_by', '')}")
    print()

    _print_section("Current Objective", current_state_sections.get("Current Objective", []))
    _print_section("Now", current_state_sections.get("Now", []))
    _print_section("Next", current_state_sections.get("Next", []))
    _print_section("Blocked", current_state_sections.get("Blocked", []))
    _print_section("Open Decisions", current_state_sections.get("Open Decisions", []))

    print("Active Tasks:")
    for task_id in current_state_meta.get("active_task_ids", []):
        task = tasks_by_id.get(str(task_id))
        if not isinstance(task, dict):
            print(f"  - {task_id}: missing from docs/tasks/registry.json")
            continue
        print(
            "  - "
            f"{task_id} [{task.get('status', '')}/{task.get('priority', '')}] "
            f"{task.get('title', '')}"
        )
        print(f"    next: {task.get('next_action', '')}")
        print(f"    detail: {task.get('detail_ref', '')}")
    print()

    print("Blocked Tasks:")
    for task_id in current_state_meta.get("blocked_task_ids", []):
        task = tasks_by_id.get(str(task_id))
        if not isinstance(task, dict):
            print(f"  - {task_id}: missing from docs/tasks/registry.json")
            continue
        blockers = ", ".join(str(value) for value in task.get("blocked_by", []))
        print(
            "  - "
            f"{task_id} [{task.get('status', '')}/{task.get('priority', '')}] "
            f"{task.get('title', '')}"
        )
        if blockers:
            print(f"    blocked_by: {blockers}")
        print(f"    next: {task.get('next_action', '')}")
    print()

    print("Active Jobs:")
    active_job_ids = current_state_meta.get("active_job_ids", [])
    if isinstance(active_job_ids, list) and active_job_ids:
        for job_id in active_job_ids:
            job = jobs_by_id.get(str(job_id))
            if not isinstance(job, dict):
                print(f"  - {job_id}: missing from active_jobs.json")
                continue
            print(f"  - {job_id} [{job.get('status', '')}] {job.get('purpose', '')}")
            print(f"    task_ref: {job.get('task_ref', '')}")
            print(f"    run_dir: {job.get('run_dir', '')}")
    else:
        print("  - none")
    print()

    print("Repo Status:")
    print(f"  - branch: {branch}")
    print(f"  - worktree: {'clean' if not status_lines else 'dirty'}")
    if status_lines:
        preview = status_lines[:10]
        for line in preview:
            print(f"    {line}")
        if len(status_lines) > len(preview):
            print(f"    ... ({len(status_lines) - len(preview)} more)")
    print()

    backend_env = repo_root / "reading-companion-backend/.env"
    backend_venv = repo_root / "reading-companion-backend/.venv/bin/python"
    frontend_env = repo_root / "reading-companion-frontend/.env.local"
    frontend_node_modules = repo_root / "reading-companion-frontend/node_modules"
    print("Local Environment:")
    print(f"  - backend .env: {'present' if backend_env.exists() else 'missing'}")
    print(f"  - backend venv: {'present' if backend_venv.exists() else 'missing'}")
    print(f"  - frontend .env.local: {'present' if frontend_env.exists() else 'missing (optional)'}")
    print(f"  - frontend node_modules: {'present' if frontend_node_modules.exists() else 'missing'}")
    print()

    _print_section("Recommended Reading Path", current_state_sections.get("Recommended Reading Path", []))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
