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
import hashlib
import json
import os
import re
import time
import unicodedata
from collections import Counter
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Callable

from src.iterator_reader.llm_utils import (
    LLMInvocationOverrides,
    LLMTraceContext,
    ReaderLLMError,
    eval_trace_context,
    invoke_json,
    llm_invocation_scope,
)
from src.reading_runtime.job_concurrency import resolve_worker_policy, submit_inherited_context
from src.reading_runtime.llm_registry import DEFAULT_DATASET_REVIEW_PROFILE_ID
from src.reading_runtime.provisioning import ensure_canonical_parse

from .case_audit_runs import (
    AGGREGATE_FILE,
    PARTIAL_AGGREGATE_FILE,
    PARTIAL_REPORT_FILE,
    REPORT_FILE,
    RUN_STATE_FILE,
    SUMMARY_DIR,
    latest_case_audit_run,
)
from .question_aligned_case_construction import render_excerpt_sentences


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
SEMANTIC_VALIDATION_ATTEMPTS = 3
AUDIT_PROMPT_CONTRACT_VERSION = "case_design_audit_v4"
AUDIT_REVIEW_OVERRIDES = LLMInvocationOverrides(temperature=0.0)
PRIMARY_REVIEW_REPLICA_COUNT = 3
PRIMARY_REVIEW_CALLBACK_ESCALATION_REPLICA_COUNT = 2
PRIMARY_REVIEW_CONSENSUS_POLICY = "majority_vote_median_scores_conservative_tiebreak"
PRIMARY_REVIEW_CALLBACK_ESCALATION_POLICY = (
    "majority_vote_median_scores_conservative_tiebreak_callback_inline_target_escalation"
)
CASE_QUOTA_RECOVERY_PASSES = 2

PRIMARY_SYSTEM = """You audit benchmark case design for a reading-mechanism evaluation dataset.

You are not judging the mechanism output. You are judging whether the case itself is strong enough to trust.

Return JSON only."""

PRIMARY_PROMPT = """Case metadata:
{case_json}

Immediate context:
{context_json}

Decide whether this is a strong benchmark case for its current purpose.

Scoring rules:
- `bucket_fit_band`, `focus_clarity_band`, and `excerpt_strength_band` use `strong|adequate|weak`
- `strong` means benchmark-worthy now on that axis
- `adequate` means promising but not yet strong on that axis
- `weak` means materially weak on that axis
- For `callback` / `cross_span_link` style cases:
  - it is acceptable for the earlier bridge target to appear inside the excerpt when the anchor line makes the inferential backlink explicit and sharply traceable
  - if the supposed callback is only broad thematic continuation, or the target/anchor relation is not clearly signaled, prefer `revise` or `drop` for `ambiguous_focus`
- Keep the bands coherent with the decision:
  - `keep` means no axis is `weak` and at most one axis is `adequate`
  - `revise` means more than one axis is `adequate`, or any axis is `weak` but still salvageable
  - `drop` should reflect materially weak fit or excerpt integrity
- Prefer the smallest stable `problem_types` set that explains the decision.
  - do not list multiple overlapping problem types unless the case clearly needs them
  - if the main defect is focus, prefer `ambiguous_focus`
  - if the main defect is excerpt quality or span integrity, prefer `weak_excerpt`
  - use `source_parse_problem` or `text_noise` only when the excerpt itself clearly shows that kind of defect

Return JSON:
{{
  "decision": "keep|revise|drop|unclear",
  "confidence": "high|medium|low",
  "problem_types": ["wrong_bucket|weak_excerpt|ambiguous_focus|text_noise|duplicate_case|too_easy|too_hard|source_parse_problem|other"],
  "bucket_fit_band": "strong|adequate|weak",
  "focus_clarity_band": "strong|adequate|weak",
  "excerpt_strength_band": "strong|adequate|weak",
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

- For `callback` / `cross_span_link` style cases, do not treat an inline earlier bridge target as a defect by itself.
- Only attack callback framing when the target/anchor relation is actually incoherent, weakly signaled, or thematically loose.

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


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _fingerprint(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _prompt_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
        for key in ("books", "source_refs"):
            entries = payload.get(key, [])
            if not isinstance(entries, list):
                continue
            for item in entries:
                if isinstance(item, dict) and item.get("source_id"):
                    source_id = str(item["source_id"])
                    existing = sources.get(source_id, {})
                    sources[source_id] = {**existing, **dict(item)}
    return sources


def default_context() -> dict[str, list[str]]:
    return {
        "lookback_sentences": [],
        "excerpt_sentences": [],
        "lookahead_sentences": [],
    }


def _case_prompt_inputs(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": str(case.get("case_id", "")).strip(),
        "case_title": str(case.get("case_title", "")).strip(),
        "target_profile_id": str(case.get("target_profile_id", "")).strip(),
        "selection_role": str(case.get("selection_role", "")).strip(),
        "question_ids": list(case.get("question_ids") or []),
        "phenomena": list(case.get("phenomena") or []),
        "selection_reason": str(case.get("selection_reason", "")).strip(),
        "judge_focus": str(case.get("judge_focus", "")).strip(),
        "prior_context_text": str(
            case.get("prior_context_text")
            or case.get("prior_context_excerpt_text")
            or ""
        ).strip(),
        "excerpt_text": str(case.get("excerpt_text", "")).strip(),
    }


def _context_prompt_inputs(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "lookback_sentences": [str(item).strip() for item in list(context.get("lookback_sentences") or [])],
        "excerpt_sentences": [str(item).strip() for item in list(context.get("excerpt_sentences") or [])],
        "lookahead_sentences": [str(item).strip() for item in list(context.get("lookahead_sentences") or [])],
    }


def _primary_user_prompt_from_inputs(case_inputs: dict[str, Any], context_inputs: dict[str, Any]) -> str:
    return PRIMARY_PROMPT.format(
        case_json=json.dumps(case_inputs, ensure_ascii=False, indent=2),
        context_json=json.dumps(context_inputs, ensure_ascii=False, indent=2),
    )


def _adversarial_user_prompt_from_inputs(case_inputs: dict[str, Any], context_inputs: dict[str, Any]) -> str:
    return ADVERSARIAL_PROMPT.format(
        case_json=json.dumps(case_inputs, ensure_ascii=False, indent=2),
        context_json=json.dumps(context_inputs, ensure_ascii=False, indent=2),
    )


def normalize_audit_prompt_input_payload(value: Any) -> dict[str, Any]:
    payload = dict(value) if isinstance(value, dict) else {}
    case_inputs = _case_prompt_inputs(dict(payload.get("case") or {}))
    context_inputs = _context_prompt_inputs(dict(payload.get("context") or {}))
    prompt_hashes_raw = dict(payload.get("prompt_hashes") or {}) if isinstance(payload.get("prompt_hashes"), dict) else {}
    prompt_hashes = {
        "primary_system_prompt_hash": str(prompt_hashes_raw.get("primary_system_prompt_hash", "")).strip(),
        "primary_user_prompt_hash": str(prompt_hashes_raw.get("primary_user_prompt_hash", "")).strip(),
        "adversarial_system_prompt_hash": str(prompt_hashes_raw.get("adversarial_system_prompt_hash", "")).strip(),
        "adversarial_user_prompt_hash": str(prompt_hashes_raw.get("adversarial_user_prompt_hash", "")).strip(),
    }
    if not any(case_inputs.values()) and not any(context_inputs.values()) and not any(prompt_hashes.values()):
        return {}
    return {
        "audit_prompt_contract_version": str(
            payload.get("audit_prompt_contract_version", AUDIT_PROMPT_CONTRACT_VERSION)
        ).strip()
        or AUDIT_PROMPT_CONTRACT_VERSION,
        "case": case_inputs,
        "context": context_inputs,
        "prompt_hashes": prompt_hashes,
    }


def build_audit_prompt_input_payload(case: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    case_inputs = _case_prompt_inputs(case)
    context_inputs = _context_prompt_inputs(context)
    return normalize_audit_prompt_input_payload(
        {
            "audit_prompt_contract_version": AUDIT_PROMPT_CONTRACT_VERSION,
            "case": case_inputs,
            "context": context_inputs,
            "prompt_hashes": {
                "primary_system_prompt_hash": _prompt_hash(PRIMARY_SYSTEM),
                "primary_user_prompt_hash": _prompt_hash(
                    _primary_user_prompt_from_inputs(case_inputs, context_inputs)
                ),
                "adversarial_system_prompt_hash": _prompt_hash(ADVERSARIAL_SYSTEM),
                "adversarial_user_prompt_hash": _prompt_hash(
                    _adversarial_user_prompt_from_inputs(case_inputs, context_inputs)
                ),
            },
        }
    )


def audit_run_input_fingerprint(case_input_fingerprints: dict[str, str]) -> str:
    normalized = {
        case_id: str(case_input_fingerprints[case_id]).strip()
        for case_id in sorted(case_input_fingerprints)
        if str(case_input_fingerprints[case_id]).strip()
    }
    if not normalized:
        return ""
    return _fingerprint(
        {
            "audit_prompt_contract_version": AUDIT_PROMPT_CONTRACT_VERSION,
            "case_input_fingerprints": normalized,
        }
    )


def _chapter_sentence_index(book_document: dict[str, Any]) -> dict[int, tuple[list[dict[str, Any]], dict[str, int]]]:
    index: dict[int, tuple[list[dict[str, Any]], dict[str, int]]] = {}
    for chapter in book_document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        chapter_id = int(chapter.get("id", 0) or 0)
        if chapter_id <= 0:
            continue
        sentences = [item for item in chapter.get("sentences", []) if isinstance(item, dict)]
        by_id = {str(sentence.get("sentence_id", "")): idx for idx, sentence in enumerate(sentences)}
        index[chapter_id] = (sentences, by_id)
    return index


def _resolve_span_from_ids(
    *,
    case_id: str,
    chapter_index: dict[int, tuple[list[dict[str, Any]], dict[str, int]]],
    chapter_id: int,
    start_sentence_id: str,
    end_sentence_id: str,
) -> tuple[list[dict[str, Any]], int, int]:
    chapter_payload = chapter_index.get(chapter_id)
    if chapter_payload is None:
        raise ValueError(f"Chapter missing for {case_id}")
    sentences, by_id = chapter_payload
    if start_sentence_id not in by_id or end_sentence_id not in by_id:
        raise ValueError(f"Sentence ids missing for {case_id}")
    start = by_id[start_sentence_id]
    end = by_id[end_sentence_id]
    return sentences[start : end + 1], start, end


def _find_multi_anchor_span_and_context(
    case: dict[str, Any],
    *,
    output_dir: Path,
    book_document_path: Path,
    book_document: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    anchor_refs = [dict(item) for item in (case.get("anchor_refs") or []) if isinstance(item, dict)]
    if not anchor_refs:
        raise ValueError(f"Missing anchor_refs for {case.get('case_id')}")
    chapter_index = _chapter_sentence_index(book_document)
    excerpt_lines: list[str] = []
    excerpt_sentences: list[str] = []
    anchor_span_resolutions: list[dict[str, Any]] = []
    first_span_context: tuple[list[dict[str, Any]], int] | None = None
    last_span_context: tuple[list[dict[str, Any]], int] | None = None
    for anchor in anchor_refs:
        stage = str(anchor.get("stage", "")).strip().upper() or "MID"
        chapter_id = int(anchor["chapter_id"])
        start_sentence_id = str(anchor["start_sentence_id"])
        end_sentence_id = str(anchor["end_sentence_id"])
        excerpt_rows, start, end = _resolve_span_from_ids(
            case_id=str(case.get("case_id", "")),
            chapter_index=chapter_index,
            chapter_id=chapter_id,
            start_sentence_id=start_sentence_id,
            end_sentence_id=end_sentence_id,
        )
        excerpt_text = render_excerpt_sentences(str(sentence.get("text", "")).strip() for sentence in excerpt_rows)
        excerpt_lines.append(f"{stage} ({chapter_id}): {excerpt_text}")
        excerpt_sentences.extend(str(sentence.get("text", "")).strip() for sentence in excerpt_rows)
        anchor_span_resolutions.append(
            {
                "stage": stage.lower(),
                "anchor_kind": str(anchor.get("anchor_kind", "")).strip(),
                "source_ref_id": str(anchor.get("source_ref_id", "")).strip(),
                "chapter_id": chapter_id,
                "start_sentence_id": start_sentence_id,
                "end_sentence_id": end_sentence_id,
                "excerpt_text_reconstructed": excerpt_text,
                "expected_anchor_excerpt_text": str(anchor.get("excerpt_text", "")).strip(),
            }
        )
        sentences, _ = chapter_index[chapter_id]
        if first_span_context is None:
            first_span_context = (sentences, start)
        last_span_context = (sentences, end)
    lookback_sentences: list[str] = []
    if first_span_context is not None:
        sentences, start = first_span_context
        lookback_sentences = [str(item.get("text", "")).strip() for item in sentences[max(0, start - 2) : start]]
    lookahead_sentences: list[str] = []
    if last_span_context is not None:
        sentences, end = last_span_context
        lookahead_sentences = [str(item.get("text", "")).strip() for item in sentences[end + 1 : end + 3]]
    return (
        {
            "source_id": case.get("source_id"),
            "output_dir": str(output_dir),
            "book_document_path": str(book_document_path),
            "excerpt_text_reconstructed": "\n".join(excerpt_lines),
            "expected_excerpt_text": str(case.get("excerpt_text", "")).strip(),
            "prior_context_sentence_ids": [
                str(sentence_id).strip()
                for sentence_id in (case.get("prior_context_sentence_ids") or [])
                if str(sentence_id).strip()
            ],
            "anchor_span_resolutions": anchor_span_resolutions,
        },
        {
            "lookback_sentences": lookback_sentences,
            "excerpt_sentences": excerpt_sentences,
            "lookahead_sentences": lookahead_sentences,
        },
    )


def _book_document_for_source(source: dict[str, Any]) -> tuple[Path, Path, dict[str, Any]]:
    output_dir_value = str(source.get("output_dir", "")).strip()
    if output_dir_value:
        output_dir = (ROOT / output_dir_value).resolve()
        book_document_path = output_dir / "public" / "book_document.json"
        if book_document_path.exists():
            return output_dir, book_document_path, load_json(book_document_path)
    relative_local_path = str(source.get("relative_local_path", "")).strip()
    if relative_local_path:
        book_path = (ROOT / relative_local_path).resolve()
        if not book_path.exists():
            raise FileNotFoundError(book_path)
        language_mode = str(source.get("output_language") or source.get("language") or "auto").strip() or "auto"
        provisioned = ensure_canonical_parse(book_path, language_mode=language_mode)
        book_document = provisioned.book_document
        if not isinstance(book_document, dict):
            raise ValueError(f"Missing canonical book document for {book_path}")
        output_dir = Path(provisioned.output_dir).resolve()
        book_document_path = output_dir / "public" / "book_document.json"
        return output_dir, book_document_path, book_document
    raise KeyError("output_dir")


def find_span_and_context(case: dict[str, Any], source_index: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    source = source_index.get(str(case.get("source_id", "")))
    if not source:
        raise ValueError(f"Missing source metadata for {case.get('case_id')}")
    output_dir, book_document_path, book_document = _book_document_for_source(source)
    if case.get("anchor_refs"):
        return _find_multi_anchor_span_and_context(
            case,
            output_dir=output_dir,
            book_document_path=book_document_path,
            book_document=book_document,
        )
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
        excerpt_text = render_excerpt_sentences(
            str(sentence.get("text", "")).strip() for sentence in excerpt_rows
        )
        prior_context_sentence_ids = [
            str(sentence_id).strip()
            for sentence_id in (case.get("prior_context_sentence_ids") or [])
            if str(sentence_id).strip() in by_id and by_id[str(sentence_id).strip()] < start
        ]
        if prior_context_sentence_ids:
            lookback_rows = [sentences[by_id[sentence_id]] for sentence_id in prior_context_sentence_ids]
        else:
            lookback_rows = sentences[max(0, start - 3) : start]
        context = {
            "lookback_sentences": [str(item.get("text", "")).strip() for item in lookback_rows],
            "excerpt_sentences": [str(item.get("text", "")).strip() for item in excerpt_rows],
            "lookahead_sentences": [str(item.get("text", "")).strip() for item in sentences[end + 1 : end + 3]],
        }
        return {
            "source_id": case.get("source_id"),
            "output_dir": str(output_dir),
            "book_document_path": str(book_document_path),
            "excerpt_text_reconstructed": excerpt_text,
            "expected_excerpt_text": str(case.get("excerpt_text", "")).strip(),
            "prior_context_sentence_ids": prior_context_sentence_ids,
        }, context
    raise ValueError(f"Chapter missing for {case.get('case_id')}")


def normalize_excerpt_text_for_compare(text: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or "").strip())
    normalized = "".join(char for char in normalized if unicodedata.category(char) != "Cf")
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


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
    issues: list[str] = []
    anchor_span_resolutions = [
        dict(item)
        for item in list(span_info.get("anchor_span_resolutions") or [])
        if isinstance(item, dict)
    ]
    if anchor_span_resolutions:
        has_excerpt_anchor_mismatch = False
        for resolution in anchor_span_resolutions:
            expected_anchor = normalize_excerpt_text_for_compare(resolution.get("expected_anchor_excerpt_text", ""))
            reconstructed_anchor = normalize_excerpt_text_for_compare(resolution.get("excerpt_text_reconstructed", ""))
            if expected_anchor == reconstructed_anchor:
                continue
            if str(resolution.get("anchor_kind", "")).strip() == "note_entry":
                continue
            has_excerpt_anchor_mismatch = True
            break
        if has_excerpt_anchor_mismatch:
            issues.append("excerpt_text_mismatch")
        normalized_expected = normalize_excerpt_text_for_compare(case.get("excerpt_text", ""))
        normalized_reconstructed = normalize_excerpt_text_for_compare(span_info["excerpt_text_reconstructed"])
    else:
        excerpt_text = span_info["expected_excerpt_text"]
        reconstructed = span_info["excerpt_text_reconstructed"]
        normalized_expected = normalize_excerpt_text_for_compare(excerpt_text)
        normalized_reconstructed = normalize_excerpt_text_for_compare(reconstructed)
        if normalized_expected != normalized_reconstructed:
            issues.append("excerpt_text_mismatch")
        excerpt_text = str(excerpt_text)
    excerpt_text = str(case.get("excerpt_text", "")).strip()
    lowered = excerpt_text.lower()
    if any(marker in lowered for marker in BOILERPLATE_MARKERS):
        issues.append("boilerplate_marker_present")
    return {
        "ok": not issues,
        "issues": issues,
        "normalized_expected_excerpt_text": normalized_expected,
        "normalized_excerpt_text_reconstructed": normalized_reconstructed,
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


def _consensus_mode(values: list[str], *, tie_order: list[str], default: str) -> str:
    cleaned = [str(value).strip().lower() for value in values if str(value).strip()]
    if not cleaned:
        return default
    counts = Counter(cleaned)
    best_count = max(counts.values())
    tied = {value for value, count in counts.items() if count == best_count}
    for candidate in tie_order:
        if candidate in tied:
            return candidate
    return cleaned[0]


def _median_int(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(int(value) for value in values)
    return ordered[len(ordered) // 2]


def _pick_primary_exemplar_index(
    payloads: list[dict[str, Any]],
    consensus: dict[str, Any],
) -> int:
    if not payloads:
        return 0

    def _score(payload: dict[str, Any]) -> tuple[int, int]:
        matches = 0
        if str(payload.get("decision", "")).strip().lower() == consensus["decision"]:
            matches += 3
        if str(payload.get("confidence", "")).strip().lower() == consensus["confidence"]:
            matches += 1
        for field in ("bucket_fit", "focus_clarity", "excerpt_strength"):
            try:
                payload_score = int(payload.get(field, 0))
            except (TypeError, ValueError):
                payload_score = 0
            if payload_score == consensus[field]:
                matches += 1
        payload_problem_types = sorted(
            str(item).strip() for item in list(payload.get("problem_types") or []) if str(item).strip()
        )
        if payload_problem_types == consensus["problem_types"]:
            matches += 1
        return matches, -payloads.index(payload)

    return max(range(len(payloads)), key=lambda index: _score(payloads[index]))


def _is_callback_case(case: dict[str, Any]) -> bool:
    title = str(case.get("case_title", "")).strip().lower()
    selection_reason = str(case.get("selection_reason", "")).strip().lower()
    judge_focus = str(case.get("judge_focus", "")).strip().lower()
    phenomena = {
        str(item).strip().lower()
        for item in list(case.get("phenomena") or [])
        if str(item).strip()
    }
    if "callback_bridge" in title:
        return True
    if {"callback", "cross_span_link", "bridge_potential"}.intersection(phenomena):
        return True
    return "backward bridge" in selection_reason or "backward bridge" in judge_focus


def _callback_case_needs_replica_escalation(
    case: dict[str, Any],
    normalized_payloads: list[dict[str, Any]],
) -> bool:
    if not _is_callback_case(case):
        return False
    if len(normalized_payloads) < PRIMARY_REVIEW_REPLICA_COUNT:
        return False
    inline_target = "earlier bridge target:" in str(case.get("selection_reason", "")).strip().lower()
    if inline_target and not list(case.get("prior_context_sentence_ids") or []):
        return True
    decisions = {
        str(payload.get("decision", "")).strip().lower()
        for payload in normalized_payloads
        if str(payload.get("decision", "")).strip()
    }
    if len(decisions) > 1:
        return True
    problem_type_sets = {
        tuple(sorted(str(item).strip() for item in list(payload.get("problem_types") or []) if str(item).strip()))
        for payload in normalized_payloads
    }
    return len(problem_type_sets) > 1


def summarize_primary_consensus(payloads: list[dict[str, Any]]) -> tuple[dict[str, Any], int]:
    normalized_payloads = [normalize_primary(payload) for payload in payloads]
    if not normalized_payloads:
        return default_primary(), 0

    consensus = default_primary()
    consensus["decision"] = _consensus_mode(
        [payload.get("decision", "") for payload in normalized_payloads],
        tie_order=["drop", "revise", "unclear", "keep"],
        default=consensus["decision"],
    )
    consensus["confidence"] = _consensus_mode(
        [payload.get("confidence", "") for payload in normalized_payloads],
        tie_order=["low", "medium", "high"],
        default=consensus["confidence"],
    )
    for field in ("bucket_fit", "focus_clarity", "excerpt_strength"):
        consensus[field] = _median_int(
            [int(payload.get(field, 0) or 0) for payload in normalized_payloads]
        )

    fallback_exemplar_index = _pick_primary_exemplar_index(normalized_payloads, consensus)
    fallback_exemplar = normalized_payloads[fallback_exemplar_index]

    if consensus["decision"] == "keep":
        consensus["problem_types"] = []
        consensus["revised_bucket"] = ""
        consensus["revised_selection_reason"] = ""
        consensus["revised_judge_focus"] = ""
    else:
        problem_type_counts = Counter(
            str(problem_type).strip()
            for payload in normalized_payloads
            for problem_type in list(payload.get("problem_types") or [])
            if str(problem_type).strip()
        )
        majority_threshold = len(normalized_payloads) // 2 + 1
        consensus["problem_types"] = sorted(
            problem_type
            for problem_type, count in problem_type_counts.items()
            if count >= majority_threshold
        )
        if consensus["decision"] in {"revise", "drop"} and not consensus["problem_types"]:
            consensus["problem_types"] = list(fallback_exemplar.get("problem_types") or []) or ["other"]
        for field in ("revised_bucket", "revised_selection_reason", "revised_judge_focus"):
            candidate_values = [
                str(payload.get(field, "")).strip()
                for payload in normalized_payloads
                if str(payload.get(field, "")).strip()
            ]
            consensus[field] = _consensus_mode(
                candidate_values,
                tie_order=sorted(set(candidate_values)),
                default="",
            )

    final_consensus = normalize_primary(consensus)
    exemplar_index = _pick_primary_exemplar_index(normalized_payloads, final_consensus)
    final_consensus["notes"] = (
        str(normalized_payloads[exemplar_index].get("notes", "")).strip() or final_consensus["notes"]
    )
    return final_consensus, exemplar_index


def normalize_primary(payload: Any) -> dict[str, Any]:
    normalized = default_primary()
    if not isinstance(payload, dict):
        return normalized

    def _score_fields() -> tuple[str, str, str]:
        return ("bucket_fit", "focus_clarity", "excerpt_strength")

    def _band_from_score(score: int) -> str:
        if score >= 4:
            return "strong"
        if score >= 3:
            return "adequate"
        if score >= 1:
            return "weak"
        return ""

    def _score_from_band(band: str) -> int:
        return {
            "strong": 4,
            "adequate": 3,
            "weak": 2,
        }.get(band, 0)

    def _derived_decision(axis_scores: dict[str, int], raw_decision: str) -> str:
        if raw_decision in {"drop", "unclear"}:
            return raw_decision
        if raw_decision == "keep" and any(score <= 2 for score in axis_scores.values()):
            return "keep"
        weak_count = sum(1 for score in axis_scores.values() if score <= 2)
        adequate_count = sum(1 for score in axis_scores.values() if score == 3)
        strong_count = sum(1 for score in axis_scores.values() if score >= 4)
        if weak_count == 0 and adequate_count <= 1 and strong_count >= 2:
            return "keep"
        return "revise"

    def _canonical_problem_types(
        raw_problem_types: list[str],
        axis_scores: dict[str, int],
        decision: str,
    ) -> list[str]:
        if decision == "keep":
            return []
        ordered_types: list[str] = []

        def _append(problem_type: str) -> None:
            if problem_type not in ordered_types:
                ordered_types.append(problem_type)

        if axis_scores["bucket_fit"] <= 2 and "wrong_bucket" in raw_problem_types:
            _append("wrong_bucket")
        if axis_scores["excerpt_strength"] <= 2:
            _append("weak_excerpt")
        elif axis_scores["excerpt_strength"] == 3 and "weak_excerpt" in raw_problem_types:
            _append("weak_excerpt")
        if axis_scores["focus_clarity"] <= 2:
            _append("ambiguous_focus")
        elif axis_scores["focus_clarity"] == 3 and "ambiguous_focus" in raw_problem_types:
            _append("ambiguous_focus")
        if axis_scores["bucket_fit"] == 3 and "wrong_bucket" in raw_problem_types:
            _append("wrong_bucket")

        for problem_type in (
            "source_parse_problem",
            "text_noise",
            "duplicate_case",
            "too_easy",
            "too_hard",
        ):
            if problem_type in raw_problem_types:
                _append(problem_type)

        if not ordered_types and raw_problem_types and "other" not in raw_problem_types:
            _append(raw_problem_types[0])
        if not ordered_types:
            _append("other")
        return ordered_types

    decision = str(payload.get("decision", "")).strip().lower()
    if decision in {"keep", "revise", "drop", "unclear"}:
        normalized["decision"] = decision
    confidence = str(payload.get("confidence", "")).strip().lower()
    if confidence in {"high", "medium", "low"}:
        normalized["confidence"] = confidence
    band_fields = {
        "bucket_fit": str(payload.get("bucket_fit_band", "")).strip().lower(),
        "focus_clarity": str(payload.get("focus_clarity_band", "")).strip().lower(),
        "excerpt_strength": str(payload.get("excerpt_strength_band", "")).strip().lower(),
    }
    for field in ("bucket_fit", "focus_clarity", "excerpt_strength"):
        band = band_fields[field]
        if band not in {"strong", "adequate", "weak"}:
            try:
                score = int(payload.get(field, 0))
            except (TypeError, ValueError):
                score = 0
            band = _band_from_score(max(0, min(5, score)))
        normalized[field] = _score_from_band(band)
    if isinstance(payload.get("problem_types"), list):
        normalized["problem_types"] = [str(item).strip() for item in payload["problem_types"] if str(item).strip()]
    normalized["revised_bucket"] = str(payload.get("revised_bucket", "")).strip()
    normalized["revised_selection_reason"] = str(payload.get("revised_selection_reason", "")).strip()
    normalized["revised_judge_focus"] = str(payload.get("revised_judge_focus", "")).strip()
    normalized["notes"] = str(payload.get("notes", "")).strip() or normalized["notes"]
    axis_scores = {field: int(normalized[field]) for field in _score_fields()}
    normalized["decision"] = _derived_decision(axis_scores, normalized["decision"])
    normalized["problem_types"] = _canonical_problem_types(
        list(normalized["problem_types"]),
        axis_scores,
        normalized["decision"],
    )
    if normalized["decision"] == "keep":
        for field in _score_fields():
            normalized[field] = 4
        normalized["problem_types"] = []
        normalized["revised_bucket"] = ""
        normalized["revised_selection_reason"] = ""
        normalized["revised_judge_focus"] = ""
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


def primary_validation_issue(payload: dict[str, Any]) -> str:
    if str(payload.get("notes", "")).strip() == default_primary()["notes"]:
        return "primary_review_unavailable"
    for field in ("bucket_fit", "focus_clarity", "excerpt_strength"):
        try:
            score = int(payload.get(field, 0))
        except (TypeError, ValueError):
            score = 0
        if score < 1:
            return f"invalid_{field}"
    return ""


def adversarial_validation_issue(payload: dict[str, Any]) -> str:
    if str(payload.get("challenge_summary", "")).strip() == default_adversarial()["challenge_summary"]:
        return "adversarial_review_unavailable"
    return ""


class AuditStageError(RuntimeError):
    """Raised when an audit stage cannot produce a usable normalized payload."""

    def __init__(
        self,
        message: str,
        *,
        stage_name: str,
        metadata: dict[str, Any],
        normalized_payload: dict[str, Any],
    ) -> None:
        super().__init__(message)
        self.stage_name = stage_name
        self.metadata = metadata
        self.normalized_payload = normalized_payload


def invoke_review_with_meta(
    *,
    stage_name: str,
    system_prompt: str,
    user_prompt: str,
    default_payload: dict[str, Any],
    normalize: Callable[[Any], dict[str, Any]],
    validation_error: Callable[[dict[str, Any]], str],
    scope_overrides: LLMInvocationOverrides | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    last_metadata: dict[str, Any] | None = None
    last_normalized = dict(default_payload)

    for semantic_attempt in range(1, SEMANTIC_VALIDATION_ATTEMPTS + 1):
        started_at = utc_now()
        started_perf = time.perf_counter()
        error: Exception | None = None
        status = "ok"
        validation_issue = ""

        try:
            with llm_invocation_scope(
                trace_context=LLMTraceContext(stage="case_design_audit", node=stage_name),
                overrides=scope_overrides,
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

        normalized = normalize(payload)
        last_normalized = normalized
        validation_issue = validation_error(normalized)
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
            "semantic_attempt_count": semantic_attempt,
            "semantic_retry_count": semantic_attempt - 1,
            "validation_issue": validation_issue,
        }
        last_metadata = metadata

        if error is None and not validation_issue:
            return normalized, metadata

        if semantic_attempt >= SEMANTIC_VALIDATION_ATTEMPTS:
            failure_reason = validation_issue or status
            raise AuditStageError(
                f"{stage_name} failed to produce a usable payload: {failure_reason}",
                stage_name=stage_name,
                metadata={
                    **metadata,
                    "status": "response_validation_failed" if validation_issue else status,
                },
                normalized_payload=normalized,
            )

        time.sleep(min(1.0, 0.2 * semantic_attempt))

    raise AuditStageError(
        f"{stage_name} failed to produce a usable payload.",
        stage_name=stage_name,
        metadata=last_metadata or {"stage": stage_name, "status": "response_validation_failed"},
        normalized_payload=last_normalized,
    )


def run_primary(case: dict[str, Any], context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    case_inputs = _case_prompt_inputs(case)
    context_inputs = _context_prompt_inputs(context)
    # Keep audit-stage scoring reproducible without changing the shared profile's throughput policy.
    replica_payloads: list[dict[str, Any]] = []
    replica_metadata: list[dict[str, Any]] = []
    system_prompt = PRIMARY_SYSTEM
    user_prompt = _primary_user_prompt_from_inputs(case_inputs, context_inputs)

    for replica_index in range(PRIMARY_REVIEW_REPLICA_COUNT):
        payload, metadata = invoke_review_with_meta(
            stage_name=f"primary_review_replica_{replica_index + 1}",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            default_payload=default_primary(),
            normalize=normalize_primary,
            validation_error=primary_validation_issue,
            scope_overrides=AUDIT_REVIEW_OVERRIDES,
        )
        replica_payloads.append(payload)
        replica_metadata.append(metadata)

    escalated = False
    if _callback_case_needs_replica_escalation(case, replica_payloads):
        escalated = True
        for replica_index in range(
            PRIMARY_REVIEW_REPLICA_COUNT,
            PRIMARY_REVIEW_REPLICA_COUNT + PRIMARY_REVIEW_CALLBACK_ESCALATION_REPLICA_COUNT,
        ):
            payload, metadata = invoke_review_with_meta(
                stage_name=f"primary_review_replica_{replica_index + 1}",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                default_payload=default_primary(),
                normalize=normalize_primary,
                validation_error=primary_validation_issue,
                scope_overrides=AUDIT_REVIEW_OVERRIDES,
            )
            replica_payloads.append(payload)
            replica_metadata.append(metadata)

    consensus_payload, exemplar_index = summarize_primary_consensus(replica_payloads)
    return consensus_payload, {
        "stage": "primary_review",
        "status": "ok",
        "started_at": replica_metadata[0]["started_at"] if replica_metadata else "",
        "completed_at": replica_metadata[-1]["completed_at"] if replica_metadata else "",
        "duration_ms": sum(int(metadata.get("duration_ms", 0) or 0) for metadata in replica_metadata),
        "replica_count": len(replica_metadata),
        "selection_policy": (
            PRIMARY_REVIEW_CALLBACK_ESCALATION_POLICY if escalated else PRIMARY_REVIEW_CONSENSUS_POLICY
        ),
        "callback_replica_escalation_applied": escalated,
        "base_replica_count": PRIMARY_REVIEW_REPLICA_COUNT,
        "selected_replica_index": exemplar_index,
        "consensus_decision": consensus_payload["decision"],
        "consensus_problem_types": list(consensus_payload["problem_types"]),
        "replicas": replica_metadata,
        "semantic_attempt_count": sum(
            int(metadata.get("semantic_attempt_count", 0) or 0) for metadata in replica_metadata
        ),
        "semantic_retry_count": sum(
            int(metadata.get("semantic_retry_count", 0) or 0) for metadata in replica_metadata
        ),
        "validation_issue": "",
    }


def run_adversarial(case: dict[str, Any], context: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    case_inputs = _case_prompt_inputs(case)
    context_inputs = _context_prompt_inputs(context)
    return invoke_review_with_meta(
        stage_name="adversarial_review",
        system_prompt=ADVERSARIAL_SYSTEM,
        user_prompt=_adversarial_user_prompt_from_inputs(case_inputs, context_inputs),
        default_payload=default_adversarial(),
        normalize=normalize_adversarial,
        validation_error=adversarial_validation_issue,
        scope_overrides=AUDIT_REVIEW_OVERRIDES,
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
    case_input_fingerprints = {
        str(row.get("case_id", "")).strip(): str(row.get("audit_prompt_input_fingerprint", "")).strip()
        for row in rows
        if str(row.get("case_id", "")).strip() and str(row.get("audit_prompt_input_fingerprint", "")).strip()
    }
    quota_recovery_entries = [
        quota_recovery
        for row in rows
        for quota_recovery in [((row.get("audit_metadata") or {}).get("quota_recovery") or {})]
        if isinstance(quota_recovery, dict)
    ]
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
        "quota_recovery_attempted_count": sum(
            int(entry.get("quota_recovery_attempted_count", 0) or 0) for entry in quota_recovery_entries
        ),
        "quota_recovery_succeeded_count": sum(
            int(entry.get("quota_recovery_succeeded_count", 0) or 0) for entry in quota_recovery_entries
        ),
        "quota_failure_remaining_count": sum(
            int(entry.get("quota_failure_remaining_count", 0) or 0) for entry in quota_recovery_entries
        ),
        "quota_recovery_passes_used": sum(
            int(entry.get("quota_recovery_passes_used", 0) or 0) for entry in quota_recovery_entries
        ),
        "audit_prompt_contract_version": AUDIT_PROMPT_CONTRACT_VERSION,
        "case_input_fingerprints": dict(sorted(case_input_fingerprints.items())),
        "run_audit_prompt_input_fingerprint": audit_run_input_fingerprint(case_input_fingerprints),
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
        f"- quota_recovery_attempted_count: `{summary['quota_recovery_attempted_count']}`",
        f"- quota_recovery_succeeded_count: `{summary['quota_recovery_succeeded_count']}`",
        f"- quota_failure_remaining_count: `{summary['quota_failure_remaining_count']}`",
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


def _fallback_completed_case_state(
    packet_id: str,
    case_id: str,
    row: dict[str, Any],
) -> dict[str, Any]:
    audit_metadata = row.get("audit_metadata") or {}
    if not isinstance(audit_metadata, dict):
        audit_metadata = {}
    timing_ms = audit_metadata.get("timing_ms") or {}
    if not isinstance(timing_ms, dict):
        timing_ms = {}
    llm_calls = audit_metadata.get("llm_calls") or {}
    if not isinstance(llm_calls, dict):
        llm_calls = {}
    state = make_case_state(packet_id, case_id)
    state["status"] = "completed"
    state["current_stage"] = "completed"
    state["factual_ok"] = bool(((row.get("factual_audit") or {}).get("ok")))
    state["timing_ms"] = dict(timing_ms)
    state["llm_calls"] = dict(llm_calls)
    state["stage_statuses"] = {
        "factual_audit": "completed",
        "primary_review": "completed",
        "adversarial_review": "completed",
    }
    state["updated_at"] = utc_now()
    state["completed_at"] = state["updated_at"]
    return state


def resumable_completed_case_rows(
    packet_id: str,
    *,
    case_order: list[str],
    runs_root: Path = RUNS_ROOT,
) -> tuple[dict[str, Any] | None, dict[str, dict[str, Any]]]:
    latest_run = latest_case_audit_run(packet_id, runs_root, require_completed=False)
    if latest_run is None:
        return None, {}
    latest_status = str(latest_run.get("status", "")).strip().lower()
    if latest_status not in {"failed", "incomplete"}:
        return latest_run, {}
    run_dir_value = str(latest_run.get("run_dir", "")).strip()
    if not run_dir_value:
        return latest_run, {}
    run_dir = Path(run_dir_value)
    reusable: dict[str, dict[str, Any]] = {}
    for case_id in case_order:
        case_path = run_dir / "cases" / f"{case_id}.json"
        if not case_path.exists():
            continue
        row = load_json(case_path)
        if str(row.get("case_id", "")).strip() != case_id:
            continue
        if str(row.get("status", "")).strip().lower() != "completed":
            continue
        reusable[case_id] = row
    return latest_run, reusable


def _is_retryable_quota_case_result(row: dict[str, Any]) -> bool:
    if str(row.get("status", "")).strip() != "failed":
        return False
    audit_metadata = row.get("audit_metadata") or {}
    if not isinstance(audit_metadata, dict):
        audit_metadata = {}
    llm_calls = audit_metadata.get("llm_calls") or {}
    if isinstance(llm_calls, dict):
        for metadata in llm_calls.values():
            if not isinstance(metadata, dict):
                continue
            if str(metadata.get("problem_code", "")).strip().lower() == "llm_quota":
                return True
            message = str(metadata.get("error_message", "")).strip().lower()
            if any(token in message for token in ("quota", "rate limit", "cooldown")):
                return True
    error = row.get("error") or {}
    if not isinstance(error, dict):
        error = {}
    message = str(error.get("error_message", "")).strip().lower()
    return any(token in message for token in ("quota", "rate limit", "cooldown"))


def _with_quota_recovery_metadata(
    row: dict[str, Any],
    *,
    attempted: bool,
    succeeded: bool,
    failure_remaining: bool,
    passes_used: int,
) -> dict[str, Any]:
    updated = dict(row)
    audit_metadata = updated.get("audit_metadata") or {}
    if not isinstance(audit_metadata, dict):
        audit_metadata = {}
    audit_metadata = dict(audit_metadata)
    audit_metadata["quota_recovery"] = {
        "quota_recovery_attempted_count": 1 if attempted else 0,
        "quota_recovery_succeeded_count": 1 if succeeded else 0,
        "quota_failure_remaining_count": 1 if failure_remaining else 0,
        "quota_recovery_passes_used": passes_used,
    }
    updated["audit_metadata"] = audit_metadata
    return updated


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
    audit_prompt_input_payload: dict[str, Any] = {}
    audit_prompt_input_fingerprint = ""
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
            audit_prompt_input_payload = build_audit_prompt_input_payload(case, context)
            audit_prompt_input_fingerprint = _fingerprint(audit_prompt_input_payload)

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
                "audit_prompt_input_payload": audit_prompt_input_payload,
                "audit_prompt_input_fingerprint": audit_prompt_input_fingerprint,
                "audit_metadata": {
                    "timing_ms": dict(state["timing_ms"]),
                    "llm_calls": dict(state["llm_calls"]),
                },
            }
    except Exception as exc:  # pragma: no cover - defensive fallback
        if isinstance(exc, AuditStageError):
            state["llm_calls"][exc.stage_name] = dict(exc.metadata)
            state["stage_statuses"][exc.stage_name] = "failed"
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
            "audit_prompt_input_payload": audit_prompt_input_payload,
            "audit_prompt_input_fingerprint": audit_prompt_input_fingerprint,
            "audit_metadata": {
                "timing_ms": dict(state["timing_ms"]),
                "llm_calls": dict(state["llm_calls"]),
            },
        }


def process_case_with_quota_recovery(
    case: dict[str, Any],
    *,
    packet_id: str,
    source_index: dict[str, dict[str, Any]],
    run_dir: Path,
    trace_context: LLMTraceContext,
) -> dict[str, Any]:
    row = process_case(
        case,
        packet_id=packet_id,
        source_index=source_index,
        run_dir=run_dir,
        trace_context=trace_context,
    )
    attempted = False
    passes_used = 0
    while _is_retryable_quota_case_result(row) and passes_used < CASE_QUOTA_RECOVERY_PASSES:
        attempted = True
        passes_used += 1
        time.sleep(min(1.0, 0.2 * passes_used))
        row = process_case(
            case,
            packet_id=packet_id,
            source_index=source_index,
            run_dir=run_dir,
            trace_context=trace_context,
        )
    return _with_quota_recovery_metadata(
        row,
        attempted=attempted,
        succeeded=attempted and str(row.get("status", "")).strip() == "completed",
        failure_remaining=attempted and _is_retryable_quota_case_result(row),
        passes_used=passes_used,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-id")
    parser.add_argument("--packet-dir")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--max-workers", type=int, default=0)
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

    worker_policy = resolve_worker_policy(
        job_kind="dataset_case_audit",
        profile_id=DEFAULT_DATASET_REVIEW_PROFILE_ID,
        task_count=len(cases),
        explicit_max_workers=args.max_workers if args.max_workers > 0 else None,
    )
    max_workers = worker_policy.worker_count
    latest_run, resumed_results = resumable_completed_case_rows(packet_id, case_order=case_order)
    resumed_case_ids = [case_id for case_id in case_order if case_id in resumed_results]
    resumed_from_run_id = str((latest_run or {}).get("run_id", "")).strip()
    resumed_from_run_dir = Path(str((latest_run or {}).get("run_dir", "")).strip()) if latest_run else None
    run_id = f"{packet_id}__{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    (run_dir / "cases").mkdir(parents=True, exist_ok=True)
    (run_dir / "case_states").mkdir(parents=True, exist_ok=True)
    (run_dir / SUMMARY_DIR).mkdir(parents=True, exist_ok=True)

    for case_id in case_order:
        if case_id in resumed_results and resumed_from_run_dir is not None:
            prior_case_state_path = resumed_from_run_dir / "case_states" / f"{case_id}.json"
            if prior_case_state_path.exists():
                write_case_state(run_dir, case_id, load_json(prior_case_state_path))
            else:
                write_case_state(
                    run_dir,
                    case_id,
                    _fallback_completed_case_state(packet_id, case_id, resumed_results[case_id]),
                )
            write_json(run_dir / "cases" / f"{case_id}.json", resumed_results[case_id])
            continue
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
        "queued_case_count": len(cases) - len(resumed_case_ids),
        "running_case_count": 0,
        "completed_case_count": len(resumed_case_ids),
        "failed_case_count": 0,
        "queued_case_ids": [case_id for case_id in case_order if case_id not in resumed_results],
        "running_case_ids": [],
        "completed_case_ids": list(resumed_case_ids),
        "failed_case_ids": [],
        "resumed_from_run_id": resumed_from_run_id,
        "reused_completed_case_count": len(resumed_case_ids),
    }
    write_run_state(run_dir, run_state)
    results_by_case_id: dict[str, dict[str, Any]] = dict(resumed_results)
    write_summary_outputs(
        run_dir,
        ordered_rows(results_by_case_id, case_order),
        aggregate(ordered_rows(results_by_case_id, case_order), total_case_count=len(cases), status="running"),
        packet_id=packet_id,
        partial=True,
    )
    if resumed_case_ids and resumed_from_run_id:
        print(
            f"[resume] reusing {len(resumed_case_ids)} completed cases from {resumed_from_run_id}",
            flush=True,
        )
    trace_context = eval_trace_context(
        run_dir,
        eval_target=f"dataset_case_design_audit:{packet_id}",
    )

    submitted: dict[Future[dict[str, Any]], str] = {}
    pending_cases = iter(
        case for case in cases if str(case.get("case_id", "")).strip() not in resumed_results
    )

    def submit_next(executor: ThreadPoolExecutor) -> bool:
        try:
            case = next(pending_cases)
        except StopIteration:
            return False
        case_id = str(case.get("case_id", ""))
        future = submit_inherited_context(
            executor,
            process_case_with_quota_recovery,
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

        final_status = "failed" if run_state["failed_case_ids"] else "completed"
        run_state["status"] = final_status
        run_state["completed_at"] = utc_now()
        run_state["updated_at"] = run_state["completed_at"]
        write_run_state(run_dir, run_state)
        ordered = ordered_rows(results_by_case_id, case_order)
        summary = aggregate(ordered, total_case_count=len(cases), status=final_status)
        write_summary_outputs(run_dir, ordered, summary, packet_id=packet_id, partial=True)
        write_summary_outputs(run_dir, ordered, summary, packet_id=packet_id, partial=False)

        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(f"run_dir={run_dir}")
        return 1 if run_state["failed_case_ids"] else 0
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
