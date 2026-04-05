from __future__ import annotations

import json
from pathlib import Path

from eval.attentional_v2.llm_usage_summary import write_llm_usage_summary


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_write_llm_usage_summary_aggregates_run_and_shard_metrics(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    _write_jsonl(
        run_root / "shards" / "alpha" / "outputs" / "unit" / "attentional_v2" / "_runtime" / "llm_standard.jsonl",
        [
            {
                "profile_id": "runtime_reader_default",
                "mechanism_key": "attentional_v2",
                "status": "ok",
                "attempt_count": 2,
                "started_at": "2026-04-05T10:00:00Z",
                "completed_at": "2026-04-05T10:00:10Z",
                "provider_gate_wait_ms": 20,
                "profile_gate_wait_ms": 10,
                "quota_wait_ms_total": 0,
            },
            {
                "profile_id": "runtime_reader_default",
                "mechanism_key": "attentional_v2",
                "status": "error",
                "problem_code": "network_blocked",
                "attempt_count": 1,
                "started_at": "2026-04-05T10:00:20Z",
                "completed_at": "2026-04-05T10:00:40Z",
                "provider_gate_wait_ms": 5,
                "profile_gate_wait_ms": 15,
                "quota_wait_ms_total": 100,
            },
        ],
    )
    _write_jsonl(
        run_root / "llm_traces" / "standard.jsonl",
        [
            {
                "profile_id": "eval_judge_high_trust",
                "mechanism_key": "",
                "shard_id": "alpha",
                "status": "ok",
                "attempt_count": 1,
                "started_at": "2026-04-05T10:01:00Z",
                "completed_at": "2026-04-05T10:01:05Z",
                "provider_gate_wait_ms": 0,
                "profile_gate_wait_ms": 30,
                "quota_wait_ms_total": 0,
            }
        ],
    )

    shard_summary = write_llm_usage_summary(
        run_root,
        summary_path=run_root / "shards" / "alpha" / "summary" / "llm_usage.json",
        shard_id="alpha",
    )
    run_summary = write_llm_usage_summary(run_root, summary_path=run_root / "summary" / "llm_usage.json")

    assert shard_summary["request_count"] == 3
    assert shard_summary["success_count"] == 2
    assert shard_summary["error_count"] == 1
    assert shard_summary["retry_count"] == 1
    assert shard_summary["provider_gate_wait_ms"] == 25
    assert shard_summary["profile_gate_wait_ms"] == 55
    assert shard_summary["quota_wait_ms"] == 100
    assert shard_summary["problem_code_counts"] == {"network_blocked": 1}
    assert shard_summary["by_shard"]["alpha"]["request_count"] == 3
    assert run_summary["request_count"] == 3
