"""Run a lightweight LLM capacity probe for software-side throughput checks."""

from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.attentional_v2.llm_usage_summary import write_llm_usage_summary
from src.iterator_reader.llm_utils import eval_trace_context, invoke_json, llm_invocation_scope
from src.reading_runtime.job_concurrency import resolve_worker_policy, submit_inherited_context
from src.reading_runtime.llm_registry import DEFAULT_RUNTIME_PROFILE_ID


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_REQUEST_COUNT = 16


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _probe_once(run_root: Path, *, index: int, shard_id: str) -> dict[str, Any]:
    with llm_invocation_scope(
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        trace_context=eval_trace_context(
            run_root,
            eval_target="llm_capacity_probe",
            stage="capacity_probe",
            node="probe_call",
            extra={"shard_id": shard_id, "probe_index": index},
        ),
    ):
        payload = invoke_json(
            "Return JSON only.",
            'Return {"ok": true, "probe": "lightweight"} only.',
            {"ok": False},
        )
    return {
        "index": index,
        "ok": bool(isinstance(payload, dict) and payload.get("ok") is True),
        "payload": payload if isinstance(payload, dict) else {},
    }


def run_capacity_probe(
    *,
    runs_root: Path,
    run_id: str | None = None,
    request_count: int = DEFAULT_REQUEST_COUNT,
    workers: int | None = None,
    shard_id: str = "capacity_probe",
) -> dict[str, Any]:
    run_name = run_id or datetime.now(timezone.utc).strftime("llm_capacity_probe_%Y%m%d-%H%M%S")
    run_root = runs_root / run_name
    run_root.mkdir(parents=True, exist_ok=True)

    worker_policy = resolve_worker_policy(
        job_kind="llm_capacity_probe",
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        task_count=max(1, int(request_count)),
        per_worker_parallelism=1,
        explicit_max_workers=workers if workers and workers > 0 else None,
    )

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, worker_policy.worker_count), thread_name_prefix="llm-capacity-probe") as executor:
        futures = {
            submit_inherited_context(executor, _probe_once, run_root, index=index, shard_id=shard_id): index
            for index in range(max(1, int(request_count)))
        }
        for future in as_completed(futures):
            index = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:  # pragma: no cover - defensive summary path
                results.append({"index": index, "ok": False, "error": f"{type(exc).__name__}: {exc}"})

    results.sort(key=lambda item: int(item["index"]))
    _json_dump(
        run_root / "summary" / "probe_results.json",
        {
            "request_count": request_count,
            "worker_count": worker_policy.worker_count,
            "results": results,
        },
    )
    usage_summary = write_llm_usage_summary(run_root, summary_path=run_root / "summary" / "llm_usage.json")
    return {
        "run_id": run_name,
        "run_root": str(run_root),
        "request_count": request_count,
        "worker_count": worker_policy.worker_count,
        "success_count": sum(1 for item in results if item.get("ok") is True),
        "llm_usage": usage_summary,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--request-count", type=int, default=DEFAULT_REQUEST_COUNT)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--shard-id", default="capacity_probe")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    summary = run_capacity_probe(
        runs_root=Path(args.runs_root).resolve(),
        run_id=args.run_id or None,
        request_count=args.request_count,
        workers=args.workers or None,
        shard_id=str(args.shard_id),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
