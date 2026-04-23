#!/usr/bin/env python3
"""One-off sidecar judge for completed Long Span vNext memory-quality windows.

This is intentionally temporary: it lets us judge completed V2 probe snapshots
while the main Phase-1 runner continues reading slower windows.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
import json
import sys
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.attentional_v2.run_long_span_vnext import (  # noqa: E402
    ReadingWindow,
    _aggregate_memory_quality,
    _json_dump,
    _jsonl_dump,
    build_read_so_far_source_text,
    judge_memory_quality_probe,
)
from src.attentional_v2.benchmark_probes import load_memory_quality_probe_export  # noqa: E402
from src.reading_core.storage import book_document_file  # noqa: E402


DEFAULT_SEGMENTS = (
    "huochu_shengming_de_yiyi_private_zh__segment_1",
    "nawaer_baodian_private_zh__segment_1",
    "value_of_others_private_en__segment_1",
)


def _load_selected_windows(run_root: Path) -> dict[str, ReadingWindow]:
    payload = json.loads((run_root / "meta" / "selected_windows.json").read_text(encoding="utf-8"))
    windows = {}
    for row in payload.get("windows") or []:
        window = ReadingWindow(**row)
        windows[window.segment_id] = window
    return windows


def _build_tasks(*, run_root: Path, segment_ids: list[str]) -> list[tuple[ReadingWindow, dict[str, Any], dict[str, Any]]]:
    windows = _load_selected_windows(run_root)
    tasks: list[tuple[ReadingWindow, dict[str, Any], dict[str, Any]]] = []
    for segment_id in segment_ids:
        if segment_id not in windows:
            raise FileNotFoundError(f"segment not found in selected_windows.json: {segment_id}")
        window = windows[segment_id]
        output_dir = run_root / "outputs" / segment_id / "attentional_v2"
        probe_export = load_memory_quality_probe_export(output_dir)
        snapshots = [item for item in probe_export.get("snapshots", []) if isinstance(item, dict)]
        if len(snapshots) < 5:
            raise RuntimeError(f"segment does not have complete 5-probe export yet: {segment_id} ({len(snapshots)}/5)")
        book_document = json.loads(book_document_file(output_dir).read_text(encoding="utf-8"))
        for snapshot in snapshots:
            capture_sentence_id = str(snapshot.get("capture_sentence_id") or "").strip()
            probe_payload = {
                "probe_index": int(snapshot.get("probe_index", 0) or 0),
                "threshold_ratio": float(snapshot.get("threshold_ratio", 0.0) or 0.0),
                "read_so_far_source_text": build_read_so_far_source_text(book_document, capture_sentence_id),
                "memory_snapshot": snapshot,
            }
            tasks.append((window, snapshot, probe_payload))
    return tasks


def _render_report(*, aggregate: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Partial Memory Quality Judge",
        "",
        "This sidecar report judges only windows whose V2 probe snapshots were already complete.",
        "It is not the formal Long Span vNext summary; the main runner still owns the final `summary/` outputs.",
        "",
        "## Aggregate",
        "",
        f"- Probe count: `{aggregate.get('probe_count', 0)}`",
        f"- Window count: `{aggregate.get('window_count', 0)}`",
        f"- Average overall memory quality: `{aggregate.get('average_overall_memory_quality_score', 0.0):.3f}`",
        "",
        "## Windows",
        "",
    ]
    for window_summary in aggregate.get("windows", []):
        segment_id = str(window_summary["segment_id"])
        lines.extend(
            [
                f"### {window_summary['book_title']} (`{segment_id}`)",
                f"- Probe count: `{window_summary['probe_count']}`",
                f"- Average overall: `{window_summary['average_overall_memory_quality_score']:.3f}`",
                f"- Average salience: `{window_summary['average_salience_score']:.3f}`",
                f"- Average mainline fidelity: `{window_summary['average_mainline_fidelity_score']:.3f}`",
                f"- Average organization: `{window_summary['average_organization_score']:.3f}`",
                f"- Average fidelity: `{window_summary['average_fidelity_score']:.3f}`",
                "",
            ]
        )
        for row in sorted((item for item in rows if item["segment_id"] == segment_id), key=lambda item: item["probe_index"]):
            lines.append(
                f"- Probe `{row['probe_index']}` (`{row['threshold_ratio']:.0%}`): "
                f"overall `{row['overall_memory_quality_score']}`; {row['reason']}"
            )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--segment-id", action="append", default=[])
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--judge-mode", choices=["llm", "none"], default="llm")
    args = parser.parse_args()

    run_root = Path(args.run_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    segment_ids = args.segment_id or list(DEFAULT_SEGMENTS)
    tasks = _build_tasks(run_root=run_root, segment_ids=segment_ids)

    output_dir.mkdir(parents=True, exist_ok=True)
    _json_dump(
        output_dir / "input.json",
        {
            "run_root": str(run_root),
            "segment_ids": segment_ids,
            "task_count": len(tasks),
            "judge_mode": args.judge_mode,
        },
    )

    def _judge(task: tuple[ReadingWindow, dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
        window, snapshot, probe_payload = task
        judgment = judge_memory_quality_probe(
            run_root=output_dir,
            window=window,
            probe_payload=probe_payload,
            judge_mode=args.judge_mode,
        )
        return {
            "segment_id": window.segment_id,
            "source_id": window.source_id,
            "book_title": window.book_title,
            "mechanism_key": "attentional_v2",
            "probe_index": int(snapshot.get("probe_index", 0) or 0),
            "threshold_ratio": float(snapshot.get("threshold_ratio", 0.0) or 0.0),
            "capture_sentence_id": str(snapshot.get("capture_sentence_id") or "").strip(),
            **judgment,
        }

    results: list[dict[str, Any]] = [None] * len(tasks)  # type: ignore[list-item]
    with ThreadPoolExecutor(max_workers=max(1, int(args.workers or 1))) as executor:
        future_to_index = {executor.submit(_judge, task): index for index, task in enumerate(tasks)}
        for future in as_completed(future_to_index):
            results[future_to_index[future]] = future.result()
            _jsonl_dump(output_dir / "memory_quality_results.partial.jsonl", [item for item in results if item])

    aggregate = _aggregate_memory_quality(results)
    _jsonl_dump(output_dir / "memory_quality_results.jsonl", results)
    _json_dump(output_dir / "aggregate.json", aggregate)
    (output_dir / "report.md").write_text(_render_report(aggregate=aggregate, rows=results), encoding="utf-8")
    print(json.dumps({"output_dir": str(output_dir), "aggregate": aggregate}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
