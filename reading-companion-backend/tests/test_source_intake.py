"""Tests for managed library source intake."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from ebooklib import epub

from eval.attentional_v2.ingest_library_sources import (
    SourceIntakePaths,
    discover_inbox_sources,
    load_catalog,
    run_source_intake,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    _write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def _write_epub(path: Path, *, title: str, language: str, chapter_text: str, author: str = "Unknown") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    book = epub.EpubBook()
    book.set_identifier(f"id-{title}-{language}")
    book.set_title(title)
    book.set_language(language)
    book.add_author(author)

    chapter = epub.EpubHtml(title="Chapter 1", file_name="chapter_1.xhtml", lang=language)
    chapter.content = f"<h1>{title}</h1><p>{chapter_text}</p>"
    book.add_item(chapter)
    book.toc = (chapter,)
    book.spine = ["nav", chapter]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(str(path), book)


def test_discover_inbox_sources_supports_single_inbox_and_nested_batches(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    _write(paths.library_inbox_root / "batch_a" / "book_a.epub", "a")
    _write(paths.library_inbox_root / "2026-03-29" / "english" / "book_b.epub", "b")
    _write(paths.library_inbox_root / "notes.txt", "ignored")

    discovered, skipped = discover_inbox_sources(paths)

    assert [item.relative_path.as_posix() for item in discovered] == [
        "2026-03-29/english/book_b.epub",
        "batch_a/book_a.epub",
    ]
    assert all(item["status"] != "skipped_invalid_layout" for item in skipped)
    assert any(item["status"] == "skipped_unsupported_extension" for item in skipped)


def test_run_source_intake_copies_files_and_writes_catalog_with_private_default(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    source_path = paths.library_inbox_root / "2026-03-29" / "english" / "Steve Jobs.epub"
    _write(source_path, "demo epub bytes")
    _write_json(
        source_path.with_suffix(".source.json"),
        {
            "source_id": "steve_jobs_private_en",
            "title": "Steve Jobs",
            "author": "Walter Isaacson",
            "canonical_filename": "steve_jobs.epub",
            "language": "en",
            "type_tags": ["biography", "business"],
            "role_tags": ["narrative_reflective"],
            "notes": ["High-value biography source."],
        },
    )

    summary = run_source_intake(paths, run_id="run_a")

    assert summary["candidate_count"] == 1
    assert summary["ingested_count"] == 1
    copied_path = paths.library_source_root / "en" / "steve_jobs.epub"
    assert copied_path.exists()

    catalog = load_catalog(paths.source_catalog_path)
    assert catalog["record_count"] == 1
    record = catalog["records"][0]
    assert record["source_id"] == "steve_jobs_private_en"
    assert record["title"] == "Steve Jobs"
    assert record["author"] == "Walter Isaacson"
    assert record["language"] == "en"
    assert record["visibility"] == "private"
    assert record["relative_local_path"] == "state/library_sources/en/steve_jobs.epub"
    assert record["ingest_batch_ids"] == ["2026-03-29/english"]
    assert record["parse_status"] == "not_started"
    assert record["screening_status"] == "not_started"
    assert record["packaging_status"] == "not_started"
    assert (paths.source_intake_runs_root / "run_a.json").exists()
    assert paths.source_catalog_md_path.exists()


def test_run_source_intake_auto_detects_language_for_english_and_chinese_epubs(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    _write_epub(
        paths.library_inbox_root / "drop_a" / "Walden.epub",
        title="Walden",
        language="en",
        chapter_text="Where I lived, and what I lived for.",
    )
    _write_epub(
        paths.library_inbox_root / "drop_b" / "朝花夕拾.epub",
        title="朝花夕拾",
        language="zh",
        chapter_text="我不知道为什么家里的人要将我送进书塾里去了。",
    )

    summary = run_source_intake(paths, run_id="auto_lang")

    assert summary["candidate_count"] == 2
    assert summary["ingested_count"] == 2
    assert (paths.library_source_root / "en" / "walden.epub").exists()
    assert (paths.library_source_root / "zh" / "朝花夕拾.epub").exists()

    records = {record["title"]: record for record in load_catalog(paths.source_catalog_path)["records"]}
    assert records["Walden"]["language"] == "en"
    assert records["朝花夕拾"]["language"] == "zh"
    assert records["Walden"]["visibility"] == "private"
    assert records["朝花夕拾"]["visibility"] == "private"


def test_run_source_intake_keeps_visibility_only_as_metadata_and_uses_shared_path(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    source_path = paths.library_inbox_root / "public_candidates" / "Walden.epub"
    _write(source_path, "demo epub bytes")
    _write_json(
        source_path.with_suffix(".source.json"),
        {
            "title": "Walden",
            "canonical_filename": "walden.epub",
            "language": "en",
            "visibility": "public",
        },
    )

    summary = run_source_intake(paths, run_id="public_run")

    assert summary["ingested_count"] == 1
    assert (paths.library_source_root / "en" / "walden.epub").exists()
    record = load_catalog(paths.source_catalog_path)["records"][0]
    assert record["visibility"] == "public"
    assert record["relative_local_path"] == "state/library_sources/en/walden.epub"


def test_run_source_intake_default_source_id_no_longer_bakes_visibility_into_identifier(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    source_path = paths.library_inbox_root / "batch_a" / "Walden.epub"
    _write(source_path, "demo")
    _write_json(
        source_path.with_suffix(".source.json"),
        {
            "title": "Walden",
            "language": "en",
        },
    )

    run_source_intake(paths, run_id="source_id_default")

    record = load_catalog(paths.source_catalog_path)["records"][0]
    assert record["source_id"] == "walden_en"


def test_reingest_same_hash_updates_existing_record_without_duplication(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    source_path = paths.library_inbox_root / "drop_zh" / "Book.epub"
    _write_epub(
        source_path,
        title="Book",
        language="zh",
        chapter_text="走出唯一真理观的一个章节片段。",
    )

    first = run_source_intake(paths, run_id="run_first")
    assert first["ingested_count"] == 1

    _write_json(
        source_path.with_suffix(".source.json"),
        {
            "title": "走出唯一真理观",
            "author": "Unknown",
            "language": "zh",
            "type_tags": ["social_thought"],
            "notes": ["Added later."],
        },
    )
    second = run_source_intake(paths, run_id="run_second")

    assert second["existing_count"] == 1
    catalog = load_catalog(paths.source_catalog_path)
    assert catalog["record_count"] == 1
    record = catalog["records"][0]
    assert record["title"] == "走出唯一真理观"
    assert record["author"] == "Unknown"
    assert record["type_tags"] == ["social_thought"]
    assert record["language"] == "zh"
    assert record["seen_count"] == 2


def test_run_source_intake_dry_run_does_not_mutate_state(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    source_path = paths.library_inbox_root / "batch_a" / "Walden.epub"
    _write(source_path, "demo")
    _write_json(
        source_path.with_suffix(".source.json"),
        {
            "title": "Walden",
            "language": "en",
        },
    )

    summary = run_source_intake(paths, dry_run=True, run_id="dry_run")

    assert summary["candidate_count"] == 1
    assert summary["ingested_count"] == 1
    assert not paths.source_catalog_path.exists()
    assert not (paths.library_source_root / "en" / "walden.epub").exists()
    assert not (paths.source_intake_runs_root / "dry_run.json").exists()


def test_ingest_library_sources_cli_supports_temp_root(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    source_path = tmp_path / "state" / "library_inbox" / "batch_a" / "book.epub"
    _write(source_path, "demo")
    _write_json(
        source_path.with_suffix(".source.json"),
        {
            "language": "en",
        },
    )

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "eval.attentional_v2.ingest_library_sources",
            "--root",
            str(tmp_path),
            "--run-id",
            "cli_run",
        ],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    assert payload["run_id"] == "cli_run"
    assert payload["ingested_count"] == 1
    assert (tmp_path / "state" / "dataset_build" / "source_catalog.json").exists()
