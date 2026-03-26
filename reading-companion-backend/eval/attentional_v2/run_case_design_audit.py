"""Audit benchmark case design for a review packet.

This evaluates the dataset cases themselves rather than the mechanism outputs.
It combines:
- factual excerpt/boundary checks
- a primary case-design review
- an adversarial disagreement review

The runner is intentionally traceable:
- `run_state.json` tracks packet-level status and progress
- `case_states/<case_id>.json` tracks per-case stage progress
- `summary/*.partial.*` files update after each completed case
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from src.iterator_reader.llm_utils import LLMTraceContext, ReaderLLMError, eval_trace_context, invoke_json, llm_invocation_scope
from src.reading_runtime.llm_registry import DEFAULT_DATASET_REVIEW_PROFILE_ID, get_llm_profile_max_concurrency

from .case_audit_runs import (
    AGGREGATE_FILE,
    PARTIAL_AGGREGATE_FILE,
    PARTIAL_REPORT_FILE,
    REPORT_FILE,
    RUN_STATE_FILE,
    SUMMARY_DIR,
)


ROOT = Path(__file__).resolve().parents[2]
REVIEW_PACKET_ROOT = ROOT / "eval" / "review_packets" / "pending"
RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2" / "case_audits"

BOILERPLATE_MARKERS = (
    "project gutenberg",
    "license",
    ".mw-parser-output",
    "public domain",
    "www.gutenberg.org",
)

PRIMARY_SYSTEM = """You audit benchmark case design for a reading-mechanism evaluation dataset.

You are not judging the mechanism output. You are judging whether the case itself is strong enough to trust.

Return JSON only."""

PRIMARY_PROMPT = """Case metadata:
{case_json}

Immediate context:
{context_json}

Decide whether this is a strong benchmark case for its current purpose.

Return JSON:
{{
  "decision": "keep|revise|drop|unclear",
  "confidence": "high|medium|low",
  "problem_types": ["wrong_bucket|weak_excerpt|ambiguous_focus|text_noise|duplicate_case|too_easy|too_hard|source_parse_problem|other"],
  "bucket_fit": 1,
  "focus_clarity": 1,
  "excerpt_strength": 1,
  "revised_bucket": "",
  "revised_selection_reason": "",
  "revised_judge_focus": "",
  "notes": "2-5 sentences."
}}
"""

ADVERSARIAL_SYSTEM = """You are doing adversarial benchmark review.

Try to find the strongest plausible argument that the current case design is misleading, mislabeled, or too weak to trust.

Return JSON only."""

ADVERSARIAL_PROMPT = """Case metadata:
{case_json}

Immediate context:
{context_json}

Return JSON:
{{
  "risk_level": "low|medium|high",
  "suspected_problem_types": ["wrong_bucket|weak_excerpt|ambiguous_focus|text_noise|duplicate_case|too_easy|too_hard|source_parse_problem|other"],
  "alternative_bucket": "",
  "challenge_summary": "2-5 sentences.",
  "notes": ""
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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def packet_dir_from_args(packet_id: str | None, packet_dir: str | None) -> Path:
    if packet_dir:
        return Path(packet_dir).expanduser().resolve()
    if not packet_id:
        raise ValueError("Provide --packet-id or --packet-dir")
    return (REVIEW_PACKET_ROOT / packet_id).resolve()


def load_source_index(dataset_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    for ref in dataset_manifest.get("source_manifest_refs", []):
        path = ROOT / str(ref)
        if not path.exists():
            continue
        payload = load_json(path)
        books = payload.get("books", [])
        if not isinstance(books, list):
            continue
        for item in books:
            if isinstance(item, dict) and item.get("source_id"):
                sources[str(item["source_id"])] = dict(item)
    return sources


def default_context() -> dict[str, list[str]]:
    return {
        "lookback_sentences": [],
        "excerpt_sentences": [],
        "lookahead_sentences": [],
    }


def find_span_and_context(case: dict[str, Any], source_index: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    source = source_index.get(str(case.get("source_id", "")))
    if not source:
        raise ValueError(f"Missing source metadata for {case.get('case_id')}")
    output_dir = ROOT / str(source["output_dir"])
    book_document_path = output_dir / "public" / "book_document.json"
    book_document = load_json(book_document_path)
    chapter_id = int(case["chapter_id"])
    start_sentence_id = str(case["start_sentence_id"])
    end_sentence_id = str(case["end_sentence_id"])
    for chapter in book_document.get("chapters", []):
        if not isinstance(chapter, dict) or int(chapter.get("id", 0) or 0) != chapter_id:
            continue
        sentences = [item for item in chapter.get("sentences", []) if isinstance(item, dict)]
        by_id = {str(sentence.get("sentence_id", "")): idx for idx, sentence in enumerate(sentences)}
        if start_sentence_id not in by_id or end_sentence_id not in by_id:
            raise ValueError(f"Sentence ids missing for {case.get('case_id')}")
        start = by_id[start_sentence_id]
        end = by_id[end_sentence_id]
        excerpt_rows = sentences[start : end + 1]
        excerpt_text = "\n".join(str(sentence.get("text", "")).strip() for sentence in excerpt_rows).strip()
        context = {
            "lookback_sentences": [str(item.get("text", "")).strip() for item in sentences[max(0, start - 3) : start]],
            "excerpt_sentences": [str(item.get("text", "")).strip() for item in excerpt_rows],
            "lookahead_sentences": [str(item.get("text", "")).strip() for item in sentences[end + 1 : end + 3]],
        }
        return {
            "source_id": case.get("source_id"),
            "output_dir": str(output_dir),
            "book_document_path": str(book_document_path),
            "excerpt_text_reconstructed": excerpt_text,
            "expected_excerpt_text": str(case.get("excerpt_text", "")).strip(),
        }, context
    raise ValueError(f"Chapter missing for {case.get('case_id')}")


def factual_audit(case: dict[str, Any], source_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source = source_index.get(str(case.get("source_id", "")))
    if not source:
        return {
            "ok": False,
            "issues": ["missing_source_metadata"],
        }
    try:
        span_info, _ = find_span_and_context(case, source_index)
    except Exception as exc:
        return {
            "ok": False,
            "issues": [f"span_resolution_error:{exc}"],
        }
    excerpt_text = span_info["expected_excerpt_text"]
    reconstructed = span_info["excerpt_text_reconstructed"]
    issues: list[str] = []
    if excerpt_text != reconstructed:
        issues.append("excerpt_text_mismatch")
    lowered = excerpt_text.lower()
    if any(marker in lowered for marker in BOILERPLATE_MARKERS):
        issues.append("boilerplate_marker_present")
    return {
        "ok": not issues,
        "issues": issues,
        **span_info,
    }


def default_primary() -> dict[str, Any]:
    return {
        "decision": "unclear",
        "confidence": "low",
        "problem_types": ["other"],
        "bucket_fit": 0,
        "focus_clarity": 0,
        "excerpt_strength": 0,
        "revised_bucket": "",
        "revised_selection_reason": "",
        "revised_judge_focus": "",
        "notes": "review_unavailable",
    }


def default_adversarial() -> dict[str, Any]:
    return {
        "risk_level": "medium",
        "suspected_problem_types": ["other"],
        "alternative_bucket": "",
        "challenge_summary": "adversarial_review_unavailable",
        "notes": "",
    }


def normalize_primary(payload: Any) -> dict[str, Any]:
    normalized = default_primary()
    if not isinstance(payload, dict):
        return normalized
    decision = str(payload.get("decision", "")).strip().lower()
    if decision in {"keep", "revise", "drop", "unclear"}:
        normalized["decision"] = decision
    confidence = str(payload.get("confidence", "")).strip().lower()
    if confidence in {"high", "medium", "low"}:
        normalized["confidence"] = confidence
    for field in ("bucket_fit", "focus_clarity", "excerpt_strength"):
        try:
            score = int(payload.get(field, 0))
        except (TypeError, ValueError):
            score = 0
        normalized[field] = max(0, min(5, score))
    if isinstance(payload.get("problem_types"), list):
        normalized["problem_types"] = [str(item).strip() for item in payload["problem_types"] if str(item).strip()]
    normalized["revised_bucket"] = str(payload.get("revised_bucket", "")).strip()
    normalized["revised_selection_reason"] = str(payload.get("revised_selection_reason", "")).strip()
    normalized["revised_judge_focus"] = str(payload.get("revised_judge_focus", "")).strip()
    normalized["notes"] = str(payload.get("notes", "")).strip() or normalized["notes"]
    return normalized


def normalize_adversarial(payload: Any) -> dict[str, Any]:
    normalized = default_adversarial()
    if not isinstance(payload, dict):
        return normalized
    risk_level = str(payload.get("risk_level", "")).strip().lower()
    if risk_level in {"low", "medium", "high"}:
        normalized["risk_level"] = risk_level
    if isinstance(payload.get("suspected_problem_types"), list):
        normalized["suspected_problem_types"] = [str(item).strip() for item in payload["suspected_problem_types"] if str(item).strip()]
    normalized["alternative_bucket"] = str(payload.get("alternative_bucket", "")).strip()
    normalized["challenge_summary"] = str(payload.get("challenge_summary", "")).strip() or normalized["challenge_summary"]
    normalized["notes"] = str(payload.get("notes", "")).strip()
    return normalized


def invoke_review_with_meta(
    *,
    stage_name: str,
    system_prompt: str,
    user_prompt: str,
    default_payload: dict[str, Any],
    normalize: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started_at = utc_now()
    started_perf = time.perf_counter()
    error: Exception | None = None
    status = "ok"
    try:
        with llm_invocation_scope(
            trace_context=LLMTraceContext(stage="case_design_audit", node=stage_name),
        ):
            payload = invoke_json(system_prompt, user_prompt, default=default_payload)
    except ReaderLLMError as exc:
        payload = default_payload
        error = exc
        status = "reader_llm_error"
    except Exception as exc:  # pragma: no cover - defensive fallback
        payload = default_payload
        error = exc
        status = "unexpected_error"
    completed_at = utc_now()
    duration_ms = int((time.perf_counter() - started_perf) * 1000)
    metadata = {
        "stage": stage_name,
        "status": status,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "error_type": error.__class__.__name__ if error else "",
        "error_message": str(error) if error else "",
        "problem_code": getattr(error, "problem_code", "") if error else "",
    }
    return normalize(payload), metadata


def run_primary(case: dict[str, Any], context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return invoke_review_with_meta(
        stage_name="primary_review",
        system_prompt=PRIMARY_SYSTEM,
        user_prompt=PRIMARY_PROMPT.format(
            case_json=json.dumps(
                {
                    "case_id": case.get("case_id"),
                    "case_title": case.get("case_title"),
                    "question_ids": case.get("question_ids", []),
                    "phenomena": case.get("phenomena", []),
                    "selection_reason": case.get("selection_reason", ""),
                    "judge_focus": case.get("judge_focus", ""),
                    "excerpt_text": case.get("excerpt_text", ""),
                },
                ensure_ascii=False,
                indent=2,
            ),
            context_json=json.dumps(context, ensure_ascii=False, indent=2),
        ),
        default_payload=default_primary(),
        normalize=normalize_primary,
    )


def run_adversarial(case: dict[str, Any], context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return invoke_review_with_meta(
        stage_name="adversarial_review",
        system_prompt=ADVERSARIAL_SYSTEM,
        user_prompt=ADVERSARIAL_PROMPT.format(
            case_json=json.dumps(
                {
                    "case_id": case.get("case_id"),
                    "case_title": case.get("case_title"),
                    "question_ids": case.get("question_ids", []),
                    "phenomena": case.get("phenomena", []),
                    "selection_reason": case.get("selection_reason", ""),
                    "judge_focus": case.get("judge_focus", ""),
                    "excerpt_text": case.get("excerpt_text", ""),
                },
                ensure_ascii=False,
                indent=2,
            ),
            context_json=json.dumps(context, ensure_ascii=False, indent=2),
        ),
        default_payload=default_adversarial(),
        normalize=normalize_adversarial,
    )


def case_state_path(run_dir: Path, case_id: str) -> Path:
    return run_dir / "case_states" / f"{case_id}.json"


def write_case_state(run_dir: Path, case_id: str, payload: dict[str, Any]) -> None:
    write_json(case_state_path(run_dir, case_id), payload)


def write_run_state(run_dir: Path, payload: dict[str, Any]) -> None:
    write_json(run_dir / RUN_STATE_FILE, payload)


def make_case_state(packet_id: str, case_id: str) -> dict[str, Any]:
    return {
        "packet_id": packet_id,
        "case_id": case_id,
        "status": "queued",
        "current_stage": "queued",
        "started_at": "",
        "updated_at": utc_now(),
        "completed_at": "",
        "factual_ok": None,
        "timing_ms": {},
        "llm_calls": {},
        "stage_statuses": {
            "factual_audit": "queued",
            "primary_review": "queued",
            "adversarial_review": "queued",
        },
        "error": {},
    }


def aggregate(rows: list[dict[str, Any]], *, total_case_count: int, status: str) -> dict[str, Any]:
    completed_rows = [row for row in rows if row.get("status") == "completed"]
    failed_rows = [row for row in rows if row.get("status") == "failed"]
    primary_decisions = Counter(str(row["primary_review"]["decision"]) for row in completed_rows)
    adversarial_risks = Counter(str(row["adversarial_review"]["risk_level"]) for row in completed_rows)
    factual_failures = sum(1 for row in completed_rows if not bool(row["factual_audit"]["ok"]))
    return {
        "status": status,
        "case_count": total_case_count,
        "completed_case_count": len(completed_rows),
        "failed_case_count": len(failed_rows),
        "incomplete_case_count": max(0, total_case_count - len(completed_rows) - len(failed_rows)),
        "factual_failure_count": factual_failures,
        "primary_decisions": dict(primary_decisions),
        "adversarial_risk_counts": dict(adversarial_risks),
        "average_bucket_fit": round(mean(row["primary_review"]["bucket_fit"] for row in completed_rows), 3) if completed_rows else 0.0,
        "average_focus_clarity": round(mean(row["primary_review"]["focus_clarity"] for row in completed_rows), 3) if completed_rows else 0.0,
        "average_excerpt_strength": round(mean(row["primary_review"]["excerpt_strength"] for row in completed_rows), 3) if completed_rows else 0.0,
    }


def render_report(rows: list[dict[str, Any]], summary: dict[str, Any], *, packet_id: str) -> str:
    lines = [
        f"# Case Design Audit: `{packet_id}`",
        "",
        "## Summary",
        f"- status: `{summary['status']}`",
        f"- case_count: `{summary['case_count']}`",
        f"- completed_case_count: `{summary['completed_case_count']}`",
        f"- failed_case_count: `{summary['failed_case_count']}`",
        f"- incomplete_case_count: `{summary['incomplete_case_count']}`",
        f"- factual_failure_count: `{summary['factual_failure_count']}`",
        f"- primary_decisions: `{json.dumps(summary['primary_decisions'], ensure_ascii=False)}`",
        f"- adversarial_risk_counts: `{json.dumps(summary['adversarial_risk_counts'], ensure_ascii=False)}`",
        f"- average_bucket_fit: `{summary['average_bucket_fit']}`",
        f"- average_focus_clarity: `{summary['average_focus_clarity']}`",
        f"- average_excerpt_strength: `{summary['average_excerpt_strength']}`",
        "",
        "## Completed / Flagged Cases",
    ]
    for row in rows:
        if row.get("status") != "completed":
            continue
        primary = row["primary_review"]
        adversarial = row["adversarial_review"]
        factual = row["factual_audit"]
        if primary["decision"] == "keep" and adversarial["risk_level"] == "low" and factual["ok"]:
            continue
        lines.extend(
            [
                f"- `{row['case_id']}`",
                f"  - primary_decision: `{primary['decision']}`",
                f"  - adversarial_risk: `{adversarial['risk_level']}`",
                f"  - factual_ok: `{factual['ok']}`",
                f"  - primary_notes: {primary['notes']}",
                f"  - challenge_summary: {adversarial['challenge_summary']}",
            ]
        )
    failed_rows = [row for row in rows if row.get("status") == "failed"]
    if failed_rows:
        lines.extend(["", "## Failed Cases"])
        for row in failed_rows:
            error = row.get("error", {})
            lines.extend(
                [
                    f"- `{row['case_id']}`",
                    f"  - error_type: `{error.get('error_type', '')}`",
                    f"  - error_message: {error.get('error_message', '')}",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def write_summary_outputs(
    run_dir: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    *,
    packet_id: str,
    partial: bool,
) -> None:
    summary_dir = run_dir / SUMMARY_DIR
    if partial:
        write_json(summary_dir / PARTIAL_AGGREGATE_FILE, summary)
        write_jsonl(summary_dir / "case_results.partial.jsonl", rows)
        (summary_dir / PARTIAL_REPORT_FILE).write_text(render_report(rows, summary, packet_id=packet_id), encoding="utf-8")
        return
    write_json(summary_dir / AGGREGATE_FILE, summary)
    write_jsonl(summary_dir / "case_results.jsonl", rows)
    (summary_dir / REPORT_FILE).write_text(render_report(rows, summary, packet_id=packet_id), encoding="utf-8")


def ordered_rows(results_by_case_id: dict[str, dict[str, Any]], case_order: list[str]) -> list[dict[str, Any]]:
    return [results_by_case_id[case_id] for case_id in case_order if case_id in results_by_case_id]


def process_case(
    case: dict[str, Any],
    *,
    packet_id: str,
    source_index: dict[str, dict[str, Any]],
    run_dir: Path,
    trace_context: LLMTraceContext,
) -> dict[str, Any]:
    case_id = str(case.get("case_id", ""))
    state = make_case_state(packet_id, case_id)
    state["status"] = "running"
    state["current_stage"] = "factual_audit"
    state["started_at"] = utc_now()
    state["updated_at"] = state["started_at"]
    state["stage_statuses"]["factual_audit"] = "running"
    write_case_state(run_dir, case_id, state)

    overall_started = time.perf_counter()
    try:
        with llm_invocation_scope(
            profile_id=DEFAULT_DATASET_REVIEW_PROFILE_ID,
            trace_context=trace_context,
        ):
            factual_started = time.perf_counter()
            factual = factual_audit(case, source_index)
            state["timing_ms"]["factual_audit"] = int((time.perf_counter() - factual_started) * 1000)
            state["factual_ok"] = bool(factual.get("ok"))
            state["stage_statuses"]["factual_audit"] = "completed"
            state["current_stage"] = "primary_review"
            state["stage_statuses"]["primary_review"] = "running"
            state["updated_at"] = utc_now()
            write_case_state(run_dir, case_id, state)

            context = default_context()
            if factual.get("ok"):
                _, context = find_span_and_context(case, source_index)

            primary, primary_meta = run_primary(case, context)
            state["llm_calls"]["primary_review"] = primary_meta
            state["timing_ms"]["primary_review"] = primary_meta["duration_ms"]
            state["stage_statuses"]["primary_review"] = "completed"
            state["current_stage"] = "adversarial_review"
            state["stage_statuses"]["adversarial_review"] = "running"
            state["updated_at"] = utc_now()
            write_case_state(run_dir, case_id, state)

            adversarial, adversarial_meta = run_adversarial(case, context)
            state["llm_calls"]["adversarial_review"] = adversarial_meta
            state["timing_ms"]["adversarial_review"] = adversarial_meta["duration_ms"]
            state["timing_ms"]["total"] = int((time.perf_counter() - overall_started) * 1000)
            state["stage_statuses"]["adversarial_review"] = "completed"
            state["status"] = "completed"
            state["current_stage"] = "completed"
            state["updated_at"] = utc_now()
            state["completed_at"] = state["updated_at"]
            write_case_state(run_dir, case_id, state)

            return {
                "case_id": case_id,
                "case_title": case.get("case_title"),
                "packet_id": packet_id,
                "status": "completed",
                "factual_audit": factual,
                "primary_review": primary,
                "adversarial_review": adversarial,
                "audit_metadata": {
                    "timing_ms": dict(state["timing_ms"]),
                    "llm_calls": dict(state["llm_calls"]),
                },
            }
    except Exception as exc:  # pragma: no cover - defensive fallback
        state["status"] = "failed"
        state["current_stage"] = "failed"
        state["updated_at"] = utc_now()
        state["completed_at"] = state["updated_at"]
        state["error"] = {
            "error_type": exc.__class__.__name__,
            "error_message": str(exc),
        }
        state["timing_ms"]["total"] = int((time.perf_counter() - overall_started) * 1000)
        write_case_state(run_dir, case_id, state)
        return {
            "case_id": case_id,
            "case_title": case.get("case_title"),
            "packet_id": packet_id,
            "status": "failed",
            "error": dict(state["error"]),
            "audit_metadata": {
                "timing_ms": dict(state["timing_ms"]),
                "llm_calls": dict(state["llm_calls"]),
            },
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-id")
    parser.add_argument("--packet-dir")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-workers", type=int, default=2)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    packet_dir = packet_dir_from_args(args.packet_id, args.packet_dir)
    packet_manifest = load_json(packet_dir / "packet_manifest.json")
    packet_id = str(packet_manifest["packet_id"])
    dataset_manifest = load_json(ROOT / str(packet_manifest["dataset_manifest_path"]))
    source_index = load_source_index(dataset_manifest)
    cases = load_jsonl(packet_dir / "cases.source.jsonl")
    if args.limit > 0:
        cases = cases[: args.limit]
    case_order = [str(case.get("case_id", "")) for case in cases]
    if not case_order:
        raise ValueError("No cases selected for audit")

    max_workers = max(1, min(args.max_workers, get_llm_profile_max_concurrency(DEFAULT_DATASET_REVIEW_PROFILE_ID), len(cases)))
    run_id = f"{packet_id}__{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "cases").mkdir(parents=True, exist_ok=True)
    (run_dir / "case_states").mkdir(parents=True, exist_ok=True)
    (run_dir / SUMMARY_DIR).mkdir(parents=True, exist_ok=True)

    for case_id in case_order:
        write_case_state(run_dir, case_id, make_case_state(packet_id, case_id))

    run_state = {
        "packet_id": packet_id,
        "run_id": run_id,
        "status": "running",
        "pid": os.getpid(),
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "completed_at": "",
        "case_count": len(cases),
        "max_workers": max_workers,
        "queued_case_count": len(cases),
        "running_case_count": 0,
        "completed_case_count": 0,
        "failed_case_count": 0,
        "queued_case_ids": list(case_order),
        "running_case_ids": [],
        "completed_case_ids": [],
        "failed_case_ids": [],
    }
    write_run_state(run_dir, run_state)
    write_summary_outputs(
        run_dir,
        [],
        aggregate([], total_case_count=len(cases), status="running"),
        packet_id=packet_id,
        partial=True,
    )

    results_by_case_id: dict[str, dict[str, Any]] = {}
    submitted: dict[Future[dict[str, Any]], str] = {}
    pending_cases = iter(cases)

    def submit_next(executor: ThreadPoolExecutor) -> bool:
        try:
            case = next(pending_cases)
        except StopIteration:
            return False
        case_id = str(case.get("case_id", ""))
        future = executor.submit(
            process_case,
            case,
            packet_id=packet_id,
            source_index=source_index,
            run_dir=run_dir,
            trace_context=trace_context,
        )
        submitted[future] = case_id
        run_state["queued_case_ids"].remove(case_id)
        run_state["running_case_ids"].append(case_id)
        run_state["queued_case_count"] = len(run_state["queued_case_ids"])
        run_state["running_case_count"] = len(run_state["running_case_ids"])
        run_state["updated_at"] = utc_now()
        write_run_state(run_dir, run_state)
        print(f"[submitted] {case_id}", flush=True)
        return True

    try:
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="case-audit") as executor:
            for _ in range(max_workers):
                if not submit_next(executor):
                    break

            while submitted:
                future = next(as_completed(tuple(submitted.keys())))
                case_id = submitted.pop(future)
                row = future.result()
                results_by_case_id[case_id] = row
                write_json(run_dir / "cases" / f"{case_id}.json", row)

                if case_id in run_state["running_case_ids"]:
                    run_state["running_case_ids"].remove(case_id)
                if row.get("status") == "completed":
                    run_state["completed_case_ids"].append(case_id)
                else:
                    run_state["failed_case_ids"].append(case_id)
                run_state["running_case_count"] = len(run_state["running_case_ids"])
                run_state["completed_case_count"] = len(run_state["completed_case_ids"])
                run_state["failed_case_count"] = len(run_state["failed_case_ids"])
                run_state["updated_at"] = utc_now()
                write_run_state(run_dir, run_state)

                ordered = ordered_rows(results_by_case_id, case_order)
                write_summary_outputs(
                    run_dir,
                    ordered,
                    aggregate(ordered, total_case_count=len(cases), status="running"),
                    packet_id=packet_id,
                    partial=True,
                )
                print(
                    f"[completed {run_state['completed_case_count'] + run_state['failed_case_count']}/{len(cases)}] "
                    f"{case_id} -> {row.get('status')}",
                    flush=True,
                )
                submit_next(executor)

        run_state["status"] = "completed"
        run_state["completed_at"] = utc_now()
        run_state["updated_at"] = run_state["completed_at"]
        write_run_state(run_dir, run_state)
        ordered = ordered_rows(results_by_case_id, case_order)
        summary = aggregate(ordered, total_case_count=len(cases), status="completed")
        write_summary_outputs(run_dir, ordered, summary, packet_id=packet_id, partial=True)
        write_summary_outputs(run_dir, ordered, summary, packet_id=packet_id, partial=False)

        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"run_dir={run_dir}")
        return 0
    except KeyboardInterrupt:  # pragma: no cover - operational behavior
        run_state["status"] = "incomplete"
        run_state["completed_at"] = utc_now()
        run_state["updated_at"] = run_state["completed_at"]
        write_run_state(run_dir, run_state)
        ordered = ordered_rows(results_by_case_id, case_order)
        write_summary_outputs(
            run_dir,
            ordered,
            aggregate(ordered, total_case_count=len(cases), status="incomplete"),
            packet_id=packet_id,
            partial=True,
        )
        raise
    except Exception:  # pragma: no cover - operational behavior
        run_state["status"] = "failed"
        run_state["completed_at"] = utc_now()
        run_state["updated_at"] = run_state["completed_at"]
        write_run_state(run_dir, run_state)
        ordered = ordered_rows(results_by_case_id, case_order)
        write_summary_outputs(
            run_dir,
            ordered,
            aggregate(ordered, total_case_count=len(cases), status="failed"),
            packet_id=packet_id,
            partial=True,
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
    trace_context = eval_trace_context(
        run_dir,
        eval_target=f"dataset_case_design_audit:{packet_id}",
    )
