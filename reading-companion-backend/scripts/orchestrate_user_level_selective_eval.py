#!/usr/bin/env python3
"""Run the active user-level selective benchmark in parallel and merge shard results."""

from __future__ import annotations

import argparse
import json
import os
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

from eval.attentional_v2.llm_usage_summary import write_llm_usage_summary  # noqa: E402
from eval.attentional_v2.run_user_level_selective_comparison import (  # noqa: E402
    MANIFEST_PATH,
    _aggregate_results,
    _json_dump,
    _jsonl_load,
    _render_report,
)


PYTHON = BACKEND_ROOT / ".venv" / "bin" / "python"
RUNNER = BACKEND_ROOT / "eval" / "attentional_v2" / "run_user_level_selective_comparison.py"
RUNS_ROOT = BACKEND_ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_TARGET_IDS = ("MiniMax-M2.7-personal", "MiniMax-M2.7-personal-2")


@dataclass(frozen=True)
class SegmentPlan:
    segment_id: str
    source_id: str
    book_title: str
    covered_note_count: int
    target_id: str
    shard_run_id: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(message: str) -> None:
    print(f"[{utc_now()}] {message}", flush=True)


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _load_segment_note_ids(dataset_dir: Path) -> dict[str, list[str]]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    note_cases = _jsonl_load(dataset_dir / str(manifest["note_cases_file"]))
    by_segment: dict[str, list[str]] = {}
    for row in note_cases:
        segment_id = str(row["segment_id"])
        by_segment.setdefault(segment_id, []).append(str(row["note_case_id"]))
    return by_segment


def _assign_targets(
    *,
    selected_segments: list[dict[str, Any]],
    target_ids: tuple[str, ...],
    run_id: str,
) -> list[SegmentPlan]:
    if not target_ids:
        raise ValueError("at least one target id is required")
    ordered = sorted(
        selected_segments,
        key=lambda item: (-int(item.get("covered_note_count", 0) or 0), str(item.get("segment_id"))),
    )
    target_loads = {target_id: 0 for target_id in target_ids}
    target_counts = {target_id: 0 for target_id in target_ids}
    max_jobs_per_target = (len(ordered) + len(target_ids) - 1) // len(target_ids)
    plans: list[SegmentPlan] = []
    for row in ordered:
        available_targets = [
            target_id for target_id in target_ids if target_counts[target_id] < max_jobs_per_target
        ] or list(target_ids)
        target_id = min(available_targets, key=lambda item: (target_loads[item], target_counts[item], item))
        note_weight = int(row.get("covered_note_count", 0) or 0)
        target_loads[target_id] += note_weight
        target_counts[target_id] += 1
        source_id = str(row["source_id"])
        segment_id = str(row["segment_id"])
        plans.append(
            SegmentPlan(
                segment_id=segment_id,
                source_id=source_id,
                book_title=str(row["book_title"]),
                covered_note_count=note_weight,
                target_id=target_id,
                shard_run_id=f"{run_id}/shards/{source_id}",
            )
        )
    return sorted(plans, key=lambda item: item.segment_id)


def _launch_shard(
    *,
    plan: SegmentPlan,
    manifest_path: Path,
    mechanism_filter: str,
    judge_mode: str,
    run_root: Path,
) -> subprocess.Popen[bytes]:
    shard_root = RUNS_ROOT / plan.shard_run_id
    shard_root.mkdir(parents=True, exist_ok=True)
    log_path = run_root / "logs" / f"{plan.source_id}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        str(PYTHON),
        str(RUNNER),
        "--run-id",
        plan.shard_run_id,
        "--manifest-path",
        str(manifest_path),
        "--mechanism-filter",
        mechanism_filter,
        "--judge-mode",
        judge_mode,
        "--segment-id",
        plan.segment_id,
    ]
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


def _wait_for_shards(processes: dict[str, subprocess.Popen[bytes]]) -> dict[str, int]:
    exit_codes: dict[str, int] = {}
    while processes:
        completed: list[str] = []
        for source_id, process in processes.items():
            exit_code = process.poll()
            if exit_code is None:
                continue
            log_handle = getattr(process, "_codex_log_handle", None)
            if log_handle is not None:
                try:
                    log_handle.write(f"[{utc_now()}] shard exited with code {exit_code}\n".encode("utf-8"))
                    log_handle.flush()
                    log_handle.close()
                except Exception:
                    pass
            exit_codes[source_id] = int(exit_code)
            completed.append(source_id)
        for source_id in completed:
            processes.pop(source_id, None)
        if processes:
            time.sleep(5)
    return exit_codes


def _merge_shards(
    *,
    run_id: str,
    manifest_path: Path,
    plans: list[SegmentPlan],
    mechanism_keys: tuple[str, ...],
) -> dict[str, Any]:
    run_root = RUNS_ROOT / run_id
    manifest = _load_manifest(manifest_path)
    dataset_roots = [Path(item) for item in (manifest.get("source_refs") or {}).get("user_level_dataset_roots") or []]
    dataset_dir = (BACKEND_ROOT / dataset_roots[0]).resolve() if dataset_roots else (BACKEND_ROOT / "state").resolve()
    note_case_ids_by_segment = _load_segment_note_ids(dataset_dir)

    merged_note_cases: list[dict[str, Any]] = []
    shard_summaries: list[dict[str, Any]] = []
    for plan in plans:
        shard_root = RUNS_ROOT / plan.shard_run_id
        shard_summary_path = shard_root / "summary" / "aggregate.json"
        if not shard_summary_path.exists():
            raise FileNotFoundError(f"missing shard summary: {shard_summary_path}")
        shard_summary = json.loads(shard_summary_path.read_text(encoding="utf-8"))
        shard_summaries.append(
            {
                "source_id": plan.source_id,
                "segment_id": plan.segment_id,
                "target_id": plan.target_id,
                "shard_run_id": plan.shard_run_id,
                "note_case_count": shard_summary.get("note_case_count"),
            }
        )
        for note_case_id in note_case_ids_by_segment.get(plan.segment_id, []):
            note_case_path = shard_root / "note_cases" / f"{note_case_id}.json"
            if not note_case_path.exists():
                raise FileNotFoundError(f"missing note-case payload: {note_case_path}")
            merged_note_cases.append(json.loads(note_case_path.read_text(encoding="utf-8")))

    aggregate = _aggregate_results(note_case_payloads=merged_note_cases, mechanism_keys=mechanism_keys)
    aggregate.update(
        {
            "run_id": run_id,
            "generated_at": utc_now(),
            "manifest_path": str(manifest_path),
            "dataset_dir": str(dataset_dir),
            "segment_count": len(plans),
            "note_case_count": len(merged_note_cases),
            "shards": shard_summaries,
        }
    )
    _json_dump(run_root / "summary" / "aggregate.json", aggregate)
    (run_root / "summary").mkdir(parents=True, exist_ok=True)
    (run_root / "summary" / "report.md").write_text(
        _render_report(aggregate=aggregate, run_id=run_id),
        encoding="utf-8",
    )
    write_llm_usage_summary(run_root, summary_path=run_root / "summary" / "llm_usage.json")
    return aggregate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-id",
        default=f"attentional_v2_user_level_selective_v1_judged_{datetime.now(timezone.utc).strftime('%Y%m%d')}",
    )
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--mechanism-filter", choices=("both",), default="both")
    parser.add_argument("--judge-mode", choices=("llm",), default="llm")
    parser.add_argument("--target-id", action="append", dest="target_ids", default=[])
    parser.add_argument("--segment-id", action="append", dest="segment_ids", default=[])
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest_path).resolve()
    manifest = _load_manifest(manifest_path)
    selected_segments = list(manifest.get("selected_segments") or [])
    if args.segment_ids:
        wanted = set(str(item) for item in args.segment_ids)
        selected_segments = [row for row in selected_segments if str(row.get("segment_id")) in wanted]
    if not selected_segments:
        raise SystemExit("no selected segments available")

    target_ids = tuple(str(item) for item in (args.target_ids or list(DEFAULT_TARGET_IDS)))
    plans = _assign_targets(selected_segments=selected_segments, target_ids=target_ids, run_id=str(args.run_id))
    run_root = RUNS_ROOT / str(args.run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    _json_dump(
        run_root / "meta" / "shard_plan.json",
        {
            "generated_at": utc_now(),
            "run_id": str(args.run_id),
            "manifest_path": str(manifest_path),
            "target_ids": list(target_ids),
            "plans": [
                {
                    "segment_id": plan.segment_id,
                    "source_id": plan.source_id,
                    "book_title": plan.book_title,
                    "covered_note_count": plan.covered_note_count,
                    "target_id": plan.target_id,
                    "shard_run_id": plan.shard_run_id,
                }
                for plan in plans
            ],
        },
    )

    if args.dry_run:
        print(json.dumps({"run_id": args.run_id, "plans": [plan.__dict__ for plan in plans]}, ensure_ascii=False, indent=2))
        return 0

    log(f"Launching {len(plans)} user-level selective shard(s) under run {args.run_id}")
    processes = {
        plan.source_id: _launch_shard(
            plan=plan,
            manifest_path=manifest_path,
            mechanism_filter=str(args.mechanism_filter),
            judge_mode=str(args.judge_mode),
            run_root=run_root,
        )
        for plan in plans
    }
    exit_codes = _wait_for_shards(processes)
    _json_dump(run_root / "meta" / "shard_exit_codes.json", exit_codes)
    failures = {source_id: code for source_id, code in exit_codes.items() if int(code) != 0}
    if failures:
        write_llm_usage_summary(run_root, summary_path=run_root / "summary" / "llm_usage.json")
        raise SystemExit(f"one or more shards failed: {failures}")

    aggregate = _merge_shards(
        run_id=str(args.run_id),
        manifest_path=manifest_path,
        plans=plans,
        mechanism_keys=("attentional_v2", "iterator_v1"),
    )
    log(
        "Completed user-level selective run "
        f"{args.run_id}: note_cases={aggregate['note_case_count']}, "
        f"attentional_v2_recall={aggregate['mechanisms']['attentional_v2']['note_recall']}, "
        f"iterator_v1_recall={aggregate['mechanisms']['iterator_v1']['note_recall']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
