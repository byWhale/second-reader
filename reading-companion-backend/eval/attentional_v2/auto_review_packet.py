"""Run final LLM adjudication over a review packet and fill the review CSV."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .case_audit_runs import latest_case_audit_run as find_latest_case_audit_run
from src.iterator_reader.llm_utils import LLMTraceContext, ReaderLLMError, eval_trace_context, invoke_json, llm_invocation_scope
from src.reading_runtime.llm_registry import DEFAULT_DATASET_REVIEW_PROFILE_ID


ROOT = Path(__file__).resolve().parents[2]
REVIEW_PACKET_ROOT = ROOT / "eval" / "review_packets" / "pending"
CASE_AUDIT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2" / "case_audits"

ALLOWED_ACTIONS = {"keep", "revise", "drop", "unclear"}
ALLOWED_CONFIDENCE = {"high", "medium", "low"}
ALLOWED_PROBLEM_TYPES = {
    "wrong_bucket",
    "weak_excerpt",
    "ambiguous_focus",
    "text_noise",
    "duplicate_case",
    "too_easy",
    "too_hard",
    "source_parse_problem",
    "other",
}

SYSTEM = """You are the final benchmark-review adjudicator for a reading-mechanism evaluation dataset.

You are separate from:
- the dataset builder
- the primary LLM case auditor
- the adversarial disagreement auditor

For the current operational policy, your multi-prompt LLM adjudication replaces manual packet review.
Be conservative and independent. Do not defend the existing case label just because it already exists.

Return JSON only."""

PROMPT = """Packet case:
{case_json}

Factual audit:
{factual_json}

Primary case review:
{primary_json}

Adversarial disagreement review:
{adversarial_json}

Decide the final operational review action for this case.

Rules:
- `keep` only if the case is strong enough to enter the reviewed benchmark slice now.
- `revise` if the case is promising but should not be frozen yet without relabeling, focus rewrite, or excerpt redesign.
- `drop` if the case should leave the active benchmark.
- `unclear` if the case still needs later adjudication.
- If you choose `revise` or `drop`, include at least one problem type.
- Only suggest a revised bucket if the current bucket is genuinely wrong or materially weaker than a better one.
- Notes should be concise and decision-bearing.

Return JSON:
{{
  "review__action": "keep|revise|drop|unclear",
  "review__confidence": "high|medium|low",
  "review__problem_types": ["wrong_bucket|weak_excerpt|ambiguous_focus|text_noise|duplicate_case|too_easy|too_hard|source_parse_problem|other"],
  "review__revised_bucket": "",
  "review__revised_selection_reason": "",
  "review__revised_judge_focus": "",
  "review__notes": "2-5 sentences."
}}
"""


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


def packet_dir_from_args(packet_id: str | None, packet_dir: str | None) -> Path:
    if packet_dir:
        return Path(packet_dir).expanduser().resolve()
    if not packet_id:
        raise ValueError("Provide --packet-id or --packet-dir")
    return (REVIEW_PACKET_ROOT / packet_id).resolve()

def parse_review_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    if not rows:
        raise ValueError(f"No review rows found in {path}")
    return fieldnames, rows


def write_review_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def default_review() -> dict[str, Any]:
    return {
        "review__action": "unclear",
        "review__confidence": "low",
        "review__problem_types": ["other"],
        "review__revised_bucket": "",
        "review__revised_selection_reason": "",
        "review__revised_judge_focus": "",
        "review__notes": "llm_adjudication_unavailable",
    }


def normalize_review(payload: Any) -> dict[str, Any]:
    normalized = default_review()
    if not isinstance(payload, dict):
        return normalized
    action = str(payload.get("review__action", "")).strip().lower()
    if action in ALLOWED_ACTIONS:
        normalized["review__action"] = action
    confidence = str(payload.get("review__confidence", "")).strip().lower()
    if confidence in ALLOWED_CONFIDENCE:
        normalized["review__confidence"] = confidence
    problem_types = payload.get("review__problem_types", [])
    if isinstance(problem_types, list):
        cleaned = [str(item).strip() for item in problem_types if str(item).strip() in ALLOWED_PROBLEM_TYPES]
        if cleaned:
            normalized["review__problem_types"] = cleaned
    normalized["review__revised_bucket"] = str(payload.get("review__revised_bucket", "")).strip()
    normalized["review__revised_selection_reason"] = str(payload.get("review__revised_selection_reason", "")).strip()
    normalized["review__revised_judge_focus"] = str(payload.get("review__revised_judge_focus", "")).strip()
    normalized["review__notes"] = str(payload.get("review__notes", "")).strip() or normalized["review__notes"]
    if normalized["review__action"] in {"revise", "drop"} and not normalized["review__problem_types"]:
        normalized["review__problem_types"] = ["other"]
    return normalized


def adjudicate(case: dict[str, Any], audit_row: dict[str, Any]) -> dict[str, Any]:
    try:
        with llm_invocation_scope(
            trace_context=LLMTraceContext(stage="packet_adjudication", node="final_adjudication"),
        ):
            payload = invoke_json(
                SYSTEM,
                PROMPT.format(
                    case_json=json.dumps(case, ensure_ascii=False, indent=2),
                    factual_json=json.dumps(audit_row.get("factual_audit", {}), ensure_ascii=False, indent=2),
                    primary_json=json.dumps(audit_row.get("primary_review", {}), ensure_ascii=False, indent=2),
                    adversarial_json=json.dumps(audit_row.get("adversarial_review", {}), ensure_ascii=False, indent=2),
                ),
                default=default_review(),
            )
    except ReaderLLMError:
        return default_review()
    except Exception:
        return default_review()
    return normalize_review(payload)


def render_report(packet_id: str, run_id: str, rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        f"# LLM Packet Review: `{packet_id}`",
        "",
        f"- run_id: `{run_id}`",
        f"- generated_at: `{summary['generated_at']}`",
        f"- case_count: `{summary['case_count']}`",
        f"- action_counts: `{json.dumps(summary['action_counts'], ensure_ascii=False, sort_keys=True)}`",
        "",
        "## Case Decisions",
        "",
    ]
    for row in rows:
        decision = row["llm_review"]
        lines.extend(
            [
                f"- `{row['case_id']}`",
                f"  - action: `{decision['review__action']}`",
                f"  - confidence: `{decision['review__confidence']}`",
                f"  - problem_types: `{('|'.join(decision['review__problem_types']) if decision['review__problem_types'] else '')}`",
                f"  - notes: {decision['review__notes']}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-id")
    parser.add_argument("--packet-dir")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet_dir = packet_dir_from_args(args.packet_id, args.packet_dir)
    packet_manifest_path = packet_dir / "packet_manifest.json"
    packet_manifest = load_json(packet_manifest_path)
    packet_id = str(packet_manifest["packet_id"])
    audit_run = find_latest_case_audit_run(packet_id, CASE_AUDIT_RUNS_ROOT, require_completed=True)
    if audit_run is None:
        raise FileNotFoundError(f"No completed case audit run found for packet {packet_id}")
    audit_run_dir = Path(str(audit_run["run_dir"]))
    audit_cases_dir = audit_run_dir / "cases"

    fieldnames, review_rows = parse_review_rows(packet_dir / "cases.review.csv")
    source_rows = {str(row.get("case_id", "")): row for row in load_jsonl(packet_dir / "cases.source.jsonl")}

    run_id = f"{packet_id}__llm_review__{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    review_run_dir = packet_dir / "llm_review_runs" / run_id
    trace_context = eval_trace_context(
        review_run_dir,
        eval_target=f"dataset_packet_adjudication:{packet_id}",
    )

    adjudicated_rows: list[dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    with llm_invocation_scope(
        profile_id=DEFAULT_DATASET_REVIEW_PROFILE_ID,
        trace_context=trace_context,
    ):
        for row in review_rows:
            case_id = str(row.get("case_id", "")).strip()
            source_row = source_rows[case_id]
            audit_row = load_json(audit_cases_dir / f"{case_id}.json")
            llm_review = adjudicate(source_row, audit_row)
            row["review__action"] = llm_review["review__action"]
            row["review__confidence"] = llm_review["review__confidence"]
            row["review__problem_types"] = "|".join(llm_review["review__problem_types"])
            row["review__revised_bucket"] = llm_review["review__revised_bucket"]
            row["review__revised_selection_reason"] = llm_review["review__revised_selection_reason"]
            row["review__revised_judge_focus"] = llm_review["review__revised_judge_focus"]
            row["review__notes"] = llm_review["review__notes"]
            adjudicated_rows.append({"case_id": case_id, "llm_review": llm_review})
            action_counts[llm_review["review__action"]] += 1
    summary = {
        "packet_id": packet_id,
        "run_id": run_id,
        "generated_at": utc_now(),
        "review_origin": "llm",
        "review_policy": "llm_multi_prompt_adjudication_v1",
        "case_count": len(adjudicated_rows),
        "action_counts": dict(action_counts),
        "source_case_audit_run_id": audit_run_dir.name,
    }

    write_json(packet_dir / "llm_review_summary.json", summary)
    (packet_dir / "llm_review_report.md").write_text(render_report(packet_id, run_id, adjudicated_rows, summary), encoding="utf-8")

    packet_manifest["review_origin"] = "llm"
    packet_manifest["review_policy"] = "llm_multi_prompt_adjudication_v1"
    packet_manifest["llm_review_run_id"] = run_id
    packet_manifest["llm_review_generated_at"] = summary["generated_at"]
    packet_manifest["source_case_audit_run_id"] = audit_run_dir.name

    if args.dry_run:
        print(json.dumps({"status": "dry_run_ok", **summary}, ensure_ascii=False, indent=2))
        return 0

    write_review_rows(packet_dir / "cases.review.csv", fieldnames, review_rows)
    write_json(packet_manifest_path, packet_manifest)

    print(json.dumps({"status": "ok", **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
