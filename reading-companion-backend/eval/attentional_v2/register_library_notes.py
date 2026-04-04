#!/usr/bin/env python3
"""Register raw notes exports into managed local notes storage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.attentional_v2.library_notes import (
    LibraryNotesPaths,
    register_notes_asset,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(ROOT), help="Backend root that owns state/library_notes.")
    parser.add_argument(
        "--source-catalog",
        default="",
        help="Optional source catalog path. Defaults to state/dataset_build/source_catalog.json under --root.",
    )
    parser.add_argument("--notes-id", required=True, help="Stable notes asset id.")
    parser.add_argument("--linked-source-id", required=True, help="Managed source id from source_catalog.json.")
    parser.add_argument("--title", required=True, help="Display title for the notes asset.")
    parser.add_argument("--language", required=True, help="Language code for the notes asset.")
    parser.add_argument("--origin-path", required=True, help="Raw notes export path to register.")
    parser.add_argument("--notes-format", choices=["auto", "google_books_markdown", "wechat_markdown"], default="auto")
    parser.add_argument("--structure-mode", default="", help="Optional explicit structure mode.")
    parser.add_argument("--status", default="active", help="Operator status label for the notes asset.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.root).expanduser().resolve()
    paths = LibraryNotesPaths.from_root(root)
    source_catalog_path = (
        Path(args.source_catalog).expanduser().resolve()
        if str(args.source_catalog).strip()
        else root / "state" / "dataset_build" / "source_catalog.json"
    )
    result = register_notes_asset(
        paths,
        notes_id=args.notes_id,
        linked_source_id=args.linked_source_id,
        title=args.title,
        language=args.language,
        notes_format=args.notes_format,
        origin_path=Path(args.origin_path).expanduser().resolve(),
        structure_mode=args.structure_mode,
        status=args.status,
        source_catalog_path=source_catalog_path,
        title_hint=args.title,
    )

    payload = {
        "registered_asset_count": 1,
        "results": [
            {
                "notes_id": result["asset"]["notes_id"],
                "linked_source_id": result["asset"]["linked_source_id"],
                "source_link_status": result["asset"]["source_link_status"],
                "entry_count": result["asset"]["entry_count"],
                "aligned_entry_count": result["asset"]["aligned_entry_count"],
                "relative_notes_path": result["asset"]["relative_notes_path"],
                "entries_rel_path": result["asset"]["entries_rel_path"],
            }
        ],
        "notes_catalog_json": str(paths.notes_catalog_json_path),
        "notes_catalog_md": str(paths.notes_catalog_md_path),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
