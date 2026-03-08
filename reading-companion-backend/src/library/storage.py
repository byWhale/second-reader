"""Filesystem helpers for product-layer state."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def timestamp() -> str:
    """Return a stable UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def state_dir(root: Path | None = None) -> Path:
    """Root directory for product-layer state."""
    return (root or Path.cwd()) / "state"


def uploads_dir(root: Path | None = None) -> Path:
    """Directory storing uploaded EPUB files."""
    return state_dir(root) / "uploads"


def jobs_dir(root: Path | None = None) -> Path:
    """Directory storing job records."""
    return state_dir(root) / "jobs"


def user_marks_file(root: Path | None = None) -> Path:
    """Path to the single-user marks state file."""
    return state_dir(root) / "user_marks.json"


def job_file(job_id: str, root: Path | None = None) -> Path:
    """Path to one persisted job record."""
    return jobs_dir(root) / f"{job_id}.json"


def job_log_file(job_id: str, root: Path | None = None) -> Path:
    """Path to one background job log file."""
    return jobs_dir(root) / f"{job_id}.log"


def upload_file(job_id: str, root: Path | None = None) -> Path:
    """Path to one uploaded EPUB."""
    return uploads_dir(root) / f"{job_id}.epub"


def save_json(path: Path, payload: object) -> None:
    """Persist JSON with UTF-8 formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path) -> dict:
    """Load one JSON object from disk."""
    return json.loads(path.read_text(encoding="utf-8"))
