"""File-backed WebSocket helpers for live analysis updates."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import WebSocket

from src.api.contract import canonical_book_path, canonical_chapter_path, to_api_book_id
from src.api.schemas import (
    ActivityCreatedPayload,
    ActivityEvent,
    BookCompletedPayload,
    ChapterCompletedPayload,
    ChapterStartedPayload,
    HeartbeatPayload,
    JobErrorPayload,
    JobSnapshotPayload,
    JobStatusResponse,
    SegmentStartedPayload,
    StageChangedPayload,
    StructureReadyPayload,
    WsEventEnvelope,
)
from src.library.catalog import get_activity, get_analysis_state
from src.library.jobs import load_job, refresh_job


def _timestamp() -> str:
    """Return a stable UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _event_id(event_type: str, payload: dict, *, job_id: str | None, book_id: int | None) -> str:
    """Build a stable-ish event id for websocket messages."""
    raw = json.dumps(
        {
            "event_type": event_type,
            "payload": payload,
            "job_id": job_id,
            "book_id": book_id,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def _stage_label(status: str, current_chapter_ref: str | None = None) -> str:
    """Map status to user-facing stage label."""
    if status == "queued":
        return "等待开始"
    if status == "parsing_structure":
        return "正在解析书籍结构"
    if status == "deep_reading":
        if current_chapter_ref:
            return f"正在分析 {current_chapter_ref}"
        return "正在顺序深读"
    if status == "chapter_note_generation":
        return "正在生成章节笔记"
    if status == "completed":
        return "全部完成"
    if status == "error":
        return "分析中断"
    return status


def build_job_status_response(job_id: str, root: Path) -> JobStatusResponse:
    """Build the typed job polling payload from persisted state."""
    record = refresh_job(job_id, root)
    internal_book_id = str(record.get("book_id", "") or "") or None
    status = str(record.get("status", "queued"))
    book_title = None
    progress_percent = None
    completed_chapters = None
    total_chapters = None
    current_chapter_id = None
    current_chapter_ref = None
    current_section_ref = None
    eta_seconds = None
    last_error = None
    stage_label = _stage_label(status)

    if internal_book_id:
        try:
            analysis = get_analysis_state(internal_book_id, root)
        except FileNotFoundError:
            analysis = None
        if analysis:
            status = str(analysis.get("status", status))
            book_title = str(analysis.get("title", "") or "") or None
            progress_percent = analysis.get("progress_percent")
            completed_chapters = int(analysis.get("completed_chapters", 0))
            total_chapters = int(analysis.get("total_chapters", 0))
            current_chapter_id = analysis.get("current_chapter_id")
            current_chapter_ref = analysis.get("current_chapter_ref")
            current_section_ref = analysis.get("current_state_panel", {}).get("current_section_ref")
            eta_seconds = analysis.get("eta_seconds")
            last_error = analysis.get("last_error")
            stage_label = str(analysis.get("stage_label", stage_label))

    if status == "error" and last_error is None:
        last_error = {
            "error_id": "job-error",
            "code": "ANALYSIS_FAILED",
            "message": str(record.get("error", "") or "Analysis failed."),
            "status": 409,
            "retryable": False,
            "details": None,
        }

    return JobStatusResponse(
        job_id=str(record.get("job_id", job_id)),
        status=status,  # type: ignore[arg-type]
        book_id=(to_api_book_id(internal_book_id) if internal_book_id else None),
        book_title=book_title,
        progress_percent=progress_percent,
        completed_chapters=completed_chapters,
        total_chapters=total_chapters,
        current_chapter_id=current_chapter_id,
        current_chapter_ref=current_chapter_ref,
        current_section_ref=current_section_ref,
        eta_seconds=eta_seconds,
        last_error=last_error,
        created_at=str(record.get("created_at", "")),
        updated_at=str(record.get("updated_at", "")),
        ws_url=f"/api/ws/jobs/{job_id}",
    )


def build_job_snapshot_payload(job_status: JobStatusResponse) -> JobSnapshotPayload:
    """Convert a job polling payload into the websocket snapshot payload."""
    return JobSnapshotPayload(
        status=job_status.status,
        stage_label=_stage_label(job_status.status, job_status.current_chapter_ref),
        progress_percent=job_status.progress_percent,
        completed_chapters=job_status.completed_chapters,
        total_chapters=job_status.total_chapters,
        current_chapter_id=job_status.current_chapter_id,
        current_chapter_ref=job_status.current_chapter_ref,
        current_section_ref=job_status.current_section_ref,
        eta_seconds=job_status.eta_seconds,
    )


def build_book_snapshot_payload(book_id: str, root: Path) -> JobSnapshotPayload:
    """Build a websocket snapshot payload for a known analyzing book."""
    analysis = get_analysis_state(book_id, root)
    return JobSnapshotPayload(
        status=str(analysis.get("status", "queued")),
        stage_label=str(analysis.get("stage_label", "")),
        progress_percent=analysis.get("progress_percent"),
        completed_chapters=int(analysis.get("completed_chapters", 0)),
        total_chapters=int(analysis.get("total_chapters", 0)),
        current_chapter_id=analysis.get("current_chapter_id"),
        current_chapter_ref=analysis.get("current_chapter_ref"),
        current_section_ref=analysis.get("current_state_panel", {}).get("current_section_ref"),
        eta_seconds=analysis.get("eta_seconds"),
    )


def _public_book_id(book_id: str | None) -> int | None:
    """Convert an internal book id into the public integer id."""
    return to_api_book_id(book_id) if book_id else None


async def _send_event(
    websocket: WebSocket,
    *,
    event_type: str,
    payload: dict,
    job_id: str | None = None,
    book_id: int | None = None,
    event_id: str | None = None,
) -> None:
    """Send a typed websocket envelope."""
    envelope = WsEventEnvelope(
        event_id=event_id or _event_id(event_type, payload, job_id=job_id, book_id=book_id),
        event_type=event_type,
        sent_at=_timestamp(),
        job_id=job_id,
        book_id=book_id,
        payload=payload,
    )
    await websocket.send_json(envelope.model_dump(mode="json"))


async def _send_structure_ready(websocket: WebSocket, *, book_id: str, root: Path, job_id: str | None) -> None:
    """Emit the structure.ready event."""
    analysis = get_analysis_state(book_id, root)
    payload = StructureReadyPayload(
        book_id=int(analysis.get("book_id", to_api_book_id(book_id))),
        title=str(analysis.get("title", "")),
        chapter_count=len(analysis.get("chapters", [])),
        chapters=analysis.get("chapters", []),
    )
    await _send_event(
        websocket,
        event_type="structure.ready",
        payload=payload.model_dump(mode="json"),
        job_id=job_id,
        book_id=payload.book_id,
    )


async def stream_job_events(
    websocket: WebSocket,
    *,
    root: Path,
    job_id: str | None = None,
    book_id: str | None = None,
    poll_interval: float = 1.0,
    heartbeat_interval: float = 15.0,
) -> None:
    """Stream file-backed progress and activity updates over a websocket."""
    await websocket.accept()

    current_book_id = book_id
    if job_id:
        snapshot = build_job_snapshot_payload(build_job_status_response(job_id, root))
    else:
        if current_book_id is None:
            raise FileNotFoundError("Missing websocket scope.")
        snapshot = build_book_snapshot_payload(current_book_id, root)

    await _send_event(
        websocket,
        event_type="job.snapshot",
        payload=snapshot.model_dump(mode="json"),
        job_id=job_id,
        book_id=_public_book_id(current_book_id),
    )

    last_status = snapshot.status
    last_completed_sent = False
    error_sent = False
    last_heartbeat = asyncio.get_running_loop().time()
    structure_sent = False

    if job_id:
        initial_record = load_job(job_id, root)
        current_book_id = str(initial_record.get("book_id", "") or "") or current_book_id
    if current_book_id:
        if current_book_id and not structure_sent:
            try:
                await _send_structure_ready(websocket, book_id=current_book_id, root=root, job_id=job_id)
                structure_sent = True
            except FileNotFoundError:
                structure_sent = False
        initial_activity = get_activity(current_book_id, root)
    else:
        initial_activity = []
    seen_activity_ids = {str(item.get("event_id", "")) for item in initial_activity}

    while True:
        if job_id:
            job_status = build_job_status_response(job_id, root)
            current_book_id = str(load_job(job_id, root).get("book_id", "") or "") or current_book_id
            snapshot = build_job_snapshot_payload(job_status)
        else:
            if current_book_id is None:
                raise FileNotFoundError("Missing websocket scope.")
            snapshot = build_book_snapshot_payload(current_book_id, root)

        if snapshot.status != last_status:
            await _send_event(
                websocket,
                event_type="stage.changed",
                payload=StageChangedPayload(
                    previous_status=last_status,
                    current_status=snapshot.status,
                    stage_label=snapshot.stage_label,
                ).model_dump(mode="json"),
                job_id=job_id,
                book_id=_public_book_id(current_book_id),
            )
            last_status = snapshot.status

        if current_book_id and not structure_sent:
            try:
                await _send_structure_ready(websocket, book_id=current_book_id, root=root, job_id=job_id)
                structure_sent = True
            except FileNotFoundError:
                structure_sent = False

        if current_book_id:
            for event in get_activity(current_book_id, root):
                event_id = str(event.get("event_id", ""))
                if event_id in seen_activity_ids:
                    continue
                seen_activity_ids.add(event_id)
                await _send_event(
                    websocket,
                    event_type="activity.created",
                    payload=ActivityCreatedPayload(event=ActivityEvent.model_validate(event)).model_dump(mode="json"),
                    job_id=job_id,
                    book_id=int(event.get("book_id", 0) or 0) or _public_book_id(current_book_id),
                    event_id=event_id,
                )
                event_type = str(event.get("type", ""))
                if event_type == "chapter_started":
                    await _send_event(
                        websocket,
                        event_type="chapter.started",
                        payload=ChapterStartedPayload(
                            chapter_id=int(event.get("chapter_id", 0) or 0),
                            chapter_ref=str(event.get("chapter_ref", "")),
                            title=str(event.get("message", "")),
                            segment_count=0,
                        ).model_dump(mode="json"),
                        job_id=job_id,
                        book_id=_public_book_id(current_book_id),
                    )
                elif event_type == "segment_started":
                    await _send_event(
                        websocket,
                        event_type="segment.started",
                        payload=SegmentStartedPayload(
                            chapter_id=int(event.get("chapter_id", 0) or 0),
                            chapter_ref=str(event.get("chapter_ref", "")),
                            section_ref=str(event.get("section_ref", "") or ""),
                            section_summary=str(event.get("message", "")),
                        ).model_dump(mode="json"),
                        job_id=job_id,
                        book_id=_public_book_id(current_book_id),
                    )
                elif event_type == "chapter_completed":
                    await _send_event(
                        websocket,
                        event_type="chapter.completed",
                        payload=ChapterCompletedPayload(
                            chapter_id=int(event.get("chapter_id", 0) or 0),
                            chapter_ref=str(event.get("chapter_ref", "")),
                            title=str(event.get("chapter_ref", "")),
                            visible_reaction_count=int(event.get("visible_reaction_count", 0) or 0),
                            high_signal_reaction_count=int(event.get("high_signal_reaction_count", 0) or 0),
                            featured_reactions=event.get("featured_reactions", []),
                            result_url=str(
                                event.get("result_url", "")
                                or canonical_chapter_path(_public_book_id(current_book_id) or 0, int(event.get("chapter_id", 0) or 0))
                            ),
                        ).model_dump(mode="json"),
                        job_id=job_id,
                        book_id=_public_book_id(current_book_id),
                    )

        if snapshot.status == "completed" and not last_completed_sent and current_book_id:
            await _send_event(
                websocket,
                event_type="book.completed",
                payload=BookCompletedPayload(
                    book_id=_public_book_id(current_book_id) or 0,
                    completed_at=_timestamp(),
                    result_url=canonical_book_path(_public_book_id(current_book_id) or 0),
                ).model_dump(mode="json"),
                job_id=job_id,
                book_id=_public_book_id(current_book_id),
            )
            last_completed_sent = True

        if snapshot.status == "error" and not error_sent:
            await _send_event(
                websocket,
                event_type="job.error",
                payload=JobErrorPayload(
                    code="ANALYSIS_FAILED",
                    message=(
                        build_job_status_response(job_id, root).last_error.message
                        if job_id and build_job_status_response(job_id, root).last_error
                        else "Analysis failed."
                    ),
                    retryable=False,
                    chapter_id=snapshot.current_chapter_id,
                    chapter_ref=snapshot.current_chapter_ref,
                    section_ref=snapshot.current_section_ref,
                ).model_dump(mode="json"),
                job_id=job_id,
                book_id=_public_book_id(current_book_id),
            )
            error_sent = True

        now = asyncio.get_running_loop().time()
        if now - last_heartbeat >= heartbeat_interval:
            await _send_event(
                websocket,
                event_type="heartbeat",
                payload=HeartbeatPayload(status=snapshot.status, server_time=_timestamp()).model_dump(mode="json"),
                job_id=job_id,
                book_id=_public_book_id(current_book_id),
            )
            last_heartbeat = now

        await asyncio.sleep(poll_interval)
