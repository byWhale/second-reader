"""Generate a revision/replacement review packet from benchmark-status flags.

This packet type is for round-2 hardening after an earlier review import has
already marked cases as `needs_revision` or `needs_replacement`.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .export_dataset_review_packet import (
    FAMILY_CHOICES,
    REVIEWABLE_FIELDS,
    ROOT,
    STORAGE_MODE_CHOICES,
    PENDING_PACKET_ROOT,
    dataset_dir,
    load_json,
    load_jsonl,
    normalize_pipe_list,
    packet_readme_text,
    write_json,
    write_jsonl,
)


STATUS_ORDER = {
    "needs_revision": 0,
    "needs_replacement": 1,
    "needs_adjudication": 2,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_packet_id(dataset_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{dataset_id}__revision_replacement__{timestamp}"


def select_rows(
    rows: list[dict[str, Any]],
    *,
    statuses: set[str],
    case_ids: set[str],
    limit: int | None,
) -> list[dict[str, Any]]:
    selected = [
        row
        for row in rows
        if (
            (not case_ids or str(row.get("case_id", "")) in case_ids)
            and str(row.get("benchmark_status", "")).strip() in statuses
        )
    ]
    selected.sort(
        key=lambda row: (
            STATUS_ORDER.get(str(row.get("benchmark_status", "")).strip(), 99),
            str(row.get("case_id", "")),
        )
    )
    if limit and limit > 0:
        return selected[:limit]
    return selected


def latest_problem_types(row: dict[str, Any]) -> str:
    latest = row.get("review_latest", {})
    if isinstance(latest, dict):
        return normalize_pipe_list(latest.get("problem_types", []))
    return ""


def latest_revised_bucket(row: dict[str, Any]) -> str:
    latest = row.get("review_latest", {})
    if isinstance(latest, dict):
        return str(latest.get("revised_bucket", "")).strip()
    return ""


def build_review_rows(
    rows: list[dict[str, Any]],
    *,
    dataset_id: str,
    family: str,
    storage_mode: str,
) -> list[dict[str, str]]:
    review_rows: list[dict[str, str]] = []
    for row in rows:
        latest = row.get("review_latest", {})
        latest_action = str(latest.get("action", "")).strip() if isinstance(latest, dict) else ""
        latest_notes = str(latest.get("notes", "")).strip() if isinstance(latest, dict) else ""
        review_rows.append(
            {
                "case_id": str(row.get("case_id", "")),
                "dataset_id": dataset_id,
                "family": family,
                "storage_mode": storage_mode,
                "language": str(row.get("output_language", row.get("language_track", ""))),
                "benchmark_status": str(row.get("benchmark_status", "")),
                "review_status": str(row.get("review_status", "")),
                "latest_review_action": latest_action,
                "latest_problem_types": latest_problem_types(row),
                "latest_revised_bucket": latest_revised_bucket(row),
                "latest_notes": latest_notes,
                "book_title": str(row.get("book_title", "")),
                "author": str(row.get("author", "")),
                "chapter_id": str(row.get("chapter_id", "")),
                "chapter_title": str(row.get("chapter_title", "")),
                "question_ids": normalize_pipe_list(row.get("question_ids", [])),
                "phenomena": normalize_pipe_list(row.get("phenomena", [])),
                "selection_reason": str(row.get("selection_reason", "")),
                "judge_focus": str(row.get("judge_focus", "")),
                "excerpt_text": str(row.get("excerpt_text", row.get("chapter_excerpt", ""))),
                "notes": str(row.get("notes", "")),
                "review__action": "",
                "review__confidence": "",
                "review__problem_types": "",
                "review__revised_bucket": "",
                "review__revised_selection_reason": "",
                "review__revised_judge_focus": "",
                "review__notes": "",
            }
        )
    return review_rows


def write_review_csv(path: Path, rows: list[dict[str, str]]) -> None:
    import csv

    fieldnames = list(rows[0].keys()) if rows else [
        "case_id",
        "dataset_id",
        "family",
        "storage_mode",
        "language",
        "benchmark_status",
        "review_status",
        "latest_review_action",
        "latest_problem_types",
        "latest_revised_bucket",
        "latest_notes",
        "book_title",
        "author",
        "chapter_id",
        "chapter_title",
        "question_ids",
        "phenomena",
        "selection_reason",
        "judge_focus",
        "excerpt_text",
        "notes",
        *REVIEWABLE_FIELDS,
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_preview_markdown(
    path: Path,
    *,
    packet_id: str,
    dataset_manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    statuses: list[str],
) -> None:
    lines = [
        f"# Revision/Replacement Packet `{packet_id}`",
        "",
        "This packet was generated automatically from cases whose current `benchmark_status` requires another hardening round.",
        "",
        "## Dataset",
        f"- dataset_id: `{dataset_manifest.get('dataset_id', '')}`",
        f"- family: `{dataset_manifest.get('family', '')}`",
        f"- language_track: `{dataset_manifest.get('language_track', '')}`",
        f"- version: `{dataset_manifest.get('version', '')}`",
        f"- targeted_statuses: `{ '|'.join(statuses) }`",
        "",
        "## Review Actions",
        "- `keep`",
        "- `revise`",
        "- `drop`",
        "- `unclear`",
        "",
        "## Confidence",
        "- `high`",
        "- `medium`",
        "- `low`",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        latest = row.get("review_latest", {})
        latest_action = str(latest.get("action", "")).strip() if isinstance(latest, dict) else ""
        latest_notes = str(latest.get("notes", "")).strip() if isinstance(latest, dict) else ""
        latest_problem_types = latest_problem_types = (
            normalize_pipe_list(latest.get("problem_types", [])) if isinstance(latest, dict) else ""
        )
        latest_revised_bucket = str(latest.get("revised_bucket", "")).strip() if isinstance(latest, dict) else ""
        lines.extend(
            [
                f"## {index}. `{row.get('case_id', '')}`",
                "",
                f"- benchmark_status: `{row.get('benchmark_status', '')}`",
                f"- review_status: `{row.get('review_status', '')}`",
                f"- book: `{row.get('book_title', '')}`",
                f"- author: `{row.get('author', '')}`",
                f"- chapter: `{row.get('chapter_title', '')}` (`{row.get('chapter_id', '')}`)",
                f"- question_ids: `{normalize_pipe_list(row.get('question_ids', []))}`",
                f"- phenomena: `{normalize_pipe_list(row.get('phenomena', []))}`",
                f"- selection_reason: {row.get('selection_reason', '')}",
                f"- judge_focus: {row.get('judge_focus', '')}",
                f"- latest_review_action: `{latest_action}`",
                f"- latest_problem_types: `{latest_problem_types}`",
                f"- latest_revised_bucket: `{latest_revised_bucket}`",
                f"- latest_notes: {latest_notes}",
                "",
                "```text",
                str(row.get("excerpt_text", row.get("chapter_excerpt", ""))).strip(),
                "```",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--family", default="excerpt_cases", choices=FAMILY_CHOICES)
    parser.add_argument("--storage-mode", default="tracked", choices=STORAGE_MODE_CHOICES)
    parser.add_argument("--packet-id")
    parser.add_argument(
        "--status",
        action="append",
        default=["needs_revision", "needs_replacement"],
        help="benchmark_status values to include",
    )
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    current_dataset_dir = dataset_dir(
        family=args.family,
        dataset_id=args.dataset_id,
        storage_mode=args.storage_mode,
    )
    dataset_manifest_path = current_dataset_dir / "manifest.json"
    if not dataset_manifest_path.exists():
        raise FileNotFoundError(f"Dataset manifest not found: {dataset_manifest_path}")
    dataset_manifest = load_json(dataset_manifest_path)
    primary_file = str(dataset_manifest.get("primary_file", "")).strip()
    if not primary_file:
        raise ValueError(f"Dataset manifest missing primary_file: {dataset_manifest_path}")
    source_rows = load_jsonl(current_dataset_dir / primary_file)
    statuses = [status.strip() for status in args.status if status.strip()]
    status_set = set(statuses)
    selected_rows = select_rows(
        source_rows,
        statuses=status_set,
        case_ids={case_id.strip() for case_id in args.case_id if case_id.strip()},
        limit=args.limit if args.limit > 0 else None,
    )
    if not selected_rows:
        raise ValueError("No rows selected for revision/replacement packet")

    packet_id = args.packet_id.strip() if args.packet_id else default_packet_id(args.dataset_id)
    packet_dir = PENDING_PACKET_ROOT / packet_id
    if packet_dir.exists():
        raise FileExistsError(f"Packet already exists: {packet_dir}")
    packet_dir.mkdir(parents=True, exist_ok=False)

    packet_manifest = {
        "packet_id": packet_id,
        "packet_kind": "revision_replacement",
        "created_at": utc_now(),
        "dataset_id": args.dataset_id,
        "family": args.family,
        "storage_mode": args.storage_mode,
        "dataset_manifest_path": str(dataset_manifest_path.relative_to(ROOT)),
        "dataset_primary_file_path": str((current_dataset_dir / primary_file).relative_to(ROOT)),
        "selection_filters": {
            "statuses": statuses,
            "limit": args.limit,
            "case_ids": list(args.case_id),
        },
        "case_count": len(selected_rows),
        "status_counts": dict(Counter(str(row.get("benchmark_status", "")) for row in selected_rows)),
        "import_contract_version": "1",
    }
    write_json(packet_dir / "packet_manifest.json", packet_manifest)
    write_review_csv(
        packet_dir / "cases.review.csv",
        build_review_rows(
            selected_rows,
            dataset_id=args.dataset_id,
            family=args.family,
            storage_mode=args.storage_mode,
        ),
    )
    write_preview_markdown(
        packet_dir / "cases.preview.md",
        packet_id=packet_id,
        dataset_manifest=dataset_manifest,
        rows=selected_rows,
        statuses=statuses,
    )
    write_jsonl(packet_dir / "cases.source.jsonl", selected_rows)
    (packet_dir / "README.md").write_text(packet_readme_text(packet_id), encoding="utf-8")

    import json

    print(
        json.dumps(
            {
            "status": "ok",
            "packet_id": packet_id,
            "packet_dir": str(packet_dir),
            "case_count": len(selected_rows),
            "status_counts": packet_manifest["status_counts"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
