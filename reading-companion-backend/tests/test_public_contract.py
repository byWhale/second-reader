"""Contract-focused tests for the public API boundary."""

from __future__ import annotations

import importlib
import json
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.contract import (
    MARK_TYPES,
    REACTION_FILTERS,
    REACTION_TYPES,
    resolve_book_id,
    resolve_mark_id,
    resolve_reaction_id,
    to_api_book_id,
    to_api_mark_id,
    to_api_reaction_id,
)


api_module = importlib.import_module("src.api.app")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(f"{path.suffix}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def _append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False))
        handle.write("\n")


def _bootstrap_contract_book(
    root: Path,
    *,
    stage: str = "completed",
    include_activity: bool = True,
    reaction_type: str = "retrospect",
) -> str:
    book_id = "contract-book"
    output_dir = root / "output" / book_id
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        output_dir / "book_manifest.json",
        {
            "book_id": book_id,
            "book": "Contract Book",
            "author": "Contract Tester",
            "cover_image_url": None,
            "book_language": "en",
            "output_language": "en",
            "source_file": str((root / "state" / "uploads" / "job123.epub").resolve()),
            "source_asset": {"format": "epub", "file": "_assets/source.epub"},
            "updated_at": "2026-03-08T00:00:00Z",
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
            "book": "Contract Book",
            "current_chapter_id": None if stage == "completed" else 1,
            "current_chapter_ref": None if stage == "completed" else "Chapter 1",
            "current_segment_ref": None if stage == "completed" else "1.1",
            "completed_chapters": 1 if stage == "completed" else 0,
            "total_chapters": 1,
            "eta_seconds": 0 if stage == "completed" else 30,
            "updated_at": "2026-03-08T00:00:00Z",
            "error": None,
        },
    )
    (output_dir / "activity.jsonl").write_text("", encoding="utf-8")
    if include_activity:
        _append_jsonl(
            output_dir / "activity.jsonl",
            {
                "event_id": "contract-evt-1",
                "timestamp": "2026-03-08T00:00:00Z",
                "type": "chapter_completed",
                "message": "Chapter 1 完成，已生成结果文件。",
                "chapter_id": 1,
                "chapter_ref": "Chapter 1",
                "reaction_types": [reaction_type],
                "highlight_quote": "Legacy retrospect quote" if reaction_type == "retrospect" else "Legacy connect-back quote",
                "visible_reaction_count": 1,
                "featured_reactions": [
                    {
                        "reaction_id": "r1",
                        "type": reaction_type,
                        "segment_ref": "1.1",
                        "anchor_quote": "Legacy retrospect quote" if reaction_type == "retrospect" else "Legacy connect-back quote",
                        "content": "This uses the current public name." if reaction_type == "retrospect" else "This still uses the internal legacy name.",
                        "target_locator": {
                            "href": "chapter-1.xhtml",
                            "start_cfi": "epubcfi(/6/2!/4/2)",
                            "end_cfi": "epubcfi(/6/2!/4/2)",
                            "match_text": "Legacy retrospect quote" if reaction_type == "retrospect" else "Legacy connect-back quote",
                            "match_mode": "exact",
                        },
                    }
                ],
            },
        )
    if stage == "completed":
        _write_json(
            output_dir / "ch01_deep_read.json",
            {
                "book_title": "Contract Book",
                "chapter": {
                    "id": 1,
                    "title": "Chapter 1",
                    "chapter_number": 1,
                    "reference": "Chapter 1",
                    "status": "done",
                },
                "output_language": "en",
                "generated_at": "2026-03-08T00:00:00Z",
                "sections": [
                    {
                        "segment_id": "1.1",
                        "segment_ref": "1.1",
                        "summary": "A section with one callback-style reaction.",
                        "original_text": "Legacy retrospect quote" if reaction_type == "retrospect" else "Legacy connect-back quote",
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
                                "type": reaction_type,
                                "anchor_quote": "Legacy retrospect quote" if reaction_type == "retrospect" else "Legacy connect-back quote",
                                "content": "This uses the current public name." if reaction_type == "retrospect" else "This still uses the internal legacy name.",
                                "search_query": "",
                                "search_results": [],
                                "target_locator": {
                                    "href": "chapter-1.xhtml",
                                    "start_cfi": "epubcfi(/6/2!/4/2)",
                                    "end_cfi": "epubcfi(/6/2!/4/2)",
                                    "match_text": "Legacy retrospect quote" if reaction_type == "retrospect" else "Legacy connect-back quote",
                                    "match_mode": "exact",
                                },
                        }
                    ],
                }
            ],
            "chapter_heading": {
                "label": "Chapter 1",
                "title": "Contract framing",
                "text": "Chapter 1\nContract framing",
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
                    "type": reaction_type,
                        "segment_ref": "1.1",
                        "anchor_quote": "Legacy retrospect quote" if reaction_type == "retrospect" else "Legacy connect-back quote",
                        "content": "This uses the current public name." if reaction_type == "retrospect" else "This still uses the internal legacy name.",
                        "target_locator": {
                            "href": "chapter-1.xhtml",
                            "start_cfi": "epubcfi(/6/2!/4/2)",
                            "end_cfi": "epubcfi(/6/2!/4/2)",
                            "match_text": "Legacy retrospect quote" if reaction_type == "retrospect" else "Legacy connect-back quote",
                            "match_mode": "exact",
                        },
                    }
                ],
                "visible_reaction_count": 1,
                "reaction_type_diversity": 1,
                "ui_summary": {
                    "kept_section_count": 1,
                    "skipped_section_count": 0,
                    "reaction_counts": {reaction_type: 1},
                },
            },
        )
    asset_dir = output_dir / "_assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / "source.epub").write_bytes(b"epub")
    return book_id


def _migrate_contract_book_to_public_layout(root: Path, book_id: str) -> None:
    """Re-home a legacy test book into the current public/runtime layout."""
    output_dir = root / "output" / book_id
    public_dir = output_dir / "public"
    chapters_dir = public_dir / "chapters"
    runtime_dir = output_dir / "_runtime"
    public_dir.mkdir(parents=True, exist_ok=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "book_manifest.json").replace(public_dir / "book_manifest.json")
    (output_dir / "run_state.json").replace(runtime_dir / "run_state.json")
    (output_dir / "activity.jsonl").replace(runtime_dir / "activity.jsonl")

    chapter_result = output_dir / "ch01_deep_read.json"
    if chapter_result.exists():
        chapter_result.replace(chapters_dir / "ch01_deep_read.json")


def test_openapi_public_snapshot_and_key_contracts(tmp_path):
    """OpenAPI should stay aligned with the committed public contract snapshot."""
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    current = client.get("/openapi.json").json()
    snapshot_path = Path(__file__).resolve().parents[2] / "contract" / "openapi.public.snapshot.json"
    assert current == json.loads(snapshot_path.read_text(encoding="utf-8"))

    paths = current["paths"]
    assert "/api/landing" not in paths
    assert "/api/sample" not in paths
    assert "/api/books/{book_id}/chapters/{chapter_id}/outline" in paths

    schemas = current["components"]["schemas"]
    mark_record = schemas["MarkRecord"]
    assert mark_record["properties"]["mark_id"]["type"] == "integer"
    assert mark_record["properties"]["reaction_id"]["type"] == "integer"
    assert mark_record["properties"]["book_id"]["type"] == "integer"

    reaction_card = schemas["ReactionCard"]
    assert reaction_card["properties"]["type"]["enum"] == list(REACTION_TYPES)
    assert reaction_card["properties"]["primary_anchor"]["anyOf"][0]["$ref"] == "#/components/schemas/ReactionAnchor"
    assert reaction_card["properties"]["related_anchors"]["items"]["$ref"] == "#/components/schemas/ReactionAnchor"

    chapter_detail = schemas["ChapterDetailResponse"]
    assert chapter_detail["properties"]["available_filters"]["items"]["enum"] == REACTION_FILTERS
    assert chapter_detail["properties"]["chapter_heading"]["anyOf"][0]["$ref"] == "#/components/schemas/ChapterHeadingBlock"

    chapter_outline = schemas["ChapterOutlineResponse"]
    assert chapter_outline["properties"]["status"]["enum"] == ["pending", "completed", "error"]
    assert chapter_outline["properties"]["chapter_heading"]["anyOf"][0]["$ref"] == "#/components/schemas/ChapterHeadingBlock"
    outline_section = schemas["ChapterOutlineSectionItem"]
    assert outline_section["properties"]["visible_reaction_count"]["type"] == "integer"

    current_activity = schemas["CurrentReadingActivity"]
    assert current_activity["properties"]["reading_locus"]["anyOf"][0]["$ref"] == "#/components/schemas/ReadingLocus"
    assert current_activity["properties"]["move_type"]["anyOf"][0]["enum"] == ["advance", "dwell", "bridge", "reframe"]

    expected_status_reason_enum = [
        "runtime_stale",
        "runtime_interrupted",
        "resume_incompatible",
        "dev_run_abandoned",
    ]
    assert schemas["BookShelfCard"]["properties"]["status_reason"]["anyOf"][0]["enum"] == expected_status_reason_enum
    assert schemas["BookDetailResponse"]["properties"]["status_reason"]["anyOf"][0]["enum"] == expected_status_reason_enum
    assert schemas["AnalysisStateResponse"]["properties"]["status_reason"]["anyOf"][0]["enum"] == expected_status_reason_enum
    assert schemas["JobStatusResponse"]["properties"]["status_reason"]["anyOf"][0]["enum"] == expected_status_reason_enum

    mark_record = schemas["MarkRecord"]
    assert mark_record["properties"]["primary_anchor"]["anyOf"][0]["$ref"] == "#/components/schemas/ReactionAnchor"

    set_mark_request = schemas["SetMarkRequest"]
    assert set_mark_request["properties"]["mark_type"]["enum"] == list(MARK_TYPES)


def test_rest_payloads_scrub_legacy_names_and_routes(tmp_path):
    """REST responses should normalize legacy names and expose canonical routes only."""
    book_id = _bootstrap_contract_book(tmp_path)
    public_book_id = to_api_book_id(book_id)
    public_reaction_id = to_api_reaction_id(book_id=book_id, reaction_id="r1")
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    put_response = client.put(
        f"/api/marks/{public_reaction_id}",
        json={"book_id": public_book_id, "mark_type": "resonance"},
    )
    assert put_response.status_code == 200

    payloads = {
        "books": client.get("/api/books").json(),
        "book": client.get(f"/api/books/{public_book_id}").json(),
        "analysis": client.get(f"/api/books/{public_book_id}/analysis-state").json(),
        "activity": client.get(f"/api/books/{public_book_id}/activity").json(),
        "chapter": client.get(f"/api/books/{public_book_id}/chapters/1").json(),
        "book_marks": client.get(f"/api/books/{public_book_id}/marks").json(),
        "marks": client.get("/api/marks").json(),
    }

    assert payloads["book"]["reaction_counts"] == {reaction_type: (1 if reaction_type == "retrospect" else 0) for reaction_type in REACTION_TYPES}
    assert payloads["analysis"]["current_state_panel"]["reaction_counts"] == {
        reaction_type: (1 if reaction_type == "retrospect" else 0)
        for reaction_type in REACTION_TYPES
    }
    assert payloads["chapter"]["available_filters"] == REACTION_FILTERS

    mark_item = payloads["marks"]["items"][0]
    assert set(mark_item).issuperset(
        {
            "mark_id",
            "reaction_id",
            "book_id",
            "chapter_id",
            "mark_type",
            "reaction_type",
            "anchor_quote",
            "created_at",
        }
    )
    assert mark_item["primary_anchor"]["quote"] == "Legacy retrospect quote"

    error_payload = client.get("/api/books/999999999").json()
    assert set(error_payload) == {"error_id", "code", "message", "status", "retryable", "details"}

    serialized = json.dumps(payloads, ensure_ascii=False, sort_keys=True)
    for banned in ["connect_back", "critique", "curiosity", "insight", "/bookshelf", "/book/", "/analysis/"]:
        assert banned not in serialized


def test_legacy_connect_back_still_normalizes_to_retrospect(tmp_path):
    """Old connect_back artifacts should remain readable through the public API."""
    book_id = _bootstrap_contract_book(tmp_path, reaction_type="connect_back")
    public_book_id = to_api_book_id(book_id)
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    chapter_payload = client.get(f"/api/books/{public_book_id}/chapters/1").json()
    activity_payload = client.get(f"/api/books/{public_book_id}/activity").json()

    assert chapter_payload["featured_reactions"][0]["type"] == "retrospect"
    assert chapter_payload["featured_reactions"][0]["primary_anchor"]["quote"] == "Legacy connect-back quote"
    assert chapter_payload["sections"][0]["reactions"][0]["type"] == "retrospect"
    assert activity_payload["items"][0]["reaction_types"] == ["retrospect"]
    assert activity_payload["items"][0]["featured_reactions"][0]["type"] == "retrospect"


def test_websocket_payloads_scrub_legacy_names_and_routes(tmp_path):
    """WebSocket envelopes should also stay normalized at the public boundary."""
    book_id = _bootstrap_contract_book(tmp_path, stage="deep_reading", include_activity=False)
    public_book_id = to_api_book_id(book_id)
    api_module.app.state.root = tmp_path
    api_module.app.state.ws_poll_interval = 0.05
    api_module.app.state.ws_heartbeat_interval = 0.2
    client = TestClient(api_module.app)

    def complete_run() -> None:
        time.sleep(0.15)
        output_dir = tmp_path / "output" / book_id
        _write_json(
            output_dir / "ch01_deep_read.json",
            {
                "book_title": "Contract Book",
                "chapter": {
                    "id": 1,
                    "title": "Chapter 1",
                    "chapter_number": 1,
                    "reference": "Chapter 1",
                    "status": "done",
                },
                "output_language": "en",
                "generated_at": "2026-03-08T00:00:01Z",
                "sections": [
                    {
                        "segment_id": "1.1",
                        "segment_ref": "1.1",
                        "summary": "A section with one callback-style reaction.",
                        "original_text": "Legacy retrospect quote",
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
                                "type": "retrospect",
                                "anchor_quote": "Legacy retrospect quote",
                                "content": "This uses the current public name.",
                                "search_query": "",
                                "search_results": [],
                                "target_locator": {
                                    "href": "chapter-1.xhtml",
                                    "start_cfi": "epubcfi(/6/2!/4/2)",
                                    "end_cfi": "epubcfi(/6/2!/4/2)",
                                    "match_text": "Legacy retrospect quote",
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
                        "type": "retrospect",
                        "segment_ref": "1.1",
                        "anchor_quote": "Legacy retrospect quote",
                        "content": "This uses the current public name.",
                        "target_locator": {
                            "href": "chapter-1.xhtml",
                            "start_cfi": "epubcfi(/6/2!/4/2)",
                            "end_cfi": "epubcfi(/6/2!/4/2)",
                            "match_text": "Legacy retrospect quote",
                            "match_mode": "exact",
                        },
                    }
                ],
                "visible_reaction_count": 1,
                "reaction_type_diversity": 1,
                "ui_summary": {
                    "kept_section_count": 1,
                    "skipped_section_count": 0,
                    "reaction_counts": {"retrospect": 1},
                },
            },
        )
        manifest = json.loads((output_dir / "book_manifest.json").read_text(encoding="utf-8"))
        manifest["chapters"][0]["status"] = "done"
        manifest["chapters"][0]["visible_reaction_count"] = 1
        manifest["chapters"][0]["reaction_type_diversity"] = 1
        _write_json(output_dir / "book_manifest.json", manifest)
        _write_json(
            output_dir / "run_state.json",
            {
                "mode": "sequential",
                "stage": "completed",
                "book": "Contract Book",
                "current_chapter_id": None,
                "current_chapter_ref": None,
                "current_segment_ref": None,
                "completed_chapters": 1,
                "total_chapters": 1,
                "eta_seconds": 0,
                "updated_at": "2026-03-08T00:00:01Z",
                "error": None,
            },
        )
        _append_jsonl(
            output_dir / "activity.jsonl",
            {
                "event_id": "contract-evt-2",
                "timestamp": "2026-03-08T00:00:01Z",
                "type": "chapter_completed",
                "message": "Chapter 1 完成，已生成结果文件。",
                "chapter_id": 1,
                "chapter_ref": "Chapter 1",
                "reaction_types": ["retrospect"],
                "highlight_quote": "Legacy retrospect quote",
                "visible_reaction_count": 1,
                "featured_reactions": [
                    {
                        "reaction_id": "r1",
                        "type": "retrospect",
                        "segment_ref": "1.1",
                        "anchor_quote": "Legacy retrospect quote",
                        "content": "This uses the current public name.",
                        "target_locator": {
                            "href": "chapter-1.xhtml",
                            "start_cfi": "epubcfi(/6/2!/4/2)",
                            "end_cfi": "epubcfi(/6/2!/4/2)",
                            "match_text": "Legacy retrospect quote",
                            "match_mode": "exact",
                        },
                    }
                ],
            },
        )

    threading.Thread(target=complete_run, daemon=True).start()

    received: list[dict] = []
    with client.websocket_connect(f"/api/ws/books/{public_book_id}/analysis") as websocket:
        for _ in range(8):
            payload = websocket.receive_json()
            received.append(payload)
            event_types = {item.get("event_type") for item in received}
            if {"activity.created", "chapter.completed", "book.completed"}.issubset(event_types):
                break

    serialized = json.dumps(received, ensure_ascii=False, sort_keys=True)
    for banned in ["connect_back", "critique", "curiosity", "insight", "/bookshelf", "/book/", "/analysis/"]:
        assert banned not in serialized
    assert any(item["event_type"] == "activity.created" for item in received)
    assert any(item["event_type"] == "chapter.completed" for item in received)
    assert any(item["event_type"] == "book.completed" for item in received)


def test_public_integer_ids_are_stable_and_resolvable(tmp_path):
    """Public integer ids should be stable and reversible without changing storage internals."""
    book_id = _bootstrap_contract_book(tmp_path)

    public_book_id = to_api_book_id(book_id)
    public_reaction_id = to_api_reaction_id(book_id=book_id, reaction_id="r1")
    public_mark_id = to_api_mark_id(book_id=book_id, reaction_id="r1")

    assert public_book_id == to_api_book_id(book_id)
    assert public_reaction_id == to_api_reaction_id(book_id=book_id, reaction_id="r1")
    assert public_mark_id == to_api_mark_id(book_id=book_id, reaction_id="r1")

    assert resolve_book_id(public_book_id, root=tmp_path) == book_id
    assert resolve_reaction_id(public_reaction_id, root=tmp_path, internal_book_id=book_id) == "r1"
    assert resolve_mark_id(public_mark_id, root=tmp_path) == (book_id, "r1")


def test_public_integer_ids_resolve_from_current_public_layout(tmp_path):
    """Public ids should also resolve when artifacts only exist in the current public/runtime directories."""
    book_id = _bootstrap_contract_book(tmp_path)
    _migrate_contract_book_to_public_layout(tmp_path, book_id)

    public_book_id = to_api_book_id(book_id)
    public_reaction_id = to_api_reaction_id(book_id=book_id, reaction_id="r1")
    public_mark_id = to_api_mark_id(book_id=book_id, reaction_id="r1")

    assert resolve_book_id(public_book_id, root=tmp_path) == book_id
    assert resolve_reaction_id(public_reaction_id, root=tmp_path, internal_book_id=book_id) == "r1"
    assert resolve_mark_id(public_mark_id, root=tmp_path) == (book_id, "r1")


def test_rest_payloads_work_from_current_public_layout(tmp_path):
    """Book detail, chapter detail, and mark routes should work against the current artifact layout."""
    book_id = _bootstrap_contract_book(tmp_path)
    _migrate_contract_book_to_public_layout(tmp_path, book_id)
    public_book_id = to_api_book_id(book_id)
    public_reaction_id = to_api_reaction_id(book_id=book_id, reaction_id="r1")
    api_module.app.state.root = tmp_path
    client = TestClient(api_module.app)

    assert client.get(f"/api/books/{public_book_id}").status_code == 200
    assert client.get(f"/api/books/{public_book_id}/analysis-state").status_code == 200
    assert client.get(f"/api/books/{public_book_id}/activity").status_code == 200
    assert client.get(f"/api/books/{public_book_id}/chapters/1").status_code == 200

    put_response = client.put(
        f"/api/marks/{public_reaction_id}",
        json={"book_id": public_book_id, "mark_type": "bookmark"},
    )
    assert put_response.status_code == 200
    assert put_response.json()["mark_type"] == "bookmark"
