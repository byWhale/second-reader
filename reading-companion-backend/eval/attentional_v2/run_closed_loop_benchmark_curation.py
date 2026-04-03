"""Run the first closed-loop benchmark-curation pass over the managed local supplement.

This runner keeps the existing builder, packet review scripts, and queue-summary
refresh as the source of truth. It adds a run-scoped controller that can:

1. construct_dataset
2. export_review_packets
3. audit_packets
4. adjudicate_packets
5. import_packets
6. repair_open_backlog
7. refresh_queue_summary
8. final_summary

By default the repair wave is skipped unless explicitly enabled. The runner
stops after writing a summary and does not launch any decision-bearing follow-up
such as promotion, freeze, runtime-viability, or default-cutover work.
"""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .build_private_library_supplement import (
    BENCHMARK_MODE_VALUES,
    SupplementBuildOptions,
    build_options_from_args as build_builder_options_from_args,
    build_private_library_supplement,
)
from .compare_packet_adjudication_runs import compare_adjudication_runs


ROOT = Path(__file__).resolve().parents[2]
LOCAL_DATASET_ROOT = ROOT / "state" / "eval_local_datasets"
REVIEW_PACKET_ROOT = ROOT / "eval" / "review_packets"
PENDING_PACKET_ROOT = REVIEW_PACKET_ROOT / "pending"
ARCHIVE_PACKET_ROOT = REVIEW_PACKET_ROOT / "archive"
QUEUE_SUMMARY_JSON = REVIEW_PACKET_ROOT / "review_queue_summary.json"
QUEUE_SUMMARY_MD = REVIEW_PACKET_ROOT / "review_queue_summary.md"

STAGES = (
    "construct_dataset",
    "export_review_packets",
    "audit_packets",
    "adjudicate_packets",
    "import_packets",
    "repair_open_backlog",
    "refresh_queue_summary",
    "final_summary",
)
SUMMARY_JSON_NAME = "closed_loop_benchmark_curation_summary.json"
SUMMARY_MD_NAME = "closed_loop_benchmark_curation_summary.md"
RUN_STATE_JSON_NAME = "closed_loop_benchmark_curation_run_state.json"
NO_DECISION_NOTE = (
    "No decision-bearing next phase was launched. Promotion, reviewed-slice freezing, "
    "runtime-viability, and default-cutover remain human-owned follow-up work."
)

CommandRunner = Callable[[list[str], Path], None]
BuilderRunner = Callable[[SupplementBuildOptions], dict[str, Any]]


@dataclass(frozen=True)
class ClosedLoopPaths:
    backend_root: Path
    local_dataset_root: Path
    pending_packet_root: Path
    archive_packet_root: Path
    queue_summary_json: Path
    queue_summary_md: Path
    run_root: Path
    run_state_json: Path
    summary_json: Path
    summary_md: Path

    @classmethod
    def from_root(cls, root: Path, run_id: str) -> "ClosedLoopPaths":
        root = root.resolve()
        run_root = root / "state" / "dataset_build" / "build_runs" / run_id
        return cls(
            backend_root=root,
            local_dataset_root=root / "state" / "eval_local_datasets",
            pending_packet_root=PENDING_PACKET_ROOT if root == ROOT else root / "eval" / "review_packets" / "pending",
            archive_packet_root=ARCHIVE_PACKET_ROOT if root == ROOT else root / "eval" / "review_packets" / "archive",
            queue_summary_json=QUEUE_SUMMARY_JSON if root == ROOT else root / "eval" / "review_packets" / "review_queue_summary.json",
            queue_summary_md=QUEUE_SUMMARY_MD if root == ROOT else root / "eval" / "review_packets" / "review_queue_summary.md",
            run_root=run_root,
            run_state_json=run_root / RUN_STATE_JSON_NAME,
            summary_json=run_root / SUMMARY_JSON_NAME,
            summary_md=run_root / SUMMARY_MD_NAME,
        )


@dataclass
class ClosedLoopState:
    run_id: str
    build_mode: str
    executed_stages: list[str] = field(default_factory=list)
    stage_commands: list[dict[str, Any]] = field(default_factory=list)
    builder_summary: dict[str, Any] | None = None
    initial_packets_by_language: dict[str, dict[str, Any]] = field(default_factory=dict)
    repair_pipeline_by_language: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "build_mode": self.build_mode,
            "executed_stages": normalized_stage_history(self.executed_stages),
            "stage_commands": list(self.stage_commands),
            "builder_summary": self.builder_summary,
            "initial_packets_by_language": self.initial_packets_by_language,
            "repair_pipeline_by_language": self.repair_pipeline_by_language,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ClosedLoopState":
        return cls(
            run_id=str(payload.get("run_id", "")).strip(),
            build_mode=str(payload.get("build_mode", "")).strip() or "scratch",
            executed_stages=normalized_stage_history(list(payload.get("executed_stages") or [])),
            stage_commands=list(payload.get("stage_commands") or []),
            builder_summary=payload.get("builder_summary") if isinstance(payload.get("builder_summary"), dict) else None,
            initial_packets_by_language=dict(payload.get("initial_packets_by_language") or {}),
            repair_pipeline_by_language=dict(payload.get("repair_pipeline_by_language") or {}),
        )


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def normalized_stage_history(values: list[str] | tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    requested: list[str] = []
    extras: list[str] = []
    stage_order = {stage: index for index, stage in enumerate(STAGES)}
    for value in values:
        stage = str(value).strip()
        if not stage or stage in seen:
            continue
        seen.add(stage)
        if stage in stage_order:
            requested.append(stage)
        else:
            extras.append(stage)
    requested.sort(key=lambda stage: stage_order[stage])
    return requested + extras


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected object row in {path}")
        rows.append(payload)
    return rows


def default_command_runner(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)


def default_builder_runner(options: SupplementBuildOptions) -> dict[str, Any]:
    return build_private_library_supplement(options)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-mode", choices=("scratch", "live"), default="scratch")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--benchmark-mode", choices=BENCHMARK_MODE_VALUES, default="default")
    parser.add_argument("--source-id", action="append", default=[], dest="source_ids")
    parser.add_argument("--chapter-case-id", action="append", default=[], dest="chapter_case_ids")
    parser.add_argument("--language", action="append", default=[], dest="languages")
    parser.add_argument("--limit-sources", type=int, default=0)
    parser.add_argument("--cases-per-chapter", type=int, default=0)
    parser.add_argument("--reserves-per-chapter", type=int, default=0)
    parser.add_argument("--feedback-dataset-id-en", default="")
    parser.add_argument("--feedback-dataset-id-zh", default="")
    parser.add_argument("--no-feedback", action="store_true")
    parser.add_argument("--tracked-override-manifest-path", default="")
    parser.add_argument("--no-tracked-overrides", action="store_true")
    parser.add_argument("--repair-open-backlog", action="store_true")
    parser.add_argument("--from-stage", choices=STAGES)
    parser.add_argument("--through-stage", choices=STAGES)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audit-max-workers", type=int, default=0)
    parser.add_argument("--review-max-workers", type=int, default=0)
    return parser


def resolved_run_id(raw_run_id: str) -> str:
    cleaned = str(raw_run_id).strip()
    return cleaned or default_run_id()


def planned_stages(
    from_stage: str | None,
    through_stage: str | None,
    *,
    include_repair: bool,
) -> list[str]:
    active_stages = list(STAGES)
    if not include_repair and "repair_open_backlog" in active_stages:
        active_stages.remove("repair_open_backlog")
    start = from_stage or active_stages[0]
    end = through_stage or active_stages[-1]
    if start not in active_stages:
        raise ValueError(f"Stage {start!r} is not enabled for this run.")
    if end not in active_stages:
        raise ValueError(f"Stage {end!r} is not enabled for this run.")
    start_index = active_stages.index(start)
    end_index = active_stages.index(end)
    if start_index > end_index:
        raise ValueError(f"Invalid stage range: {start} comes after {end}")
    return active_stages[start_index : end_index + 1]


def builder_options_from_closed_loop_args(args: argparse.Namespace, *, run_id: str) -> SupplementBuildOptions:
    builder_args = argparse.Namespace(
        scratch=args.build_mode == "scratch",
        run_id=run_id,
        benchmark_mode=args.benchmark_mode,
        source_ids=args.source_ids,
        chapter_case_ids=args.chapter_case_ids,
        languages=args.languages,
        limit_sources=args.limit_sources,
        cases_per_chapter=args.cases_per_chapter,
        reserves_per_chapter=args.reserves_per_chapter,
        feedback_dataset_id_en=args.feedback_dataset_id_en,
        feedback_dataset_id_zh=args.feedback_dataset_id_zh,
        no_feedback=args.no_feedback,
        tracked_override_manifest_path=args.tracked_override_manifest_path,
        no_tracked_overrides=args.no_tracked_overrides,
        no_bootstrap_catalog_if_missing=False,
    )
    return build_builder_options_from_args(builder_args)


def excerpt_dataset_path(paths: ClosedLoopPaths, dataset_id: str) -> Path:
    return paths.local_dataset_root / "excerpt_cases" / dataset_id / "cases.jsonl"


def benchmark_status_counts(paths: ClosedLoopPaths, dataset_id: str) -> dict[str, int]:
    counts = Counter(
        str(row.get("benchmark_status", "")).strip() or "unset"
        for row in load_jsonl(excerpt_dataset_path(paths, dataset_id))
    )
    return dict(sorted(counts.items()))


def open_backlog_count(counts: dict[str, int]) -> int:
    return int(counts.get("needs_revision", 0)) + int(counts.get("needs_replacement", 0))


def record_stage_command(
    state: ClosedLoopState,
    stage: str,
    command: list[str] | str,
    *,
    label: str = "",
) -> None:
    rendered = command if isinstance(command, str) else shlex.join(command)
    state.stage_commands.append(
        {
            "stage": stage,
            "label": label,
            "command": rendered,
        }
    )


def write_run_state(paths: ClosedLoopPaths, state: ClosedLoopState) -> None:
    write_json(paths.run_state_json, state.to_dict())


def load_run_state(paths: ClosedLoopPaths) -> ClosedLoopState:
    if not paths.run_state_json.exists():
        raise FileNotFoundError(f"Missing closed-loop run state: {paths.run_state_json}")
    return ClosedLoopState.from_dict(load_json(paths.run_state_json))


def mark_stage_completed(state: ClosedLoopState, stage: str) -> None:
    stage = str(stage).strip()
    if not stage or stage in state.executed_stages:
        return
    state.executed_stages.append(stage)


def initial_packet_id(dataset_id: str, run_id: str) -> str:
    return f"{dataset_id}__initial_review__{run_id}"


def repair_packet_id(dataset_id: str, run_id: str) -> str:
    return f"{dataset_id}__repair__{run_id}"


def builder_command_preview(args: argparse.Namespace, *, run_id: str) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "eval.attentional_v2.build_private_library_supplement",
        "--run-id",
        run_id,
        "--benchmark-mode",
        str(args.benchmark_mode),
    ]
    if args.build_mode == "scratch":
        command.append("--scratch")
    for source_id in args.source_ids:
        command.extend(["--source-id", str(source_id)])
    for chapter_case_id in args.chapter_case_ids:
        command.extend(["--chapter-case-id", str(chapter_case_id)])
    for language in args.languages:
        command.extend(["--language", str(language)])
    if args.limit_sources > 0:
        command.extend(["--limit-sources", str(args.limit_sources)])
    if args.cases_per_chapter > 0:
        command.extend(["--cases-per-chapter", str(args.cases_per_chapter)])
    if args.reserves_per_chapter > 0:
        command.extend(["--reserves-per-chapter", str(args.reserves_per_chapter)])
    if args.no_feedback:
        command.append("--no-feedback")
    else:
        if str(args.feedback_dataset_id_en).strip():
            command.extend(["--feedback-dataset-id-en", str(args.feedback_dataset_id_en).strip()])
        if str(args.feedback_dataset_id_zh).strip():
            command.extend(["--feedback-dataset-id-zh", str(args.feedback_dataset_id_zh).strip()])
    if args.no_tracked_overrides:
        command.append("--no-tracked-overrides")
    elif str(args.tracked_override_manifest_path).strip():
        command.extend(
            ["--tracked-override-manifest-path", str(args.tracked_override_manifest_path).strip()]
        )
    return command


def export_packet_command(*, dataset_id: str, packet_id: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "eval.attentional_v2.export_dataset_review_packet",
        "--dataset-id",
        dataset_id,
        "--family",
        "excerpt_cases",
        "--storage-mode",
        "local-only",
        "--packet-id",
        packet_id,
        "--only-unreviewed",
    ]


def audit_packet_command(packet_dir: Path, *, max_workers: int) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "eval.attentional_v2.run_case_design_audit",
        "--packet-dir",
        str(packet_dir),
    ]
    if max_workers > 0:
        command.extend(["--max-workers", str(max_workers)])
    return command


def adjudicate_packet_command(packet_dir: Path, *, max_workers: int) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "eval.attentional_v2.auto_review_packet",
        "--packet-dir",
        str(packet_dir),
    ]
    if max_workers > 0:
        command.extend(["--max-workers", str(max_workers)])
    return command


def import_packet_command(packet_dir: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "eval.attentional_v2.import_dataset_review_packet",
        "--packet-dir",
        str(packet_dir),
        "--review-origin",
        "llm",
        "--archive",
    ]


def repair_pipeline_command(*, dataset_id: str, packet_id: str, args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "eval.attentional_v2.run_dataset_review_pipeline",
        "--dataset-id",
        dataset_id,
        "--family",
        "excerpt_cases",
        "--storage-mode",
        "local-only",
        "--packet-id",
        packet_id,
    ]
    if args.audit_max_workers > 0:
        command.extend(["--audit-max-workers", str(args.audit_max_workers)])
    if args.review_max_workers > 0:
        command.extend(["--review-max-workers", str(args.review_max_workers)])
    return command


def refresh_queue_summary_command() -> list[str]:
    return [sys.executable, "-m", "eval.attentional_v2.build_review_queue_summary"]


def validate_resume_requirements(paths: ClosedLoopPaths, *, stages: list[str]) -> None:
    if stages and stages[0] != "construct_dataset" and not paths.run_state_json.exists():
        raise FileNotFoundError(
            f"Resuming from {stages[0]!r} requires an existing run state at {paths.run_state_json}"
        )


def render_summary_markdown(summary: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"# Closed-Loop Benchmark Curation Summary: `{summary['run_id']}`",
            "",
            f"- generated_at: `{summary['generated_at']}`",
            f"- build_mode: `{summary['build_mode']}`",
            f"- executed_stages: `{', '.join(summary['executed_stages'])}`",
            f"- initial_packet_ids: `{json.dumps(summary['initial_packet_ids_by_language'], ensure_ascii=False, sort_keys=True)}`",
            f"- repair_packet_ids: `{json.dumps(summary['repair_packet_ids_by_language'], ensure_ascii=False, sort_keys=True)}`",
            f"- initial_import_action_counts: `{json.dumps(summary['initial_import_action_counts_by_language'], ensure_ascii=False, sort_keys=True)}`",
            f"- post_import_benchmark_status_counts: `{json.dumps(summary['post_import_benchmark_status_counts_by_language'], ensure_ascii=False, sort_keys=True)}`",
            f"- initial_adjudication_input_fingerprints: `{json.dumps(summary['initial_adjudication_input_fingerprints_by_language'], ensure_ascii=False, sort_keys=True)}`",
            f"- repair_adjudication_input_fingerprints: `{json.dumps(summary['repair_adjudication_input_fingerprints_by_language'], ensure_ascii=False, sort_keys=True)}`",
            f"- variability_guard_triggered: `{summary['variability_guard_triggered']}`",
            "",
            "## Stop Point",
            f"- {summary['decision_note']}",
        ]
    )


def packet_adjudication_summary(packet_dir: Path) -> dict[str, Any] | None:
    summary_path = packet_dir / "llm_review_summary.json"
    if not summary_path.exists():
        return None
    return load_json(summary_path)


def packet_adjudication_variability(packet_dir: Path) -> list[dict[str, Any]]:
    run_root = packet_dir / "llm_review_runs"
    if not run_root.exists():
        return []
    run_dirs = sorted(path for path in run_root.iterdir() if path.is_dir() and (path / "summary.json").exists())
    if len(run_dirs) < 2:
        return []

    warnings: list[dict[str, Any]] = []
    for baseline, candidate in zip(run_dirs, run_dirs[1:]):
        comparison = compare_adjudication_runs(baseline, candidate)
        drift_counts = dict(comparison.get("drift_counts") or {})
        case_diffs = list(comparison.get("case_diffs") or [])
        comparable_same_source_cases = [
            item for item in case_diffs if bool(item.get("same_source_row_fingerprint"))
        ]
        if not comparable_same_source_cases:
            continue
        if any(int(drift_counts.get(key, 0) or 0) > 0 for key in drift_counts):
            warnings.append(
                {
                    "baseline_run_id": str(comparison.get("run_id_a", "")).strip(),
                    "candidate_run_id": str(comparison.get("run_id_b", "")).strip(),
                    "packet_input_fingerprint_a": str(
                        comparison.get("packet_input_fingerprint_a", "")
                    ).strip(),
                    "packet_input_fingerprint_b": str(
                        comparison.get("packet_input_fingerprint_b", "")
                    ).strip(),
                    "same_packet_input_fingerprint": bool(
                        comparison.get("same_packet_input_fingerprint")
                    ),
                    "same_source_case_count": len(comparable_same_source_cases),
                    "drift_counts": drift_counts,
                }
            )
    return warnings


def write_final_summary(paths: ClosedLoopPaths, state: ClosedLoopState) -> dict[str, Any]:
    builder_summary = state.builder_summary or {}
    excerpt_dataset_ids = dict(((builder_summary.get("dataset_ids") or {}).get("excerpt_cases") or {}))
    initial_packet_ids = {
        language: str(packet_info.get("packet_id", "")).strip()
        for language, packet_info in sorted(state.initial_packets_by_language.items())
        if str(packet_info.get("packet_id", "")).strip()
    }
    repair_packet_ids = {
        language: str(packet_info.get("packet_id", "")).strip()
        for language, packet_info in sorted(state.repair_pipeline_by_language.items())
        if str(packet_info.get("packet_id", "")).strip()
    }
    initial_import_action_counts: dict[str, dict[str, int]] = {}
    for language, packet_info in state.initial_packets_by_language.items():
        archived_packet_dir = str(packet_info.get("archived_packet_dir", "")).strip()
        if not archived_packet_dir:
            continue
        summary_path = Path(archived_packet_dir) / "import_summary.json"
        if not summary_path.exists():
            continue
        import_summary = load_json(summary_path)
        initial_import_action_counts[language] = dict(import_summary.get("action_counts", {}))

    repair_action_counts: dict[str, dict[str, int]] = {}
    for language, packet_info in state.repair_pipeline_by_language.items():
        summary_path = str(packet_info.get("summary_path", "")).strip()
        if not summary_path:
            continue
        payload = load_json(Path(summary_path))
        repair_action_counts[language] = dict(payload.get("action_counts", {}))

    initial_adjudication_input_fingerprints: dict[str, str] = {}
    initial_variability_warnings: dict[str, list[dict[str, Any]]] = {}
    for language, packet_info in state.initial_packets_by_language.items():
        archived_packet_dir = str(packet_info.get("archived_packet_dir", "")).strip()
        if not archived_packet_dir:
            continue
        packet_dir = Path(archived_packet_dir)
        adjudication_summary = packet_adjudication_summary(packet_dir)
        if adjudication_summary is not None:
            fingerprint = str(adjudication_summary.get("adjudication_input_fingerprint", "")).strip()
            if fingerprint:
                initial_adjudication_input_fingerprints[language] = fingerprint
        warnings = packet_adjudication_variability(packet_dir)
        if warnings:
            initial_variability_warnings[language] = warnings

    repair_adjudication_input_fingerprints: dict[str, str] = {}
    repair_variability_warnings: dict[str, list[dict[str, Any]]] = {}
    for language, packet_info in state.repair_pipeline_by_language.items():
        packet_id = str(packet_info.get("packet_id", "")).strip()
        if not packet_id:
            continue
        archived_packet_dir = paths.archive_packet_root / packet_id
        if not archived_packet_dir.exists():
            continue
        adjudication_summary = packet_adjudication_summary(archived_packet_dir)
        if adjudication_summary is not None:
            fingerprint = str(adjudication_summary.get("adjudication_input_fingerprint", "")).strip()
            if fingerprint:
                repair_adjudication_input_fingerprints[language] = fingerprint
        warnings = packet_adjudication_variability(archived_packet_dir)
        if warnings:
            repair_variability_warnings[language] = warnings

    variability_guard_triggered = bool(initial_variability_warnings or repair_variability_warnings)
    post_import_counts = {
        language: benchmark_status_counts(paths, dataset_id)
        for language, dataset_id in sorted(excerpt_dataset_ids.items())
    }
    summary = {
        "generated_at": utc_now(),
        "run_id": state.run_id,
        "run_root": str(paths.run_root),
        "build_mode": state.build_mode,
        "executed_stages": list(state.executed_stages),
        "dataset_ids": dict(sorted(excerpt_dataset_ids.items())),
        "initial_packet_ids_by_language": initial_packet_ids,
        "repair_packet_ids_by_language": repair_packet_ids,
        "initial_import_action_counts_by_language": dict(sorted(initial_import_action_counts.items())),
        "repair_action_counts_by_language": dict(sorted(repair_action_counts.items())),
        "initial_adjudication_input_fingerprints_by_language": dict(
            sorted(initial_adjudication_input_fingerprints.items())
        ),
        "repair_adjudication_input_fingerprints_by_language": dict(
            sorted(repair_adjudication_input_fingerprints.items())
        ),
        "initial_adjudication_variability_warnings_by_language": dict(sorted(initial_variability_warnings.items())),
        "repair_adjudication_variability_warnings_by_language": dict(sorted(repair_variability_warnings.items())),
        "variability_guard_triggered": variability_guard_triggered,
        "post_import_benchmark_status_counts_by_language": post_import_counts,
        "decision_bearing_followup_launched": False,
        "decision_note": NO_DECISION_NOTE,
    }
    write_json(paths.summary_json, summary)
    paths.summary_md.parent.mkdir(parents=True, exist_ok=True)
    paths.summary_md.write_text(render_summary_markdown(summary).rstrip() + "\n", encoding="utf-8")
    return summary


def partial_run_payload(
    *,
    paths: ClosedLoopPaths,
    state: ClosedLoopState,
    planned_stages: list[str],
    status: str,
) -> dict[str, Any]:
    builder_summary = state.builder_summary or {}
    excerpt_dataset_ids = dict(((builder_summary.get("dataset_ids") or {}).get("excerpt_cases") or {}))
    return {
        "status": status,
        "run_id": state.run_id,
        "run_root": str(paths.run_root),
        "build_mode": state.build_mode,
        "planned_stages": list(planned_stages),
        "executed_stages": list(state.executed_stages),
        "dataset_ids": dict(sorted(excerpt_dataset_ids.items())),
        "initial_packet_ids_by_language": {
            language: str(packet_info.get("packet_id", "")).strip()
            for language, packet_info in sorted(state.initial_packets_by_language.items())
            if str(packet_info.get("packet_id", "")).strip()
        },
        "repair_packet_ids_by_language": {
            language: str(packet_info.get("packet_id", "")).strip()
            for language, packet_info in sorted(state.repair_pipeline_by_language.items())
            if str(packet_info.get("packet_id", "")).strip()
        },
        "run_state_json": str(paths.run_state_json),
        "decision_note": NO_DECISION_NOTE,
    }


def run_closed_loop(
    args: argparse.Namespace,
    *,
    paths: ClosedLoopPaths | None = None,
    command_runner: CommandRunner = default_command_runner,
    builder_runner: BuilderRunner = default_builder_runner,
) -> dict[str, Any]:
    run_id = resolved_run_id(args.run_id)
    include_repair = bool(
        args.repair_open_backlog
        or args.from_stage == "repair_open_backlog"
        or args.through_stage == "repair_open_backlog"
    )
    stages = planned_stages(args.from_stage, args.through_stage, include_repair=include_repair)
    paths = paths or ClosedLoopPaths.from_root(ROOT, run_id)
    validate_resume_requirements(paths, stages=stages)

    if paths.run_state_json.exists():
        state = load_run_state(paths)
        if state.run_id and state.run_id != run_id:
            raise ValueError(
                f"Run-state id mismatch: expected {run_id}, found {state.run_id} at {paths.run_state_json}"
            )
    else:
        state = ClosedLoopState(run_id=run_id, build_mode=args.build_mode)

    if state.build_mode and state.build_mode != args.build_mode:
        raise ValueError(
            f"Run {run_id} was created with build_mode={state.build_mode}, not {args.build_mode}."
        )

    if args.dry_run:
        return {
            "status": "dry_run_ok",
            "run_id": run_id,
            "run_root": str(paths.run_root),
            "planned_stages": stages,
            "builder_command": shlex.join(builder_command_preview(args, run_id=run_id)),
        }

    paths.run_root.mkdir(parents=True, exist_ok=True)
    state.build_mode = args.build_mode

    for stage in stages:
        if stage == "construct_dataset":
            builder_command = builder_command_preview(args, run_id=run_id)
            record_stage_command(state, stage, builder_command)
            state.builder_summary = builder_runner(builder_options_from_closed_loop_args(args, run_id=run_id))
        elif stage == "export_review_packets":
            if state.builder_summary is None:
                raise FileNotFoundError("export_review_packets requires a builder summary from construct_dataset.")
            excerpt_dataset_ids = dict(
                ((state.builder_summary.get("dataset_ids") or {}).get("excerpt_cases") or {})
            )
            for language, dataset_id in sorted(excerpt_dataset_ids.items()):
                rows = load_jsonl(excerpt_dataset_path(paths, dataset_id))
                if not rows:
                    state.initial_packets_by_language[language] = {
                        "dataset_id": dataset_id,
                        "status": "skipped_empty",
                    }
                    continue
                packet_id = initial_packet_id(dataset_id, run_id)
                command = export_packet_command(dataset_id=dataset_id, packet_id=packet_id)
                record_stage_command(state, stage, command, label=language)
                command_runner(command, paths.backend_root)
                packet_dir = paths.pending_packet_root / packet_id
                manifest = load_json(packet_dir / "packet_manifest.json")
                state.initial_packets_by_language[language] = {
                    "dataset_id": dataset_id,
                    "packet_id": packet_id,
                    "packet_dir": str(packet_dir),
                    "case_count": int(manifest.get("case_count", 0)),
                    "status": "pending",
                }
        elif stage == "audit_packets":
            for language, packet_info in sorted(state.initial_packets_by_language.items()):
                packet_id = str(packet_info.get("packet_id", "")).strip()
                packet_dir_text = str(packet_info.get("packet_dir", "")).strip()
                if not packet_id or not packet_dir_text:
                    continue
                packet_dir = Path(packet_dir_text)
                command = audit_packet_command(packet_dir, max_workers=args.audit_max_workers)
                record_stage_command(state, stage, command, label=language)
                command_runner(command, paths.backend_root)
        elif stage == "adjudicate_packets":
            for language, packet_info in sorted(state.initial_packets_by_language.items()):
                packet_id = str(packet_info.get("packet_id", "")).strip()
                packet_dir_text = str(packet_info.get("packet_dir", "")).strip()
                if not packet_id or not packet_dir_text:
                    continue
                packet_dir = Path(packet_dir_text)
                command = adjudicate_packet_command(packet_dir, max_workers=args.review_max_workers)
                record_stage_command(state, stage, command, label=language)
                command_runner(command, paths.backend_root)
        elif stage == "import_packets":
            for language, packet_info in sorted(state.initial_packets_by_language.items()):
                packet_id = str(packet_info.get("packet_id", "")).strip()
                packet_dir_text = str(packet_info.get("packet_dir", "")).strip()
                if not packet_id or not packet_dir_text:
                    continue
                packet_dir = Path(packet_dir_text)
                command = import_packet_command(packet_dir)
                record_stage_command(state, stage, command, label=language)
                command_runner(command, paths.backend_root)
                archive_dir = paths.archive_packet_root / packet_id
                packet_info["archived_packet_dir"] = str(archive_dir)
                packet_info["status"] = "archived"
        elif stage == "repair_open_backlog":
            if state.builder_summary is None:
                raise FileNotFoundError("repair_open_backlog requires a builder summary from construct_dataset.")
            excerpt_dataset_ids = dict(
                ((state.builder_summary.get("dataset_ids") or {}).get("excerpt_cases") or {})
            )
            for language, dataset_id in sorted(excerpt_dataset_ids.items()):
                counts = benchmark_status_counts(paths, dataset_id)
                backlog = open_backlog_count(counts)
                if backlog <= 0:
                    state.repair_pipeline_by_language[language] = {
                        "dataset_id": dataset_id,
                        "status": "skipped_clean",
                        "open_backlog_count": backlog,
                    }
                    continue
                packet_id = repair_packet_id(dataset_id, run_id)
                command = repair_pipeline_command(dataset_id=dataset_id, packet_id=packet_id, args=args)
                record_stage_command(state, stage, command, label=language)
                command_runner(command, paths.backend_root)
                summary_path = (
                    paths.archive_packet_root
                    / packet_id
                    / "dataset_review_pipeline_summary.json"
                )
                state.repair_pipeline_by_language[language] = {
                    "dataset_id": dataset_id,
                    "packet_id": packet_id,
                    "status": "completed",
                    "open_backlog_count": backlog,
                    "summary_path": str(summary_path),
                }
        elif stage == "refresh_queue_summary":
            command = refresh_queue_summary_command()
            record_stage_command(state, stage, command)
            command_runner(command, paths.backend_root)
        elif stage == "final_summary":
            mark_stage_completed(state, stage)
            summary = write_final_summary(paths, state)
            write_run_state(paths, state)
            return summary
        else:
            raise ValueError(f"Unsupported stage: {stage}")

        mark_stage_completed(state, stage)
        write_run_state(paths, state)

    return partial_run_payload(
        paths=paths,
        state=state,
        planned_stages=stages,
        status="ok",
    )


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = build_parser().parse_args(argv)
    payload = run_closed_loop(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def cli(argv: list[str] | None = None) -> int:
    main(sys.argv[1:] if argv is None else argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
