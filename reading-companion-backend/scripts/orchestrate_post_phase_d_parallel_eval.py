#!/usr/bin/env python3
"""Run the Post-Phase-D judged validation with a two-target shard scheduler."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.reading_runtime.background_job_registry import (  # noqa: E402
    TERMINAL_JOB_STATUSES,
    get_job_record,
    refresh_background_jobs,
)


PYTHON = BACKEND_ROOT / ".venv" / "bin" / "python"
RUNS_ROOT = BACKEND_ROOT / "eval" / "runs" / "attentional_v2"

TASK_REF = "TASK-ATTENTIONAL-V2-STRUCTURAL-REWORK"
TARGET_IDS = ("MiniMax-M2.7-personal", "MiniMax-M2.7-personal-2")
SUCCESS_TERMINAL_STATUSES = {"completed", "ready"}

LONG_RUN_ID = "attentional_v2_post_phase_d_longspan_judged_20260413"
LONG_FORMAL_MANIFEST = BACKEND_ROOT / "eval" / "manifests" / "splits" / "attentional_v2_accumulation_benchmark_v1_draft.json"
LONG_BASELINE_RUN = RUNS_ROOT / "attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407"
LONG_SMOKE_RUN = RUNS_ROOT / "attentional_v2_post_phase_d_longspan_smoke_20260412"

EXCERPT_RUN_ID = "attentional_v2_post_phase_d_excerpt_regression_20260413"
EXCERPT_FORMAL_MANIFEST = BACKEND_ROOT / "eval" / "manifests" / "splits" / "attentional_v2_excerpt_surface_v1_1_draft.json"
EXCERPT_BASELINE_RUN = RUNS_ROOT / "attentional_v2_excerpt_surface_v1_1_judged_20260406"

LONG_WINDOWS = (
    "huochu_shengming_de_yiyi_private_zh__13_16",
    "steve_jobs_private_en__17",
    "value_of_others_private_en__8_10",
    "supremacy_private_en__13",
    "xidaduo_private_zh__13_15",
)
LONG_FRESH_V2_WINDOWS = (
    ("xidaduo_private_zh__13_15", 3),
    ("supremacy_private_en__13", 1),
)
LONG_SMOKE_V2_WINDOWS = (
    "huochu_shengming_de_yiyi_private_zh__13_16",
    "steve_jobs_private_en__17",
    "value_of_others_private_en__8_10",
)
LONG_JUDGE_WEIGHTS = {
    "huochu_shengming_de_yiyi_private_zh__13_16": 2,
    "xidaduo_private_zh__13_15": 2,
    "steve_jobs_private_en__17": 1,
    "supremacy_private_en__13": 1,
    "value_of_others_private_en__8_10": 1,
}

EXCERPT_UNITS = (
    ("supremacy_private_en__chapter_13", 12),
    ("meiguoren_de_xingge_private_zh__chapter_19", 12),
    ("value_of_others_private_en__chapter_8", 8),
    ("huochu_shengming_de_yiyi_private_zh__chapter_8", 8),
    ("xidaduo_private_zh__chapter_15", 8),
    ("nawaer_baodian_private_zh__chapter_13", 6),
    ("nawaer_baodian_private_zh__chapter_22", 5),
)


Stage = Literal["runtime", "judge", "merge"]
Lane = Literal["longspan", "excerpt"]


@dataclass(frozen=True)
class ShardTask:
    job_id: str
    lane: Lane
    stage: Stage
    item_id: str
    shard_id: str
    run_id: str
    expected_outputs: tuple[Path, ...]
    weight: int
    target_id: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def run_root(run_id: str) -> Path:
    return RUNS_ROOT / run_id


def summary_dir(run_id: str) -> Path:
    return run_root(run_id) / "summary"


def _json_load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _json_dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _require_completed_bundle(path: Path, *, mechanism_key: str, item_id: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"Missing seed bundle for {mechanism_key} {item_id}: {path}")
    payload = _json_load(path)
    if payload.get("status") != "completed":
        raise RuntimeError(f"Seed bundle is not completed for {mechanism_key} {item_id}: {path}")
    if "normalized_eval_bundle" not in payload or "bundle_summary" not in payload:
        raise RuntimeError(f"Seed bundle is structurally incomplete for {mechanism_key} {item_id}: {path}")


def _copy_bundle(src: Path, dst: Path, *, mechanism_key: str, item_id: str) -> dict[str, str]:
    _require_completed_bundle(src, mechanism_key=mechanism_key, item_id=item_id)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return {
        "mechanism_key": mechanism_key,
        "item_id": item_id,
        "source": str(src),
        "destination": str(dst),
    }


def _find_single_bundle(run_root_path: Path, *, mechanism_key: str, item_id: str) -> Path:
    matches = sorted(run_root_path.glob(f"shards/*/bundles/{mechanism_key}/{item_id}.json"))
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected exactly one {mechanism_key} seed bundle for {item_id} under {run_root_path}; found {len(matches)}."
        )
    return matches[0]


def seed_longspan_bundles() -> list[dict[str, str]]:
    seeded: list[dict[str, str]] = []
    destination_root = run_root(LONG_RUN_ID)
    for window_id in LONG_WINDOWS:
        src = LONG_BASELINE_RUN / "shards" / "main" / "bundles" / "iterator_v1" / f"{window_id}.json"
        dst = destination_root / "shards" / "seed_iterator_v1" / "bundles" / "iterator_v1" / f"{window_id}.json"
        seeded.append(_copy_bundle(src, dst, mechanism_key="iterator_v1", item_id=window_id))
    for window_id in LONG_SMOKE_V2_WINDOWS:
        src = LONG_SMOKE_RUN / "shards" / "default" / "bundles" / "attentional_v2" / f"{window_id}.json"
        dst = destination_root / "shards" / "seed_smoke_attentional_v2" / "bundles" / "attentional_v2" / f"{window_id}.json"
        seeded.append(_copy_bundle(src, dst, mechanism_key="attentional_v2", item_id=window_id))
    return seeded


def seed_excerpt_bundles() -> list[dict[str, str]]:
    seeded: list[dict[str, str]] = []
    destination_root = run_root(EXCERPT_RUN_ID)
    for unit_id, _weight in EXCERPT_UNITS:
        src = _find_single_bundle(EXCERPT_BASELINE_RUN, mechanism_key="iterator_v1", item_id=unit_id)
        dst = destination_root / "shards" / "seed_iterator_v1" / "bundles" / "iterator_v1" / f"{unit_id}.json"
        seeded.append(_copy_bundle(src, dst, mechanism_key="iterator_v1", item_id=unit_id))
    return seeded


def seed_reusable_bundles() -> None:
    seeded = {
        "generated_at": utc_now(),
        "longspan": seed_longspan_bundles(),
        "excerpt": seed_excerpt_bundles(),
    }
    _json_dump(run_root(LONG_RUN_ID) / "meta" / "seeded_bundles.json", seeded["longspan"])
    _json_dump(run_root(EXCERPT_RUN_ID) / "meta" / "seeded_bundles.json", seeded["excerpt"])
    _json_dump(RUNS_ROOT / "post_phase_d_parallel_eval_20260413_seed_manifest.json", seeded)
    log(
        "Seeded reusable bundles: "
        f"longspan={len(seeded['longspan'])}, excerpt={len(seeded['excerpt'])}"
    )


def long_runtime_tasks() -> list[ShardTask]:
    return [
        ShardTask(
            job_id=f"bgjob_post_phase_d_runtime_longspan_{window_id}_20260413",
            lane="longspan",
            stage="runtime",
            item_id=window_id,
            shard_id=f"runtime_{window_id}",
            run_id=LONG_RUN_ID,
            expected_outputs=(
                run_root(LONG_RUN_ID) / "shards" / f"runtime_{window_id}" / "bundles" / "attentional_v2" / f"{window_id}.json",
            ),
            weight=weight,
        )
        for window_id, weight in LONG_FRESH_V2_WINDOWS
    ]


def excerpt_runtime_tasks() -> list[ShardTask]:
    return [
        ShardTask(
            job_id=f"bgjob_post_phase_d_runtime_excerpt_{unit_id}_20260413",
            lane="excerpt",
            stage="runtime",
            item_id=unit_id,
            shard_id=f"runtime_{unit_id}",
            run_id=EXCERPT_RUN_ID,
            expected_outputs=(
                run_root(EXCERPT_RUN_ID) / "shards" / f"runtime_{unit_id}" / "bundles" / "attentional_v2" / f"{unit_id}.json",
            ),
            weight=weight,
        )
        for unit_id, weight in EXCERPT_UNITS
    ]


def long_judge_tasks() -> list[ShardTask]:
    return [
        ShardTask(
            job_id=f"bgjob_post_phase_d_judge_longspan_{window_id}_20260413",
            lane="longspan",
            stage="judge",
            item_id=window_id,
            shard_id=f"judge_{window_id}",
            run_id=LONG_RUN_ID,
            expected_outputs=(
                run_root(LONG_RUN_ID) / "shards" / f"judge_{window_id}" / "summary" / "llm_usage.json",
            ),
            weight=LONG_JUDGE_WEIGHTS[window_id],
        )
        for window_id in LONG_WINDOWS
    ]


def excerpt_judge_tasks() -> list[ShardTask]:
    return [
        ShardTask(
            job_id=f"bgjob_post_phase_d_judge_excerpt_{unit_id}_20260413",
            lane="excerpt",
            stage="judge",
            item_id=unit_id,
            shard_id=f"judge_{unit_id}",
            run_id=EXCERPT_RUN_ID,
            expected_outputs=(
                run_root(EXCERPT_RUN_ID) / "shards" / f"judge_{unit_id}" / "summary" / "llm_usage.json",
            ),
            weight=max(1, round(weight / 4)),
        )
        for unit_id, weight in EXCERPT_UNITS
    ]


def merge_tasks() -> list[ShardTask]:
    return [
        ShardTask(
            job_id="bgjob_post_phase_d_merge_longspan_20260413",
            lane="longspan",
            stage="merge",
            item_id="longspan_merge",
            shard_id="merge",
            run_id=LONG_RUN_ID,
            expected_outputs=(
                summary_dir(LONG_RUN_ID) / "aggregate.json",
                summary_dir(LONG_RUN_ID) / "case_results.jsonl",
            ),
            weight=0,
        ),
        ShardTask(
            job_id="bgjob_post_phase_d_merge_excerpt_20260413",
            lane="excerpt",
            stage="merge",
            item_id="excerpt_merge",
            shard_id="merge",
            run_id=EXCERPT_RUN_ID,
            expected_outputs=(
                summary_dir(EXCERPT_RUN_ID) / "aggregate.json",
                summary_dir(EXCERPT_RUN_ID) / "case_results.jsonl",
            ),
            weight=0,
        ),
    ]


def balanced_assign(tasks: list[ShardTask], target_ids: tuple[str, ...] = TARGET_IDS) -> dict[str, list[ShardTask]]:
    queues: dict[str, list[ShardTask]] = {target_id: [] for target_id in target_ids}
    weights = {target_id: 0 for target_id in target_ids}
    for task in sorted(tasks, key=lambda item: (-item.weight, item.lane, item.item_id)):
        target_id = min(target_ids, key=lambda item: (weights[item], len(queues[item]), item))
        queues[target_id].append(replace(task, target_id=target_id))
        weights[target_id] += max(1, task.weight)
    return queues


def build_eval_command(task: ShardTask) -> list[str]:
    if task.lane == "longspan":
        command = [
            str(PYTHON),
            "-m",
            "eval.attentional_v2.run_accumulation_comparison",
            "--formal-manifest",
            str(LONG_FORMAL_MANIFEST),
            "--run-id",
            task.run_id,
            "--shard-id",
            task.shard_id,
            "--target-slice",
            "both",
            "--skip-existing",
        ]
        if task.stage == "runtime":
            command.extend(
                [
                    "--stage",
                    "bundle",
                    "--judge-mode",
                    "none",
                    "--mechanism-filter",
                    "attentional_v2",
                    "--mechanism-execution-mode",
                    "serial",
                    "--unit-workers",
                    "1",
                    "--window-case-id",
                    task.item_id,
                ]
            )
        elif task.stage == "judge":
            command.extend(
                [
                    "--stage",
                    "judge",
                    "--judge-mode",
                    "llm",
                    "--judge-execution-mode",
                    "serial",
                    "--judge-workers",
                    "1",
                    "--window-case-id",
                    task.item_id,
                ]
            )
        elif task.stage == "merge":
            command.extend(["--stage", "merge", "--judge-mode", "llm"])
        else:
            raise ValueError(f"unsupported task stage: {task.stage}")
        return command

    command = [
        str(PYTHON),
        "-m",
        "eval.attentional_v2.run_excerpt_comparison",
        "--formal-manifest",
        str(EXCERPT_FORMAL_MANIFEST),
        "--run-id",
        task.run_id,
        "--shard-id",
        task.shard_id,
        "--target-slice",
        "both",
        "--skip-existing",
    ]
    if task.stage == "runtime":
        command.extend(
            [
                "--stage",
                "bundle",
                "--judge-mode",
                "none",
                "--mechanism-filter",
                "attentional_v2",
                "--mechanism-execution-mode",
                "serial",
                "--unit-workers",
                "1",
                "--unit-key",
                task.item_id,
            ]
        )
    elif task.stage == "judge":
        command.extend(
            [
                "--stage",
                "judge",
                "--judge-mode",
                "llm",
                "--judge-execution-mode",
                "serial",
                "--judge-workers",
                "1",
                "--unit-key",
                task.item_id,
            ]
        )
    elif task.stage == "merge":
        command.extend(["--stage", "merge", "--judge-mode", "llm"])
    else:
        raise ValueError(f"unsupported task stage: {task.stage}")
    return command


def launch_registered_job(task: ShardTask) -> None:
    record = get_job_record(task.job_id, root=BACKEND_ROOT)
    if record is not None:
        status = str(record.get("status", "")).strip().lower()
        if status in SUCCESS_TERMINAL_STATUSES:
            missing = [str(path) for path in task.expected_outputs if not path.exists()]
            if missing:
                raise RuntimeError(f"Job {task.job_id} is marked {status} but expected outputs are missing: {missing}")
        elif status in TERMINAL_JOB_STATUSES and not _pid_alive(record):
            raise RuntimeError(f"Job {task.job_id} already exists with non-success terminal status {status}.")
        log(f"Job already exists, not relaunching: {task.job_id} status={status or 'unknown'}")
        return

    command = build_eval_command(task)
    wrapped_command = list(command)
    notes = f"Post-Phase-D {task.lane} {task.stage} shard={task.item_id}."
    if task.target_id:
        wrapped_command = [
            "/usr/bin/env",
            f"LLM_FORCE_TARGET_ID={task.target_id}",
            "LLM_PROCESS_RUNTIME_PROFILE_MAX_CONCURRENCY=1",
            "LLM_PROCESS_EVAL_JUDGE_PROFILE_MAX_CONCURRENCY=1",
            *command,
        ]
        notes += f" Pinned target: {task.target_id}."

    args = [
        str(PYTHON),
        "scripts/launch_registered_job_detached.py",
        "--",
        "--root",
        str(BACKEND_ROOT),
        "--job-id",
        task.job_id,
        "--task-ref",
        TASK_REF,
        "--lane",
        "mechanism_eval",
        "--purpose",
        f"Post-Phase-D {task.lane} {task.stage} shard for {task.item_id}.",
        "--cwd",
        str(BACKEND_ROOT),
        "--run-dir",
        str(run_root(task.run_id)),
        "--next-check-hint",
        "Inspect shard logs, bundle/case payloads, and llm_usage before widening evaluation.",
        "--decision-if-success",
        "Continue the Post-Phase-D targeted judged validation pipeline.",
        "--decision-if-failure",
        "Stop downstream merge for this lane and diagnose the failed shard first.",
        "--notes",
        notes,
    ]
    for output in task.expected_outputs:
        args.extend(["--expected-output", str(output)])
    check_command = build_check_command(task)
    if check_command:
        args.extend(["--check-command", check_command])
    args.extend(["--", *wrapped_command])
    log(f"Launching {task.job_id}: {' '.join(shlex.quote(part) for part in wrapped_command)}")
    subprocess.run(args, cwd=BACKEND_ROOT, check=True)
    _wait_for_job_to_start(task.job_id)


def build_check_command(task: ShardTask) -> str:
    if task.stage != "runtime":
        return ""
    if len(task.expected_outputs) != 1:
        return ""
    snippet = (
        "import json,sys;"
        "p=sys.argv[1];"
        "data=json.load(open(p,encoding='utf-8'));"
        "assert data.get('status')=='completed', data"
    )
    return f"{shlex.quote(str(PYTHON))} -c {shlex.quote(snippet)} {shlex.quote(str(task.expected_outputs[0]))}"


def _status_for(job_id: str, *, run_check_commands: bool = True) -> str:
    existing = get_job_record(job_id, root=BACKEND_ROOT)
    if existing is not None and _pid_alive(existing):
        return "running"
    refreshed = refresh_background_jobs(root=BACKEND_ROOT, job_ids=[job_id], run_check_commands=run_check_commands)
    if not refreshed:
        return "missing"
    return str(refreshed[0].get("status", "")).strip().lower()


def _pid_alive(record: dict[str, object]) -> bool:
    try:
        pid = int(record.get("pid") or 0)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _wait_for_job_to_start(job_id: str, *, timeout_seconds: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_status = "missing"
    while time.monotonic() <= deadline:
        record = get_job_record(job_id, root=BACKEND_ROOT)
        if record is None:
            time.sleep(0.1)
            continue
        last_status = str(record.get("status", "")).strip().lower()
        if _pid_alive(record) or last_status in TERMINAL_JOB_STATUSES:
            return
        time.sleep(0.1)
    log(f"Job {job_id} did not publish a live PID within {timeout_seconds:.1f}s; last_status={last_status}")


def _wait_for_jobs(job_ids: list[str], *, poll_seconds: int, label: str) -> None:
    if not job_ids:
        return
    last_seen: dict[str, str] = {}
    while True:
        statuses = {job_id: _status_for(job_id) for job_id in job_ids}
        if statuses != last_seen:
            log(f"{label} statuses: {statuses}")
            last_seen = dict(statuses)
        missing = [job_id for job_id in job_ids if job_id not in statuses]
        if missing:
            raise RuntimeError(f"Missing job records while waiting for {label}: {missing}")
        failures = {
            job_id: status
            for job_id, status in statuses.items()
            if status in TERMINAL_JOB_STATUSES and status not in SUCCESS_TERMINAL_STATUSES
        }
        if failures:
            raise RuntimeError(f"{label} stopped with non-success terminal statuses: {failures}")
        if all(status in SUCCESS_TERMINAL_STATUSES for status in statuses.values()):
            return
        time.sleep(poll_seconds)


def run_target_queues(queues: dict[str, list[ShardTask]], *, poll_seconds: int, label: str) -> None:
    active_by_target: dict[str, ShardTask | None] = {target_id: None for target_id in queues}
    completed_ids: set[str] = set()

    while True:
        made_progress = False
        for target_id, active in list(active_by_target.items()):
            if active is None:
                if queues[target_id]:
                    task = queues[target_id].pop(0)
                    launch_registered_job(task)
                    active_by_target[target_id] = task
                    made_progress = True
                continue

            status = _status_for(active.job_id)
            log(f"{label} target={target_id} job={active.job_id} status={status}")
            if status in TERMINAL_JOB_STATUSES and status not in SUCCESS_TERMINAL_STATUSES:
                raise RuntimeError(f"{label} job failed: {active.job_id} status={status}")
            if status in SUCCESS_TERMINAL_STATUSES:
                completed_ids.add(active.job_id)
                active_by_target[target_id] = None
                made_progress = True
                if queues[target_id]:
                    task = queues[target_id].pop(0)
                    launch_registered_job(task)
                    active_by_target[target_id] = task
                    made_progress = True

        if all(active is None for active in active_by_target.values()) and all(not queue for queue in queues.values()):
            log(f"{label} completed: {sorted(completed_ids)}")
            return
        if not made_progress:
            time.sleep(poll_seconds)


def run_merge_jobs(*, poll_seconds: int) -> None:
    tasks = merge_tasks()
    for task in tasks:
        launch_registered_job(task)
    _wait_for_jobs([task.job_id for task in tasks], poll_seconds=poll_seconds, label="merge")


def final_summary_ok() -> None:
    required = [
        summary_dir(LONG_RUN_ID) / "aggregate.json",
        summary_dir(LONG_RUN_ID) / "case_results.jsonl",
        summary_dir(EXCERPT_RUN_ID) / "aggregate.json",
        summary_dir(EXCERPT_RUN_ID) / "case_results.jsonl",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise RuntimeError(f"Post-Phase-D validation missing final outputs: {missing}")
    failures: list[dict[str, object]] = []
    for aggregate_path in (summary_dir(LONG_RUN_ID) / "aggregate.json", summary_dir(EXCERPT_RUN_ID) / "aggregate.json"):
        aggregate = _json_load(aggregate_path)
        for target_name, target_summary in dict(aggregate.get("target_summaries") or {}).items():
            if not isinstance(target_summary, dict):
                continue
            mechanism_failure_count = int(target_summary.get("mechanism_failure_count", 0) or 0)
            judge_unavailable_count = int(target_summary.get("judge_unavailable_count", 0) or 0)
            if mechanism_failure_count or judge_unavailable_count:
                failures.append(
                    {
                        "aggregate": str(aggregate_path),
                        "target": target_name,
                        "mechanism_failure_count": mechanism_failure_count,
                        "judge_unavailable_count": judge_unavailable_count,
                    }
                )
    if failures:
        raise RuntimeError(
            "Post-Phase-D validation completed but failed success criteria:\n"
            + json.dumps(failures, ensure_ascii=False, indent=2)
        )


def orchestrate(*, poll_seconds: int) -> int:
    log("Starting Post-Phase-D parallel judged validation.")
    seed_reusable_bundles()

    runtime_queues = balanced_assign([*long_runtime_tasks(), *excerpt_runtime_tasks()])
    log(
        "Runtime target queues: "
        + json.dumps({target: [task.item_id for task in tasks] for target, tasks in runtime_queues.items()}, ensure_ascii=False)
    )
    run_target_queues(runtime_queues, poll_seconds=poll_seconds, label="runtime")

    judge_queues = balanced_assign([*long_judge_tasks(), *excerpt_judge_tasks()])
    log(
        "Judge target queues: "
        + json.dumps({target: [task.item_id for task in tasks] for target, tasks in judge_queues.items()}, ensure_ascii=False)
    )
    run_target_queues(judge_queues, poll_seconds=poll_seconds, label="judge")

    run_merge_jobs(poll_seconds=poll_seconds)
    final_summary_ok()
    log("Post-Phase-D parallel judged validation completed.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-seconds", type=int, default=60, help="Polling cadence for child shard jobs.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return orchestrate(poll_seconds=max(5, int(args.poll_seconds)))


if __name__ == "__main__":
    raise SystemExit(main())
