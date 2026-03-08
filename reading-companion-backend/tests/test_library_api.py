"""Tests for product-layer state, jobs, REST API, and realtime API behavior."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.contract import to_api_book_id, to_api_reaction_id
from src.library.jobs import refresh_job, save_job
from src.library.storage import upload_file
from src.library.user_marks import delete_mark, list_book_marks, load_marks_state, put_mark


api_module = importlib.import_module("src.api.app")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_jsonl(path: Path, payloads: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in payloads) + "\n",
        encoding="utf-8",
    )


def _bootstrap_book(root: Path, *, stage: str = "completed") -> str:
    book_id = "demo-book"
    output_dir = root / "output" / book_id
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "book_manifest.json",
        {
            "book_id": book_id,
            "book": "Demo Book",
            "author": "Tester",
            "cover_image_url": None,
            "book_language": "en",
            "output_language": "en",
            "source_file": str((root / "state" / "uploads" / "job123.epub").resolve()),
            "source_asset": {"format": "epub", "file": "_assets/source.epub"},
            "updated_at": "2026-03-07T00:00:00Z",
            "chapters": [
                {
                    "id": 1,
                    "title": "Chapter 1",
                    "chapter_number": 1,
                    "reference": "Chapter 1",
                    "status": "done",
                    "segment_count": 1,
                    "markdown_file": "ch01_deep_read.md",
                    "result_file": "ch01_deep_read.json",
                    "visible_reaction_count": 1,
                    "reaction_type_diversity": 1,
                    "high_signal_reaction_count": 1,
                }
            ],
        },
    )
    _write_json(
        output_dir / "run_state.json",
        {
            "mode": "sequential",
            "stage": stage,
            "book": "Demo Book",
            "current_chapter_id": None if stage == "completed" else 1,
            "current_chapter_ref": None if stage == "completed" else "Chapter 1",
            "current_segment_ref": None if stage == "completed" else "1.1",
            "completed_chapters": 1 if stage == "completed" else 0,
            "total_chapters": 1,
            "eta_seconds": 0 if stage == "completed" else 60,
            "updated_at": "2026-03-07T00:00:00Z",
            "error": None,
        },
    )
    _write_jsonl(
        output_dir / "activity.jsonl",
        [
            {
                "event_id": "evt-1",
                "timestamp": "2026-03-07T00:00:00Z",
                "type": "chapter_completed",
                "message": "Chapter 1 完成，已生成结果文件。",
                "chapter_id": 1,
                "chapter_ref": "Chapter 1",
                "reaction_types": ["highlight"],
                "highlight_quote": "Alpha beta",
                "visible_reaction_count": 1,
                "high_signal_reaction_count": 1,
                "featured_reactions": [
                    {
                        "reaction_id": "r1",
                        "type": "highlight",
                        "segment_ref": "1.1",
                        "anchor_quote": "Alpha beta",
                        "content": "Important line.",
                        "target_locator": {
                            "href": "chapter-1.xhtml",
                            "start_cfi": "epubcfi(/6/2!/4/2)",
                            "end_cfi": "epubcfi(/6/2!/4/2)",
                            "match_text": "Alpha beta",
                            "match_mode": "exact",
                        },
                    }
                ],
                "result_file": "ch01_deep_read.json",
            }
        ],
    )
    _write_json(
        output_dir / "ch01_deep_read.json",
        {
            "chapter": {
                "id": 1,
                "title": "Chapter 1",
                "chapter_number": 1,
                "reference": "Chapter 1",
                "status": "done",
            },
            "output_language": "en",
            "generated_at": "2026-03-07T00:00:00Z",
            "sections": [
                {
                    "segment_id": "1.1",
                    "segment_ref": "1.1",
                    "summary": "Segment 1",
                    "original_text": "Alpha beta",
                    "verdict": "pass",
                    "quality_status": "strong",
                    "reflection_summary": "Keep",
                    "reflection_reason_codes": [],
                    "locator": {
                        "href": "chapter-1.xhtml",
                        "start_cfi": "epubcfi(/6/2!/4/2)",
                        "end_cfi": "epubcfi(/6/2!/4/2)",
                        "paragraph_start": 1,
                        "paragraph_end": 1,
                    },
                    "reactions": [
                        {
                            "reaction_id": "r1",
                            "type": "highlight",
                            "anchor_quote": "Alpha beta",
                            "content": "Important line.",
                            "search_query": "",
                            "search_results": [],
                            "target_locator": {
                                "href": "chapter-1.xhtml",
                                "start_cfi": "epubcfi(/6/2!/4/2)",
                                "end_cfi": "epubcfi(/6/2!/4/2)",
                                "match_text": "Alpha beta",
                                "match_mode": "exact",
                            },
                        }
                    ],
                }
            ],
            "chapter_reflection": {"chapter_insights": ["Arc"]},
            "featured_reactions": [
                {
                    "reaction_id": "r1",
                    "type": "highlight",
                    "segment_ref": "1.1",
                    "anchor_quote": "Alpha beta",
                    "content": "Important line.",
                    "target_locator": {
                        "href": "chapter-1.xhtml",
                        "start_cfi": "epubcfi(/6/2!/4/2)",
                        "end_cfi": "epubcfi(/6/2!/4/2)",
                        "match_text": "Alpha beta",
                        "match_mode": "exact",
                    },
                }
            ],
            "visible_reaction_count": 1,
            "reaction_type_diversity": 1,
            "high_signal_reaction_count": 1,
            "ui_summary": {
                "kept_section_count": 1,
                "skipped_section_count": 0,
                "reaction_counts": {"highlight": 1},
            },
        },
    )
    asset_dir = output_dir / "_assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / "source.epub").write_bytes(b"epub")
    return book_id


def test_user_marks_put_is_idempotent_and_overwrites(tmp_path):
    """Marks should be idempotent for the same value and overwrite on new values."""
    book_id = _bootstrap_book(tmp_path)

    first = put_mark(book_id=book_id, reaction_id="r1", mark_type="known", root=tmp_path)
    second = put_mark(book_id=book_id, reaction_id="r1", mark_type="known", root=tmp_path)
    third = put_mark(book_id=book_id, reaction_id="r1", mark_type="blindspot", root=tmp_path)

    assert first["reaction_id"] == "r1"
    assert second["mark_type"] == "known"
    assert third["mark_type"] == "blindspot"
    assert third["created_at"] == first["created_at"]
    assert len(list_book_marks(book_id, root=tmp_path)) == 1

    deleted = delete_mark("r1", root=tmp_path)
    assert deleted is True
    assert load_marks_state(tmp_path)["marks"] == {}


def test_refresh_job_picks_up_book_id_from_generated_artifacts(tmp_path):
    """Job refresh should populate book_id once manifests become available."""
    upload_path = upload_file("job123", tmp_path)
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(b"epub")
    _bootstrap_book(tmp_path)

    save_job(
        {
            "job_id": "job123",
            "status": "queued",
            "upload_path": str(upload_path),
            "book_id": None,
            "pid": None,
            "created_at": "2026-03-07T00:00:00Z",
            "updated_at": "2026-03-07T00:00:00Z",
            "error": None,
        },
        tmp_path,
    )

    refreshed = refresh_job("job123", root=tmp_path)

    assert refreshed["book_id"] == "demo-book"
    assert refreshed["status"] == "completed"


def test_api_reads_books_chapters_marks_and_docs(tmp_path):
    """The API should expose typed bookshelf, result, marks, and docs endpoints."""
    book_id = _bootstrap_book(tmp_path)
    public_book_id = to_api_book_id(book_id)
    public_reaction_id = to_api_reaction_id(book_id=book_id, reaction_id="r1")
    api_module.app.state.root = tmp_path
    api_module.app.state.sample_book_id = book_id
    client = TestClient(api_module.app)

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200

    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    assert "/api/books" in openapi_response.json()["paths"]

    landing_response = client.get("/api/landing")
    assert landing_response.status_code == 200
    assert landing_response.json()["sample_book"]["book_id"] == public_book_id

    sample_response = client.get("/api/sample")
    assert sample_response.status_code == 200
    assert sample_response.json()["book_id"] == public_book_id
    assert sample_response.json()["default_chapter_id"] == 1

    books_response = client.get("/api/books")
    assert books_response.status_code == 200
    books_payload = books_response.json()
    assert books_payload["items"][0]["book_id"] == public_book_id
    assert books_payload["page_info"]["has_more"] is False

    detail_response = client.get(f"/api/books/{public_book_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "Demo Book"
    assert detail_response.json()["sample"] is True

    analysis_response = client.get(f"/api/books/{public_book_id}/analysis-state")
    assert analysis_response.status_code == 200
    assert analysis_response.json()["status"] == "completed"
    assert analysis_response.json()["book_id"] == public_book_id

    activity_response = client.get(f"/api/books/{public_book_id}/activity")
    assert activity_response.status_code == 200
    assert activity_response.json()["items"][0]["event_id"] == "evt-1"

    chapter_response = client.get(f"/api/books/{public_book_id}/chapters/1")
    assert chapter_response.status_code == 200
    assert chapter_response.json()["book_id"] == public_book_id
    assert chapter_response.json()["featured_reactions"][0]["reaction_id"] == public_reaction_id

    reactions_response = client.get(f"/api/books/{public_book_id}/chapters/1/reactions")
    assert reactions_response.status_code == 200
    assert reactions_response.json()["items"][0]["reaction_id"] == public_reaction_id

    source_response = client.get(f"/api/books/{public_book_id}/source")
    assert source_response.status_code == 200
    assert source_response.content == b"epub"

    put_response = client.put(
        f"/api/marks/{public_reaction_id}",
        json={"book_id": public_book_id, "mark_type": "known"},
    )
    assert put_response.status_code == 200
    assert put_response.json()["mark_type"] == "known"
    assert put_response.json()["reaction_id"] == public_reaction_id

    marks_response = client.get(f"/api/books/{public_book_id}/marks")
    assert marks_response.status_code == 200
    assert marks_response.json()["book_id"] == public_book_id
    assert marks_response.json()["groups"][0]["items"][0]["reaction_id"] == public_reaction_id
    assert isinstance(marks_response.json()["groups"][0]["items"][0]["mark_id"], int)

    global_marks_response = client.get("/api/marks")
    assert global_marks_response.status_code == 200
    assert global_marks_response.json()["items"][0]["reaction_id"] == public_reaction_id
    assert isinstance(global_marks_response.json()["items"][0]["mark_id"], int)

    delete_response = client.delete(f"/api/marks/{public_reaction_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["reaction_id"] == public_reaction_id
    assert delete_response.json()["deleted"] is True


def test_api_upload_and_job_polling(tmp_path, monkeypatch):
    """Upload should return a job envelope and job polling should surface the typed status payload."""
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    monkeypatch.setattr(api_module, "create_upload_job", lambda root: ("job999", root / "state" / "uploads" / "job999.epub"))
    monkeypatch.setattr(
        api_module,
        "launch_sequential_job",
        lambda upload_path, root=None: {
            "job_id": "job999",
            "status": "queued",
            "upload_path": str(upload_path),
            "book_id": None,
            "pid": 123,
            "created_at": "2026-03-07T00:00:00Z",
            "updated_at": "2026-03-07T00:00:00Z",
            "error": None,
        },
    )
    monkeypatch.setattr(
        api_module,
        "_ensure_job_exists",
        lambda job_id: None,
    )
    monkeypatch.setattr(
        api_module,
        "build_job_status_response",
        lambda job_id, root: api_module.JobStatusResponse(
            job_id=job_id,
            status="deep_reading",
            book_id=to_api_book_id("demo-book"),
            book_title="Demo Book",
            progress_percent=50.0,
            completed_chapters=1,
            total_chapters=2,
            current_chapter_id=2,
            current_chapter_ref="Chapter 2",
            current_section_ref="2.3",
            eta_seconds=120,
            last_error=None,
            created_at="2026-03-07T00:00:00Z",
            updated_at="2026-03-07T00:00:01Z",
            ws_url=f"/api/ws/jobs/{job_id}",
        ),
    )

    upload_response = client.post(
        "/api/uploads/epub",
        files={"file": ("demo.epub", b"epub-bytes", "application/epub+zip")},
    )
    assert upload_response.status_code == 202
    assert upload_response.json()["job_id"] == "job999"
    assert upload_response.json()["ws_url"] == "/api/ws/jobs/job999"

    job_response = client.get("/api/jobs/job999")
    assert job_response.status_code == 200
    assert job_response.json()["book_id"] == to_api_book_id("demo-book")
    assert job_response.json()["status"] == "deep_reading"


def test_api_errors_use_stable_error_envelope(tmp_path):
    """Validation and missing-resource failures should use the shared ErrorResponse schema."""
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    upload_response = client.post(
        "/api/uploads/epub",
        files={"file": ("demo.txt", b"bad", "text/plain")},
    )
    assert upload_response.status_code == 400
    assert upload_response.json()["code"] == "UNSUPPORTED_FILE_TYPE"

    missing_book = client.get("/api/books/999999999")
    assert missing_book.status_code == 404
    assert missing_book.json()["code"] == "BOOK_NOT_FOUND"


def test_websocket_streams_snapshot_activity_and_heartbeat(tmp_path):
    """The job websocket should emit the snapshot, activity-created, and heartbeat events."""
    book_id = _bootstrap_book(tmp_path, stage="deep_reading")
    upload_path = upload_file("job123", tmp_path)
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(b"epub")
    _write_json(
        tmp_path / "state" / "jobs" / "job123.json",
        {
            "job_id": "job123",
            "status": "deep_reading",
            "upload_path": str(upload_path),
            "book_id": book_id,
            "pid": None,
            "created_at": "2026-03-07T00:00:00Z",
            "updated_at": "2026-03-07T00:00:00Z",
            "error": None,
        },
    )

    api_module.app.state.root = tmp_path
    api_module.app.state.ws_poll_interval = 0.01
    api_module.app.state.ws_heartbeat_interval = 0.01
    client = TestClient(api_module.app)

    with client.websocket_connect("/api/ws/jobs/job123") as websocket:
        first = websocket.receive_json()
        second = websocket.receive_json()
        third = websocket.receive_json()

    assert first["event_type"] == "job.snapshot"
    assert first["payload"]["status"] == "deep_reading"
    assert second["event_type"] in {"structure.ready", "activity.created"}
    assert third["event_type"] in {"activity.created", "heartbeat", "chapter.completed"}
