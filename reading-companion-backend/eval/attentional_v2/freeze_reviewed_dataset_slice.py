"""Freeze a reviewed subset of a dataset into a new dataset package."""

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


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dataset-id", required=True)
    parser.add_argument("--target-dataset-id", required=True)
    parser.add_argument("--family", default="excerpt_cases")
    parser.add_argument("--storage-mode", default="tracked")
    parser.add_argument("--include-status", action="append", default=["reviewed_active"])
    parser.add_argument("--allow-empty", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = root_for_storage(args.storage_mode)
    source_dir = root / args.family / args.source_dataset_id
    target_dir = root / args.family / args.target_dataset_id
    if target_dir.exists():
        raise FileExistsError(f"Target dataset already exists: {target_dir}")

    source_manifest = load_json(source_dir / "manifest.json")
    primary_file = str(source_manifest.get("primary_file", "")).strip()
    if not primary_file:
        raise ValueError(f"Source dataset missing primary_file: {source_dir / 'manifest.json'}")
    source_rows = load_jsonl(source_dir / primary_file)
    include_status = {item.strip() for item in args.include_status if item.strip()}
    selected_rows = [row for row in source_rows if str(row.get("benchmark_status", "")).strip() in include_status]
    if not selected_rows and not args.allow_empty:
        raise ValueError("No rows selected for reviewed slice")

    target_manifest = dict(source_manifest)
    target_manifest["dataset_id"] = args.target_dataset_id
    target_manifest["description"] = f"Reviewed slice frozen from {args.source_dataset_id}."
    target_manifest["derived_from_dataset_id"] = args.source_dataset_id
    target_manifest["frozen_at"] = utc_now()
    target_manifest["freeze_criteria"] = {
        "include_status": sorted(include_status),
    }
    target_manifest["review_queue_summary"] = {
        "row_count": len(selected_rows),
        "review_status_counts": {},
        "benchmark_status_counts": {},
    }

    for row in selected_rows:
        row["freeze_metadata"] = {
            "frozen_from_dataset_id": args.source_dataset_id,
            "frozen_at": target_manifest["frozen_at"],
            "benchmark_status_at_freeze": str(row.get("benchmark_status", "")),
            "review_status_at_freeze": str(row.get("review_status", "")),
        }
        review_status = str(row.get("review_status", "")).strip() or "missing"
        benchmark_status = str(row.get("benchmark_status", "")).strip() or "missing"
        target_manifest["review_queue_summary"]["review_status_counts"][review_status] = (
            target_manifest["review_queue_summary"]["review_status_counts"].get(review_status, 0) + 1
        )
        target_manifest["review_queue_summary"]["benchmark_status_counts"][benchmark_status] = (
            target_manifest["review_queue_summary"]["benchmark_status_counts"].get(benchmark_status, 0) + 1
        )

    write_json(target_dir / "manifest.json", target_manifest)
    write_jsonl(target_dir / primary_file, selected_rows)
    print(
        json.dumps(
            {
                "status": "ok",
                "source_dataset_id": args.source_dataset_id,
                "target_dataset_id": args.target_dataset_id,
                "row_count": len(selected_rows),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
