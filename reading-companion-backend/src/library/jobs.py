"""Background job helpers for uploaded sequential deep-read runs."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .catalog import find_book_id_by_source, source_asset_path
from .runtime_truth import (
    effective_resume_available,
    iter_orphan_active_runs,
    latest_job_for_book,
)
from .storage import (
    job_file,
    job_log_file,
    load_json as load_job_json,
    save_json as save_job_json,
    timestamp,
    upload_file,
)
from src.config import (
    get_backend_boot_id,
    get_backend_run_mode,
    get_backend_version,
    get_reader_resume_compat_version,
)
from src.reading_runtime import default_mechanism_key
from src.reading_runtime.artifacts import existing_runtime_shell_file
from src.reading_runtime.background_job_registry import (
    PRODUCT_RUNTIME_DOMAIN,
    list_job_records,
    load_job_record,
    migrate_product_shadow_jobs,
    save_job_record,
)
from src.reading_runtime.provisioning import ensure_book_assets, ensure_output_dir, inspect_book
from src.reading_runtime.sequential_state import (
    append_activity_event,
    append_deduped_activity_event,
    build_run_state,
    build_minimal_book_manifest,
    reset_activity,
    write_book_manifest,
    write_run_state,
)
from src.iterator_reader.storage import (
    clear_iterator_private_artifacts,
    chapter_qa_file,
    book_id_from_output_dir,
    existing_activity_file,
    existing_book_manifest_file,
    existing_chapter_markdown_file,
    existing_chapter_result_file,
    existing_parse_state_file,
    existing_run_state_file,
    existing_structure_file,
    legacy_activity_file,
    legacy_book_manifest_file,
    legacy_run_state_file,
    load_json as load_structure_json,
    load_json as load_runtime_json,
    runtime_dir,
    run_history_job_file,
    run_history_job_log_file,
    run_history_summary_file,
    run_history_trace_file,
    save_structure,
)


AUTO_RESUME_LIMIT = 1
ACTIVE_JOB_STATUSES = {"queued", "parsing_structure", "deep_reading", "chapter_note_generation"}
TERMINAL_JOB_STATUSES = {"completed", "error"}
MIN_SUPPORTED_PYTHON = (3, 11)
ACTIVE_RUNTIME_STALE_SECONDS = 45


def _job_record(
    *,
    job_id: str,
    status: str,
    upload_path: Path,
    job_kind: str,
    mechanism_key: str | None = None,
    language: str = "auto",
    intent: str | None = None,
    resume_count: int = 0,
    auto_resume_count: int = 0,
    book_id: str | None = None,
    pid: int | None = None,
    error: str | None = None,
    created_at: str | None = None,
) -> dict:
    """Build one persisted job record."""
    now = timestamp()
    return {
        "job_id": job_id,
        "status": status,
        "job_kind": job_kind,
        "mechanism_key": str(mechanism_key or "").strip() or None,
        "upload_path": str(upload_path),
        "book_id": book_id,
        "language": language,
        "intent": intent,
        "resume_count": int(resume_count),
        "auto_resume_count": int(auto_resume_count),
        "pid": pid,
        "boot_id": get_backend_boot_id(),
        "backend_version": get_backend_version(),
        "resume_compat_version": get_reader_resume_compat_version(),
        "python_executable": sys.executable,
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        "created_at": created_at or now,
        "updated_at": now,
        "error": error,
    }


def _normalize_record(record: dict) -> dict:
    """Backfill defaults for older job records."""
    status = str(record.get("status", "queued") or "queued")
    job_kind = str(record.get("job_kind", "") or "").strip()
    if not job_kind:
        job_kind = "parse" if status in {"queued", "parsing_structure", "ready"} else "read"
    return {
        **record,
        "job_kind": job_kind,
        "mechanism_key": str(record.get("mechanism_key", "") or "").strip() or None,
        "language": str(record.get("language", "auto") or "auto"),
        "intent": str(record.get("intent", "") or "") or None,
        "resume_count": int(record.get("resume_count", 0) or 0),
        "auto_resume_count": int(record.get("auto_resume_count", 0) or 0),
        "boot_id": str(record.get("boot_id", "") or "") or None,
        "backend_version": str(record.get("backend_version", "") or "") or None,
        "resume_compat_version": _resume_compat_version(record.get("resume_compat_version")),
    }


def _process_running(pid: int | None) -> bool:
    """Return whether a subprocess still appears alive."""
    if not pid:
        return False
    try:
        waited_pid, _status = os.waitpid(int(pid), os.WNOHANG)
        if waited_pid == int(pid):
            return False
    except ChildProcessError:
        pass
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def _python_runtime_issue() -> str | None:
    """Return a user-facing runtime issue when the current interpreter is unsupported."""
    if sys.version_info < MIN_SUPPORTED_PYTHON:
        return (
            "Background jobs require Python "
            f"{MIN_SUPPORTED_PYTHON[0]}.{MIN_SUPPORTED_PYTHON[1]}+ but the backend is running under "
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} "
            f"({sys.executable})."
        )
    return None


def _resume_compat_version(value: object) -> int | None:
    """Normalize one persisted resume-compat marker."""
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _run_state_resume_compat(run_state: dict | None) -> int | None:
    """Return the resume-compat version recorded in runtime artifacts."""
    return _resume_compat_version((run_state or {}).get("resume_compat_version"))


def _record_resume_compat(record: dict) -> int | None:
    """Return the resume-compat version recorded in the job record."""
    return _resume_compat_version(record.get("resume_compat_version"))


def _resume_compatible(*, record: dict, run_state: dict | None, parse_state: dict | None = None) -> bool:
    """Return whether persisted job/runtime artifacts can be safely resumed."""
    expected = get_reader_resume_compat_version()
    if _record_resume_compat(record) != expected:
        return False

    known_state_versions: list[int | None] = []
    if run_state is not None:
        known_state_versions.append(_run_state_resume_compat(run_state))
    if parse_state is not None:
        known_state_versions.append(_resume_compat_version(parse_state.get("resume_compat_version")))
    if not known_state_versions:
        return True
    return all(version == expected for version in known_state_versions)


def _is_dev_boot_mismatch(record: dict) -> bool:
    """Return whether a job belongs to an older development backend boot."""
    if get_backend_run_mode() != "dev":
        return False
    recorded_boot_id = str(record.get("boot_id", "") or "").strip()
    if not recorded_boot_id:
        return False
    return recorded_boot_id != get_backend_boot_id()


def _parse_timestamp(value: object) -> datetime | None:
    """Parse one UTC timestamp when available."""
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _seconds_since(value: object) -> float | None:
    """Return age in seconds for one persisted timestamp."""
    parsed = _parse_timestamp(value)
    if parsed is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


def _activity_context(run_state: dict | None) -> dict[str, object]:
    """Extract the recent reading location from run_state."""
    state = run_state or {}
    return {
        "chapter_id": int(state.get("current_chapter_id", 0) or 0) or None,
        "chapter_ref": str(state.get("current_chapter_ref", "") or "") or None,
        "segment_ref": str(state.get("current_segment_ref", "") or "") or None,
    }


def _runtime_stalled_message(run_state: dict | None, *, stale_seconds: float) -> str:
    """Build one operator-facing stalled-runtime summary."""
    state = run_state or {}
    segment_ref = str(state.get("current_segment_ref", "") or "").strip()
    chapter_ref = str(state.get("current_chapter_ref", "") or "").strip()
    target = segment_ref or chapter_ref or "the current section"
    return f"Runtime activity stalled for {int(round(stale_seconds))}s while reading {target}."


def _status_from_run_state(run_state: dict | None, *, running: bool) -> tuple[str, str | None]:
    """Map run_state into the public job status vocabulary."""
    if not run_state:
        return ("parsing_structure" if running else "queued"), None

    stage = str(run_state.get("stage", "")).strip()
    error = str(run_state.get("error", "") or "") or None
    if stage == "parsing_structure":
        return "parsing_structure", error
    if stage == "deep_reading":
        return "deep_reading", error
    if stage == "completed":
        return "completed", error
    if stage == "paused":
        return "paused", error
    if stage == "error":
        return "error", error
    if stage == "ready":
        return ("parsing_structure" if running else "ready"), error
    return ("parsing_structure" if running else "queued"), error


def create_upload_job(root: Path | None = None) -> tuple[str, Path]:
    """Allocate a job id and upload path."""
    job_id = uuid.uuid4().hex[:12]
    return job_id, upload_file(job_id, root)


def save_job(record: dict, root: Path | None = None) -> dict:
    """Persist one job record."""
    normalized = _normalize_record(record)
    normalized["updated_at"] = timestamp()
    save_job_json(job_file(str(normalized["job_id"]), root), normalized)
    canonical_payload = {
        **normalized,
        "domain": PRODUCT_RUNTIME_DOMAIN,
        "lane": "product_runtime",
        "phase": str(normalized.get("status", "")),
        "show_in_active_views": False,
        "log_file": str(job_log_file(str(normalized["job_id"]), root)),
        "purpose": str(
            normalized.get("purpose")
            or ("Sequential deep reading job" if str(normalized.get("job_kind", "read")) == "read" else "Structure parse job")
        ),
        "cwd": str(root or Path.cwd()),
    }
    book_id = str(normalized.get("book_id", "") or "").strip()
    if book_id:
        canonical_payload["run_dir"] = str(_book_output_dir(book_id, root))
    save_job_record(canonical_payload, root=root)
    return normalized


def load_job(job_id: str, root: Path | None = None) -> dict:
    """Load one job record."""
    try:
        return _normalize_record(load_job_record(job_id, root=root))
    except FileNotFoundError:
        return _normalize_record(load_job_json(job_file(job_id, root)))


def _normalized_mechanism_key(value: object) -> str | None:
    """Return one cleaned mechanism key or None."""

    cleaned = str(value or "").strip()
    return cleaned or None


def _resolved_mechanism_key(value: object) -> str | None:
    """Resolve one mechanism key while omitting the current default from CLI flags."""

    mechanism_key = _normalized_mechanism_key(value)
    if mechanism_key == default_mechanism_key():
        return None
    return mechanism_key


def _job_command(record: dict, *, continue_mode: bool, mechanism_key: str | None = None) -> list[str]:
    """Build the CLI command for one persisted job record."""
    upload_path = Path(str(record.get("upload_path", "")))
    language = str(record.get("language", "auto") or "auto")
    intent = str(record.get("intent", "") or "") or None
    job_kind = str(record.get("job_kind", "read") or "read")
    selected_mechanism = _resolved_mechanism_key(mechanism_key or record.get("mechanism_key"))

    if job_kind == "parse":
        command = [
            sys.executable,
            "main.py",
            "parse",
            str(upload_path),
            "--language",
            language,
        ]
        if continue_mode:
            command.append("--continue")
        if selected_mechanism:
            command.extend(["--mechanism", selected_mechanism])
        return command

    command = [
        sys.executable,
        "main.py",
        "read",
        str(upload_path),
        "--mode",
        "sequential",
        "--language",
        language,
    ]
    if continue_mode:
        command.append("--continue")
    if intent:
        command.extend(["--intent", intent])
    if selected_mechanism:
        command.extend(["--mechanism", selected_mechanism])
    return command


def _launch_subprocess_job(
    *,
    upload_path: Path,
    command: list[str],
    job_kind: str,
    mechanism_key: str | None = None,
    language: str = "auto",
    intent: str | None = None,
    root: Path | None = None,
    job_id: str | None = None,
    initial_status: str = "queued",
    book_id: str | None = None,
    resume_count: int = 0,
) -> dict:
    """Start a detached subprocess and persist the tracking record."""
    resolved_job_id = job_id or upload_path.stem
    runtime_issue = _python_runtime_issue()
    record = _job_record(
        job_id=resolved_job_id,
        status="error" if runtime_issue else initial_status,
        upload_path=upload_path,
        job_kind=job_kind,
        mechanism_key=mechanism_key,
        language=language,
        intent=intent,
        book_id=book_id,
        resume_count=resume_count,
        error=runtime_issue,
    )
    record["command"] = " ".join(command)
    record["cwd"] = str(root or Path.cwd())
    saved_record = save_job(record, root)
    if runtime_issue:
        if book_id:
            append_deduped_activity_event(
                _book_output_dir(book_id, root),
                {
                    "type": "runtime_environment_error",
                    "message": "Background job started under unsupported Python runtime.",
                    "details": {
                        "reason": runtime_issue,
                        "python_executable": sys.executable,
                        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    },
                },
            )
        return saved_record

    log_path = job_log_file(resolved_job_id, root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=str(root or Path.cwd()),
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    launched_record = _job_record(
        job_id=resolved_job_id,
        status=initial_status,
        upload_path=upload_path,
        job_kind=job_kind,
        mechanism_key=mechanism_key,
        language=language,
        intent=intent,
        book_id=book_id,
        resume_count=resume_count,
        pid=process.pid,
        created_at=str(record["created_at"]),
    )
    launched_record["command"] = " ".join(command)
    launched_record["cwd"] = str(root or Path.cwd())
    return save_job(launched_record, root)


def launch_sequential_job(
    upload_path: Path,
    *,
    mechanism_key: str | None = None,
    language: str = "auto",
    intent: str | None = None,
    root: Path | None = None,
    book_id: str | None = None,
) -> dict:
    """Start a sequential read as a detached subprocess and persist the job."""
    command = [
        sys.executable,
        "main.py",
        "read",
        str(upload_path),
        "--mode",
        "sequential",
        "--language",
        language,
    ]
    if _resolved_mechanism_key(mechanism_key):
        command.extend(["--mechanism", str(mechanism_key)])
    if intent:
        command.extend(["--intent", intent])

    return _launch_subprocess_job(
        upload_path=upload_path,
        command=command,
        job_kind="read",
        mechanism_key=mechanism_key,
        language=language,
        intent=intent,
        root=root,
        initial_status="queued",
        book_id=book_id,
    )


def launch_parse_job(
    upload_path: Path,
    *,
    mechanism_key: str | None = None,
    language: str = "auto",
    root: Path | None = None,
    book_id: str | None = None,
) -> dict:
    """Start a structure-only parse job and persist the job record."""
    command = [
        sys.executable,
        "main.py",
        "parse",
        str(upload_path),
        "--language",
        language,
    ]
    if _resolved_mechanism_key(mechanism_key):
        command.extend(["--mechanism", str(mechanism_key)])
    return _launch_subprocess_job(
        upload_path=upload_path,
        command=command,
        job_kind="parse",
        mechanism_key=mechanism_key,
        language=language,
        root=root,
        initial_status="queued",
        book_id=book_id,
    )


def provision_uploaded_book(
    upload_path: Path,
    *,
    mechanism_key: str | None = None,
    language: str = "auto",
    root: Path | None = None,
) -> str | None:
    """Create a minimal book shell so uploads can resolve a book id immediately."""
    try:
        provisioned = inspect_book(upload_path, language_mode=language, sample_text="")
        output_dir = provisioned.output_dir
        book_id = book_id_from_output_dir(output_dir)
        manifest_path = existing_book_manifest_file(output_dir)
        if manifest_path.exists():
            return book_id

        ensure_output_dir(output_dir)
        ensure_book_assets(upload_path, output_dir)

        manifest = build_minimal_book_manifest(
            output_dir,
            book_title=provisioned.title,
            author=provisioned.author,
            book_language=provisioned.book_language,
            output_language=provisioned.output_language,
            source_file=str(upload_path),
            chapters=[],
        )
        write_book_manifest(output_dir, manifest)
        write_run_state(
            output_dir,
            build_run_state(
                book_title=provisioned.title,
                stage="ready",
                total_chapters=0,
                completed_chapters=0,
            ),
        )
        append_activity_event(
            output_dir,
            {
                "type": "upload_received",
                "message": "文件已上传，正在解析书籍结构。",
            },
        )
        return book_id
    except Exception:
        return None


def launch_existing_book_read_job(
    book_id: str,
    *,
    mechanism_key: str | None = None,
    language: str = "auto",
    intent: str | None = None,
    root: Path | None = None,
) -> dict:
    """Start the active sequential deep-reading workflow for an existing uploaded book."""
    source_path = source_asset_path(book_id, root=root)
    if not source_path.exists():
        raise FileNotFoundError(source_path)

    command = [
        sys.executable,
        "main.py",
        "read",
        str(source_path),
        "--mode",
        "sequential",
        "--language",
        language,
    ]
    if _resolved_mechanism_key(mechanism_key):
        command.extend(["--mechanism", str(mechanism_key)])
    if intent:
        command.extend(["--intent", intent])

    return _launch_subprocess_job(
        upload_path=source_path,
        command=command,
        job_kind="read",
        mechanism_key=mechanism_key,
        language=language,
        intent=intent,
        root=root,
        job_id=uuid.uuid4().hex[:12],
        initial_status="queued",
        book_id=book_id,
    )


def launch_book_analysis_job(
    book_id: str,
    *,
    mechanism_key: str | None = None,
    language: str = "auto",
    intent: str | None = None,
    root: Path | None = None,
) -> dict:
    """Deprecated compatibility alias for the active existing-book deep-reading launcher."""

    return launch_existing_book_read_job(
        book_id,
        mechanism_key=mechanism_key,
        language=language,
        intent=intent,
        root=root,
    )


def _book_output_dir(book_id: str, root: Path | None = None) -> Path:
    """Resolve one book output directory."""
    return (root or Path.cwd()) / "output" / book_id


def _load_book_run_state(book_id: str, root: Path | None = None) -> dict | None:
    """Read the raw persisted run_state payload for one book."""
    path = existing_run_state_file(_book_output_dir(book_id, root))
    return load_runtime_json(path) if path.exists() else None


def _load_book_parse_state(book_id: str, root: Path | None = None) -> dict | None:
    """Read the raw persisted parse_state payload for one book."""
    path = existing_parse_state_file(_book_output_dir(book_id, root))
    return load_runtime_json(path) if path.exists() else None


def _load_book_runtime_shell(book_id: str, root: Path | None = None) -> dict | None:
    """Read the shared runtime shell payload for one book when available."""

    path = existing_runtime_shell_file(_book_output_dir(book_id, root))
    return load_runtime_json(path) if path.exists() else None


def _legacy_resume_mechanism_key(book_id: str, root: Path | None = None) -> str | None:
    """Infer one legacy mechanism key for old resumable runs that predate shell metadata."""

    output_dir = _book_output_dir(book_id, root)
    if existing_structure_file(output_dir).exists():
        return "iterator_v1"
    return None


def _resume_mechanism_key(record: dict, *, book_id: str | None, root: Path | None = None) -> str | None:
    """Resolve the mechanism key for resume/recovery with shell-first precedence."""

    if book_id:
        runtime_shell = _load_book_runtime_shell(book_id, root)
        if isinstance(runtime_shell, dict):
            mechanism_key = _normalized_mechanism_key(runtime_shell.get("mechanism_key"))
            if mechanism_key:
                return mechanism_key
    mechanism_key = _normalized_mechanism_key(record.get("mechanism_key"))
    if mechanism_key:
        return mechanism_key
    if book_id:
        legacy_mechanism_key = _legacy_resume_mechanism_key(book_id, root)
        if legacy_mechanism_key:
            return legacy_mechanism_key
    return default_mechanism_key()


def _terminate_process(pid: int | None) -> None:
    """Best-effort terminate one stale background worker."""
    if not pid:
        return
    try:
        os.kill(int(pid), signal.SIGTERM)
    except OSError:
        return


def _clear_live_analysis_artifacts(book_id: str, root: Path | None = None) -> None:
    """Reset live deep-reading artifacts so one fresh run can start cleanly."""
    from src.iterator_reader.frontend_artifacts import (
        build_run_state as build_iterator_run_state,
        write_book_manifest as write_iterator_book_manifest,
    )

    output_dir = _book_output_dir(book_id, root)
    structure_path = existing_structure_file(output_dir)
    manifest_path = existing_book_manifest_file(output_dir)
    legacy_manifest_path = legacy_book_manifest_file(output_dir)
    legacy_run_state_path = legacy_run_state_file(output_dir)
    legacy_activity_path = legacy_activity_file(output_dir)
    preserve_legacy_manifest = legacy_manifest_path.exists()
    preserve_legacy_run_state = legacy_run_state_path.exists()
    preserve_legacy_activity = legacy_activity_path.exists()
    if not structure_path.exists():
        clear_iterator_private_artifacts(output_dir)
        shutil.rmtree(runtime_dir(output_dir), ignore_errors=True)
        return

    structure = load_structure_json(structure_path)
    chapters = list(structure.get("chapters", []))
    for chapter in chapters:
        chapter.pop("output_file", None)
        chapter["status"] = "pending"
        for segment in chapter.get("segments", []):
            if isinstance(segment, dict):
                segment["status"] = "pending"
        existing_chapter_markdown_file(output_dir, chapter).unlink(missing_ok=True)
        existing_chapter_result_file(output_dir, chapter).unlink(missing_ok=True)
        chapter_qa_file(output_dir, chapter).unlink(missing_ok=True)

    shutil.rmtree(runtime_dir(output_dir), ignore_errors=True)
    clear_iterator_private_artifacts(output_dir)
    save_structure(structure_path, structure)
    if manifest_path.exists():
        manifest = write_iterator_book_manifest(output_dir, structure)
        if preserve_legacy_manifest:
            save_job_json(legacy_manifest_path, manifest)
    reset_activity(output_dir)
    run_state = write_run_state(
        output_dir,
        build_iterator_run_state(
            structure,
            stage="ready",
            total_chapters=len(chapters),
            completed_chapters=0,
            current_phase_step=None,
            resume_available=False,
            last_checkpoint_at=None,
        ),
    )
    if preserve_legacy_activity:
        legacy_activity_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_activity_path.write_text("", encoding="utf-8")
    if preserve_legacy_run_state:
        save_job_json(legacy_run_state_path, run_state)


def _current_run_stage(book_id: str, root: Path | None = None) -> str:
    """Read the current runtime stage for one book when available."""
    run_state_path = existing_run_state_file(_book_output_dir(book_id, root))
    if not run_state_path.exists():
        return "parsing_structure"
    return str(load_runtime_json(run_state_path).get("stage", "parsing_structure"))


def _resume_target_status(record: dict, book_id: str | None, root: Path | None = None) -> str:
    """Choose the status that should be resumed for one stalled job."""
    job_kind = str(record.get("job_kind", "read") or "read")
    if job_kind == "parse":
        return "parsing_structure"

    current_status = str(record.get("status", "queued") or "queued")
    if current_status in {"parsing_structure", "ready"}:
        return "parsing_structure"
    if book_id:
        stage = _current_run_stage(book_id, root)
        if stage == "parsing_structure":
            return "parsing_structure"
    return "deep_reading"


def _pause_runtime_state(
    book_id: str,
    *,
    previous_status: str,
    error: str,
    root: Path | None = None,
    latest_job: dict | None = None,
) -> None:
    """Write paused status into the book runtime files."""
    output_dir = _book_output_dir(book_id, root)
    run_state_path = existing_run_state_file(output_dir)
    parse_state_path = existing_parse_state_file(output_dir)
    runtime_shell = _load_book_runtime_shell(book_id, root)
    parse_payload = load_runtime_json(parse_state_path) if parse_state_path.exists() else None
    if run_state_path.exists():
        payload = load_runtime_json(run_state_path)
        payload["stage"] = "paused"
        payload["error"] = error
        payload["resume_available"] = effective_resume_available(
            stage="paused",
            run_state=payload,
            parse_state=parse_payload,
            runtime_shell=runtime_shell,
            latest_job=latest_job,
        )
        payload["updated_at"] = timestamp()
        payload["current_phase_step"] = "等待继续执行"
        payload["last_checkpoint_at"] = payload.get("last_checkpoint_at") or (runtime_shell or {}).get("last_checkpoint_at")
        save_job_json(run_state_path, payload)

    if previous_status == "parsing_structure" and parse_state_path.exists():
        payload = parse_payload or {}
        payload["status"] = "paused"
        payload["error"] = error
        payload["resume_available"] = effective_resume_available(
            stage="paused",
            run_state=load_runtime_json(run_state_path) if run_state_path.exists() else None,
            parse_state=payload,
            runtime_shell=runtime_shell,
            latest_job=latest_job,
        )
        payload["updated_at"] = timestamp()
        save_job_json(parse_state_path, payload)


def _abandon_dev_run(record: dict, *, book_id: str | None, run_state: dict | None, root: Path | None = None) -> dict:
    """Mark one cross-boot development run as abandoned instead of resuming it."""
    normalized = _normalize_record(record)
    pid = int(normalized.get("pid", 0) or 0) or None
    _terminate_process(pid)
    message = "Detected an unfinished reader from an older development boot; start a fresh run instead of resuming it."
    if book_id:
        _pause_runtime_state(
            book_id,
            previous_status=_resume_target_status(normalized, book_id, root),
            error=message,
            root=root,
            latest_job=normalized,
        )
        append_deduped_activity_event(
            _book_output_dir(book_id, root),
            {
                "type": "dev_run_abandoned",
                "message": "Reader from an older development session was abandoned after a backend restart.",
                **_activity_context(run_state),
                "details": {
                    "job_id": str(normalized.get("job_id", "")),
                    "boot_id": normalized.get("boot_id"),
                },
            },
        )
    return save_job(
        {
            **normalized,
            "status": "paused" if book_id else "error",
            "book_id": book_id,
            "pid": None,
            "error": message,
        },
        root,
    )


def _fresh_rerun_after_incompatibility(record: dict, *, book_id: str | None, root: Path | None = None) -> dict:
    """Archive one incompatible run, reset live artifacts, and launch a fresh job."""
    normalized = _normalize_record(record)
    resolved_book_id = str(book_id or normalized.get("book_id", "") or "").strip() or None
    mechanism_key = _resume_mechanism_key(normalized, book_id=resolved_book_id, root=root)
    reason = "Detected an incompatible resume checkpoint; clearing live analysis artifacts and starting a fresh run."
    _terminate_process(int(normalized.get("pid", 0) or 0) or None)
    archived_job = save_job(
        {
            **normalized,
            "status": "error",
            "book_id": resolved_book_id,
            "pid": None,
            "error": reason,
        },
        root,
    )
    if resolved_book_id:
        _archive_run_artifacts(book_id=resolved_book_id, job=archived_job, root=root)
        _clear_live_analysis_artifacts(resolved_book_id, root)

    fresh_record = _launch_subprocess_job(
        upload_path=Path(str(normalized.get("upload_path", ""))),
        command=_job_command(normalized, continue_mode=False, mechanism_key=mechanism_key),
        job_kind=str(normalized.get("job_kind", "read") or "read"),
        mechanism_key=mechanism_key,
        language=str(normalized.get("language", "auto") or "auto"),
        intent=normalized.get("intent"),
        root=root,
        job_id=uuid.uuid4().hex[:12],
        initial_status="queued",
        book_id=resolved_book_id,
    )
    if resolved_book_id:
        append_activity_event(
            _book_output_dir(resolved_book_id, root),
            {
                "type": "resume_incompatible",
                "message": "Detected an incompatible checkpoint from an older reader runtime; restarting this analysis from scratch.",
                "details": {
                    "previous_job_id": str(normalized.get("job_id", "")),
                    "resume_compat_version": _record_resume_compat(normalized),
                    "current_resume_compat_version": get_reader_resume_compat_version(),
                },
            },
        )
        append_activity_event(
            _book_output_dir(resolved_book_id, root),
            {
                "type": "fresh_rerun_started",
                "message": "Started a fresh analysis run after discarding incompatible live runtime artifacts.",
                "details": {
                    "job_id": str(fresh_record.get("job_id", "")),
                },
            },
        )
    return fresh_record


def _resume_supported(record: dict) -> bool:
    """Return whether one job has enough context to resume."""
    upload_path = Path(str(record.get("upload_path", "") or ""))
    return upload_path.exists()


def _resume_job(record: dict, root: Path | None = None, *, automatic: bool) -> dict:
    """Resume one stopped parse/read subprocess in place."""
    normalized = _normalize_record(record)
    book_id = str(normalized.get("book_id", "") or "") or find_book_id_by_source(Path(str(normalized.get("upload_path", ""))), root=root)
    target_status = _resume_target_status(normalized, book_id, root)
    mechanism_key = _resume_mechanism_key(normalized, book_id=book_id, root=root)
    command = _job_command(normalized, continue_mode=True, mechanism_key=mechanism_key)
    log_path = job_log_file(str(normalized.get("job_id", "")), root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        banner = f"\n[{timestamp()}] resume {'auto' if automatic else 'manual'} -> {target_status}\n"
        log.write(banner.encode("utf-8"))
        process = subprocess.Popen(
            command,
            cwd=str(root or Path.cwd()),
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    if book_id:
        append_activity_event(
            _book_output_dir(book_id, root),
            {
                "type": "resume_detected",
                "message": ("检测到中断，已自动继续执行。" if automatic else "已继续执行，系统将从最近 checkpoint 恢复。"),
            },
        )

    return save_job(
        _job_record(
            job_id=str(normalized.get("job_id", "")),
            status=target_status,
            upload_path=Path(str(normalized.get("upload_path", ""))),
            job_kind=str(normalized.get("job_kind", "read")),
            mechanism_key=mechanism_key,
            language=str(normalized.get("language", "auto")),
            intent=normalized.get("intent"),
            resume_count=int(normalized.get("resume_count", 0)) + 1,
            auto_resume_count=int(normalized.get("auto_resume_count", 0) or 0) + (1 if automatic else 0),
            book_id=book_id,
            pid=process.pid,
            error=None,
            created_at=str(normalized.get("created_at", timestamp())),
        ),
        root,
    )


def _can_auto_resume(record: dict) -> bool:
    """Return whether one stalled job should be auto-resumed."""
    return _resume_supported(record) and int(record.get("auto_resume_count", 0) or 0) < AUTO_RESUME_LIMIT


def read_job_log_tail(job_id: str, root: Path | None = None, *, line_limit: int = 120) -> list[str]:
    """Return the trailing lines from one job log file."""
    log_path = job_log_file(job_id, root)
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-line_limit:]


def analysis_log_payload(book_id: str, root: Path | None = None, *, line_limit: int = 120) -> dict:
    """Return the latest analysis log snapshot for one book."""
    migrate_product_shadow_jobs(root)
    record = latest_job_for_book(book_id, root=root)
    if not record:
        return {
            "job_id": None,
            "available": False,
            "updated_at": None,
            "lines": [],
        }
    return {
        "job_id": str(record.get("job_id", "")),
        "available": True,
        "updated_at": str(record.get("updated_at", "")),
        "lines": read_job_log_tail(str(record.get("job_id", "")), root=root, line_limit=line_limit),
    }


def resume_job_for_book(book_id: str, root: Path | None = None) -> dict:
    """Resume the latest paused or failed job for one book."""
    migrate_product_shadow_jobs(root)
    record = latest_job_for_book(book_id, root=root)
    if record is None:
        raise FileNotFoundError(book_id)
    if _process_running(int(record.get("pid", 0) or 0)):
        return save_job({**record, "book_id": book_id}, root)
    run_state = _load_book_run_state(book_id, root)
    parse_state = _load_book_parse_state(book_id, root)
    if _is_dev_boot_mismatch(record):
        raise RuntimeError("This analysis belongs to an older development boot. Start a fresh run instead of resuming it.")
    if get_backend_run_mode() in {"demo", "prod"} and not _resume_compatible(
        record=record,
        run_state=run_state,
        parse_state=parse_state,
    ):
        return _fresh_rerun_after_incompatibility(record, book_id=book_id, root=root)
    if not _resume_supported(record):
        raise RuntimeError("No resumable checkpoint is available for this book.")
    return _resume_job({**record, "book_id": book_id}, root, automatic=False)


def recover_unfinished_jobs(root: Path | None = None) -> None:
    """Refresh unfinished jobs on startup so resumable work is relaunched."""
    migrate_product_shadow_jobs(root)
    for record in list_job_records(root, include_archived=True):
        if str(record.get("domain", "") or PRODUCT_RUNTIME_DOMAIN) != PRODUCT_RUNTIME_DOMAIN:
            continue
        status = str(record.get("status", "queued") or "queued")
        if status in ACTIVE_JOB_STATUSES:
            refresh_job(str(record.get("job_id", "")), root=root)
    for book_id, run_state, projection in iter_orphan_active_runs(root):
        stale_seconds = projection.stale_seconds or ACTIVE_RUNTIME_STALE_SECONDS
        error = _runtime_stalled_message(run_state, stale_seconds=stale_seconds)
        _pause_runtime_state(
            book_id,
            previous_status=str(run_state.get("stage", "deep_reading") or "deep_reading"),
            error=error,
            root=root,
            latest_job=projection.latest_job,
        )
        append_deduped_activity_event(
            _book_output_dir(book_id, root),
            {
                "type": "runtime_stalled",
                "message": error,
                **_activity_context(run_state),
                "details": {
                    "stale_seconds": int(round(stale_seconds)),
                    "source": "startup_orphan_reconcile",
                },
            },
        )
        append_deduped_activity_event(
            _book_output_dir(book_id, root),
            {
                "type": "job_paused_by_runtime_guard",
                "message": "Reader paused because an orphaned live runtime snapshot became stale.",
                **_activity_context(run_state),
                "details": {
                    "resume_available": effective_resume_available(
                        stage="paused",
                        run_state=_load_book_run_state(book_id, root),
                        parse_state=_load_book_parse_state(book_id, root),
                        runtime_shell=_load_book_runtime_shell(book_id, root),
                        latest_job=projection.latest_job,
                    ),
                    "status_reason": "runtime_stale",
                    "source": "startup_orphan_reconcile",
                },
            },
        )


def refresh_job(job_id: str, root: Path | None = None) -> dict:
    """Refresh one job record from process state and sequential artifacts."""
    record = load_job(job_id, root)
    upload_path = Path(str(record.get("upload_path", "")))
    pid = int(record["pid"]) if record.get("pid") else None
    running = _process_running(pid)
    book_id = str(record.get("book_id", "") or "") or find_book_id_by_source(upload_path, root=root)
    error = str(record.get("error", "") or "") or None
    status = str(record.get("status", "queued") or "queued")
    run_state: dict | None = None
    parse_state: dict | None = None
    run_mode = get_backend_run_mode()

    if book_id:
        run_state = _load_book_run_state(book_id, root) or {}
        parse_state = _load_book_parse_state(book_id, root)
        status, state_error = _status_from_run_state(run_state, running=running)
        error = state_error or error
    elif running:
        status = "parsing_structure"

    if status in ACTIVE_JOB_STATUSES and _is_dev_boot_mismatch(record):
        return _abandon_dev_run(record, book_id=book_id, run_state=run_state, root=root)

    if status in ACTIVE_JOB_STATUSES and run_mode in {"demo", "prod"} and not _resume_compatible(
        record=record,
        run_state=run_state,
        parse_state=parse_state,
    ):
        return _fresh_rerun_after_incompatibility(record, book_id=book_id, root=root)

    stale_seconds = _seconds_since((run_state or {}).get("updated_at"))
    runtime_stalled = (
        bool(running)
        and status in {"parsing_structure", "deep_reading", "ready"}
        and stale_seconds is not None
        and stale_seconds >= ACTIVE_RUNTIME_STALE_SECONDS
    )
    if runtime_stalled:
        running = False
        status = "paused" if book_id else "error"
        error = _runtime_stalled_message(run_state, stale_seconds=stale_seconds)
        if book_id:
            _pause_runtime_state(
                book_id,
                previous_status=_resume_target_status(record, book_id, root),
                error=error,
                root=root,
                latest_job={**record, "book_id": book_id, "status": "paused"},
            )
            append_deduped_activity_event(
                _book_output_dir(book_id, root),
                {
                    "type": "runtime_stalled",
                    "message": error,
                    **_activity_context(run_state),
                    "details": {
                        "stale_seconds": int(round(stale_seconds)),
                        "job_id": job_id,
                    },
                },
            )
            append_deduped_activity_event(
                _book_output_dir(book_id, root),
                {
                    "type": "job_paused_by_runtime_guard",
                    "message": "Reader paused because live runtime updates stopped arriving.",
                    **_activity_context(run_state),
                    "details": {
                        "job_id": job_id,
                        "resume_available": effective_resume_available(
                            stage="paused",
                            run_state=_load_book_run_state(book_id, root),
                            parse_state=_load_book_parse_state(book_id, root),
                            runtime_shell=_load_book_runtime_shell(book_id, root),
                            latest_job={**record, "book_id": book_id, "status": "paused"},
                        ),
                        "status_reason": "runtime_stale",
                    },
                },
            )
            if run_mode in {"demo", "prod"} and _can_auto_resume(record):
                return _resume_job({**record, "book_id": book_id}, root, automatic=True)

    if not running and status not in {"completed", "error", "ready", "paused"}:
        if _can_auto_resume(record):
            return _resume_job({**record, "book_id": book_id}, root, automatic=True)

        if book_id:
            status = "paused"
            error = error or "任务已停止，等待继续执行。"
            _pause_runtime_state(
                book_id,
                previous_status=_resume_target_status(record, book_id, root),
                error=error,
                root=root,
                latest_job={**record, "book_id": book_id, "status": "paused"},
            )
            append_deduped_activity_event(
                _book_output_dir(book_id, root),
                {
                    "type": "job_paused_by_runtime_guard",
                    "message": f"Reader paused because the background job stopped unexpectedly: {error}",
                    **_activity_context(run_state),
                    "details": {
                        "job_id": job_id,
                        "resume_available": effective_resume_available(
                            stage="paused",
                            run_state=_load_book_run_state(book_id, root),
                            parse_state=_load_book_parse_state(book_id, root),
                            runtime_shell=_load_book_runtime_shell(book_id, root),
                            latest_job={**record, "book_id": book_id, "status": "paused"},
                        ),
                        "status_reason": "runtime_interrupted",
                    },
                },
            )
        else:
            status = "error"
            error = error or "Job exited before producing readable artifacts."

    refreshed = _job_record(
        job_id=job_id,
        status=status,
        upload_path=upload_path,
        job_kind=str(record.get("job_kind", "read")),
        mechanism_key=_resume_mechanism_key(record, book_id=book_id, root=root) if book_id else _normalized_mechanism_key(record.get("mechanism_key")),
        language=str(record.get("language", "auto")),
        intent=record.get("intent"),
        resume_count=int(record.get("resume_count", 0) or 0),
        auto_resume_count=int(record.get("auto_resume_count", 0) or 0),
        book_id=book_id,
        pid=pid if running else None,
        error=error,
        created_at=str(record.get("created_at", timestamp())),
    )
    saved = save_job(refreshed, root)
    if book_id and status in {"completed", "error"}:
        _archive_run_artifacts(book_id=book_id, job=saved, root=root)
    return saved


def _archive_run_artifacts(*, book_id: str, job: dict, root: Path | None = None) -> None:
    """Mirror terminal job artifacts into the book-scoped history tree."""
    output_dir = (root or Path.cwd()) / "output" / book_id
    summary_payload = {
        "job_id": str(job.get("job_id", "")),
        "status": str(job.get("status", "")),
        "book_id": book_id,
        "created_at": str(job.get("created_at", "")),
        "updated_at": str(job.get("updated_at", "")),
        "error": job.get("error"),
    }
    save_job_json(run_history_summary_file(output_dir, str(job.get("job_id", ""))), summary_payload)
    save_job_json(run_history_job_file(output_dir, str(job.get("job_id", ""))), job)

    activity_path = existing_activity_file(output_dir)
    history_trace_path = run_history_trace_file(output_dir, str(job.get("job_id", "")))
    history_trace_path.parent.mkdir(parents=True, exist_ok=True)
    if activity_path.exists():
        shutil.copy2(activity_path, history_trace_path)
    else:
        history_trace_path.write_text("", encoding="utf-8")

    source_log = job_log_file(str(job.get("job_id", "")), root)
    history_log = run_history_job_log_file(output_dir, str(job.get("job_id", "")))
    history_log.parent.mkdir(parents=True, exist_ok=True)
    if source_log.exists():
        shutil.copy2(source_log, history_log)
    else:
        history_log.write_text("", encoding="utf-8")
