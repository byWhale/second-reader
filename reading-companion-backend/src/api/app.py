"""FastAPI application for the Deep Read Agent product API."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, File, Form, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.api.contract import (
    canonical_book_path,
    resolve_book_id,
    resolve_reaction_id,
    to_api_book_id,
    to_api_mark_id,
    to_api_mark_type,
    to_api_reaction_id,
    to_api_reaction_type,
)
from src.api.errors import ApiError, install_error_handlers
from src.api.realtime import build_job_status_response, stream_job_events
from src.api.schemas import (
    ActivityEventsPageResponse,
    AnalysisLogResponse,
    AnalysisResumeAcceptedResponse,
    AnalysisStartAcceptedResponse,
    AnalysisStateResponse,
    BookDetailResponse,
    BookMarksResponse,
    BooksPageResponse,
    ChapterDetailResponse,
    ChapterOutlineResponse,
    DeleteMarkResponse,
    ErrorResponse,
    HealthResponse,
    JobStatusResponse,
    MarksPageResponse,
    MarkRecord,
    ReactionsPageResponse,
    SetMarkRequest,
    UploadAcceptedResponse,
)
from src.api.test_mode import fixture_upload_path, launch_e2e_fixture_analysis, launch_e2e_fixture_job
from src.config import (
    get_backend_cors_origins,
    get_backend_host,
    get_backend_port,
    get_backend_run_mode,
    get_backend_runtime_root,
    get_backend_test_fixture_profile,
    get_backend_test_mode,
    get_backend_version,
    get_upload_max_bytes,
)
from src.library.catalog import (
    cover_asset_path,
    get_activity_page,
    get_analysis_state,
    get_book,
    get_book_detail,
    get_chapter_detail,
    get_chapter_outline,
    get_chapter_reactions_page,
    get_chapter_result,
    list_books_page,
    source_asset_path,
)
from src.library.jobs import (
    analysis_log_payload,
    create_upload_job,
    launch_book_analysis_job,
    launch_parse_job,
    launch_sequential_job,
    load_job,
    provision_uploaded_book,
    recover_unfinished_jobs,
    resume_job_for_book,
)
from src.library.user_marks import delete_mark, list_book_marks_grouped, list_marks_page, put_mark


ERROR_MODELS = {
    400: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    413: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

app = FastAPI(title="Deep Read Agent API")
app.state.root = get_backend_runtime_root()
install_error_handlers(app)

cors_origins = get_backend_cors_origins()
if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.on_event("startup")
def recover_jobs_on_startup() -> None:
    """Refresh resumable jobs so long-running work continues after restarts."""
    recover_unfinished_jobs(_root())


@app.get("/api/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    """Return a lightweight backend liveness snapshot."""
    return HealthResponse(
        status="ok",
        service="backend",
        mode=get_backend_run_mode(),
        host=get_backend_host(),
        port=get_backend_port(),
        runtime_root=str(_root()),
        version=get_backend_version(),
    )


@app.post("/api/uploads/epub", response_model=UploadAcceptedResponse, status_code=202, responses=ERROR_MODELS)
async def upload_epub(
    file: UploadFile = File(...),
    display_title: Optional[str] = Form(default=None),
    start_mode: Literal["immediate", "deferred"] = Form(default="immediate"),
) -> UploadAcceptedResponse:
    """Upload an EPUB and start a background sequential read job."""
    del display_title
    filename = file.filename or ""
    if not filename.lower().endswith(".epub"):
        raise ApiError(status=400, code="UNSUPPORTED_FILE_TYPE", message="Only EPUB uploads are supported.")

    content = await file.read()
    max_bytes = get_upload_max_bytes()
    if len(content) > max_bytes:
        raise ApiError(
            status=413,
            code="PAYLOAD_TOO_LARGE",
            message=f"Uploaded file exceeds the configured size limit of {max_bytes} bytes.",
        )

    if get_backend_test_mode() and get_backend_test_fixture_profile() == "e2e":
        upload_path = fixture_upload_path(_root())
        job_id = upload_path.stem
    else:
        job_id, upload_path = create_upload_job(_root())
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(content)
    provisional_book_id = provision_uploaded_book(upload_path, root=_root())
    if get_backend_test_mode() and get_backend_test_fixture_profile() == "e2e":
        record = launch_e2e_fixture_job(upload_path, upload_filename=filename, root=_root(), start_mode=start_mode)
    else:
        record = (
            launch_sequential_job(upload_path, root=_root(), book_id=provisional_book_id)
            if start_mode == "immediate"
            else launch_parse_job(upload_path, root=_root(), book_id=provisional_book_id)
        )
    return UploadAcceptedResponse(upload_filename=filename, **_job_accepted_payload(record))


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse, responses=ERROR_MODELS)
def get_job(job_id: str) -> JobStatusResponse:
    """Return the refreshed state of one background job."""
    _ensure_job_exists(job_id)
    return build_job_status_response(job_id, _root())


@app.get("/api/books", response_model=BooksPageResponse, responses=ERROR_MODELS)
def books_index(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
) -> BooksPageResponse:
    """Return the paginated bookshelf view."""
    payload = list_books_page(root=_root(), limit=limit, cursor=cursor, status=status, search=search)
    return BooksPageResponse.model_validate(payload)


@app.get("/api/books/{book_id}", response_model=BookDetailResponse, responses=ERROR_MODELS)
def book_detail(book_id: int) -> BookDetailResponse:
    """Return the result-view overview for one book."""
    internal_book_id = _resolve_book_id(book_id)
    return BookDetailResponse.model_validate(_book_detail_payload(internal_book_id))


@app.get("/api/books/{book_id}/analysis-state", response_model=AnalysisStateResponse, responses=ERROR_MODELS)
def book_analysis_state(book_id: int) -> AnalysisStateResponse:
    """Return the current progress-page snapshot for one book."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_book_exists(internal_book_id)
    payload = get_analysis_state(internal_book_id, root=_root())
    if str(payload.get("status", "")) == "error":
        raise ApiError(status=409, code="ANALYSIS_FAILED", message=str(payload.get("last_error", {}).get("message", "Analysis failed.")))
    return AnalysisStateResponse.model_validate(payload)


@app.get("/api/books/{book_id}/analysis-log", response_model=AnalysisLogResponse, responses=ERROR_MODELS)
def book_analysis_log(book_id: int, line_limit: int = Query(default=120, ge=20, le=400)) -> AnalysisLogResponse:
    """Return the latest technical log tail for one book analysis."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_book_exists(internal_book_id)
    return AnalysisLogResponse.model_validate(analysis_log_payload(internal_book_id, root=_root(), line_limit=line_limit))


@app.post("/api/books/{book_id}/analysis/start", response_model=AnalysisStartAcceptedResponse, status_code=202, responses=ERROR_MODELS)
def start_book_analysis(book_id: int) -> AnalysisStartAcceptedResponse:
    """Start sequential analysis for an uploaded book that has not begun deep reading yet."""
    internal_book_id = _resolve_book_id(book_id)
    detail = _book_detail_payload(internal_book_id)
    status = str(detail.get("status", "not_started"))
    if status == "analyzing":
        raise ApiError(status=409, code="ANALYSIS_ALREADY_RUNNING", message="This book is already being analyzed.")
    if status == "completed":
        raise ApiError(status=409, code="ANALYSIS_ALREADY_COMPLETED", message="This book has already completed deep reading.")
    if status != "not_started":
        raise ApiError(status=409, code="ANALYSIS_NOT_STARTABLE", message="This book cannot start deep reading right now.")

    if get_backend_test_mode() and get_backend_test_fixture_profile() == "e2e":
        record = launch_e2e_fixture_analysis(internal_book_id, root=_root())
    else:
        try:
            record = launch_book_analysis_job(internal_book_id, root=_root())
        except FileNotFoundError as exc:
            raise ApiError(status=404, code="BOOK_NOT_FOUND", message=f"Book '{book_id}' was not found.") from exc
    return AnalysisStartAcceptedResponse(**_job_accepted_payload(record))


@app.post("/api/books/{book_id}/analysis/resume", response_model=AnalysisResumeAcceptedResponse, status_code=202, responses=ERROR_MODELS)
def resume_book_analysis(book_id: int) -> AnalysisResumeAcceptedResponse:
    """Resume a paused or interrupted analysis job from the latest checkpoint."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_book_exists(internal_book_id)
    try:
        record = resume_job_for_book(internal_book_id, root=_root())
    except FileNotFoundError as exc:
        raise ApiError(status=404, code="BOOK_NOT_FOUND", message=f"Book '{book_id}' was not found.") from exc
    except RuntimeError as exc:
        raise ApiError(status=409, code="ANALYSIS_NOT_RESUMABLE", message=str(exc)) from exc
    return AnalysisResumeAcceptedResponse(**_job_accepted_payload(record))


@app.get("/api/books/{book_id}/activity", response_model=ActivityEventsPageResponse, responses=ERROR_MODELS)
def book_activity(
    book_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
    stream: Optional[Literal["mindstream", "system"]] = Query(default=None),
    chapter_id: Optional[int] = Query(default=None),
) -> ActivityEventsPageResponse:
    """Return one book's paginated activity stream."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_book_exists(internal_book_id)
    return ActivityEventsPageResponse.model_validate(
        get_activity_page(
            internal_book_id,
            root=_root(),
            limit=limit,
            cursor=cursor,
            event_type=type,
            stream=stream,
            chapter_id=chapter_id,
        )
    )


@app.get("/api/books/{book_id}/source", responses=ERROR_MODELS)
def book_source(book_id: int) -> FileResponse:
    """Return the frontend-accessible source EPUB asset."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_book_exists(internal_book_id)
    path = source_asset_path(internal_book_id, root=_root())
    if not path.exists():
        raise ApiError(status=404, code="BOOK_NOT_FOUND", message=f"Source asset for book '{book_id}' was not found.")
    return FileResponse(path, media_type="application/epub+zip", filename="source.epub")


@app.get("/api/books/{book_id}/cover", responses=ERROR_MODELS)
def book_cover(book_id: int) -> FileResponse:
    """Return the cover image asset for one book when available."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_book_exists(internal_book_id)
    path = cover_asset_path(internal_book_id, root=_root())
    if path is None or not path.exists():
        raise ApiError(status=404, code="BOOK_NOT_FOUND", message=f"Cover asset for book '{book_id}' was not found.")
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, filename=path.name)


@app.get("/api/marks", response_model=MarksPageResponse, responses=ERROR_MODELS)
def marks_index(
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    book_id: Optional[int] = Query(default=None),
    mark_type: Optional[str] = Query(default=None),
) -> MarksPageResponse:
    """Return paginated global marks."""
    internal_book_id = _resolve_book_id(book_id) if book_id is not None else None
    if internal_book_id:
        _ensure_book_exists(internal_book_id)
    payload = list_marks_page(root=_root(), limit=limit, cursor=cursor, book_id=internal_book_id, mark_type=mark_type)
    payload["items"] = [_mark_record(item) for item in payload.get("items", [])]
    return MarksPageResponse.model_validate(payload)


@app.get("/api/books/{book_id}/marks", response_model=BookMarksResponse, responses=ERROR_MODELS)
def book_marks(book_id: int) -> BookMarksResponse:
    """Return one book's marks grouped by chapter."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_book_exists(internal_book_id)
    groups = []
    for group in list_book_marks_grouped(internal_book_id, root=_root()):
        groups.append({
            "chapter_id": int(group.get("chapter_id", 0)),
            "chapter_ref": str(group.get("chapter_ref", "")),
            "items": [_mark_record(item) for item in group.get("items", [])],
        })
    return BookMarksResponse(book_id=to_api_book_id(internal_book_id), groups=groups)


@app.get("/api/books/{book_id}/chapters/{chapter_id}", response_model=ChapterDetailResponse, responses=ERROR_MODELS)
def book_chapter(
    book_id: int,
    chapter_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    reaction_filter: Optional[str] = Query(default=None),
) -> ChapterDetailResponse:
    """Return one chapter result-view payload."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_chapter_ready(internal_book_id, chapter_id)
    return ChapterDetailResponse.model_validate(
        get_chapter_detail(internal_book_id, chapter_id, root=_root(), limit=limit, cursor=cursor, reaction_filter=reaction_filter)
    )


@app.get("/api/books/{book_id}/chapters/{chapter_id}/outline", response_model=ChapterOutlineResponse, responses=ERROR_MODELS)
def book_chapter_outline(book_id: int, chapter_id: int) -> ChapterOutlineResponse:
    """Return the lightweight semantic outline used by the chapter drawer."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_book_exists(internal_book_id)
    try:
        payload = get_chapter_outline(internal_book_id, chapter_id, root=_root())
    except FileNotFoundError as exc:
        raise ApiError(
            status=404,
            code="CHAPTER_NOT_FOUND",
            message=f"Chapter '{chapter_id}' was not found in book '{book_id}'.",
        ) from exc
    return ChapterOutlineResponse.model_validate(payload)


@app.get("/api/books/{book_id}/chapters/{chapter_id}/reactions", response_model=ReactionsPageResponse, responses=ERROR_MODELS)
def book_chapter_reactions(
    book_id: int,
    chapter_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
    section_ref: Optional[str] = Query(default=None),
    mark_type: Optional[str] = Query(default=None),
) -> ReactionsPageResponse:
    """Return a flattened paginated reaction list for one chapter."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_chapter_ready(internal_book_id, chapter_id)
    return ReactionsPageResponse.model_validate(
        get_chapter_reactions_page(
            internal_book_id,
            chapter_id,
            root=_root(),
            limit=limit,
            cursor=cursor,
            reaction_type=type,
            section_ref=section_ref,
            mark_type=mark_type,
        )
    )


@app.put("/api/marks/{reaction_id}", response_model=MarkRecord, responses=ERROR_MODELS)
def put_reaction_mark(reaction_id: int, request: SetMarkRequest) -> MarkRecord:
    """Create or update one resonance mark on a reaction."""
    internal_book_id = _resolve_book_id(request.book_id)
    _ensure_book_exists(internal_book_id)
    internal_reaction_id = _resolve_reaction_id(reaction_id, internal_book_id=internal_book_id)
    try:
        payload = put_mark(book_id=internal_book_id, reaction_id=internal_reaction_id, mark_type=request.mark_type, root=_root())
    except FileNotFoundError as exc:
        raise ApiError(status=404, code="MARK_TARGET_NOT_FOUND", message=f"Reaction '{reaction_id}' was not found.") from exc
    return MarkRecord.model_validate(_mark_record(payload))


@app.delete("/api/marks/{reaction_id}", response_model=DeleteMarkResponse, responses=ERROR_MODELS)
def delete_reaction_mark(reaction_id: int) -> DeleteMarkResponse:
    """Delete one persisted mark."""
    internal_reaction_id = _resolve_reaction_id(reaction_id)
    deleted = delete_mark(internal_reaction_id, root=_root())
    if not deleted:
        raise ApiError(status=404, code="MARK_TARGET_NOT_FOUND", message=f"Reaction '{reaction_id}' was not found.")
    return DeleteMarkResponse(reaction_id=reaction_id, deleted=True)


@app.websocket("/api/ws/jobs/{job_id}")
async def ws_job(job_id: str, websocket: WebSocket) -> None:
    """Stream live job-scoped progress updates."""
    try:
        _ensure_job_exists(job_id)
    except ApiError:
        await websocket.accept()
        await websocket.close(code=4404, reason="JOB_NOT_FOUND")
        return

    try:
        await stream_job_events(
            websocket,
            root=_root(),
            job_id=job_id,
            poll_interval=_poll_interval(),
            heartbeat_interval=_heartbeat_interval(),
        )
    except WebSocketDisconnect:
        return


@app.websocket("/api/ws/books/{book_id}/analysis")
async def ws_book_analysis(book_id: int, websocket: WebSocket) -> None:
    """Stream live book-scoped analysis updates."""
    internal_book_id = _resolve_book_id(book_id)
    try:
        _ensure_book_exists(internal_book_id)
    except ApiError:
        await websocket.accept()
        await websocket.close(code=4404, reason="BOOK_NOT_FOUND")
        return

    try:
        await stream_job_events(
            websocket,
            root=_root(),
            book_id=internal_book_id,
            poll_interval=_poll_interval(),
            heartbeat_interval=_heartbeat_interval(),
        )
    except WebSocketDisconnect:
        return


def _root() -> Path:
    """Resolve the API storage root, overridable in tests."""
    return Path(getattr(app.state, "root", get_backend_runtime_root()))


def _poll_interval() -> float:
    """Return the websocket poll interval in seconds."""
    return float(getattr(app.state, "ws_poll_interval", 1.0))


def _heartbeat_interval() -> float:
    """Return the websocket heartbeat interval in seconds."""
    return float(getattr(app.state, "ws_heartbeat_interval", 15.0))


def _mark_record(payload: dict) -> dict:
    """Normalize persisted marks into the public API field names."""
    normalized = dict(payload)
    internal_book_id = str(payload.get("book_id", ""))
    internal_reaction_id = str(payload.get("reaction_id", ""))
    normalized["mark_id"] = to_api_mark_id(book_id=internal_book_id, reaction_id=internal_reaction_id)
    normalized["book_id"] = to_api_book_id(internal_book_id)
    normalized["reaction_id"] = to_api_reaction_id(book_id=internal_book_id, reaction_id=internal_reaction_id)
    normalized["reaction_type"] = to_api_reaction_type(str(payload.get("reaction_type", "")))
    normalized["mark_type"] = to_api_mark_type(str(payload.get("mark_type", "")))
    normalized["section_ref"] = str(payload.get("section_ref", payload.get("segment_ref", "")))
    supersedes_reaction_id = str(payload.get("supersedes_reaction_id", "") or "").strip()
    normalized["supersedes_reaction_id"] = (
        to_api_reaction_id(book_id=internal_book_id, reaction_id=supersedes_reaction_id)
        if supersedes_reaction_id
        else None
    )
    normalized.pop("segment_ref", None)
    return normalized


def _job_accepted_payload(record: dict) -> dict:
    """Normalize a persisted job record into the shared accepted-job envelope."""
    return {
        "job_id": str(record["job_id"]),
        "status": str(record.get("status", "queued")),
        "book_id": (to_api_book_id(str(record.get("book_id"))) if record.get("book_id") else None),
        "job_url": f"/api/jobs/{record['job_id']}",
        "ws_url": f"/api/ws/jobs/{record['job_id']}",
    }


def _ensure_job_exists(job_id: str) -> None:
    """Raise a typed error if the job record does not exist."""
    try:
        load_job(job_id, root=_root())
    except FileNotFoundError as exc:
        raise ApiError(status=404, code="JOB_NOT_FOUND", message=f"Job '{job_id}' was not found.") from exc


def _ensure_book_exists(book_id: str) -> None:
    """Raise a typed error if the book artifacts do not exist."""
    try:
        get_book(book_id, root=_root())
    except FileNotFoundError as exc:
        raise ApiError(status=404, code="BOOK_NOT_FOUND", message=f"Book '{book_id}' was not found.") from exc


def _resolve_book_id(book_id: int | str) -> str:
    """Resolve a public book id into the internal runtime book id."""
    try:
        return resolve_book_id(book_id, root=_root())
    except FileNotFoundError as exc:
        raise ApiError(status=404, code="BOOK_NOT_FOUND", message=f"Book '{book_id}' was not found.") from exc


def _resolve_reaction_id(reaction_id: int | str, *, internal_book_id: str | None = None) -> str:
    """Resolve a public reaction id into the internal runtime reaction id."""
    try:
        return resolve_reaction_id(reaction_id, root=_root(), internal_book_id=internal_book_id)
    except FileNotFoundError as exc:
        raise ApiError(status=404, code="MARK_TARGET_NOT_FOUND", message=f"Reaction '{reaction_id}' was not found.") from exc


def _book_detail_payload(book_id: str) -> dict:
    """Load and normalize one book detail payload."""
    try:
        payload = get_book_detail(book_id, root=_root())
    except FileNotFoundError as exc:
        raise ApiError(status=404, code="BOOK_NOT_FOUND", message=f"Book '{book_id}' was not found.") from exc
    return payload


def _ensure_chapter_ready(book_id: str, chapter_id: int) -> None:
    """Raise typed errors for missing or not-yet-ready chapters."""
    try:
        book = get_book(book_id, root=_root())
    except FileNotFoundError as exc:
        raise ApiError(status=404, code="BOOK_NOT_FOUND", message=f"Book '{book_id}' was not found.") from exc

    manifest = book["manifest"]
    run_state = book.get("run_state") or {}
    chapter_entry = None
    for chapter in manifest.get("chapters", []):
        if int(chapter.get("id", 0)) == chapter_id:
            chapter_entry = chapter
            break
    if chapter_entry is None:
        raise ApiError(status=404, code="CHAPTER_NOT_FOUND", message=f"Chapter '{chapter_id}' was not found in book '{book_id}'.")

    try:
        get_chapter_result(book_id, chapter_id, root=_root())
    except FileNotFoundError as exc:
        if str(run_state.get("stage", "")) == "error":
            raise ApiError(status=409, code="ANALYSIS_FAILED", message=str(run_state.get("error", "Analysis failed."))) from exc
        raise ApiError(status=409, code="CHAPTER_NOT_READY", message=f"Chapter '{chapter_id}' is not ready yet.") from exc
