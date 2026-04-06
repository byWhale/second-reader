#!/usr/bin/env python3
"""Promote excerpt surface v1.1 judged shards as soon as their smoke units are ready."""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.reading_runtime.background_job_registry import (  # noqa: E402
    TERMINAL_JOB_STATUSES,
    get_job_record,
    refresh_background_jobs,
)
from eval.attentional_v2.run_excerpt_comparison import excerpt_unit_is_ready_for_judging  # noqa: E402


TASK_REF = "TASK-EXCERPT-SURFACE-V1.1"
MANIFEST_PATH = "eval/manifests/splits/attentional_v2_excerpt_surface_v1_1_draft.json"
SMOKE_RUN_ID = "attentional_v2_excerpt_surface_v1_1_smoke_20260406"
JUDGED_RUN_ID = "attentional_v2_excerpt_surface_v1_1_judged_20260406"
SMOKE_JOB_IDS = (
    "bgjob_excerpt_surface_v1_1_smoke_shard_a_20260406",
    "bgjob_excerpt_surface_v1_1_smoke_shard_b_20260406",
)
JUDGED_RUNTIME_CAP = "4"
JUDGED_JUDGE_CAP = "2"
SUCCESS_TERMINAL_STATUSES = {"completed", "ready"}


@dataclass(frozen=True)
class ShardConfig:
    shard_id: str
    judged_job_id: str
    purpose: str
    next_check_hint: str
    decision_if_success: str
    decision_if_failure: str
    unit_keys: tuple[str, ...]


SHARDS = (
    ShardConfig(
        shard_id="shard_a",
        judged_job_id="bgjob_excerpt_surface_v1_1_judged_shard_a_20260406",
        purpose="Run excerpt surface v1.1 judged shard A in fixed ROI-first order with moderate per-process caps.",
        next_check_hint="Confirm judged shard A completes both units and emits shard usage plus case outputs.",
        decision_if_success="If all judged shards complete cleanly, run the explicit judged merge.",
        decision_if_failure="Inspect judged shard A logs, bundle payloads, and llm_usage before trusting the v1.1 judged lane.",
        unit_keys=(
            "supremacy_private_en__chapter_13",
            "meiguoren_de_xingge_private_zh__chapter_19",
        ),
    ),
    ShardConfig(
        shard_id="shard_b",
        judged_job_id="bgjob_excerpt_surface_v1_1_judged_shard_b_20260406",
        purpose="Run excerpt surface v1.1 judged shard B in fixed ROI-first order with moderate per-process caps.",
        next_check_hint="Confirm judged shard B completes both units and emits shard usage plus case outputs.",
        decision_if_success="If all judged shards complete cleanly, run the explicit judged merge.",
        decision_if_failure="Inspect judged shard B logs, bundle payloads, and llm_usage before trusting the v1.1 judged lane.",
        unit_keys=(
            "nawaer_baodian_private_zh__chapter_13",
            "nawaer_baodian_private_zh__chapter_22",
        ),
    ),
    ShardConfig(
        shard_id="shard_c",
        judged_job_id="bgjob_excerpt_surface_v1_1_judged_shard_c_20260406",
        purpose="Run excerpt surface v1.1 judged shard C in fixed ROI-first order with moderate per-process caps.",
        next_check_hint="Confirm judged shard C completes both units and emits shard usage plus case outputs.",
        decision_if_success="If all judged shards complete cleanly, run the explicit judged merge.",
        decision_if_failure="Inspect judged shard C logs, bundle payloads, and llm_usage before trusting the v1.1 judged lane.",
        unit_keys=(
            "xidaduo_private_zh__chapter_15",
            "huochu_shengming_de_yiyi_private_zh__chapter_8",
        ),
    ),
    ShardConfig(
        shard_id="shard_d",
        judged_job_id="bgjob_excerpt_surface_v1_1_judged_shard_d_20260406",
        purpose="Run excerpt surface v1.1 judged shard D in fixed ROI-first order with moderate per-process caps.",
        next_check_hint="Confirm judged shard D completes the heavy tail unit and emits shard usage plus case outputs.",
        decision_if_success="If all judged shards complete cleanly, run the explicit judged merge.",
        decision_if_failure="Inspect judged shard D logs, bundle payloads, and llm_usage before trusting the v1.1 judged lane.",
        unit_keys=("value_of_others_private_en__chapter_8",),
    ),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-seconds", type=int, default=60, help="Polling cadence while waiting on shard jobs.")
    return parser


def run_command(args: list[str], *, label: str) -> None:
    log(f"{label}: {' '.join(shlex.quote(part) for part in args)}")
    subprocess.run(args, cwd=BACKEND_ROOT, check=True)


def run_dir(run_id: str) -> Path:
    return BACKEND_ROOT / "eval" / "runs" / "attentional_v2" / run_id


def summary_outputs_exist(run_id: str) -> bool:
    summary_dir = run_dir(run_id) / "summary"
    return (summary_dir / "aggregate.json").exists() and (summary_dir / "report.md").exists()


def _refresh_job_statuses(job_ids: tuple[str, ...], *, label: str) -> dict[str, str]:
    if not job_ids:
        return {}
    refreshed = refresh_background_jobs(root=BACKEND_ROOT, job_ids=job_ids)
    observed = {str(item.get("job_id", "")): str(item.get("status", "")) for item in refreshed}
    missing = [job_id for job_id in job_ids if job_id not in observed]
    if missing:
        raise RuntimeError(f"Missing job records while waiting for {label}: {missing}")
    failures = {
        job_id: status
        for job_id, status in observed.items()
        if status in TERMINAL_JOB_STATUSES and status not in SUCCESS_TERMINAL_STATUSES
    }
    if failures:
        raise RuntimeError(f"{label} stopped with non-success terminal statuses: {failures}")
    return observed


def _log_mapping_if_changed(
    label: str,
    current: dict[str, object],
    *,
    previous: dict[str, object],
) -> dict[str, object]:
    if current != previous:
        log(f"{label}: {current}")
        return dict(current)
    return previous


def _wait_for_job_record(job_id: str, *, timeout_seconds: float = 5.0, poll_seconds: float = 0.1) -> dict[str, object] | None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() <= deadline:
        record = get_job_record(job_id, root=BACKEND_ROOT)
        if record is not None:
            return record
        time.sleep(poll_seconds)
    return None


def merge_smoke() -> None:
    if summary_outputs_exist(SMOKE_RUN_ID):
        log("Smoke merge outputs already exist; skipping smoke merge.")
        return
    run_command(
        [
            str(BACKEND_ROOT / ".venv" / "bin" / "python"),
            "eval/attentional_v2/run_excerpt_comparison.py",
            "--formal-manifest",
            MANIFEST_PATH,
            "--run-id",
            SMOKE_RUN_ID,
            "--stage",
            "merge",
            "--target-slice",
            "both",
            "--judge-mode",
            "none",
        ],
        label="smoke merge",
    )


def judged_summary_output(shard_id: str) -> Path:
    return run_dir(JUDGED_RUN_ID) / "shards" / shard_id / "summary" / "llm_usage.json"


def build_judged_launch_args(shard: ShardConfig) -> list[str]:
    args = [
        str(BACKEND_ROOT / ".venv" / "bin" / "python"),
        "scripts/launch_registered_job_detached.py",
        "--",
        "--root",
        str(BACKEND_ROOT),
        "--job-id",
        shard.judged_job_id,
        "--task-ref",
        TASK_REF,
        "--lane",
        "mechanism_eval",
        "--purpose",
        shard.purpose,
        "--cwd",
        str(BACKEND_ROOT),
        "--run-dir",
        str(run_dir(JUDGED_RUN_ID)),
        "--expected-output",
        str(judged_summary_output(shard.shard_id)),
        "--next-check-hint",
        shard.next_check_hint,
        "--decision-if-success",
        shard.decision_if_success,
        "--decision-if-failure",
        shard.decision_if_failure,
        "--",
        "/usr/bin/env",
        f"LLM_PROCESS_RUNTIME_PROFILE_MAX_CONCURRENCY={JUDGED_RUNTIME_CAP}",
        f"LLM_PROCESS_EVAL_JUDGE_PROFILE_MAX_CONCURRENCY={JUDGED_JUDGE_CAP}",
        "./.venv/bin/python",
        "eval/attentional_v2/run_excerpt_comparison.py",
        "--formal-manifest",
        MANIFEST_PATH,
        "--run-id",
        JUDGED_RUN_ID,
        "--stage",
        "all",
        "--shard-id",
        shard.shard_id,
        "--target-slice",
        "both",
        "--judge-mode",
        "llm",
        "--mechanism-filter",
        "both",
        "--mechanism-execution-mode",
        "parallel",
        "--judge-execution-mode",
        "parallel",
        "--unit-workers",
        "2",
        "--judge-workers",
        "2",
        "--skip-existing",
    ]
    for unit_key in shard.unit_keys:
        args.extend(["--unit-key", unit_key])
    return args


def _smoke_run_root() -> Path:
    return run_dir(SMOKE_RUN_ID)


def _shard_ready_for_judging(smoke_run_root: Path, *, shard: ShardConfig) -> bool:
    return all(
        excerpt_unit_is_ready_for_judging(smoke_run_root, unit_key=unit_key, mechanism_filter="both")
        for unit_key in shard.unit_keys
    )


def judged_shard_readiness(smoke_run_root: Path) -> dict[str, bool]:
    return {shard.shard_id: _shard_ready_for_judging(smoke_run_root, shard=shard) for shard in SHARDS}


def ensure_ready_judged_shards_launched(*, ready_shard_ids: set[str]) -> tuple[str, ...]:
    job_ids: list[str] = []
    for shard in SHARDS:
        record = get_job_record(shard.judged_job_id, root=BACKEND_ROOT)
        if record is None and shard.shard_id not in ready_shard_ids:
            continue
        job_ids.append(shard.judged_job_id)
        if record is None:
            run_command(build_judged_launch_args(shard), label=f"launch judged {shard.shard_id}")
            record = _wait_for_job_record(shard.judged_job_id)
            if record is None:
                raise RuntimeError(f"Judged shard job {shard.judged_job_id} did not materialize in the registry after launch.")
            continue

        status = str(record.get("status", "")).strip().lower()
        if status in TERMINAL_JOB_STATUSES and status not in SUCCESS_TERMINAL_STATUSES:
            raise RuntimeError(
                f"Judged shard job {shard.judged_job_id} already exists with non-success terminal status {status}; "
                "manual recovery is required before auto-resume."
            )
    return tuple(job_ids)


def merge_judged() -> None:
    if summary_outputs_exist(JUDGED_RUN_ID):
        log("Judged merge outputs already exist; skipping judged merge.")
        return
    run_command(
        [
            str(BACKEND_ROOT / ".venv" / "bin" / "python"),
            "eval/attentional_v2/run_excerpt_comparison.py",
            "--formal-manifest",
            MANIFEST_PATH,
            "--run-id",
            JUDGED_RUN_ID,
            "--stage",
            "merge",
            "--target-slice",
            "both",
            "--judge-mode",
            "llm",
        ],
        label="judged merge",
    )


def orchestrate_excerpt_surface_v1_1_eval(*, poll_seconds: int) -> int:
    smoke_statuses: dict[str, object] = {}
    judged_statuses: dict[str, object] = {}
    readiness_statuses: dict[str, object] = {}
    smoke_merged = summary_outputs_exist(SMOKE_RUN_ID)
    judged_merged = summary_outputs_exist(JUDGED_RUN_ID)
    smoke_run_root = _smoke_run_root()

    while True:
        current_smoke_statuses = _refresh_job_statuses(SMOKE_JOB_IDS, label="excerpt surface v1.1 smoke")
        smoke_statuses = _log_mapping_if_changed(
            "excerpt surface v1.1 smoke statuses",
            current_smoke_statuses,
            previous=smoke_statuses,
        )

        current_readiness = judged_shard_readiness(smoke_run_root)
        readiness_statuses = _log_mapping_if_changed(
            "excerpt surface v1.1 judged shard readiness",
            current_readiness,
            previous=readiness_statuses,
        )
        ready_shard_ids = {shard_id for shard_id, ready in current_readiness.items() if ready}
        judged_job_ids = ensure_ready_judged_shards_launched(ready_shard_ids=ready_shard_ids)

        if all(status in SUCCESS_TERMINAL_STATUSES for status in current_smoke_statuses.values()) and not smoke_merged:
            merge_smoke()
            smoke_merged = True

        current_judged_statuses = _refresh_job_statuses(judged_job_ids, label="excerpt surface v1.1 judged")
        judged_statuses = _log_mapping_if_changed(
            "excerpt surface v1.1 judged statuses",
            current_judged_statuses,
            previous=judged_statuses,
        )

        if (
            smoke_merged
            and not judged_merged
            and len(judged_job_ids) == len(SHARDS)
            and all(status in SUCCESS_TERMINAL_STATUSES for status in current_judged_statuses.values())
        ):
            merge_judged()
            judged_merged = True

        if smoke_merged and judged_merged:
            log("Excerpt surface v1.1 smoke and judged pipeline completed.")
            return 0

        time.sleep(poll_seconds)


def main() -> int:
    args = build_parser().parse_args()
    return orchestrate_excerpt_surface_v1_1_eval(poll_seconds=args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
