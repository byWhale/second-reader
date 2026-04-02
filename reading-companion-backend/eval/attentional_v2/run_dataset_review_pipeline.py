"""Run the mechanical dataset-review packet pipeline end to end.

This runner intentionally orchestrates the existing review-packet scripts rather
than reimplementing their logic. Its scope is limited to the packet lifecycle:

1. generate_packet
2. audit_packet
3. adjudicate_packet
4. import_packet
5. refresh_queue_summary
6. final_summary

It stops after producing a final summary artifact and does not launch any
decision-bearing follow-up phases.
"""

from __future__ import annotations

import argparse
import csv
import json
import shlex
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .case_audit_runs import latest_case_audit_run
from .export_dataset_review_packet import FAMILY_CHOICES, STORAGE_MODE_CHOICES


ROOT = Path(__file__).resolve().parents[2]
REVIEW_PACKET_ROOT = ROOT / "eval" / "review_packets"
PENDING_PACKET_ROOT = REVIEW_PACKET_ROOT / "pending"
ARCHIVE_PACKET_ROOT = REVIEW_PACKET_ROOT / "archive"
CASE_AUDIT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2" / "case_audits"
QUEUE_SUMMARY_JSON = REVIEW_PACKET_ROOT / "review_queue_summary.json"
QUEUE_SUMMARY_MD = REVIEW_PACKET_ROOT / "review_queue_summary.md"

STAGES = (
    "generate_packet",
    "audit_packet",
    "adjudicate_packet",
    "import_packet",
    "refresh_queue_summary",
    "final_summary",
)
ACTIVE_PACKET_STAGES = {"audit_packet", "adjudicate_packet", "import_packet"}
SUMMARY_JSON_NAME = "dataset_review_pipeline_summary.json"
SUMMARY_MD_NAME = "dataset_review_pipeline_summary.md"
DEFAULT_STATUSES = ("needs_revision", "needs_replacement")
SELECTION_MODE_CHOICES = ("revision_replacement", "first_review")
DEFAULT_SELECTION_MODE = SELECTION_MODE_CHOICES[0]
NO_DECISION_NOTE = (
    "No decision-bearing next phase was launched. Benchmark promotion, reviewed-slice freezing, "
    "durable-trace, re-entry, and runtime-viability remain human-owned follow-up work."
)

CommandRunner = Callable[[list[str], Path], None]


@dataclass(frozen=True)
class PipelinePaths:
    backend_root: Path
    review_packet_root: Path
    pending_packet_root: Path
    archive_packet_root: Path
    case_audit_runs_root: Path
    queue_summary_json: Path
    queue_summary_md: Path

    @classmethod
    def from_root(cls, root: Path) -> "PipelinePaths":
        root = root.resolve()
        review_packet_root = root / "eval" / "review_packets"
        return cls(
            backend_root=root,
            review_packet_root=review_packet_root,
            pending_packet_root=review_packet_root / "pending",
            archive_packet_root=review_packet_root / "archive",
            case_audit_runs_root=root / "eval" / "runs" / "attentional_v2" / "case_audits",
            queue_summary_json=review_packet_root / "review_queue_summary.json",
            queue_summary_md=review_packet_root / "review_queue_summary.md",
        )


@dataclass
class PipelineState:
    dataset_id: str
    family: str
    storage_mode: str
    selection_mode: str = DEFAULT_SELECTION_MODE
    packet_id: str | None = None
    packet_dir: Path | None = None
    executed_stages: list[str] = field(default_factory=list)
    stage_commands: list[dict[str, Any]] = field(default_factory=list)
    audit_run: dict[str, Any] | None = None
    pipeline_summary_path: Path | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_pipeline_packet_id(dataset_id: str, *, selection_mode: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = "first_review" if selection_mode == "first_review" else "revision_replacement"
    return f"{dataset_id}__{suffix}__{timestamp}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--family", required=True, choices=FAMILY_CHOICES)
    parser.add_argument("--storage-mode", required=True, choices=STORAGE_MODE_CHOICES)
    parser.add_argument(
        "--selection-mode",
        default=DEFAULT_SELECTION_MODE,
        choices=SELECTION_MODE_CHOICES,
        help="How generate_packet selects cases. revision_replacement targets backlog statuses; first_review exports unreviewed builder-active cases by explicit case id.",
    )
    parser.add_argument(
        "--status",
        action="append",
        dest="statuses",
        default=None,
        help="benchmark_status values to include in generate_packet. Repeat the flag for more than one status.",
    )
    parser.add_argument("--case-id", action="append", default=[], dest="case_ids")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--packet-id", default="")
    parser.add_argument("--packet-dir", default="")
    parser.add_argument("--from-stage", choices=STAGES)
    parser.add_argument("--through-stage", choices=STAGES)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--audit-max-workers", type=int, default=0)
    parser.add_argument("--review-max-workers", type=int, default=0)
    return parser


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected object row in {path}")
        rows.append(payload)
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_review_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError(f"No review rows found in {path}")
    return rows


def requested_stages(from_stage: str | None, through_stage: str | None) -> list[str]:
    start = from_stage or STAGES[0]
    end = through_stage or STAGES[-1]
    start_index = STAGES.index(start)
    end_index = STAGES.index(end)
    if start_index > end_index:
        raise ValueError(f"Invalid stage range: {start} comes after {end}")
    return list(STAGES[start_index : end_index + 1])


def normalize_statuses(raw_statuses: list[str] | None) -> list[str]:
    if not raw_statuses:
        return list(DEFAULT_STATUSES)
    statuses = [status.strip() for status in raw_statuses if status.strip()]
    if not statuses:
        raise ValueError("At least one non-empty --status value is required when the flag is used.")
    return statuses


def normalize_case_ids(raw_case_ids: list[str]) -> list[str]:
    return [case_id.strip() for case_id in raw_case_ids if case_id.strip()]


def validate_selection_args(args: argparse.Namespace) -> None:
    if args.selection_mode != "first_review":
        return
    statuses = [status.strip() for status in (args.statuses or []) if status.strip()]
    if statuses:
        raise ValueError("--status is only supported for revision_replacement selection mode.")
    if not normalize_case_ids(args.case_ids):
        raise ValueError("first_review selection mode requires at least one --case-id.")


def packet_dir_for_id(paths: PipelinePaths, packet_id: str, *, archived: bool) -> Path:
    root = paths.archive_packet_root if archived else paths.pending_packet_root
    return root / packet_id


def resolve_resume_packet(paths: PipelinePaths, *, packet_id: str, packet_dir: str) -> tuple[str, Path]:
    packet_id = packet_id.strip()
    packet_dir = packet_dir.strip()
    if packet_dir:
        resolved = Path(packet_dir).expanduser().resolve()
        manifest_path = resolved / "packet_manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Packet manifest not found: {manifest_path}")
        manifest = load_json(manifest_path)
        manifest_packet_id = str(manifest.get("packet_id", "")).strip()
        if not manifest_packet_id:
            raise ValueError(f"Packet manifest missing packet_id: {manifest_path}")
        if packet_id and packet_id != manifest_packet_id:
            raise ValueError(
                f"--packet-id {packet_id!r} does not match packet_dir manifest packet_id {manifest_packet_id!r}"
            )
        return manifest_packet_id, resolved
    if not packet_id:
        raise ValueError("Provide --packet-id or --packet-dir when resuming from an existing packet.")
    pending_dir = packet_dir_for_id(paths, packet_id, archived=False)
    archive_dir = packet_dir_for_id(paths, packet_id, archived=True)
    candidates = [path for path in (pending_dir, archive_dir) if path.exists()]
    if not candidates:
        raise FileNotFoundError(f"Packet not found in pending or archive roots: {packet_id}")
    if len(candidates) > 1:
        raise ValueError(f"Packet id is ambiguous because both pending and archive copies exist: {packet_id}")
    return packet_id, candidates[0]


def packet_location(paths: PipelinePaths, packet_id: str, packet_dir: Path | None) -> str:
    if packet_dir is None:
        return "unknown"
    resolved = packet_dir.resolve()
    if resolved == packet_dir_for_id(paths, packet_id, archived=False).resolve():
        return "pending"
    if resolved == packet_dir_for_id(paths, packet_id, archived=True).resolve():
        return "archive"
    return "external"


def default_command_runner(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=str(cwd), check=True)


def command_for_stage(stage: str, *, args: argparse.Namespace, state: PipelineState) -> list[str] | None:
    python = sys.executable
    if stage == "generate_packet":
        if args.selection_mode == "first_review":
            command = [
                python,
                "-m",
                "eval.attentional_v2.export_dataset_review_packet",
                "--dataset-id",
                state.dataset_id,
                "--family",
                state.family,
                "--storage-mode",
                state.storage_mode,
                "--packet-id",
                str(state.packet_id or ""),
                "--only-unreviewed",
            ]
        else:
            command = [
                python,
                "-m",
                "eval.attentional_v2.generate_revision_replacement_packet",
                "--dataset-id",
                state.dataset_id,
                "--family",
                state.family,
                "--storage-mode",
                state.storage_mode,
                "--packet-id",
                str(state.packet_id or ""),
            ]
            for status in normalize_statuses(args.statuses):
                command.extend(["--status", status])
        for case_id in normalize_case_ids(args.case_ids):
            command.extend(["--case-id", case_id])
        if args.limit > 0:
            command.extend(["--limit", str(args.limit)])
        return command
    if stage == "audit_packet":
        if state.packet_dir is None:
            raise ValueError("audit_packet requires a resolved packet_dir")
        command = [
            python,
            "-m",
            "eval.attentional_v2.run_case_design_audit",
            "--packet-dir",
            str(state.packet_dir),
        ]
        if args.limit > 0:
            command.extend(["--limit", str(args.limit)])
        if args.audit_max_workers > 0:
            command.extend(["--max-workers", str(args.audit_max_workers)])
        return command
    if stage == "adjudicate_packet":
        if state.packet_dir is None:
            raise ValueError("adjudicate_packet requires a resolved packet_dir")
        command = [
            python,
            "-m",
            "eval.attentional_v2.auto_review_packet",
            "--packet-dir",
            str(state.packet_dir),
        ]
        if args.review_max_workers > 0:
            command.extend(["--max-workers", str(args.review_max_workers)])
        return command
    if stage == "import_packet":
        if state.packet_dir is None:
            raise ValueError("import_packet requires a resolved packet_dir")
        return [
            python,
            "-m",
            "eval.attentional_v2.import_dataset_review_packet",
            "--packet-dir",
            str(state.packet_dir),
            "--review-origin",
            "llm",
            "--archive",
        ]
    if stage == "refresh_queue_summary":
        return [
            python,
            "-m",
            "eval.attentional_v2.build_review_queue_summary",
        ]
    if stage == "final_summary":
        return None
    raise ValueError(f"Unsupported stage: {stage}")


def latest_completed_audit(paths: PipelinePaths, packet_id: str) -> dict[str, Any] | None:
    if not paths.case_audit_runs_root.exists():
        return None
    return latest_case_audit_run(packet_id, paths.case_audit_runs_root, require_completed=True)


def adjudication_summary_path(packet_dir: Path) -> Path:
    return packet_dir / "llm_review_summary.json"


def adjudication_report_path(packet_dir: Path) -> Path:
    return packet_dir / "llm_review_report.md"


def import_summary_path(packet_dir: Path) -> Path:
    return packet_dir / "import_summary.json"


def dataset_before_import_path(packet_dir: Path) -> Path:
    return packet_dir / "dataset_before_import.jsonl"


def has_adjudication_outputs(packet_dir: Path) -> bool:
    return adjudication_summary_path(packet_dir).exists() or adjudication_report_path(packet_dir).exists()


def has_import_outputs(packet_dir: Path) -> bool:
    return import_summary_path(packet_dir).exists() or dataset_before_import_path(packet_dir).exists()


def review_rows_have_actions(packet_dir: Path) -> bool:
    rows = parse_review_rows(packet_dir / "cases.review.csv")
    return all(str(row.get("review__action", "")).strip() for row in rows)


def validate_generate_prerequisites(paths: PipelinePaths, state: PipelineState, *, packet_dir_arg: str) -> None:
    if packet_dir_arg.strip():
        raise ValueError("--packet-dir cannot be used when generate_packet is included in the requested stage range.")
    if not state.packet_id:
        raise ValueError("generate_packet requires a resolved packet_id")
    pending_dir = packet_dir_for_id(paths, state.packet_id, archived=False)
    archive_dir = packet_dir_for_id(paths, state.packet_id, archived=True)
    if pending_dir.exists():
        raise FileExistsError(f"Pending packet already exists: {pending_dir}")
    if archive_dir.exists():
        raise FileExistsError(f"Archived packet already exists: {archive_dir}")


def validate_packet_stage_prerequisites(stage: str, paths: PipelinePaths, state: PipelineState) -> None:
    if not state.packet_id or state.packet_dir is None:
        raise ValueError(f"{stage} requires a resolved packet reference")
    manifest_path = state.packet_dir / "packet_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Packet manifest not found: {manifest_path}")
    location = packet_location(paths, state.packet_id, state.packet_dir)
    if stage in ACTIVE_PACKET_STAGES and location == "archive":
        raise ValueError(f"{stage} requires an active packet, but {state.packet_id} is already archived.")
    if stage == "audit_packet":
        completed_audit = latest_completed_audit(paths, state.packet_id)
        if completed_audit is not None:
            raise FileExistsError(
                f"Completed case audit already exists for packet {state.packet_id}: {completed_audit.get('run_dir', '')}"
            )
        return
    if stage == "adjudicate_packet":
        completed_audit = latest_completed_audit(paths, state.packet_id)
        if completed_audit is None:
            raise FileNotFoundError(f"adjudicate_packet requires a completed case audit for packet {state.packet_id}")
        if has_adjudication_outputs(state.packet_dir):
            raise FileExistsError(f"Adjudication outputs already exist for packet {state.packet_id}: {state.packet_dir}")
        return
    if stage == "import_packet":
        completed_audit = latest_completed_audit(paths, state.packet_id)
        if completed_audit is None:
            raise FileNotFoundError(f"import_packet requires a completed case audit for packet {state.packet_id}")
        if not has_adjudication_outputs(state.packet_dir):
            raise FileNotFoundError(f"import_packet requires adjudication outputs for packet {state.packet_id}")
        if not review_rows_have_actions(state.packet_dir):
            raise ValueError(f"Packet review CSV still has blank review__action cells: {state.packet_dir / 'cases.review.csv'}")
        archive_dir = packet_dir_for_id(paths, state.packet_id, archived=True)
        if archive_dir.exists():
            raise FileExistsError(f"Archive packet already exists: {archive_dir}")
        if has_import_outputs(state.packet_dir):
            raise FileExistsError(
                f"Import outputs already exist for the active packet. Inspect the packet before retrying: {state.packet_dir}"
            )
        return
    if stage == "final_summary":
        if not import_summary_path(state.packet_dir).exists():
            raise FileNotFoundError(f"final_summary requires import_summary.json in {state.packet_dir}")
        return


def summary_packet_dir(paths: PipelinePaths, state: PipelineState) -> Path:
    if not state.packet_id:
        raise ValueError("Cannot resolve summary packet dir without packet_id")
    archive_dir = packet_dir_for_id(paths, state.packet_id, archived=True)
    if archive_dir.exists():
        return archive_dir
    if state.packet_dir is None:
        raise ValueError("Cannot resolve summary packet dir without packet_dir")
    return state.packet_dir


def prevalidate_requested_range(paths: PipelinePaths, state: PipelineState, stages: list[str]) -> None:
    packet_available = state.packet_id is not None and state.packet_dir is not None
    location = packet_location(paths, str(state.packet_id or ""), state.packet_dir) if packet_available else "unknown"
    active_packet_available = packet_available and location != "archive"
    completed_audit_available = bool(state.packet_id and latest_completed_audit(paths, str(state.packet_id)))
    adjudication_available = bool(packet_available and state.packet_dir and has_adjudication_outputs(state.packet_dir))
    import_available = False
    if packet_available:
        try:
            import_available = import_summary_path(summary_packet_dir(paths, state)).exists()
        except ValueError:
            import_available = False

    for stage in stages:
        if stage == "generate_packet":
            validate_generate_prerequisites(paths, state, packet_dir_arg="")
            packet_available = True
            active_packet_available = True
            completed_audit_available = False
            adjudication_available = False
            import_available = False
            continue
        if stage == "audit_packet":
            if not active_packet_available:
                raise ValueError("audit_packet requires an active packet in pending or an explicit active --packet-dir.")
            if completed_audit_available:
                raise FileExistsError(f"Completed case audit already exists for packet {state.packet_id}")
            completed_audit_available = True
            continue
        if stage == "adjudicate_packet":
            if not active_packet_available:
                raise ValueError("adjudicate_packet requires an active packet in pending or an explicit active --packet-dir.")
            if not completed_audit_available:
                raise FileNotFoundError(f"adjudicate_packet requires a completed case audit for packet {state.packet_id}")
            if adjudication_available:
                raise FileExistsError(f"Adjudication outputs already exist for packet {state.packet_id}")
            adjudication_available = True
            continue
        if stage == "import_packet":
            if not active_packet_available:
                raise ValueError("import_packet requires an active packet in pending or an explicit active --packet-dir.")
            if not completed_audit_available:
                raise FileNotFoundError(f"import_packet requires a completed case audit for packet {state.packet_id}")
            if not adjudication_available:
                raise FileNotFoundError(f"import_packet requires adjudication outputs for packet {state.packet_id}")
            if state.packet_id and packet_dir_for_id(paths, str(state.packet_id), archived=True).exists():
                raise FileExistsError(f"Archive packet already exists: {packet_dir_for_id(paths, str(state.packet_id), archived=True)}")
            if state.packet_dir and import_summary_path(state.packet_dir).exists():
                raise FileExistsError(f"Import outputs already exist for the active packet: {state.packet_dir}")
            import_available = True
            active_packet_available = False
            packet_available = True
            continue
        if stage == "refresh_queue_summary":
            continue
        if stage == "final_summary":
            if not packet_available:
                raise FileNotFoundError("final_summary requires a resolved packet reference.")
            if not import_available:
                raise FileNotFoundError(
                    f"final_summary requires an imported packet. Add import_packet to the stage range or resume from an archived/imported packet for {state.packet_id}."
                )
            continue
        raise ValueError(f"Unsupported stage: {stage}")


def post_import_benchmark_status_counts(packet_manifest: dict[str, Any], *, root: Path) -> dict[str, int]:
    dataset_primary_path = root / str(packet_manifest.get("dataset_primary_file_path", ""))
    if not dataset_primary_path.exists():
        raise FileNotFoundError(f"Dataset primary file not found: {dataset_primary_path}")
    counts = Counter(str(row.get("benchmark_status", "")).strip() or "unset" for row in load_jsonl(dataset_primary_path))
    return dict(sorted(counts.items()))


def render_pipeline_summary_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Dataset Review Pipeline Summary: `{summary['packet_id']}`",
        "",
        f"- generated_at: `{summary['generated_at']}`",
        f"- dataset_id: `{summary['dataset_id']}`",
        f"- family: `{summary['family']}`",
        f"- storage_mode: `{summary['storage_mode']}`",
        f"- selection_mode: `{summary['selection_mode']}`",
        f"- packet_dir: `{summary['packet_dir']}`",
        f"- executed_stages: `{', '.join(summary['executed_stages'])}`",
        f"- action_counts: `{json.dumps(summary['action_counts'], ensure_ascii=False, sort_keys=True)}`",
        (
            f"- post_import_benchmark_status_counts: "
            f"`{json.dumps(summary['post_import_benchmark_status_counts'], ensure_ascii=False, sort_keys=True)}`"
        ),
        "",
        "## Stop Point",
        f"- {summary['decision_note']}",
        "",
    ]
    return "\n".join(lines)


def write_final_summary(paths: PipelinePaths, state: PipelineState) -> dict[str, Any]:
    packet_dir = summary_packet_dir(paths, state)
    packet_manifest = load_json(packet_dir / "packet_manifest.json")
    import_summary = load_json(import_summary_path(packet_dir))
    summary = {
        "generated_at": utc_now(),
        "dataset_id": state.dataset_id,
        "family": state.family,
        "storage_mode": state.storage_mode,
        "selection_mode": state.selection_mode,
        "packet_id": state.packet_id,
        "packet_dir": str(packet_dir),
        "executed_stages": list(state.executed_stages),
        "action_counts": dict(import_summary.get("action_counts", {})),
        "post_import_benchmark_status_counts": post_import_benchmark_status_counts(packet_manifest, root=paths.backend_root),
        "decision_bearing_followup_launched": False,
        "decision_note": NO_DECISION_NOTE,
    }
    summary_json_path = packet_dir / SUMMARY_JSON_NAME
    summary_md_path = packet_dir / SUMMARY_MD_NAME
    write_json(summary_json_path, summary)
    summary_md_path.write_text(render_pipeline_summary_markdown(summary) + "\n", encoding="utf-8")
    state.pipeline_summary_path = summary_json_path
    return summary


def record_stage_command(state: PipelineState, stage: str, command: list[str] | None) -> None:
    state.stage_commands.append(
        {
            "stage": stage,
            "command": shlex.join(command) if command else "(internal final_summary)",
        }
    )


def run_pipeline(
    args: argparse.Namespace,
    *,
    paths: PipelinePaths | None = None,
    command_runner: CommandRunner = default_command_runner,
) -> dict[str, Any]:
    paths = paths or PipelinePaths.from_root(ROOT)
    stages = requested_stages(args.from_stage, args.through_stage)
    validate_selection_args(args)
    state = PipelineState(
        dataset_id=args.dataset_id,
        family=args.family,
        storage_mode=args.storage_mode,
        selection_mode=args.selection_mode,
    )

    if stages[0] == "generate_packet":
        state.packet_id = args.packet_id.strip() or default_pipeline_packet_id(
            args.dataset_id,
            selection_mode=args.selection_mode,
        )
        state.packet_dir = packet_dir_for_id(paths, state.packet_id, archived=False)
        validate_generate_prerequisites(paths, state, packet_dir_arg=args.packet_dir)
    elif stages == ["refresh_queue_summary"] and not args.packet_id.strip() and not args.packet_dir.strip():
        pass
    else:
        state.packet_id, state.packet_dir = resolve_resume_packet(
            paths,
            packet_id=args.packet_id,
            packet_dir=args.packet_dir,
        )
        if stages[0] != "refresh_queue_summary":
            validate_packet_stage_prerequisites(stages[0], paths, state)
    prevalidate_requested_range(paths, state, stages)

    for stage in stages:
        command = command_for_stage(stage, args=args, state=state)
        record_stage_command(state, stage, command)
        if args.dry_run:
            continue
        if stage == "generate_packet":
            validate_generate_prerequisites(paths, state, packet_dir_arg=args.packet_dir)
            if command is None:
                raise ValueError("generate_packet is missing its command")
            command_runner(command, paths.backend_root)
            if state.packet_dir is None or not state.packet_dir.exists():
                raise FileNotFoundError(f"generate_packet did not create the expected packet dir: {state.packet_dir}")
            state.executed_stages.append(stage)
            continue
        if stage in ACTIVE_PACKET_STAGES or stage == "final_summary":
            validate_packet_stage_prerequisites(stage, paths, state)
        if stage == "audit_packet":
            if command is None:
                raise ValueError("audit_packet is missing its command")
            command_runner(command, paths.backend_root)
            completed_audit = latest_completed_audit(paths, str(state.packet_id))
            if completed_audit is None:
                raise FileNotFoundError(f"audit_packet finished without a completed audit artifact for {state.packet_id}")
            state.audit_run = completed_audit
            state.executed_stages.append(stage)
            continue
        if stage == "adjudicate_packet":
            if command is None:
                raise ValueError("adjudicate_packet is missing its command")
            command_runner(command, paths.backend_root)
            if state.packet_dir is None or not has_adjudication_outputs(state.packet_dir):
                raise FileNotFoundError(f"adjudicate_packet finished without adjudication outputs for {state.packet_id}")
            state.executed_stages.append(stage)
            continue
        if stage == "import_packet":
            if command is None:
                raise ValueError("import_packet is missing its command")
            command_runner(command, paths.backend_root)
            archive_dir = packet_dir_for_id(paths, str(state.packet_id), archived=True)
            if not archive_dir.exists():
                raise FileNotFoundError(f"import_packet finished without creating the archived packet dir: {archive_dir}")
            state.packet_dir = archive_dir
            state.executed_stages.append(stage)
            continue
        if stage == "refresh_queue_summary":
            if command is None:
                raise ValueError("refresh_queue_summary is missing its command")
            command_runner(command, paths.backend_root)
            if not paths.queue_summary_json.exists() or not paths.queue_summary_md.exists():
                raise FileNotFoundError("refresh_queue_summary did not write the expected queue summary artifacts")
            state.executed_stages.append(stage)
            continue
        if stage == "final_summary":
            state.executed_stages.append(stage)
            summary = write_final_summary(paths, state)
            return {
                "status": "ok",
                **summary,
                "summary_json_path": str(state.pipeline_summary_path),
                "commands": list(state.stage_commands),
            }
        raise ValueError(f"Unsupported stage: {stage}")

    return {
        "status": "dry_run_ok" if args.dry_run else "ok",
        "dataset_id": state.dataset_id,
        "selection_mode": state.selection_mode,
        "packet_id": state.packet_id,
        "packet_dir": str(state.packet_dir) if state.packet_dir else "",
        "executed_stages": list(state.executed_stages),
        "planned_stages": stages,
        "commands": list(state.stage_commands),
        "decision_note": NO_DECISION_NOTE,
    }


def main() -> int:
    args = build_parser().parse_args()
    payload = run_pipeline(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
