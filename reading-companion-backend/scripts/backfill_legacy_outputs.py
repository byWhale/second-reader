#!/usr/bin/env python3
"""Backfill frontend-facing artifacts for legacy output directories."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.iterator_reader.frontend_artifacts import (  # noqa: E402
    append_activity_event,
    build_run_state,
    reset_activity,
    write_book_manifest,
    write_run_state,
)
from src.iterator_reader.parse import _extract_epub_cover  # noqa: E402
from src.iterator_reader.storage import (  # noqa: E402
    activity_file,
    book_manifest_file,
    chapter_reference,
    ensure_source_asset,
    run_state_file,
    structure_file,
)


def _load_structure(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _infer_run_state(structure: dict) -> dict:
    chapters = list(structure.get("chapters", []))
    total = len(chapters)
    completed = sum(1 for chapter in chapters if str(chapter.get("status", "")).strip() == "done")
    current = next((chapter for chapter in chapters if str(chapter.get("status", "")).strip() == "in_progress"), None)
    if current is None and 0 < completed < total:
        current = next((chapter for chapter in chapters if str(chapter.get("status", "")).strip() != "done"), None)

    if total > 0 and completed == total:
        stage = "completed"
    elif current is not None:
        stage = "deep_reading"
    else:
        stage = "ready"

    return build_run_state(
        structure,
        stage=stage,
        total_chapters=total,
        completed_chapters=completed,
        current_chapter_id=(int(current.get("id", 0)) if current is not None else None),
        current_chapter_ref=(chapter_reference(current) if current is not None else None),
    )


def _ensure_assets(output_dir: Path, structure: dict) -> list[str]:
    changes: list[str] = []
    source_file = str(structure.get("source_file", "") or "").strip()
    if not source_file:
        return changes

    source_path = Path(source_file)
    if not source_path.exists():
        return changes

    asset_path = ensure_source_asset(source_path, output_dir)
    if asset_path.exists():
        changes.append("source_asset")

    if source_path.suffix.lower() == ".epub":
        cover_path = _extract_epub_cover(source_path, output_dir)
        if cover_path is not None and cover_path.exists():
            changes.append("cover_asset")

    return changes


def backfill_output_dir(output_dir: Path) -> list[str]:
    changes: list[str] = []
    structure_path = structure_file(output_dir)
    if not structure_path.exists():
        return changes

    structure = _load_structure(structure_path)
    changes.extend(_ensure_assets(output_dir, structure))

    manifest_path = book_manifest_file(output_dir)
    if not manifest_path.exists():
        write_book_manifest(output_dir, structure)
        changes.append("book_manifest")

    state_path = run_state_file(output_dir)
    if not state_path.exists():
        write_run_state(output_dir, _infer_run_state(structure))
        changes.append("run_state")

    stream_path = activity_file(output_dir)
    if not stream_path.exists():
        reset_activity(output_dir)
        append_activity_event(
            output_dir,
            {
                "type": "structure_ready",
                "message": "Legacy artifacts were backfilled for workspace runtime compatibility.",
            },
        )
        changes.append("activity")

    return changes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill legacy frontend-facing output artifacts.")
    parser.add_argument(
        "--root",
        default=str(ROOT),
        help="Backend runtime root that contains output/ and state/ directories.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runtime_root = Path(args.root).resolve()
    output_root = runtime_root / "output"
    if not output_root.exists():
        print(f"No output directory found at {output_root}.")
        return 0

    touched = 0
    for structure_path in sorted(output_root.glob("*/structure.json")):
        output_dir = structure_path.parent
        changes = backfill_output_dir(output_dir)
        if not changes:
            continue
        touched += 1
        print(f"{output_dir.name}: {', '.join(changes)}")

    if touched == 0:
        print("No legacy output backfill needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
