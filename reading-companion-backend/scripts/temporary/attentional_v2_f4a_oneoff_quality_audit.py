#!/usr/bin/env python3
"""Temporary one-off harness for the April 19 Phase F4A attentional_v2 quality audit.

This script is intentionally not the general project evaluation entrypoint.
Keep it under `scripts/temporary/` unless a later task proves the behavior
deserves promotion into the shared evaluation framework.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.attentional_v2.user_level_selective_v1 import DATASET_DIR as USER_LEVEL_DATASET_DIR  # noqa: E402
from src.attentional_v2.storage import (  # noqa: E402
    chapter_result_compatibility_file,
    local_continuity_file,
    normalized_eval_bundle_file,
    reaction_records_file,
    read_audit_file,
)
from src.reading_core.runtime_contracts import ReadRequest  # noqa: E402
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism  # noqa: E402
from src.reading_runtime.output_dir_overrides import override_output_dir  # noqa: E402
from src.reading_runtime.provisioning import ensure_canonical_parse  # noqa: E402

DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_TARGET_IDS = (
    "MiniMax-M2.7-personal",
    "MiniMax-M2.7-personal-2",
)
DEFAULT_MAX_UNITS = 8
DEFAULT_USER_INTENT = (
    "Read as a thoughtful co-reader and surface visible reactions that feel like they arise during the reading itself."
)
WINDOW_CASES_DATASET = ROOT / "state" / "eval_local_datasets" / "window_cases" / "attentional_v2_accumulation_benchmark_v1_window_cases" / "windows.jsonl"

SEGMENT_CASE_IDS = {
    "huochu_shengming_de_yiyi_private_zh__segment_1",
    "xidaduo_private_zh__segment_1",
    "nawaer_baodian_private_zh__segment_1",
    "mangge_zhi_dao_private_zh__segment_1",
}
CASE_TARGET_ASSIGNMENTS = {
    "supremacy_private_en__chapter_13": DEFAULT_TARGET_IDS[0],
    "huochu_shengming_de_yiyi_private_zh__segment_1": DEFAULT_TARGET_IDS[0],
    "nawaer_baodian_private_zh__segment_1": DEFAULT_TARGET_IDS[0],
    "value_of_others_private_en__8_10": DEFAULT_TARGET_IDS[1],
    "xidaduo_private_zh__segment_1": DEFAULT_TARGET_IDS[1],
    "mangge_zhi_dao_private_zh__segment_1": DEFAULT_TARGET_IDS[1],
}
CASE_GOALS = {
    "supremacy_private_en__chapter_13": "Reaction-density regression against the old low-expression problem.",
    "value_of_others_private_en__8_10": "English cross-chapter carryover style and prior-link audit.",
    "huochu_shengming_de_yiyi_private_zh__segment_1": "Chinese restrained mainline sample.",
    "xidaduo_private_zh__segment_1": "Detour narrow-scope to land-region sample.",
    "nawaer_baodian_private_zh__segment_1": "Short local anchored reactions and prior-link sample.",
    "mangge_zhi_dao_private_zh__segment_1": "Defer-detour and outside-link/search-intent risk sample.",
}
ALL_CASE_IDS = tuple(CASE_TARGET_ASSIGNMENTS.keys())


@dataclass(frozen=True)
class AuditCase:
    case_id: str
    source_id: str
    book_title: str
    language_track: str
    source_path: str
    chapter_number: int
    max_units: int
    goal: str
    target_id: str
    source_kind: str
    source_details: dict[str, Any]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _json_load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl_load(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _segment_index() -> dict[str, dict[str, Any]]:
    manifest = _json_load(USER_LEVEL_DATASET_DIR / "manifest.json")
    segments_path = USER_LEVEL_DATASET_DIR / str(manifest["segments_file"])
    return {str(row["segment_id"]): row for row in _jsonl_load(segments_path)}


def _window_index() -> dict[str, dict[str, Any]]:
    return {str(row["window_case_id"]): row for row in _jsonl_load(WINDOW_CASES_DATASET)}


def _candidate_paragraph_texts(chapter: dict[str, Any]) -> list[str]:
    texts = [
        _clean_text(paragraph.get("text"))
        for paragraph in chapter.get("paragraphs", [])
        if isinstance(paragraph, dict) and _clean_text(paragraph.get("text"))
    ]
    if texts:
        return texts
    return [
        _clean_text(sentence.get("text"))
        for sentence in chapter.get("sentences", [])
        if isinstance(sentence, dict) and _clean_text(sentence.get("text"))
    ]


def render_window_text_from_book_document(
    book_document: dict[str, Any],
    *,
    chapter_ids: list[int],
) -> str:
    """Render a compact plain-text window from selected parsed-book chapters."""

    selected = [
        dict(chapter)
        for chapter in book_document.get("chapters", [])
        if isinstance(chapter, dict) and int(chapter.get("id", 0) or 0) in set(chapter_ids)
    ]
    parts: list[str] = []
    for chapter in selected:
        title = _clean_text(chapter.get("title")) or _clean_text(chapter.get("reference")) or "Untitled chapter"
        parts.append(title)
        parts.append("")
        for paragraph_text in _candidate_paragraph_texts(chapter):
            parts.append(paragraph_text)
            parts.append("")
    return "\n".join(parts).strip() + "\n"


def _prepare_value_of_others_window_source(run_root: Path) -> tuple[Path, dict[str, Any]]:
    windows = _window_index()
    window = dict(windows["value_of_others_private_en__8_10"])
    source_path = (ROOT / str(window["relative_local_path"])).resolve()
    provisioned = ensure_canonical_parse(source_path, language_mode=str(window.get("language_track") or "en"))
    if provisioned.book_document is None:
        raise RuntimeError("Could not build canonical parse for value_of_others_private_en.")
    chapter_ids = [int(item) for item in window.get("chapter_ids", [])]
    text = render_window_text_from_book_document(
        provisioned.book_document,
        chapter_ids=chapter_ids,
    )
    prepared_path = run_root / "_inputs" / "value_of_others_private_en__8_10.txt"
    prepared_path.parent.mkdir(parents=True, exist_ok=True)
    prepared_path.write_text(text, encoding="utf-8")
    metadata = {
        "source_kind": "generated_cross_chapter_window",
        "relative_local_path": str(window.get("relative_local_path") or ""),
        "source_chapter_ids": chapter_ids,
        "source_chapter_titles": [str(item) for item in window.get("chapter_titles", [])],
    }
    _json_dump(prepared_path.with_suffix(".meta.json"), metadata)
    return prepared_path, metadata


def _resolve_case(case_id: str, *, run_root: Path) -> AuditCase:
    if case_id in SEGMENT_CASE_IDS:
        segments = _segment_index()
        row = dict(segments[case_id])
        source_path = (USER_LEVEL_DATASET_DIR / str(row["segment_source_path"])).resolve()
        return AuditCase(
            case_id=case_id,
            source_id=str(row["source_id"]),
            book_title=str(row["book_title"]),
            language_track=str(row["language_track"]),
            source_path=str(source_path),
            chapter_number=1,
            max_units=DEFAULT_MAX_UNITS,
            goal=CASE_GOALS[case_id],
            target_id=CASE_TARGET_ASSIGNMENTS[case_id],
            source_kind="segment_source",
            source_details={
                "segment_source_path": str(row["segment_source_path"]),
                "start_sentence_id": str(row["start_sentence_id"]),
                "end_sentence_id": str(row["end_sentence_id"]),
                "source_chapter_ids": [int(item) for item in row.get("source_chapter_ids", row.get("chapter_ids", []))],
            },
        )
    if case_id == "supremacy_private_en__chapter_13":
        window = dict(_window_index()["supremacy_private_en__13"])
        source_path = (ROOT / str(window["relative_local_path"])).resolve()
        return AuditCase(
            case_id=case_id,
            source_id=str(window["source_id"]),
            book_title=str(window["book_title"]),
            language_track=str(window["language_track"]),
            source_path=str(source_path),
            chapter_number=13,
            max_units=DEFAULT_MAX_UNITS,
            goal=CASE_GOALS[case_id],
            target_id=CASE_TARGET_ASSIGNMENTS[case_id],
            source_kind="source_chapter",
            source_details={
                "window_case_id": "supremacy_private_en__13",
                "source_chapter_id": 13,
                "source_chapter_title": str(window["chapter_titles"][0]),
                "relative_local_path": str(window["relative_local_path"]),
            },
        )
    if case_id == "value_of_others_private_en__8_10":
        prepared_path, metadata = _prepare_value_of_others_window_source(run_root)
        return AuditCase(
            case_id=case_id,
            source_id="value_of_others_private_en",
            book_title="The Value of Others",
            language_track="en",
            source_path=str(prepared_path),
            chapter_number=1,
            max_units=DEFAULT_MAX_UNITS,
            goal=CASE_GOALS[case_id],
            target_id=CASE_TARGET_ASSIGNMENTS[case_id],
            source_kind="generated_cross_chapter_window",
            source_details=metadata,
        )
    raise ValueError(f"Unsupported F4A case id: {case_id}")


def _reaction_card(record: dict[str, Any]) -> dict[str, Any]:
    primary_anchor = dict(record.get("primary_anchor") or {})
    return {
        "reaction_id": _clean_text(record.get("reaction_id")),
        "compat_family": _clean_text(record.get("compat_family")),
        "anchor_quote": _clean_text(primary_anchor.get("quote")),
        "content": _clean_text(record.get("thought")),
        "prior_link": dict(record.get("prior_link") or {}) if isinstance(record.get("prior_link"), dict) else {},
        "outside_link": dict(record.get("outside_link") or {}) if isinstance(record.get("outside_link"), dict) else {},
        "search_intent": dict(record.get("search_intent") or {}) if isinstance(record.get("search_intent"), dict) else {},
    }


def _count_truthy_mappings(records: list[dict[str, Any]], key: str) -> int:
    return sum(1 for record in records if isinstance(record.get(key), dict) and bool(record.get(key)))


def _pressure_signal_counts(read_audit_entries: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "continuation_pressure": 0,
        "backward_pull": 0,
        "frame_shift_pressure": 0,
    }
    for entry in read_audit_entries:
        pressure_signals = entry.get("pressure_signals") or {}
        if not isinstance(pressure_signals, dict):
            continue
        for key in counts:
            if pressure_signals.get(key):
                counts[key] += 1
    return counts


def _detour_status_counts(read_audit_entries: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "open": 0,
        "resolved": 0,
        "abandoned": 0,
    }
    for entry in read_audit_entries:
        detour_need = entry.get("detour_need") or {}
        if not isinstance(detour_need, dict):
            continue
        status = _clean_text(detour_need.get("status")).lower()
        if status in counts:
            counts[status] += 1
    return counts


def _load_case_summary(*, case: AuditCase, output_dir: Path) -> dict[str, Any]:
    read_audit_entries = _jsonl_load(read_audit_file(output_dir)) if read_audit_file(output_dir).exists() else []
    reaction_payload = _json_load(reaction_records_file(output_dir)) if reaction_records_file(output_dir).exists() else {"records": []}
    reaction_records = [dict(item) for item in reaction_payload.get("records", []) if isinstance(item, dict)]
    local_continuity = _json_load(local_continuity_file(output_dir)) if local_continuity_file(output_dir).exists() else {}
    normalized_bundle = _json_load(normalized_eval_bundle_file(output_dir)) if normalized_eval_bundle_file(output_dir).exists() else {}
    detour_trace = [dict(item) for item in local_continuity.get("detour_trace", []) if isinstance(item, dict)]
    chapter_outputs_dir = chapter_result_compatibility_file(output_dir, 1).parent
    chapter_output_paths = sorted(str(path) for path in chapter_outputs_dir.glob("chapter-*.json"))
    surfaced_reaction_counts = [
        int(entry.get("surfaced_reaction_count", 0) or 0)
        for entry in read_audit_entries
        if isinstance(entry, dict)
    ]
    return {
        "case_id": case.case_id,
        "source_id": case.source_id,
        "book_title": case.book_title,
        "language_track": case.language_track,
        "goal": case.goal,
        "target_id": case.target_id,
        "output_dir": str(output_dir),
        "read_audit_path": str(read_audit_file(output_dir)),
        "reaction_records_path": str(reaction_records_file(output_dir)),
        "local_continuity_path": str(local_continuity_file(output_dir)),
        "normalized_eval_bundle_path": str(normalized_eval_bundle_file(output_dir)),
        "chapter_result_paths": chapter_output_paths,
        "audit_window_max_units": case.max_units,
        "formal_units_read": len(read_audit_entries),
        "visible_reaction_count": len(reaction_records),
        "silent_unit_count": sum(1 for count in surfaced_reaction_counts if count == 0),
        "detour_trace_count": len(detour_trace),
        "detour_trace": detour_trace,
        "pressure_signal_counts": _pressure_signal_counts(read_audit_entries),
        "detour_status_counts": _detour_status_counts(read_audit_entries),
        "prior_link_count": _count_truthy_mappings(reaction_records, "prior_link"),
        "outside_link_count": _count_truthy_mappings(reaction_records, "outside_link"),
        "search_intent_count": _count_truthy_mappings(reaction_records, "search_intent"),
        "sampled_reactions": [_reaction_card(record) for record in reaction_records[:6]],
        "compat_projection_available": bool(chapter_output_paths),
        "normalized_eval_available": normalized_eval_bundle_file(output_dir).exists(),
        "normalized_reaction_count": len([item for item in normalized_bundle.get("reactions", []) if isinstance(item, dict)]),
        "normalized_chapter_statuses": [
            {
                "chapter_id": int(item.get("chapter_id", 0) or 0),
                "chapter_ref": _clean_text(item.get("chapter_ref")),
                "status": _clean_text(item.get("status")),
                "visible_reaction_count": int(item.get("visible_reaction_count", 0) or 0),
            }
            for item in normalized_bundle.get("chapters", [])
            if isinstance(item, dict)
        ],
    }


def _run_case(case: AuditCase, *, run_root: Path) -> dict[str, Any]:
    shard_root = run_root / "shards" / case.case_id
    output_dir = shard_root / "outputs" / case.case_id / "attentional_v2"
    if output_dir.exists():
        import shutil

        shutil.rmtree(output_dir)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    mechanism = AttentionalV2Mechanism()
    with override_output_dir(output_dir):
        result = mechanism.read_book(
            ReadRequest(
                book_path=Path(case.source_path),
                chapter_number=case.chapter_number,
                continue_mode=False,
                user_intent=DEFAULT_USER_INTENT,
                language_mode=case.language_track,
                task_mode="sequential",
                mechanism_key="attentional_v2",
                mechanism_config={
                    "persist_normalized_eval_bundle": True,
                    "audit_window_max_units": case.max_units,
                },
            )
        )
    summary = _load_case_summary(case=case, output_dir=Path(result.output_dir))
    summary["status"] = "completed"
    return summary


def _run_worker(case_id: str, *, run_root: Path, worker_result: Path) -> int:
    case = _resolve_case(case_id, run_root=run_root)
    try:
        payload = _run_case(case, run_root=run_root)
    except Exception as exc:  # pragma: no cover - exercised by the parent process
        payload = {
            "case_id": case_id,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }
    _json_dump(worker_result, payload)
    return 0 if payload.get("status") == "completed" else 1


def _report_text(summary: dict[str, Any]) -> str:
    lines = [
        "# Phase F4A Focused Quality Audit",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- generated_at: `{summary['generated_at']}`",
        f"- cases: `{summary['case_count']}`",
        f"- completed: `{summary['completed_case_count']}`",
        f"- failed: `{summary['failed_case_count']}`",
        "",
    ]
    for case in summary.get("cases", []):
        lines.extend(
            [
                f"## {case['case_id']}",
                "",
                f"- status: `{case.get('status', '')}`",
                f"- target_id: `{case.get('target_id', '')}`",
                f"- goal: {case.get('goal', '')}",
                f"- formal_units_read: `{case.get('formal_units_read', 0)}` / cap `{case.get('audit_window_max_units', 0)}`",
                f"- visible_reaction_count: `{case.get('visible_reaction_count', 0)}`",
                f"- silent_unit_count: `{case.get('silent_unit_count', 0)}`",
                f"- detour_trace_count: `{case.get('detour_trace_count', 0)}`",
                f"- prior_link / outside_link / search_intent: `{case.get('prior_link_count', 0)} / {case.get('outside_link_count', 0)} / {case.get('search_intent_count', 0)}`",
                f"- compat_projection_available: `{case.get('compat_projection_available', False)}`",
                f"- normalized_eval_available: `{case.get('normalized_eval_available', False)}`",
                f"- output_dir: `{case.get('output_dir', '')}`",
                "",
            ]
        )
        sampled_reactions = [item for item in case.get("sampled_reactions", []) if isinstance(item, dict)]
        if sampled_reactions:
            lines.append("Sampled reactions:")
            lines.append("")
            for reaction in sampled_reactions[:3]:
                lines.append(f"- `{reaction.get('compat_family', '')}` | {_clean_text(reaction.get('anchor_quote'))[:120]}")
                lines.append(f"  - {_clean_text(reaction.get('content'))[:240]}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _aggregate_results(run_id: str, cases: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [case for case in cases if case.get("status") == "completed"]
    failed = [case for case in cases if case.get("status") != "completed"]
    return {
        "run_id": run_id,
        "generated_at": _timestamp(),
        "case_count": len(cases),
        "completed_case_count": len(completed),
        "failed_case_count": len(failed),
        "cases": cases,
    }


def _write_parent_state(
    *,
    run_root: Path,
    run_id: str,
    case_ids: list[str],
    process_states: dict[str, dict[str, Any]],
) -> None:
    payload = {
        "run_id": run_id,
        "updated_at": _timestamp(),
        "cases": case_ids,
        "process_states": process_states,
    }
    _json_dump(run_root / "run_state.json", payload)


def run_audit(
    *,
    run_id: str | None = None,
    runs_root: Path = DEFAULT_RUNS_ROOT,
    case_ids: list[str] | None = None,
) -> dict[str, Any]:
    selected_case_ids = [case_id for case_id in (case_ids or list(ALL_CASE_IDS)) if case_id in CASE_TARGET_ASSIGNMENTS]
    if not selected_case_ids:
        raise ValueError("No valid F4A case ids were selected.")
    actual_run_id = run_id or f"attentional_v2_f4a_quality_audit_{_timestamp_slug()}"
    run_root = runs_root / actual_run_id
    run_root.mkdir(parents=True, exist_ok=True)
    cases = [_resolve_case(case_id, run_root=run_root) for case_id in selected_case_ids]
    _json_dump(run_root / "meta" / "cases.json", [asdict(case) for case in cases])

    python = ROOT / ".venv" / "bin" / "python"
    if not python.exists():
        python = Path(sys.executable)

    processes: dict[str, subprocess.Popen[bytes]] = {}
    process_states: dict[str, dict[str, Any]] = {}
    for case in cases:
        shard_root = run_root / "shards" / case.case_id
        log_path = shard_root / "worker.log"
        result_path = shard_root / "result.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env["LLM_FORCE_TARGET_ID"] = case.target_id
        command = [
            str(python),
            str(Path(__file__).resolve()),
            "--runs-root",
            str(runs_root),
            "--run-id",
            actual_run_id,
            "--worker-case-id",
            case.case_id,
            "--worker-result",
            str(result_path),
        ]
        with log_path.open("ab") as handle:
            process = subprocess.Popen(
                command,
                cwd=str(ROOT),
                env=env,
                stdout=handle,
                stderr=subprocess.STDOUT,
            )
        processes[case.case_id] = process
        process_states[case.case_id] = {
            "target_id": case.target_id,
            "status": "running",
            "pid": process.pid,
            "result_path": str(result_path),
            "log_path": str(log_path),
        }
    _write_parent_state(run_root=run_root, run_id=actual_run_id, case_ids=selected_case_ids, process_states=process_states)

    pending = set(processes)
    while pending:
        for case_id in list(pending):
            process = processes[case_id]
            exit_code = process.poll()
            if exit_code is None:
                continue
            pending.remove(case_id)
            process_states[case_id]["status"] = "completed" if exit_code == 0 else "failed"
            process_states[case_id]["exit_code"] = exit_code
            process_states[case_id]["finished_at"] = _timestamp()
        _write_parent_state(run_root=run_root, run_id=actual_run_id, case_ids=selected_case_ids, process_states=process_states)
        if pending:
            time.sleep(5)

    case_results: list[dict[str, Any]] = []
    for case in cases:
        result_path = run_root / "shards" / case.case_id / "result.json"
        if result_path.exists():
            case_results.append(_json_load(result_path))
        else:
            case_results.append(
                {
                    "case_id": case.case_id,
                    "status": "failed",
                    "error": "worker_result_missing",
                }
            )

    summary = _aggregate_results(actual_run_id, case_results)
    _json_dump(run_root / "summary" / "aggregate.json", summary)
    report_path = run_root / "summary" / "report.md"
    report_path.write_text(_report_text(summary), encoding="utf-8")
    summary["run_root"] = str(run_root)
    summary["report_path"] = str(report_path)
    _write_parent_state(run_root=run_root, run_id=actual_run_id, case_ids=selected_case_ids, process_states=process_states)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--worker-case-id", default="", help=argparse.SUPPRESS)
    parser.add_argument("--worker-result", default="", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    runs_root = Path(args.runs_root).resolve()
    if args.worker_case_id:
        if not args.worker_result:
            raise ValueError("--worker-result is required with --worker-case-id")
        return _run_worker(
            args.worker_case_id,
            run_root=runs_root / args.run_id,
            worker_result=Path(args.worker_result).resolve(),
        )
    summary = run_audit(
        run_id=args.run_id or None,
        runs_root=runs_root,
        case_ids=[str(item) for item in args.case_id if str(item).strip()] or None,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"run_root={summary['run_root']}")
    print(f"report_path={summary['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
