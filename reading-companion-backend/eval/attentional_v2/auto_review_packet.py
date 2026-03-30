"""Run final LLM adjudication over a review packet and fill the review CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .case_audit_runs import latest_case_audit_run as find_latest_case_audit_run
from src.iterator_reader.llm_utils import (
    LLMTraceContext,
    ReaderLLMError,
    current_llm_scope,
    eval_trace_context,
    invoke_json,
    llm_invocation_scope,
)
from src.reading_runtime.job_concurrency import resolve_worker_policy, submit_inherited_context
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
REVIEW_POLICY = "llm_multi_prompt_adjudication_v2"
ADJUDICATION_CONTRACT_VERSION = "packet_adjudication_rubric_v2"
RUN_SUMMARY_NAME = "summary.json"
RUN_MANIFEST_NAME = "manifest.json"
RUN_REPORT_NAME = "report.md"

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
- First score the case through explicit gates instead of jumping straight to the action.
- `benchmark_readiness` means:
  - `ready` if the case is benchmark-worthy now
  - `revise` if the case is promising but not benchmark-worthy yet
  - `reject` if the case should leave the active benchmark
  - `unclear` if the evidence is too mixed to commit
- `bucket_fit` means:
  - `correct` if the current bucket is the best fit
  - `relabel` if another bucket is materially better
  - `unclear` if you cannot tell safely
- `focus_clarity` means:
  - `clear`, `partial`, or `weak`
- `excerpt_integrity` means:
  - `strong`, `adequate`, or `weak`
- Then set `review__action` from those gates:
  - `keep` only when `benchmark_readiness=ready`, `excerpt_integrity` is not `weak`, and `focus_clarity` is not `weak`
  - `revise` when the case has real value but needs bucket/focus/excerpt repair
  - `drop` when the case should not stay active
  - `unclear` only when the record is genuinely inconclusive
- If you choose `revise` or `drop`, include at least one problem type.
- Only suggest a revised bucket if the current bucket is genuinely wrong or materially weaker than a better one.
- Notes should be concise and decision-bearing.

Return JSON:
{{
  "benchmark_readiness": "ready|revise|reject|unclear",
  "bucket_fit": "correct|relabel|unclear",
  "focus_clarity": "clear|partial|weak",
  "excerpt_integrity": "strong|adequate|weak",
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


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _review_prompt(case: dict[str, Any], audit_row: dict[str, Any]) -> str:
    audit_inputs = _stable_audit_prompt_inputs(audit_row)
    return PROMPT.format(
        case_json=json.dumps(case, ensure_ascii=False, indent=2),
        factual_json=json.dumps(audit_inputs["factual_audit"], ensure_ascii=False, indent=2),
        primary_json=json.dumps(audit_inputs["primary_review"], ensure_ascii=False, indent=2),
        adversarial_json=json.dumps(audit_inputs["adversarial_review"], ensure_ascii=False, indent=2),
    )


def _dict_payload(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _stable_audit_prompt_inputs(audit_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "factual_audit": _dict_payload(audit_row.get("factual_audit")),
        "primary_review": _dict_payload(audit_row.get("primary_review")),
        "adversarial_review": _dict_payload(audit_row.get("adversarial_review")),
    }


def _case_input_payload(
    *,
    case: dict[str, Any],
    audit_row: dict[str, Any],
    system_prompt: str,
    user_prompt: str,
    source_case_audit_run_id: str,
) -> dict[str, Any]:
    audit_inputs = _stable_audit_prompt_inputs(audit_row)
    return {
        "review_policy": REVIEW_POLICY,
        "adjudication_contract_version": ADJUDICATION_CONTRACT_VERSION,
        "case": case,
        "audit_prompt_inputs": audit_inputs,
        "system_prompt_hash": _prompt_hash(system_prompt),
        "user_prompt_hash": _prompt_hash(user_prompt),
    }


def packet_input_fingerprint(
    *,
    review_policy: str,
    adjudication_contract_version: str,
    source_case_audit_run_id: str,
    case_input_fingerprints: dict[str, str],
) -> str:
    return _fingerprint(
        {
            "review_policy": review_policy,
            "adjudication_contract_version": adjudication_contract_version,
            "case_input_fingerprints": {
                case_id: str(case_input_fingerprints[case_id]).strip()
                for case_id in sorted(case_input_fingerprints)
            },
        }
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _latest_trace_entry_for_case(trace_path: Path, case_id: str) -> dict[str, Any]:
    matches = [row for row in _load_jsonl(trace_path) if str(row.get("case_id", "")).strip() == case_id]
    return dict(matches[-1]) if matches else {}


def default_review() -> dict[str, Any]:
    return {
        "benchmark_readiness": "unclear",
        "bucket_fit": "unclear",
        "focus_clarity": "weak",
        "excerpt_integrity": "weak",
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
    benchmark_readiness = str(payload.get("benchmark_readiness", "")).strip().lower()
    if benchmark_readiness in {"ready", "revise", "reject", "unclear"}:
        normalized["benchmark_readiness"] = benchmark_readiness
    bucket_fit = str(payload.get("bucket_fit", "")).strip().lower()
    if bucket_fit in {"correct", "relabel", "unclear"}:
        normalized["bucket_fit"] = bucket_fit
    focus_clarity = str(payload.get("focus_clarity", "")).strip().lower()
    if focus_clarity in {"clear", "partial", "weak"}:
        normalized["focus_clarity"] = focus_clarity
    excerpt_integrity = str(payload.get("excerpt_integrity", "")).strip().lower()
    if excerpt_integrity in {"strong", "adequate", "weak"}:
        normalized["excerpt_integrity"] = excerpt_integrity
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


def adjudicate(
    case_id: str,
    case: dict[str, Any],
    audit_row: dict[str, Any],
    *,
    standard_trace_path: Path,
    source_case_audit_run_id: str,
) -> dict[str, Any]:
    system_prompt = SYSTEM
    user_prompt = _review_prompt(case, audit_row)
    input_payload = _case_input_payload(
        case=case,
        audit_row=audit_row,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        source_case_audit_run_id=source_case_audit_run_id,
    )
    raw_payload: Any = default_review()
    status = "ok"
    error_type = ""
    error_message = ""
    try:
        with llm_invocation_scope(
            trace_context=LLMTraceContext(
                stage="packet_adjudication",
                node="final_adjudication",
                extra={"case_id": case_id},
            ),
        ):
            scope = current_llm_scope()
            raw_payload = invoke_json(system_prompt, user_prompt, default=default_review())
            trace_entry = _latest_trace_entry_for_case(standard_trace_path, case_id)
            normalized = normalize_review(raw_payload)
            return {
                "case_id": case_id,
                "raw_model_payload": raw_payload if isinstance(raw_payload, dict) else {"value": raw_payload},
                "normalized_review": normalized,
                "adjudication_input_fingerprint": _fingerprint(input_payload),
                "source_row_fingerprint": _fingerprint(case),
                "audit_row_fingerprint": _fingerprint(_stable_audit_prompt_inputs(audit_row)),
                "prompt_hashes": {
                    "system_prompt_hash": input_payload["system_prompt_hash"],
                    "user_prompt_hash": input_payload["user_prompt_hash"],
                },
                "selected_target_id": str(trace_entry.get("selected_target_id") or (scope.pinned_target_id if scope else "") or ""),
                "selected_tier_id": str(trace_entry.get("selected_tier_id") or (scope.pinned_tier_id if scope else "") or ""),
                "provider_id": str(trace_entry.get("provider_id", "") or ""),
                "contract": str(trace_entry.get("contract", "") or ""),
                "model": str(trace_entry.get("model", "") or ""),
                "key_slot_id": str(trace_entry.get("key_slot_id", "") or ""),
                "selection_reason": str(trace_entry.get("selection_reason", "") or ""),
                "selection_override_source": str(trace_entry.get("selection_override_source", "") or ""),
                "trace_call_id": str(trace_entry.get("call_id", "") or ""),
                "trace_status": str(trace_entry.get("status", "") or "ok"),
                "attempt_count": int(trace_entry.get("attempt_count", 0) or 0),
                "source_case_audit_run_id": source_case_audit_run_id,
                "input_payload": input_payload,
                "error": {
                    "status": status,
                    "error_type": error_type,
                    "error_message": error_message,
                },
            }
    except ReaderLLMError as exc:
        status = "reader_llm_error"
        error_type = exc.__class__.__name__
        error_message = str(exc)
    except Exception as exc:
        status = "unexpected_error"
        error_type = exc.__class__.__name__
        error_message = str(exc)
    trace_entry = _latest_trace_entry_for_case(standard_trace_path, case_id)
    normalized = normalize_review(raw_payload)
    return {
        "case_id": case_id,
        "raw_model_payload": raw_payload if isinstance(raw_payload, dict) else {"value": raw_payload},
        "normalized_review": normalized,
        "adjudication_input_fingerprint": _fingerprint(input_payload),
        "source_row_fingerprint": _fingerprint(case),
        "audit_row_fingerprint": _fingerprint(_stable_audit_prompt_inputs(audit_row)),
        "prompt_hashes": {
            "system_prompt_hash": input_payload["system_prompt_hash"],
            "user_prompt_hash": input_payload["user_prompt_hash"],
        },
        "selected_target_id": str(trace_entry.get("selected_target_id", "") or ""),
        "selected_tier_id": str(trace_entry.get("selected_tier_id", "") or ""),
        "provider_id": str(trace_entry.get("provider_id", "") or ""),
        "contract": str(trace_entry.get("contract", "") or ""),
        "model": str(trace_entry.get("model", "") or ""),
        "key_slot_id": str(trace_entry.get("key_slot_id", "") or ""),
        "selection_reason": str(trace_entry.get("selection_reason", "") or ""),
        "selection_override_source": str(trace_entry.get("selection_override_source", "") or ""),
        "trace_call_id": str(trace_entry.get("call_id", "") or ""),
        "trace_status": str(trace_entry.get("status", "") or status),
        "attempt_count": int(trace_entry.get("attempt_count", 0) or 0),
        "source_case_audit_run_id": source_case_audit_run_id,
        "input_payload": input_payload,
        "error": {
            "status": status,
            "error_type": error_type,
            "error_message": error_message,
        },
    }


def adjudicate_review_row(
    row: dict[str, str],
    *,
    source_rows: dict[str, dict[str, Any]],
    audit_cases_dir: Path,
    standard_trace_path: Path,
    source_case_audit_run_id: str,
) -> dict[str, Any]:
    """Adjudicate one packet review row in isolation."""

    case_id = str(row.get("case_id", "")).strip()
    source_row = source_rows[case_id]
    audit_row = load_json(audit_cases_dir / f"{case_id}.json")
    return adjudicate(
        case_id,
        source_row,
        audit_row,
        standard_trace_path=standard_trace_path,
        source_case_audit_run_id=source_case_audit_run_id,
    )


def render_report(packet_id: str, run_id: str, rows: list[dict[str, Any]], summary: dict[str, Any]) -> str:
    lines = [
        f"# LLM Packet Review: `{packet_id}`",
        "",
        f"- run_id: `{run_id}`",
        f"- generated_at: `{summary['generated_at']}`",
        f"- case_count: `{summary['case_count']}`",
        f"- action_counts: `{json.dumps(summary['action_counts'], ensure_ascii=False, sort_keys=True)}`",
        f"- adjudication_input_fingerprint: `{summary['adjudication_input_fingerprint']}`",
        f"- probe_only: `{summary['probe_only']}`",
        "",
        "## Case Decisions",
        "",
    ]
    for row in rows:
        decision = row["normalized_review"]
        lines.extend(
            [
                f"- `{row['case_id']}`",
                f"  - action: `{decision['review__action']}`",
                f"  - confidence: `{decision['review__confidence']}`",
                f"  - problem_types: `{('|'.join(decision['review__problem_types']) if decision['review__problem_types'] else '')}`",
                f"  - adjudication_input_fingerprint: `{row['adjudication_input_fingerprint']}`",
                f"  - notes: {decision['review__notes']}",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-id")
    parser.add_argument("--packet-dir")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--max-workers", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
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
    standard_trace_path = review_run_dir / "llm_traces" / "standard.jsonl"
    trace_context = eval_trace_context(
        review_run_dir,
        eval_target=f"dataset_packet_adjudication:{packet_id}",
    )

    adjudicated_rows: list[dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    worker_policy = resolve_worker_policy(
        job_kind="packet_adjudication",
        profile_id=DEFAULT_DATASET_REVIEW_PROFILE_ID,
        task_count=len(review_rows),
        explicit_max_workers=args.max_workers if args.max_workers > 0 else None,
    )
    reviews_by_case_id: dict[str, dict[str, Any]] = {}
    with llm_invocation_scope(
        profile_id=DEFAULT_DATASET_REVIEW_PROFILE_ID,
        trace_context=trace_context,
    ):
        if worker_policy.worker_count <= 1:
            for row in review_rows:
                result = adjudicate_review_row(
                    row,
                    source_rows=source_rows,
                    audit_cases_dir=audit_cases_dir,
                    standard_trace_path=standard_trace_path,
                    source_case_audit_run_id=audit_run_dir.name,
                )
                reviews_by_case_id[result["case_id"]] = result
        else:
            with ThreadPoolExecutor(max_workers=worker_policy.worker_count, thread_name_prefix="packet-adjudication") as executor:
                future_to_case_id = {
                    submit_inherited_context(
                        executor,
                        adjudicate_review_row,
                        row,
                        source_rows=source_rows,
                        audit_cases_dir=audit_cases_dir,
                        standard_trace_path=standard_trace_path,
                        source_case_audit_run_id=audit_run_dir.name,
                    ): str(row.get("case_id", "")).strip()
                    for row in review_rows
                }
                for future in as_completed(future_to_case_id):
                    result = future.result()
                    reviews_by_case_id[result["case_id"]] = result
        for row in review_rows:
            case_id = str(row.get("case_id", "")).strip()
            case_record = reviews_by_case_id[case_id]
            llm_review = case_record["normalized_review"]
            row["review__action"] = llm_review["review__action"]
            row["review__confidence"] = llm_review["review__confidence"]
            row["review__problem_types"] = "|".join(llm_review["review__problem_types"])
            row["review__revised_bucket"] = llm_review["review__revised_bucket"]
            row["review__revised_selection_reason"] = llm_review["review__revised_selection_reason"]
            row["review__revised_judge_focus"] = llm_review["review__revised_judge_focus"]
            row["review__notes"] = llm_review["review__notes"]
            adjudicated_rows.append(case_record)
            action_counts[llm_review["review__action"]] += 1
    case_input_fingerprints = {
        row["case_id"]: row["adjudication_input_fingerprint"]
        for row in adjudicated_rows
    }
    packet_input_fingerprint_value = packet_input_fingerprint(
        review_policy=REVIEW_POLICY,
        adjudication_contract_version=ADJUDICATION_CONTRACT_VERSION,
        source_case_audit_run_id=audit_run_dir.name,
        case_input_fingerprints=case_input_fingerprints,
    )
    summary = {
        "packet_id": packet_id,
        "run_id": run_id,
        "run_dir": str(review_run_dir),
        "generated_at": utc_now(),
        "review_origin": "llm",
        "review_policy": REVIEW_POLICY,
        "adjudication_contract_version": ADJUDICATION_CONTRACT_VERSION,
        "case_count": len(adjudicated_rows),
        "action_counts": dict(action_counts),
        "source_case_audit_run_id": audit_run_dir.name,
        "adjudication_input_fingerprint": packet_input_fingerprint_value,
        "case_input_fingerprints": case_input_fingerprints,
        "probe_only": bool(args.probe_only),
    }
    run_manifest = {
        "packet_id": packet_id,
        "run_id": run_id,
        "run_dir": str(review_run_dir),
        "review_origin": "llm",
        "review_policy": REVIEW_POLICY,
        "adjudication_contract_version": ADJUDICATION_CONTRACT_VERSION,
        "source_case_audit_run_id": audit_run_dir.name,
        "case_count": len(adjudicated_rows),
        "adjudication_input_fingerprint": packet_input_fingerprint_value,
        "case_input_fingerprints": case_input_fingerprints,
        "probe_only": bool(args.probe_only),
        "generated_at": summary["generated_at"],
    }

    if args.dry_run:
        print(json.dumps({"status": "dry_run_ok", **summary}, ensure_ascii=False, indent=2))
        return 0

    for row in adjudicated_rows:
        write_json(review_run_dir / "cases" / f"{row['case_id']}.json", row)
    write_json(review_run_dir / RUN_MANIFEST_NAME, run_manifest)
    write_json(review_run_dir / RUN_SUMMARY_NAME, summary)
    (review_run_dir / RUN_REPORT_NAME).write_text(render_report(packet_id, run_id, adjudicated_rows, summary), encoding="utf-8")

    if not args.probe_only:
        write_json(packet_dir / "llm_review_summary.json", summary)
        (packet_dir / "llm_review_report.md").write_text(
            render_report(packet_id, run_id, adjudicated_rows, summary),
            encoding="utf-8",
        )
        packet_manifest["review_origin"] = "llm"
        packet_manifest["review_policy"] = REVIEW_POLICY
        packet_manifest["llm_review_run_id"] = run_id
        packet_manifest["llm_review_run_dir"] = str(review_run_dir)
        packet_manifest["llm_review_generated_at"] = summary["generated_at"]
        packet_manifest["source_case_audit_run_id"] = audit_run_dir.name
        packet_manifest["adjudication_contract_version"] = ADJUDICATION_CONTRACT_VERSION
        packet_manifest["adjudication_input_fingerprint"] = packet_input_fingerprint_value
        write_review_rows(packet_dir / "cases.review.csv", fieldnames, review_rows)
        write_json(packet_manifest_path, packet_manifest)

    print(json.dumps({"status": "ok", **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
