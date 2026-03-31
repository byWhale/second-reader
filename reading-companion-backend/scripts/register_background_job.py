#!/usr/bin/env python3
"""Create, update, or archive one long-running eval/dataset background job record."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reading_runtime.background_job_registry import (  # noqa: E402
    TERMINAL_JOB_STATUSES,
    archive_background_job,
    get_job_record,
    upsert_background_job,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="Backend root that owns state/job_registry.")
    parser.add_argument("--job-id", default=None, help="Stable background job identifier. Required for updates and archive.")
    parser.add_argument("--archive", action="store_true", help="Archive an existing active job instead of creating/updating it.")
    parser.add_argument("--archive-reason", default="", help="Optional archive reason written into history.")
    parser.add_argument("--task-ref", default=None, help="Execution-tracker or roadmap reference for this job.")
    parser.add_argument("--lane", default=None, help="Work lane, for example mechanism_eval or dataset_growth.")
    parser.add_argument("--purpose", default=None, help="Human-readable purpose of the job.")
    parser.add_argument("--command", default=None, help="Exact launch command for the background process.")
    parser.add_argument("--cwd", default=None, help="Working directory used for the launch command.")
    parser.add_argument("--pid", type=int, default=None, help="Process id when already launched.")
    parser.add_argument("--run-dir", default=None, help="Primary run/output directory for this job.")
    parser.add_argument("--status-file", default=None, help="Status JSON to inspect when checking the job later.")
    parser.add_argument("--log-file", default=None, help="Log file to inspect for this job later.")
    parser.add_argument(
        "--expected-output",
        dest="expected_outputs",
        action="append",
        default=None,
        help="Expected output path. Repeat this flag to store more than one path.",
    )
    parser.add_argument("--check-command", default=None, help="Shell command to run when checking this job later.")
    parser.add_argument("--next-check-hint", default=None, help="Human hint for what to verify next.")
    parser.add_argument("--decision-if-success", default=None, help="What to do next if the job succeeds.")
    parser.add_argument("--decision-if-failure", default=None, help="What to do next if the job fails.")
    parser.add_argument(
        "--status",
        choices=["registered", "running", *sorted(TERMINAL_JOB_STATUSES)],
        default=None,
        help="Explicit job status. Defaults to registered for new jobs and preserves the old status for updates.",
    )
    parser.add_argument("--notes", default=None, help="Optional free-text notes tied to this job.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).resolve()

    if args.archive:
        if not args.job_id:
            raise SystemExit("--archive requires --job-id")
        archived = archive_background_job(args.job_id, root=root, archive_reason=args.archive_reason)
        print(json.dumps({"archived": True, "job": archived}, ensure_ascii=False, indent=2))
        return 0

    existing = get_job_record(args.job_id, root=root) if args.job_id else None
    if existing is None and args.job_id:
        create_mode = True
    else:
        create_mode = existing is None

    if create_mode:
        required = {
            "task_ref": args.task_ref,
            "lane": args.lane,
            "purpose": args.purpose,
            "command": args.command,
            "cwd": args.cwd or str(Path.cwd()),
        }
        missing = [name for name, value in required.items() if not str(value or "").strip()]
        if missing:
            raise SystemExit(f"Creating a background job requires: {', '.join(missing)}")

    cwd_value = args.cwd if args.cwd is not None else (str(Path.cwd()) if create_mode else None)

    record = upsert_background_job(
        job_id=args.job_id,
        root=root,
        task_ref=args.task_ref,
        lane=args.lane,
        purpose=args.purpose,
        command=args.command,
        cwd=cwd_value,
        pid=args.pid,
        run_dir=args.run_dir,
        status_file=args.status_file,
        log_file=args.log_file,
        expected_outputs=args.expected_outputs,
        check_command=args.check_command,
        next_check_hint=args.next_check_hint,
        decision_if_success=args.decision_if_success,
        decision_if_failure=args.decision_if_failure,
        status=args.status,
        notes=args.notes,
    )
    print(json.dumps({"created": create_mode, "job": record}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
