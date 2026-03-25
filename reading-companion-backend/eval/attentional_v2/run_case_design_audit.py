"""Audit benchmark case design for a review packet.

This evaluates the dataset cases themselves rather than the mechanism outputs.
It combines:
- factual excerpt/boundary checks
- a primary case-design review
- an adversarial disagreement review
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from src.iterator_reader.llm_utils import ReaderLLMError, invoke_json


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


def run_primary(case: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = invoke_json(
            PRIMARY_SYSTEM,
            PRIMARY_PROMPT.format(
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
            default=default_primary(),
        )
    except ReaderLLMError:
        return default_primary()
    except Exception:
        return default_primary()
    return normalize_primary(payload)


def run_adversarial(case: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    try:
        payload = invoke_json(
            ADVERSARIAL_SYSTEM,
            ADVERSARIAL_PROMPT.format(
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
            default=default_adversarial(),
        )
    except ReaderLLMError:
        return default_adversarial()
    except Exception:
        return default_adversarial()
    return normalize_adversarial(payload)


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    primary_decisions = Counter(str(row["primary_review"]["decision"]) for row in rows)
    adversarial_risks = Counter(str(row["adversarial_review"]["risk_level"]) for row in rows)
    factual_failures = sum(1 for row in rows if not bool(row["factual_audit"]["ok"]))
    return {
        "case_count": len(rows),
        "factual_failure_count": factual_failures,
        "primary_decisions": dict(primary_decisions),
        "adversarial_risk_counts": dict(adversarial_risks),
        "average_bucket_fit": round(mean(row["primary_review"]["bucket_fit"] for row in rows), 3) if rows else 0.0,
        "average_focus_clarity": round(mean(row["primary_review"]["focus_clarity"] for row in rows), 3) if rows else 0.0,
        "average_excerpt_strength": round(mean(row["primary_review"]["excerpt_strength"] for row in rows), 3) if rows else 0.0,
    }


def write_report(run_dir: Path, rows: list[dict[str, Any]], summary: dict[str, Any], *, packet_id: str) -> None:
    lines = [
        f"# Case Design Audit: `{packet_id}`",
        "",
        "## Summary",
        f"- case_count: `{summary['case_count']}`",
        f"- factual_failure_count: `{summary['factual_failure_count']}`",
        f"- primary_decisions: `{json.dumps(summary['primary_decisions'], ensure_ascii=False)}`",
        f"- adversarial_risk_counts: `{json.dumps(summary['adversarial_risk_counts'], ensure_ascii=False)}`",
        f"- average_bucket_fit: `{summary['average_bucket_fit']}`",
        f"- average_focus_clarity: `{summary['average_focus_clarity']}`",
        f"- average_excerpt_strength: `{summary['average_excerpt_strength']}`",
        "",
        "## Flagged Cases",
    ]
    for row in rows:
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
    (run_dir / "summary" / "report.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-id")
    parser.add_argument("--packet-dir")
    parser.add_argument("--limit", type=int, default=0)
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

    run_id = f"{packet_id}__{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index}/{len(cases)}] {case.get('case_id')}")
        factual = factual_audit(case, source_index)
        _, context = find_span_and_context(case, source_index) if factual.get("ok") else ({}, {"lookback_sentences": [], "excerpt_sentences": [], "lookahead_sentences": []})
        primary = run_primary(case, context)
        adversarial = run_adversarial(case, context)
        row = {
            "case_id": case.get("case_id"),
            "case_title": case.get("case_title"),
            "packet_id": packet_id,
            "factual_audit": factual,
            "primary_review": primary,
            "adversarial_review": adversarial,
        }
        results.append(row)
        write_json(run_dir / "cases" / f"{case.get('case_id')}.json", row)

    summary = aggregate(results)
    write_json(run_dir / "summary" / "aggregate.json", summary)
    write_jsonl(run_dir / "summary" / "case_results.jsonl", results)
    write_report(run_dir, results, summary, packet_id=packet_id)

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"run_dir={run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
