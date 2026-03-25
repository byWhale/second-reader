"""Import a completed human-review packet back into a benchmark dataset."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REVIEW_PACKET_ROOT = ROOT / "eval" / "review_packets"
PENDING_PACKET_ROOT = REVIEW_PACKET_ROOT / "pending"
ARCHIVE_PACKET_ROOT = REVIEW_PACKET_ROOT / "archive"

ALLOWED_ACTIONS = {"keep", "revise", "drop", "unclear"}
ALLOWED_CONFIDENCE = {"", "high", "medium", "low"}


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


def normalize_problem_types(raw_value: str) -> list[str]:
    return [item.strip() for item in str(raw_value or "").split("|") if item.strip()]


def parse_review_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError(f"No review rows found in {path}")
    return rows


def validate_review_rows(rows: list[dict[str, str]]) -> None:
    for row in rows:
        case_id = str(row.get("case_id", "")).strip()
        action = str(row.get("review__action", "")).strip().lower()
        confidence = str(row.get("review__confidence", "")).strip().lower()
        if not case_id:
            raise ValueError("Review row missing case_id")
        if action not in ALLOWED_ACTIONS:
            raise ValueError(f"Invalid review__action for {case_id}: {action!r}")
        if confidence not in ALLOWED_CONFIDENCE:
            raise ValueError(f"Invalid review__confidence for {case_id}: {confidence!r}")


def packet_dir_from_args(packet_id: str | None, packet_dir: str | None) -> Path:
    if packet_dir:
        return Path(packet_dir).expanduser().resolve()
    if not packet_id:
        raise ValueError("Provide --packet-id or --packet-dir")
    return (PENDING_PACKET_ROOT / packet_id).resolve()


def merge_review_event(row: dict[str, Any], review_row: dict[str, str], *, packet_id: str) -> dict[str, Any]:
    action = str(review_row.get("review__action", "")).strip().lower()
    confidence = str(review_row.get("review__confidence", "")).strip().lower()
    problem_types = normalize_problem_types(review_row.get("review__problem_types", ""))
    revised_bucket = str(review_row.get("review__revised_bucket", "")).strip()
    revised_selection_reason = str(review_row.get("review__revised_selection_reason", "")).strip()
    revised_judge_focus = str(review_row.get("review__revised_judge_focus", "")).strip()
    review_notes = str(review_row.get("review__notes", "")).strip()

    event = {
        "packet_id": packet_id,
        "reviewed_at": utc_now(),
        "action": action,
        "confidence": confidence,
        "problem_types": problem_types,
        "revised_bucket": revised_bucket,
        "revised_selection_reason": revised_selection_reason,
        "revised_judge_focus": revised_judge_focus,
        "notes": review_notes,
    }
    history = list(row.get("review_history", []))
    history.append(event)
    row["review_history"] = history
    row["human_review_latest"] = event
    row["review_status"] = "human_reviewed"
    row["human_review_decision"] = action

    benchmark_status_map = {
        "keep": "reviewed_active",
        "revise": "needs_revision",
        "drop": "needs_replacement",
        "unclear": "needs_adjudication",
    }
    row["benchmark_status"] = benchmark_status_map[action]
    row["curation_status"] = f"human_reviewed_v1_{action}"

    if revised_selection_reason:
        row["selection_reason"] = revised_selection_reason
    if revised_judge_focus:
        row["judge_focus"] = revised_judge_focus
    if revised_bucket:
        row["review_suggested_bucket"] = revised_bucket
    if review_notes:
        row["human_review_notes"] = review_notes
    if problem_types:
        row["human_review_problem_types"] = problem_types
    case_provenance = row.get("case_provenance")
    if not isinstance(case_provenance, dict):
        case_provenance = {}
        row["case_provenance"] = case_provenance
    packet_ids = case_provenance.get("review_packet_ids")
    if not isinstance(packet_ids, list):
        packet_ids = []
        case_provenance["review_packet_ids"] = packet_ids
    if packet_id not in packet_ids:
        packet_ids.append(packet_id)
    case_provenance["human_review_count"] = len(history)
    row["metadata_sync"] = {
        "last_synced_at": utc_now(),
        "sync_reason": "import_dataset_review_packet",
        "case_id": str(row.get("case_id", "")),
        "packet_id": packet_id,
    }
    return row


def archive_packet(packet_dir: Path, *, packet_id: str) -> Path:
    archive_dir = ARCHIVE_PACKET_ROOT / packet_id
    if archive_dir.exists():
        raise FileExistsError(f"Archive packet already exists: {archive_dir}")
    archive_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(packet_dir), str(archive_dir))
    return archive_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-id")
    parser.add_argument("--packet-dir")
    parser.add_argument("--archive", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet_dir = packet_dir_from_args(args.packet_id, args.packet_dir)
    packet_manifest = load_json(packet_dir / "packet_manifest.json")
    packet_id = str(packet_manifest["packet_id"])
    review_rows = parse_review_rows(packet_dir / "cases.review.csv")
    validate_review_rows(review_rows)

    dataset_primary_file = ROOT / str(packet_manifest["dataset_primary_file_path"])
    dataset_rows = load_jsonl(dataset_primary_file)
    by_case_id = {str(row.get("case_id", "")): row for row in dataset_rows}

    for review_row in review_rows:
        case_id = str(review_row["case_id"]).strip()
        if case_id not in by_case_id:
            raise ValueError(f"Packet references case missing from dataset: {case_id}")
        by_case_id[case_id] = merge_review_event(by_case_id[case_id], review_row, packet_id=packet_id)

    updated_rows = [by_case_id[str(row.get("case_id", ""))] for row in dataset_rows]
    summary = {
        "packet_id": packet_id,
        "imported_at": utc_now(),
        "dataset_primary_file_path": str(dataset_primary_file),
        "reviewed_case_count": len(review_rows),
        "action_counts": {
            action: sum(1 for row in review_rows if str(row.get("review__action", "")).strip().lower() == action)
            for action in sorted(ALLOWED_ACTIONS)
        },
    }

    write_json(packet_dir / "import_summary.json", summary)
    if args.dry_run:
        print(json.dumps({"status": "dry_run_ok", **summary}, ensure_ascii=False, indent=2))
        return 0

    dataset_before_import = packet_dir / "dataset_before_import.jsonl"
    dataset_before_import.write_text(dataset_primary_file.read_text(encoding="utf-8"), encoding="utf-8")
    write_jsonl(dataset_primary_file, updated_rows)

    archived_dir = packet_dir
    if args.archive:
        archived_dir = archive_packet(packet_dir, packet_id=packet_id)

    print(
        json.dumps(
            {
                "status": "ok",
                **summary,
                "archived_packet_dir": str(archived_dir),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
