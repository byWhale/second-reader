#!/usr/bin/env python3
"""Run the frozen accumulation v2 benchmark in parallel and merge shard results."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from eval.attentional_v2.accumulation_benchmark_v2 import ACTIVE_QUESTION_FAMILY  # noqa: E402
from eval.attentional_v2.llm_usage_summary import write_llm_usage_summary  # noqa: E402
from eval.attentional_v2.run_accumulation_evaluation_v2 import (  # noqa: E402
    _aggregate_results,
    _json_dump,
    _jsonl_load,
    _mechanism_keys_for_filter,
    _prepare_selection,
    _render_report,
)
from scripts.update_evaluation_catalog import build_entry, upsert_catalog_entry  # noqa: E402


PYTHON = BACKEND_ROOT / ".venv" / "bin" / "python"
RUNNER = BACKEND_ROOT / "eval" / "attentional_v2" / "run_accumulation_evaluation_v2.py"
RUNS_ROOT = BACKEND_ROOT / "eval" / "runs" / "attentional_v2"
FROZEN_MANIFEST_PATH = (
    BACKEND_ROOT / "eval" / "manifests" / "splits" / "attentional_v2_accumulation_benchmark_v2_frozen.json"
)
DEFAULT_TARGET_IDS = ("MiniMax-M2.7-personal", "MiniMax-M2.7-personal-2")
RETRYABLE_ERROR_MARKERS = (
    "ReaderLLMError",
    "timed out or interrupted",
    "quota cooldown remains active",
    "overloaded_error",
    "unknown error, 520",
    "Error code: 529",
    "network_blocked",
)
FULL_MECHANISM_SET = {"attentional_v2", "iterator_v1"}


@dataclass(frozen=True)
class ShardPlan:
    segment_id: str
    source_id: str
    book_title: str
    case_count: int
    mechanism_key: str
    target_id: str
    shard_run_id: str

    @property
    def shard_key(self) -> str:
        return f"{self.source_id}::{self.mechanism_key}"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def _assign_targets(
    *,
    selected_segments: list[dict[str, Any]],
    mechanism_keys: tuple[str, ...],
    target_ids: tuple[str, ...],
    run_id: str,
) -> list[ShardPlan]:
    if not target_ids:
        raise ValueError("at least one target id is required")
    shard_rows = [
        {
            **row,
            "mechanism_key": mechanism_key,
        }
        for row in selected_segments
        for mechanism_key in mechanism_keys
    ]
    ordered = sorted(
        shard_rows,
        key=lambda item: (
            -int(item.get("case_count", 0) or 0),
            str(item.get("mechanism_key") or ""),
            str(item.get("segment_id")),
        ),
    )
    per_mechanism_total = {mechanism_key: 0 for mechanism_key in mechanism_keys}
    for row in ordered:
        per_mechanism_total[str(row["mechanism_key"])] += 1
    target_loads = {
        mechanism_key: {target_id: 0 for target_id in target_ids}
        for mechanism_key in mechanism_keys
    }
    target_counts = {
        mechanism_key: {target_id: 0 for target_id in target_ids}
        for mechanism_key in mechanism_keys
    }
    plans: list[ShardPlan] = []
    for row in ordered:
        mechanism_key = str(row["mechanism_key"])
        max_jobs_per_target = (per_mechanism_total[mechanism_key] + len(target_ids) - 1) // len(target_ids)
        available_targets = [
            target_id for target_id in target_ids if target_counts[mechanism_key][target_id] < max_jobs_per_target
        ] or list(target_ids)
        target_id = min(
            available_targets,
            key=lambda item: (target_loads[mechanism_key][item], target_counts[mechanism_key][item], item),
        )
        case_weight = int(row.get("case_count", 0) or 0)
        target_loads[mechanism_key][target_id] += case_weight
        target_counts[mechanism_key][target_id] += 1
        source_id = str(row["source_id"])
        segment_id = str(row["segment_id"])
        plans.append(
            ShardPlan(
                segment_id=segment_id,
                source_id=source_id,
                book_title=str(row["book_title"]),
                case_count=case_weight,
                mechanism_key=mechanism_key,
                target_id=target_id,
                shard_run_id=f"{run_id}/shards/{source_id}__{mechanism_key}",
            )
        )
    return sorted(plans, key=lambda item: (item.segment_id, item.mechanism_key))


def _filter_plans_by_shard_keys(plans: list[ShardPlan], shard_keys: set[str]) -> list[ShardPlan]:
    if not shard_keys:
        return plans
    return [plan for plan in plans if plan.shard_key in shard_keys]


def _launch_shard(
    *,
    plan: ShardPlan,
    manifest_path: Path,
    judge_mode: str,
    run_root: Path,
    reuse_output_dir: Path | None = None,
) -> subprocess.Popen[bytes]:
    shard_root = RUNS_ROOT / plan.shard_run_id
    shard_root.mkdir(parents=True, exist_ok=True)
    log_path = run_root / "logs" / f"{plan.source_id}__{plan.mechanism_key}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(PYTHON),
        str(RUNNER),
        "--run-id",
        plan.shard_run_id,
        "--manifest-path",
        str(manifest_path),
        "--mechanism-filter",
        plan.mechanism_key,
        "--judge-mode",
        judge_mode,
        "--segment-id",
        plan.segment_id,
    ]
    if reuse_output_dir is not None:
        command.extend(["--reuse-output-dir", str(reuse_output_dir)])
    env = os.environ.copy()
    env["LLM_FORCE_TARGET_ID"] = plan.target_id
    handle = log_path.open("ab")
    handle.write(f"[{utc_now()}] launching {' '.join(command)}\n".encode("utf-8"))
    handle.flush()
    process = subprocess.Popen(
        command,
        cwd=str(BACKEND_ROOT),
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    process._codex_log_handle = handle  # type: ignore[attr-defined]
    return process


def _log_path_for_plan(*, run_root: Path, plan: ShardPlan) -> Path:
    return run_root / "logs" / f"{plan.source_id}__{plan.mechanism_key}.log"


def _shard_root_for_plan(plan: ShardPlan) -> Path:
    return RUNS_ROOT / plan.shard_run_id


def _same_run_output_dir(plan: ShardPlan) -> Path:
    return _shard_root_for_plan(plan) / "outputs" / plan.segment_id / plan.mechanism_key


def _source_output_dir(*, seed_run_id: str, plan: ShardPlan) -> Path:
    return RUNS_ROOT / seed_run_id / "shards" / Path(plan.shard_run_id).name / "outputs" / plan.segment_id / plan.mechanism_key


def _completed_output_dir(output_dir: Path) -> Path | None:
    run_state_path = output_dir / "_runtime" / "run_state.json"
    if not run_state_path.exists():
        return None
    try:
        payload = json.loads(run_state_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    status = str(payload.get("status") or payload.get("stage") or "")
    if output_dir.exists() and status == "completed":
        return output_dir
    return None


def _completed_output_dir_from_same_run(*, plan: ShardPlan) -> Path | None:
    return _completed_output_dir(_same_run_output_dir(plan))


def _completed_output_dir_from_seed_runs(*, plan: ShardPlan, seed_run_ids: tuple[str, ...]) -> Path | None:
    for seed_run_id in seed_run_ids:
        completed_output_dir = _completed_output_dir(_source_output_dir(seed_run_id=seed_run_id, plan=plan))
        if completed_output_dir is not None:
            return completed_output_dir
    return None


def _resolve_ready_reuse_output_dir(*, plan: ShardPlan, seed_run_ids: tuple[str, ...]) -> Path | None:
    return _completed_output_dir_from_same_run(plan=plan) or _completed_output_dir_from_seed_runs(
        plan=plan,
        seed_run_ids=seed_run_ids,
    )


def _reset_failed_shard_outputs(plan: ShardPlan, *, preserve_output_dir: Path | None = None) -> None:
    shard_root = _shard_root_for_plan(plan)
    if not shard_root.exists():
        return
    preserved_path = preserve_output_dir.resolve() if preserve_output_dir is not None else None
    shard_root_resolved = shard_root.resolve()
    if preserved_path is None or (
        preserved_path != shard_root_resolved and shard_root_resolved not in preserved_path.parents
    ):
        shutil.rmtree(shard_root)
        return

    for child in list(shard_root.iterdir()):
        child_resolved = child.resolve()
        if child_resolved == preserved_path or child_resolved in preserved_path.parents:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _is_retryable_failure(*, log_path: Path) -> bool:
    if not log_path.exists():
        return False
    try:
        tail = "\n".join(log_path.read_text(errors="ignore").strip().splitlines()[-40:]).lower()
    except Exception:
        return False
    return any(marker.lower() in tail for marker in RETRYABLE_ERROR_MARKERS)


def _write_process_log(process: subprocess.Popen[bytes], message: str) -> None:
    log_handle = getattr(process, "_codex_log_handle", None)
    if log_handle is None:
        return
    try:
        log_handle.write(message.encode("utf-8"))
        log_handle.flush()
    except Exception:
        return


def _close_process_log(process: subprocess.Popen[bytes]) -> None:
    log_handle = getattr(process, "_codex_log_handle", None)
    if log_handle is None:
        return
    try:
        log_handle.close()
    except Exception:
        pass
    finally:
        try:
            process._codex_log_handle = None  # type: ignore[attr-defined]
        except Exception:
            pass


def _stop_remaining_processes(
    *,
    processes: dict[str, subprocess.Popen[bytes]],
    exclude_shard_key: str,
    reason: str,
) -> None:
    for shard_key, process in list(processes.items()):
        if shard_key == exclude_shard_key:
            continue
        exit_code = process.poll()
        if exit_code is not None:
            _write_process_log(process, f"[{utc_now()}] shard exited with code {exit_code}\n")
            _close_process_log(process)
            continue
        _write_process_log(
            process,
            f"[{utc_now()}] stopping shard so the parent orchestrator can fail fast and let watchdog recover the run: {reason}\n",
        )
        try:
            process.terminate()
            exit_code = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _write_process_log(process, f"[{utc_now()}] shard did not stop after SIGTERM; sending SIGKILL\n")
            process.kill()
            exit_code = process.wait(timeout=5)
        except Exception:
            exit_code = process.poll()
        if exit_code is not None:
            _write_process_log(process, f"[{utc_now()}] shard exited with code {exit_code}\n")
        _close_process_log(process)


def _wait_for_shards(
    *,
    processes: dict[str, subprocess.Popen[bytes]],
    plan_by_key: dict[str, ShardPlan],
    pending_plans: dict[str, ShardPlan] | None,
    manifest_path: Path,
    judge_mode: str,
    run_root: Path,
    max_attempts: int,
    retry_backoff_seconds: int,
    reuse_output_dirs: dict[str, Path] | None = None,
    seed_run_ids: tuple[str, ...] = (),
    wait_for_reuse_ready: bool = False,
    reuse_ready_poll_seconds: int = 30,
) -> dict[str, int]:
    exit_codes: dict[str, int] = {}
    attempts = {key: 1 for key in processes}
    reuse_output_dirs = dict(reuse_output_dirs or {})
    pending = dict(pending_plans or {})
    last_waiting_signature: tuple[str, ...] | None = None
    while processes or pending:
        launched_any = False
        for shard_key, plan in list(pending.items()):
            reuse_output_dir = reuse_output_dirs.get(shard_key)
            if reuse_output_dir is None:
                reuse_output_dir = _resolve_ready_reuse_output_dir(plan=plan, seed_run_ids=seed_run_ids)
                if reuse_output_dir is not None:
                    reuse_output_dirs[shard_key] = reuse_output_dir
            if wait_for_reuse_ready and reuse_output_dir is None:
                continue
            processes[shard_key] = _launch_shard(
                plan=plan,
                manifest_path=manifest_path,
                judge_mode=judge_mode,
                run_root=run_root,
                reuse_output_dir=reuse_output_dir,
            )
            plan_by_key[shard_key] = plan
            attempts.setdefault(shard_key, 1)
            pending.pop(shard_key, None)
            launched_any = True
        if wait_for_reuse_ready and pending:
            waiting_signature = tuple(sorted(pending))
            if waiting_signature != last_waiting_signature:
                log(
                    "Waiting for reusable excerpt outputs before launching "
                    f"{len(waiting_signature)} accumulation shard(s): {', '.join(waiting_signature)}"
                )
                last_waiting_signature = waiting_signature
        else:
            last_waiting_signature = None
        completed: list[str] = []
        progress = False
        for shard_key, process in list(processes.items()):
            exit_code = process.poll()
            if exit_code is None:
                continue
            progress = True
            _write_process_log(process, f"[{utc_now()}] shard exited with code {exit_code}\n")
            _close_process_log(process)
            plan = plan_by_key[shard_key]
            log_path = _log_path_for_plan(run_root=run_root, plan=plan)
            attempt = attempts[shard_key]
            if int(exit_code) != 0 and attempt < max_attempts and _is_retryable_failure(log_path=log_path):
                with log_path.open("ab") as handle:
                    handle.write(
                        (
                            f"[{utc_now()}] retrying shard after recoverable failure "
                            f"(attempt {attempt + 1}/{max_attempts}) in {retry_backoff_seconds}s\n"
                        ).encode("utf-8")
                    )
                    handle.flush()
                if retry_backoff_seconds > 0:
                    time.sleep(retry_backoff_seconds)
                _reset_failed_shard_outputs(plan, preserve_output_dir=reuse_output_dirs.get(shard_key))
                processes[shard_key] = _launch_shard(
                    plan=plan,
                    manifest_path=manifest_path,
                    judge_mode=judge_mode,
                    run_root=run_root,
                    reuse_output_dir=reuse_output_dirs.get(shard_key),
                )
                attempts[shard_key] = attempt + 1
                continue
            exit_codes[shard_key] = int(exit_code)
            if int(exit_code) != 0:
                reason = (
                    f"terminal shard failure for {shard_key} after {attempt} attempt(s); "
                    "remaining shard workers will stop so watchdog can relaunch the same run cleanly"
                )
                log(reason)
                _stop_remaining_processes(processes=processes, exclude_shard_key=shard_key, reason=reason)
                return exit_codes
            completed.append(shard_key)
        for shard_key in completed:
            processes.pop(shard_key, None)
        if not processes and pending and wait_for_reuse_ready:
            time.sleep(max(1, int(reuse_ready_poll_seconds)))
            continue
        if processes or pending:
            if not launched_any and not progress:
                time.sleep(5)
    return exit_codes


def _load_case_ids_by_segment(manifest_path: Path) -> tuple[dict[str, list[str]], Any]:
    selection = _prepare_selection(formal_manifest_path=manifest_path)
    case_ids_by_segment = {
        segment_id: [case.case_id for case in cases]
        for segment_id, cases in selection.cases_by_window.items()
    }
    return case_ids_by_segment, selection


def _merge_shards(
    *,
    run_id: str,
    manifest_path: Path,
    plans: list[ShardPlan],
    mechanism_keys: tuple[str, ...],
    selection: Any,
) -> dict[str, Any]:
    run_root = RUNS_ROOT / run_id
    case_ids_by_segment, _ = _load_case_ids_by_segment(manifest_path)

    merged_cases_by_id: dict[str, dict[str, Any]] = {}
    shard_summaries: list[dict[str, Any]] = []
    for plan in plans:
        shard_root = _shard_root_for_plan(plan)
        shard_summary_path = shard_root / "summary" / "aggregate.json"
        if not shard_summary_path.exists():
            raise FileNotFoundError(f"missing shard summary for {plan.shard_key}: {shard_summary_path}")
        shard_summary = json.loads(shard_summary_path.read_text(encoding="utf-8"))
        shard_summaries.append(
            {
                "source_id": plan.source_id,
                "segment_id": plan.segment_id,
                "mechanism_key": plan.mechanism_key,
                "target_id": plan.target_id,
                "shard_run_id": plan.shard_run_id,
                "case_count": shard_summary.get("case_count"),
            }
        )
        for case_id in case_ids_by_segment.get(plan.segment_id, []):
            case_path = shard_root / "cases" / f"{case_id}.json"
            if not case_path.exists():
                raise FileNotFoundError(f"missing case payload: {case_path}")
            payload = json.loads(case_path.read_text(encoding="utf-8"))
            existing = merged_cases_by_id.get(case_id)
            if existing is None:
                merged_cases_by_id[case_id] = payload
                continue
            existing_mechanisms = dict(existing.get("mechanism_results") or {})
            existing_mechanisms.update(dict(payload.get("mechanism_results") or {}))
            existing["mechanism_results"] = existing_mechanisms

    merged_case_payloads = list(merged_cases_by_id.values())
    aggregate = _aggregate_results(case_payloads=merged_case_payloads, mechanism_keys=mechanism_keys)
    aggregate.update(
        {
            "run_id": run_id,
            "generated_at": utc_now(),
            "manifest_path": str(manifest_path),
            "dataset_dir": str(selection.dataset_dir),
            "segment_count": len(selection.segments),
            "case_count": len(merged_case_payloads),
            "question_family": ACTIVE_QUESTION_FAMILY,
            "shards": shard_summaries,
        }
    )
    _json_dump(run_root / "summary" / "aggregate.json", aggregate)
    _json_dump(
        run_root / "summary" / "selection.json",
        {
            "generated_at": utc_now(),
            "segment_ids": [segment.segment_id for segment in selection.segments],
            "case_ids": [case.case_id for case in selection.cases],
        },
    )
    (run_root / "summary").mkdir(parents=True, exist_ok=True)
    (run_root / "summary" / "case_results.jsonl").write_text(
        "".join(json.dumps(payload, ensure_ascii=False) + "\n" for payload in merged_case_payloads),
        encoding="utf-8",
    )
    (run_root / "summary" / "report.md").write_text(
        _render_report(
            run_id=run_id,
            selection=selection,
            aggregate=aggregate,
            mechanism_keys=mechanism_keys,
        ),
        encoding="utf-8",
    )
    write_llm_usage_summary(run_root, summary_path=run_root / "summary" / "llm_usage.json")
    return aggregate


def _update_catalog_or_warn(
    *,
    run_id: str,
    run_root: Path,
    aggregate: dict[str, Any],
    mechanism_keys: tuple[str, ...],
    full_scope: bool,
) -> None:
    if not full_scope:
        log("Skipping evidence catalog update for partial-scope run.")
        return
    if set(mechanism_keys) != FULL_MECHANISM_SET:
        log("Skipping evidence catalog update for non-complete mechanism filter.")
        return
    try:
        mechanisms = aggregate.get("mechanisms") or {}
        v2_quality = (mechanisms.get("attentional_v2") or {}).get("average_quality_score")
        v1_quality = (mechanisms.get("iterator_v1") or {}).get("average_quality_score")
        dataset_dir = str(aggregate.get("dataset_dir") or "")
        entry = build_entry(
            run_id=run_id,
            surface="target_centered_accumulation_v2",
            status="current_formal_evidence",
            run_dir=run_root,
            dataset_id=Path(dataset_dir).name if dataset_dir else "",
            dataset_path=dataset_dir,
            manifest_path=str(aggregate.get("manifest_path") or ""),
            one_line_conclusion=(
                "Formal target-centered accumulation v2 rerun completed; "
                f"attentional_v2 average_quality_score={v2_quality}, "
                f"iterator_v1 average_quality_score={v1_quality}."
            ),
        )
        upsert_catalog_entry(entry)
        log("Updated evaluation evidence catalog for accumulation v2 run.")
    except Exception as exc:  # pragma: no cover - defensive operator logging
        log(f"WARNING: failed to update evaluation evidence catalog: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-id",
        default=f"attentional_v2_accumulation_benchmark_v2_frozen_judged_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
    )
    parser.add_argument("--manifest-path", type=Path, default=FROZEN_MANIFEST_PATH)
    parser.add_argument("--mechanism-filter", choices=("both", "attentional_v2", "iterator_v1"), default="both")
    parser.add_argument("--judge-mode", choices=("llm",), default="llm")
    parser.add_argument("--target-id", action="append", dest="target_ids", default=[])
    parser.add_argument("--segment-id", action="append", dest="segment_ids", default=[])
    parser.add_argument("--shard-key", action="append", dest="shard_keys", default=[])
    parser.add_argument("--reuse-output-run-id", action="append", dest="reuse_output_run_ids", default=[])
    parser.add_argument("--wait-for-reuse-ready", action="store_true")
    parser.add_argument("--reuse-ready-poll-seconds", type=int, default=30)
    parser.add_argument("--max-shard-attempts", type=int, default=3)
    parser.add_argument("--retry-backoff-seconds", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest_path).resolve()
    selection = _prepare_selection(formal_manifest_path=manifest_path)
    if args.segment_ids:
        wanted = set(str(item) for item in args.segment_ids)
        selected_segments = [segment for segment in selection.segments if segment.segment_id in wanted]
        selected_cases = [case for case in selection.cases if case.window_id in wanted]
        selection = type(selection)(
            dataset_dir=selection.dataset_dir,
            dataset_manifest=selection.dataset_manifest,
            case_dataset_manifests=selection.case_dataset_manifests,
            segments=selected_segments,
            cases=selected_cases,
            selected_case_ids=[case.case_id for case in selected_cases],
            cases_by_window={
                window_id: cases for window_id, cases in selection.cases_by_window.items() if window_id in wanted
            },
            formal_manifest_path=selection.formal_manifest_path,
        )
    else:
        selected_segments = list(selection.segments)
    if not selected_segments:
        raise SystemExit("no selected segments available")

    case_counts = {segment_id: len(cases) for segment_id, cases in selection.cases_by_window.items()}
    segment_rows = [
        {
            "segment_id": segment.segment_id,
            "source_id": segment.source_id,
            "book_title": segment.book_title,
            "case_count": case_counts.get(segment.segment_id, 0),
        }
        for segment in selected_segments
    ]

    target_ids = tuple(str(item) for item in (args.target_ids or list(DEFAULT_TARGET_IDS)))
    mechanism_keys = _mechanism_keys_for_filter(str(args.mechanism_filter))
    plans = _assign_targets(
        selected_segments=segment_rows,
        mechanism_keys=mechanism_keys,
        target_ids=target_ids,
        run_id=str(args.run_id),
    )
    plans = _filter_plans_by_shard_keys(plans, {str(item) for item in args.shard_keys})
    if not plans:
        raise SystemExit("no shard plans selected")

    run_root = RUNS_ROOT / str(args.run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    reuse_output_run_ids = tuple(str(item) for item in args.reuse_output_run_ids)
    if args.wait_for_reuse_ready and not reuse_output_run_ids:
        raise SystemExit("--wait-for-reuse-ready requires at least one --reuse-output-run-id")
    completed_shard_keys = {
        plan.shard_key
        for plan in plans
        if (_shard_root_for_plan(plan) / "summary" / "aggregate.json").exists()
    }
    reuse_output_dirs = {
        plan.shard_key: _resolve_ready_reuse_output_dir(plan=plan, seed_run_ids=reuse_output_run_ids) or output_dir
        for plan in plans
        if plan.shard_key not in completed_shard_keys
        and (
            (output_dir := _resolve_ready_reuse_output_dir(plan=plan, seed_run_ids=reuse_output_run_ids)) is not None
        )
    }
    launch_plans = [plan for plan in plans if plan.shard_key not in completed_shard_keys]
    _json_dump(
        run_root / "meta" / "shard_plan.json",
        {
            "generated_at": utc_now(),
            "run_id": str(args.run_id),
            "manifest_path": str(manifest_path),
            "target_ids": list(target_ids),
            "reuse_output_run_ids": list(reuse_output_run_ids),
            "wait_for_reuse_ready": bool(args.wait_for_reuse_ready),
            "reuse_ready_poll_seconds": int(args.reuse_ready_poll_seconds),
            "max_shard_attempts": int(args.max_shard_attempts),
            "retry_backoff_seconds": int(args.retry_backoff_seconds),
            "plans": [
                {
                    "segment_id": plan.segment_id,
                    "source_id": plan.source_id,
                    "book_title": plan.book_title,
                    "case_count": plan.case_count,
                    "mechanism_key": plan.mechanism_key,
                    "target_id": plan.target_id,
                    "shard_run_id": plan.shard_run_id,
                    "already_completed_in_run": plan.shard_key in completed_shard_keys,
                    "reuse_output_dir": str(reuse_output_dirs.get(plan.shard_key, "")),
                }
                for plan in plans
            ],
        },
    )

    if args.dry_run:
        print(
            json.dumps(
                {
                    "run_id": args.run_id,
                    "plans": [
                        {
                            **plan.__dict__,
                            "already_completed_in_run": plan.shard_key in completed_shard_keys,
                            "reuse_output_dir": str(reuse_output_dirs.get(plan.shard_key, "")),
                        }
                        for plan in plans
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    log(f"Launching {len(launch_plans)} accumulation v2 shard(s) under run {args.run_id}")
    if completed_shard_keys:
        log(f"Skipping {len(completed_shard_keys)} shard(s) already completed in the current run.")
    if reuse_output_dirs:
        log(f"Reusing completed reading outputs for {len(reuse_output_dirs)} shard(s).")
    exit_codes = _wait_for_shards(
        processes={},
        plan_by_key={},
        pending_plans={plan.shard_key: plan for plan in launch_plans},
        manifest_path=manifest_path,
        judge_mode=str(args.judge_mode),
        run_root=run_root,
        max_attempts=max(1, int(args.max_shard_attempts)),
        retry_backoff_seconds=max(0, int(args.retry_backoff_seconds)),
        reuse_output_dirs=reuse_output_dirs,
        seed_run_ids=reuse_output_run_ids,
        wait_for_reuse_ready=bool(args.wait_for_reuse_ready),
        reuse_ready_poll_seconds=max(1, int(args.reuse_ready_poll_seconds)),
    )
    _json_dump(run_root / "meta" / "shard_exit_codes.json", exit_codes)
    failures = {shard_key: code for shard_key, code in exit_codes.items() if int(code) != 0}
    if failures:
        write_llm_usage_summary(run_root, summary_path=run_root / "summary" / "llm_usage.json")
        raise SystemExit(f"one or more shards failed: {failures}")

    if args.shard_keys:
        _json_dump(
            run_root / "meta" / "last_filtered_recovery.json",
            {
                "updated_at": utc_now(),
                "run_id": str(args.run_id),
                "selected_shard_keys": [plan.shard_key for plan in plans],
                "status": "completed",
                "root_merge": "skipped",
                "reason": "shard-filtered recovery runs must not overwrite the run-level aggregate/report",
            },
        )
        write_llm_usage_summary(run_root, summary_path=run_root / "summary" / "llm_usage.json")
        log(
            "Completed shard-filtered accumulation v2 recovery "
            f"{args.run_id}; skipped root merge to preserve full-run summary ownership."
        )
        return 0

    aggregate = _merge_shards(
        run_id=str(args.run_id),
        manifest_path=manifest_path,
        plans=plans,
        mechanism_keys=mechanism_keys,
        selection=selection,
    )
    _update_catalog_or_warn(
        run_id=str(args.run_id),
        run_root=run_root,
        aggregate=aggregate,
        mechanism_keys=mechanism_keys,
        full_scope=not bool(args.segment_ids or args.shard_keys),
    )
    quality_parts = [
        f"{mechanism_key}_quality={aggregate['mechanisms'][mechanism_key]['average_quality_score']}"
        for mechanism_key in mechanism_keys
    ]
    log(f"Completed accumulation v2 run {args.run_id}: cases={aggregate['case_count']}, {', '.join(quality_parts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
