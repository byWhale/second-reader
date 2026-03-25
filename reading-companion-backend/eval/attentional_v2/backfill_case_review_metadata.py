"""Backfill baseline review/provenance metadata onto curated excerpt datasets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TRACKED_DATASET_ROOT = ROOT / "eval" / "datasets"
LOCAL_DATASET_ROOT = ROOT / "state" / "eval_local_datasets"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object JSON at {path}")
    return payload


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError(f"Expected object row in {path}")
        rows.append(payload)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def root_for_storage(storage_mode: str) -> Path:
    if storage_mode == "tracked":
        return TRACKED_DATASET_ROOT
    if storage_mode == "local-only":
        return LOCAL_DATASET_ROOT
    raise ValueError(f"Unsupported storage_mode: {storage_mode}")


def normalize_rows(dataset_manifest: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        row.setdefault("review_status", "builder_curated")
        row.setdefault("benchmark_status", "builder_active")
        row.setdefault("review_history", [])
        row.setdefault(
            "case_provenance",
            {
                "dataset_id": str(dataset_manifest.get("dataset_id", "")),
                "dataset_version": str(dataset_manifest.get("version", "")),
                "language_track": str(dataset_manifest.get("language_track", "")),
                "family": str(dataset_manifest.get("family", "")),
                "storage_mode": str(dataset_manifest.get("storage_mode", "")),
                "source_policy": str(row.get("source_policy", "")),
                "source_id": str(row.get("source_id", "")),
                "source_manifest_refs": list(dataset_manifest.get("source_manifest_refs", [])),
                "split_refs": list(dataset_manifest.get("split_refs", [])),
            },
        )
        row.setdefault(
            "metadata_sync",
            {
                "last_synced_at": utc_now(),
                "sync_reason": "backfill_case_review_metadata",
                "case_id": case_id,
            },
        )
        normalized.append(row)
    return normalized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--family", default="excerpt_cases")
    parser.add_argument("--storage-mode", default="tracked")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dataset_dir = root_for_storage(args.storage_mode) / args.family / args.dataset_id
    dataset_manifest = load_json(dataset_dir / "manifest.json")
    primary_file = str(dataset_manifest.get("primary_file", "")).strip()
    if not primary_file:
        raise ValueError(f"Dataset manifest missing primary_file: {dataset_dir / 'manifest.json'}")
    rows = load_jsonl(dataset_dir / primary_file)
    updated_rows = normalize_rows(dataset_manifest, rows)
    write_jsonl(dataset_dir / primary_file, updated_rows)
    print(
        json.dumps(
            {
                "status": "ok",
                "dataset_id": args.dataset_id,
                "row_count": len(updated_rows),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
