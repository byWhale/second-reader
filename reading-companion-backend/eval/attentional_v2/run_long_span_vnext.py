"""Run the Phase-1 Long Span vNext benchmark."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from statistics import mean
import time
from typing import Any

from eval.attentional_v2.completed_output_reuse import rebuild_normalized_bundle_from_completed_output, run_state_status
from eval.attentional_v2.llm_usage_summary import write_llm_usage_summary
from eval.attentional_v2.user_level_selective_v1 import DATASET_DIR, MANIFEST_PATH
from src.attentional_v2.benchmark_probes import is_memory_quality_probe_export_complete, load_memory_quality_probe_export
from src.attentional_v2.storage import load_json as load_attentional_v2_json
from src.attentional_v2.storage import memory_quality_probe_export_file, normalized_eval_bundle_file, reaction_records_file
from src.iterator_reader.llm_utils import ReaderLLMError, invoke_json, llm_invocation_scope
from src.reading_core.runtime_contracts import ReadRequest
from src.reading_core.storage import book_document_file
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_mechanisms.iterator_v1 import IteratorV1Mechanism
from src.reading_runtime.llm_gateway import eval_trace_context
from src.reading_runtime.llm_registry import DEFAULT_EVAL_JUDGE_PROFILE_ID
from src.reading_runtime.output_dir_overrides import override_output_dir


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_REACTION_REUSE_RUN_ROOT = DEFAULT_RUNS_ROOT / "attentional_v2_user_level_selective_v1_active_rerun_20260419"
DEFAULT_TARGET = "long_span_vnext_phase1"
DEFAULT_USER_INTENT = (
    "Read as a thoughtful co-reader, maintain meaningful memory continuity, and surface visible reactions when earlier material naturally comes back into view."
)
MECHANISM_KEYS = ("attentional_v2", "iterator_v1")
REACTION_LABELS = ("local_only", "grounded_callback", "weak_callback", "false_visible_integration")
JUDGE_MODE_VALUES = ("llm", "none")
JUDGE_SCHEMA_RETRY_INSTRUCTION = (
    "\n\nReminder: return exactly one JSON object matching the requested schema. "
    "Do not wrap it in markdown fences or nest it under another key."
)
DEFAULT_OUTPUT_ATTEMPTS = 4
DEFAULT_OUTPUT_RETRY_SLEEP_SECONDS = 300
RETRYABLE_OUTPUT_ERROR_MARKERS = (
    "overloaded",
    "timeout",
    "timed out",
    "rate limit",
    "quota",
    "529",
    "520",
)


def _run_in_parallel(items: list[Any], worker_count: int, fn) -> list[Any]:
    if worker_count <= 1 or len(items) <= 1:
        return [fn(item) for item in items]

    results: list[Any] = [None] * len(items)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_index = {executor.submit(fn, item): index for index, item in enumerate(items)}
        for future in as_completed(future_to_index):
            results[future_to_index[future]] = future.result()
    return results


def _output_dir_for(run_root: Path, segment_id: str, mechanism_key: str) -> Path:
    return run_root / "outputs" / segment_id / mechanism_key


def _runtime_error_text(output_dir: Path) -> str:
    state_path = output_dir / "_runtime" / "run_state.json"
    if not state_path.exists():
        return ""
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    return _clean_text(payload.get("error"))


def _is_retryable_output_error(exc: BaseException, *, output_dir: Path) -> bool:
    text = f"{exc} {_runtime_error_text(output_dir)}".lower()
    return any(marker in text for marker in RETRYABLE_OUTPUT_ERROR_MARKERS)


@dataclass(frozen=True)
class ReadingWindow:
    segment_id: str
    source_id: str
    book_title: str
    author: str
    language_track: str
    start_sentence_id: str
    end_sentence_id: str
    source_chapter_ids: list[int]
    chapter_titles: list[str]
    target_note_count: int
    covered_note_count: int
    termination_reason: str
    segment_source_path: str


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _json_dump(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _resolve_dataset_dir(manifest_path: Path) -> Path:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    refs = dict(payload.get("source_refs") or {})
    roots = [Path(str(item)) for item in refs.get("user_level_dataset_roots") or []]
    if roots:
        root = roots[0]
        return root if root.is_absolute() else (ROOT / root).resolve()
    return DATASET_DIR.resolve()


def _resolve_path(value: object, *, base: Path = ROOT) -> Path:
    path = Path(str(value))
    return path if path.is_absolute() else (base / path).resolve()


def _load_windows(dataset_dir: Path) -> list[ReadingWindow]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    with (dataset_dir / str(manifest["segments_file"])).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return [
        ReadingWindow(
            segment_id=str(row["segment_id"]),
            source_id=str(row["source_id"]),
            book_title=str(row["book_title"]),
            author=str(row.get("author", "")),
            language_track=str(row["language_track"]),
            start_sentence_id=str(row["start_sentence_id"]),
            end_sentence_id=str(row["end_sentence_id"]),
            source_chapter_ids=[int(item) for item in row.get("source_chapter_ids", row.get("chapter_ids", []))],
            chapter_titles=[str(item) for item in row.get("chapter_titles", [])],
            target_note_count=int(row["target_note_count"]),
            covered_note_count=int(row["covered_note_count"]),
            termination_reason=str(row["termination_reason"]),
            segment_source_path=str(row["segment_source_path"]),
        )
        for row in rows
    ]


def _window_by_segment_id(dataset_dir: Path, segment_id: str) -> ReadingWindow | None:
    try:
        return next((window for window in _load_windows(dataset_dir) if window.segment_id == segment_id), None)
    except Exception:
        return None


def _normalized_text_hash(text: str) -> str:
    normalized = " ".join(str(text or "").split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _window_source_hash(dataset_dir: Path, window: ReadingWindow) -> str:
    path = dataset_dir / window.segment_source_path
    if not path.exists():
        return ""
    return _normalized_text_hash(path.read_text(encoding="utf-8"))


def _window_fingerprint(dataset_dir: Path, window: ReadingWindow) -> dict[str, Any]:
    return {
        "segment_id": window.segment_id,
        "source_id": window.source_id,
        "start_sentence_id": window.start_sentence_id,
        "end_sentence_id": window.end_sentence_id,
        "source_chapter_ids": list(window.source_chapter_ids),
        "source_text_sha256": _window_source_hash(dataset_dir, window),
    }


def _candidate_reuse_output_dirs(
    *,
    reuse_run_root: Path,
    window: ReadingWindow,
    mechanism_key: str,
) -> list[Path]:
    candidates = [
        reuse_run_root / "shards" / f"{window.source_id}__{mechanism_key}" / "outputs" / window.segment_id / mechanism_key,
        reuse_run_root / "outputs" / window.segment_id / mechanism_key,
    ]
    candidates.extend(sorted(reuse_run_root.glob(f"shards/*__{mechanism_key}/outputs/{window.segment_id}/{mechanism_key}")))

    seen: set[str] = set()
    unique: list[Path] = []
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _reuse_selection_path(*, reuse_run_root: Path, window: ReadingWindow, mechanism_key: str) -> Path:
    return reuse_run_root / "shards" / f"{window.source_id}__{mechanism_key}" / "meta" / "selection.json"


def _validate_reuse_window_match(
    *,
    current_dataset_dir: Path,
    current_window: ReadingWindow,
    reuse_run_root: Path,
    mechanism_key: str,
) -> tuple[bool, dict[str, Any]]:
    selection_path = _reuse_selection_path(
        reuse_run_root=reuse_run_root,
        window=current_window,
        mechanism_key=mechanism_key,
    )
    report: dict[str, Any] = {
        "reuse_run_root": str(reuse_run_root),
        "selection_path": str(selection_path),
        "reason": "",
        "current_fingerprint": _window_fingerprint(current_dataset_dir, current_window),
        "reuse_fingerprint": None,
    }
    if not selection_path.exists():
        report["reason"] = "missing_selection"
        return False, report

    try:
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
    except Exception:
        report["reason"] = "invalid_selection"
        return False, report

    if current_window.segment_id not in {str(item) for item in selection.get("segment_ids") or []}:
        report["reason"] = "selection_segment_mismatch"
        return False, report
    if mechanism_key not in {str(item) for item in selection.get("mechanism_keys") or []}:
        report["reason"] = "selection_mechanism_mismatch"
        return False, report

    reuse_dataset_dir = _resolve_path(selection.get("dataset_dir", ""))
    reuse_window = _window_by_segment_id(reuse_dataset_dir, current_window.segment_id)
    if reuse_window is None:
        report["reason"] = "missing_reuse_segment"
        report["reuse_dataset_dir"] = str(reuse_dataset_dir)
        return False, report

    reuse_fingerprint = _window_fingerprint(reuse_dataset_dir, reuse_window)
    report["reuse_dataset_dir"] = str(reuse_dataset_dir)
    report["reuse_fingerprint"] = reuse_fingerprint

    for key in ("segment_id", "start_sentence_id", "end_sentence_id", "source_chapter_ids", "source_text_sha256"):
        if report["current_fingerprint"].get(key) != reuse_fingerprint.get(key):
            report["reason"] = f"{key}_mismatch"
            return False, report

    report["reason"] = "matched"
    return True, report


def find_reaction_reuse_output(
    *,
    current_dataset_dir: Path,
    window: ReadingWindow,
    mechanism_key: str,
    reuse_run_root: Path | None,
) -> dict[str, Any] | None:
    if mechanism_key != "iterator_v1" or reuse_run_root is None:
        return None
    reuse_run_root = reuse_run_root.resolve()
    if not reuse_run_root.exists():
        return None

    matched, validation = _validate_reuse_window_match(
        current_dataset_dir=current_dataset_dir,
        current_window=window,
        reuse_run_root=reuse_run_root,
        mechanism_key=mechanism_key,
    )
    if not matched:
        return {
            "status": "rejected",
            "mechanism_key": mechanism_key,
            "segment_id": window.segment_id,
            "validation": validation,
        }

    for output_dir in _candidate_reuse_output_dirs(
        reuse_run_root=reuse_run_root,
        window=window,
        mechanism_key=mechanism_key,
    ):
        if run_state_status(output_dir) != "completed":
            continue
        try:
            payload = _completed_output_payload(
                mechanism_key=mechanism_key,
                output_dir=output_dir,
                segment_id=window.segment_id,
            )
        except Exception as exc:
            validation = dict(validation)
            validation["reason"] = "completed_output_rebuild_failed"
            validation["error"] = str(exc)
            return {
                "status": "rejected",
                "mechanism_key": mechanism_key,
                "segment_id": window.segment_id,
                "validation": validation,
            }
        payload["run_mode"] = "reuse_reaction_output"
        payload["reuse_source_run_root"] = str(reuse_run_root)
        payload["reuse_validation"] = validation
        return payload

    validation = dict(validation)
    validation["reason"] = "missing_completed_output"
    return {
        "status": "rejected",
        "mechanism_key": mechanism_key,
        "segment_id": window.segment_id,
        "validation": validation,
    }


def _mechanism_for_key(mechanism_key: str):
    if mechanism_key == "attentional_v2":
        return AttentionalV2Mechanism()
    if mechanism_key == "iterator_v1":
        return IteratorV1Mechanism()
    raise ValueError(f"unsupported mechanism: {mechanism_key}")


@contextmanager
def _isolated_output_dir(output_dir: Path):
    with override_output_dir(output_dir):
        yield


def _bundle_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    reactions = [item for item in bundle.get("reactions") or [] if isinstance(item, dict)]
    return {
        "reaction_count": len(reactions),
        "memory_summary_count": len([item for item in bundle.get("memory_summaries") or [] if str(item).strip()]),
    }


def _v2_probe_config(window: ReadingWindow) -> dict[str, object]:
    return {
        "enabled": True,
        "segment_id": window.segment_id,
        "source_id": window.source_id,
        "book_title": window.book_title,
        "language_track": window.language_track,
    }


def _completed_output_payload(
    *,
    mechanism_key: str,
    output_dir: Path,
    segment_id: str,
) -> dict[str, Any]:
    rebuilt = rebuild_normalized_bundle_from_completed_output(
        mechanism_key=mechanism_key,
        source_output_dir=output_dir,
        segment_id=segment_id,
    )
    bundle = dict(rebuilt.get("normalized_eval_bundle") or {})
    return {
        "status": "completed",
        "mechanism_key": mechanism_key,
        "mechanism_label": str(rebuilt.get("mechanism_label") or mechanism_key),
        "output_dir": str(output_dir),
        "normalized_eval_bundle": bundle,
        "bundle_summary": _bundle_summary(bundle),
    }


def ensure_window_output(
    *,
    window: ReadingWindow,
    dataset_dir: Path,
    mechanism_key: str,
    run_root: Path,
    require_probe_export: bool,
) -> dict[str, Any]:
    output_dir = _output_dir_for(run_root, window.segment_id, mechanism_key)
    status = run_state_status(output_dir) if output_dir.exists() else ""

    if status == "completed":
        if mechanism_key != "attentional_v2" or not require_probe_export or is_memory_quality_probe_export_complete(output_dir):
            payload = _completed_output_payload(
                mechanism_key=mechanism_key,
                output_dir=output_dir,
                segment_id=window.segment_id,
            )
            payload["run_mode"] = "reuse_completed"
            return payload
        shutil.rmtree(output_dir, ignore_errors=True)
        status = ""

    continue_mode = False
    if output_dir.exists() and status and status != "completed":
        if mechanism_key == "attentional_v2" and require_probe_export:
            continue_mode = memory_quality_probe_export_file(output_dir).exists()
            if not continue_mode:
                shutil.rmtree(output_dir, ignore_errors=True)
        else:
            continue_mode = True
    elif output_dir.exists() and status != "completed":
        shutil.rmtree(output_dir, ignore_errors=True)

    mechanism = _mechanism_for_key(mechanism_key)
    segment_path = dataset_dir / window.segment_source_path
    mechanism_config: dict[str, object] = {"persist_normalized_eval_bundle": True}
    if mechanism_key == "attentional_v2" and require_probe_export:
        mechanism_config["memory_quality_probe_export"] = _v2_probe_config(window)

    with _isolated_output_dir(output_dir):
        mechanism.read_book(
            ReadRequest(
                book_path=segment_path,
                chapter_number=1,
                continue_mode=continue_mode,
                user_intent=DEFAULT_USER_INTENT,
                language_mode=window.language_track,
                task_mode="sequential",
                mechanism_key=mechanism_key,
                mechanism_config=mechanism_config,
            )
        )

    payload = _completed_output_payload(
        mechanism_key=mechanism_key,
        output_dir=output_dir,
        segment_id=window.segment_id,
    )
    payload["run_mode"] = "resume" if continue_mode else "fresh"
    return payload


def ensure_window_output_with_retries(
    *,
    window: ReadingWindow,
    dataset_dir: Path,
    mechanism_key: str,
    run_root: Path,
    require_probe_export: bool,
    max_attempts: int,
    retry_sleep_seconds: int,
) -> dict[str, Any]:
    output_dir = _output_dir_for(run_root, window.segment_id, mechanism_key)
    attempts = max(1, int(max_attempts or 1))
    sleep_seconds = max(0, int(retry_sleep_seconds or 0))
    last_error: BaseException | None = None

    for attempt in range(1, attempts + 1):
        try:
            payload = ensure_window_output(
                window=window,
                dataset_dir=dataset_dir,
                mechanism_key=mechanism_key,
                run_root=run_root,
                require_probe_export=require_probe_export,
            )
            payload["output_attempt"] = attempt
            return payload
        except Exception as exc:
            last_error = exc
            retryable = _is_retryable_output_error(exc, output_dir=output_dir)
            if attempt >= attempts or not retryable:
                raise
            if sleep_seconds:
                print(
                    json.dumps(
                        {
                            "event": "output_retry_wait",
                            "segment_id": window.segment_id,
                            "mechanism_key": mechanism_key,
                            "attempt": attempt,
                            "next_attempt": attempt + 1,
                            "sleep_seconds": sleep_seconds,
                            "error": str(exc),
                            "runtime_error": _runtime_error_text(output_dir),
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )
                time.sleep(sleep_seconds)

    assert last_error is not None
    raise last_error


def _paragraph_lookup(chapter: dict[str, Any]) -> dict[int, str]:
    lookup: dict[int, str] = {}
    for paragraph in chapter.get("paragraphs", []):
        if not isinstance(paragraph, dict):
            continue
        paragraph_index = int(paragraph.get("paragraph_index", 0) or 0)
        if paragraph_index <= 0:
            continue
        lookup[paragraph_index] = _clean_text(paragraph.get("text"))
    return lookup


def build_read_so_far_source_text(book_document: dict[str, Any], capture_sentence_id: str) -> str:
    capture_sentence_id = _clean_text(capture_sentence_id)
    if not capture_sentence_id:
        return ""

    paragraphs: list[str] = []
    for raw_chapter in book_document.get("chapters", []):
        if not isinstance(raw_chapter, dict):
            continue
        chapter = dict(raw_chapter)
        paragraph_lookup = _paragraph_lookup(chapter)
        capture_sentence: dict[str, Any] | None = next(
            (
                dict(sentence)
                for sentence in chapter.get("sentences", [])
                if isinstance(sentence, dict) and _clean_text(sentence.get("sentence_id")) == capture_sentence_id
            ),
            None,
        )
        capture_paragraph_index = int(capture_sentence.get("paragraph_index", 0) or 0) if capture_sentence else 0
        capture_char_end = 0
        if capture_sentence and isinstance(capture_sentence.get("locator"), dict):
            capture_char_end = int(capture_sentence["locator"].get("char_end", 0) or 0)

        for paragraph in chapter.get("paragraphs", []):
            if not isinstance(paragraph, dict):
                continue
            paragraph_index = int(paragraph.get("paragraph_index", 0) or 0)
            paragraph_text = paragraph_lookup.get(paragraph_index) or _clean_text(paragraph.get("text"))
            if not paragraph_text:
                continue
            if capture_sentence and paragraph_index == capture_paragraph_index:
                if capture_char_end > 0:
                    paragraphs.append(paragraph_text[:capture_char_end].rstrip())
                else:
                    sentences_in_paragraph = [
                        _clean_text(sentence.get("text"))
                        for sentence in chapter.get("sentences", [])
                        if isinstance(sentence, dict) and int(sentence.get("paragraph_index", 0) or 0) == paragraph_index
                    ]
                    cut_index = next(
                        (
                            index
                            for index, sentence in enumerate(chapter.get("sentences", []))
                            if isinstance(sentence, dict) and _clean_text(sentence.get("sentence_id")) == capture_sentence_id
                        ),
                        -1,
                    )
                    captured_parts = []
                    for sentence in chapter.get("sentences", []):
                        if not isinstance(sentence, dict):
                            continue
                        if int(sentence.get("paragraph_index", 0) or 0) != paragraph_index:
                            continue
                        captured_parts.append(_clean_text(sentence.get("text")))
                        if _clean_text(sentence.get("sentence_id")) == capture_sentence_id:
                            break
                    paragraphs.append(" ".join(part for part in captured_parts if part).strip() or paragraph_text)
                return "\n\n".join(part for part in paragraphs if part)
            paragraphs.append(paragraph_text)
        if capture_sentence:
            break
    return "\n\n".join(part for part in paragraphs if part)


def _default_memory_quality_judgment(*, reason: str) -> dict[str, Any]:
    return {
        "salience_score": 1,
        "mainline_fidelity_score": 1,
        "organization_score": 1,
        "fidelity_score": 1,
        "overall_memory_quality_score": 1,
        "reason": reason,
    }


def _normalize_memory_quality_judgment(payload: object) -> dict[str, Any]:
    raw = payload if isinstance(payload, dict) else {}

    def _score(key: str) -> int:
        try:
            value = int(raw.get(key, 1) or 1)
        except (TypeError, ValueError):
            value = 1
        return max(1, min(5, value))

    return {
        "salience_score": _score("salience_score"),
        "mainline_fidelity_score": _score("mainline_fidelity_score"),
        "organization_score": _score("organization_score"),
        "fidelity_score": _score("fidelity_score"),
        "overall_memory_quality_score": _score("overall_memory_quality_score"),
        "reason": _clean_text(raw.get("reason")) or "judge_unavailable",
    }


def judge_memory_quality_probe(
    *,
    run_root: Path,
    window: ReadingWindow,
    probe_payload: dict[str, Any],
    judge_mode: str,
) -> dict[str, Any]:
    if judge_mode == "none":
        return _default_memory_quality_judgment(reason="judge_skipped")

    system_prompt = """You are judging long-span memory quality for a continuous-reading agent.

Focus on what the memory snapshot actually retains at this probe point.
The source slice shows what has already been read; it is context, not substitute memory.
Do not reward the snapshot for information that exists only in the source slice.

Judge holistically on:
- salience: whether retained items are important and worth remembering
- mainline fidelity: whether the retained picture stays close to the book's main line so far
- organization: whether memory is organized into usable concepts/threads instead of scattered fragments
- fidelity: whether retained items are accurate rather than drifted, distorted, or over-abstracted
- overall memory quality

Return JSON only."""
    base_user_prompt = (
        f"Reading window metadata:\n{json.dumps(asdict(window), ensure_ascii=False, indent=2)}\n\n"
        f"Probe payload:\n{json.dumps(probe_payload, ensure_ascii=False, indent=2)}\n\n"
        'Return JSON: {"salience_score":1,"mainline_fidelity_score":1,"organization_score":1,"fidelity_score":1,"overall_memory_quality_score":1,"reason":"2-5 sentences citing concrete retained items and any important omissions/drift."}'
    )
    payload: object = {}
    for user_prompt in (base_user_prompt, base_user_prompt + JUDGE_SCHEMA_RETRY_INSTRUCTION):
        try:
            with llm_invocation_scope(
                profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
                trace_context=eval_trace_context(
                    run_root,
                    eval_target=DEFAULT_TARGET,
                    stage="memory_quality",
                    node="memory_quality_probe",
                    extra={
                        "segment_id": window.segment_id,
                        "probe_index": int(probe_payload.get("probe_index", 0) or 0),
                    },
                ),
            ):
                payload = invoke_json(system_prompt, user_prompt, _default_memory_quality_judgment(reason="judge_unavailable"))
        except ReaderLLMError:
            payload = {}
        except Exception:
            payload = {}
        normalized = _normalize_memory_quality_judgment(payload)
        if normalized["reason"] != "judge_unavailable":
            return normalized
    return _normalize_memory_quality_judgment(payload)


def _reaction_auxiliary_metadata(*, mechanism_key: str, output_dir: Path) -> dict[str, dict[str, Any]]:
    if mechanism_key != "attentional_v2":
        return {}
    path = reaction_records_file(output_dir)
    if not path.exists():
        return {}
    payload = load_attentional_v2_json(path)
    records = payload.get("records", []) if isinstance(payload, dict) else []
    metadata: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        reaction_id = _clean_text(record.get("reaction_id"))
        if not reaction_id:
            continue
        metadata[reaction_id] = {
            "compat_family": _clean_text(record.get("compat_family") or record.get("type")),
            "prior_link": dict(record.get("prior_link", {})) if isinstance(record.get("prior_link"), dict) else None,
            "outside_link": dict(record.get("outside_link", {})) if isinstance(record.get("outside_link"), dict) else None,
            "search_intent": dict(record.get("search_intent", {})) if isinstance(record.get("search_intent"), dict) else None,
        }
    return metadata


def _reaction_audit_items(
    *,
    mechanism_key: str,
    output_dir: Path,
    normalized_bundle: dict[str, Any],
) -> list[dict[str, Any]]:
    auxiliary = _reaction_auxiliary_metadata(mechanism_key=mechanism_key, output_dir=output_dir)
    items: list[dict[str, Any]] = []
    for index, reaction in enumerate(normalized_bundle.get("reactions") or [], start=1):
        if not isinstance(reaction, dict):
            continue
        reaction_id = _clean_text(reaction.get("reaction_id"))
        if not reaction_id:
            continue
        items.append(
            {
                "reaction_index": index,
                "reaction_id": reaction_id,
                "section_ref": _clean_text(reaction.get("section_ref")),
                "compat_type": _clean_text(reaction.get("type")),
                "anchor_quote": _clean_text(reaction.get("anchor_quote")),
                "content": _clean_text(reaction.get("content")),
                "auxiliary": auxiliary.get(reaction_id, {}),
            }
        )
    return items


def _default_reaction_label(reaction_id: str, *, reason: str) -> dict[str, Any]:
    return {"reaction_id": reaction_id, "label": "local_only", "reason": reason}


def _normalize_reaction_labels(
    payload: object,
    *,
    audit_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    raw_results = payload.get("results", []) if isinstance(payload, dict) else []
    by_id: dict[str, dict[str, Any]] = {}
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        reaction_id = _clean_text(item.get("reaction_id"))
        label = _clean_text(item.get("label"))
        if reaction_id and label in REACTION_LABELS:
            by_id[reaction_id] = {
                "reaction_id": reaction_id,
                "label": label,
                "reason": _clean_text(item.get("reason")) or "judge_unavailable",
            }
    results: list[dict[str, Any]] = []
    for item in audit_items:
        reaction_id = str(item["reaction_id"])
        results.append(by_id.get(reaction_id, _default_reaction_label(reaction_id, reason="judge_unavailable")))
    return results


def audit_window_reactions(
    *,
    run_root: Path,
    window: ReadingWindow,
    mechanism_key: str,
    output_dir: Path,
    normalized_bundle: dict[str, Any],
    judge_mode: str,
) -> list[dict[str, Any]]:
    audit_items = _reaction_audit_items(
        mechanism_key=mechanism_key,
        output_dir=output_dir,
        normalized_bundle=normalized_bundle,
    )
    if not audit_items:
        return []
    if judge_mode == "none":
        return [_default_reaction_label(str(item["reaction_id"]), reason="judge_skipped") for item in audit_items]

    system_prompt = """You are auditing visible reactions from one completed reading window.

Classify each reaction using the ordered visible reactions from this same window as the primary evidence surface.
Later reactions may callback to earlier visible material in the same list.
Auxiliary metadata is only support; do not overrule the visible reaction text with metadata alone.

Labels:
- local_only: no meaningful earlier-material linkage attempt
- grounded_callback: clearly and correctly links back to earlier visible material
- weak_callback: callback-like but vague, partial, or under-supported
- false_visible_integration: overclaimed, misremembered, theme-only, or hard-linked without real grounding

Return JSON only."""
    base_user_prompt = (
        f"Reading window metadata:\n{json.dumps(asdict(window), ensure_ascii=False, indent=2)}\n\n"
        f"Mechanism key: {mechanism_key}\n\n"
        f"Ordered visible reactions:\n{json.dumps(audit_items, ensure_ascii=False, indent=2)}\n\n"
        'Return JSON: {"results":[{"reaction_id":"...","label":"local_only|grounded_callback|weak_callback|false_visible_integration","reason":"1-2 sentences."}]}'
    )
    payload: object = {}
    for user_prompt in (base_user_prompt, base_user_prompt + JUDGE_SCHEMA_RETRY_INSTRUCTION):
        try:
            with llm_invocation_scope(
                profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
                trace_context=eval_trace_context(
                    run_root,
                    eval_target=DEFAULT_TARGET,
                    stage="reaction_audit",
                    node="reaction_audit_batch",
                    extra={"segment_id": window.segment_id, "mechanism_key": mechanism_key},
                ),
            ):
                payload = invoke_json(
                    system_prompt,
                    user_prompt,
                    {"results": [_default_reaction_label(str(item["reaction_id"]), reason="judge_unavailable") for item in audit_items]},
                )
        except ReaderLLMError:
            payload = {}
        except Exception:
            payload = {}
        normalized = _normalize_reaction_labels(payload, audit_items=audit_items)
        if all(_clean_text(item.get("reason")) != "judge_unavailable" for item in normalized):
            return normalized
    return _normalize_reaction_labels(payload, audit_items=audit_items)


def _reaction_summary_rows(
    *,
    window: ReadingWindow,
    mechanism_key: str,
    mechanism_label: str,
    normalized_bundle: dict[str, Any],
    labels: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reactions = [dict(item) for item in normalized_bundle.get("reactions") or [] if isinstance(item, dict)]
    label_by_id = {str(item["reaction_id"]): item for item in labels}
    rows: list[dict[str, Any]] = []
    counts = Counter()
    for reaction in reactions:
        reaction_id = _clean_text(reaction.get("reaction_id"))
        label_payload = label_by_id.get(reaction_id, _default_reaction_label(reaction_id, reason="missing_label"))
        label = str(label_payload["label"])
        counts[label] += 1
        rows.append(
            {
                "segment_id": window.segment_id,
                "source_id": window.source_id,
                "book_title": window.book_title,
                "mechanism_key": mechanism_key,
                "mechanism_label": mechanism_label,
                "reaction_id": reaction_id,
                "reaction_index": len(rows) + 1,
                "label": label,
                "reason": _clean_text(label_payload.get("reason")),
                "section_ref": _clean_text(reaction.get("section_ref")),
                "anchor_quote": _clean_text(reaction.get("anchor_quote")),
                "content": _clean_text(reaction.get("content")),
                "compat_type": _clean_text(reaction.get("type")),
            }
        )

    total_visible_reactions = len(rows)
    callback_attempt_count = counts["grounded_callback"] + counts["weak_callback"] + counts["false_visible_integration"]
    summary = {
        "segment_id": window.segment_id,
        "source_id": window.source_id,
        "book_title": window.book_title,
        "mechanism_key": mechanism_key,
        "mechanism_label": mechanism_label,
        "total_visible_reactions": total_visible_reactions,
        "callback_attempt_count": callback_attempt_count,
        "grounded_callback_count": counts["grounded_callback"],
        "weak_callback_count": counts["weak_callback"],
        "false_visible_integration_count": counts["false_visible_integration"],
        "local_only_count": counts["local_only"],
        "callback_attempt_rate": callback_attempt_count / total_visible_reactions if total_visible_reactions else 0.0,
        "grounded_callback_rate": counts["grounded_callback"] / total_visible_reactions if total_visible_reactions else 0.0,
        "false_visible_integration_rate": counts["false_visible_integration"] / total_visible_reactions if total_visible_reactions else 0.0,
        "false_rate_among_callback_attempts": counts["false_visible_integration"] / callback_attempt_count if callback_attempt_count else 0.0,
        "representative_grounded_callbacks": [
            {
                "reaction_id": row["reaction_id"],
                "anchor_quote": row["anchor_quote"],
                "content": row["content"],
                "reason": row["reason"],
            }
            for row in rows
            if row["label"] == "grounded_callback"
        ][:3],
        "representative_false_visible_integrations": [
            {
                "reaction_id": row["reaction_id"],
                "anchor_quote": row["anchor_quote"],
                "content": row["content"],
                "reason": row["reason"],
            }
            for row in rows
            if row["label"] == "false_visible_integration"
        ][:3],
    }
    return rows, summary


def _aggregate_memory_quality(probe_results: list[dict[str, Any]]) -> dict[str, Any]:
    windows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in probe_results:
        windows[str(row["segment_id"])].append(row)

    window_summaries: list[dict[str, Any]] = []
    for segment_id, rows in windows.items():
        window_summaries.append(
            {
                "segment_id": segment_id,
                "source_id": rows[0]["source_id"],
                "book_title": rows[0]["book_title"],
                "probe_count": len(rows),
                "average_salience_score": mean(float(row["salience_score"]) for row in rows),
                "average_mainline_fidelity_score": mean(float(row["mainline_fidelity_score"]) for row in rows),
                "average_organization_score": mean(float(row["organization_score"]) for row in rows),
                "average_fidelity_score": mean(float(row["fidelity_score"]) for row in rows),
                "average_overall_memory_quality_score": mean(float(row["overall_memory_quality_score"]) for row in rows),
            }
        )
    ordered_windows = sorted(window_summaries, key=lambda item: item["segment_id"])
    return {
        "mechanism_key": "attentional_v2",
        "probe_count": len(probe_results),
        "window_count": len(ordered_windows),
        "average_overall_memory_quality_score": mean(
            float(item["average_overall_memory_quality_score"]) for item in ordered_windows
        )
        if ordered_windows
        else 0.0,
        "windows": ordered_windows,
    }


def _aggregate_reaction_audit(window_summaries: list[dict[str, Any]]) -> dict[str, Any]:
    by_mechanism: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for summary in window_summaries:
        by_mechanism[str(summary["mechanism_key"])].append(summary)
    mechanisms: dict[str, Any] = {}
    for mechanism_key, rows in by_mechanism.items():
        total_visible_reactions = sum(int(row["total_visible_reactions"]) for row in rows)
        callback_attempt_count = sum(int(row["callback_attempt_count"]) for row in rows)
        grounded_callback_count = sum(int(row["grounded_callback_count"]) for row in rows)
        weak_callback_count = sum(int(row["weak_callback_count"]) for row in rows)
        false_visible_integration_count = sum(int(row["false_visible_integration_count"]) for row in rows)
        local_only_count = sum(int(row["local_only_count"]) for row in rows)
        mechanisms[mechanism_key] = {
            "mechanism_key": mechanism_key,
            "mechanism_label": rows[0]["mechanism_label"],
            "window_count": len(rows),
            "total_visible_reactions": total_visible_reactions,
            "callback_attempt_count": callback_attempt_count,
            "grounded_callback_count": grounded_callback_count,
            "weak_callback_count": weak_callback_count,
            "false_visible_integration_count": false_visible_integration_count,
            "local_only_count": local_only_count,
            "callback_attempt_rate": callback_attempt_count / total_visible_reactions if total_visible_reactions else 0.0,
            "grounded_callback_rate": grounded_callback_count / total_visible_reactions if total_visible_reactions else 0.0,
            "false_visible_integration_rate": false_visible_integration_count / total_visible_reactions if total_visible_reactions else 0.0,
            "false_rate_among_callback_attempts": false_visible_integration_count / callback_attempt_count if callback_attempt_count else 0.0,
        }
    return {
        "mechanisms": mechanisms,
        "windows": sorted(window_summaries, key=lambda item: (item["segment_id"], item["mechanism_key"])),
    }


def _render_report(
    *,
    aggregate: dict[str, Any],
    memory_quality_results: list[dict[str, Any]],
    reaction_window_summaries: list[dict[str, Any]],
) -> str:
    memory_quality = dict(aggregate.get("memory_quality") or {})
    reaction_audit = dict(aggregate.get("reaction_audit") or {})
    lines = [
        "# Long Span vNext Phase 1",
        "",
        "## Memory Quality (V2 only)",
        "",
        f"- Overall average memory quality score: `{memory_quality.get('average_overall_memory_quality_score', 0.0):.3f}`",
        f"- Probe count: `{memory_quality.get('probe_count', 0)}`",
        f"- Window count: `{memory_quality.get('window_count', 0)}`",
        "",
    ]
    for window_summary in memory_quality.get("windows", []):
        lines.extend(
            [
                f"### {window_summary['book_title']} (`{window_summary['segment_id']}`)",
                f"- Average overall memory quality: `{window_summary['average_overall_memory_quality_score']:.3f}`",
                f"- Probe count: `{window_summary['probe_count']}`",
                "",
            ]
        )
        probe_rows = [row for row in memory_quality_results if row["segment_id"] == window_summary["segment_id"]]
        for row in probe_rows:
            lines.append(
                f"- Probe `{row['probe_index']}` (`{row['threshold_ratio']:.1%}`): overall `{row['overall_memory_quality_score']}`. {row['reason']}"
            )
        lines.append("")

    lines.extend(["## Reaction Audit", ""])
    for mechanism_key in MECHANISM_KEYS:
        mechanism_summary = dict((reaction_audit.get("mechanisms") or {}).get(mechanism_key) or {})
        if not mechanism_summary:
            continue
        lines.extend(
            [
                f"### {mechanism_summary['mechanism_label']} (`{mechanism_key}`)",
                f"- Total visible reactions: `{mechanism_summary['total_visible_reactions']}`",
                f"- Callback attempts: `{mechanism_summary['callback_attempt_count']}` (`{mechanism_summary['callback_attempt_rate']:.3f}`)",
                f"- Grounded callbacks: `{mechanism_summary['grounded_callback_count']}` (`{mechanism_summary['grounded_callback_rate']:.3f}`)",
                f"- Weak callbacks: `{mechanism_summary['weak_callback_count']}`",
                f"- False visible integrations: `{mechanism_summary['false_visible_integration_count']}` (`{mechanism_summary['false_visible_integration_rate']:.3f}`)",
                "",
            ]
        )

    lines.extend(["## Per-window Reaction Audit", ""])
    for summary in reaction_window_summaries:
        lines.extend(
            [
                f"### {summary['book_title']} / {summary['mechanism_key']}",
                f"- Total visible reactions: `{summary['total_visible_reactions']}`",
                f"- Grounded callbacks: `{summary['grounded_callback_count']}`",
                f"- False visible integrations: `{summary['false_visible_integration_count']}`",
            ]
        )
        if summary["representative_grounded_callbacks"]:
            lines.append("- Representative grounded callbacks:")
            for example in summary["representative_grounded_callbacks"]:
                lines.append(
                    f"  - `{example['reaction_id']}`: “{example['anchor_quote']}” -> {example['content']} ({example['reason']})"
                )
        if summary["representative_false_visible_integrations"]:
            lines.append("- Representative false visible integrations:")
            for example in summary["representative_false_visible_integrations"]:
                lines.append(
                    f"  - `{example['reaction_id']}`: “{example['anchor_quote']}” -> {example['content']} ({example['reason']})"
                )
        if not summary["representative_grounded_callbacks"] and not summary["representative_false_visible_integrations"]:
            lines.append("- This window stayed mostly local.")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def run_long_span_vnext(
    *,
    run_root: Path,
    manifest_path: Path = MANIFEST_PATH,
    judge_mode: str = "llm",
    segment_ids: set[str] | None = None,
    window_limit: int | None = None,
    workers: int = 1,
    output_attempts: int = DEFAULT_OUTPUT_ATTEMPTS,
    output_retry_sleep_seconds: int = DEFAULT_OUTPUT_RETRY_SLEEP_SECONDS,
    reaction_reuse_run_root: Path | None = DEFAULT_REACTION_REUSE_RUN_ROOT,
) -> dict[str, Any]:
    worker_count = max(1, int(workers or 1))
    dataset_dir = _resolve_dataset_dir(manifest_path)
    windows = _load_windows(dataset_dir)
    if segment_ids:
        windows = [window for window in windows if window.segment_id in segment_ids]
    if window_limit is not None:
        windows = windows[:window_limit]

    reaction_reuse_run_root = reaction_reuse_run_root.resolve() if reaction_reuse_run_root else None

    (run_root / "meta").mkdir(parents=True, exist_ok=True)
    _json_dump(
        run_root / "meta" / "selected_windows.json",
        {
            "generated_at": _timestamp(),
            "dataset_dir": str(dataset_dir),
            "manifest_path": str(manifest_path),
            "reaction_reuse_run_root": str(reaction_reuse_run_root) if reaction_reuse_run_root else "",
            "windows": [asdict(window) for window in windows],
            "window_fingerprints": [_window_fingerprint(dataset_dir, window) for window in windows],
        },
    )

    output_payloads: dict[tuple[str, str], dict[str, Any]] = {}
    reuse_decisions: list[dict[str, Any]] = []
    output_tasks: list[tuple[ReadingWindow, str]] = []
    for window in windows:
        output_tasks.append((window, "attentional_v2"))
        reuse_payload = find_reaction_reuse_output(
            current_dataset_dir=dataset_dir,
            window=window,
            mechanism_key="iterator_v1",
            reuse_run_root=reaction_reuse_run_root,
        )
        if reuse_payload and reuse_payload.get("status") == "completed":
            output_payloads[(window.segment_id, "iterator_v1")] = reuse_payload
            reuse_decisions.append(
                {
                    "segment_id": window.segment_id,
                    "mechanism_key": "iterator_v1",
                    "decision": "reused",
                    "output_dir": reuse_payload.get("output_dir"),
                    "validation": reuse_payload.get("reuse_validation"),
                }
            )
        else:
            output_tasks.append((window, "iterator_v1"))
            reuse_decisions.append(
                {
                    "segment_id": window.segment_id,
                    "mechanism_key": "iterator_v1",
                    "decision": "fresh_required",
                    "validation": (reuse_payload or {}).get("validation") if isinstance(reuse_payload, dict) else None,
                }
            )

    def _ensure_output(task: tuple[ReadingWindow, str]) -> tuple[tuple[str, str], dict[str, Any]]:
        window, mechanism_key = task
        payload = ensure_window_output_with_retries(
            window=window,
            dataset_dir=dataset_dir,
            mechanism_key=mechanism_key,
            run_root=run_root,
            require_probe_export=mechanism_key == "attentional_v2",
            max_attempts=output_attempts,
            retry_sleep_seconds=output_retry_sleep_seconds,
        )
        return (window.segment_id, mechanism_key), payload

    output_payloads.update(dict(_run_in_parallel(output_tasks, worker_count, _ensure_output)))
    _json_dump(
        run_root / "meta" / "output_sourcing.json",
        {
            "generated_at": _timestamp(),
            "reaction_reuse_run_root": str(reaction_reuse_run_root) if reaction_reuse_run_root else "",
            "fresh_task_count": len(output_tasks),
            "fresh_tasks": [
                {
                    "segment_id": window.segment_id,
                    "mechanism_key": mechanism_key,
                }
                for window, mechanism_key in output_tasks
            ],
            "reuse_decisions": reuse_decisions,
            "output_modes": {
                f"{segment_id}:{mechanism_key}": payload.get("run_mode")
                for (segment_id, mechanism_key), payload in sorted(output_payloads.items())
            },
        },
    )

    memory_quality_tasks: list[tuple[ReadingWindow, dict[str, Any], dict[str, Any]]] = []
    for window in windows:
        payload = output_payloads[(window.segment_id, "attentional_v2")]
        output_dir = Path(str(payload["output_dir"]))
        probe_export = load_memory_quality_probe_export(output_dir)
        book_document = json.loads(book_document_file(output_dir).read_text(encoding="utf-8"))
        for snapshot in probe_export.get("snapshots", []):
            if not isinstance(snapshot, dict):
                continue
            capture_sentence_id = _clean_text(snapshot.get("capture_sentence_id"))
            probe_payload = {
                "probe_index": int(snapshot.get("probe_index", 0) or 0),
                "threshold_ratio": float(snapshot.get("threshold_ratio", 0.0) or 0.0),
                "read_so_far_source_text": build_read_so_far_source_text(book_document, capture_sentence_id),
                "memory_snapshot": snapshot,
            }
            memory_quality_tasks.append((window, snapshot, probe_payload))

    def _judge_probe(task: tuple[ReadingWindow, dict[str, Any], dict[str, Any]]) -> dict[str, Any]:
        window, snapshot, probe_payload = task
        capture_sentence_id = _clean_text(snapshot.get("capture_sentence_id"))
        judgment = judge_memory_quality_probe(
            run_root=run_root,
            window=window,
            probe_payload=probe_payload,
            judge_mode=judge_mode,
        )
        return {
            "segment_id": window.segment_id,
            "source_id": window.source_id,
            "book_title": window.book_title,
            "mechanism_key": "attentional_v2",
            "probe_index": int(snapshot.get("probe_index", 0) or 0),
            "threshold_ratio": float(snapshot.get("threshold_ratio", 0.0) or 0.0),
            "capture_sentence_id": capture_sentence_id,
            **judgment,
        }

    memory_quality_results: list[dict[str, Any]] = _run_in_parallel(memory_quality_tasks, worker_count, _judge_probe)

    reaction_tasks = [
        (window, mechanism_key)
        for window in windows
        for mechanism_key in MECHANISM_KEYS
    ]

    def _audit_reactions(task: tuple[ReadingWindow, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        window, mechanism_key = task
        payload = output_payloads[(window.segment_id, mechanism_key)]
        output_dir = Path(str(payload["output_dir"]))
        normalized_bundle = dict(payload.get("normalized_eval_bundle") or {})
        labels = audit_window_reactions(
            run_root=run_root,
            window=window,
            mechanism_key=mechanism_key,
            output_dir=output_dir,
            normalized_bundle=normalized_bundle,
            judge_mode=judge_mode,
        )
        return _reaction_summary_rows(
            window=window,
            mechanism_key=mechanism_key,
            mechanism_label=str(payload.get("mechanism_label") or mechanism_key),
            normalized_bundle=normalized_bundle,
            labels=labels,
        )

    reaction_audit_results: list[dict[str, Any]] = []
    reaction_window_summaries: list[dict[str, Any]] = []
    for rows, window_summary in _run_in_parallel(reaction_tasks, worker_count, _audit_reactions):
        reaction_audit_results.extend(rows)
        reaction_window_summaries.append(window_summary)

    aggregate = {
        "run_id": run_root.name,
        "target": DEFAULT_TARGET,
        "generated_at": _timestamp(),
        "dataset_dir": str(dataset_dir),
        "metric_slugs": ["memory_quality", "spontaneous_callback", "false_visible_integration"],
        "memory_quality": _aggregate_memory_quality(memory_quality_results),
        "reaction_audit": _aggregate_reaction_audit(reaction_window_summaries),
        "output_modes": {
            f"{segment_id}:{mechanism_key}": payload.get("run_mode")
            for (segment_id, mechanism_key), payload in output_payloads.items()
        },
    }

    summary_dir = run_root / "summary"
    _jsonl_dump(summary_dir / "memory_quality_results.jsonl", memory_quality_results)
    _jsonl_dump(summary_dir / "reaction_audit_results.jsonl", reaction_audit_results)
    _jsonl_dump(summary_dir / "reaction_window_summaries.jsonl", reaction_window_summaries)
    _json_dump(summary_dir / "aggregate.json", aggregate)
    (summary_dir / "report.md").write_text(
        _render_report(
            aggregate=aggregate,
            memory_quality_results=memory_quality_results,
            reaction_window_summaries=reaction_window_summaries,
        ),
        encoding="utf-8",
    )
    write_llm_usage_summary(run_root)
    return aggregate


def _default_run_id() -> str:
    return f"attentional_v2_long_span_vnext_phase1_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default=_default_run_id())
    parser.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--judge-mode", choices=JUDGE_MODE_VALUES, default="llm")
    parser.add_argument("--segment-id", action="append", default=[])
    parser.add_argument("--window-limit", type=int, default=None)
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers for window reads and judge calls.")
    parser.add_argument("--output-attempts", type=int, default=DEFAULT_OUTPUT_ATTEMPTS)
    parser.add_argument("--output-retry-sleep-seconds", type=int, default=DEFAULT_OUTPUT_RETRY_SLEEP_SECONDS)
    parser.add_argument(
        "--reaction-reuse-run-root",
        default=str(DEFAULT_REACTION_REUSE_RUN_ROOT),
        help=(
            "Completed active excerpt run root used as the default source for iterator_v1 reaction-audit outputs. "
            "Pass an empty string to disable cross-run reuse."
        ),
    )
    args = parser.parse_args(argv)

    run_root = args.runs_root / args.run_id
    run_root.mkdir(parents=True, exist_ok=True)
    reaction_reuse_run_root = Path(args.reaction_reuse_run_root) if str(args.reaction_reuse_run_root).strip() else None
    aggregate = run_long_span_vnext(
        run_root=run_root,
        manifest_path=args.manifest_path,
        judge_mode=args.judge_mode,
        segment_ids={str(item) for item in args.segment_id if str(item).strip()} or None,
        window_limit=args.window_limit,
        workers=args.workers,
        output_attempts=args.output_attempts,
        output_retry_sleep_seconds=args.output_retry_sleep_seconds,
        reaction_reuse_run_root=reaction_reuse_run_root,
    )
    print(json.dumps(aggregate, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
