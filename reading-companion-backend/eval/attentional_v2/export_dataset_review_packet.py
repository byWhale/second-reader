"""Export a review packet for a benchmark dataset.

The packet is designed for fast review without a frontend UI. It creates:
- packet_manifest.json
- cases.review.csv
- cases.preview.md
- cases.source.jsonl
under eval/review_packets/pending/<packet_id>/
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
TRACKED_DATASET_ROOT = ROOT / "eval" / "datasets"
LOCAL_DATASET_ROOT = ROOT / "state" / "eval_local_datasets"
REVIEW_PACKET_ROOT = ROOT / "eval" / "review_packets"
PENDING_PACKET_ROOT = REVIEW_PACKET_ROOT / "pending"

FAMILY_CHOICES = (
    "excerpt_cases",
    "chapter_corpora",
    "runtime_fixtures",
    "compatibility_fixtures",
    "window_cases",
    "accumulation_probes",
)
STORAGE_MODE_CHOICES = ("tracked", "local-only")
REVIEWABLE_FIELDS = (
    "review__action",
    "review__confidence",
    "review__problem_types",
    "review__revised_bucket",
    "review__revised_selection_reason",
    "review__revised_judge_focus",
    "review__notes",
)


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


def root_for_storage_mode(storage_mode: str) -> Path:
    if storage_mode == "tracked":
        return TRACKED_DATASET_ROOT
    if storage_mode == "local-only":
        return LOCAL_DATASET_ROOT
    raise ValueError(f"Unsupported storage mode: {storage_mode}")


def dataset_dir(*, family: str, dataset_id: str, storage_mode: str) -> Path:
    return root_for_storage_mode(storage_mode) / family / dataset_id


def normalize_pipe_list(value: Any) -> str:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value or "")


def filtered_rows(
    rows: list[dict[str, Any]],
    *,
    buckets: set[str],
    limit: int | None,
    only_unreviewed: bool,
    case_ids: set[str],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        case_id = str(row.get("case_id", ""))
        if case_ids and case_id not in case_ids:
            continue
        if buckets and not any(f"__{bucket}__" in case_id for bucket in buckets):
            continue
        if only_unreviewed:
            review_status = str(row.get("review_status", "")).strip()
            if review_status and review_status != "builder_curated":
                continue
            if row.get("review_latest") or row.get("human_review_latest") or row.get("llm_review_latest"):
                continue
        selected.append(row)
    if limit and limit > 0:
        return selected[:limit]
    return selected


def packet_id_for(dataset_id: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{dataset_id}__review__{timestamp}"


def build_review_rows(
    rows: list[dict[str, Any]],
    *,
    dataset_id: str,
    family: str,
    storage_mode: str,
) -> list[dict[str, str]]:
    review_rows: list[dict[str, str]] = []
    for row in rows:
        review_rows.append(
            {
                "case_id": str(row.get("case_id", "")),
                "dataset_id": dataset_id,
                "family": family,
                "storage_mode": storage_mode,
                "language": str(row.get("output_language", row.get("language_track", ""))),
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
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "case_id",
        "dataset_id",
        "family",
        "storage_mode",
        "language",
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
) -> None:
    lines = [
        f"# Review Packet `{packet_id}`",
        "",
        "This file is for reading. Edit `cases.review.csv`, not this Markdown file.",
        "",
        "## Dataset",
        f"- dataset_id: `{dataset_manifest.get('dataset_id', '')}`",
        f"- family: `{dataset_manifest.get('family', '')}`",
        f"- language_track: `{dataset_manifest.get('language_track', '')}`",
        f"- version: `{dataset_manifest.get('version', '')}`",
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
        "## Problem Types",
        "- `wrong_bucket`",
        "- `weak_excerpt`",
        "- `ambiguous_focus`",
        "- `text_noise`",
        "- `duplicate_case`",
        "- `too_easy`",
        "- `too_hard`",
        "- `source_parse_problem`",
        "- `other`",
        "",
    ]
    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"## {index}. `{row.get('case_id', '')}`",
                "",
                f"- book: `{row.get('book_title', '')}`",
                f"- author: `{row.get('author', '')}`",
                f"- chapter: `{row.get('chapter_title', '')}` (`{row.get('chapter_id', '')}`)",
                f"- question_ids: `{normalize_pipe_list(row.get('question_ids', []))}`",
                f"- phenomena: `{normalize_pipe_list(row.get('phenomena', []))}`",
                f"- selection_reason: {row.get('selection_reason', '')}",
                f"- judge_focus: {row.get('judge_focus', '')}",
                "",
                "```text",
                str(row.get("excerpt_text", row.get("chapter_excerpt", ""))).strip(),
                "```",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def packet_readme_text(packet_id: str) -> str:
    return f"""# Dataset Review Packet `{packet_id}`

This packet is designed for fast review without a frontend UI.

## Files
- `packet_manifest.json`
  - machine-readable packet metadata
- `cases.review.csv`
  - the file you should edit
- `cases.preview.md`
  - human-readable preview of the cases
- `cases.source.jsonl`
  - exact source rows that were exported into this packet

## What To Edit
Only edit the `review__...` columns in `cases.review.csv`.

Required:
- `review__action`
  - `keep`
  - `revise`
  - `drop`
  - `unclear`

Recommended:
- `review__confidence`
  - `high`
  - `medium`
  - `low`
- `review__problem_types`
  - use `|` between codes if there are several

Optional:
- `review__revised_bucket`
- `review__revised_selection_reason`
- `review__revised_judge_focus`
- `review__notes`

## Return Process
Current operational mode:
- Codex may fill the `review__...` columns automatically through multi-prompt LLM adjudication.

Optional manual mode:
1. Read `cases.preview.md` if you want the cleanest reading view.
2. Open `cases.review.csv` in Numbers, Excel, Google Sheets, or a text editor.
3. Fill in the `review__...` columns.
4. Save the file in place.
5. Tell Codex that packet `{packet_id}` is ready.

Codex will then import this packet, archive it, and merge the review metadata back into the dataset.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-id", required=True)
    parser.add_argument("--family", default="excerpt_cases", choices=FAMILY_CHOICES)
    parser.add_argument("--storage-mode", default="tracked", choices=STORAGE_MODE_CHOICES)
    parser.add_argument("--packet-id")
    parser.add_argument("--bucket", action="append", default=[])
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--only-unreviewed", action="store_true")
    parser.add_argument("--case-id", action="append", default=[])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    current_dataset_dir = dataset_dir(family=args.family, dataset_id=args.dataset_id, storage_mode=args.storage_mode)
    dataset_manifest_path = current_dataset_dir / "manifest.json"
    if not dataset_manifest_path.exists():
        raise FileNotFoundError(f"Dataset manifest not found: {dataset_manifest_path}")
    dataset_manifest = load_json(dataset_manifest_path)
    primary_file = str(dataset_manifest.get("primary_file", "")).strip()
    if not primary_file:
        raise ValueError(f"Dataset manifest missing primary_file: {dataset_manifest_path}")
    source_rows = load_jsonl(current_dataset_dir / primary_file)
    selected_rows = filtered_rows(
        source_rows,
        buckets={bucket.strip() for bucket in args.bucket if bucket.strip()},
        limit=args.limit if args.limit > 0 else None,
        only_unreviewed=bool(args.only_unreviewed),
        case_ids={case_id.strip() for case_id in args.case_id if case_id.strip()},
    )
    if not selected_rows:
        raise ValueError("No rows selected for review packet")

    packet_id = args.packet_id.strip() if args.packet_id else packet_id_for(args.dataset_id)
    packet_dir = PENDING_PACKET_ROOT / packet_id
    if packet_dir.exists():
        raise FileExistsError(f"Packet already exists: {packet_dir}")
    packet_dir.mkdir(parents=True, exist_ok=False)

    packet_manifest = {
        "packet_id": packet_id,
        "created_at": utc_now(),
        "dataset_id": args.dataset_id,
        "family": args.family,
        "storage_mode": args.storage_mode,
        "dataset_manifest_path": str(dataset_manifest_path.relative_to(ROOT)),
        "dataset_primary_file_path": str((current_dataset_dir / primary_file).relative_to(ROOT)),
        "selection_filters": {
            "buckets": list(args.bucket),
            "limit": args.limit,
            "only_unreviewed": bool(args.only_unreviewed),
            "case_ids": list(args.case_id),
        },
        "case_count": len(selected_rows),
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
    )
    write_jsonl(packet_dir / "cases.source.jsonl", selected_rows)
    (packet_dir / "README.md").write_text(packet_readme_text(packet_id), encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "ok",
                "packet_id": packet_id,
                "packet_dir": str(packet_dir),
                "case_count": len(selected_rows),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
