"""FastAPI application for the Deep Read Agent product API."""

from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Query, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from src.api.contract import (
    canonical_book_path,
    resolve_book_id,
    resolve_reaction_id,
    to_api_book_id,
    to_api_mark_id,
    to_api_reaction_id,
    to_api_reaction_type,
)
from src.api.errors import ApiError, install_error_handlers
from src.api.realtime import build_job_status_response, stream_job_events
from src.api.schemas import (
    ActivityEventsPageResponse,
    AnalysisStateResponse,
    BookDetailResponse,
    BookMarksResponse,
    BooksPageResponse,
    ChapterDetailResponse,
    DeleteMarkResponse,
    ErrorResponse,
    JobStatusResponse,
    LandingResponse,
    MarksPageResponse,
    MarkRecord,
    ReactionsPageResponse,
    SamplePageResponse,
    SetMarkRequest,
    UploadAcceptedResponse,
)
from src.config import get_backend_cors_origins, get_backend_runtime_root, get_sample_book_id, get_upload_max_bytes
from src.library.catalog import (
    cover_asset_path,
    get_activity_page,
    get_analysis_state,
    get_book,
    get_book_detail,
    get_book_featured_reactions,
    get_chapter_detail,
    get_chapter_reactions_page,
    get_chapter_result,
    list_books_page,
    source_asset_path,
)
from src.library.jobs import create_upload_job, launch_sequential_job, load_job
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


REACTION_TYPE_INFOS = [
    {
        "type": "highlight",
        "label": "Highlight",
        "description": "Marks a sentence the agent thinks is worth carrying forward.",
        "priority": 0,
    },
    {
        "type": "association",
        "label": "Association",
        "description": "Connects the passage to adjacent ideas or patterns.",
        "priority": 4,
    },
    {
        "type": "curious",
        "label": "Curious",
        "description": "Pushes on unanswered questions or missing evidence.",
        "priority": 3,
    },
    {
        "type": "discern",
        "label": "Discern",
        "description": "Surfaces the sharper distinction or hidden tension in a claim.",
        "priority": 1,
    },
    {
        "type": "retrospect",
        "label": "Retrospect",
        "description": "Connects the current passage back to an earlier thread in the book.",
        "priority": 2,
    },
]


LANDING_ACTIONS = [
    {"key": "open_books", "label": "Open Books", "target_url": "/books"},
    {"key": "open_marks", "label": "My Marks", "target_url": "/marks"},
]


@app.get("/api/landing", response_model=LandingResponse, responses=ERROR_MODELS, deprecated=True)
def get_landing() -> LandingResponse:
    """Return the legacy backend-driven landing payload."""
    sample_book_id = _sample_book_id()
    detail = _book_detail_payload(sample_book_id)
    teasers = get_book_featured_reactions(sample_book_id, root=_root(), limit=3)
    return LandingResponse(
        product_title="Deep Read Agent",
        tagline="A co-reader that surfaces tensions, blind spots, and sharp reactions while you read nonfiction.",
        primary_actions=LANDING_ACTIONS,
        reaction_types=REACTION_TYPE_INFOS,
        sample_book={
            "book_id": detail["book_id"],
            "title": detail["title"],
            "author": detail["author"],
            "cover_image_url": detail["cover_image_url"],
            "status": detail["status"],
            "result_url": canonical_book_path(detail["book_id"]),
        },
        sample_teasers=teasers,
    )


@app.get("/api/sample", response_model=SamplePageResponse, responses=ERROR_MODELS, deprecated=True)
def get_sample() -> SamplePageResponse:
    """Return the legacy backend-driven sample payload."""
    sample_book_id = _sample_book_id()
    detail = _book_detail_payload(sample_book_id)
    chapters = detail.get("chapters", [])
    if not chapters:
        raise ApiError(status=404, code="BOOK_NOT_FOUND", message="Configured sample book has no chapters.")
    default_chapter_id = int(chapters[0]["chapter_id"])
    for chapter in chapters:
        if chapter.get("result_ready"):
            default_chapter_id = int(chapter["chapter_id"])
            break
    return SamplePageResponse(
        book_id=detail["book_id"],
        default_chapter_id=default_chapter_id,
        title=detail["title"],
        author=detail["author"],
        cover_image_url=detail["cover_image_url"],
        teaser_reactions=get_book_featured_reactions(sample_book_id, root=_root(), limit=3),
        result_entry_url=canonical_book_path(detail["book_id"]),
    )


@app.post("/api/uploads/epub", response_model=UploadAcceptedResponse, status_code=202, responses=ERROR_MODELS)
async def upload_epub(
    file: UploadFile = File(...),
    display_title: Optional[str] = Form(default=None),
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

    job_id, upload_path = create_upload_job(_root())
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(content)
    record = launch_sequential_job(upload_path, root=_root())
    return UploadAcceptedResponse(
        job_id=str(record["job_id"]),
        upload_filename=filename,
        status=str(record.get("status", "queued")),
        book_id=(to_api_book_id(str(record.get("book_id"))) if record.get("book_id") else None),
        job_url=f"/api/jobs/{record['job_id']}",
        ws_url=f"/api/ws/jobs/{record['job_id']}",
    )


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


@app.get("/api/books/{book_id}/activity", response_model=ActivityEventsPageResponse, responses=ERROR_MODELS)
def book_activity(
    book_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
    chapter_id: Optional[int] = Query(default=None),
) -> ActivityEventsPageResponse:
    """Return one book's paginated activity stream."""
    internal_book_id = _resolve_book_id(book_id)
    _ensure_book_exists(internal_book_id)
    return ActivityEventsPageResponse.model_validate(
        get_activity_page(internal_book_id, root=_root(), limit=limit, cursor=cursor, event_type=type, chapter_id=chapter_id)
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


@app.get("/api/books/{book_id}/chapters/{chapter_id}/reactions", response_model=ReactionsPageResponse, responses=ERROR_MODELS)
def book_chapter_reactions(
    book_id: int,
    chapter_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    type: Optional[str] = Query(default=None),
    section_ref: Optional[str] = Query(default=None),
    mark_type: Optional[str] = Query(default=None),
    high_signal_only: bool = Query(default=False),
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
            high_signal_only=high_signal_only,
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


def _sample_book_id() -> str:
    """Resolve the configured sample book id."""
    sample_book_id = str(getattr(app.state, "sample_book_id", "") or get_sample_book_id()).strip()
    if not sample_book_id:
        raise ApiError(status=404, code="BOOK_NOT_FOUND", message="Sample book is not configured.")
    return sample_book_id


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
    normalized["section_ref"] = str(payload.get("section_ref", payload.get("segment_ref", "")))
    normalized.pop("segment_ref", None)
    return normalized


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
    payload["sample"] = book_id == str(getattr(app.state, "sample_book_id", "") or get_sample_book_id()).strip()
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
