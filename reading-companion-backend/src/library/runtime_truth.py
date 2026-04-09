"""Shared lifecycle truth helpers for public state projection and reconcile."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from src.reading_runtime.background_job_registry import PRODUCT_RUNTIME_DOMAIN, list_job_records


StatusReason = Literal[
    "runtime_stale",
    "runtime_interrupted",
    "resume_incompatible",
    "dev_run_abandoned",
]

ACTIVE_JOB_STATUSES = frozenset({"queued", "parsing_structure", "deep_reading", "chapter_note_generation"})
ACTIVE_RUNTIME_STAGES = frozenset({"parsing_structure", "deep_reading", "chapter_note_generation"})
ACTIVE_RUNTIME_STALE_SECONDS = 45
PARSE_STAGE_JOB_KINDS = frozenset({"parse"})


@dataclass(frozen=True)
class RuntimeTruthProjection:
    """Projected runtime truth for one book-scoped public state."""

    effective_stage: str | None
    status_reason: StatusReason | None
    has_active_job: bool
    has_resume_record: bool
    runtime_fresh: bool
    stale_seconds: float | None
    is_orphan_active_run: bool
    latest_job: dict[str, Any] | None


def _parse_timestamp(value: object) -> datetime | None:
    """Parse one persisted UTC timestamp when available."""

    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def seconds_since(value: object) -> float | None:
    """Return the age in seconds for one persisted timestamp."""

    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


def latest_job_for_book(book_id: str, root: Path | None = None) -> dict[str, Any] | None:
    """Return the latest canonical product-runtime job for one book."""

    matches: list[dict[str, Any]] = []
    for record in list_job_records(root, include_archived=True):
        if str(record.get("domain", "") or PRODUCT_RUNTIME_DOMAIN) != PRODUCT_RUNTIME_DOMAIN:
            continue
        if str(record.get("book_id", "") or "").strip() != book_id:
            continue
        matches.append(record)
    if not matches:
        return None
    matches.sort(
        key=lambda item: (
            str(item.get("updated_at", "")),
            str(item.get("created_at", "")),
            str(item.get("job_id", "")),
        ),
        reverse=True,
    )
    return matches[0]


def has_active_job_truth(book_id: str, root: Path | None = None) -> bool:
    """Return whether any canonical product-runtime job is still active for the book."""

    for record in list_job_records(root, include_archived=True):
        if str(record.get("domain", "") or PRODUCT_RUNTIME_DOMAIN) != PRODUCT_RUNTIME_DOMAIN:
            continue
        if str(record.get("book_id", "") or "").strip() != book_id:
            continue
        if str(record.get("status", "") or "").strip() in ACTIVE_JOB_STATUSES:
            return True
    return False


def infer_status_reason(*messages: object) -> StatusReason | None:
    """Infer one public status reason from persisted error/message text when possible."""

    normalized = " ".join(str(item or "").strip().lower() for item in messages if str(item or "").strip())
    if not normalized:
        return None
    if "older development boot" in normalized or "development session was abandoned" in normalized:
        return "dev_run_abandoned"
    if "incompatible checkpoint" in normalized or "resume_incompatible" in normalized:
        return "resume_incompatible"
    if "runtime activity stalled" in normalized or "runtime updates stopped arriving" in normalized:
        return "runtime_stale"
    if (
        "stopped unexpectedly" in normalized
        or "处理中断" in normalized
        or "任务已停止" in normalized
        or "interrupted" in normalized
    ):
        return "runtime_interrupted"
    return None


def read_checkpoint_available(
    run_state: dict[str, Any] | None,
    runtime_shell: dict[str, Any] | None = None,
) -> bool:
    """Return whether one read-stage runtime has a real resume checkpoint."""

    state = run_state or {}
    shell = runtime_shell or {}
    return bool(
        state.get("last_checkpoint_at")
        or shell.get("last_checkpoint_id")
        or shell.get("last_checkpoint_at")
    )


def parse_checkpoint_available(parse_state: dict[str, Any] | None) -> bool:
    """Return whether one parse-stage runtime has a real resume point."""

    state = parse_state or {}
    return bool(
        state.get("last_checkpoint_at")
        or state.get("parsed_chapter_ids")
        or state.get("segmented_chapter_ids")
    )


def effective_resume_available(
    *,
    stage: str | None,
    run_state: dict[str, Any] | None,
    parse_state: dict[str, Any] | None,
    runtime_shell: dict[str, Any] | None,
    latest_job: dict[str, Any] | None,
) -> bool:
    """Return whether the current book truthfully has a usable resume path."""

    if not latest_job:
        return False
    upload_path = Path(str(latest_job.get("upload_path", "") or ""))
    if not upload_path.exists():
        return False

    effective_stage = str(stage or "").strip()
    job_kind = str((latest_job or {}).get("job_kind", "") or "").strip()
    uses_parse_checkpoint = effective_stage == "parsing_structure" or (
        effective_stage == "paused" and job_kind in PARSE_STAGE_JOB_KINDS
    )
    if uses_parse_checkpoint:
        state = parse_state or {}
        return bool(state.get("resume_available")) and parse_checkpoint_available(state)

    state = run_state or {}
    shell = runtime_shell or {}
    return bool(state.get("resume_available") or shell.get("resume_available")) and read_checkpoint_available(state, shell)


def coalesce_last_checkpoint_at(
    *,
    stage: str | None,
    run_state: dict[str, Any] | None,
    parse_state: dict[str, Any] | None,
    runtime_shell: dict[str, Any] | None,
    latest_job: dict[str, Any] | None = None,
) -> str | None:
    """Return the best available checkpoint timestamp for the effective stage."""

    effective_stage = str(stage or "").strip()
    job_kind = str((latest_job or {}).get("job_kind", "") or "").strip()
    uses_parse_checkpoint = effective_stage == "parsing_structure" or (
        effective_stage == "paused" and job_kind in PARSE_STAGE_JOB_KINDS
    )
    if uses_parse_checkpoint:
        return str((parse_state or {}).get("last_checkpoint_at", "") or (run_state or {}).get("last_checkpoint_at", "") or "").strip() or None
    return str((run_state or {}).get("last_checkpoint_at", "") or (runtime_shell or {}).get("last_checkpoint_at", "") or "").strip() or None


def project_runtime_truth(
    book_id: str,
    run_state: dict[str, Any] | None,
    *,
    root: Path | None = None,
) -> RuntimeTruthProjection:
    """Project persisted job/runtime artifacts into one public lifecycle truth."""

    latest_job = latest_job_for_book(book_id, root=root)
    has_active_job = has_active_job_truth(book_id, root=root)
    stage = str((run_state or {}).get("stage", "") or "").strip() or None
    stale_seconds = seconds_since((run_state or {}).get("updated_at"))
    runtime_fresh = stale_seconds is not None and stale_seconds < ACTIVE_RUNTIME_STALE_SECONDS
    active_runtime_stage = stage in ACTIVE_RUNTIME_STAGES
    is_orphan_active_run = bool(active_runtime_stage and not has_active_job and stale_seconds is not None and stale_seconds >= ACTIVE_RUNTIME_STALE_SECONDS)
    status_reason = infer_status_reason(
        (run_state or {}).get("error"),
        latest_job.get("error") if isinstance(latest_job, dict) else None,
    )
    effective_stage = stage
    if is_orphan_active_run:
        effective_stage = "paused"
        status_reason = status_reason or "runtime_stale"
    return RuntimeTruthProjection(
        effective_stage=effective_stage,
        status_reason=status_reason,
        has_active_job=has_active_job,
        has_resume_record=bool(latest_job),
        runtime_fresh=runtime_fresh,
        stale_seconds=stale_seconds,
        is_orphan_active_run=is_orphan_active_run,
        latest_job=latest_job,
    )


def iter_orphan_active_runs(root: Path | None = None) -> list[tuple[str, dict[str, Any], RuntimeTruthProjection]]:
    """Return stale active runs that no longer have active canonical job truth."""

    results: list[tuple[str, dict[str, Any], RuntimeTruthProjection]] = []
    output_dir = (root or Path.cwd()) / "output"
    for run_state_path in sorted(output_dir.glob("*/_runtime/run_state.json")):
        book_id = run_state_path.parent.parent.name
        try:
            run_state = json.loads(run_state_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if not isinstance(run_state, dict):
            continue
        projection = project_runtime_truth(book_id, run_state, root=root)
        if projection.is_orphan_active_run:
            results.append((book_id, run_state, projection))
    return results
