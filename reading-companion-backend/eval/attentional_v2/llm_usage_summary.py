"""Summarize lightweight LLM usage for eval runs and shards."""

from __future__ import annotations

import json
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


TRACE_FILENAMES = ("standard.jsonl", "llm_standard.jsonl")


@dataclass(frozen=True)
class TraceEntry:
    payload: dict[str, Any]
    path: Path
    shard_id: str
    profile_id: str
    target_id: str
    mechanism_key: str
    status: str
    problem_code: str
    started_at_epoch: float
    completed_at_epoch: float


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _parse_timestamp(value: object) -> float:
    text = _clean_text(value)
    if not text:
        return 0.0
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return float(datetime.fromisoformat(text).timestamp())
    except ValueError:
        return 0.0


def _infer_shard_id(path: Path) -> str:
    parts = path.parts
    if "shards" in parts:
        index = parts.index("shards")
        if index + 1 < len(parts):
            return parts[index + 1]
    return "run"


def _iter_trace_paths(run_root: Path) -> list[Path]:
    seen: set[Path] = set()
    resolved: list[Path] = []
    for pattern in ("**/standard.jsonl", "**/llm_standard.jsonl"):
        for path in run_root.glob(pattern):
            if path.is_file():
                canonical = path.resolve()
                if canonical not in seen:
                    seen.add(canonical)
                    resolved.append(canonical)
    return sorted(resolved)


def load_trace_entries(run_root: Path, *, shard_id: str | None = None) -> list[TraceEntry]:
    entries: list[TraceEntry] = []
    for path in _iter_trace_paths(run_root):
        inferred_shard_id = _infer_shard_id(path)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(payload, dict):
                continue
            payload_shard_id = _clean_text(payload.get("shard_id")) or inferred_shard_id
            if shard_id and payload_shard_id != shard_id:
                continue
            entries.append(
                TraceEntry(
                    payload=payload,
                    path=path,
                    shard_id=payload_shard_id,
                    profile_id=_clean_text(payload.get("profile_id")),
                    target_id=_clean_text(payload.get("selected_target_id")) or _clean_text(payload.get("provider_id")),
                    mechanism_key=_clean_text(payload.get("mechanism_key")),
                    status=_clean_text(payload.get("status")).lower() or "unknown",
                    problem_code=_clean_text(payload.get("problem_code")),
                    started_at_epoch=_parse_timestamp(payload.get("started_at")),
                    completed_at_epoch=_parse_timestamp(payload.get("completed_at")),
                )
            )
    return entries


def _peak_rpm(timestamps: list[float], *, window_seconds: int) -> float:
    if not timestamps:
        return 0.0
    queue: deque[float] = deque()
    peak_count = 0
    for current in timestamps:
        queue.append(current)
        while queue and current - queue[0] > window_seconds:
            queue.popleft()
        peak_count = max(peak_count, len(queue))
    return round((peak_count * 60.0) / float(window_seconds), 3)


def _average_rpm(started_times: list[float], completed_times: list[float]) -> float:
    if not started_times:
        return 0.0
    start = min(started_times)
    end = max(completed_times) if completed_times else max(started_times)
    elapsed_seconds = max(1.0, end - start)
    return round((len(started_times) * 60.0) / elapsed_seconds, 3)


def _inflight_summary(entries: list[TraceEntry]) -> tuple[float, int]:
    intervals: list[tuple[float, int]] = []
    for entry in entries:
        start = entry.started_at_epoch
        end = entry.completed_at_epoch or start
        if start <= 0:
            continue
        if end < start:
            end = start
        intervals.append((start, 1))
        intervals.append((end, -1))
    if not intervals:
        return 0.0, 0
    intervals.sort(key=lambda item: (item[0], item[1]))
    active = 0
    last_t = intervals[0][0]
    weighted_sum = 0.0
    max_active = 0
    for current_t, delta in intervals:
        if current_t > last_t:
            weighted_sum += active * (current_t - last_t)
            last_t = current_t
        active += delta
        max_active = max(max_active, active)
    total_span = max(1.0, intervals[-1][0] - intervals[0][0])
    return round(weighted_sum / total_span, 3), max_active


def _bucketed_counts(entries: list[TraceEntry], *, key: str) -> dict[str, dict[str, int]]:
    buckets: dict[str, list[TraceEntry]] = defaultdict(list)
    for entry in entries:
        if key == "profile":
            bucket_key = entry.profile_id or "unknown"
        elif key == "target":
            bucket_key = entry.target_id or "unknown"
        elif key == "mechanism":
            bucket_key = entry.mechanism_key or "unknown"
        elif key == "shard":
            bucket_key = entry.shard_id or "run"
        else:
            bucket_key = "unknown"
        buckets[bucket_key].append(entry)
    payload: dict[str, dict[str, int]] = {}
    for bucket_key, scoped in sorted(buckets.items()):
        payload[bucket_key] = {
            "request_count": len(scoped),
            "success_count": sum(1 for entry in scoped if entry.status == "ok"),
            "error_count": sum(1 for entry in scoped if entry.status != "ok"),
            "retry_count": sum(max(0, int(entry.payload.get("attempt_count", 1) or 1) - 1) for entry in scoped),
            "problem_code_counts": dict(Counter(entry.problem_code for entry in scoped if entry.problem_code)),
        }
    return payload


def summarize_trace_entries(entries: list[TraceEntry]) -> dict[str, Any]:
    started_times = sorted(entry.started_at_epoch for entry in entries if entry.started_at_epoch > 0)
    completed_times = sorted(entry.completed_at_epoch for entry in entries if entry.completed_at_epoch > 0)
    average_inflight, max_inflight = _inflight_summary(entries)
    problem_code_counts = Counter(entry.problem_code for entry in entries if entry.problem_code)
    return {
        "request_count": len(entries),
        "success_count": sum(1 for entry in entries if entry.status == "ok"),
        "error_count": sum(1 for entry in entries if entry.status != "ok"),
        "retry_count": sum(max(0, int(entry.payload.get("attempt_count", 1) or 1) - 1) for entry in entries),
        "average_rpm": _average_rpm(started_times, completed_times),
        "peak_1m_rpm": _peak_rpm(started_times, window_seconds=60),
        "peak_5m_rpm": _peak_rpm(started_times, window_seconds=300),
        "average_inflight": average_inflight,
        "max_inflight": max_inflight,
        "provider_gate_wait_ms": sum(int(entry.payload.get("provider_gate_wait_ms", 0) or 0) for entry in entries),
        "profile_gate_wait_ms": sum(int(entry.payload.get("profile_gate_wait_ms", 0) or 0) for entry in entries),
        "quota_wait_ms": sum(int(entry.payload.get("quota_wait_ms_total", 0) or 0) for entry in entries),
        "problem_code_counts": dict(problem_code_counts),
        "by_profile": _bucketed_counts(entries, key="profile"),
        "by_target": _bucketed_counts(entries, key="target"),
        "by_mechanism": _bucketed_counts(entries, key="mechanism"),
        "by_shard": _bucketed_counts(entries, key="shard"),
    }


def write_llm_usage_summary(run_root: Path, *, summary_path: Path, shard_id: str | None = None) -> dict[str, Any]:
    entries = load_trace_entries(run_root, shard_id=shard_id)
    summary = summarize_trace_entries(entries)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


__all__ = [
    "TRACE_FILENAMES",
    "TraceEntry",
    "load_trace_entries",
    "summarize_trace_entries",
    "write_llm_usage_summary",
]
