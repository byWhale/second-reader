#!/usr/bin/env python3
"""Launch the registry wrapper in a detached session."""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "run_registered_job.py"
PYTHON = (ROOT / ".venv" / "bin" / "python") if (ROOT / ".venv" / "bin" / "python").exists() else Path(sys.executable)


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _extract_flag_value(args: list[str], flag: str) -> str:
    for index, value in enumerate(args):
        if value == flag and index + 1 < len(args):
            return str(args[index + 1]).strip()
        if value.startswith(f"{flag}="):
            return str(value.split("=", 1)[1]).strip()
    return ""


def _final_wrapper_args(args: list[str]) -> list[str]:
    trimmed = list(args)
    if trimmed and trimmed[0] == "--":
        trimmed = trimmed[1:]
    if not trimmed:
        raise SystemExit("Wrapper arguments are required. Pass run_registered_job.py arguments after --.")
    return trimmed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--launcher-log-file",
        default="",
        help="Optional log file for the detached wrapper process itself.",
    )
    parser.add_argument("wrapper_args", nargs=argparse.REMAINDER, help="Arguments to pass through to run_registered_job.py.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    wrapper_args = _final_wrapper_args(args.wrapper_args)

    root_value = _extract_flag_value(wrapper_args, "--root")
    root = Path(root_value).resolve() if root_value else ROOT
    job_id = _extract_flag_value(wrapper_args, "--job-id") or f"bgjob_{_timestamp_slug()}_{secrets.token_hex(4)}"
    launcher_log = (
        Path(args.launcher_log_file).resolve()
        if str(args.launcher_log_file).strip()
        else (root / "state" / "job_registry" / "logs" / f"{job_id}.launcher.log").resolve()
    )
    launcher_log.parent.mkdir(parents=True, exist_ok=True)

    command = [str(PYTHON), str(WRAPPER), *wrapper_args]
    with launcher_log.open("ab") as handle:
        process = subprocess.Popen(
            command,
            cwd=str(root),
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )

    print(
        json.dumps(
            {
                "status": "launched",
                "job_id": job_id,
                "launcher_pid": process.pid,
                "launcher_log_file": str(launcher_log),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
