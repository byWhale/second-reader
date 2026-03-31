"""Unified durable registry for product and offline long-running jobs."""

from __future__ import annotations

import json
import os
import secrets
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


REGISTRY_VERSION = 2
ACTIVE_JOBS_FILE = "active_jobs.json"
ACTIVE_JOBS_SUMMARY_FILE = "active_jobs.md"
HISTORY_JOBS_FILE = "history_jobs.jsonl"
JOBS_DIR_NAME = "jobs"
PRODUCT_SHADOW_JOBS_DIR = "jobs"

PRODUCT_RUNTIME_DOMAIN = "product_runtime"
OFFLINE_BACKGROUND_DOMAIN = "offline_background"
VALID_JOB_STATUSES = {
    "registered",
    "queued",
    "running",
    "parsing_structure",
    "ready",
    "deep_reading",
    "chapter_note_generation",
    "paused",
    "completed",
    "failed",
    "error",
    "abandoned",
}
TERMINAL_JOB_STATUSES = {"ready", "completed", "failed", "error", "abandoned"}


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _state_dir(root: Path | None = None) -> Path:
    return (root or Path.cwd()) / "state"


def job_registry_dir(root: Path | None = None) -> Path:
    return _state_dir(root) / "job_registry"


def job_records_dir(root: Path | None = None) -> Path:
    return job_registry_dir(root) / JOBS_DIR_NAME


def job_record_file(job_id: str, root: Path | None = None) -> Path:
    return job_records_dir(root) / f"{job_id}.json"


def product_shadow_jobs_dir(root: Path | None = None) -> Path:
    return _state_dir(root) / PRODUCT_SHADOW_JOBS_DIR


def product_shadow_job_file(job_id: str, root: Path | None = None) -> Path:
    return product_shadow_jobs_dir(root) / f"{job_id}.json"


def active_jobs_file(root: Path | None = None) -> Path:
    return job_registry_dir(root) / ACTIVE_JOBS_FILE


def active_jobs_summary_file(root: Path | None = None) -> Path:
    return job_registry_dir(root) / ACTIVE_JOBS_SUMMARY_FILE


def history_jobs_file(root: Path | None = None) -> Path:
    return job_registry_dir(root) / HISTORY_JOBS_FILE


def process_is_alive(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def generate_job_id(prefix: str = "bgjob") -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}"


def _empty_registry() -> dict[str, Any]:
    now = _timestamp()
    return {"version": REGISTRY_VERSION, "updated_at": now, "jobs": []}


def _ensure_registry_dir(root: Path | None = None) -> Path:
    path = job_registry_dir(root)
    path.mkdir(parents=True, exist_ok=True)
    job_records_dir(root).mkdir(parents=True, exist_ok=True)
    return path


def _dedupe_strings(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in items:
        value = str(raw).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _normalize_optional_path(value: str | Path | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_optional_text(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _normalize_status(value: str | None, *, default: str) -> str:
    candidate = str(value or default).strip().lower()
    if candidate not in VALID_JOB_STATUSES:
        raise ValueError(f"Unsupported background job status: {candidate}")
    return candidate


def _normalize_bool(value: object, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _load_json_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _normalize_job_record(record: dict[str, Any], *, create: bool = False) -> dict[str, Any]:
    normalized = dict(record)
    now = _timestamp()
    normalized["job_id"] = str(normalized.get("job_id", "")).strip()
    if not normalized["job_id"]:
        raise ValueError("Canonical job record requires job_id")

    existing_domain = str(normalized.get("domain", "") or "").strip()
    if not existing_domain:
        existing_domain = PRODUCT_RUNTIME_DOMAIN if str(normalized.get("upload_path", "")).strip() else OFFLINE_BACKGROUND_DOMAIN
    normalized["domain"] = existing_domain
    normalized["job_kind"] = str(normalized.get("job_kind", "") or "").strip()
    normalized["task_ref"] = _normalize_optional_text(normalized.get("task_ref"))
    normalized["lane"] = _normalize_optional_text(normalized.get("lane"))
    normalized["purpose"] = _normalize_optional_text(normalized.get("purpose"))
    normalized["mechanism_key"] = _normalize_optional_text(normalized.get("mechanism_key")) or None
    normalized["book_id"] = _normalize_optional_text(normalized.get("book_id")) or None
    normalized["status"] = _normalize_status(
        normalized.get("status"),
        default="queued" if normalized["domain"] == PRODUCT_RUNTIME_DOMAIN else "registered",
    )
    normalized["phase"] = _normalize_optional_text(normalized.get("phase"))
    pid = normalized.get("pid")
    normalized["pid"] = int(pid) if pid not in {"", None} else None
    exit_code = normalized.get("exit_code")
    normalized["exit_code"] = int(exit_code) if exit_code not in {"", None} else None
    normalized["started_at"] = _normalize_optional_text(normalized.get("started_at"))
    normalized["ended_at"] = _normalize_optional_text(normalized.get("ended_at"))
    normalized["error"] = _normalize_optional_text(normalized.get("error")) or None
    normalized["run_dir"] = _normalize_optional_path(normalized.get("run_dir"))
    normalized["status_file"] = _normalize_optional_path(normalized.get("status_file"))
    normalized["log_file"] = _normalize_optional_path(normalized.get("log_file"))
    normalized["expected_outputs"] = _dedupe_strings(normalized.get("expected_outputs", []))
    normalized["check_command"] = _normalize_optional_text(normalized.get("check_command"))
    normalized["latest_observation"] = (
        dict(normalized.get("latest_observation", {})) if isinstance(normalized.get("latest_observation"), dict) else {}
    )
    normalized["show_in_active_views"] = _normalize_bool(
        normalized.get("show_in_active_views"),
        default=normalized["domain"] != PRODUCT_RUNTIME_DOMAIN,
    )
    normalized["command"] = _normalize_optional_text(normalized.get("command"))
    normalized["cwd"] = _normalize_optional_path(normalized.get("cwd"))
    normalized["next_check_hint"] = _normalize_optional_text(normalized.get("next_check_hint"))
    normalized["decision_if_success"] = _normalize_optional_text(normalized.get("decision_if_success"))
    normalized["decision_if_failure"] = _normalize_optional_text(normalized.get("decision_if_failure"))
    normalized["notes"] = _normalize_optional_text(normalized.get("notes"))
    normalized["archived_at"] = _normalize_optional_text(normalized.get("archived_at"))
    normalized["archive_reason"] = _normalize_optional_text(normalized.get("archive_reason"))
    normalized["created_at"] = _normalize_optional_text(normalized.get("created_at")) or (now if create else now)
    normalized["updated_at"] = now
    return normalized


def save_job_record(record: dict[str, Any], *, root: Path | None = None, sync_views: bool = True) -> dict[str, Any]:
    _ensure_registry_dir(root)
    target = job_record_file(str(record.get("job_id", "")).strip(), root)
    existing = _load_json_payload(target) if target.exists() else {}
    merged = {**existing, **record}
    normalized = _normalize_job_record(merged, create=not target.exists())
    target.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    if sync_views:
        sync_registry_views(root)
    return normalized


def _import_legacy_active_jobs(root: Path | None = None) -> None:
    path = active_jobs_file(root)
    if not path.exists():
        return
    payload = _load_json_payload(path)
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        return
    for item in jobs:
        if not isinstance(item, dict):
            continue
        job_id = str(item.get("job_id", "")).strip()
        if not job_id or job_record_file(job_id, root).exists():
            continue
        migrated = {
            **item,
            "domain": OFFLINE_BACKGROUND_DOMAIN,
            "show_in_active_views": True,
        }
        save_job_record(migrated, root=root, sync_views=False)


def import_product_shadow_job(job_id: str, *, root: Path | None = None, sync_views: bool = False) -> dict[str, Any]:
    shadow_path = product_shadow_job_file(job_id, root)
    if not shadow_path.exists():
        raise FileNotFoundError(shadow_path)
    payload = _load_json_payload(shadow_path)
    payload.setdefault("job_id", job_id)
    payload.setdefault("domain", PRODUCT_RUNTIME_DOMAIN)
    payload.setdefault("lane", "product_runtime")
    payload.setdefault("show_in_active_views", False)
    payload.setdefault("phase", str(payload.get("status", "")))
    payload.setdefault("log_file", str((root or Path.cwd()) / "state" / "jobs" / f"{job_id}.log"))
    book_id = str(payload.get("book_id", "") or "").strip()
    if book_id:
        payload.setdefault("run_dir", str((root or Path.cwd()) / "output" / book_id))
    return save_job_record(payload, root=root, sync_views=sync_views)


def migrate_product_shadow_jobs(root: Path | None = None) -> int:
    migrated = 0
    shadow_dir = product_shadow_jobs_dir(root)
    if not shadow_dir.exists():
        return migrated
    for path in shadow_dir.glob("*.json"):
        job_id = path.stem
        if job_record_file(job_id, root).exists():
            continue
        import_product_shadow_job(job_id, root=root, sync_views=False)
        migrated += 1
    if migrated:
        sync_registry_views(root)
    return migrated


def load_job_record(job_id: str, root: Path | None = None) -> dict[str, Any]:
    _ensure_registry_dir(root)
    target = job_record_file(job_id, root)
    if target.exists():
        return _normalize_job_record(_load_json_payload(target), create=False)

    _import_legacy_active_jobs(root)
    if target.exists():
        return _normalize_job_record(_load_json_payload(target), create=False)

    if product_shadow_job_file(job_id, root).exists():
        return import_product_shadow_job(job_id, root=root, sync_views=False)

    raise FileNotFoundError(target)


def get_job_record(job_id: str, root: Path | None = None) -> dict[str, Any] | None:
    try:
        return load_job_record(job_id, root=root)
    except FileNotFoundError:
        return None


def list_job_records(root: Path | None = None, *, include_archived: bool = False) -> list[dict[str, Any]]:
    _ensure_registry_dir(root)
    _import_legacy_active_jobs(root)
    records: list[dict[str, Any]] = []
    for path in sorted(job_records_dir(root).glob("*.json")):
        try:
            record = _normalize_job_record(_load_json_payload(path), create=False)
        except ValueError:
            continue
        if not include_archived and str(record.get("archived_at", "")).strip():
            continue
        records.append(record)
    records.sort(key=lambda item: (str(item.get("created_at", "")), str(item.get("updated_at", "")), str(item.get("job_id", ""))))
    return records


def _should_show_in_active_views(record: dict[str, Any]) -> bool:
    if str(record.get("archived_at", "")).strip():
        return False
    if not bool(record.get("show_in_active_views", False)):
        return False
    status = str(record.get("status", "registered") or "registered").strip().lower()
    return status not in TERMINAL_JOB_STATUSES


def sync_registry_views(root: Path | None = None) -> dict[str, Any]:
    _ensure_registry_dir(root)
    jobs = [dict(item) for item in list_job_records(root, include_archived=False) if _should_show_in_active_views(item)]
    payload = {"version": REGISTRY_VERSION, "updated_at": _timestamp(), "jobs": jobs}
    active_jobs_file(root).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_active_jobs_summary(root, jobs)
    return payload


def load_active_registry(root: Path | None = None) -> dict[str, Any]:
    return sync_registry_views(root)


def save_active_registry(payload: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    if not isinstance(jobs, list):
        raise ValueError("Expected jobs list in active registry payload")
    for item in jobs:
        if not isinstance(item, dict):
            continue
        migrated = {
            **item,
            "domain": item.get("domain") or OFFLINE_BACKGROUND_DOMAIN,
            "show_in_active_views": True,
        }
        save_job_record(migrated, root=root, sync_views=False)
    return sync_registry_views(root)


def list_active_jobs(root: Path | None = None) -> list[dict[str, Any]]:
    return load_active_registry(root).get("jobs", [])


def get_active_job(job_id: str, root: Path | None = None) -> dict[str, Any] | None:
    record = get_job_record(job_id, root=root)
    if record is None or not _should_show_in_active_views(record):
        return None
    return record


def _merge_background_job_fields(existing: dict[str, Any] | None, updates: dict[str, Any], *, create: bool) -> dict[str, Any]:
    record = dict(existing or {})
    now = _timestamp()
    if create:
        record["created_at"] = now
    elif "created_at" not in record:
        record["created_at"] = now

    for key, value in updates.items():
        if value is None:
            continue
        if key == "expected_outputs":
            record[key] = _dedupe_strings(value if isinstance(value, list) else [str(value)])
        elif key in {"pid", "exit_code"}:
            record[key] = int(value) if value not in {"", None} else None
        elif key == "latest_observation":
            record[key] = value if isinstance(value, dict) else {}
        else:
            record[key] = value

    required = ("job_id", "task_ref", "lane", "purpose", "command", "cwd")
    missing = [field for field in required if not str(record.get(field, "")).strip()]
    if missing:
        raise ValueError(f"Missing required background job fields: {', '.join(missing)}")
    return record


def upsert_background_job(
    *,
    job_id: str | None = None,
    root: Path | None = None,
    task_ref: str | None = None,
    lane: str | None = None,
    purpose: str | None = None,
    command: str | None = None,
    cwd: str | Path | None = None,
    pid: int | None = None,
    run_dir: str | Path | None = None,
    status_file: str | Path | None = None,
    log_file: str | Path | None = None,
    expected_outputs: list[str] | None = None,
    check_command: str | None = None,
    next_check_hint: str | None = None,
    decision_if_success: str | None = None,
    decision_if_failure: str | None = None,
    status: str | None = None,
    notes: str | None = None,
    phase: str | None = None,
    exit_code: int | None = None,
    started_at: str | None = None,
    ended_at: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    target_id = str(job_id).strip() if job_id else generate_job_id()
    existing = get_job_record(target_id, root=root)
    updates = {
        "job_id": target_id,
        "domain": OFFLINE_BACKGROUND_DOMAIN,
        "show_in_active_views": True,
        "task_ref": task_ref if task_ref is not None else (existing or {}).get("task_ref"),
        "lane": lane if lane is not None else (existing or {}).get("lane"),
        "purpose": purpose if purpose is not None else (existing or {}).get("purpose"),
        "command": command if command is not None else (existing or {}).get("command"),
        "cwd": str(cwd) if cwd is not None else (existing or {}).get("cwd"),
        "pid": pid if pid is not None else (existing or {}).get("pid"),
        "run_dir": str(run_dir) if run_dir is not None else (existing or {}).get("run_dir"),
        "status_file": str(status_file) if status_file is not None else (existing or {}).get("status_file"),
        "log_file": str(log_file) if log_file is not None else (existing or {}).get("log_file"),
        "expected_outputs": expected_outputs if expected_outputs is not None else (existing or {}).get("expected_outputs", []),
        "check_command": check_command if check_command is not None else (existing or {}).get("check_command"),
        "next_check_hint": next_check_hint if next_check_hint is not None else (existing or {}).get("next_check_hint"),
        "decision_if_success": decision_if_success if decision_if_success is not None else (existing or {}).get("decision_if_success"),
        "decision_if_failure": decision_if_failure if decision_if_failure is not None else (existing or {}).get("decision_if_failure"),
        "status": status if status is not None else (existing or {}).get("status", "registered"),
        "notes": notes if notes is not None else (existing or {}).get("notes"),
        "phase": phase if phase is not None else (existing or {}).get("phase"),
        "exit_code": exit_code if exit_code is not None else (existing or {}).get("exit_code"),
        "started_at": started_at if started_at is not None else (existing or {}).get("started_at"),
        "ended_at": ended_at if ended_at is not None else (existing or {}).get("ended_at"),
        "error": error if error is not None else (existing or {}).get("error"),
        "latest_observation": (existing or {}).get("latest_observation", {}),
    }
    merged = _merge_background_job_fields(existing, updates, create=existing is None)
    return save_job_record(merged, root=root)


def append_history_entry(record: dict[str, Any], root: Path | None = None) -> None:
    _ensure_registry_dir(root)
    entry = {"archived_at": _timestamp(), "job": record}
    with history_jobs_file(root).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def archive_background_job(job_id: str, *, root: Path | None = None, archive_reason: str | None = None) -> dict[str, Any]:
    record = load_job_record(job_id, root=root)
    archived = {
        **record,
        "archived_at": _timestamp(),
        "archive_reason": _normalize_optional_text(archive_reason),
    }
    save_job_record(archived, root=root, sync_views=False)
    append_history_entry(archived, root)
    sync_registry_views(root)
    return archived


def _run_check_command(command: str, cwd: str) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=cwd or None,
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    return {
        "exit_code": int(completed.returncode),
        "stdout": stdout[-4000:],
        "stderr": stderr[-4000:],
        "ok": completed.returncode == 0,
    }


def _runtime_artifact_status(record: dict[str, Any], *, root: Path | None = None) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    book_id = str(record.get("book_id", "") or "").strip()
    if not book_id:
        return "", {}, []
    try:
        from src.iterator_reader.storage import existing_parse_state_file, existing_run_state_file
    except Exception:
        return "", {}, []

    output_dir = (root or Path.cwd()) / "output" / book_id
    observations: list[dict[str, Any]] = []

    run_state_path = existing_run_state_file(output_dir)
    if run_state_path.exists():
        payload = _load_json_payload(run_state_path)
        observations.append({"path": str(run_state_path), "exists": True})
        stage = str(payload.get("stage", "")).strip().lower()
        return stage, payload, observations
    observations.append({"path": str(run_state_path), "exists": False})

    parse_state_path = existing_parse_state_file(output_dir)
    if parse_state_path.exists():
        payload = _load_json_payload(parse_state_path)
        observations.append({"path": str(parse_state_path), "exists": True})
        stage = str(payload.get("status", "")).strip().lower()
        return stage, payload, observations
    observations.append({"path": str(parse_state_path), "exists": False})
    return "", {}, observations


def _success_from_outputs_or_check(expected_output_entries: list[dict[str, Any]], check_result: dict[str, Any]) -> bool:
    outputs_present = bool(expected_output_entries) and all(bool(item.get("exists")) for item in expected_output_entries)
    if outputs_present:
        return True
    if check_result:
        return bool(check_result.get("ok"))
    return False


def _failure_from_outputs_or_check(expected_output_entries: list[dict[str, Any]], check_result: dict[str, Any]) -> bool:
    outputs_present = bool(expected_output_entries) and all(bool(item.get("exists")) for item in expected_output_entries)
    if check_result and not bool(check_result.get("ok")) and not outputs_present:
        return True
    return False


def _product_runtime_status_to_registry(status: str) -> str:
    normalized = str(status or "").strip().lower()
    if normalized in {"completed", "ready", "paused", "deep_reading", "parsing_structure", "chapter_note_generation", "queued", "error"}:
        return normalized
    return ""


def inspect_background_job(record: dict[str, Any], *, root: Path | None = None, run_check_command: bool = False) -> dict[str, Any]:
    pid = record.get("pid")
    pid_alive = process_is_alive(pid if isinstance(pid, int) else None)

    status_file_path = Path(record["status_file"]) if str(record.get("status_file", "")).strip() else None
    status_payload: dict[str, Any] = {}
    status_file_status = ""
    if status_file_path and status_file_path.exists():
        status_payload = _load_json_payload(status_file_path)
        status_file_status = str(status_payload.get("status", "")).strip().lower()

    runtime_status, runtime_payload, runtime_paths = _runtime_artifact_status(record, root=root)
    runtime_status = _product_runtime_status_to_registry(runtime_status)

    expected_output_entries: list[dict[str, Any]] = []
    for path_text in record.get("expected_outputs", []):
        output_path = Path(path_text)
        expected_output_entries.append({"path": str(output_path), "exists": output_path.exists()})

    check_result: dict[str, Any] = {}
    if run_check_command and str(record.get("check_command", "")).strip():
        check_result = _run_check_command(str(record["check_command"]), str(record.get("cwd", "")))

    explicit_status = str(record.get("status", "registered")).strip().lower()
    domain = str(record.get("domain", OFFLINE_BACKGROUND_DOMAIN)).strip() or OFFLINE_BACKGROUND_DOMAIN
    exit_code = record.get("exit_code")
    success_evidence = _success_from_outputs_or_check(expected_output_entries, check_result)
    failure_evidence = _failure_from_outputs_or_check(expected_output_entries, check_result)

    if explicit_status in TERMINAL_JOB_STATUSES:
        effective_status = explicit_status
    elif status_file_status in {"completed", "ready"}:
        effective_status = status_file_status
    elif status_file_status in {"failed", "error", "incomplete"}:
        effective_status = "error" if status_file_status == "error" else "failed"
    elif runtime_status:
        effective_status = runtime_status
    elif pid_alive:
        if explicit_status in {"queued", "parsing_structure", "deep_reading", "chapter_note_generation", "paused"}:
            effective_status = explicit_status
        else:
            effective_status = "running"
    elif isinstance(exit_code, int):
        if exit_code != 0:
            effective_status = "error" if domain == PRODUCT_RUNTIME_DOMAIN else "failed"
        elif failure_evidence:
            effective_status = "error" if domain == PRODUCT_RUNTIME_DOMAIN else "failed"
        else:
            effective_status = "completed"
    elif success_evidence:
        effective_status = "completed"
    elif failure_evidence:
        effective_status = "error" if domain == PRODUCT_RUNTIME_DOMAIN else "failed"
    elif explicit_status == "registered":
        effective_status = "registered"
    else:
        effective_status = "abandoned"

    return {
        "job_id": str(record.get("job_id", "")),
        "status": effective_status,
        "pid_alive": pid_alive,
        "status_file_exists": bool(status_file_path and status_file_path.exists()),
        "status_file_status": status_file_status,
        "status_payload": status_payload,
        "runtime_status": runtime_status,
        "runtime_payload": runtime_payload,
        "runtime_paths": runtime_paths,
        "expected_outputs": expected_output_entries,
        "check_result": check_result,
        "checked_at": _timestamp(),
    }


def refresh_background_jobs(
    *,
    root: Path | None = None,
    job_ids: Iterable[str] | None = None,
    run_check_commands: bool = False,
    archive_terminal: bool = False,
) -> list[dict[str, Any]]:
    selected_ids = {str(job_id) for job_id in job_ids} if job_ids else None
    refreshed: list[dict[str, Any]] = []

    if selected_ids is not None:
        records = [record for record in (get_job_record(job_id, root=root) for job_id in selected_ids) if record is not None]
    else:
        records = [record for record in list_job_records(root, include_archived=False) if _should_show_in_active_views(record)]

    for item in records:
        observation = inspect_background_job(item, root=root, run_check_command=run_check_commands)
        updated = dict(item)
        updated["status"] = observation["status"]
        updated["last_checked_at"] = observation["checked_at"]
        updated["latest_observation"] = observation
        if observation["status"] == "running" and not str(updated.get("started_at", "")).strip():
            updated["started_at"] = observation["checked_at"]
        if observation["status"] in TERMINAL_JOB_STATUSES and not str(updated.get("ended_at", "")).strip():
            updated["ended_at"] = observation["checked_at"]
        if observation["status"] in {"failed", "error"} and not str(updated.get("error", "")).strip():
            check_result = observation.get("check_result", {})
            updated["error"] = str(check_result.get("stderr", "") or "") or "Job failed."
        refreshed.append(save_job_record(updated, root=root, sync_views=False))
        if archive_terminal and observation["status"] in TERMINAL_JOB_STATUSES:
            archive_background_job(str(updated.get("job_id", "")), root=root, archive_reason="archived_by_checker")

    sync_registry_views(root)
    return refreshed


def render_active_jobs_markdown(jobs: list[dict[str, Any]]) -> str:
    lines = ["# Active Background Jobs", "", f"Last updated: `{_timestamp()}`", ""]
    if not jobs:
        lines.append("- No active background jobs are currently registered.")
        return "\n".join(lines) + "\n"

    for job in jobs:
        observation = job.get("latest_observation", {}) if isinstance(job.get("latest_observation"), dict) else {}
        lines.append(f"## `{job.get('job_id', '')}`")
        lines.append(f"- Status: `{job.get('status', '')}`")
        if str(job.get("domain", "")).strip():
            lines.append(f"- Domain: `{job.get('domain', '')}`")
        if str(job.get("task_ref", "")).strip():
            lines.append(f"- Task ref: `{job.get('task_ref', '')}`")
        if str(job.get("lane", "")).strip():
            lines.append(f"- Lane: `{job.get('lane', '')}`")
        if str(job.get("purpose", "")).strip():
            lines.append(f"- Purpose: {job.get('purpose', '')}")
        if str(job.get("phase", "")).strip():
            lines.append(f"- Phase: `{job.get('phase', '')}`")
        if str(job.get("command", "")).strip():
            lines.append(f"- Command: `{job.get('command', '')}`")
        if str(job.get("cwd", "")).strip():
            lines.append(f"- CWD: `{job.get('cwd', '')}`")
        if str(job.get("pid", "")).strip():
            lines.append(f"- PID: `{job.get('pid')}`")
        if str(job.get("exit_code", "")).strip():
            lines.append(f"- Exit code: `{job.get('exit_code')}`")
        if str(job.get("run_dir", "")).strip():
            lines.append(f"- Run dir: `{job.get('run_dir', '')}`")
        if str(job.get("status_file", "")).strip():
            lines.append(f"- Status file: `{job.get('status_file', '')}`")
        if str(job.get("log_file", "")).strip():
            lines.append(f"- Log file: `{job.get('log_file', '')}`")
        if job.get("expected_outputs"):
            lines.append("- Expected outputs:")
            for path_text in job["expected_outputs"]:
                lines.append(f"  - `{path_text}`")
        if str(job.get("check_command", "")).strip():
            lines.append(f"- Check command: `{job.get('check_command', '')}`")
        if str(job.get("next_check_hint", "")).strip():
            lines.append(f"- Next check hint: {job.get('next_check_hint', '')}")
        if str(job.get("decision_if_success", "")).strip():
            lines.append(f"- If success: {job.get('decision_if_success', '')}")
        if str(job.get("decision_if_failure", "")).strip():
            lines.append(f"- If failure: {job.get('decision_if_failure', '')}")
        if observation:
            lines.append("- Latest observation:")
            lines.append(f"  - checked_at: `{observation.get('checked_at', '')}`")
            lines.append(f"  - pid_alive: `{observation.get('pid_alive', False)}`")
            if observation.get("status_file_status"):
                lines.append(f"  - status_file_status: `{observation.get('status_file_status', '')}`")
            if observation.get("runtime_status"):
                lines.append(f"  - runtime_status: `{observation.get('runtime_status', '')}`")
            outputs = observation.get("expected_outputs", [])
            if isinstance(outputs, list) and outputs:
                existing = sum(1 for item in outputs if isinstance(item, dict) and item.get("exists"))
                lines.append(f"  - expected_outputs_present: `{existing}/{len(outputs)}`")
            check_result = observation.get("check_result", {})
            if isinstance(check_result, dict) and check_result:
                lines.append(f"  - check_command_exit_code: `{check_result.get('exit_code')}`")
        lines.append("")
    return "\n".join(lines)


def write_active_jobs_summary(root: Path | None = None, jobs: list[dict[str, Any]] | None = None) -> Path:
    _ensure_registry_dir(root)
    payload = jobs if jobs is not None else list_active_jobs(root)
    path = active_jobs_summary_file(root)
    path.write_text(render_active_jobs_markdown(payload), encoding="utf-8")
    return path
