"""Background job helpers for uploaded sequential deep-read runs."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from .catalog import find_book_id_by_source, get_book, source_asset_path
from .storage import (
    job_file,
    job_log_file,
    jobs_dir,
    load_json as load_job_json,
    save_json as save_job_json,
    timestamp,
    upload_file,
)
from src.iterator_reader.frontend_artifacts import append_activity_event
from src.iterator_reader.storage import (
    book_id_from_output_dir,
    existing_activity_file,
    existing_parse_state_file,
    existing_run_state_file,
    load_json as load_runtime_json,
    parse_state_file,
    run_history_job_file,
    run_history_job_log_file,
    run_history_summary_file,
    run_history_trace_file,
)


AUTO_RESUME_LIMIT = 3
ACTIVE_JOB_STATUSES = {"queued", "parsing_structure", "deep_reading", "chapter_note_generation"}
TERMINAL_JOB_STATUSES = {"completed", "error"}


def _job_record(
    *,
    job_id: str,
    status: str,
    upload_path: Path,
    job_kind: str,
    language: str = "auto",
    intent: str | None = None,
    resume_count: int = 0,
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
        "upload_path": str(upload_path),
        "book_id": book_id,
        "language": language,
        "intent": intent,
        "resume_count": int(resume_count),
        "pid": pid,
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
        "language": str(record.get("language", "auto") or "auto"),
        "intent": str(record.get("intent", "") or "") or None,
        "resume_count": int(record.get("resume_count", 0) or 0),
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
    return normalized


def load_job(job_id: str, root: Path | None = None) -> dict:
    """Load one job record."""
    return _normalize_record(load_job_json(job_file(job_id, root)))


def _job_command(record: dict, *, continue_mode: bool) -> list[str]:
    """Build the CLI command for one persisted job record."""
    upload_path = Path(str(record.get("upload_path", "")))
    language = str(record.get("language", "auto") or "auto")
    intent = str(record.get("intent", "") or "") or None
    job_kind = str(record.get("job_kind", "read") or "read")

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
    return command


def _launch_subprocess_job(
    *,
    upload_path: Path,
    command: list[str],
    job_kind: str,
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
    record = _job_record(
        job_id=resolved_job_id,
        status=initial_status,
        upload_path=upload_path,
        job_kind=job_kind,
        language=language,
        intent=intent,
        book_id=book_id,
        resume_count=resume_count,
    )
    save_job(record, root)

    log_path = job_log_file(resolved_job_id, root)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            command,
            cwd=str(root or Path.cwd()),
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    return save_job(
        _job_record(
            job_id=resolved_job_id,
            status=initial_status,
            upload_path=upload_path,
            job_kind=job_kind,
            language=language,
            intent=intent,
            book_id=book_id,
            resume_count=resume_count,
            pid=process.pid,
            created_at=str(record["created_at"]),
        ),
        root,
    )


def launch_sequential_job(
    upload_path: Path,
    *,
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
    if intent:
        command.extend(["--intent", intent])

    return _launch_subprocess_job(
        upload_path=upload_path,
        command=command,
        job_kind="read",
        language=language,
        intent=intent,
        root=root,
        initial_status="queued",
        book_id=book_id,
    )


def launch_parse_job(
    upload_path: Path,
    *,
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
    return _launch_subprocess_job(
        upload_path=upload_path,
        command=command,
        job_kind="parse",
        language=language,
        root=root,
        initial_status="queued",
        book_id=book_id,
    )


def provision_uploaded_book(
    upload_path: Path,
    *,
    language: str = "auto",
    root: Path | None = None,
) -> str | None:
    """Create a minimal book shell so uploads can resolve a book id immediately."""
    from src.iterator_reader.frontend_artifacts import build_run_state, write_book_manifest, write_run_state
    from src.iterator_reader.language import detect_book_language, resolve_output_language
    from src.iterator_reader.parse import _extract_epub_cover, extract_book_metadata
    from src.iterator_reader.storage import ensure_output_dir, ensure_source_asset, existing_book_manifest_file, resolve_output_dir

    try:
        title, author = extract_book_metadata(upload_path)
        book_language = detect_book_language(upload_path, sample_text="")
        output_language = resolve_output_language(language, book_language)
        output_dir = resolve_output_dir(upload_path, title, book_language, output_language)
        book_id = book_id_from_output_dir(output_dir)
        manifest_path = existing_book_manifest_file(output_dir)
        if manifest_path.exists():
            return book_id

        ensure_output_dir(output_dir)
        ensure_source_asset(upload_path, output_dir)
        if upload_path.suffix.lower() == ".epub":
            _extract_epub_cover(upload_path, output_dir)

        structure = {
            "book": title,
            "author": author,
            "book_language": book_language,
            "output_language": output_language,
            "source_file": str(upload_path),
            "output_dir": str(output_dir),
            "chapters": [],
        }
        write_book_manifest(output_dir, structure)
        write_run_state(
            output_dir,
            build_run_state(
                structure,
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


def launch_book_analysis_job(
    book_id: str,
    *,
    language: str = "auto",
    intent: str | None = None,
    root: Path | None = None,
) -> dict:
    """Start sequential analysis for an existing uploaded book."""
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
    if intent:
        command.extend(["--intent", intent])

    return _launch_subprocess_job(
        upload_path=source_path,
        command=command,
        job_kind="read",
        language=language,
        intent=intent,
        root=root,
        job_id=uuid.uuid4().hex[:12],
        initial_status="queued",
        book_id=book_id,
    )


def _book_output_dir(book_id: str, root: Path | None = None) -> Path:
    """Resolve one book output directory."""
    return (root or Path.cwd()) / "output" / book_id


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


def _pause_runtime_state(book_id: str, *, previous_status: str, error: str, root: Path | None = None) -> None:
    """Write paused status into the book runtime files."""
    output_dir = _book_output_dir(book_id, root)
    run_state_path = existing_run_state_file(output_dir)
    if run_state_path.exists():
        payload = load_runtime_json(run_state_path)
        payload["stage"] = "paused"
        payload["error"] = error
        payload["resume_available"] = True
        payload["updated_at"] = timestamp()
        payload["current_phase_step"] = "等待继续执行"
        payload["last_checkpoint_at"] = payload.get("last_checkpoint_at") or timestamp()
        save_job_json(run_state_path, payload)

    parse_state_path = existing_parse_state_file(output_dir)
    if previous_status == "parsing_structure" and parse_state_path.exists():
        payload = load_runtime_json(parse_state_path)
        payload["status"] = "paused"
        payload["error"] = error
        payload["resume_available"] = True
        payload["updated_at"] = timestamp()
        save_job_json(parse_state_path, payload)


def _resume_supported(record: dict) -> bool:
    """Return whether one job has enough context to resume."""
    upload_path = Path(str(record.get("upload_path", "") or ""))
    return upload_path.exists()


def _resume_job(record: dict, root: Path | None = None, *, automatic: bool) -> dict:
    """Resume one stopped parse/read subprocess in place."""
    normalized = _normalize_record(record)
    book_id = str(normalized.get("book_id", "") or "") or find_book_id_by_source(Path(str(normalized.get("upload_path", ""))), root=root)
    target_status = _resume_target_status(normalized, book_id, root)
    command = _job_command(normalized, continue_mode=True)
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
            language=str(normalized.get("language", "auto")),
            intent=normalized.get("intent"),
            resume_count=int(normalized.get("resume_count", 0)) + 1,
            book_id=book_id,
            pid=process.pid,
            error=None,
            created_at=str(normalized.get("created_at", timestamp())),
        ),
        root,
    )


def _can_auto_resume(record: dict) -> bool:
    """Return whether one stalled job should be auto-resumed."""
    return _resume_supported(record) and int(record.get("resume_count", 0) or 0) < AUTO_RESUME_LIMIT


def latest_job_for_book(book_id: str, root: Path | None = None) -> dict | None:
    """Return the latest persisted job for one book."""
    matches: list[dict] = []
    for path in sorted(jobs_dir(root).glob("*.json")):
        try:
            record = _normalize_record(load_job_json(path))
        except (FileNotFoundError, OSError, ValueError):
            continue
        if str(record.get("book_id", "") or "") != book_id:
            continue
        matches.append(record)
    if not matches:
        return None
    matches.sort(key=lambda item: (str(item.get("updated_at", "")), str(item.get("created_at", "")), str(item.get("job_id", ""))), reverse=True)
    return matches[0]


def read_job_log_tail(job_id: str, root: Path | None = None, *, line_limit: int = 120) -> list[str]:
    """Return the trailing lines from one job log file."""
    log_path = job_log_file(job_id, root)
    if not log_path.exists():
        return []
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-line_limit:]


def analysis_log_payload(book_id: str, root: Path | None = None, *, line_limit: int = 120) -> dict:
    """Return the latest analysis log snapshot for one book."""
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
    record = latest_job_for_book(book_id, root=root)
    if record is None:
        raise FileNotFoundError(book_id)
    if _process_running(int(record.get("pid", 0) or 0)):
        return save_job({**record, "book_id": book_id}, root)
    if not _resume_supported(record):
        raise RuntimeError("No resumable checkpoint is available for this book.")
    return _resume_job({**record, "book_id": book_id}, root, automatic=False)


def recover_unfinished_jobs(root: Path | None = None) -> None:
    """Refresh unfinished jobs on startup so resumable work is relaunched."""
    for path in sorted(jobs_dir(root).glob("*.json")):
        try:
            record = _normalize_record(load_job_json(path))
        except (FileNotFoundError, OSError, ValueError):
            continue
        status = str(record.get("status", "queued") or "queued")
        if status in ACTIVE_JOB_STATUSES:
            refresh_job(str(record.get("job_id", "")), root=root)


def refresh_job(job_id: str, root: Path | None = None) -> dict:
    """Refresh one job record from process state and sequential artifacts."""
    record = load_job(job_id, root)
    upload_path = Path(str(record.get("upload_path", "")))
    pid = int(record["pid"]) if record.get("pid") else None
    running = _process_running(pid)
    book_id = str(record.get("book_id", "") or "") or find_book_id_by_source(upload_path, root=root)
    error = str(record.get("error", "") or "") or None
    status = str(record.get("status", "queued") or "queued")

    if book_id:
        book = get_book(book_id, root=root)
        run_state = book.get("run_state") or {}
        status, state_error = _status_from_run_state(run_state, running=running)
        error = state_error or error
    elif running:
        status = "parsing_structure"

    if not running and status not in {"completed", "error", "ready", "paused"}:
        if _can_auto_resume(record):
            return _resume_job({**record, "book_id": book_id}, root, automatic=True)

        if book_id:
            status = "paused"
            error = error or "任务已停止，等待继续执行。"
            _pause_runtime_state(book_id, previous_status=_resume_target_status(record, book_id, root), error=error, root=root)
        else:
            status = "error"
            error = error or "Job exited before producing readable artifacts."

    refreshed = _job_record(
        job_id=job_id,
        status=status,
        upload_path=upload_path,
        job_kind=str(record.get("job_kind", "read")),
        language=str(record.get("language", "auto")),
        intent=record.get("intent"),
        resume_count=int(record.get("resume_count", 0) or 0),
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
