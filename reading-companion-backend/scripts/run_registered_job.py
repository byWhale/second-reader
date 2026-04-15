#!/usr/bin/env python3
"""Launch one generic long-running job under the unified registry wrapper."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.reading_runtime.background_job_registry import (  # noqa: E402
    generate_job_id,
    job_registry_dir,
    refresh_background_jobs,
    upsert_background_job,
)


def _timestamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default_log_file(job_id: str, root: Path) -> Path:
    path = job_registry_dir(root) / "logs" / f"{job_id}.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="Backend root that owns state/job_registry.")
    parser.add_argument("--job-id", default="", help="Stable job id. Defaults to a generated bgjob id.")
    parser.add_argument("--task-ref", required=True, help="Execution tracker or roadmap reference.")
    parser.add_argument("--lane", required=True, help="Work lane, for example mechanism_eval or dataset_growth.")
    parser.add_argument("--purpose", required=True, help="Human-readable purpose.")
    parser.add_argument("--cwd", default="", help="Working directory for the wrapped command.")
    parser.add_argument("--run-dir", default="", help="Primary run/output directory.")
    parser.add_argument("--log-file", default="", help="Log file path. Defaults to state/job_registry/logs/<job_id>.log.")
    parser.add_argument("--status-file", default="", help="Optional status JSON path.")
    parser.add_argument(
        "--expected-output",
        dest="expected_outputs",
        action="append",
        default=None,
        help="Expected output path. Repeat this flag for more than one path.",
    )
    parser.add_argument("--check-command", default="", help="Optional shell check run after the wrapped command exits.")
    parser.add_argument("--next-check-hint", default="", help="Human hint for follow-up verification.")
    parser.add_argument("--decision-if-success", default="", help="Decision note on success.")
    parser.add_argument("--decision-if-failure", default="", help="Decision note on failure.")
    parser.add_argument("--notes", default="", help="Optional free-text note.")
    parser.add_argument(
        "--shell-command",
        default="",
        help="Optional shell command string launched via $SHELL -lc. Preserves the stored command text across relaunches.",
    )
    parser.add_argument("--auto-recovery-mode", default=None, choices=["off", "recoverable", "always"])
    parser.add_argument("--auto-recovery-interval-seconds", type=int, default=None)
    parser.add_argument("--auto-recovery-max-relaunches", type=int, default=None)
    parser.add_argument("--auto-recovery-relaunch-count", type=int, default=None)
    parser.add_argument("--auto-recovery-last-relaunch-at", default=None)
    parser.add_argument("--auto-recovery-last-relaunch-reason", default=None)
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Wrapped command. Prefix with -- before the command.")
    return parser


def _final_command(command: list[str], *, shell_command: str) -> tuple[list[str], str]:
    shell_text = str(shell_command or "").strip()
    if shell_text:
        shell_path = Path(os.environ.get("SHELL", "/bin/zsh"))
        return [str(shell_path), "-lc", shell_text], shell_text
    trimmed = list(command)
    if trimmed and trimmed[0] == "--":
        trimmed = trimmed[1:]
    if not trimmed:
        raise SystemExit("Wrapped command is required. Pass it after --.")
    return trimmed, " ".join(trimmed)


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).resolve()
    job_id = str(args.job_id).strip() or generate_job_id("bgjob")
    cwd = Path(args.cwd).resolve() if str(args.cwd).strip() else root
    command, stored_command = _final_command(args.command, shell_command=args.shell_command)
    log_file = Path(args.log_file).resolve() if str(args.log_file).strip() else _default_log_file(job_id, root)

    upsert_background_job(
        job_id=job_id,
        root=root,
        task_ref=args.task_ref,
        lane=args.lane,
        purpose=args.purpose,
        command=stored_command,
        cwd=str(cwd),
        run_dir=args.run_dir or None,
        status_file=args.status_file or None,
        log_file=str(log_file),
        expected_outputs=args.expected_outputs,
        check_command=args.check_command or None,
        next_check_hint=args.next_check_hint or None,
        decision_if_success=args.decision_if_success or None,
        decision_if_failure=args.decision_if_failure or None,
        status="registered",
        notes=args.notes or None,
        auto_recovery_mode=args.auto_recovery_mode,
        auto_recovery_interval_seconds=args.auto_recovery_interval_seconds,
        auto_recovery_max_relaunches=args.auto_recovery_max_relaunches,
        auto_recovery_relaunch_count=args.auto_recovery_relaunch_count,
        auto_recovery_last_relaunch_at=args.auto_recovery_last_relaunch_at,
        auto_recovery_last_relaunch_reason=args.auto_recovery_last_relaunch_reason,
    )

    process: subprocess.Popen[bytes] | None = None
    termination_signal: int | None = None
    started_at = _timestamp()
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("ab") as log_handle:
            banner = f"[{started_at}] launching: {' '.join(command)}\n"
            log_handle.write(banner.encode("utf-8"))
            log_handle.flush()

            def _handle_termination(signum: int, _frame) -> None:
                nonlocal termination_signal
                termination_signal = signum
                notice = f"[{_timestamp()}] wrapper received signal {signum}; forwarding to child\n"
                try:
                    log_handle.write(notice.encode("utf-8"))
                    log_handle.flush()
                except Exception:
                    pass
                if process is not None and process.poll() is None:
                    try:
                        process.send_signal(signum)
                    except OSError:
                        pass

            previous_sigterm = signal.signal(signal.SIGTERM, _handle_termination)
            previous_sighup = signal.signal(signal.SIGHUP, _handle_termination)
            process = subprocess.Popen(
                command,
                cwd=str(cwd),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            upsert_background_job(
                job_id=job_id,
                root=root,
                status="running",
                pid=process.pid,
                log_file=str(log_file),
                started_at=started_at,
            )
            exit_code = process.wait()
            signal.signal(signal.SIGTERM, previous_sigterm)
            signal.signal(signal.SIGHUP, previous_sighup)
    except KeyboardInterrupt:
        if process is not None:
            try:
                process.send_signal(signal.SIGTERM)
            except OSError:
                pass
        ended_at = _timestamp()
        upsert_background_job(
            job_id=job_id,
            root=root,
            status="abandoned",
            pid=None,
            ended_at=ended_at,
            error="Registry wrapper interrupted before completion.",
        )
        refresh_background_jobs(root=root, job_ids=[job_id], run_check_commands=bool(args.check_command))
        raise
    except Exception as exc:
        ended_at = _timestamp()
        upsert_background_job(
            job_id=job_id,
            root=root,
            status="failed",
            pid=None,
            ended_at=ended_at,
            error=str(exc),
        )
        refresh_background_jobs(root=root, job_ids=[job_id], run_check_commands=bool(args.check_command))
        raise

    ended_at = _timestamp()
    upsert_background_job(
        job_id=job_id,
        root=root,
        status="abandoned" if termination_signal is not None else ("running" if exit_code == 0 else "failed"),
        pid=None,
        exit_code=exit_code,
        ended_at=ended_at,
        error=(
            f"Registry wrapper received signal {termination_signal}."
            if termination_signal is not None
            else (None if exit_code == 0 else f"Wrapped command exited with code {exit_code}.")
        ),
    )
    refreshed = refresh_background_jobs(root=root, job_ids=[job_id], run_check_commands=bool(args.check_command))
    payload = {"job_id": job_id, "exit_code": exit_code, "refreshed": refreshed}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return int(exit_code)


if __name__ == "__main__":
    raise SystemExit(main())
