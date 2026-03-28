"""Run the first chapter-scale local-reading and span-trajectory comparison."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any
from unittest.mock import patch

from eval.common.taxonomy import (
    DETERMINISTIC_METRICS,
    LOCAL_IMPACT,
    PAIRWISE_JUDGE,
    RUBRIC_JUDGE,
    SYSTEM_REGRESSION,
    normalize_methods,
    normalize_scopes,
    validate_target_slug,
)
from src.iterator_reader.llm_utils import LLMTraceContext, ReaderLLMError, eval_trace_context, invoke_json, llm_invocation_scope
from src.reading_core.runtime_contracts import ReadRequest
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_mechanisms.iterator_v1 import IteratorV1Mechanism
from src.reading_runtime.job_concurrency import resolve_worker_policy, submit_inherited_context
from src.reading_runtime.llm_registry import DEFAULT_EVAL_JUDGE_PROFILE_ID, DEFAULT_RUNTIME_PROFILE_ID


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_DIRS = (
    ROOT / "eval" / "datasets" / "chapter_corpora" / "attentional_v2_chapters_en_v2",
    ROOT / "eval" / "datasets" / "chapter_corpora" / "attentional_v2_chapters_zh_v2",
)
DEFAULT_SOURCE_MANIFEST = ROOT / "eval" / "manifests" / "source_books" / "attentional_v2_public_benchmark_pool_v2.json"
DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_TARGET = validate_target_slug("reader_end_to_end")
DEFAULT_SCOPES = normalize_scopes([LOCAL_IMPACT, SYSTEM_REGRESSION])
DEFAULT_METHODS = normalize_methods([DETERMINISTIC_METRICS, PAIRWISE_JUDGE, RUBRIC_JUDGE])
DEFAULT_COMPARISON_TARGET = "attentional_v2 vs iterator_v1 on balanced chapter-scale local-reading and span-trajectory cases"
DEFAULT_USER_INTENT = (
    "Read as a thoughtful co-reader and notice meaningful turns, tensions, callbacks, definitions, and chapter-level development."
)
SELECTION_ROLES = ("expository", "argumentative", "narrative_reflective", "reference_heavy")
MECHANISM_KEYS = ("attentional_v2", "iterator_v1")

LOCAL_READING_SYSTEM = """You are doing offline cross-mechanism reader evaluation.

Question family: `local_reading_behavior`

Compare two mechanisms reading the same chapter. Focus on the quality of their passage-level reading steps as evidenced by:
- local selectivity
- source anchoring
- focus
- meaningful curiosity
- whether visible reactions feel earned rather than generic

Return JSON only."""

LOCAL_READING_PROMPT = """Chapter case:
{case_json}

Attentional V2 evidence:
{left_json}

Iterator V1 evidence:
{right_json}

Return JSON:
{{
  "winner": "attentional_v2|iterator_v1|tie",
  "confidence": "high|medium|low",
  "scores": {{
    "attentional_v2": {{
      "text_groundedness": 1,
      "focus_selectivity": 1,
      "source_anchoring": 1,
      "meaningful_curiosity": 1,
      "local_step_quality": 1
    }},
    "iterator_v1": {{
      "text_groundedness": 1,
      "focus_selectivity": 1,
      "source_anchoring": 1,
      "meaningful_curiosity": 1,
      "local_step_quality": 1
    }}
  }},
  "reason": "3-6 sentences."
}}"""

SPAN_TRAJECTORY_SYSTEM = """You are doing offline cross-mechanism reader evaluation.

Question family: `span_trajectory`

Compare two mechanisms reading the same chapter. Focus on whether understanding develops coherently across the larger span, including:
- coherent accumulation
- callback quality
- chapter-arc clarity
- memory carry-over
- product-fit as a reading mind rather than generic summary

Return JSON only."""

SPAN_TRAJECTORY_PROMPT = """Chapter case:
{case_json}

Attentional V2 evidence:
{left_json}

Iterator V1 evidence:
{right_json}

Return JSON:
{{
  "winner": "attentional_v2|iterator_v1|tie",
  "confidence": "high|medium|low",
  "scores": {{
    "attentional_v2": {{
      "coherent_accumulation": 1,
      "callback_quality": 1,
      "chapter_arc_clarity": 1,
      "memory_carryover": 1,
      "product_fit": 1
    }},
    "iterator_v1": {{
      "coherent_accumulation": 1,
      "callback_quality": 1,
      "chapter_arc_clarity": 1,
      "memory_carryover": 1,
      "product_fit": 1
    }}
  }},
  "reason": "3-6 sentences."
}}"""


@dataclass(frozen=True)
class ChapterCase:
    chapter_case_id: str
    source_id: str
    book_title: str
    author: str
    language_track: str
    type_tags: list[str]
    role_tags: list[str]
    output_dir: str
    chapter_id: int
    chapter_title: str
    sentence_count: int
    paragraph_count: int
    candidate_position_bucket: str
    candidate_score: float
    selection_status: str
    selection_priority: int
    selection_role: str
    dataset_id: str
    dataset_version: str


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _load_cases(dataset_dir: Path) -> tuple[dict[str, Any], list[ChapterCase]]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: list[ChapterCase] = []
    with (dataset_dir / str(manifest["primary_file"])).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(
                ChapterCase(
                    chapter_case_id=str(raw["chapter_case_id"]),
                    source_id=str(raw["source_id"]),
                    book_title=str(raw["book_title"]),
                    author=str(raw["author"]),
                    language_track=str(raw["language_track"]),
                    type_tags=[str(item) for item in raw.get("type_tags", [])],
                    role_tags=[str(item) for item in raw.get("role_tags", [])],
                    output_dir=str(raw.get("output_dir", "")),
                    chapter_id=int(raw["chapter_id"]),
                    chapter_title=str(raw.get("chapter_title", "")),
                    sentence_count=int(raw.get("sentence_count", 0) or 0),
                    paragraph_count=int(raw.get("paragraph_count", 0) or 0),
                    candidate_position_bucket=str(raw.get("candidate_position_bucket", "")),
                    candidate_score=float(raw.get("candidate_score", 0.0) or 0.0),
                    selection_status=str(raw.get("selection_status", "")),
                    selection_priority=int(raw.get("selection_priority", 999) or 999),
                    selection_role=str(raw.get("selection_role", "")),
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


def _case_sort_key(case: ChapterCase) -> tuple[int, float, str]:
    return (case.selection_priority, -case.candidate_score, case.chapter_case_id)


def _core_case_sort_key(case: ChapterCase) -> tuple[int, int, float, str]:
    return (case.sentence_count, case.selection_priority, -case.candidate_score, case.chapter_case_id)


def _select_core_cases(cases: list[ChapterCase]) -> list[ChapterCase]:
    selected: list[ChapterCase] = []
    by_language_role: dict[tuple[str, str], list[ChapterCase]] = defaultdict(list)
    for case in cases:
        if case.selection_role in SELECTION_ROLES:
            by_language_role[(case.language_track, case.selection_role)].append(case)
    for language in ("en", "zh"):
        for role in SELECTION_ROLES:
            # Use the smallest trustworthy chapter per role for the first broader-comparison pass.
            options = sorted(by_language_role.get((language, role), []), key=_core_case_sort_key)
            if not options:
                raise ValueError(f"missing core chapter case for {language}/{role}")
            selected.append(options[0])
    return selected


def _normalize_judgment(payload: object, *, left_key: str, right_key: str, score_keys: tuple[str, ...]) -> dict[str, Any]:
    default = {
        "winner": "tie",
        "confidence": "low",
        "scores": {
            left_key: {key: 0 for key in score_keys},
            right_key: {key: 0 for key in score_keys},
        },
        "reason": "judge_unavailable",
    }
    if not isinstance(payload, dict):
        return default
    winner = _clean_text(payload.get("winner")).lower()
    if winner not in {left_key, right_key, "tie"}:
        winner = "tie"
    confidence = _clean_text(payload.get("confidence")).lower()
    if confidence not in {"high", "medium", "low"}:
        confidence = "low"
    normalized = {
        "winner": winner,
        "confidence": confidence,
        "scores": {
            left_key: {key: 0 for key in score_keys},
            right_key: {key: 0 for key in score_keys},
        },
        "reason": _clean_text(payload.get("reason")) or "judge_unavailable",
    }
    scores = payload.get("scores")
    if isinstance(scores, dict):
        for side in (left_key, right_key):
            side_scores = scores.get(side)
            if not isinstance(side_scores, dict):
                continue
            for key in score_keys:
                try:
                    value = int(side_scores.get(key))
                except (TypeError, ValueError):
                    value = 0
                normalized["scores"][side][key] = max(0, min(5, value))
    return normalized


def _summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    chapter = {}
    chapters = bundle.get("chapters") or []
    if isinstance(chapters, list) and chapters:
        chapter = dict(chapters[0])
    reactions = []
    for item in bundle.get("reactions") or []:
        if not isinstance(item, dict):
            continue
        reactions.append(
            {
                "type": _clean_text(item.get("type")),
                "section_ref": _clean_text(item.get("section_ref")),
                "anchor_quote": _clean_text(item.get("anchor_quote"))[:180],
                "content": _clean_text(item.get("content"))[:240],
            }
        )
    attention_events = []
    for item in bundle.get("attention_events") or []:
        if not isinstance(item, dict):
            continue
        if _clean_text(item.get("kind")) in {"position", "checkpoint"}:
            continue
        attention_events.append(
            {
                "kind": _clean_text(item.get("kind")),
                "phase": _clean_text(item.get("phase")),
                "section_ref": _clean_text(item.get("section_ref")),
                "move_type": _clean_text(item.get("move_type")),
                "message": _clean_text(item.get("message"))[:180],
                "current_excerpt": _clean_text(item.get("current_excerpt"))[:180],
            }
        )
    return {
        "run_snapshot": dict(bundle.get("run_snapshot") or {}),
        "chapter_output": chapter,
        "reaction_count": len(reactions),
        "attention_event_count": len(attention_events),
        "reactions": reactions[:5],
        "attention_events": attention_events[:8],
        "memory_summaries": [str(item)[:280] for item in (bundle.get("memory_summaries") or [])[:4]],
    }


@contextmanager
def _isolated_output_dir(output_dir: Path):
    import src.iterator_reader.parse as iterator_parse_module
    import src.iterator_reader.storage as iterator_storage_module
    import src.reading_runtime.provisioning as provisioning_module

    with ExitStack() as stack:
        stack.enter_context(patch.object(provisioning_module, "resolve_output_dir", lambda *_args, **_kwargs: output_dir))
        stack.enter_context(patch.object(iterator_storage_module, "resolve_output_dir", lambda *_args, **_kwargs: output_dir))
        stack.enter_context(patch.object(iterator_parse_module, "resolve_output_dir", lambda *_args, **_kwargs: output_dir))
        yield


def _run_mechanism_for_case(
    case: ChapterCase,
    source: dict[str, Any],
    *,
    mechanism_key: str,
    run_root: Path,
) -> dict[str, Any]:
    if mechanism_key == "attentional_v2":
        mechanism = AttentionalV2Mechanism()
    elif mechanism_key == "iterator_v1":
        mechanism = IteratorV1Mechanism()
    else:
        raise ValueError(f"unsupported mechanism: {mechanism_key}")

    book_path = ROOT / str(source["relative_local_path"])
    isolated_output_dir = run_root / "outputs" / case.chapter_case_id / mechanism_key
    shutil.rmtree(isolated_output_dir, ignore_errors=True)
    isolated_output_dir.parent.mkdir(parents=True, exist_ok=True)
    with _isolated_output_dir(isolated_output_dir):
        result = mechanism.read_book(
            ReadRequest(
                book_path=book_path,
                chapter_number=int(case.chapter_id),
                continue_mode=False,
                user_intent=DEFAULT_USER_INTENT,
                language_mode=case.language_track,
                task_mode="sequential",
                mechanism_key=mechanism_key,
                mechanism_config={"persist_normalized_eval_bundle": True},
            )
        )
    bundle = dict(result.normalized_eval_bundle or {})
    _json_dump(run_root / "bundles" / mechanism_key / f"{case.chapter_case_id}.json", bundle)
    return {
        "mechanism_key": mechanism_key,
        "mechanism_label": result.mechanism.label,
        "output_dir": str(result.output_dir),
        "normalized_eval_bundle": bundle,
        "bundle_summary": _summarize_bundle(bundle),
    }


def _write_json_payload(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _run_mechanism_worker(payload_path: Path, result_path: Path) -> int:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    case = ChapterCase(**dict(payload["case"]))
    source = dict(payload["source"])
    result = _run_mechanism_for_case(
        case,
        source,
        mechanism_key=str(payload["mechanism_key"]),
        run_root=Path(str(payload["run_root"])),
    )
    _write_json_payload(result_path, result)
    return 0


def _run_mechanism_subprocess(
    case: ChapterCase,
    source: dict[str, Any],
    *,
    mechanism_key: str,
    run_root: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="chapter-comparison-worker-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        payload_path = temp_dir / "payload.json"
        result_path = temp_dir / "result.json"
        _write_json_payload(
            payload_path,
            {
                "case": asdict(case),
                "source": source,
                "mechanism_key": mechanism_key,
                "run_root": str(run_root),
            },
        )
        command = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--worker-payload",
            str(payload_path),
            "--worker-result",
            str(result_path),
        ]
        subprocess.run(command, cwd=str(ROOT), check=True)
        return json.loads(result_path.read_text(encoding="utf-8"))


def _run_mechanisms_for_case(
    case: ChapterCase,
    source: dict[str, Any],
    *,
    run_root: Path,
    mechanism_execution_mode: str,
) -> dict[str, dict[str, Any]]:
    if mechanism_execution_mode == "serial":
        return {
            mechanism_key: _run_mechanism_for_case(case, source, mechanism_key=mechanism_key, run_root=run_root)
            for mechanism_key in MECHANISM_KEYS
        }

    if mechanism_execution_mode != "parallel":
        raise ValueError(f"unsupported mechanism execution mode: {mechanism_execution_mode}")

    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=len(MECHANISM_KEYS), thread_name_prefix="mechanism-worker") as executor:
        future_to_mechanism = {
            executor.submit(
                _run_mechanism_subprocess,
                case,
                source,
                mechanism_key=mechanism_key,
                run_root=run_root,
            ): mechanism_key
            for mechanism_key in MECHANISM_KEYS
        }
        for future in as_completed(future_to_mechanism):
            mechanism_key = future_to_mechanism[future]
            results[mechanism_key] = future.result()
    return {mechanism_key: results[mechanism_key] for mechanism_key in MECHANISM_KEYS}


def _judge_scope(
    *,
    scope: str,
    case: ChapterCase,
    attentional: dict[str, Any],
    iterator: dict[str, Any],
    run_root: Path,
    judge_mode: str,
) -> dict[str, Any]:
    if scope == LOCAL_IMPACT:
        system_prompt = LOCAL_READING_SYSTEM
        user_prompt = LOCAL_READING_PROMPT
        score_keys = (
            "text_groundedness",
            "focus_selectivity",
            "source_anchoring",
            "meaningful_curiosity",
            "local_step_quality",
        )
        eval_target = "local_reading_behavior"
    elif scope == SYSTEM_REGRESSION:
        system_prompt = SPAN_TRAJECTORY_SYSTEM
        user_prompt = SPAN_TRAJECTORY_PROMPT
        score_keys = (
            "coherent_accumulation",
            "callback_quality",
            "chapter_arc_clarity",
            "memory_carryover",
            "product_fit",
        )
        eval_target = "span_trajectory"
    else:
        raise ValueError(f"unsupported scope: {scope}")

    if judge_mode == "none":
        return _normalize_judgment({}, left_key="attentional_v2", right_key="iterator_v1", score_keys=score_keys)

    try:
        with llm_invocation_scope(
            profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
            trace_context=eval_trace_context(
                run_root,
                eval_target=eval_target,
                stage="chapter_comparison",
                node=scope,
            ),
        ):
            payload = invoke_json(
                system_prompt,
                user_prompt.format(
                    case_json=json.dumps(
                        {
                            "chapter_case_id": case.chapter_case_id,
                            "book_title": case.book_title,
                            "author": case.author,
                            "language_track": case.language_track,
                            "selection_role": case.selection_role,
                            "chapter_title": case.chapter_title,
                            "sentence_count": case.sentence_count,
                            "paragraph_count": case.paragraph_count,
                            "type_tags": case.type_tags,
                            "role_tags": case.role_tags,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    left_json=json.dumps(attentional["bundle_summary"], ensure_ascii=False, indent=2),
                    right_json=json.dumps(iterator["bundle_summary"], ensure_ascii=False, indent=2),
                ),
                {
                    "winner": "tie",
                    "confidence": "low",
                    "scores": {},
                    "reason": "judge_unavailable",
                },
            )
    except ReaderLLMError:
        payload = {}
    except Exception:
        payload = {}
    return _normalize_judgment(payload, left_key="attentional_v2", right_key="iterator_v1", score_keys=score_keys)


def _score_average(side_scores: dict[str, int]) -> float:
    values = [float(value) for value in side_scores.values()]
    return round(mean(values), 3) if values else 0.0


def _judge_scopes_for_case(
    *,
    case: ChapterCase,
    mechanism_results: dict[str, dict[str, Any]],
    run_root: Path,
    judge_mode: str,
    judge_execution_mode: str,
) -> dict[str, dict[str, Any]]:
    if judge_execution_mode == "serial" or judge_mode == "none" or len(DEFAULT_SCOPES) <= 1:
        return {
            scope: {
                "judgment": _judge_scope(
                    scope=scope,
                    case=case,
                    attentional=mechanism_results["attentional_v2"],
                    iterator=mechanism_results["iterator_v1"],
                    run_root=run_root,
                    judge_mode=judge_mode,
                )
            }
            for scope in DEFAULT_SCOPES
        }

    if judge_execution_mode != "parallel":
        raise ValueError(f"unsupported judge execution mode: {judge_execution_mode}")

    scope_results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=len(DEFAULT_SCOPES), thread_name_prefix="judge-scope") as executor:
        future_to_scope = {
            executor.submit(
                _judge_scope,
                scope=scope,
                case=case,
                attentional=mechanism_results["attentional_v2"],
                iterator=mechanism_results["iterator_v1"],
                run_root=run_root,
                judge_mode=judge_mode,
            ): scope
            for scope in DEFAULT_SCOPES
        }
        for future in as_completed(future_to_scope):
            scope = future_to_scope[future]
            scope_results[scope] = {"judgment": future.result()}
    return {scope: scope_results[scope] for scope in DEFAULT_SCOPES}


def _evaluate_case(
    case: ChapterCase,
    *,
    source: dict[str, Any],
    run_root: Path,
    judge_mode: str,
    mechanism_execution_mode: str,
    judge_execution_mode: str,
) -> dict[str, Any]:
    mechanism_results = _run_mechanisms_for_case(
        case,
        source,
        run_root=run_root,
        mechanism_execution_mode=mechanism_execution_mode,
    )
    scope_results = _judge_scopes_for_case(
        case=case,
        mechanism_results=mechanism_results,
        run_root=run_root,
        judge_mode=judge_mode,
        judge_execution_mode=judge_execution_mode,
    )
    return {
        "chapter_case_id": case.chapter_case_id,
        "language_track": case.language_track,
        "selection_role": case.selection_role,
        "book_title": case.book_title,
        "author": case.author,
        "source_id": case.source_id,
        "chapter_id": case.chapter_id,
        "chapter_title": case.chapter_title,
        "mechanisms": {
            key: {
                "mechanism_label": value["mechanism_label"],
                "output_dir": value["output_dir"],
                "bundle_summary": value["bundle_summary"],
            }
            for key, value in mechanism_results.items()
        },
        "scope_results": scope_results,
    }


def _aggregate(case_results: list[dict[str, Any]], scopes: list[str]) -> dict[str, Any]:
    aggregate: dict[str, Any] = {
        "case_count": len(case_results),
        "scopes": list(scopes),
        "scope_summaries": {},
    }
    for scope in scopes:
        scoped = [item["scope_results"][scope] for item in case_results]
        winner_counts = Counter(result["judgment"]["winner"] for result in scoped)
        by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for case_result, scoped_result in zip(case_results, scoped, strict=False):
            by_language[str(case_result["language_track"])].append(scoped_result)
        scope_summary = {
            "winner_counts": dict(winner_counts),
            "attentional_v2_win_or_tie_rate": round(
                (winner_counts.get("attentional_v2", 0) + winner_counts.get("tie", 0)) / max(1, len(scoped)),
                3,
            ),
            "attentional_v2_loss_rate": round(winner_counts.get("iterator_v1", 0) / max(1, len(scoped)), 3),
            "average_scores": {
                "attentional_v2": round(
                    mean(_score_average(result["judgment"]["scores"]["attentional_v2"]) for result in scoped),
                    3,
                ),
                "iterator_v1": round(
                    mean(_score_average(result["judgment"]["scores"]["iterator_v1"]) for result in scoped),
                    3,
                ),
            },
            "language_summaries": {},
        }
        for language, items in sorted(by_language.items()):
            lang_winners = Counter(result["judgment"]["winner"] for result in items)
            scope_summary["language_summaries"][language] = {
                "winner_counts": dict(lang_winners),
                "attentional_v2_win_or_tie_rate": round(
                    (lang_winners.get("attentional_v2", 0) + lang_winners.get("tie", 0)) / max(1, len(items)),
                    3,
                ),
                "attentional_v2_loss_rate": round(lang_winners.get("iterator_v1", 0) / max(1, len(items)), 3),
            }
        aggregate["scope_summaries"][scope] = scope_summary
    return aggregate


def _build_markdown_report(*, run_id: str, selected_cases: list[ChapterCase], aggregate: dict[str, Any], case_results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Chapter Comparison")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("This report records the first chapter-scale `local_reading_behavior` and `span_trajectory` comparison between `attentional_v2` and `iterator_v1` on a balanced core slice.")
    lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append(f"- Run ID: `{run_id}`")
    lines.append(f"- Target: `{DEFAULT_TARGET}`")
    lines.append(f"- Methods: `{', '.join(DEFAULT_METHODS)}`")
    lines.append(f"- Comparison target: {DEFAULT_COMPARISON_TARGET}")
    lines.append("")
    lines.append("## Selected Cases")
    lines.append("")
    for case in selected_cases:
        lines.append(f"- `{case.chapter_case_id}` (`{case.language_track}`, `{case.selection_role}`, `{case.book_title}`)")
    lines.append("")
    lines.append("## Aggregate Findings")
    lines.append("")
    for scope, summary in aggregate["scope_summaries"].items():
        lines.append(f"### `{scope}`")
        lines.append(f"- Winner counts: `{json.dumps(summary['winner_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- `attentional_v2` win-or-tie rate: `{summary['attentional_v2_win_or_tie_rate']}`")
        lines.append(f"- `attentional_v2` loss rate: `{summary['attentional_v2_loss_rate']}`")
        lines.append(f"- Average scores: `{json.dumps(summary['average_scores'], ensure_ascii=False, sort_keys=True)}`")
        for language, lang_summary in summary["language_summaries"].items():
            lines.append(f"- `{language}` winner counts: `{json.dumps(lang_summary['winner_counts'], ensure_ascii=False, sort_keys=True)}`")
            lines.append(f"- `{language}` `attentional_v2` win-or-tie rate: `{lang_summary['attentional_v2_win_or_tie_rate']}`")
        lines.append("")
    lines.append("## Case Highlights")
    lines.append("")
    for case_result in case_results:
        lines.append(f"- `{case_result['chapter_case_id']}`")
        for scope, scope_result in case_result["scope_results"].items():
            lines.append(f"  - `{scope}` winner: `{scope_result['judgment']['winner']}`")
            lines.append(f"  - reason: {scope_result['judgment']['reason']}")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def run_benchmark(
    *,
    dataset_dirs: list[Path],
    source_manifest_path: Path,
    runs_root: Path,
    run_id: str | None = None,
    judge_mode: str = "llm",
    case_ids: list[str] | None = None,
    mechanism_execution_mode: str = "parallel",
    judge_execution_mode: str = "parallel",
    case_workers: int | None = None,
) -> dict[str, Any]:
    manifests: list[dict[str, Any]] = []
    all_cases: list[ChapterCase] = []
    for dataset_dir in dataset_dirs:
        manifest, cases = _load_cases(dataset_dir)
        manifests.append(manifest)
        all_cases.extend(cases)
    selected_cases = (
        [case for case in all_cases if case.chapter_case_id in set(case_ids or [])]
        if case_ids
        else _select_core_cases(all_cases)
    )
    if not selected_cases:
        raise ValueError("no chapter cases selected")

    run_name = run_id or datetime.now(timezone.utc).strftime("attentional_v2_vs_iterator_v1_chapter_comparison_%Y%m%d-%H%M%S")
    run_root = runs_root / run_name
    run_root.mkdir(parents=True, exist_ok=True)
    source_index = _load_source_index(source_manifest_path)

    _json_dump(
        run_root / "dataset_manifest.json",
        {
            "target": DEFAULT_TARGET,
            "scopes": DEFAULT_SCOPES,
            "methods": DEFAULT_METHODS,
            "comparison_target": DEFAULT_COMPARISON_TARGET,
            "dataset_ids": [manifest["dataset_id"] for manifest in manifests],
            "selected_case_ids": [case.chapter_case_id for case in selected_cases],
            "judge_mode": judge_mode,
            "mechanism_execution_mode": mechanism_execution_mode,
            "judge_execution_mode": judge_execution_mode,
            "generated_at": _timestamp(),
        },
    )

    per_case_parallelism = 2 if (mechanism_execution_mode == "parallel" or (judge_mode != "none" and judge_execution_mode == "parallel")) else 1
    worker_policy = resolve_worker_policy(
        job_kind="chapter_case_comparison",
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        task_count=len(selected_cases),
        per_worker_parallelism=per_case_parallelism,
        explicit_max_workers=case_workers if case_workers and case_workers > 0 else None,
    )
    results_by_case_id: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, worker_policy.worker_count), thread_name_prefix="chapter-case") as executor:
        future_to_case = {}
        for index, case in enumerate(selected_cases, start=1):
            print(f"[submitted {index}/{len(selected_cases)}] {case.chapter_case_id}", flush=True)
            future_to_case[
                submit_inherited_context(
                    executor,
                    _evaluate_case,
                    case,
                    source=source_index[case.source_id],
                    run_root=run_root,
                    judge_mode=judge_mode,
                    mechanism_execution_mode=mechanism_execution_mode,
                    judge_execution_mode=judge_execution_mode,
                )
            ] = case
        for future in as_completed(future_to_case):
            case = future_to_case[future]
            case_payload = future.result()
            results_by_case_id[case.chapter_case_id] = case_payload
            _json_dump(run_root / "cases" / f"{case.chapter_case_id}.json", case_payload)
            print(f"[completed] {case.chapter_case_id}", flush=True)
    case_results = [results_by_case_id[case.chapter_case_id] for case in selected_cases]

    aggregate = _aggregate(case_results, DEFAULT_SCOPES)
    _json_dump(run_root / "summary" / "aggregate.json", aggregate)
    _jsonl_dump(run_root / "summary" / "case_results.jsonl", case_results)
    report_path = run_root / "summary" / "report.md"
    report_path.write_text(
        _build_markdown_report(run_id=run_name, selected_cases=selected_cases, aggregate=aggregate, case_results=case_results),
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
    parser.add_argument("--dataset-dir", action="append", default=[], help="Chapter corpus dataset directory.")
    parser.add_argument("--source-manifest", default=str(DEFAULT_SOURCE_MANIFEST))
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--judge-mode", choices=["llm", "none"], default="llm")
    parser.add_argument("--mechanism-execution-mode", choices=["serial", "parallel"], default="parallel")
    parser.add_argument("--judge-execution-mode", choices=["serial", "parallel"], default="parallel")
    parser.add_argument("--case-workers", type=int, default=0)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--case-ids", default="")
    parser.add_argument("--worker-payload", default="", help=argparse.SUPPRESS)
    parser.add_argument("--worker-result", default="", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.worker_payload:
        if not args.worker_result:
            raise ValueError("--worker-result is required when --worker-payload is set")
        return _run_mechanism_worker(Path(args.worker_payload).resolve(), Path(args.worker_result).resolve())
    dataset_dirs = [Path(item).resolve() for item in args.dataset_dir] if args.dataset_dir else list(DEFAULT_DATASET_DIRS)
    case_ids = [item.strip() for item in args.case_id if str(item).strip()]
    if args.case_ids:
        case_ids.extend([item.strip() for item in str(args.case_ids).split(",") if item.strip()])
    summary = run_benchmark(
        dataset_dirs=dataset_dirs,
        source_manifest_path=Path(args.source_manifest).resolve(),
        runs_root=Path(args.runs_root).resolve(),
        run_id=args.run_id or None,
        judge_mode=args.judge_mode,
        case_ids=case_ids or None,
        mechanism_execution_mode=args.mechanism_execution_mode,
        judge_execution_mode=args.judge_execution_mode,
        case_workers=args.case_workers or None,
    )
    print(json.dumps(summary["aggregate"], ensure_ascii=False, indent=2))
    print(f"run_root={summary['run_root']}")
    print(f"report_path={summary['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
