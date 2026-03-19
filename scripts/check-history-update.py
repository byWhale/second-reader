#!/usr/bin/env python3
"""Warn when decision-bearing docs change without a matching decision-log update."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


DEFAULT_ROOT_DIR = Path(__file__).resolve().parents[1]
DECISION_LOG_PATH = Path("docs/history/decision-log.md")
TRIGGER_PATHS = (
    Path("AGENTS.md"),
    Path("reading-companion-backend/AGENTS.md"),
    Path("reading-companion-frontend/AGENTS.md"),
    Path("docs/workspace-overview.md"),
    Path("docs/product-interaction-model.md"),
    Path("docs/runtime-modes.md"),
    Path("docs/backend-sequential-lifecycle.md"),
    Path("docs/backend-reading-mechanism.md"),
    Path("docs/backend-state-aggregation.md"),
    Path("docs/frontend-visual-system.md"),
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Warn when high-signal design docs change without a matching decision-log update."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_ROOT_DIR,
        help="Repository root to inspect. Defaults to the workspace root that contains this script.",
    )
    return parser.parse_args()


def _run_git(repo_root: Path, *args: str) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _changed_paths(repo_root: Path) -> set[Path]:
    tracked = _run_git(repo_root, "diff", "--name-only", "HEAD")
    untracked = _run_git(repo_root, "ls-files", "--others", "--exclude-standard")
    return {Path(item) for item in tracked + untracked}


def _warning_message(trigger_hits: list[Path]) -> str:
    trigger_list = "\n".join(f"- {path.as_posix()}" for path in trigger_hits)
    return "\n".join(
        [
            "warning: high-signal design docs changed without a matching decision-log update.",
            "These paths may indicate a design inflection:",
            trigger_list,
            "Consider updating docs/history/decision-log.md or naming the concrete reason for leaving it unchanged in the task close-out.",
        ]
    )


def main() -> int:
    args = _parse_args()
    repo_root = args.repo_root.resolve()
    changed = _changed_paths(repo_root)
    trigger_hits = sorted(path for path in changed if path in TRIGGER_PATHS)

    if trigger_hits and DECISION_LOG_PATH not in changed:
        print(_warning_message(trigger_hits))
    else:
        print("History update reminder: no likely missed decision-log entry detected.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
