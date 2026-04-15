#!/usr/bin/env python3
"""Inspect long-running eval and dataset background jobs from the durable registry."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reading_runtime.background_job_registry import (  # noqa: E402
    active_jobs_summary_file,
    recover_background_jobs,
    refresh_background_jobs,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="Backend root that owns state/job_registry.")
    parser.add_argument(
        "--job-id",
        dest="job_ids",
        action="append",
        default=None,
        help="Only inspect the specified job id. Repeat this flag to inspect multiple jobs.",
    )
    parser.add_argument(
        "--run-check-commands",
        action="store_true",
        help="Execute each stored check_command while refreshing observations.",
    )
    parser.add_argument(
        "--archive-terminal",
        action="store_true",
        help="Move completed/failed/abandoned jobs from active registry into history after refresh.",
    )
    parser.add_argument(
        "--auto-recover",
        action="store_true",
        help="After each refresh, relaunch eligible terminal jobs that have auto-recovery enabled.",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Keep looping instead of doing a single refresh pass.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=300,
        help="Sleep interval between watch passes. Default: 300 seconds.",
    )
    parser.add_argument(
        "--max-passes",
        type=int,
        default=0,
        help="Optional cap for watch mode. `0` means run indefinitely.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).resolve()

    passes_run = 0
    while True:
        refreshed = refresh_background_jobs(
            root=root,
            job_ids=args.job_ids,
            run_check_commands=args.run_check_commands,
            archive_terminal=args.archive_terminal,
        )
        recovery_actions = (
            recover_background_jobs(root=root, job_ids=args.job_ids, now=datetime.now(timezone.utc))
            if args.auto_recover
            else []
        )
        payload = {
            "jobs": refreshed,
            "recovery_actions": recovery_actions,
            "summary_file": str(active_jobs_summary_file(root)),
            "archived_terminal_jobs": bool(args.archive_terminal),
            "ran_check_commands": bool(args.run_check_commands),
            "watch_mode": bool(args.watch),
            "interval_seconds": max(1, int(args.interval_seconds)),
            "passes_run": passes_run + 1,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        passes_run += 1
        if not args.watch:
            break
        if int(args.max_passes or 0) > 0 and passes_run >= int(args.max_passes):
            break
        time.sleep(max(1, int(args.interval_seconds)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
