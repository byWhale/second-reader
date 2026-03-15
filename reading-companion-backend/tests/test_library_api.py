"""Tests for product-layer state, jobs, REST API, and realtime API behavior."""

from __future__ import annotations

import importlib
import json
from pathlib import Path

from fastapi.testclient import TestClient
from src.api.contract import to_api_book_id, to_api_reaction_id
from src.iterator_reader.storage import parse_state_file
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
                    "status": "done" if stage == "completed" else "pending",
                    "segment_count": 1,
                    "markdown_file": "ch01_deep_read.md",
                    "result_file": "ch01_deep_read.json",
                    "visible_reaction_count": 1 if stage == "completed" else 0,
                    "reaction_type_diversity": 1 if stage == "completed" else 0,
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
            "current_chapter_id": 1 if stage == "deep_reading" else None,
            "current_chapter_ref": "Chapter 1" if stage == "deep_reading" else None,
            "current_segment_ref": "1.1" if stage == "deep_reading" else None,
            "completed_chapters": 1 if stage == "completed" else 0,
            "total_chapters": 1,
            "eta_seconds": 60 if stage == "deep_reading" else 0,
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
            "chapter_heading": {
                "label": "Chapter 1",
                "title": "Opening frame",
                "text": "Chapter 1\nOpening frame",
                "locator": {
                    "href": "chapter-1.xhtml",
                    "start_cfi": "epubcfi(/6/2!/4/2)",
                    "end_cfi": "epubcfi(/6/2!/4/2)",
                    "paragraph_start": 1,
                    "paragraph_end": 1,
                },
            },
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

    first = put_mark(book_id=book_id, reaction_id="r1", mark_type="resonance", root=tmp_path)
    second = put_mark(book_id=book_id, reaction_id="r1", mark_type="resonance", root=tmp_path)
    third = put_mark(book_id=book_id, reaction_id="r1", mark_type="blindspot", root=tmp_path)

    assert first["reaction_id"] == "r1"
    assert second["mark_type"] == "resonance"
    assert third["mark_type"] == "blindspot"
    assert third["created_at"] == first["created_at"]
    assert len(list_book_marks(book_id, root=tmp_path)) == 1

    deleted = delete_mark("r1", root=tmp_path)
    assert deleted is True
    assert load_marks_state(tmp_path)["marks"] == {}


def test_legacy_known_mark_normalizes_to_resonance(tmp_path):
    """Legacy persisted mark_type=known should read back as resonance."""
    book_id = _bootstrap_book(tmp_path)
    _write_json(
        tmp_path / "state" / "user_marks.json",
        {
            "updated_at": "2026-03-07T00:00:00Z",
            "marks": {
                "r1": {
                    "reaction_id": "r1",
                    "book_id": book_id,
                    "book_title": "Demo Book",
                    "chapter_id": 1,
                    "chapter_ref": "Chapter 1",
                    "segment_ref": "1.1",
                    "reaction_type": "highlight",
                    "mark_type": "known",
                    "reaction_excerpt": "Important line.",
                    "anchor_quote": "Alpha beta",
                    "created_at": "2026-03-07T00:00:00Z",
                    "updated_at": "2026-03-07T00:00:00Z",
                }
            },
        },
    )

    marks_state = load_marks_state(tmp_path)
    assert marks_state["marks"]["r1"]["mark_type"] == "resonance"


def test_chapter_outline_endpoint_returns_sections_and_preview_text(tmp_path):
    """Chapter outline should expose compact semantic sections for the drawer."""
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)
    book_id = _bootstrap_book(tmp_path)

    response = client.get(f"/api/books/{to_api_book_id(book_id)}/chapters/1/outline")
    assert response.status_code == 200
    payload = response.json()

    assert payload["book_id"] == to_api_book_id(book_id)
    assert payload["chapter_id"] == 1
    assert payload["chapter_ref"] == "Chapter 1"
    assert payload["title"] == "Chapter 1"
    assert payload["result_ready"] is True
    assert payload["status"] == "completed"
    assert payload["chapter_heading"] == {
        "label": "Chapter 1",
        "title": "Opening frame",
        "subtitle": None,
        "text": "Chapter 1\nOpening frame",
        "locator": {
            "href": "chapter-1.xhtml",
            "start_cfi": "epubcfi(/6/2!/4/2)",
            "end_cfi": "epubcfi(/6/2!/4/2)",
            "paragraph_start": 1,
            "paragraph_end": 1,
        },
    }
    assert payload["section_count"] == 1
    assert payload["sections"] == [
        {
            "section_ref": "1.1",
            "summary": "Segment 1",
            "preview_text": "Alpha beta",
            "visible_reaction_count": 1,
            "locator": {
                "href": "chapter-1.xhtml",
                "start_cfi": "epubcfi(/6/2!/4/2)",
                "end_cfi": "epubcfi(/6/2!/4/2)",
                "paragraph_start": 1,
                "paragraph_end": 1,
            },
        }
    ]


def test_chapter_outline_endpoint_returns_pending_stub_for_unready_chapter(tmp_path):
    """Not-ready chapters should still appear in the drawer without sections."""
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)
    book_id = _bootstrap_book(tmp_path, stage="deep_reading")
    manifest_path = tmp_path / "output" / book_id / "book_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["chapters"][0]["status"] = "pending"
    manifest["chapters"][0]["visible_reaction_count"] = 0
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (tmp_path / "output" / book_id / "ch01_deep_read.json").unlink()

    response = client.get(f"/api/books/{to_api_book_id(book_id)}/chapters/1/outline")
    assert response.status_code == 200
    payload = response.json()

    assert payload["result_ready"] is False
    assert payload["status"] == "pending"
    assert payload["chapter_heading"] is None
    assert payload["section_count"] == 1
    assert payload["sections"] == []


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


def test_refresh_job_matches_uploaded_copy_via_source_asset_digest(tmp_path):
    """Job refresh should still resolve the book when the upload is a copied file with the same EPUB bytes."""
    upload_path = upload_file("job999", tmp_path)
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(b"epub")
    book_id = _bootstrap_book(tmp_path)
    manifest_path = tmp_path / "output" / book_id / "book_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_file"] = str((tmp_path / "data" / "original.epub").resolve())
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    save_job(
        {
            "job_id": "job999",
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

    refreshed = refresh_job("job999", root=tmp_path)

    assert refreshed["book_id"] == "demo-book"
    assert refreshed["status"] == "completed"


def test_refresh_job_auto_resumes_reaped_child(tmp_path, monkeypatch):
    """Zombie child processes should resume from the latest checkpoint budget when possible."""
    jobs_module = importlib.import_module("src.library.jobs")
    upload_path = upload_file("job-zombie", tmp_path)
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_bytes(b"epub")

    launched: list[list[str]] = []

    class _FakeProcess:
        pid = 8765

    monkeypatch.setattr(
        jobs_module.subprocess,
        "Popen",
        lambda command, cwd, stdout, stderr: launched.append(command) or _FakeProcess(),
    )

    save_job(
        {
            "job_id": "job-zombie",
            "status": "queued",
            "upload_path": str(upload_path),
            "book_id": None,
            "pid": 4321,
            "created_at": "2026-03-07T00:00:00Z",
            "updated_at": "2026-03-07T00:00:00Z",
            "error": None,
        },
        tmp_path,
    )

    monkeypatch.setattr(jobs_module.os, "waitpid", lambda pid, flags: (4321, 0))
    monkeypatch.setattr(jobs_module.os, "kill", lambda pid, sig: (_ for _ in ()).throw(AssertionError("kill should not run")))

    refreshed = refresh_job("job-zombie", root=tmp_path)

    assert refreshed["status"] == "parsing_structure"
    assert refreshed["pid"] == 8765
    assert refreshed["resume_count"] == 1
    assert launched


def test_api_reads_books_chapters_marks_and_docs(tmp_path):
    """The API should expose typed bookshelf, result, marks, and docs endpoints."""
    book_id = _bootstrap_book(tmp_path)
    public_book_id = to_api_book_id(book_id)
    public_reaction_id = to_api_reaction_id(book_id=book_id, reaction_id="r1")
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    docs_response = client.get("/docs")
    assert docs_response.status_code == 200

    openapi_response = client.get("/openapi.json")
    assert openapi_response.status_code == 200
    assert "/api/books" in openapi_response.json()["paths"]
    assert "/api/landing" not in openapi_response.json()["paths"]
    assert "/api/sample" not in openapi_response.json()["paths"]

    books_response = client.get("/api/books")
    assert books_response.status_code == 200
    books_payload = books_response.json()
    assert books_payload["items"][0]["book_id"] == public_book_id
    assert books_payload["items"][0]["open_target"] == f"/books/{public_book_id}"
    assert books_payload["page_info"]["has_more"] is False

    detail_response = client.get(f"/api/books/{public_book_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["title"] == "Demo Book"

    analysis_response = client.get(f"/api/books/{public_book_id}/analysis-state")
    assert analysis_response.status_code == 200
    assert analysis_response.json()["status"] == "completed"
    assert analysis_response.json()["book_id"] == public_book_id

    activity_response = client.get(f"/api/books/{public_book_id}/activity")
    assert activity_response.status_code == 200
    assert activity_response.json()["items"][0]["event_id"] == "evt-1"
    assert activity_response.json()["items"][0]["stream"] == "mindstream"
    assert activity_response.json()["items"][0]["kind"] == "chapter_complete"
    assert activity_response.json()["items"][0]["visibility"] == "default"

    chapter_response = client.get(f"/api/books/{public_book_id}/chapters/1")
    assert chapter_response.status_code == 200
    assert chapter_response.json()["book_id"] == public_book_id
    assert chapter_response.json()["featured_reactions"][0]["reaction_id"] == public_reaction_id
    assert chapter_response.json()["chapter_heading"]["title"] == "Opening frame"

    reactions_response = client.get(f"/api/books/{public_book_id}/chapters/1/reactions")
    assert reactions_response.status_code == 200
    assert reactions_response.json()["items"][0]["reaction_id"] == public_reaction_id

    source_response = client.get(f"/api/books/{public_book_id}/source")
    assert source_response.status_code == 200
    assert source_response.content == b"epub"

    put_response = client.put(
        f"/api/marks/{public_reaction_id}",
        json={"book_id": public_book_id, "mark_type": "resonance"},
    )
    assert put_response.status_code == 200
    assert put_response.json()["mark_type"] == "resonance"
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


def test_book_activity_supports_stream_filter(tmp_path):
    """Activity API should filter mindstream and system events without splitting storage."""
    book_id = _bootstrap_book(tmp_path, stage="completed")
    public_book_id = to_api_book_id(book_id)
    output_dir = tmp_path / "output" / book_id
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
            },
            {
                "event_id": "evt-2",
                "timestamp": "2026-03-07T00:00:01Z",
                "type": "structure_checkpoint_saved",
                "message": "已保存解析 checkpoint：Chapter 1",
                "chapter_id": 1,
                "chapter_ref": "Chapter 1",
            },
        ],
    )

    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    mindstream_response = client.get(f"/api/books/{public_book_id}/activity?stream=mindstream")
    system_response = client.get(f"/api/books/{public_book_id}/activity?stream=system")

    assert mindstream_response.status_code == 200
    assert system_response.status_code == 200
    assert [item["event_id"] for item in mindstream_response.json()["items"]] == ["evt-1"]
    assert [item["event_id"] for item in system_response.json()["items"]] == ["evt-2"]


def test_analysis_state_prefers_parse_checkpoint_during_structure_stage(tmp_path):
    """analysis-state should surface parse checkpoint details while the book is still preparing readable chapters."""
    book_id = _bootstrap_book(tmp_path, stage="parsing_structure")
    public_book_id = to_api_book_id(book_id)
    output_dir = tmp_path / "output" / book_id
    _write_json(
        parse_state_file(output_dir),
        {
            "status": "parsing_structure",
            "total_chapters": 3,
            "completed_chapters": 1,
            "parsed_chapter_ids": [1],
            "segmented_chapter_ids": [1],
            "inflight_chapter_ids": [2],
            "pending_chapter_ids": [2, 3],
            "current_chapter_id": 2,
            "current_chapter_ref": "Chapter 2",
            "current_step": "后台准备后续章节",
            "worker_limit": 3,
            "resume_available": True,
            "last_checkpoint_at": "2026-03-14T01:00:00Z",
            "updated_at": "2026-03-14T01:00:00Z",
            "error": None,
        },
    )

    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    response = client.get(f"/api/books/{public_book_id}/analysis-state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "parsing_structure"
    assert payload["completed_chapters"] == 1
    assert payload["total_chapters"] == 3
    assert payload["current_chapter_id"] == 2
    assert payload["current_chapter_ref"] == "Chapter 2"
    assert payload["current_phase_step"] == "后台准备后续章节"
    assert payload["current_phase_step_key"] == "system.step.prefetchFutureChapters"
    assert payload["current_phase_step_params"] is None
    assert payload["resume_available"] is True
    assert payload["stage_label"] == "正在解析 Chapter 2"
    assert payload["stage_label_key"] == "system.stage.parsingChapter"
    assert payload["stage_label_params"] == {"chapter": "Chapter 2"}


def test_chapter_api_tolerates_empty_legacy_target_locator(tmp_path):
    """Legacy featured reactions with empty locator dicts should normalize to null, not 500."""
    book_id = _bootstrap_book(tmp_path)
    public_book_id = to_api_book_id(book_id)
    output_dir = tmp_path / "output" / book_id
    payload = json.loads((output_dir / "ch01_deep_read.json").read_text(encoding="utf-8"))
    payload["featured_reactions"][0]["target_locator"] = {}
    (output_dir / "ch01_deep_read.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    response = client.get(f"/api/books/{public_book_id}/chapters/1")

    assert response.status_code == 200
    assert response.json()["featured_reactions"][0]["target_locator"] is None


def test_api_upload_and_job_polling(tmp_path, monkeypatch):
    """Upload should return a job envelope and job polling should surface the typed status payload."""
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    monkeypatch.setattr(api_module, "create_upload_job", lambda root: ("job999", root / "state" / "uploads" / "job999.epub"))
    monkeypatch.setattr(api_module, "provision_uploaded_book", lambda upload_path, language="auto", root=None: "demo-book")
    monkeypatch.setattr(
        api_module,
        "launch_sequential_job",
        lambda upload_path, root=None, book_id=None: {
            "job_id": "job999",
            "status": "queued",
            "upload_path": str(upload_path),
            "book_id": book_id,
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
    assert upload_response.json()["book_id"] == to_api_book_id("demo-book")
    assert upload_response.json()["ws_url"] == "/api/ws/jobs/job999"

    job_response = client.get("/api/jobs/job999")
    assert job_response.status_code == 200
    assert job_response.json()["book_id"] == to_api_book_id("demo-book")
    assert job_response.json()["status"] == "deep_reading"


def test_api_upload_deferred_returns_ready_job(tmp_path, monkeypatch):
    """Deferred uploads should launch parse-only work and return the ready job envelope."""
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    monkeypatch.setattr(api_module, "create_upload_job", lambda root: ("jobparse", root / "state" / "uploads" / "jobparse.epub"))
    monkeypatch.setattr(api_module, "provision_uploaded_book", lambda upload_path, language="auto", root=None: "demo-book")
    monkeypatch.setattr(
        api_module,
        "launch_parse_job",
        lambda upload_path, root=None, book_id=None: {
            "job_id": "jobparse",
            "status": "ready",
            "upload_path": str(upload_path),
            "book_id": book_id,
            "pid": None,
            "created_at": "2026-03-07T00:00:00Z",
            "updated_at": "2026-03-07T00:00:00Z",
            "error": None,
        },
    )

    upload_response = client.post(
        "/api/uploads/epub",
        data={"start_mode": "deferred"},
        files={"file": ("demo.epub", b"epub-bytes", "application/epub+zip")},
    )
    assert upload_response.status_code == 202
    assert upload_response.json()["status"] == "ready"
    assert upload_response.json()["book_id"] == to_api_book_id("demo-book")


def test_api_start_analysis_for_uploaded_book(tmp_path, monkeypatch):
    """Starting deep reading for a not-started book should return a new accepted job."""
    book_id = _bootstrap_book(tmp_path, stage="ready")
    public_book_id = to_api_book_id(book_id)
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    monkeypatch.setattr(
        api_module,
        "launch_book_analysis_job",
        lambda internal_book_id, root=None: {
            "job_id": "jobstart",
            "status": "queued",
            "upload_path": str((tmp_path / "output" / internal_book_id / "_assets" / "source.epub")),
            "book_id": internal_book_id,
            "pid": 456,
            "created_at": "2026-03-07T00:00:00Z",
            "updated_at": "2026-03-07T00:00:00Z",
            "error": None,
        },
    )

    response = client.post(f"/api/books/{public_book_id}/analysis/start")
    assert response.status_code == 202
    assert response.json()["job_id"] == "jobstart"
    assert response.json()["book_id"] == public_book_id


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
    assert first["payload"]["stage_label_key"] == "system.stage.deepReadingChapter"
    assert second["event_type"] in {"structure.ready", "activity.created"}
    assert third["event_type"] in {"activity.created", "heartbeat", "chapter.completed"}
