"""Run durable-trace comparison and re-entry audits for the decisive eval lane."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import nullcontext
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from eval.common.taxonomy import DETERMINISTIC_METRICS, RUBRIC_JUDGE, normalize_methods, validate_target_slug
from src.attentional_v2.resume import resume_from_checkpoint
from src.iterator_reader.llm_utils import LLMTraceContext, ReaderLLMError, invoke_json, llm_invocation_scope
from src.reading_core.runtime_contracts import ReadRequest
from src.reading_core.storage import existing_book_document_file, load_book_document
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_mechanisms.iterator_v1 import IteratorV1Mechanism
from src.reading_runtime.job_concurrency import resolve_worker_policy, submit_inherited_context
from src.reading_runtime.llm_registry import DEFAULT_EVAL_JUDGE_PROFILE_ID
from src.reading_runtime.output_dir_overrides import override_output_dir


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHAPTER_DATASET_DIRS = (
    ROOT / "eval" / "datasets" / "chapter_corpora" / "attentional_v2_chapters_en_v2",
    ROOT / "eval" / "datasets" / "chapter_corpora" / "attentional_v2_chapters_zh_v2",
)
DEFAULT_RUNTIME_FIXTURE_DIRS = (
    ROOT / "eval" / "datasets" / "runtime_fixtures" / "attentional_v2_runtime_en_v2",
    ROOT / "eval" / "datasets" / "runtime_fixtures" / "attentional_v2_runtime_zh_v2",
)
DEFAULT_SOURCE_MANIFEST = ROOT / "eval" / "manifests" / "source_books" / "attentional_v2_public_benchmark_pool_v2.json"
DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_TARGET = validate_target_slug("durable_trace_reentry_gate")
DEFAULT_METHODS = normalize_methods([DETERMINISTIC_METRICS, RUBRIC_JUDGE])
DEFAULT_COMPARISON_TARGET = "attentional_v2 vs iterator_v1 durable-trace comparison plus attentional_v2 re-entry audit"
DEFAULT_USER_INTENT = (
    "Read as a thoughtful co-reader and notice meaningful turns, tensions, callbacks, definitions, and chapter-level development."
)
SELECTION_ROLES = ("expository", "argumentative", "narrative_reflective", "reference_heavy")
MECHANISM_KEYS = ("attentional_v2", "iterator_v1")
RESUME_KIND_MAP = {
    "warm": "warm_resume",
    "cold": "cold_resume",
    "reconstitution": "reconstitution_resume",
}

JUDGE_SYSTEM = """You are doing offline cross-mechanism reader evaluation.

Question family: durable_trace.

Compare the durable reading trail left by two mechanisms after reading the same chapter.
Focus on whether the saved trace would help a later return, mark, or re-entry.

Scoring dimensions:
- anchor_traceability
- reaction_reusability
- memory_carryover
- return_path_clarity
- later_value

Use integer scores from 1 to 5.
Return JSON only."""

JUDGE_PROMPT = """Chapter case:
{case_json}

Attentional V2 durable trace:
{left_json}

Iterator V1 durable trace:
{right_json}

Return JSON:
{{
  "winner": "attentional_v2|iterator_v1|tie",
  "confidence": "high|medium|low",
  "scores": {{
    "attentional_v2": {{
      "anchor_traceability": 1,
      "reaction_reusability": 1,
      "memory_carryover": 1,
      "return_path_clarity": 1,
      "later_value": 1
    }},
    "iterator_v1": {{
      "anchor_traceability": 1,
      "reaction_reusability": 1,
      "memory_carryover": 1,
      "return_path_clarity": 1,
      "later_value": 1
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


@dataclass(frozen=True)
class RuntimeFixture:
    fixture_id: str
    source_id: str
    language_track: str
    chapter_case_id: str
    selection_role: str
    resume_kind: str
    target_sentence_index: int
    dataset_id: str
    dataset_version: str


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json_payload(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _load_chapter_cases(dataset_dir: Path) -> tuple[dict[str, Any], list[ChapterCase]]:
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


def _load_runtime_fixtures(dataset_dir: Path) -> tuple[dict[str, Any], list[RuntimeFixture]]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: list[RuntimeFixture] = []
    with (dataset_dir / str(manifest["primary_file"])).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(
                RuntimeFixture(
                    fixture_id=str(raw["fixture_id"]),
                    source_id=str(raw["source_id"]),
                    language_track=str(raw["language_track"]),
                    chapter_case_id=str(raw["chapter_case_id"]),
                    selection_role=str(raw.get("selection_role", "")),
                    resume_kind=str(raw.get("resume_kind", "")),
                    target_sentence_index=int(raw.get("target_sentence_index", 0) or 0),
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


def _case_sort_key(case: ChapterCase) -> tuple[int, int, float, str]:
    return (case.sentence_count, case.selection_priority, -case.candidate_score, case.chapter_case_id)


def _select_fixture_linked_cases(chapter_cases: list[ChapterCase], fixtures: list[RuntimeFixture]) -> list[ChapterCase]:
    fixture_case_ids = {fixture.chapter_case_id for fixture in fixtures}
    eligible = [case for case in chapter_cases if case.chapter_case_id in fixture_case_ids and case.selection_role in SELECTION_ROLES]
    if not eligible:
        raise ValueError("no chapter cases overlap with runtime fixtures")
    selected: list[ChapterCase] = []
    by_language_role: dict[tuple[str, str], list[ChapterCase]] = defaultdict(list)
    for case in eligible:
        by_language_role[(case.language_track, case.selection_role)].append(case)
    for language in ("en", "zh"):
        for role in SELECTION_ROLES:
            options = sorted(by_language_role.get((language, role), []), key=_case_sort_key)
            if options:
                selected.append(options[0])
    if selected:
        seen: set[str] = set()
        deduped: list[ChapterCase] = []
        for case in selected:
            if case.chapter_case_id in seen:
                continue
            seen.add(case.chapter_case_id)
            deduped.append(case)
        return deduped
    return sorted(eligible, key=_case_sort_key)


def _summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    chapters = bundle.get("chapters") or []
    chapter_summary = dict(chapters[0]) if isinstance(chapters, list) and chapters else {}
    reactions = []
    for item in bundle.get("reactions") or []:
        if not isinstance(item, dict):
            continue
        reactions.append(
            {
                "type": _clean_text(item.get("type")),
                "section_ref": _clean_text(item.get("section_ref")),
                "anchor_quote": _clean_text(item.get("anchor_quote"))[:180],
                "content": _clean_text(item.get("content"))[:220],
                "related_anchor_count": len(item.get("related_anchors") or []),
                "has_primary_anchor": bool(item.get("primary_anchor")),
            }
        )
    snapshot = dict(bundle.get("run_snapshot") or {})
    return {
        "run_snapshot": {
            "status": _clean_text(snapshot.get("status")),
            "resume_available": bool(snapshot.get("resume_available")) if snapshot.get("resume_available") is not None else None,
            "last_checkpoint_at": snapshot.get("last_checkpoint_at"),
            "completed_chapters": int(snapshot.get("completed_chapters", 0) or 0),
            "total_chapters": int(snapshot.get("total_chapters", 0) or 0),
        },
        "chapter_output": chapter_summary,
        "reaction_count": len(reactions),
        "memory_summary_count": len(bundle.get("memory_summaries") or []),
        "reactions": reactions[:5],
        "memory_summaries": [str(item)[:240] for item in (bundle.get("memory_summaries") or [])[:4]],
    }


def _default_judgment() -> dict[str, Any]:
    score_keys = (
        "anchor_traceability",
        "reaction_reusability",
        "memory_carryover",
        "return_path_clarity",
        "later_value",
    )
    return {
        "winner": "tie",
        "confidence": "low",
        "scores": {
            "attentional_v2": {key: 0 for key in score_keys},
            "iterator_v1": {key: 0 for key in score_keys},
        },
        "reason": "judge_disabled",
    }


def _normalize_judgment(payload: object) -> dict[str, Any]:
    normalized = _default_judgment()
    if not isinstance(payload, dict):
        return normalized
    winner = _clean_text(payload.get("winner")).lower()
    if winner in {"attentional_v2", "iterator_v1", "tie"}:
        normalized["winner"] = winner
    confidence = _clean_text(payload.get("confidence")).lower()
    if confidence in {"high", "medium", "low"}:
        normalized["confidence"] = confidence
    scores = payload.get("scores")
    if isinstance(scores, dict):
        for side in ("attentional_v2", "iterator_v1"):
            side_scores = scores.get(side)
            if not isinstance(side_scores, dict):
                continue
            for key in normalized["scores"][side]:
                try:
                    value = int(side_scores.get(key))
                except (TypeError, ValueError):
                    value = 0
                normalized["scores"][side][key] = max(0, min(5, value))
    normalized["reason"] = _clean_text(payload.get("reason")) or normalized["reason"]
    return normalized


def _score_average(side_scores: dict[str, int]) -> float:
    values = [float(value) for value in side_scores.values()]
    return round(mean(values), 3) if values else 0.0


def _mechanism_failure_judgment(error: str) -> dict[str, Any]:
    judgment = _default_judgment()
    judgment["reason"] = _clean_text(error) or "mechanism_failure"
    return judgment


def _log_case_progress(case: ChapterCase, message: str) -> None:
    print(f"[durable case {case.chapter_case_id}] {message}", flush=True)


def _base_case_payload(case: ChapterCase, runtime_fixtures: list[RuntimeFixture]) -> dict[str, Any]:
    return {
        "chapter_case_id": case.chapter_case_id,
        "language_track": case.language_track,
        "selection_role": case.selection_role,
        "book_title": case.book_title,
        "author": case.author,
        "source_id": case.source_id,
        "chapter_id": case.chapter_id,
        "chapter_title": case.chapter_title,
        "runtime_fixture_ids": [fixture.fixture_id for fixture in runtime_fixtures],
    }


def _case_failure_payload(
    case: ChapterCase,
    *,
    runtime_fixtures: list[RuntimeFixture],
    stage: str,
    error_message: str,
    mechanisms: dict[str, Any] | None = None,
    reentry_audits: dict[str, dict[str, Any]] | None = None,
    traceback_text: str = "",
) -> dict[str, Any]:
    error_payload: dict[str, Any] = {
        "stage": stage,
        "error": error_message,
    }
    if traceback_text:
        error_payload["traceback"] = traceback_text
    return {
        **_base_case_payload(case, runtime_fixtures),
        "case_status": "failed",
        "errors": [error_payload],
        "mechanisms": mechanisms or {},
        "durable_trace": _default_judgment(),
        "reentry_audits": reentry_audits or {},
    }


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
    _log_case_progress(case, f"[mechanism-start] {mechanism_key}")
    shutil.rmtree(isolated_output_dir, ignore_errors=True)
    isolated_output_dir.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    bundle: dict[str, Any] = {}
    error = ""
    output_dir = isolated_output_dir
    mechanism_label = mechanism.label
    success = False
    try:
        with override_output_dir(isolated_output_dir):
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
        output_dir = result.output_dir
        mechanism_label = result.mechanism.label
        success = True
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    duration_seconds = round(time.perf_counter() - started, 3)
    _json_dump(run_root / "bundles" / mechanism_key / f"{case.chapter_case_id}.json", bundle)
    _log_case_progress(case, f"[mechanism-completed] {mechanism_key} success={success}")
    return {
        "mechanism_key": mechanism_key,
        "mechanism_label": mechanism_label,
        "output_dir": str(output_dir),
        "success": success,
        "error": error,
        "duration_seconds": duration_seconds,
        "bundle_summary": _summarize_bundle(bundle),
    }


def _judge_durable_trace(
    *,
    case: ChapterCase,
    attentional: dict[str, Any],
    iterator: dict[str, Any],
    run_root: Path,
    judge_mode: str,
) -> dict[str, Any]:
    if not bool(attentional.get("success")) or not bool(iterator.get("success")):
        error_parts = [str(side.get("error", "")).strip() for side in (attentional, iterator) if str(side.get("error", "")).strip()]
        return _mechanism_failure_judgment("; ".join(error_parts))
    if judge_mode == "none":
        return _default_judgment()
    try:
        with llm_invocation_scope(
            profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
            trace_context=LLMTraceContext(stage="durable_trace_reentry", node="durable_trace_judge"),
        ):
            payload = invoke_json(
                JUDGE_SYSTEM,
                JUDGE_PROMPT.format(
                    case_json=json.dumps(
                        {
                            "chapter_case_id": case.chapter_case_id,
                            "book_title": case.book_title,
                            "author": case.author,
                            "language_track": case.language_track,
                            "selection_role": case.selection_role,
                            "chapter_title": case.chapter_title,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    left_json=json.dumps(attentional["bundle_summary"], ensure_ascii=False, indent=2),
                    right_json=json.dumps(iterator["bundle_summary"], ensure_ascii=False, indent=2),
                ),
                _default_judgment(),
            )
    except ReaderLLMError:
        payload = {}
    except Exception:
        payload = {}
    return _normalize_judgment(payload)


def _run_reentry_audits(
    *,
    case: ChapterCase,
    attentional_output_dir: Path,
    run_root: Path,
    runtime_fixtures: list[RuntimeFixture],
    attentional_success: bool,
    attentional_error: str,
) -> dict[str, dict[str, Any]]:
    audits: dict[str, dict[str, Any]] = {}
    for fixture in runtime_fixtures:
        requested_resume_kind = RESUME_KIND_MAP.get(fixture.resume_kind)
        if not requested_resume_kind:
            continue
        if not attentional_success:
            audits[fixture.resume_kind] = {
                "requested_resume_kind": requested_resume_kind,
                "error": _clean_text(attentional_error) or "attentional_mechanism_failed",
                "compatibility_status": "mechanism_failure",
                "resume_window_sentence_count": 0,
                "reconstructed_hot_state": False,
                "target_sentence_index": fixture.target_sentence_index,
            }
            continue
        audit_dir = run_root / "reentry" / case.chapter_case_id / fixture.resume_kind
        shutil.rmtree(audit_dir, ignore_errors=True)
        shutil.copytree(attentional_output_dir, audit_dir)
        try:
            book_document = load_book_document(existing_book_document_file(audit_dir))
            payload = resume_from_checkpoint(
                audit_dir,
                book_document=book_document,
                requested_resume_kind=requested_resume_kind,  # type: ignore[arg-type]
            )
            cursor = dict(payload.get("cursor") or {})
            resume_metadata = dict(payload.get("resume_metadata") or {})
            audits[fixture.resume_kind] = {
                "requested_resume_kind": requested_resume_kind,
                "effective_resume_kind": _clean_text(payload.get("effective_resume_kind")),
                "compatibility_status": _clean_text(payload.get("compatibility_status")),
                "compatibility_issues": [str(item) for item in payload.get("compatibility_issues", [])],
                "checkpoint_id": payload.get("checkpoint_id"),
                "resume_window_sentence_count": len(payload.get("resume_window_sentence_ids", []) or []),
                "reconstructed_hot_state": bool(resume_metadata.get("reconstructed_hot_state")),
                "current_sentence_id": _clean_text(cursor.get("sentence_id")),
                "span_start_sentence_id": _clean_text(cursor.get("span_start_sentence_id")),
                "span_end_sentence_id": _clean_text(cursor.get("span_end_sentence_id")),
                "target_sentence_index": fixture.target_sentence_index,
            }
        except Exception as exc:
            audits[fixture.resume_kind] = {
                "requested_resume_kind": requested_resume_kind,
                "error": f"{type(exc).__name__}: {exc}",
                "compatibility_status": "runner_error",
                "resume_window_sentence_count": 0,
                "reconstructed_hot_state": False,
                "target_sentence_index": fixture.target_sentence_index,
            }
    return audits


def _evaluate_case(
    case: ChapterCase,
    *,
    source: dict[str, Any],
    run_root: Path,
    judge_mode: str,
    runtime_fixtures: list[RuntimeFixture],
) -> dict[str, Any]:
    _log_case_progress(case, "[case-start]")
    mechanism_results = {
        mechanism_key: _run_mechanism_for_case(case, source, mechanism_key=mechanism_key, run_root=run_root)
        for mechanism_key in MECHANISM_KEYS
    }
    durable_trace = _judge_durable_trace(
        case=case,
        attentional=mechanism_results["attentional_v2"],
        iterator=mechanism_results["iterator_v1"],
        run_root=run_root,
        judge_mode=judge_mode,
    )
    reentry_audits = _run_reentry_audits(
        case=case,
        attentional_output_dir=Path(mechanism_results["attentional_v2"]["output_dir"]),
        run_root=run_root,
        runtime_fixtures=runtime_fixtures,
        attentional_success=bool(mechanism_results["attentional_v2"].get("success")),
        attentional_error=str(mechanism_results["attentional_v2"].get("error", "")),
    )
    mechanism_failures = {
        key: str(value.get("error", "")).strip()
        for key, value in mechanism_results.items()
        if not bool(value.get("success")) and str(value.get("error", "")).strip()
    }
    errors = [
        {
            "stage": f"{mechanism_key}_run",
            "error": error_message,
        }
        for mechanism_key, error_message in mechanism_failures.items()
    ]
    _log_case_progress(case, "[case-completed]")
    return {
        **_base_case_payload(case, runtime_fixtures),
        "case_status": "completed" if not mechanism_failures else "partial_failure",
        "case_error": "; ".join(mechanism_failures.values()),
        "errors": errors,
        "mechanisms": {
            key: {
                "mechanism_label": value["mechanism_label"],
                "output_dir": value["output_dir"],
                "success": bool(value.get("success")),
                "error": str(value.get("error", "")),
                "duration_seconds": float(value.get("duration_seconds", 0.0) or 0.0),
                "bundle_summary": value["bundle_summary"],
            }
            for key, value in mechanism_results.items()
        },
        "durable_trace": durable_trace,
        "reentry_audits": reentry_audits,
    }


def _case_failure_result(
    case: ChapterCase,
    *,
    runtime_fixtures: list[RuntimeFixture],
    error: str,
) -> dict[str, Any]:
    return {
        **_base_case_payload(case, runtime_fixtures),
        "case_status": "runner_error",
        "case_error": _clean_text(error),
        "errors": [{"stage": "case_runner", "error": _clean_text(error)}],
        "mechanisms": {},
        "durable_trace": _mechanism_failure_judgment(error),
        "reentry_audits": {
            fixture.resume_kind: {
                "requested_resume_kind": RESUME_KIND_MAP.get(fixture.resume_kind, ""),
                "error": _clean_text(error),
                "compatibility_status": "runner_error",
                "resume_window_sentence_count": 0,
                "reconstructed_hot_state": False,
                "target_sentence_index": fixture.target_sentence_index,
            }
            for fixture in runtime_fixtures
            if RESUME_KIND_MAP.get(fixture.resume_kind)
        },
    }


def _run_case_worker(payload_path: Path, result_path: Path) -> int:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    case = ChapterCase(**dict(payload["case"]))
    runtime_fixtures = [RuntimeFixture(**dict(item)) for item in payload.get("runtime_fixtures", [])]
    try:
        result = _evaluate_case(
            case,
            source=dict(payload["source"]),
            run_root=Path(str(payload["run_root"])),
            judge_mode=str(payload["judge_mode"]),
            runtime_fixtures=runtime_fixtures,
        )
    except Exception as exc:
        result = _case_failure_payload(
            case,
            runtime_fixtures=runtime_fixtures,
            stage="case_worker",
            error_message=f"{type(exc).__name__}: {exc}",
            traceback_text=traceback.format_exc(),
        )
    _write_json_payload(result_path, result)
    return 0


def _run_case_subprocess(
    case: ChapterCase,
    *,
    source: dict[str, Any],
    run_root: Path,
    judge_mode: str,
    runtime_fixtures: list[RuntimeFixture],
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="durable-trace-case-worker-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        payload_path = temp_dir / "payload.json"
        result_path = temp_dir / "result.json"
        _write_json_payload(
            payload_path,
            {
                "case": asdict(case),
                "source": source,
                "run_root": str(run_root),
                "judge_mode": judge_mode,
                "runtime_fixtures": [asdict(item) for item in runtime_fixtures],
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
        completed = subprocess.run(command, cwd=str(ROOT), check=False)
        if result_path.exists():
            return json.loads(result_path.read_text(encoding="utf-8"))
        return _case_failure_payload(
            case,
            runtime_fixtures=runtime_fixtures,
            stage="case_subprocess",
            error_message=f"case worker exited with code {completed.returncode}",
        )


def _aggregate(case_results: list[dict[str, Any]]) -> dict[str, Any]:
    completed_case_results = [
        item for item in case_results if _clean_text(item.get("case_status") or "completed") == "completed"
    ]
    failed_case_results = [
        item for item in case_results if _clean_text(item.get("case_status") or "completed") != "completed"
    ]
    durable_rows = [item["durable_trace"] for item in completed_case_results]
    winner_counts = Counter(result["winner"] for result in durable_rows)
    aggregate: dict[str, Any] = {
        "case_count": len(case_results),
        "evaluated_case_count": len(completed_case_results),
        "failed_case_count": len(failed_case_results),
        "failed_case_ids": [str(item.get("chapter_case_id", "")) for item in failed_case_results],
        "case_status_counts": dict(Counter(_clean_text(item.get("case_status", "completed")) for item in case_results)),
        "durable_trace_summary": {
            "evaluated_case_count": len(durable_rows),
            "winner_counts": dict(winner_counts),
            "attentional_v2_win_or_tie_rate": round(
                (winner_counts.get("attentional_v2", 0) + winner_counts.get("tie", 0)) / max(1, len(durable_rows)),
                3,
            ),
            "average_scores": {
                "attentional_v2": round(mean(_score_average(item["scores"]["attentional_v2"]) for item in durable_rows), 3)
                if durable_rows
                else 0.0,
                "iterator_v1": round(mean(_score_average(item["scores"]["iterator_v1"]) for item in durable_rows), 3)
                if durable_rows
                else 0.0,
            },
        },
        "reentry_summary": {},
    }
    by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case_result in case_results:
        for kind, audit in dict(case_result.get("reentry_audits") or {}).items():
            by_kind[str(kind)].append(dict(audit))
    for kind, audits in sorted(by_kind.items()):
        aggregate["reentry_summary"][kind] = {
            "case_count": len(audits),
            "compatibility_status_counts": dict(Counter(_clean_text(item.get("compatibility_status")) for item in audits)),
            "effective_resume_kind_counts": dict(Counter(_clean_text(item.get("effective_resume_kind")) for item in audits)),
            "average_resume_window_sentence_count": round(
                mean(int(item.get("resume_window_sentence_count", 0) or 0) for item in audits),
                3,
            )
            if audits
            else 0.0,
            "reconstructed_hot_state_count": sum(1 for item in audits if bool(item.get("reconstructed_hot_state"))),
        }
    return aggregate


def _build_markdown_report(*, run_id: str, selected_cases: list[ChapterCase], aggregate: dict[str, Any], case_results: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append("# Durable Trace And Re-entry")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("This report records durable-trace comparison and attentional_v2 re-entry audits on fixture-linked chapter cases.")
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
    lines.append(f"- Case statuses: `{json.dumps(aggregate['case_status_counts'], ensure_ascii=False, sort_keys=True)}`")
    lines.append(f"- Evaluated case count: `{aggregate['evaluated_case_count']}`")
    lines.append(f"- Failed case count: `{aggregate['failed_case_count']}`")
    if aggregate["failed_case_ids"]:
        lines.append(f"- Failed case ids: `{json.dumps(aggregate['failed_case_ids'], ensure_ascii=False)}`")
    lines.append("")
    durable_summary = aggregate["durable_trace_summary"]
    lines.append("### `durable_trace`")
    lines.append(f"- Winner counts: `{json.dumps(durable_summary['winner_counts'], ensure_ascii=False, sort_keys=True)}`")
    lines.append(f"- `attentional_v2` win-or-tie rate: `{durable_summary['attentional_v2_win_or_tie_rate']}`")
    lines.append(f"- Average scores: `{json.dumps(durable_summary['average_scores'], ensure_ascii=False, sort_keys=True)}`")
    lines.append("")
    for kind, summary in aggregate["reentry_summary"].items():
        lines.append(f"### `reentry:{kind}`")
        lines.append(f"- Case count: `{summary['case_count']}`")
        lines.append(f"- Compatibility statuses: `{json.dumps(summary['compatibility_status_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Effective resume kinds: `{json.dumps(summary['effective_resume_kind_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Average resume window sentence count: `{summary['average_resume_window_sentence_count']}`")
        lines.append("")
    lines.append("## Case Highlights")
    lines.append("")
    for case_result in case_results:
        case_status = _clean_text(case_result.get("case_status") or "completed")
        if case_status == "completed":
            lines.append(f"- `{case_result['chapter_case_id']}` status=`completed` durable winner=`{case_result['durable_trace']['winner']}`")
        else:
            lines.append(
                f"- `{case_result['chapter_case_id']}` status=`{case_status}` case_error=`{_clean_text(case_result.get('case_error'))}`"
            )
        if _clean_text(case_result.get("case_error")):
            lines.append(f"  - case_error=`{_clean_text(case_result.get('case_error'))}`")
        for error in case_result.get("errors", []) or []:
            if not isinstance(error, dict):
                continue
            lines.append(
                f"  - error `{_clean_text(error.get('stage')) or 'unknown'}`: `{_clean_text(error.get('error')) or 'unknown failure'}`"
            )
        for mechanism_key in MECHANISM_KEYS:
            mechanism = dict(case_result.get("mechanisms", {}).get(mechanism_key) or {})
            if not mechanism:
                continue
            lines.append(
                f"  - `{mechanism_key}` success=`{bool(mechanism.get('success'))}` duration_seconds=`{mechanism.get('duration_seconds', 0)}` error=`{_clean_text(mechanism.get('error'))}`"
            )
        for kind, audit in dict(case_result.get("reentry_audits") or {}).items():
            lines.append(
                f"  - `{kind}` compatibility=`{audit.get('compatibility_status', '')}` window=`{audit.get('resume_window_sentence_count', 0)}`"
            )
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def run_benchmark(
    *,
    chapter_dataset_dirs: list[Path],
    runtime_fixture_dirs: list[Path],
    source_manifest_path: Path,
    runs_root: Path,
    run_id: str | None = None,
    judge_mode: str = "llm",
    case_ids: list[str] | None = None,
    case_workers: int | None = None,
) -> dict[str, Any]:
    chapter_manifests: list[dict[str, Any]] = []
    chapter_cases: list[ChapterCase] = []
    for dataset_dir in chapter_dataset_dirs:
        manifest, cases = _load_chapter_cases(dataset_dir)
        chapter_manifests.append(manifest)
        chapter_cases.extend(cases)
    runtime_manifests: list[dict[str, Any]] = []
    runtime_fixtures: list[RuntimeFixture] = []
    for dataset_dir in runtime_fixture_dirs:
        manifest, fixtures = _load_runtime_fixtures(dataset_dir)
        runtime_manifests.append(manifest)
        runtime_fixtures.extend(fixtures)
    fixtures_by_case_id: dict[str, list[RuntimeFixture]] = defaultdict(list)
    for fixture in runtime_fixtures:
        fixtures_by_case_id[fixture.chapter_case_id].append(fixture)

    selected_cases = (
        [case for case in chapter_cases if case.chapter_case_id in set(case_ids or [])]
        if case_ids
        else _select_fixture_linked_cases(chapter_cases, runtime_fixtures)
    )
    if not selected_cases:
        raise ValueError("no durable-trace cases selected")

    run_name = run_id or datetime.now(timezone.utc).strftime("attentional_v2_durable_trace_reentry_%Y%m%d-%H%M%S")
    run_root = runs_root / run_name
    run_root.mkdir(parents=True, exist_ok=True)
    source_index = _load_source_index(source_manifest_path)

    _json_dump(
        run_root / "dataset_manifest.json",
        {
            "target": DEFAULT_TARGET,
            "methods": DEFAULT_METHODS,
            "comparison_target": DEFAULT_COMPARISON_TARGET,
            "chapter_dataset_ids": [manifest["dataset_id"] for manifest in chapter_manifests],
            "runtime_fixture_dataset_ids": [manifest["dataset_id"] for manifest in runtime_manifests],
            "selected_case_ids": [case.chapter_case_id for case in selected_cases],
            "judge_mode": judge_mode,
            "generated_at": _timestamp(),
        },
    )

    worker_policy = resolve_worker_policy(
        job_kind="durable_trace_reentry",
        profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID if judge_mode != "none" else "runtime_reader_default",
        task_count=len(selected_cases),
        per_worker_parallelism=2,
        explicit_max_workers=case_workers if case_workers and case_workers > 0 else None,
    )
    case_runner = _run_case_subprocess if worker_policy.worker_count > 1 else _evaluate_case
    results_by_case_id: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, worker_policy.worker_count), thread_name_prefix="durable-case") as executor:
        future_to_case = {}
        for index, case in enumerate(selected_cases, start=1):
            print(f"[submitted {index}/{len(selected_cases)}] {case.chapter_case_id}", flush=True)
            future_to_case[
                submit_inherited_context(
                    executor,
                    case_runner,
                    case,
                    source=source_index[case.source_id],
                    run_root=run_root,
                    judge_mode=judge_mode,
                    runtime_fixtures=fixtures_by_case_id.get(case.chapter_case_id, []),
                )
            ] = case
        for future in as_completed(future_to_case):
            case = future_to_case[future]
            try:
                case_payload = future.result()
            except Exception as exc:
                case_payload = _case_failure_result(
                    case,
                    runtime_fixtures=fixtures_by_case_id.get(case.chapter_case_id, []),
                    error=f"{type(exc).__name__}: {exc}",
                )
            results_by_case_id[case.chapter_case_id] = case_payload
            _json_dump(run_root / "cases" / f"{case.chapter_case_id}.json", case_payload)
            print(f"[completed] {case.chapter_case_id}", flush=True)

    case_results = [results_by_case_id[case.chapter_case_id] for case in selected_cases]
    aggregate = _aggregate(case_results)
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
    parser.add_argument("--chapter-dataset-dir", action="append", default=[], help="Chapter corpus dataset directory.")
    parser.add_argument("--runtime-fixture-dir", action="append", default=[], help="Runtime fixture dataset directory.")
    parser.add_argument("--source-manifest", default=str(DEFAULT_SOURCE_MANIFEST))
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--judge-mode", choices=["llm", "none"], default="llm")
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
        return _run_case_worker(Path(args.worker_payload).resolve(), Path(args.worker_result).resolve())
    chapter_dataset_dirs = (
        [Path(item).resolve() for item in args.chapter_dataset_dir]
        if args.chapter_dataset_dir
        else list(DEFAULT_CHAPTER_DATASET_DIRS)
    )
    runtime_fixture_dirs = (
        [Path(item).resolve() for item in args.runtime_fixture_dir]
        if args.runtime_fixture_dir
        else list(DEFAULT_RUNTIME_FIXTURE_DIRS)
    )
    case_ids = [item.strip() for item in args.case_id if str(item).strip()]
    if args.case_ids:
        case_ids.extend([item.strip() for item in str(args.case_ids).split(",") if item.strip()])
    summary = run_benchmark(
        chapter_dataset_dirs=chapter_dataset_dirs,
        runtime_fixture_dirs=runtime_fixture_dirs,
        source_manifest_path=Path(args.source_manifest).resolve(),
        runs_root=Path(args.runs_root).resolve(),
        run_id=args.run_id or None,
        judge_mode=args.judge_mode,
        case_ids=case_ids or None,
        case_workers=args.case_workers or None,
    )
    print(json.dumps(summary["aggregate"], ensure_ascii=False, indent=2))
    print(f"run_root={summary['run_root']}")
    print(f"report_path={summary['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
