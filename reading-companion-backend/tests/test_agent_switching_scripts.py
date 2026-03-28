"""Tests for the agent-switching context and traceability scripts."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
TRACEABILITY_SCRIPT = ROOT_DIR / "scripts" / "check-agent-traceability.py"
CONTEXT_SCRIPT = ROOT_DIR / "scripts" / "print-agent-context.py"


def _run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    _write(path, json.dumps(payload, ensure_ascii=False, indent=2))


def _init_repo(repo_root: Path) -> None:
    _run(["git", "init"], cwd=repo_root)
    _run(["git", "config", "user.name", "Test User"], cwd=repo_root)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo_root)

    _write(repo_root / "AGENTS.md", "# Root Guide\n")
    _write(repo_root / "README.md", "# Workspace\n")
    _write(repo_root / "docs/source-of-truth-map.md", "# Source Of Truth Map\n")
    _write(repo_root / "docs/truth.md", "# Truth\n")
    _write(repo_root / "docs/detail.md", "# Detail\n")
    _write(repo_root / "docs/acceptance.md", "# Acceptance\n")
    _write(repo_root / "docs/evidence.md", "# Evidence\n")
    _write(repo_root / "docs/tasks/registry.md", "# Task Registry\n")
    _write(
        repo_root / "docs/agent-handoff.md",
        "\n".join(
            [
                "# Agent Handoff",
                "",
                "## Session Scratchpad",
                "- Leave empty when no session-only notes are needed.",
                "- No session-only notes right now.",
                "- Move anything durable into `docs/current-state.md` or `docs/tasks/registry.*` before ending the task.",
                "",
            ]
        ),
    )
    _write(
        repo_root / "docs/current-state.md",
        "\n".join(
            [
                "# Current State",
                "",
                "## Current Objective",
                "- Recover live state from the repo without chat history.",
                "",
                "## Now",
                "- Review the active task and running job.",
                "",
                "## Next",
                "- Finish the active job and clear blockers.",
                "",
                "## Blocked",
                "- TASK-2 waits on TASK-1.",
                "",
                "## Open Decisions",
                "- Q1",
                "",
                "## Active Risks",
                "- Drift between task state and job state.",
                "",
                "## Recommended Reading Path",
                "1. AGENTS.md",
                "2. README.md",
                "",
                "## Machine-Readable Appendix",
                "```json",
                json.dumps(
                    {
                        "updated_at": "2026-03-28T05:59:20Z",
                        "last_updated_by": "codex",
                        "active_task_ids": ["TASK-1"],
                        "blocked_task_ids": ["TASK-2"],
                        "active_job_ids": ["JOB-1"],
                        "open_decision_ids": ["Q1"],
                        "detail_refs": ["docs/detail.md"],
                        "truth_refs": ["docs/truth.md", "docs/tasks/registry.json"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                "```",
                "",
            ]
        ),
    )
    _write_json(
        repo_root / "docs/tasks/registry.json",
        {
            "version": 1,
            "updated_at": "2026-03-28T05:59:20Z",
            "tasks": [
                {
                    "id": "TASK-1",
                    "title": "Primary active task",
                    "status": "active",
                    "lane": "core",
                    "priority": "high",
                    "detail_ref": "docs/detail.md",
                    "truth_refs": ["docs/truth.md"],
                    "decision_refs": ["DEC-001"],
                    "job_refs": ["JOB-1"],
                    "acceptance_ref": "docs/acceptance.md",
                    "next_action": "Review the latest output.",
                    "blocked_by": [],
                    "evidence_refs": ["docs/evidence.md"],
                    "last_updated": "2026-03-28T05:59:20Z",
                    "last_updated_by": "codex",
                },
                {
                    "id": "TASK-2",
                    "title": "Blocked follow-up task",
                    "status": "blocked",
                    "lane": "core",
                    "priority": "medium",
                    "detail_ref": "docs/detail.md",
                    "truth_refs": ["docs/truth.md"],
                    "decision_refs": ["DEC-001"],
                    "job_refs": [],
                    "acceptance_ref": "docs/acceptance.md",
                    "next_action": "Wait for TASK-1.",
                    "blocked_by": ["TASK-1"],
                    "evidence_refs": ["docs/evidence.md"],
                    "last_updated": "2026-03-28T05:59:20Z",
                    "last_updated_by": "codex",
                },
            ],
        },
    )
    _write_json(
        repo_root / "reading-companion-backend/state/job_registry/active_jobs.json",
        {
            "version": 1,
            "updated_at": "2026-03-28T05:59:20Z",
            "jobs": [
                {
                    "job_id": "JOB-1",
                    "task_ref": "TASK-1",
                    "purpose": "Run the active job",
                    "run_dir": "/tmp/run",
                    "status": "running",
                }
            ],
        },
    )
    _write(
        repo_root / "docs/history/decision-log.md",
        "\n".join(
            [
                "# Decision Log",
                "",
                "## Entry 1",
                "**ID**: DEC-001",
                "**Status**: active",
                "",
                "**Decision / Inflection**: Example decision.",
                "",
            ]
        ),
    )

    _run(["git", "add", "."], cwd=repo_root)
    _run(["git", "commit", "-m", "initial"], cwd=repo_root)


def _run_traceability(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(TRACEABILITY_SCRIPT), "--repo-root", str(repo_root)],
        check=False,
        capture_output=True,
        text=True,
    )


def _run_context(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CONTEXT_SCRIPT), "--repo-root", str(repo_root)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_agent_traceability_checker_is_quiet_when_memory_files_align(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    result = _run_traceability(repo_root)

    assert result.returncode == 0
    assert "no issues detected" in result.stdout
    assert "warning:" not in result.stdout


def test_agent_traceability_checker_warns_when_active_job_disagrees(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    _write_json(
        repo_root / "reading-companion-backend/state/job_registry/active_jobs.json",
        {
            "version": 1,
            "updated_at": "2026-03-28T05:59:20Z",
            "jobs": [
                {
                    "job_id": "JOB-1",
                    "task_ref": "TASK-1",
                    "purpose": "Run the active job",
                    "run_dir": "/tmp/run",
                    "status": "completed",
                }
            ],
        },
    )

    result = _run_traceability(repo_root)

    assert result.returncode == 0
    assert "warning: agent-switching traceability issues detected." in result.stdout
    assert "lists job 'JOB-1' as active, but the job registry status is 'completed'" in result.stdout


def test_agent_traceability_checker_warns_when_handoff_scratch_remains(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    _write(
        repo_root / "docs/agent-handoff.md",
        "\n".join(
            [
                "# Agent Handoff",
                "",
                "## Session Scratchpad",
                "- Leave empty when no session-only notes are needed.",
                "- Remember to relaunch the stuck background lane.",
                "",
            ]
        ),
    )

    result = _run_traceability(repo_root)

    assert result.returncode == 0
    assert "docs/agent-handoff.md still contains session scratch content" in result.stdout


def test_agent_traceability_checker_warns_for_missing_decision_refs(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    _write_json(
        repo_root / "docs/tasks/registry.json",
        {
            "version": 1,
            "updated_at": "2026-03-28T05:59:20Z",
            "tasks": [
                {
                    "id": "TASK-1",
                    "title": "Primary active task",
                    "status": "active",
                    "lane": "core",
                    "priority": "high",
                    "detail_ref": "docs/detail.md",
                    "truth_refs": ["docs/truth.md"],
                    "decision_refs": ["DEC-999"],
                    "job_refs": ["JOB-1"],
                    "acceptance_ref": "docs/acceptance.md",
                    "next_action": "Review the latest output.",
                    "blocked_by": [],
                    "evidence_refs": ["docs/evidence.md"],
                    "last_updated": "2026-03-28T05:59:20Z",
                    "last_updated_by": "codex",
                },
                {
                    "id": "TASK-2",
                    "title": "Blocked follow-up task",
                    "status": "blocked",
                    "lane": "core",
                    "priority": "medium",
                    "detail_ref": "docs/detail.md",
                    "truth_refs": ["docs/truth.md"],
                    "decision_refs": ["DEC-001"],
                    "job_refs": [],
                    "acceptance_ref": "docs/acceptance.md",
                    "next_action": "Wait for TASK-1.",
                    "blocked_by": ["TASK-1"],
                    "evidence_refs": ["docs/evidence.md"],
                    "last_updated": "2026-03-28T05:59:20Z",
                    "last_updated_by": "codex",
                },
            ],
        },
    )

    result = _run_traceability(repo_root)

    assert result.returncode == 0
    assert "points to missing decision id 'DEC-999'" in result.stdout


def test_agent_context_script_prints_canonical_summary(tmp_path: Path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    result = _run_context(repo_root)

    assert result.returncode == 0
    assert "Agent Context" in result.stdout
    assert "Recover live state from the repo without chat history." in result.stdout
    assert "Primary active task" in result.stdout
    assert "JOB-1 [running]" in result.stdout
