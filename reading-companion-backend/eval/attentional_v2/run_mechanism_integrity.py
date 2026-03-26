"""Run the attentional_v2 local mechanism-integrity benchmark over curated excerpt cases."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from eval.common.taxonomy import DETERMINISTIC_METRICS, DIRECT_QUALITY, RUBRIC_JUDGE, normalize_methods, normalize_scopes, validate_target_slug
from src.attentional_v2.nodes import run_phase4_local_cycle
from src.attentional_v2.retrieval import generate_candidate_set
from src.attentional_v2.schemas import build_default_reader_policy, build_empty_anchor_memory, build_empty_knowledge_activations, build_empty_working_pressure
from src.iterator_reader.llm_utils import LLMTraceContext, ReaderLLMError, eval_trace_context, invoke_json, llm_invocation_scope
from src.reading_core import BookDocument
from src.reading_core.storage import existing_book_document_file, load_book_document
from src.reading_runtime.llm_registry import DEFAULT_EVAL_JUDGE_PROFILE_ID, DEFAULT_RUNTIME_PROFILE_ID
from src.reading_runtime.provisioning import ProvisionedBook, ensure_canonical_parse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_DIRS = (
    ROOT / "eval" / "datasets" / "excerpt_cases" / "attentional_v2_excerpt_en_curated_v2",
    ROOT / "eval" / "datasets" / "excerpt_cases" / "attentional_v2_excerpt_zh_curated_v2",
)
DEFAULT_SOURCE_MANIFEST = ROOT / "eval" / "manifests" / "source_books" / "attentional_v2_public_benchmark_pool_v2.json"
DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_TARGET = validate_target_slug("attentional_v2_mechanism_integrity")
DEFAULT_SCOPES = normalize_scopes([DIRECT_QUALITY])
DEFAULT_METHODS = normalize_methods([DETERMINISTIC_METRICS, RUBRIC_JUDGE])
DEFAULT_COMPARISON_TARGET = "attentional_v2 local cycle vs curated excerpt-case expectations"

JUDGE_SYSTEM = """You are doing offline reader evaluation for attentional_v2.

This is not runtime co-reading. Judge one local mechanism output against one curated excerpt case.

Scoring dimensions:
- `text_groundedness`: stays answerable to the excerpt rather than drifting into generic commentary
- `meaning_unit_quality`: closes around a real local unit instead of producing a shallow or blurred reading
- `move_quality`: chooses an appropriate next move for the passage pressure
- `reaction_quality`: visible reaction is selective, anchored, and worthwhile; withholding is acceptable when justified
- `case_fit`: addresses the case's actual benchmark focus and phenomenon pressure

Use an integer score from 1 to 5 for each dimension:
- `5`: excellent / clearly trustworthy
- `4`: strong
- `3`: mixed but acceptable
- `2`: weak
- `1`: poor / untrustworthy

Verdict:
- `pass`: clearly strong and trustworthy on this case
- `partial`: mixed, thin, or only partly responsive
- `fail`: detached, weakly anchored, or misses the case pressure badly

Return JSON only."""

JUDGE_PROMPT = """Case:
{case_json}

Mechanism evidence:
{evidence_json}

Return JSON:
{{
  "verdict": "pass|partial|fail",
  "scores": {{
    "text_groundedness": 1,
    "meaning_unit_quality": 1,
    "move_quality": 1,
    "reaction_quality": 1,
    "case_fit": 1
  }},
  "dimension_notes": {{
    "text_groundedness": "",
    "meaning_unit_quality": "",
    "move_quality": "",
    "reaction_quality": "",
    "case_fit": ""
  }},
  "reason": "2-5 sentences."
}}"""


@dataclass(frozen=True)
class ExcerptCase:
    case_id: str
    case_title: str
    split: str
    source_id: str
    book_title: str
    author: str
    output_language: str
    chapter_id: int
    chapter_title: str
    start_sentence_id: str
    end_sentence_id: str
    excerpt_text: str
    question_ids: list[str]
    phenomena: list[str]
    selection_reason: str
    judge_focus: str
    dataset_id: str
    dataset_version: str


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _sentence_order_key(sentence_id: object) -> tuple[int, int]:
    raw = _clean_text(sentence_id)
    if not raw:
        return (-1, -1)
    chapter_part, _, sentence_part = raw.partition("-s")
    chapter_digits = "".join(ch for ch in chapter_part if ch.isdigit())
    sentence_digits = "".join(ch for ch in sentence_part if ch.isdigit())
    try:
        chapter_index = int(chapter_digits)
    except ValueError:
        chapter_index = -1
    try:
        sentence_index = int(sentence_digits)
    except ValueError:
        sentence_index = -1
    return (chapter_index, sentence_index)


def _bucket_from_case_id(case_id: str) -> str:
    stem = str(case_id).rsplit("__", 1)[0]
    return stem.split("__")[-1]


def _default_judgment() -> dict[str, Any]:
    return {
        "verdict": "partial",
        "scores": {
            "text_groundedness": 0,
            "meaning_unit_quality": 0,
            "move_quality": 0,
            "reaction_quality": 0,
            "case_fit": 0,
        },
        "dimension_notes": {
            "text_groundedness": "",
            "meaning_unit_quality": "",
            "move_quality": "",
            "reaction_quality": "",
            "case_fit": "",
        },
        "reason": "judge_unavailable",
    }


def _normalize_judgment(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return _default_judgment()
    normalized = _default_judgment()
    verdict = _clean_text(payload.get("verdict")).lower()
    if verdict in {"pass", "partial", "fail"}:
        normalized["verdict"] = verdict
    scores = payload.get("scores")
    if isinstance(scores, dict):
        for key in normalized["scores"]:
            raw_score = scores.get(key)
            try:
                score_value = int(raw_score)
            except (TypeError, ValueError):
                score_value = 0
            normalized["scores"][key] = max(0, min(5, score_value))
    notes = payload.get("dimension_notes")
    if isinstance(notes, dict):
        for key in normalized["dimension_notes"]:
            normalized["dimension_notes"][key] = _clean_text(notes.get(key))
    normalized["reason"] = _clean_text(payload.get("reason")) or normalized["reason"]
    return normalized


def _judge_case(case: ExcerptCase, evidence: dict[str, Any], *, judge_mode: str) -> dict[str, Any]:
    if judge_mode == "none":
        return _default_judgment()
    try:
        with llm_invocation_scope(
            profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
            trace_context=LLMTraceContext(stage="mechanism_integrity", node="rubric_judge"),
        ):
            payload = invoke_json(
                JUDGE_SYSTEM,
                JUDGE_PROMPT.format(
                    case_json=json.dumps(
                        {
                            "case_id": case.case_id,
                            "case_title": case.case_title,
                            "judge_focus": case.judge_focus,
                            "selection_reason": case.selection_reason,
                            "question_ids": case.question_ids,
                            "phenomena": case.phenomena,
                            "excerpt_text": case.excerpt_text,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    evidence_json=json.dumps(evidence, ensure_ascii=False, indent=2),
                ),
                default=_default_judgment(),
            )
    except ReaderLLMError:
        return _default_judgment()
    except Exception:
        return _default_judgment()
    return _normalize_judgment(payload)


def _load_cases(dataset_dir: Path) -> tuple[dict[str, Any], list[ExcerptCase]]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: list[ExcerptCase] = []
    with (dataset_dir / str(manifest["primary_file"])).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(
                ExcerptCase(
                    case_id=str(raw["case_id"]),
                    case_title=str(raw.get("case_title", raw["case_id"])),
                    split=str(raw.get("split", "")),
                    source_id=str(raw["source_id"]),
                    book_title=str(raw["book_title"]),
                    author=str(raw["author"]),
                    output_language=str(raw["output_language"]),
                    chapter_id=int(raw["chapter_id"]),
                    chapter_title=str(raw.get("chapter_title", "")),
                    start_sentence_id=str(raw["start_sentence_id"]),
                    end_sentence_id=str(raw["end_sentence_id"]),
                    excerpt_text=str(raw["excerpt_text"]),
                    question_ids=[str(item) for item in raw.get("question_ids", [])],
                    phenomena=[str(item) for item in raw.get("phenomena", [])],
                    selection_reason=str(raw.get("selection_reason", "")),
                    judge_focus=str(raw.get("judge_focus", "")),
                    dataset_id=str(manifest["dataset_id"]),
                    dataset_version=str(manifest["version"]),
                )
            )
    return manifest, rows


def _load_source_index(manifest_path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {
        str(item["source_id"]): dict(item)
        for item in payload.get("books", [])
        if isinstance(item, dict) and item.get("source_id")
    }


def _ensure_provisioned(source: dict[str, Any], *, language_mode: str) -> ProvisionedBook:
    book_path = ROOT / str(source["relative_local_path"])
    if not book_path.exists():
        raise FileNotFoundError(f"Missing source book: {book_path}")
    output_dir = ROOT / str(source["output_dir"])
    if existing_book_document_file(output_dir).exists():
        return ProvisionedBook(
            book_path=book_path,
            title=str(source.get("title", "") or ""),
            author=str(source.get("author", "") or ""),
            book_language=str(source.get("detected_book_language", source.get("language", "")) or ""),
            output_language=str(source.get("output_language", language_mode) or language_mode),
            output_dir=output_dir,
            raw_chapters=None,
            book_document=load_book_document(existing_book_document_file(output_dir)),
        )
    return ensure_canonical_parse(book_path, language_mode=language_mode)


def _find_span(document: BookDocument, case: ExcerptCase) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        if int(chapter.get("id", 0) or 0) != case.chapter_id:
            continue
        sentences = [item for item in chapter.get("sentences", []) if isinstance(item, dict)]
        by_id = {str(sentence.get("sentence_id", "")): index for index, sentence in enumerate(sentences)}
        if case.start_sentence_id not in by_id or case.end_sentence_id not in by_id:
            raise ValueError(f"case span not found in chapter: {case.case_id}")
        start = by_id[case.start_sentence_id]
        end = by_id[case.end_sentence_id]
        if end < start:
            raise ValueError(f"case span reversed: {case.case_id}")
        current_span = sentences[start : end + 1]
        lookback = sentences[:start]
        return chapter, current_span, lookback
    raise ValueError(f"chapter missing for case: {case.case_id}")


def _build_bridge_candidates(document: BookDocument, case: ExcerptCase, current_span: list[dict[str, Any]]) -> list[dict[str, Any]]:
    focal_sentence = current_span[-1]
    candidate_set = generate_candidate_set(
        document,
        current_sentence_id=str(focal_sentence.get("sentence_id", "")),
        current_text=case.excerpt_text,
        anchor_memory=build_empty_anchor_memory(mechanism_version="attentional_v2-phase8"),
        max_memory_candidates=0,
        max_lookback_candidates=8,
    )
    bridge_candidates: list[dict[str, Any]] = []
    for item in candidate_set.get("lookback_candidates", []):
        if not isinstance(item, dict):
            continue
        overlap = int(item.get("overlap_score", 0) or 0)
        sentence_id = str(item.get("sentence_id", "") or "")
        if not sentence_id or overlap <= 0:
            continue
        bridge_candidates.append(
            {
                "candidate_kind": "source_lookback",
                "target_anchor_id": "",
                "target_sentence_id": sentence_id,
                "retrieval_channel": "source_lookback",
                "relation_type": "echo",
                "score": float(overlap),
                "why_now": "Lexical overlap from bounded lookback source space.",
                "quote": _clean_text(item.get("text"))[:280],
            }
        )
    return bridge_candidates[:3]


def _deterministic_metrics(
    case: ExcerptCase,
    current_span: list[dict[str, Any]],
    lookback: list[dict[str, Any]],
    bridge_candidates: list[dict[str, Any]],
    phase4: dict[str, Any],
) -> dict[str, Any]:
    zoom_result = phase4.get("zoom_result") or {}
    closure_result = phase4.get("closure_result") or {}
    controller_result = phase4.get("controller_result") or {}
    reaction_result = phase4.get("reaction_result") or {}
    anchor_quote = _clean_text((reaction_result.get("reaction") or {}).get("anchor_quote")) or _clean_text(zoom_result.get("anchor_quote"))
    current_sentence_key = _sentence_order_key(current_span[-1].get("sentence_id"))
    future_bridge_ids = [
        str(item.get("target_sentence_id", "") or "")
        for item in bridge_candidates
        if _sentence_order_key(item.get("target_sentence_id")) >= current_sentence_key
    ]
    return {
        "excerpt_sentence_count": len(current_span),
        "lookback_sentence_count": len(lookback),
        "bridge_candidate_count": len(bridge_candidates),
        "anchor_quote_present": bool(anchor_quote),
        "anchor_quote_in_excerpt": bool(anchor_quote and anchor_quote in case.excerpt_text),
        "reaction_emitted": str(reaction_result.get("decision", "")) == "emit",
        "controller_move": _clean_text(controller_result.get("chosen_move")),
        "closure_decision": _clean_text(closure_result.get("closure_decision")),
        "future_safe_bridge_candidates": not future_bridge_ids,
        "future_bridge_candidate_ids": future_bridge_ids,
    }


def _case_payload(case: ExcerptCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "case_title": case.case_title,
        "dataset_id": case.dataset_id,
        "dataset_version": case.dataset_version,
        "language": case.output_language,
        "source_id": case.source_id,
        "chapter_id": case.chapter_id,
        "question_ids": list(case.question_ids),
        "phenomena": list(case.phenomena),
        "bucket": _bucket_from_case_id(case.case_id),
    }


def _run_case(
    case: ExcerptCase,
    source_index: dict[str, dict[str, Any]],
    cache: dict[str, ProvisionedBook],
    *,
    judge_mode: str,
    trace_context: LLMTraceContext,
) -> dict[str, Any]:
    source = source_index[case.source_id]
    provisioned = cache.setdefault(case.source_id, _ensure_provisioned(source, language_mode=case.output_language))
    document = provisioned.book_document
    if document is None:
        raise RuntimeError(f"Missing book_document for {case.source_id}")
    chapter, current_span, lookback = _find_span(document, case)
    bridge_candidates = _build_bridge_candidates(document, case, current_span)
    with llm_invocation_scope(
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        trace_context=trace_context,
    ):
        phase4 = run_phase4_local_cycle(
            focal_sentence=current_span[-1],
            current_span_sentences=current_span,
            trigger_state={"output": "zoom_now", "gate_state": "engaged"},
            working_pressure=build_empty_working_pressure(mechanism_version="attentional_v2-phase8"),
            anchor_memory=build_empty_anchor_memory(mechanism_version="attentional_v2-phase8"),
            knowledge_activations=build_empty_knowledge_activations(mechanism_version="attentional_v2-phase8"),
            reader_policy=build_default_reader_policy(mechanism_version="attentional_v2-phase8", policy_version="attentional_v2-phase8"),
            bridge_candidates=bridge_candidates,
            output_language=case.output_language,
            output_dir=None,
            book_title=case.book_title,
            author=case.author,
            chapter_title=str(chapter.get("title", case.chapter_title) or case.chapter_title),
            boundary_context={
                "span_sentence_count": len(current_span),
                "lookback_sentence_count": len(lookback),
                "start_sentence_id": case.start_sentence_id,
                "end_sentence_id": case.end_sentence_id,
            },
        )
    deterministic = _deterministic_metrics(case, current_span, lookback, bridge_candidates, phase4)
    evidence = {
        "focal_sentence": {
            "sentence_id": str(current_span[-1].get("sentence_id", "") or ""),
            "text": _clean_text(current_span[-1].get("text")),
        },
        "current_span": [
            {
                "sentence_id": str(sentence.get("sentence_id", "") or ""),
                "text": _clean_text(sentence.get("text")),
            }
            for sentence in current_span
        ],
        "bridge_candidates": bridge_candidates,
        "phase4": phase4,
        "deterministic_metrics": deterministic,
    }
    judgment = _judge_case(case, evidence, judge_mode=judge_mode)
    result = {
        **_case_payload(case),
        "source_book_path": str(provisioned.book_path),
        "output_dir": str(provisioned.output_dir),
        "deterministic_metrics": deterministic,
        "phase4": phase4,
        "judgment": judgment,
    }
    return result


def _score_value(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _aggregate(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    verdict_counts = Counter(str(item.get("judgment", {}).get("verdict", "")) for item in case_results)
    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    move_counts = Counter()
    structural_failures = 0
    judge_unavailable = 0
    for item in case_results:
        language = str(item.get("language", ""))
        bucket = str(item.get("bucket", ""))
        by_language[language].append(item)
        by_bucket[bucket].append(item)
        move_counts[str(item.get("deterministic_metrics", {}).get("controller_move", ""))] += 1
        if not bool(item.get("deterministic_metrics", {}).get("future_safe_bridge_candidates", True)):
            structural_failures += 1
        if str(item.get("judgment", {}).get("reason", "")) == "judge_unavailable":
            judge_unavailable += 1

    def avg_score(items: list[dict[str, Any]], key: str) -> float:
        values = [_score_value(item.get("judgment", {}).get("scores", {}).get(key)) for item in items]
        return round(mean(values), 3) if values else 0.0

    score_keys = ("text_groundedness", "meaning_unit_quality", "move_quality", "reaction_quality", "case_fit")
    return {
        "case_count": len(case_results),
        "verdict_counts": dict(verdict_counts),
        "judge_unavailable_count": judge_unavailable,
        "structural_failure_count": structural_failures,
        "move_counts": dict(move_counts),
        "average_scores": {key: avg_score(case_results, key) for key in score_keys},
        "language_summaries": {
            language: {
                "case_count": len(items),
                "verdict_counts": dict(Counter(str(item.get("judgment", {}).get("verdict", "")) for item in items)),
                "average_scores": {key: avg_score(items, key) for key in score_keys},
            }
            for language, items in sorted(by_language.items())
        },
        "bucket_summaries": {
            bucket: {
                "case_count": len(items),
                "average_scores": {key: avg_score(items, key) for key in score_keys},
            }
            for bucket, items in sorted(by_bucket.items())
        },
    }


def _top_cases(case_results: list[dict[str, Any]], *, reverse: bool) -> list[dict[str, Any]]:
    def avg(item: dict[str, Any]) -> float:
        scores = item.get("judgment", {}).get("scores", {})
        values = [_score_value(scores.get(key)) for key in ("text_groundedness", "meaning_unit_quality", "move_quality", "reaction_quality", "case_fit")]
        return mean(values) if values else 0.0

    return sorted(case_results, key=avg, reverse=reverse)[:3]


def _build_markdown_report(*, run_id: str, aggregate: dict[str, Any], case_results: list[dict[str, Any]], datasets: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Attentional V2 Mechanism Integrity")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("This report records a local `mechanism_integrity` benchmark pass over the selected excerpt datasets for `attentional_v2`.")
    lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append(f"- Run ID: `{run_id}`")
    lines.append(f"- Target: `{DEFAULT_TARGET}`")
    lines.append(f"- Scope: `{DIRECT_QUALITY}`")
    lines.append(f"- Methods: `{DETERMINISTIC_METRICS}`, `{RUBRIC_JUDGE}`")
    lines.append(f"- Comparison target: {DEFAULT_COMPARISON_TARGET}")
    lines.append("")
    lines.append("## Datasets")
    lines.append("")
    for dataset in datasets:
        lines.append(f"- `{dataset['dataset_id']}` (language `{dataset['language_track']}`, version `{dataset['version']}`)")
    lines.append("")
    lines.append("## Aggregate Findings")
    lines.append("")
    lines.append(f"- Cases evaluated: `{aggregate['case_count']}`")
    lines.append(f"- Verdict counts: `{json.dumps(aggregate['verdict_counts'], ensure_ascii=False, sort_keys=True)}`")
    lines.append(f"- Judge unavailable count: `{aggregate['judge_unavailable_count']}`")
    lines.append(f"- Structural failure count: `{aggregate['structural_failure_count']}`")
    lines.append(f"- Move counts: `{json.dumps(aggregate['move_counts'], ensure_ascii=False, sort_keys=True)}`")
    lines.append("- Average scores:")
    for key, value in aggregate["average_scores"].items():
        lines.append(f"  - `{key}`: `{value:.3f}`")
    lines.append("")
    lines.append("## By Language")
    lines.append("")
    for language, summary in aggregate["language_summaries"].items():
        lines.append(f"### `{language}`")
        lines.append(f"- Cases: `{summary['case_count']}`")
        lines.append(f"- Verdict counts: `{json.dumps(summary['verdict_counts'], ensure_ascii=False, sort_keys=True)}`")
        for key, value in summary["average_scores"].items():
            lines.append(f"- `{key}`: `{value:.3f}`")
        lines.append("")
    lines.append("## Strongest Cases")
    lines.append("")
    for item in _top_cases(case_results, reverse=True):
        lines.append(f"- `{item['case_id']}`")
        lines.append(f"  - verdict: `{item['judgment']['verdict']}`")
        lines.append(f"  - reason: {item['judgment']['reason']}")
    lines.append("")
    lines.append("## Weakest Cases")
    lines.append("")
    for item in _top_cases(case_results, reverse=False):
        lines.append(f"- `{item['case_id']}`")
        lines.append(f"  - verdict: `{item['judgment']['verdict']}`")
        lines.append(f"  - reason: {item['judgment']['reason']}")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def run_benchmark(
    *,
    dataset_dirs: list[Path],
    source_manifest_path: Path,
    runs_root: Path,
    run_id: str | None = None,
    case_ids: list[str] | None = None,
    judge_mode: str = "llm",
    limit: int | None = None,
) -> dict[str, Any]:
    datasets: list[dict[str, Any]] = []
    all_cases: list[ExcerptCase] = []
    for dataset_dir in dataset_dirs:
        manifest, cases = _load_cases(dataset_dir)
        datasets.append(manifest)
        all_cases.extend(cases)
    if case_ids:
        wanted = {item for item in case_ids}
        all_cases = [case for case in all_cases if case.case_id in wanted]
    if limit is not None:
        all_cases = all_cases[: max(0, int(limit))]
    if not all_cases:
        raise ValueError("no excerpt cases selected")

    source_index = _load_source_index(source_manifest_path)
    cache: dict[str, ProvisionedBook] = {}
    run_name = run_id or datetime.now(timezone.utc).strftime("attentional_v2_integrity_v2_%Y%m%d-%H%M%S")
    run_root = runs_root / run_name
    run_root.mkdir(parents=True, exist_ok=True)
    trace_context = eval_trace_context(
        run_root,
        eval_target=DEFAULT_TARGET,
    )

    _json_dump(
        run_root / "dataset_manifest.json",
        {
            "target": DEFAULT_TARGET,
            "scopes": DEFAULT_SCOPES,
            "methods": DEFAULT_METHODS,
            "comparison_target": DEFAULT_COMPARISON_TARGET,
            "dataset_ids": [dataset["dataset_id"] for dataset in datasets],
            "selected_case_ids": [case.case_id for case in all_cases],
            "judge_mode": judge_mode,
            "generated_at": _timestamp(),
        },
    )

    case_results: list[dict[str, Any]] = []
    for index, case in enumerate(all_cases, start=1):
        print(f"[{index}/{len(all_cases)}] {case.case_id}", flush=True)
        result = _run_case(case, source_index, cache, judge_mode=judge_mode, trace_context=trace_context)
        case_results.append(result)
        _json_dump(run_root / "cases" / f"{case.case_id}.json", result)

    aggregate = _aggregate(case_results)
    _json_dump(run_root / "summary" / "aggregate.json", aggregate)
    _jsonl_dump(run_root / "summary" / "case_results.jsonl", case_results)
    report_path = run_root / "summary" / "report.md"
    report_path.write_text(
        _build_markdown_report(run_id=run_name, aggregate=aggregate, case_results=case_results, datasets=datasets),
        encoding="utf-8",
    )
    return {
        "run_id": run_name,
        "run_root": str(run_root),
        "report_path": str(report_path),
        "aggregate": aggregate,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset-dir",
        action="append",
        default=[],
        help="Curated excerpt dataset directory. Defaults to the tracked EN/ZH curated v2 packs.",
    )
    parser.add_argument("--source-manifest", default=str(DEFAULT_SOURCE_MANIFEST))
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--case-ids", default="")
    parser.add_argument("--judge-mode", choices=["llm", "none"], default="llm")
    parser.add_argument("--limit", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    dataset_dirs = [Path(item).resolve() for item in args.dataset_dir] if args.dataset_dir else list(DEFAULT_DATASET_DIRS)
    case_ids = [item.strip() for item in args.case_id if str(item).strip()]
    if args.case_ids:
        case_ids.extend([item.strip() for item in str(args.case_ids).split(",") if item.strip()])
    summary = run_benchmark(
        dataset_dirs=dataset_dirs,
        source_manifest_path=Path(args.source_manifest).resolve(),
        runs_root=Path(args.runs_root).resolve(),
        run_id=args.run_id or None,
        case_ids=case_ids or None,
        judge_mode=args.judge_mode,
        limit=args.limit or None,
    )
    print(json.dumps(summary["aggregate"], ensure_ascii=False, indent=2))
    print(f"run_root={summary['run_root']}")
    print(f"report_path={summary['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
