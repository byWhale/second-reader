"""Neutral artifact layout helpers shared across backend reading mechanisms."""

from __future__ import annotations

import json
from pathlib import Path


MECHANISM_ARTIFACT_SCHEMA_VERSION = 1


def book_id_from_output_dir(output_dir: Path) -> str:
    """Derive the stable book id from the output directory name."""

    return output_dir.name


def public_dir(output_dir: Path) -> Path:
    """Directory storing user-visible stable artifacts."""

    return output_dir / "public"


def public_chapters_dir(output_dir: Path) -> Path:
    """Directory storing public per-chapter artifacts."""

    return public_dir(output_dir) / "chapters"


def assets_dir(output_dir: Path) -> Path:
    """Directory storing frontend-accessible source assets."""

    return output_dir / "_assets"


def source_asset_file(output_dir: Path) -> Path:
    """Path to the copied source EPUB asset."""

    return assets_dir(output_dir) / "source.epub"


def cover_asset_file(output_dir: Path, extension: str = ".jpg") -> Path:
    """Path to the copied cover image asset."""

    suffix = extension if extension.startswith(".") else f".{extension}"
    return assets_dir(output_dir) / f"cover{suffix}"


def existing_cover_asset_file(output_dir: Path) -> Path | None:
    """Return the first persisted cover image asset if present."""

    for path in sorted(assets_dir(output_dir).glob("cover.*")):
        if path.is_file():
            return path
    return None


def runtime_dir(output_dir: Path) -> Path:
    """Directory storing current live runtime state."""

    return output_dir / "_runtime"


def history_dir(output_dir: Path) -> Path:
    """Directory storing archived run summaries."""

    return output_dir / "_history"


def history_runs_dir(output_dir: Path) -> Path:
    """Directory storing archived runs keyed by job id."""

    return history_dir(output_dir) / "runs"


def run_history_dir(output_dir: Path, run_id: str) -> Path:
    """Directory for one archived run."""

    return history_runs_dir(output_dir) / run_id


def run_history_summary_file(output_dir: Path, run_id: str) -> Path:
    """Path to one archived run summary."""

    return run_history_dir(output_dir, run_id) / "summary.json"


def run_history_trace_file(output_dir: Path, run_id: str) -> Path:
    """Path to one archived run trace JSONL."""

    return run_history_dir(output_dir, run_id) / "trace.jsonl"


def run_history_job_file(output_dir: Path, run_id: str) -> Path:
    """Path to one archived job record."""

    return run_history_dir(output_dir, run_id) / "job.json"


def run_history_job_log_file(output_dir: Path, run_id: str) -> Path:
    """Path to one archived job log."""

    return run_history_dir(output_dir, run_id) / "job.log"


def book_manifest_file(output_dir: Path) -> Path:
    """Path to the frontend-facing book manifest JSON."""

    return public_dir(output_dir) / "book_manifest.json"


def run_state_file(output_dir: Path) -> Path:
    """Path to the frontend-facing sequential run state JSON."""

    return runtime_dir(output_dir) / "run_state.json"


def activity_file(output_dir: Path) -> Path:
    """Path to the frontend-facing sequential activity stream JSONL."""

    return runtime_dir(output_dir) / "activity.jsonl"


def parse_state_file(output_dir: Path) -> Path:
    """Path to parse-stage checkpoint metadata."""

    return runtime_dir(output_dir) / "parse_state.json"


def runtime_shell_file(output_dir: Path) -> Path:
    """Path to the shared thin runtime envelope for any mechanism."""

    return runtime_dir(output_dir) / "runtime_shell.json"


def checkpoint_summaries_dir(output_dir: Path) -> Path:
    """Directory storing shared checkpoint summaries."""

    return runtime_dir(output_dir) / "checkpoint_summaries"


def checkpoint_summary_file(output_dir: Path, checkpoint_id: str) -> Path:
    """Path to one shared checkpoint summary."""

    slug = str(checkpoint_id or "").strip() or "latest"
    return checkpoint_summaries_dir(output_dir) / f"{slug}.json"


def legacy_book_manifest_file(output_dir: Path) -> Path:
    """Legacy flat manifest path."""

    return output_dir / "book_manifest.json"


def legacy_run_state_file(output_dir: Path) -> Path:
    """Legacy flat run-state path."""

    return output_dir / "run_state.json"


def legacy_activity_file(output_dir: Path) -> Path:
    """Legacy flat activity-stream path."""

    return output_dir / "activity.jsonl"


def first_existing_path(*paths: Path) -> Path | None:
    """Return the first existing path from a candidate list."""

    for path in paths:
        if path.exists():
            return path
    return None


def resolve_output_relative_file(output_dir: Path, relative_path: str | None, *, fallback: Path | None = None) -> Path:
    """Resolve a manifest-relative artifact path with legacy fallback support."""

    candidate = output_dir / str(relative_path or "").strip() if relative_path else None
    if candidate is not None and candidate.exists():
        return candidate
    if fallback is not None and fallback.exists():
        return fallback
    if candidate is not None:
        return candidate
    if fallback is not None:
        return fallback
    raise ValueError("A relative path or fallback must be provided.")


def existing_book_manifest_file(output_dir: Path) -> Path:
    """Return the existing manifest path with legacy fallback."""

    return first_existing_path(book_manifest_file(output_dir), legacy_book_manifest_file(output_dir)) or book_manifest_file(output_dir)


def existing_run_state_file(output_dir: Path) -> Path:
    """Return the existing run-state path with legacy fallback."""

    return first_existing_path(run_state_file(output_dir), legacy_run_state_file(output_dir)) or run_state_file(output_dir)


def existing_activity_file(output_dir: Path) -> Path:
    """Return the existing activity stream path with legacy fallback."""

    return first_existing_path(activity_file(output_dir), legacy_activity_file(output_dir)) or activity_file(output_dir)


def existing_parse_state_file(output_dir: Path) -> Path:
    """Return the existing parse-state path."""

    return parse_state_file(output_dir)


def existing_runtime_shell_file(output_dir: Path) -> Path:
    """Return the existing shared runtime-envelope path."""

    return runtime_shell_file(output_dir)


def mechanisms_dir(output_dir: Path) -> Path:
    """Directory storing mechanism-private artifacts."""

    return output_dir / "_mechanisms"


def mechanism_dir(output_dir: Path, mechanism_key: str) -> Path:
    """Directory storing one mechanism's private artifacts."""

    return mechanisms_dir(output_dir) / str(mechanism_key or "").strip()


def mechanism_derived_dir(output_dir: Path, mechanism_key: str) -> Path:
    """Directory storing one mechanism's derived structural artifacts."""

    return mechanism_dir(output_dir, mechanism_key) / "derived"


def mechanism_runtime_dir(output_dir: Path, mechanism_key: str) -> Path:
    """Directory storing one mechanism's live runtime state."""

    return mechanism_dir(output_dir, mechanism_key) / "runtime"


def mechanism_internal_dir(output_dir: Path, mechanism_key: str) -> Path:
    """Directory storing one mechanism's diagnostics and internal artifacts."""

    return mechanism_dir(output_dir, mechanism_key) / "internal"


def mechanism_internal_qa_dir(output_dir: Path, mechanism_key: str) -> Path:
    """Directory storing one mechanism's chapter-level QA sidecars."""

    return mechanism_internal_dir(output_dir, mechanism_key) / "qa" / "chapters"


def mechanism_internal_diagnostics_dir(output_dir: Path, mechanism_key: str) -> Path:
    """Directory storing one mechanism's diagnostics."""

    return mechanism_internal_dir(output_dir, mechanism_key) / "diagnostics"


def mechanism_internal_analysis_dir(output_dir: Path, mechanism_key: str) -> Path:
    """Directory storing one mechanism's analysis artifacts."""

    return mechanism_internal_dir(output_dir, mechanism_key) / "analysis"


def mechanism_exports_dir(output_dir: Path, mechanism_key: str) -> Path:
    """Directory storing one mechanism's normalized exports."""

    return mechanism_dir(output_dir, mechanism_key) / "exports"


def mechanism_manifest_file(output_dir: Path, mechanism_key: str) -> Path:
    """Path to one mechanism's artifact manifest."""

    return mechanism_dir(output_dir, mechanism_key) / "manifest.json"


def mechanism_export_file(output_dir: Path, mechanism_key: str, filename: str) -> Path:
    """Path to one mechanism export artifact."""

    return mechanism_exports_dir(output_dir, mechanism_key) / filename


def mechanism_manifest_payload(output_dir: Path, mechanism_key: str) -> dict[str, object]:
    """Build the current manifest payload for one mechanism artifact tree."""

    return {
        "schema_version": MECHANISM_ARTIFACT_SCHEMA_VERSION,
        "mechanism_key": mechanism_key,
        "derived_dir": str(mechanism_derived_dir(output_dir, mechanism_key).relative_to(output_dir)),
        "runtime_dir": str(mechanism_runtime_dir(output_dir, mechanism_key).relative_to(output_dir)),
        "internal_dir": str(mechanism_internal_dir(output_dir, mechanism_key).relative_to(output_dir)),
        "exports_dir": str(mechanism_exports_dir(output_dir, mechanism_key).relative_to(output_dir)),
    }


def ensure_mechanism_manifest(output_dir: Path, mechanism_key: str) -> Path:
    """Ensure the manifest for one mechanism artifact tree exists and is current."""

    manifest_path = mechanism_manifest_file(output_dir, mechanism_key)
    payload = mechanism_manifest_payload(output_dir, mechanism_key)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    current = None
    if manifest_path.exists():
        try:
            current = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            current = None
    if current != payload:
        manifest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path


def ensure_mechanism_manifest_for_artifact_path(path: Path) -> None:
    """Ensure the corresponding mechanism manifest exists for one artifact path."""

    parts = path.parts
    if "_mechanisms" not in parts:
        return
    index = parts.index("_mechanisms")
    if len(parts) <= index + 1:
        return
    mechanism_key = parts[index + 1]
    output_dir = Path(*parts[:index])
    ensure_mechanism_manifest(output_dir, mechanism_key)
