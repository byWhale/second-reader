"""Tests for the warning-only history reminder script."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "check-history-update.py"


def _run(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _init_repo(repo_root: Path) -> None:
    _run(["git", "init"], cwd=repo_root)
    _run(["git", "config", "user.name", "Test User"], cwd=repo_root)
    _run(["git", "config", "user.email", "test@example.com"], cwd=repo_root)

    _write(repo_root / "AGENTS.md", "# Root Guide\n")
    _write(repo_root / "docs/history/decision-log.md", "# Decision Log\n")
    _write(repo_root / "docs/backend-reading-mechanism.md", "# Reader Mechanism\n")
    _write(repo_root / "docs/api-contract.md", "# Contract\n")

    _run(["git", "add", "."], cwd=repo_root)
    _run(["git", "commit", "-m", "initial"], cwd=repo_root)


def _run_checker(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--repo-root", str(repo_root)],
        check=False,
        capture_output=True,
        text=True,
    )


def test_history_update_checker_is_quiet_without_trigger_changes(tmp_path: Path):
    """No trigger-path changes should produce the no-warning status line."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    result = _run_checker(repo_root)

    assert result.returncode == 0
    assert "no likely missed decision-log entry detected" in result.stdout
    assert "warning:" not in result.stdout


def test_history_update_checker_warns_for_trigger_change_without_decision_log(tmp_path: Path):
    """Changing a trigger doc alone should emit an advisory warning."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    _write(repo_root / "docs/backend-reading-mechanism.md", "# Reader Mechanism\nupdated\n")

    result = _run_checker(repo_root)

    assert result.returncode == 0
    assert "warning: high-signal design docs changed without a matching decision-log update." in result.stdout
    assert "- docs/backend-reading-mechanism.md" in result.stdout


def test_history_update_checker_suppresses_warning_when_decision_log_also_changes(tmp_path: Path):
    """A matching decision-log change should satisfy the reminder."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    _write(repo_root / "docs/backend-reading-mechanism.md", "# Reader Mechanism\nupdated\n")
    _write(repo_root / "docs/history/decision-log.md", "# Decision Log\nEntry\n")

    result = _run_checker(repo_root)

    assert result.returncode == 0
    assert "warning:" not in result.stdout
    assert "no likely missed decision-log entry detected" in result.stdout


def test_history_update_checker_counts_untracked_trigger_files(tmp_path: Path):
    """Untracked high-signal docs should still trigger the advisory warning."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    _write(repo_root / "docs/frontend-visual-system.md", "# Visual System\n")

    result = _run_checker(repo_root)

    assert result.returncode == 0
    assert "warning:" in result.stdout
    assert "- docs/frontend-visual-system.md" in result.stdout


def test_history_update_checker_ignores_non_trigger_changes(tmp_path: Path):
    """Routine non-trigger docs should not create history warnings."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _init_repo(repo_root)

    _write(repo_root / "docs/api-contract.md", "# Contract\nupdated\n")

    result = _run_checker(repo_root)

    assert result.returncode == 0
    assert "warning:" not in result.stdout
    assert "no likely missed decision-log entry detected" in result.stdout
