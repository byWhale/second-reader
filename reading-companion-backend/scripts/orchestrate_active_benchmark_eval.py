#!/usr/bin/env python3
"""Run the active excerpt + long-span benchmark rerun with durable child jobs."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.reading_runtime.background_job_registry import (  # noqa: E402
    TERMINAL_JOB_STATUSES,
    get_job_record,
    refresh_background_jobs,
    relaunch_background_job,
)


PYTHON = BACKEND_ROOT / ".venv" / "bin" / "python"
DETACHED_LAUNCHER = BACKEND_ROOT / "scripts" / "launch_registered_job_detached.py"
RUNS_ROOT = BACKEND_ROOT / "eval" / "runs" / "attentional_v2"
EXCERPT_ORCHESTRATOR = BACKEND_ROOT / "scripts" / "orchestrate_user_level_selective_eval.py"
ACCUMULATION_ORCHESTRATOR = BACKEND_ROOT / "scripts" / "orchestrate_accumulation_v2_eval.py"
EXCERPT_MANIFEST_PATH = BACKEND_ROOT / "eval" / "manifests" / "splits" / "attentional_v2_user_level_selective_v1_draft.json"
ACCUMULATION_MANIFEST_PATH = (
    BACKEND_ROOT / "eval" / "manifests" / "splits" / "attentional_v2_accumulation_benchmark_v2_frozen.json"
)
SUCCESS_TERMINAL_STATUSES = {"completed", "ready"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _job_status(job_id: str) -> dict[str, Any] | None:
    refresh_background_jobs(root=BACKEND_ROOT, job_ids=[job_id], run_check_commands=False)
    return get_job_record(job_id, root=BACKEND_ROOT)


def _shell_command_for_python(script_path: Path, args: list[str]) -> str:
    return " ".join([shlex.quote(str(PYTHON)), shlex.quote(str(script_path)), *[shlex.quote(str(item)) for item in args]])


def _launch_child_job(
    *,
    job_id: str,
    task_ref: str,
    purpose: str,
    command_text: str,
    run_dir: Path,
    expected_outputs: list[Path],
) -> dict[str, Any]:
    wrapper_args = [
        str(PYTHON),
        str(DETACHED_LAUNCHER),
        "--",
        "--root",
        str(BACKEND_ROOT),
        "--job-id",
        job_id,
        "--task-ref",
        task_ref,
        "--lane",
        "dataset_platform",
        "--purpose",
        purpose,
        "--cwd",
        str(BACKEND_ROOT),
        "--run-dir",
        str(run_dir),
        "--auto-recovery-mode",
        "recoverable",
        "--auto-recovery-interval-seconds",
        "300",
        "--auto-recovery-max-relaunches",
        "0",
    ]
    for output_path in expected_outputs:
        wrapper_args.extend(["--expected-output", str(output_path)])
    wrapper_args.extend(["--shell-command", command_text])
    completed = subprocess.run(
        wrapper_args,
        cwd=str(BACKEND_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _ensure_child_job_running(
    *,
    job_id: str,
    task_ref: str,
    purpose: str,
    command_text: str,
    run_dir: Path,
    expected_outputs: list[Path],
) -> dict[str, Any]:
    record = _job_status(job_id)
    if record is None:
        log(f"Launching child job {job_id}")
        return _launch_child_job(
            job_id=job_id,
            task_ref=task_ref,
            purpose=purpose,
            command_text=command_text,
            run_dir=run_dir,
            expected_outputs=expected_outputs,
        )
    status = str(record.get("status") or "").strip().lower()
    if status in SUCCESS_TERMINAL_STATUSES:
        return {"status": "already_completed", "job_id": job_id}
    if status not in TERMINAL_JOB_STATUSES:
        return {"status": "already_running", "job_id": job_id}
    log(f"Relaunching child job {job_id} from terminal status {status}")
    return relaunch_background_job(job_id, root=BACKEND_ROOT, reason="parent_orchestrator_resume")


def _wait_for_child_registration(job_id: str, *, label: str, grace_seconds: int) -> dict[str, Any]:
    deadline = time.monotonic() + max(1, int(grace_seconds))
    while True:
        record = _job_status(job_id)
        if record is not None:
            return record
        if time.monotonic() >= deadline:
            raise RuntimeError(f"{label} child job never appeared in registry after launch: {job_id}")
        time.sleep(1)


def _wait_for_child_job(job_id: str, *, label: str, poll_seconds: int, status_path: Path) -> dict[str, Any]:
    while True:
        record = _job_status(job_id)
        if record is None:
            raise RuntimeError(f"{label} child job disappeared from registry: {job_id}")
        status = str(record.get("status") or "").strip().lower()
        _json_dump(
            status_path,
            {
                "updated_at": utc_now(),
                "job_id": job_id,
                "label": label,
                "status": status,
                "record": record,
            },
        )
        if status in SUCCESS_TERMINAL_STATUSES:
            return record
        if status in TERMINAL_JOB_STATUSES:
            raise RuntimeError(f"{label} child job failed with status {status}: {job_id}")
        time.sleep(max(1, int(poll_seconds)))


def _render_report(*, run_id: str, excerpt_child: dict[str, Any], accumulation_child: dict[str, Any]) -> str:
    excerpt_aggregate = json.loads(Path(str(excerpt_child["aggregate_path"])).read_text(encoding="utf-8"))
    accumulation_aggregate = json.loads(Path(str(accumulation_child["aggregate_path"])).read_text(encoding="utf-8"))
    lines = [
        f"# Active Benchmark Rerun: {run_id}",
        "",
        "## Excerpt",
        f"- run id: `{excerpt_child['run_id']}`",
        f"- job id: `{excerpt_child['job_id']}`",
        f"- note cases: `{excerpt_aggregate['note_case_count']}`",
        f"- attentional_v2 note recall: `{excerpt_aggregate['mechanisms']['attentional_v2']['note_recall']}`",
        f"- iterator_v1 note recall: `{excerpt_aggregate['mechanisms']['iterator_v1']['note_recall']}`",
        "",
        "## Long-Span",
        f"- run id: `{accumulation_child['run_id']}`",
        f"- job id: `{accumulation_child['job_id']}`",
        f"- target cases: `{accumulation_aggregate['case_count']}`",
        f"- attentional_v2 average quality score: `{accumulation_aggregate['mechanisms']['attentional_v2']['average_quality_score']}`",
        f"- iterator_v1 average quality score: `{accumulation_aggregate['mechanisms']['iterator_v1']['average_quality_score']}`",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    date_slug = datetime.now(timezone.utc).strftime("%Y%m%d")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=f"attentional_v2_active_benchmark_rerun_{date_slug}")
    parser.add_argument("--excerpt-run-id", default=f"attentional_v2_user_level_selective_v1_active_rerun_{date_slug}")
    parser.add_argument(
        "--accumulation-run-id",
        default=f"attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_{date_slug}",
    )
    parser.add_argument("--excerpt-job-id", default=f"bgjob_user_level_selective_v1_active_formal_{date_slug}")
    parser.add_argument("--accumulation-job-id", default=f"bgjob_accumulation_benchmark_v2_active_formal_{date_slug}")
    parser.add_argument("--manifest-path", type=Path, default=EXCERPT_MANIFEST_PATH)
    parser.add_argument("--accumulation-manifest-path", type=Path, default=ACCUMULATION_MANIFEST_PATH)
    parser.add_argument("--target-id", action="append", dest="target_ids", default=[])
    parser.add_argument("--poll-seconds", type=int, default=30)
    parser.add_argument("--reuse-ready-poll-seconds", type=int, default=30)
    parser.add_argument("--max-shard-attempts", type=int, default=3)
    parser.add_argument("--retry-backoff-seconds", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_root = RUNS_ROOT / str(args.run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    target_ids = [str(item) for item in (args.target_ids or ["MiniMax-M2.7-personal", "MiniMax-M2.7-personal-2"])]

    excerpt_args = [
        "--run-id",
        str(args.excerpt_run_id),
        "--manifest-path",
        str(Path(args.manifest_path).resolve()),
        "--mechanism-filter",
        "both",
        "--judge-mode",
        "llm",
        "--max-shard-attempts",
        str(int(args.max_shard_attempts)),
        "--retry-backoff-seconds",
        str(int(args.retry_backoff_seconds)),
    ]
    for target_id in target_ids:
        excerpt_args.extend(["--target-id", target_id])

    accumulation_args = [
        "--run-id",
        str(args.accumulation_run_id),
        "--manifest-path",
        str(Path(args.accumulation_manifest_path).resolve()),
        "--mechanism-filter",
        "both",
        "--judge-mode",
        "llm",
        "--max-shard-attempts",
        str(int(args.max_shard_attempts)),
        "--retry-backoff-seconds",
        str(int(args.retry_backoff_seconds)),
        "--reuse-output-run-id",
        str(args.excerpt_run_id),
        "--wait-for-reuse-ready",
        "--reuse-ready-poll-seconds",
        str(int(args.reuse_ready_poll_seconds)),
    ]
    for target_id in target_ids:
        accumulation_args.extend(["--target-id", target_id])

    excerpt_child = {
        "job_id": str(args.excerpt_job_id),
        "task_ref": "TASK-USER-LEVEL-SELECTIVE-V1",
        "purpose": "Formal active rerun for the user-level selective v1 benchmark.",
        "run_id": str(args.excerpt_run_id),
        "run_dir": RUNS_ROOT / str(args.excerpt_run_id),
        "aggregate_path": RUNS_ROOT / str(args.excerpt_run_id) / "summary" / "aggregate.json",
        "report_path": RUNS_ROOT / str(args.excerpt_run_id) / "summary" / "report.md",
        "command_text": _shell_command_for_python(EXCERPT_ORCHESTRATOR, excerpt_args),
    }
    accumulation_child = {
        "job_id": str(args.accumulation_job_id),
        "task_ref": "TASK-ACCUMULATION-BENCHMARK-V2",
        "purpose": "Formal active rerun for the frozen accumulation benchmark v2.",
        "run_id": str(args.accumulation_run_id),
        "run_dir": RUNS_ROOT / str(args.accumulation_run_id),
        "aggregate_path": RUNS_ROOT / str(args.accumulation_run_id) / "summary" / "aggregate.json",
        "report_path": RUNS_ROOT / str(args.accumulation_run_id) / "summary" / "report.md",
        "command_text": _shell_command_for_python(ACCUMULATION_ORCHESTRATOR, accumulation_args),
    }

    _json_dump(
        run_root / "meta" / "orchestration_plan.json",
        {
            "generated_at": utc_now(),
            "run_id": str(args.run_id),
            "target_ids": target_ids,
            "excerpt": {key: str(value) for key, value in excerpt_child.items()},
            "accumulation": {key: str(value) for key, value in accumulation_child.items()},
        },
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "run_id": args.run_id,
                    "target_ids": target_ids,
                    "excerpt": {key: str(value) for key, value in excerpt_child.items()},
                    "accumulation": {key: str(value) for key, value in accumulation_child.items()},
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    _ensure_child_job_running(
        job_id=excerpt_child["job_id"],
        task_ref=excerpt_child["task_ref"],
        purpose=excerpt_child["purpose"],
        command_text=excerpt_child["command_text"],
        run_dir=excerpt_child["run_dir"],
        expected_outputs=[excerpt_child["aggregate_path"], excerpt_child["report_path"]],
    )
    _wait_for_child_registration(excerpt_child["job_id"], label="excerpt", grace_seconds=15)

    _ensure_child_job_running(
        job_id=accumulation_child["job_id"],
        task_ref=accumulation_child["task_ref"],
        purpose=accumulation_child["purpose"],
        command_text=accumulation_child["command_text"],
        run_dir=accumulation_child["run_dir"],
        expected_outputs=[accumulation_child["aggregate_path"], accumulation_child["report_path"]],
    )
    _wait_for_child_registration(accumulation_child["job_id"], label="accumulation", grace_seconds=15)

    excerpt_record = _wait_for_child_job(
        excerpt_child["job_id"],
        label="excerpt",
        poll_seconds=int(args.poll_seconds),
        status_path=run_root / "meta" / "excerpt_status.json",
    )
    _json_dump(run_root / "meta" / "excerpt_completed_record.json", excerpt_record)

    accumulation_record = _wait_for_child_job(
        accumulation_child["job_id"],
        label="accumulation",
        poll_seconds=int(args.poll_seconds),
        status_path=run_root / "meta" / "accumulation_status.json",
    )
    _json_dump(run_root / "meta" / "accumulation_completed_record.json", accumulation_record)

    summary_payload = {
        "run_id": str(args.run_id),
        "generated_at": utc_now(),
        "excerpt": {
            "run_id": excerpt_child["run_id"],
            "job_id": excerpt_child["job_id"],
            "aggregate_path": str(excerpt_child["aggregate_path"]),
            "report_path": str(excerpt_child["report_path"]),
        },
        "accumulation": {
            "run_id": accumulation_child["run_id"],
            "job_id": accumulation_child["job_id"],
            "aggregate_path": str(accumulation_child["aggregate_path"]),
            "report_path": str(accumulation_child["report_path"]),
            "reused_output_run_ids": [str(args.excerpt_run_id)],
        },
    }
    _json_dump(run_root / "summary" / "aggregate.json", summary_payload)
    (run_root / "summary").mkdir(parents=True, exist_ok=True)
    (run_root / "summary" / "report.md").write_text(
        _render_report(
            run_id=str(args.run_id),
            excerpt_child=summary_payload["excerpt"],
            accumulation_child=summary_payload["accumulation"],
        ),
        encoding="utf-8",
    )
    log(
        "Completed active benchmark rerun "
        f"{args.run_id}: excerpt={args.excerpt_run_id}, accumulation={args.accumulation_run_id}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
