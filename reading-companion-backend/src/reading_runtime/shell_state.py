"""Shared thin runtime-shell helpers for multi-mechanism backend runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.reading_core.runtime_contracts import CheckpointSummary, ResumeKind, RuntimeShellState, SharedRunCursor

from .artifacts import checkpoint_summary_file, runtime_shell_file


def _timestamp() -> str:
    """Return a stable UTC timestamp."""

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def empty_cursor() -> SharedRunCursor:
    """Return the default shared cursor before live reading begins."""

    return {
        "position_kind": "chapter",
        "chapter_id": None,
        "chapter_ref": "",
    }


def build_runtime_shell(
    *,
    mechanism_key: str,
    mechanism_version: str,
    policy_version: str,
    status: str = "initialized",
    phase: str = "preparing",
) -> RuntimeShellState:
    """Build the default shared runtime shell for one mechanism run."""

    return {
        "mechanism_key": mechanism_key,
        "mechanism_version": mechanism_version,
        "policy_version": policy_version,
        "status": status,
        "phase": phase,
        "cursor": empty_cursor(),
        "active_artifact_refs": {},
        "resume_available": False,
        "last_checkpoint_id": None,
        "last_checkpoint_at": None,
        "updated_at": _timestamp(),
    }


def ensure_runtime_shell(
    output_dir: Path,
    *,
    mechanism_key: str,
    mechanism_version: str,
    policy_version: str,
) -> RuntimeShellState:
    """Ensure the shared runtime shell exists for one output directory."""

    path = runtime_shell_file(output_dir)
    if path.exists():
        return load_runtime_shell(path)
    shell = build_runtime_shell(
        mechanism_key=mechanism_key,
        mechanism_version=mechanism_version,
        policy_version=policy_version,
    )
    save_runtime_shell(path, shell)
    return shell


def build_checkpoint_summary(
    *,
    checkpoint_id: str,
    mechanism_key: str,
    mechanism_version: str,
    policy_version: str,
    resume_kind: ResumeKind = "warm_resume",
) -> CheckpointSummary:
    """Build a thin shared checkpoint summary."""

    return {
        "checkpoint_id": checkpoint_id,
        "mechanism_key": mechanism_key,
        "mechanism_version": mechanism_version,
        "policy_version": policy_version,
        "created_at": _timestamp(),
        "resume_kind": resume_kind,
        "cursor": empty_cursor(),
        "active_artifact_refs": {},
        "visible_reaction_ids": [],
    }


def save_runtime_shell(path: Path, payload: RuntimeShellState) -> None:
    """Persist one shared runtime shell payload."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_runtime_shell(path: Path) -> RuntimeShellState:
    """Load one shared runtime shell payload."""

    return json.loads(path.read_text(encoding="utf-8"))


def save_checkpoint_summary(path: Path, payload: CheckpointSummary) -> None:
    """Persist one shared checkpoint summary payload."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_checkpoint_summary(path: Path) -> CheckpointSummary:
    """Load one shared checkpoint summary payload."""

    return json.loads(path.read_text(encoding="utf-8"))


def write_checkpoint_summary(output_dir: Path, payload: CheckpointSummary) -> Path:
    """Persist one shared checkpoint summary under the standard runtime path."""

    path = checkpoint_summary_file(output_dir, str(payload.get("checkpoint_id", "") or "latest"))
    save_checkpoint_summary(path, payload)
    return path
