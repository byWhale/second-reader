"""Tests for managed library source intake."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

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


def test_discover_inbox_sources_filters_supported_layout(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    _write(paths.library_inbox_root / "en" / "private" / "batch_a" / "book_a.epub", "a")
    _write(paths.library_inbox_root / "en" / "private" / "batch_a" / "book_a.source.json", "{}")
    _write(paths.library_inbox_root / "en" / "private" / "batch_a" / "notes.txt", "ignored")
    _write(paths.library_inbox_root / "misc" / "book_b.epub", "bad")

    discovered, skipped = discover_inbox_sources(paths)

    assert [item.relative_path.as_posix() for item in discovered] == ["en/private/batch_a/book_a.epub"]
    assert any(item["status"] == "skipped_unsupported_extension" for item in skipped)
    assert any(item["status"] == "skipped_invalid_layout" for item in skipped)


def test_run_source_intake_copies_files_and_writes_catalog(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    source_path = paths.library_inbox_root / "en" / "private" / "batch_a" / "Steve Jobs.epub"
    _write(source_path, "demo epub bytes")
    _write_json(
        source_path.with_suffix(".source.json"),
        {
            "source_id": "steve_jobs_private_en",
            "title": "Steve Jobs",
            "author": "Walter Isaacson",
            "canonical_filename": "steve_jobs.epub",
            "type_tags": ["biography", "business"],
            "role_tags": ["narrative_reflective"],
            "notes": ["High-value biography source."],
        },
    )

    summary = run_source_intake(paths, run_id="run_a")

    assert summary["ingested_count"] == 1
    copied_path = paths.library_source_root / "en" / "private" / "steve_jobs.epub"
    assert copied_path.exists()

    catalog = load_catalog(paths.source_catalog_path)
    assert catalog["record_count"] == 1
    record = catalog["records"][0]
    assert record["source_id"] == "steve_jobs_private_en"
    assert record["title"] == "Steve Jobs"
    assert record["author"] == "Walter Isaacson"
    assert record["relative_local_path"] == "state/library_sources/en/private/steve_jobs.epub"
    assert record["parse_status"] == "not_started"
    assert record["screening_status"] == "not_started"
    assert record["packaging_status"] == "not_started"
    assert (paths.source_intake_runs_root / "run_a.json").exists()
    assert (paths.source_catalog_md_path).exists()


def test_reingest_same_hash_updates_existing_record_without_duplication(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    source_path = paths.library_inbox_root / "zh" / "private" / "batch_a" / "Book.epub"
    _write(source_path, "same bytes")

    first = run_source_intake(paths, run_id="run_first")
    assert first["ingested_count"] == 1

    _write_json(
        source_path.with_suffix(".source.json"),
        {
            "title": "走出唯一真理观",
            "author": "Unknown",
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
    assert record["seen_count"] == 2


def test_run_source_intake_dry_run_does_not_mutate_state(tmp_path: Path) -> None:
    paths = SourceIntakePaths.from_root(tmp_path)
    _write(paths.library_inbox_root / "en" / "public" / "batch_a" / "Walden.epub", "demo")

    summary = run_source_intake(paths, dry_run=True, run_id="dry_run")

    assert summary["ingested_count"] == 1
    assert not paths.source_catalog_path.exists()
    assert not (paths.library_source_root / "en" / "walden.epub").exists()
    assert not (paths.source_intake_runs_root / "dry_run.json").exists()


def test_ingest_library_sources_cli_supports_temp_root(tmp_path: Path) -> None:
    backend_root = Path(__file__).resolve().parents[1]
    _write(tmp_path / "state" / "library_inbox" / "en" / "private" / "batch_a" / "book.epub", "demo")

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
