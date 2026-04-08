"""Run the bounded long-span cross-mechanism accumulation comparison."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from eval.common.taxonomy import DETERMINISTIC_METRICS, PAIRWISE_JUDGE, RUBRIC_JUDGE, normalize_methods, validate_target_slug
from eval.attentional_v2.llm_usage_summary import write_llm_usage_summary
from eval.attentional_v2.runtime_progress import runtime_progress_heartbeat
from eval.attentional_v2.run_excerpt_comparison import (
    _clean_text,
    _default_judgment,
    _load_source_index,
    _manifest_paths_from_entries,
    _match_entry,
    _normalize_compare_text,
    _normalize_judgment,
    _primary_match_method,
    _score_average,
)
from src.iterator_reader.llm_utils import ReaderLLMError, eval_trace_context, invoke_json, llm_invocation_scope
from src.reading_core import BookDocument
from src.reading_core.runtime_contracts import ReadRequest
from src.reading_mechanisms.attentional_v2 import AttentionalV2Mechanism
from src.reading_mechanisms.iterator_v1 import IteratorV1Mechanism
from src.reading_runtime.job_concurrency import resolve_worker_policy, submit_inherited_context
from src.reading_runtime.llm_registry import DEFAULT_EVAL_JUDGE_PROFILE_ID, DEFAULT_RUNTIME_PROFILE_ID
from src.reading_runtime.output_dir_overrides import override_output_dir
from src.reading_runtime.provisioning import ProvisionedBook, ensure_canonical_parse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_FORMAL_MANIFEST = ROOT / "eval" / "manifests" / "splits" / "attentional_v2_accumulation_benchmark_v1_draft.json"
DEFAULT_RUNS_ROOT = ROOT / "eval" / "runs" / "attentional_v2"
DEFAULT_TARGET = validate_target_slug("accumulation_comparison")
DEFAULT_METHODS = normalize_methods([DETERMINISTIC_METRICS, PAIRWISE_JUDGE, RUBRIC_JUDGE])
DEFAULT_COMPARISON_TARGET = "attentional_v2 vs iterator_v1 on bounded long-span continuity and long-span value probes"
DEFAULT_USER_INTENT = (
    "Read as a thoughtful co-reader and preserve meaningful continuity, carryover, tension, and clarification across the bounded reading window."
)
MECHANISM_KEYS = ("attentional_v2", "iterator_v1")
MECHANISM_FILTER_VALUES = ("attentional_v2", "iterator_v1", "both")
TARGET_SLICE_VALUES = ("coherent_accumulation", "insight_and_clarification", "both")
STAGE_VALUES = ("all", "bundle", "judge", "merge")
RECOVERABLE_MECHANISM_PROBLEM_CODES = {
    "network_blocked",
    "llm_timeout",
    "llm_quota",
    "search_timeout",
    "search_quota",
}
TARGET_FIELD_BY_SLICE = {
    "coherent_accumulation": ("accumulation_probes_frozen_draft", "accumulation_probe_core_draft"),
    "insight_and_clarification": (
        "insight_and_clarification_subset_frozen_draft",
        "insight_and_clarification_subset_draft",
    ),
}

ACCUMULATION_SCORE_KEYS = (
    "coherent_accumulation",
    "earlier_material_use",
    "arc_tracking",
    "memory_discipline",
    "product_fit",
)
INSIGHT_SCORE_KEYS = (
    "distinction_or_definition",
    "tension_tracking",
    "clarifying_value",
    "bridge_or_context_use",
    "strong_reading_plus_knowledge",
)

TARGET_CONFIGS: dict[str, dict[str, Any]] = {
    "coherent_accumulation": {
        "label": "reader_character.coherent_accumulation",
        "score_keys": ACCUMULATION_SCORE_KEYS,
        "system_prompt": """You are doing offline cross-mechanism reader evaluation.

Question family: `reader_character.coherent_accumulation`

Compare two mechanisms on the same bounded long-span probe. Focus on whether the reader carries meaningful earlier material forward through the window and uses it coherently later.

Judge the visible reading behavior by:
- coherent accumulation
- disciplined reuse of earlier material
- arc tracking across the bounded window
- memory carryover without drift
- product fit as a reading mind rather than generic summary

Return JSON only.""",
        "user_prompt": """Long-span probe:
{probe_json}

Attentional V2 long-span evidence:
{left_json}

Iterator V1 long-span evidence:
{right_json}

Return JSON:
{{
  "winner": "attentional_v2|iterator_v1|tie",
  "confidence": "high|medium|low",
  "scores": {{
    "attentional_v2": {{
      "coherent_accumulation": 1,
      "earlier_material_use": 1,
      "arc_tracking": 1,
      "memory_discipline": 1,
      "product_fit": 1
    }},
    "iterator_v1": {{
      "coherent_accumulation": 1,
      "earlier_material_use": 1,
      "arc_tracking": 1,
      "memory_discipline": 1,
      "product_fit": 1
    }}
  }},
  "reason": "3-6 sentences."
}}""",
    },
    "insight_and_clarification": {
        "label": "reader_value.insight_and_clarification",
        "score_keys": INSIGHT_SCORE_KEYS,
        "system_prompt": """You are doing offline cross-mechanism reader evaluation.

Question family: `reader_value.insight_and_clarification`

Compare two mechanisms on the same long-span probe. Focus on whether the reader turns the bounded long-span material into clarifying value rather than only preserving continuity.

Judge the visible reading behavior by:
- distinction or definition sharpening
- honest tension tracking
- clarifying value
- disciplined bridge or context use
- whether the result feels enabled by strong reading plus broad knowledge rather than generic paraphrase

Return JSON only.""",
        "user_prompt": """Long-span probe:
{probe_json}

Attentional V2 long-span evidence:
{left_json}

Iterator V1 long-span evidence:
{right_json}

Return JSON:
{{
  "winner": "attentional_v2|iterator_v1|tie",
  "confidence": "high|medium|low",
  "scores": {{
    "attentional_v2": {{
      "distinction_or_definition": 1,
      "tension_tracking": 1,
      "clarifying_value": 1,
      "bridge_or_context_use": 1,
      "strong_reading_plus_knowledge": 1
    }},
    "iterator_v1": {{
      "distinction_or_definition": 1,
      "tension_tracking": 1,
      "clarifying_value": 1,
      "bridge_or_context_use": 1,
      "strong_reading_plus_knowledge": 1
    }}
  }},
  "reason": "3-6 sentences."
}}""",
    },
}


@dataclass(frozen=True)
class WindowCase:
    window_case_id: str
    source_id: str
    book_title: str
    author: str
    output_language: str
    benchmark_line: str
    window_kind: str
    chapter_case_ids: list[str]
    chapter_ids: list[str]
    chapter_numbers: list[int]
    chapter_titles: list[str]
    sentence_count: int
    selection_group_id: str
    selection_group_label: str
    cross_chapter_window: dict[str, Any]


@dataclass(frozen=True)
class Probe:
    probe_id: str
    window_case_id: str
    source_id: str
    book_title: str
    author: str
    output_language: str
    probe_type: str
    anchor_refs: list[dict[str, Any]]
    selection_reason: str
    judge_focus: str
    note_provenance: list[str]


@dataclass(frozen=True)
class AccumulationRunSelection:
    window_manifests: list[dict[str, Any]]
    probe_manifests: list[dict[str, Any]]
    selected_windows: list[WindowCase]
    selected_probes: list[Probe]
    target_probe_ids: dict[str, list[str]]
    source_index: dict[str, dict[str, Any]]
    source_manifest_paths: list[Path]
    probes_by_window: dict[str, list[Probe]]
    formal_manifest_path: Path


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def _jsonl_dump(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json_payload(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _load_formal_manifest(manifest_path: Path) -> dict[str, Any]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _window_dataset_dirs_from_manifest(formal_manifest: dict[str, Any]) -> list[Path]:
    source_refs = dict(formal_manifest.get("source_refs") or {})
    for key in ("window_case_datasets", "window_case_dataset"):
        resolved = _manifest_paths_from_entries(list(source_refs.get(key) or []))
        if resolved:
            return resolved
    raise ValueError("benchmark manifest missing window_case_datasets")


def _probe_dataset_dirs_from_manifest(formal_manifest: dict[str, Any]) -> list[Path]:
    source_refs = dict(formal_manifest.get("source_refs") or {})
    for key in ("accumulation_probe_datasets", "accumulation_probe_dataset"):
        resolved = _manifest_paths_from_entries(list(source_refs.get(key) or []))
        if resolved:
            return resolved
    raise ValueError("benchmark manifest missing accumulation_probe_datasets")


def _source_manifest_paths_from_manifest(formal_manifest: dict[str, Any]) -> list[Path]:
    source_refs = dict(formal_manifest.get("source_refs") or {})
    resolved = _manifest_paths_from_entries(list(source_refs.get("source_manifests") or []))
    if not resolved:
        raise ValueError("benchmark manifest missing source_manifests")
    return resolved


def _target_probe_ids_from_manifest(formal_manifest: dict[str, Any], *, target_slice: str) -> dict[str, list[str]]:
    if target_slice not in TARGET_SLICE_VALUES:
        raise ValueError(f"unsupported target slice: {target_slice}")
    requested = ("coherent_accumulation", "insight_and_clarification") if target_slice == "both" else (target_slice,)
    target_probe_ids: dict[str, list[str]] = {}
    for target_name in requested:
        split_names = TARGET_FIELD_BY_SLICE[target_name]
        selected: list[str] = []
        for split_name in split_names:
            payload = dict(formal_manifest.get("splits", {}).get(split_name) or {})
            selected = [str(item) for item in payload.get("all", []) if _clean_text(item)]
            if selected:
                break
        if not selected:
            raise ValueError(f"benchmark manifest split is empty for {target_name}")
        target_probe_ids[target_name] = selected
    return target_probe_ids


def _merge_probe_order(target_probe_ids: dict[str, list[str]]) -> list[str]:
    merged: list[str] = []
    for probe_ids in target_probe_ids.values():
        for probe_id in probe_ids:
            if probe_id not in merged:
                merged.append(probe_id)
    return merged


def _load_windows(dataset_dir: Path) -> tuple[dict[str, Any], list[WindowCase]]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: list[WindowCase] = []
    primary_file = str(manifest["primary_file"])
    with (dataset_dir / primary_file).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(
                WindowCase(
                    window_case_id=str(raw["window_case_id"]),
                    source_id=str(raw["source_id"]),
                    book_title=str(raw.get("book_title", "")),
                    author=str(raw.get("author", "")),
                    output_language=str(raw.get("output_language") or raw.get("language_track") or ""),
                    benchmark_line=str(raw.get("benchmark_line") or raw.get("origin_line") or ""),
                    window_kind=str(raw.get("window_kind", "")),
                    chapter_case_ids=[str(item) for item in raw.get("chapter_case_ids", [])],
                    chapter_ids=[str(item) for item in raw.get("chapter_ids", [])],
                    chapter_numbers=[int(item) for item in raw.get("chapter_numbers", [])],
                    chapter_titles=[str(item) for item in raw.get("chapter_titles", [])],
                    sentence_count=int(raw.get("sentence_count") or raw.get("sentence_count_total") or 0),
                    selection_group_id=str(raw.get("selection_group_id") or raw.get("window_case_id") or ""),
                    selection_group_label=str(raw.get("selection_group_label") or raw.get("window_title") or ""),
                    cross_chapter_window=dict(raw.get("cross_chapter_window") or {}),
                )
            )
    return manifest, rows


def _load_probes(dataset_dir: Path) -> tuple[dict[str, Any], list[Probe]]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    rows: list[Probe] = []
    primary_file = str(manifest["primary_file"])
    with (dataset_dir / primary_file).open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            raw = json.loads(line)
            rows.append(
                Probe(
                    probe_id=str(raw["probe_id"]),
                    window_case_id=str(raw["window_case_id"]),
                    source_id=str(raw["source_id"]),
                    book_title=str(raw.get("book_title", "")),
                    author=str(raw.get("author", "")),
                    output_language=str(raw.get("output_language") or raw.get("language_track") or ""),
                    probe_type=str(raw.get("probe_type", "")),
                    anchor_refs=[dict(item) for item in raw.get("anchor_refs", []) if isinstance(item, dict)],
                    selection_reason=str(raw.get("selection_reason", "")),
                    judge_focus=str(raw.get("judge_focus", "")),
                    note_provenance=[str(item) for item in raw.get("note_provenance", [])],
                )
            )
    return manifest, rows


def _resolve_selected_windows_and_probes(
    *,
    window_dataset_dirs: list[Path],
    probe_dataset_dirs: list[Path],
    selected_probe_ids: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[WindowCase], list[Probe], dict[str, Probe]]:
    window_manifests: list[dict[str, Any]] = []
    probe_manifests: list[dict[str, Any]] = []
    window_index: dict[str, WindowCase] = {}
    probe_index: dict[str, Probe] = {}
    for dataset_dir in window_dataset_dirs:
        manifest, rows = _load_windows(dataset_dir)
        window_manifests.append(manifest)
        for row in rows:
            window_index.setdefault(row.window_case_id, row)
    for dataset_dir in probe_dataset_dirs:
        manifest, rows = _load_probes(dataset_dir)
        probe_manifests.append(manifest)
        for row in rows:
            probe_index.setdefault(row.probe_id, row)
    selected_probes: list[Probe] = []
    missing_probe_ids: list[str] = []
    for probe_id in selected_probe_ids:
        probe = probe_index.get(probe_id)
        if probe is None:
            missing_probe_ids.append(probe_id)
            continue
        selected_probes.append(probe)
    if missing_probe_ids:
        raise ValueError(f"missing probes: {', '.join(sorted(missing_probe_ids))}")
    selected_windows: list[WindowCase] = []
    seen_window_ids: set[str] = set()
    for probe in selected_probes:
        if probe.window_case_id in seen_window_ids:
            continue
        window = window_index.get(probe.window_case_id)
        if window is None:
            raise ValueError(f"missing window for probe: {probe.probe_id}")
        seen_window_ids.add(probe.window_case_id)
        selected_windows.append(window)
    return window_manifests, probe_manifests, selected_windows, selected_probes, probe_index


def _window_log_label(window: WindowCase) -> str:
    return window.window_case_id


def _log_window_progress(window: WindowCase, message: str) -> None:
    print(f"[window {_window_log_label(window)}] {message}", flush=True)


def _log_probe_progress(probe: Probe, message: str) -> None:
    print(f"[probe {probe.probe_id}] {message}", flush=True)


def _meta_dir(run_root: Path) -> Path:
    return run_root / "meta"


def _shard_root(run_root: Path, shard_id: str) -> Path:
    return run_root / "shards" / shard_id


def _shard_windows_dir(run_root: Path, shard_id: str) -> Path:
    return _shard_root(run_root, shard_id) / "units"


def _shard_bundles_dir(run_root: Path, shard_id: str, mechanism_key: str) -> Path:
    return _shard_root(run_root, shard_id) / "bundles" / mechanism_key


def _shard_probe_cases_dir(run_root: Path, shard_id: str) -> Path:
    return _shard_root(run_root, shard_id) / "cases"


def _shard_summary_dir(run_root: Path, shard_id: str) -> Path:
    return _shard_root(run_root, shard_id) / "summary"


def _window_payload_path(run_root: Path, shard_id: str, window_case_id: str) -> Path:
    return _shard_windows_dir(run_root, shard_id) / f"{window_case_id}.json"


def _bundle_payload_path(run_root: Path, shard_id: str, mechanism_key: str, window_case_id: str) -> Path:
    return _shard_bundles_dir(run_root, shard_id, mechanism_key) / f"{window_case_id}.json"


def _probe_payload_path(run_root: Path, shard_id: str, probe_id: str) -> Path:
    return _shard_probe_cases_dir(run_root, shard_id) / f"{probe_id}.json"


def _selection_dataset_manifest_path(run_root: Path) -> Path:
    return _meta_dir(run_root) / "dataset_manifest.json"


def _selection_windows_manifest_path(run_root: Path) -> Path:
    return _meta_dir(run_root) / "selected_windows.json"


def _mechanism_keys_for_filter(mechanism_filter: str) -> tuple[str, ...]:
    if mechanism_filter not in MECHANISM_FILTER_VALUES:
        raise ValueError(f"unsupported mechanism filter: {mechanism_filter}")
    if mechanism_filter == "both":
        return MECHANISM_KEYS
    return (mechanism_filter,)


def _load_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _bundle_payload_is_structurally_complete(payload: dict[str, Any]) -> bool:
    return bool(payload.get("status")) and "normalized_eval_bundle" in payload and "bundle_summary" in payload


def _path_shard_id(path: Path) -> str:
    parts = list(path.parts)
    try:
        shard_index = parts.index("shards")
    except ValueError:
        return "default"
    if shard_index + 1 >= len(parts):
        return "default"
    return parts[shard_index + 1]


def _load_exported_bundle_payload(*, output_dir: Path, mechanism_key: str) -> dict[str, Any] | None:
    export_path = output_dir / "_mechanisms" / mechanism_key / "exports" / "normalized_eval_bundle.json"
    bundle = _load_json_if_exists(export_path)
    if bundle is None:
        return None
    mechanism_label = _clean_text(bundle.get("mechanism_label")) or mechanism_key
    payload = {
        "status": "completed",
        "mechanism_key": mechanism_key,
        "mechanism_label": mechanism_label,
        "output_dir": str(output_dir),
        "normalized_eval_bundle": bundle,
        "bundle_summary": _summarize_bundle(bundle),
        "error": "",
    }
    return payload if payload.get("status") == "completed" and _bundle_payload_is_structurally_complete(payload) else None


def _recover_bundle_payload(run_root: Path, *, window_case_id: str, mechanism_key: str) -> tuple[Path, dict[str, Any]] | None:
    window_candidates = [path for path in run_root.glob(f"shards/*/units/{window_case_id}.json") if path.is_file()]
    for window_path in sorted(window_candidates, key=lambda item: (item.stat().st_mtime_ns, str(item)), reverse=True):
        window_payload = _load_json_if_exists(window_path)
        if window_payload is None:
            continue
        mechanism_payload = dict((window_payload.get("mechanisms") or {}).get(mechanism_key) or {})
        shard_id = _path_shard_id(window_path)
        destination = _bundle_payload_path(run_root, shard_id, mechanism_key, window_case_id)
        if mechanism_payload.get("status") == "completed" and _bundle_payload_is_structurally_complete(mechanism_payload):
            _json_dump(destination, mechanism_payload)
            return destination, mechanism_payload
        output_dir_text = _clean_text(mechanism_payload.get("output_dir"))
        if output_dir_text:
            recovered = _load_exported_bundle_payload(output_dir=Path(output_dir_text), mechanism_key=mechanism_key)
            if recovered is not None:
                _json_dump(destination, recovered)
                return destination, recovered
    output_candidates = [path for path in run_root.glob(f"shards/*/outputs/{window_case_id}/{mechanism_key}") if path.is_dir()]
    for output_dir in sorted(output_candidates, key=lambda item: (item.stat().st_mtime_ns, str(item)), reverse=True):
        recovered = _load_exported_bundle_payload(output_dir=output_dir, mechanism_key=mechanism_key)
        if recovered is None:
            continue
        shard_id = _path_shard_id(output_dir)
        destination = _bundle_payload_path(run_root, shard_id, mechanism_key, window_case_id)
        _json_dump(destination, recovered)
        return destination, recovered
    return None


def _existing_bundle_payload(run_root: Path, *, window_case_id: str, mechanism_key: str) -> tuple[Path, dict[str, Any]] | None:
    candidates = [
        path
        for path in run_root.glob(f"shards/*/bundles/{mechanism_key}/{window_case_id}.json")
        if path.is_file()
    ]
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(candidates, key=lambda item: (item.stat().st_mtime_ns, str(item))):
        payload = _load_json_if_exists(path)
        if payload is not None:
            loaded.append((path, payload))
    completed = [item for item in loaded if item[1].get("status") == "completed" and _bundle_payload_is_structurally_complete(item[1])]
    if completed:
        return completed[-1]
    recovered = _recover_bundle_payload(run_root, window_case_id=window_case_id, mechanism_key=mechanism_key)
    if recovered is not None:
        return recovered
    complete = [item for item in loaded if _bundle_payload_is_structurally_complete(item[1])]
    if complete:
        return complete[-1]
    return loaded[-1] if loaded else None


def _existing_probe_payload(run_root: Path, *, probe_id: str) -> tuple[Path, dict[str, Any]] | None:
    candidates = [path for path in run_root.glob(f"shards/*/cases/{probe_id}.json") if path.is_file()]
    if not candidates:
        return None
    candidates.sort(key=lambda path: (path.stat().st_mtime_ns, str(path)))
    path = candidates[-1]
    payload = _load_json_if_exists(path)
    if payload is None:
        return None
    return path, payload


def _probe_payload_covers_targets(payload: dict[str, Any], *, target_names: list[str]) -> bool:
    target_results = payload.get("target_results")
    if not isinstance(target_results, dict):
        return False
    return all(target_name in target_results for target_name in target_names)


def _mechanism_failure_payload(mechanism_key: str, *, error: str, status: str = "failed") -> dict[str, Any]:
    return {
        "status": status,
        "mechanism_key": mechanism_key,
        "mechanism_label": mechanism_key,
        "output_dir": "",
        "normalized_eval_bundle": {},
        "bundle_summary": {},
        "error": error,
    }


@contextmanager
def _isolated_output_dir(output_dir: Path):
    with override_output_dir(output_dir):
        yield


def _run_state_path(output_dir: Path) -> Path:
    return output_dir / "_runtime" / "run_state.json"


def _recoverable_resume_context(output_dir: Path, *, error: Exception | None = None) -> dict[str, str] | None:
    payload = _load_json_if_exists(_run_state_path(output_dir))
    if not isinstance(payload, dict):
        payload = {}
    current_activity = payload.get("current_reading_activity")
    if not isinstance(current_activity, dict):
        current_activity = {}
    problem_code = _clean_text(getattr(error, "problem_code", "")).lower()
    if not problem_code:
        problem_code = _clean_text(current_activity.get("problem_code")).lower()
    if not problem_code:
        problem_code = _clean_text(payload.get("problem_code")).lower()
    if problem_code not in RECOVERABLE_MECHANISM_PROBLEM_CODES:
        return None
    if not bool(payload.get("resume_available")):
        return None
    stage = _clean_text(payload.get("stage")).lower()
    if stage == "completed":
        return None
    return {
        "problem_code": problem_code,
        "last_checkpoint_at": _clean_text(payload.get("last_checkpoint_at")),
        "stage": stage,
    }


def _summarize_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    chapter_outputs = [dict(item) for item in bundle.get("chapters") or [] if isinstance(item, dict)]
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
        "chapter_outputs": chapter_outputs,
        "reaction_count": len(reactions),
        "attention_event_count": len(attention_events),
        "reactions": reactions[:8],
        "attention_events": attention_events[:10],
        "memory_summaries": [str(item)[:320] for item in (bundle.get("memory_summaries") or [])[:5]],
    }


def _run_mechanism_attempt(
    window: WindowCase,
    source: dict[str, Any],
    *,
    mechanism_key: str,
    shard_root: Path,
    resume_from_existing: bool,
) -> dict[str, Any]:
    if mechanism_key == "attentional_v2":
        mechanism = AttentionalV2Mechanism()
    elif mechanism_key == "iterator_v1":
        mechanism = IteratorV1Mechanism()
    else:
        raise ValueError(f"unsupported mechanism: {mechanism_key}")

    book_path = ROOT / str(source["relative_local_path"])
    isolated_output_dir = shard_root / "outputs" / window.window_case_id / mechanism_key
    runtime_dir = isolated_output_dir / "_runtime"
    _log_window_progress(
        window,
        f"[mechanism-start] {mechanism_key}"
        + (" resume=true" if resume_from_existing else ""),
    )
    if not resume_from_existing:
        shutil.rmtree(isolated_output_dir, ignore_errors=True)
    isolated_output_dir.parent.mkdir(parents=True, exist_ok=True)
    result = None
    with runtime_progress_heartbeat(
        runtime_dir=runtime_dir,
        mechanism_key=mechanism_key,
        emit=lambda message: _log_window_progress(window, message),
    ):
        with _isolated_output_dir(isolated_output_dir):
            for index, chapter_case_id in enumerate(window.chapter_case_ids):
                chapter_id = int(chapter_case_id.rsplit("__", 1)[-1])
                result = mechanism.read_book(
                    ReadRequest(
                        book_path=book_path,
                        chapter_number=chapter_id,
                        continue_mode=resume_from_existing or index > 0,
                        user_intent=DEFAULT_USER_INTENT,
                        language_mode=window.output_language,
                        task_mode="sequential",
                        mechanism_key=mechanism_key,
                        mechanism_config={"persist_normalized_eval_bundle": True},
                    )
                )
    bundle = dict((result.normalized_eval_bundle if result else {}) or {})
    _log_window_progress(window, f"[mechanism-completed] {mechanism_key}")
    return {
        "status": "completed",
        "mechanism_key": mechanism_key,
        "mechanism_label": result.mechanism.label if result else mechanism_key,
        "output_dir": str(result.output_dir) if result else "",
        "normalized_eval_bundle": bundle,
        "bundle_summary": _summarize_bundle(bundle),
        "error": "",
    }


def _run_mechanism_for_window(
    window: WindowCase,
    source: dict[str, Any],
    *,
    mechanism_key: str,
    shard_root: Path,
) -> dict[str, Any]:
    isolated_output_dir = shard_root / "outputs" / window.window_case_id / mechanism_key
    recovery_context = _recoverable_resume_context(isolated_output_dir)
    resume_from_existing = recovery_context is not None
    recovery_already_used = resume_from_existing
    if recovery_context is not None:
        checkpoint_note = (
            f" last_checkpoint_at={recovery_context['last_checkpoint_at']}"
            if recovery_context.get("last_checkpoint_at")
            else ""
        )
        stage_note = f" stage={recovery_context['stage']}" if recovery_context.get("stage") else ""
        _log_window_progress(
            window,
            f"[mechanism-resume-existing] {mechanism_key} problem_code={recovery_context['problem_code']}"
            f"{checkpoint_note}{stage_note}",
        )

    while True:
        try:
            return _run_mechanism_attempt(
                window,
                source,
                mechanism_key=mechanism_key,
                shard_root=shard_root,
                resume_from_existing=resume_from_existing,
            )
        except Exception as exc:
            recovery_context = _recoverable_resume_context(isolated_output_dir, error=exc)
            if recovery_already_used or recovery_context is None:
                raise
            checkpoint_note = (
                f" last_checkpoint_at={recovery_context['last_checkpoint_at']}"
                if recovery_context.get("last_checkpoint_at")
                else ""
            )
            _log_window_progress(
                window,
                f"[mechanism-auto-recover] {mechanism_key} problem_code={recovery_context['problem_code']}"
                f"{checkpoint_note}",
            )
            resume_from_existing = True
            recovery_already_used = True


def _run_mechanism_worker(payload_path: Path, result_path: Path) -> int:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    window = WindowCase(**dict(payload["window"]))
    source = dict(payload["source"])
    result = _run_mechanism_for_window(
        window,
        source,
        mechanism_key=str(payload["mechanism_key"]),
        shard_root=Path(str(payload["shard_root"])),
    )
    _write_json_payload(result_path, result)
    return 0


def _run_window_bundle_worker(payload_path: Path, result_path: Path) -> int:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    window = WindowCase(**dict(payload["window"]))
    source = dict(payload["source"])
    result = _run_window_bundle(
        window,
        source=source,
        run_root=Path(str(payload["run_root"])),
        shard_id=str(payload["shard_id"]),
        mechanism_execution_mode=str(payload["mechanism_execution_mode"]),
        mechanism_filter=str(payload["mechanism_filter"]),
        skip_existing=bool(payload.get("skip_existing", False)),
    )
    _write_json_payload(result_path, result)
    return 0


def _run_payload_worker(payload_path: Path, result_path: Path) -> int:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    worker_kind = str(payload.get("worker_kind", "mechanism")).strip() or "mechanism"
    if worker_kind == "mechanism":
        return _run_mechanism_worker(payload_path, result_path)
    if worker_kind == "window_bundle":
        return _run_window_bundle_worker(payload_path, result_path)
    raise ValueError(f"unsupported worker kind: {worker_kind}")


def _run_mechanism_subprocess(
    window: WindowCase,
    source: dict[str, Any],
    *,
    mechanism_key: str,
    shard_root: Path,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="accumulation-comparison-mechanism-worker-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        payload_path = temp_dir / "payload.json"
        result_path = temp_dir / "result.json"
        _write_json_payload(
            payload_path,
            {
                "worker_kind": "mechanism",
                "window": asdict(window),
                "source": source,
                "mechanism_key": mechanism_key,
                "shard_root": str(shard_root),
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


def _run_window_subprocess(
    window: WindowCase,
    *,
    source: dict[str, Any],
    run_root: Path,
    shard_id: str,
    mechanism_execution_mode: str,
    mechanism_filter: str,
    skip_existing: bool,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="accumulation-comparison-window-worker-") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        payload_path = temp_dir / "payload.json"
        result_path = temp_dir / "result.json"
        _write_json_payload(
            payload_path,
            {
                "worker_kind": "window_bundle",
                "window": asdict(window),
                "source": source,
                "run_root": str(run_root),
                "shard_id": shard_id,
                "mechanism_execution_mode": mechanism_execution_mode,
                "mechanism_filter": mechanism_filter,
                "skip_existing": bool(skip_existing),
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


def _window_result_payload(
    window: WindowCase,
    *,
    mechanisms: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "window_case_id": window.window_case_id,
        "source_id": window.source_id,
        "output_language": window.output_language,
        "book_title": window.book_title,
        "author": window.author,
        "chapter_case_ids": list(window.chapter_case_ids),
        "mechanisms": mechanisms,
    }


def _build_window_result_from_existing_bundles(
    *,
    run_root: Path,
    window: WindowCase,
    fallback_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    fallback_results = fallback_results or {}
    mechanisms: dict[str, dict[str, Any]] = {}
    for mechanism_key in MECHANISM_KEYS:
        payload = fallback_results.get(mechanism_key)
        if payload is None:
            existing = _existing_bundle_payload(run_root, window_case_id=window.window_case_id, mechanism_key=mechanism_key)
            payload = existing[1] if existing is not None else None
        mechanisms[mechanism_key] = payload or _mechanism_failure_payload(
            mechanism_key,
            error="bundle_missing",
            status="missing",
        )
    return _window_result_payload(window, mechanisms=mechanisms)


def _write_bundle_payload(
    *,
    run_root: Path,
    shard_id: str,
    window_case_id: str,
    mechanism_key: str,
    payload: dict[str, Any],
) -> None:
    _json_dump(_bundle_payload_path(run_root, shard_id, mechanism_key, window_case_id), payload)


def _run_window_bundle(
    window: WindowCase,
    *,
    source: dict[str, Any],
    run_root: Path,
    shard_id: str,
    mechanism_execution_mode: str,
    mechanism_filter: str,
    skip_existing: bool,
) -> dict[str, Any]:
    if mechanism_execution_mode not in {"serial", "parallel"}:
        raise ValueError(f"unsupported mechanism execution mode: {mechanism_execution_mode}")
    mechanism_keys = _mechanism_keys_for_filter(mechanism_filter)
    shard_root = _shard_root(run_root, shard_id)

    def _run_one(mechanism_key: str) -> dict[str, Any]:
        existing = _existing_bundle_payload(run_root, window_case_id=window.window_case_id, mechanism_key=mechanism_key)
        if skip_existing and existing is not None and _bundle_payload_is_structurally_complete(existing[1]):
            _log_window_progress(window, f"[mechanism-skip-existing] {mechanism_key}")
            return existing[1]
        try:
            payload = _run_mechanism_for_window(window, source, mechanism_key=mechanism_key, shard_root=shard_root)
            _write_bundle_payload(
                run_root=run_root,
                shard_id=shard_id,
                window_case_id=window.window_case_id,
                mechanism_key=mechanism_key,
                payload=payload,
            )
            return payload
        except Exception as exc:
            _log_window_progress(window, f"[mechanism-failed] {mechanism_key} error={exc}")
            payload = _mechanism_failure_payload(mechanism_key, error=str(exc))
            _write_bundle_payload(
                run_root=run_root,
                shard_id=shard_id,
                window_case_id=window.window_case_id,
                mechanism_key=mechanism_key,
                payload=payload,
            )
            return payload

    results: dict[str, dict[str, Any]] = {}
    if mechanism_execution_mode == "serial" or len(mechanism_keys) <= 1:
        for mechanism_key in mechanism_keys:
            results[mechanism_key] = _run_one(mechanism_key)
    else:
        with ThreadPoolExecutor(max_workers=len(mechanism_keys), thread_name_prefix="accumulation-mechanism") as executor:
            future_to_mechanism = {
                executor.submit(
                    _run_mechanism_subprocess,
                    window,
                    source,
                    mechanism_key=mechanism_key,
                    shard_root=shard_root,
                ): mechanism_key
                for mechanism_key in mechanism_keys
            }
            for future in as_completed(future_to_mechanism):
                mechanism_key = future_to_mechanism[future]
                try:
                    results[mechanism_key] = future.result()
                except Exception as exc:
                    results[mechanism_key] = _mechanism_failure_payload(mechanism_key, error=str(exc))
                    _write_bundle_payload(
                        run_root=run_root,
                        shard_id=shard_id,
                        window_case_id=window.window_case_id,
                        mechanism_key=mechanism_key,
                        payload=results[mechanism_key],
                    )
    payload = _build_window_result_from_existing_bundles(run_root=run_root, window=window, fallback_results=results)
    _json_dump(_window_payload_path(run_root, shard_id, window.window_case_id), payload)
    return payload


def _find_anchor_span(document: BookDocument, anchor: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    chapter_id = int(anchor["chapter_id"])
    start_sentence_id = str(anchor["start_sentence_id"])
    end_sentence_id = str(anchor["end_sentence_id"])
    anchor_label = _clean_text(anchor.get("anchor_id")) or _clean_text(anchor.get("source_ref_id")) or f"{chapter_id}:{start_sentence_id}-{end_sentence_id}"
    for chapter in document.get("chapters", []):
        if not isinstance(chapter, dict):
            continue
        if int(chapter.get("id", 0) or 0) != chapter_id:
            continue
        sentences = [item for item in chapter.get("sentences", []) if isinstance(item, dict)]
        by_id = {str(sentence.get("sentence_id", "")): index for index, sentence in enumerate(sentences)}
        if start_sentence_id not in by_id or end_sentence_id not in by_id:
            raise ValueError(f"probe anchor span not found: {anchor_label}")
        start = by_id[start_sentence_id]
        end = by_id[end_sentence_id]
        if end < start:
            raise ValueError(f"probe anchor span reversed: {anchor_label}")
        return chapter, sentences[start : end + 1]
    raise ValueError(f"chapter missing for probe anchor: {anchor_label}")


def _section_refs_for_span(span: list[dict[str, Any]], *, chapter_id: int) -> set[str]:
    refs: set[str] = set()
    for sentence in span:
        paragraph_index = int(sentence.get("paragraph_index", 0) or 0)
        if paragraph_index > 0:
            refs.add(f"{chapter_id}.{paragraph_index}")
    return refs


def _extract_probe_local_evidence(
    *,
    probe: Probe,
    bundle: dict[str, Any],
    document: BookDocument,
    window: WindowCase,
) -> dict[str, Any]:
    anchor_summaries: list[dict[str, Any]] = []
    matched_reactions: list[dict[str, Any]] = []
    matched_events: list[dict[str, Any]] = []
    match_method_counts = Counter()

    for anchor in probe.anchor_refs:
        chapter, span = _find_anchor_span(document, anchor)
        anchor_excerpt_norm = _normalize_compare_text(anchor.get("excerpt_text"))
        sentence_norms = [_normalize_compare_text(sentence.get("text", "")) for sentence in span]
        section_refs = _section_refs_for_span(span, chapter_id=int(anchor["chapter_id"]))

        anchor_reactions: list[dict[str, Any]] = []
        for item in bundle.get("reactions") or []:
            if not isinstance(item, dict):
                continue
            candidate_text = _clean_text(item.get("anchor_quote") or item.get("content"))
            score, methods = _match_entry(
                chapter_id=int(anchor["chapter_id"]),
                case_section_refs=section_refs,
                case_excerpt_norm=anchor_excerpt_norm,
                sentence_norms=sentence_norms,
                section_ref=_clean_text(item.get("section_ref")),
                candidate_text=candidate_text,
            )
            if score <= 0:
                continue
            payload = {
                "anchor_id": _clean_text(anchor.get("anchor_id")) or _clean_text(anchor.get("source_ref_id")),
                "type": _clean_text(item.get("type")),
                "section_ref": _clean_text(item.get("section_ref")),
                "anchor_quote": _clean_text(item.get("anchor_quote"))[:240],
                "content": _clean_text(item.get("content"))[:320],
                "match_score": score,
                "match_methods": methods,
            }
            anchor_reactions.append(payload)
            matched_reactions.append(payload)

        anchor_events: list[dict[str, Any]] = []
        for item in bundle.get("attention_events") or []:
            if not isinstance(item, dict):
                continue
            candidate_text = _clean_text(item.get("current_excerpt") or item.get("message"))
            score, methods = _match_entry(
                chapter_id=int(anchor["chapter_id"]),
                case_section_refs=section_refs,
                case_excerpt_norm=anchor_excerpt_norm,
                sentence_norms=sentence_norms,
                section_ref=_clean_text(item.get("section_ref")),
                candidate_text=candidate_text,
            )
            if score <= 0:
                continue
            payload = {
                "anchor_id": _clean_text(anchor.get("anchor_id")) or _clean_text(anchor.get("source_ref_id")),
                "kind": _clean_text(item.get("kind")),
                "phase": _clean_text(item.get("phase")),
                "section_ref": _clean_text(item.get("section_ref")),
                "move_type": _clean_text(item.get("move_type")),
                "message": _clean_text(item.get("message"))[:240],
                "current_excerpt": _clean_text(item.get("current_excerpt"))[:240],
                "match_score": score,
                "match_methods": methods,
            }
            anchor_events.append(payload)
            matched_events.append(payload)

        for payload in anchor_reactions + anchor_events:
            match_method_counts.update(str(method) for method in payload.get("match_methods", []))
        anchor_summaries.append(
            {
                "anchor_id": _clean_text(anchor.get("anchor_id")) or _clean_text(anchor.get("source_ref_id")),
                "anchor_kind": _clean_text(anchor.get("anchor_kind")),
                "chapter_id": str(anchor["chapter_id"]),
                "target_profile_id": _clean_text(anchor.get("target_profile_id")),
                "excerpt_text": _clean_text(anchor.get("excerpt_text"))[:280],
                "section_refs": sorted(section_refs),
                "matched_reaction_count": len(anchor_reactions),
                "matched_attention_event_count": len(anchor_events),
                "match_method": _primary_match_method(
                    Counter(method for payload in anchor_reactions + anchor_events for method in payload.get("match_methods", []))
                ),
            }
        )

    matched_reactions.sort(key=lambda item: (-int(item["match_score"]), str(item["section_ref"]), str(item["type"])))
    matched_events.sort(key=lambda item: (-int(item["match_score"]), str(item["section_ref"]), str(item["kind"])))
    chapter_outputs = [
        dict(item)
        for item in bundle.get("chapters") or []
        if isinstance(item, dict) and str(item.get("chapter_id")) in set(window.chapter_ids)
    ]
    return {
        "window_case_id": window.window_case_id,
        "window_kind": window.window_kind,
        "anchor_count": len(probe.anchor_refs),
        "anchor_hit_count": sum(
            1
            for summary in anchor_summaries
            if int(summary["matched_reaction_count"]) > 0 or int(summary["matched_attention_event_count"]) > 0
        ),
        "anchor_summaries": anchor_summaries,
        "matched_reaction_count": len(matched_reactions),
        "matched_attention_event_count": len(matched_events),
        "matched_reactions": matched_reactions[:10],
        "matched_attention_events": matched_events[:12],
        "match_method": _primary_match_method(match_method_counts),
        "match_method_counts": dict(match_method_counts),
        "chapter_outputs": chapter_outputs,
        "memory_summaries": [str(item)[:320] for item in (bundle.get("memory_summaries") or [])[:5]],
    }


def _judge_target(
    *,
    target_name: str,
    probe: Probe,
    window: WindowCase,
    attentional: dict[str, Any],
    iterator: dict[str, Any],
    run_root: Path,
    judge_mode: str,
    shard_id: str,
) -> dict[str, Any]:
    config = TARGET_CONFIGS[target_name]
    score_keys = tuple(config["score_keys"])
    if judge_mode == "none":
        judgment = _default_judgment(score_keys, reason="judge_disabled")
        _log_probe_progress(probe, f"[judge-skip] {target_name} winner={judgment['winner']}")
        return judgment
    if attentional.get("status") != "completed" or iterator.get("status") != "completed":
        judgment = _default_judgment(score_keys, reason="mechanism_unavailable")
        _log_probe_progress(probe, f"[judge-skip] {target_name} reason=mechanism_unavailable")
        return judgment

    _log_probe_progress(probe, f"[judge-start] {target_name}")
    try:
        with llm_invocation_scope(
            profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
            trace_context=eval_trace_context(
                run_root,
                eval_target=DEFAULT_TARGET,
                stage="accumulation_comparison",
                node=target_name,
                extra={
                    "shard_id": shard_id,
                    "probe_id": probe.probe_id,
                    "window_case_id": window.window_case_id,
                },
            ),
        ):
            payload = invoke_json(
                str(config["system_prompt"]),
                str(config["user_prompt"]).format(
                    probe_json=json.dumps(
                        {
                            "probe_id": probe.probe_id,
                            "probe_type": probe.probe_type,
                            "selection_reason": probe.selection_reason,
                            "judge_focus": probe.judge_focus,
                            "window_case_id": window.window_case_id,
                            "window_kind": window.window_kind,
                            "chapter_case_ids": window.chapter_case_ids,
                            "anchor_refs": probe.anchor_refs,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                    left_json=json.dumps(attentional["local_evidence"], ensure_ascii=False, indent=2),
                    right_json=json.dumps(iterator["local_evidence"], ensure_ascii=False, indent=2),
                ),
                _default_judgment(score_keys, reason="judge_unavailable"),
            )
    except ReaderLLMError:
        payload = {}
    except Exception:
        payload = {}
    judgment = _normalize_judgment(payload, score_keys=score_keys, default_reason="judge_unavailable")
    _log_probe_progress(probe, f"[judge-completed] {target_name} winner={judgment['winner']}")
    return judgment


def _judge_targets_for_probe(
    *,
    probe: Probe,
    window: WindowCase,
    probe_targets: list[str],
    mechanisms: dict[str, dict[str, Any]],
    run_root: Path,
    judge_mode: str,
    judge_execution_mode: str,
    shard_id: str,
) -> dict[str, dict[str, Any]]:
    if judge_execution_mode not in {"serial", "parallel"}:
        raise ValueError(f"unsupported judge execution mode: {judge_execution_mode}")
    if judge_execution_mode == "serial" or judge_mode == "none" or len(probe_targets) <= 1:
        return {
            target_name: {
                "judgment": _judge_target(
                    target_name=target_name,
                    probe=probe,
                    window=window,
                    attentional=mechanisms["attentional_v2"],
                    iterator=mechanisms["iterator_v1"],
                    run_root=run_root,
                    judge_mode=judge_mode,
                    shard_id=shard_id,
                )
            }
            for target_name in probe_targets
        }

    target_results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=len(probe_targets), thread_name_prefix="accumulation-judge") as executor:
        future_to_target = {
            executor.submit(
                _judge_target,
                target_name=target_name,
                probe=probe,
                window=window,
                attentional=mechanisms["attentional_v2"],
                iterator=mechanisms["iterator_v1"],
                run_root=run_root,
                judge_mode=judge_mode,
                shard_id=shard_id,
            ): target_name
            for target_name in probe_targets
        }
        for future in as_completed(future_to_target):
            target_name = future_to_target[future]
            try:
                judgment = future.result()
            except Exception:
                judgment = _default_judgment(tuple(TARGET_CONFIGS[target_name]["score_keys"]), reason="judge_unavailable")
            target_results[target_name] = {"judgment": judgment}
    return {target_name: target_results[target_name] for target_name in probe_targets}


def _evaluate_probe(
    probe: Probe,
    *,
    probe_targets: list[str],
    window: WindowCase,
    unit_result: dict[str, Any],
    document: BookDocument,
    run_root: Path,
    judge_mode: str,
    judge_execution_mode: str,
    shard_id: str,
) -> dict[str, Any]:
    _log_probe_progress(probe, f"[probe-start] judge_mode={judge_mode} judge_execution_mode={judge_execution_mode}")
    mechanisms: dict[str, dict[str, Any]] = {}
    for mechanism_key in MECHANISM_KEYS:
        mechanism_result = dict(unit_result["mechanisms"][mechanism_key])
        if mechanism_result.get("status") == "completed":
            local_evidence = _extract_probe_local_evidence(
                probe=probe,
                bundle=dict(mechanism_result.get("normalized_eval_bundle") or {}),
                document=document,
                window=window,
            )
        else:
            local_evidence = {
                "error": _clean_text(mechanism_result.get("error")),
                "anchor_count": len(probe.anchor_refs),
                "anchor_hit_count": 0,
                "matched_reaction_count": 0,
                "matched_attention_event_count": 0,
                "anchor_summaries": [],
                "matched_reactions": [],
                "matched_attention_events": [],
                "match_method_counts": {},
            }
        mechanisms[mechanism_key] = {
            "status": str(mechanism_result.get("status", "failed") or "failed"),
            "mechanism_label": _clean_text(mechanism_result.get("mechanism_label")) or mechanism_key,
            "output_dir": _clean_text(mechanism_result.get("output_dir")),
            "bundle_summary": dict(mechanism_result.get("bundle_summary") or {}),
            "local_evidence": local_evidence,
            "error": _clean_text(mechanism_result.get("error")),
        }
    target_results = _judge_targets_for_probe(
        probe=probe,
        window=window,
        probe_targets=probe_targets,
        mechanisms=mechanisms,
        run_root=run_root,
        judge_mode=judge_mode,
        judge_execution_mode=judge_execution_mode,
        shard_id=shard_id,
    )
    _log_probe_progress(probe, "[probe-completed]")
    return {
        "probe_id": probe.probe_id,
        "window_case_id": window.window_case_id,
        "probe_type": probe.probe_type,
        "source_id": probe.source_id,
        "book_title": probe.book_title,
        "author": probe.author,
        "output_language": probe.output_language,
        "probe_targets": probe_targets,
        "mechanisms": mechanisms,
        "target_results": target_results,
    }


def _probe_failure_result(
    probe: Probe,
    *,
    probe_targets: list[str],
    window: WindowCase,
    unit_result: dict[str, Any],
    error: str,
) -> dict[str, Any]:
    mechanisms: dict[str, dict[str, Any]] = {}
    for mechanism_key in MECHANISM_KEYS:
        mechanism_result = dict(unit_result.get("mechanisms", {}).get(mechanism_key) or {})
        mechanisms[mechanism_key] = {
            "status": str(mechanism_result.get("status", "failed") or "failed"),
            "mechanism_label": _clean_text(mechanism_result.get("mechanism_label")) or mechanism_key,
            "output_dir": _clean_text(mechanism_result.get("output_dir")),
            "bundle_summary": dict(mechanism_result.get("bundle_summary") or {}),
            "local_evidence": {
                "error": _clean_text(error),
                "anchor_count": len(probe.anchor_refs),
                "anchor_hit_count": 0,
                "matched_reaction_count": 0,
                "matched_attention_event_count": 0,
                "anchor_summaries": [],
                "matched_reactions": [],
                "matched_attention_events": [],
                "match_method": "none",
                "match_method_counts": {},
            },
            "error": _clean_text(mechanism_result.get("error")),
        }
    target_results = {
        target_name: {
            "judgment": _default_judgment(tuple(TARGET_CONFIGS[target_name]["score_keys"]), reason="probe_error")
        }
        for target_name in probe_targets
    }
    return {
        "probe_id": probe.probe_id,
        "window_case_id": window.window_case_id,
        "probe_type": probe.probe_type,
        "source_id": probe.source_id,
        "book_title": probe.book_title,
        "author": probe.author,
        "output_language": probe.output_language,
        "probe_targets": probe_targets,
        "mechanisms": mechanisms,
        "target_results": target_results,
        "probe_error": _clean_text(error),
    }


def _aggregate_target(probe_results: list[dict[str, Any]], *, target_name: str) -> dict[str, Any]:
    scoped = [item for item in probe_results if target_name in item["target_results"]]
    if not scoped:
        return {
            "case_count": 0,
            "winner_counts": {},
            "judge_unavailable_count": 0,
            "mechanism_failure_count": 0,
            "average_scores": {"attentional_v2": 0.0, "iterator_v1": 0.0},
            "language_summaries": {},
        }
    winner_counts = Counter(item["target_results"][target_name]["judgment"]["winner"] for item in scoped)
    judge_unavailable_count = sum(
        1
        for item in scoped
        if item["target_results"][target_name]["judgment"]["reason"] in {"judge_unavailable", "mechanism_unavailable", "probe_error"}
    )
    mechanism_failure_count = sum(
        1
        for item in scoped
        if any(payload.get("status") != "completed" for payload in item["mechanisms"].values())
    )
    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in scoped:
        by_language[str(item["output_language"])].append(item)
    summary = {
        "case_count": len(scoped),
        "winner_counts": dict(winner_counts),
        "judge_unavailable_count": judge_unavailable_count,
        "mechanism_failure_count": mechanism_failure_count,
        "average_scores": {
            "attentional_v2": round(
                mean(_score_average(item["target_results"][target_name]["judgment"]["scores"]["attentional_v2"]) for item in scoped),
                3,
            ),
            "iterator_v1": round(
                mean(_score_average(item["target_results"][target_name]["judgment"]["scores"]["iterator_v1"]) for item in scoped),
                3,
            ),
        },
        "language_summaries": {},
    }
    for language, items in sorted(by_language.items()):
        summary["language_summaries"][language] = {
            "case_count": len(items),
            "winner_counts": dict(Counter(item["target_results"][target_name]["judgment"]["winner"] for item in items)),
            "judge_unavailable_count": sum(
                1
                for item in items
                if item["target_results"][target_name]["judgment"]["reason"] in {"judge_unavailable", "mechanism_unavailable", "probe_error"}
            ),
            "average_scores": {
                "attentional_v2": round(
                    mean(_score_average(item["target_results"][target_name]["judgment"]["scores"]["attentional_v2"]) for item in items),
                    3,
                ),
                "iterator_v1": round(
                    mean(_score_average(item["target_results"][target_name]["judgment"]["scores"]["iterator_v1"]) for item in items),
                    3,
                ),
            },
        }
    return summary


def _aggregate(probe_results: list[dict[str, Any]], *, target_names: list[str]) -> dict[str, Any]:
    return {
        "case_count": len(probe_results),
        "target_summaries": {
            target_name: _aggregate_target(probe_results, target_name=target_name)
            for target_name in target_names
        },
    }


def _build_markdown_report(
    *,
    run_id: str,
    selected_windows: list[WindowCase],
    selected_probes: list[Probe],
    target_probe_ids: dict[str, list[str]],
    aggregate: dict[str, Any],
    window_datasets: list[dict[str, Any]],
    probe_datasets: list[dict[str, Any]],
) -> str:
    lines: list[str] = []
    lines.append("# Accumulation Comparison")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("This report records the bounded long-span cross-mechanism comparison between `attentional_v2` and `iterator_v1`.")
    lines.append("")
    lines.append("## Run")
    lines.append("")
    lines.append(f"- Run ID: `{run_id}`")
    lines.append(f"- Target: `{DEFAULT_TARGET}`")
    lines.append(f"- Methods: `{', '.join(DEFAULT_METHODS)}`")
    lines.append(f"- Comparison target: {DEFAULT_COMPARISON_TARGET}")
    lines.append("")
    lines.append("## Datasets")
    lines.append("")
    for dataset in window_datasets + probe_datasets:
        lines.append(f"- `{dataset['dataset_id']}` (family `{dataset['family']}`, version `{dataset['version']}`)")
    lines.append("")
    lines.append("## Windows")
    lines.append("")
    for window in selected_windows:
        lines.append(f"- `{window.window_case_id}` ({window.window_kind}, chapters `{', '.join(window.chapter_case_ids)}`)")
    lines.append("")
    lines.append("## Selected Probes")
    lines.append("")
    for probe in selected_probes:
        target_membership = [name for name, ids in target_probe_ids.items() if probe.probe_id in ids]
        lines.append(f"- `{probe.probe_id}` (`{probe.output_language}`, targets `{', '.join(target_membership)}`)")
    lines.append("")
    lines.append("## Aggregate Findings")
    lines.append("")
    for target_name, summary in aggregate["target_summaries"].items():
        lines.append(f"### `{target_name}`")
        lines.append(f"- Cases: `{summary['case_count']}`")
        lines.append(f"- Winner counts: `{json.dumps(summary['winner_counts'], ensure_ascii=False, sort_keys=True)}`")
        lines.append(f"- Judge unavailable count: `{summary['judge_unavailable_count']}`")
        lines.append(f"- Mechanism failure count: `{summary['mechanism_failure_count']}`")
        lines.append(f"- Average scores: `{json.dumps(summary['average_scores'], ensure_ascii=False, sort_keys=True)}`")
        for language, language_summary in summary["language_summaries"].items():
            lines.append(
                f"- `{language}`: `{json.dumps({'case_count': language_summary['case_count'], 'winner_counts': language_summary['winner_counts'], 'judge_unavailable_count': language_summary['judge_unavailable_count'], 'average_scores': language_summary['average_scores']}, ensure_ascii=False, sort_keys=True)}`"
            )
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _prepare_selection(
    *,
    formal_manifest_path: Path,
    target_slice: str = "both",
    probe_ids: list[str] | None = None,
) -> AccumulationRunSelection:
    formal_manifest = _load_formal_manifest(formal_manifest_path)
    window_dataset_dirs = _window_dataset_dirs_from_manifest(formal_manifest)
    probe_dataset_dirs = _probe_dataset_dirs_from_manifest(formal_manifest)
    source_manifest_paths = _source_manifest_paths_from_manifest(formal_manifest)
    target_probe_ids = _target_probe_ids_from_manifest(formal_manifest, target_slice=target_slice)
    if probe_ids:
        wanted = set(probe_ids)
        target_probe_ids = {
            target_name: [probe_id for probe_id in ids if probe_id in wanted]
            for target_name, ids in target_probe_ids.items()
        }
    selected_probe_ids = _merge_probe_order(target_probe_ids)
    if not selected_probe_ids:
        raise ValueError("no accumulation probes selected")

    window_manifests, probe_manifests, selected_windows, selected_probes, _probe_index = _resolve_selected_windows_and_probes(
        window_dataset_dirs=window_dataset_dirs,
        probe_dataset_dirs=probe_dataset_dirs,
        selected_probe_ids=selected_probe_ids,
    )
    source_index = _load_source_index(source_manifest_paths)
    missing_sources = sorted({window.source_id for window in selected_windows if window.source_id not in source_index})
    if missing_sources:
        raise ValueError(f"missing source references: {', '.join(missing_sources)}")
    probes_by_window: dict[str, list[Probe]] = defaultdict(list)
    for probe in selected_probes:
        probes_by_window[probe.window_case_id].append(probe)
    return AccumulationRunSelection(
        window_manifests=window_manifests,
        probe_manifests=probe_manifests,
        selected_windows=selected_windows,
        selected_probes=selected_probes,
        target_probe_ids=target_probe_ids,
        source_index=source_index,
        source_manifest_paths=source_manifest_paths,
        probes_by_window=dict(probes_by_window),
        formal_manifest_path=formal_manifest_path,
    )


def _write_selection_metadata(
    *,
    run_root: Path,
    selection: AccumulationRunSelection,
    judge_mode: str,
    mechanism_execution_mode: str,
    judge_execution_mode: str,
) -> None:
    _json_dump(
        _selection_dataset_manifest_path(run_root),
        {
            "target": DEFAULT_TARGET,
            "methods": DEFAULT_METHODS,
            "comparison_target": DEFAULT_COMPARISON_TARGET,
            "window_dataset_ids": [manifest["dataset_id"] for manifest in selection.window_manifests],
            "probe_dataset_ids": [manifest["dataset_id"] for manifest in selection.probe_manifests],
            "selected_probe_ids": [probe.probe_id for probe in selection.selected_probes],
            "target_probe_ids": selection.target_probe_ids,
            "source_manifest_paths": [str(path) for path in selection.source_manifest_paths],
            "formal_manifest_path": str(selection.formal_manifest_path),
            "judge_mode": judge_mode,
            "mechanism_execution_mode": mechanism_execution_mode,
            "judge_execution_mode": judge_execution_mode,
            "generated_at": _timestamp(),
        },
    )
    _json_dump(
        _selection_windows_manifest_path(run_root),
        {
            "window_count": len(selection.selected_windows),
            "windows": [
                {
                    "window_case_id": window.window_case_id,
                    "source_id": window.source_id,
                    "probe_ids": [probe.probe_id for probe in selection.probes_by_window.get(window.window_case_id, [])],
                }
                for window in selection.selected_windows
            ],
        },
    )


def _filtered_windows(selection: AccumulationRunSelection, *, window_case_ids: list[str] | None) -> list[WindowCase]:
    if not window_case_ids:
        return list(selection.selected_windows)
    wanted = {item for item in window_case_ids if item}
    windows = [window for window in selection.selected_windows if window.window_case_id in wanted]
    if not windows:
        raise ValueError("no windows selected after --window-case-id filtering")
    return windows


def _document_for_source(
    *,
    source_id: str,
    selection: AccumulationRunSelection,
    output_language: str,
    cache: dict[str, ProvisionedBook],
    cache_lock: threading.Lock,
) -> BookDocument:
    with cache_lock:
        provisioned = cache.get(source_id)
        if provisioned is None:
            provisioned = ensure_canonical_parse(
                ROOT / str(selection.source_index[source_id]["relative_local_path"]),
                language_mode=output_language,
            )
            cache[source_id] = provisioned
    document = provisioned.book_document
    if document is None:
        raise ValueError(f"missing provisioned book document for source: {source_id}")
    return document


def _judge_probes_for_window(
    window: WindowCase,
    *,
    selection: AccumulationRunSelection,
    run_root: Path,
    shard_id: str,
    judge_mode: str,
    judge_execution_mode: str,
    skip_existing: bool,
    document_cache: dict[str, ProvisionedBook],
    document_cache_lock: threading.Lock,
) -> dict[str, dict[str, Any]]:
    unit_result = _build_window_result_from_existing_bundles(run_root=run_root, window=window)
    probes = selection.probes_by_window.get(window.window_case_id, [])
    results: dict[str, dict[str, Any]] = {}
    try:
        document = _document_for_source(
            source_id=window.source_id,
            selection=selection,
            output_language=window.output_language,
            cache=document_cache,
            cache_lock=document_cache_lock,
        )
    except Exception as exc:
        document = {}
        document_error = f"{type(exc).__name__}: {exc}"
    else:
        document_error = ""

    for probe in probes:
        probe_targets = [target_name for target_name, ids in selection.target_probe_ids.items() if probe.probe_id in ids]
        if skip_existing:
            existing = _existing_probe_payload(run_root, probe_id=probe.probe_id)
            if existing is not None and _probe_payload_covers_targets(existing[1], target_names=probe_targets):
                _log_probe_progress(probe, "[probe-skip-existing]")
                results[probe.probe_id] = existing[1]
                continue
        try:
            if document_error:
                raise ValueError(document_error)
            probe_result = _evaluate_probe(
                probe,
                probe_targets=probe_targets,
                window=window,
                unit_result=unit_result,
                document=document,
                run_root=run_root,
                judge_mode=judge_mode,
                judge_execution_mode=judge_execution_mode,
                shard_id=shard_id,
            )
        except Exception as exc:
            probe_result = _probe_failure_result(
                probe,
                probe_targets=probe_targets,
                window=window,
                unit_result=unit_result,
                error=f"{type(exc).__name__}: {exc}",
            )
        results[probe.probe_id] = probe_result
        _json_dump(_probe_payload_path(run_root, shard_id, probe.probe_id), probe_result)
    return results


def _write_shard_usage_summary(run_root: Path, *, shard_id: str) -> dict[str, Any]:
    return write_llm_usage_summary(
        run_root,
        summary_path=_shard_summary_dir(run_root, shard_id) / "llm_usage.json",
        shard_id=shard_id,
    )


def _merge_probe_results(
    *,
    run_root: Path,
    selection: AccumulationRunSelection,
    window_case_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    allowed = set(window_case_ids or [])
    results: list[dict[str, Any]] = []
    for probe in selection.selected_probes:
        if allowed and probe.window_case_id not in allowed:
            continue
        existing = _existing_probe_payload(run_root, probe_id=probe.probe_id)
        if existing is not None:
            results.append(existing[1])
    return results


def _write_merge_outputs(
    *,
    run_root: Path,
    run_name: str,
    selection: AccumulationRunSelection,
    probe_results: list[dict[str, Any]],
) -> tuple[dict[str, Any], Path]:
    target_names = list(selection.target_probe_ids.keys())
    aggregate = _aggregate(probe_results, target_names=target_names)
    _json_dump(run_root / "summary" / "aggregate.json", aggregate)
    _jsonl_dump(run_root / "summary" / "case_results.jsonl", probe_results)
    report_path = run_root / "summary" / "report.md"
    report_path.write_text(
        _build_markdown_report(
            run_id=run_name,
            selected_windows=selection.selected_windows,
            selected_probes=selection.selected_probes,
            target_probe_ids=selection.target_probe_ids,
            aggregate=aggregate,
            window_datasets=selection.window_manifests,
            probe_datasets=selection.probe_manifests,
        ),
        encoding="utf-8",
    )
    write_llm_usage_summary(run_root, summary_path=run_root / "summary" / "llm_usage.json")
    return aggregate, report_path


def run_benchmark(
    *,
    formal_manifest_path: Path,
    runs_root: Path,
    target_slice: str = "both",
    probe_ids: list[str] | None = None,
    judge_mode: str = "llm",
    mechanism_execution_mode: str = "parallel",
    judge_execution_mode: str = "serial",
    case_workers: int | None = None,
    run_id: str | None = None,
    stage: str = "all",
    shard_id: str = "default",
    window_case_ids: list[str] | None = None,
    mechanism_filter: str = "both",
    skip_existing: bool = False,
    unit_workers: int | None = None,
    judge_workers: int | None = None,
) -> dict[str, Any]:
    if stage not in STAGE_VALUES:
        raise ValueError(f"unsupported stage: {stage}")
    if case_workers and unit_workers is None:
        unit_workers = case_workers

    run_name = run_id or datetime.now(timezone.utc).strftime("attentional_v2_vs_iterator_v1_accumulation_comparison_%Y%m%d-%H%M%S")
    run_root = runs_root / run_name
    run_root.mkdir(parents=True, exist_ok=True)

    selection = _prepare_selection(
        formal_manifest_path=formal_manifest_path,
        target_slice=target_slice,
        probe_ids=probe_ids,
    )
    _write_selection_metadata(
        run_root=run_root,
        selection=selection,
        judge_mode=judge_mode,
        mechanism_execution_mode=mechanism_execution_mode,
        judge_execution_mode=judge_execution_mode,
    )
    windows = _filtered_windows(selection, window_case_ids=window_case_ids)

    summary: dict[str, Any] = {
        "run_id": run_name,
        "run_root": str(run_root),
        "stage": stage,
        "shard_id": shard_id,
        "selected_window_count": len(windows),
    }

    if stage == "merge":
        probe_results = _merge_probe_results(
            run_root=run_root,
            selection=selection,
            window_case_ids=[window.window_case_id for window in windows] if window_case_ids else None,
        )
        aggregate, report_path = _write_merge_outputs(
            run_root=run_root,
            run_name=run_name,
            selection=selection,
            probe_results=probe_results,
        )
        summary["aggregate"] = aggregate
        summary["report_path"] = str(report_path)
        return summary

    document_cache: dict[str, ProvisionedBook] = {}
    document_cache_lock = threading.Lock()

    if stage == "judge":
        judge_policy = resolve_worker_policy(
            job_kind="accumulation_probe_judge",
            profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
            task_count=len(windows),
            per_worker_parallelism=1,
            explicit_max_workers=judge_workers if judge_workers and judge_workers > 0 else None,
        )
        results_by_probe_id: dict[str, dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=max(1, judge_policy.worker_count), thread_name_prefix="accumulation-judge-window") as executor:
            future_to_window = {
                submit_inherited_context(
                    executor,
                    _judge_probes_for_window,
                    window,
                    selection=selection,
                    run_root=run_root,
                    shard_id=shard_id,
                    judge_mode=judge_mode,
                    judge_execution_mode=judge_execution_mode,
                    skip_existing=skip_existing,
                    document_cache=document_cache,
                    document_cache_lock=document_cache_lock,
                ): window
                for window in windows
            }
            for future in as_completed(future_to_window):
                window = future_to_window[future]
                try:
                    results_by_probe_id.update(future.result())
                except Exception as exc:
                    unit_result = _build_window_result_from_existing_bundles(run_root=run_root, window=window)
                    for probe in selection.probes_by_window.get(window.window_case_id, []):
                        probe_targets = [target_name for target_name, ids in selection.target_probe_ids.items() if probe.probe_id in ids]
                        failure = _probe_failure_result(
                            probe,
                            probe_targets=probe_targets,
                            window=window,
                            unit_result=unit_result,
                            error=f"{type(exc).__name__}: {exc}",
                        )
                        results_by_probe_id[probe.probe_id] = failure
                        _json_dump(_probe_payload_path(run_root, shard_id, probe.probe_id), failure)
        summary["probe_count"] = len(results_by_probe_id)
        summary["llm_usage"] = _write_shard_usage_summary(run_root, shard_id=shard_id)
        return summary

    per_worker_parallelism = len(_mechanism_keys_for_filter(mechanism_filter)) if mechanism_execution_mode == "parallel" else 1
    worker_policy = resolve_worker_policy(
        job_kind="accumulation_window_bundle",
        profile_id=DEFAULT_RUNTIME_PROFILE_ID,
        task_count=len(windows),
        per_worker_parallelism=per_worker_parallelism,
        explicit_max_workers=unit_workers if unit_workers and unit_workers > 0 else None,
    )
    window_runner = _run_window_subprocess if worker_policy.worker_count > 1 else _run_window_bundle
    window_results: dict[str, dict[str, Any]] = {}

    if stage == "bundle":
        with ThreadPoolExecutor(max_workers=max(1, worker_policy.worker_count), thread_name_prefix="accumulation-window") as executor:
            future_to_window: dict[Any, WindowCase] = {}
            for index, window in enumerate(windows, start=1):
                print(f"[submitted {index}/{len(windows)}] {window.window_case_id}", flush=True)
                future = submit_inherited_context(
                    executor,
                    window_runner,
                    window,
                    source=selection.source_index[window.source_id],
                    run_root=run_root,
                    shard_id=shard_id,
                    mechanism_execution_mode=mechanism_execution_mode,
                    mechanism_filter=mechanism_filter,
                    skip_existing=skip_existing,
                )
                future_to_window[future] = window
            for future in as_completed(future_to_window):
                window = future_to_window[future]
                try:
                    payload = future.result()
                except Exception as exc:
                    payload = _window_result_payload(
                        window,
                        mechanisms={
                            mechanism_key: _mechanism_failure_payload(mechanism_key, error=str(exc))
                            for mechanism_key in MECHANISM_KEYS
                        },
                    )
                window_results[payload["window_case_id"]] = payload
                _json_dump(_window_payload_path(run_root, shard_id, payload["window_case_id"]), payload)
                print(f"[completed] {payload['window_case_id']}", flush=True)
        summary["window_count"] = len(window_results)
        summary["llm_usage"] = _write_shard_usage_summary(run_root, shard_id=shard_id)
        return summary

    judge_policy = resolve_worker_policy(
        job_kind="accumulation_probe_judge",
        profile_id=DEFAULT_EVAL_JUDGE_PROFILE_ID,
        task_count=len(windows),
        per_worker_parallelism=1,
        explicit_max_workers=judge_workers if judge_workers and judge_workers > 0 else None,
    )
    results_by_probe_id: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=max(1, worker_policy.worker_count), thread_name_prefix="accumulation-window") as bundle_executor, ThreadPoolExecutor(
        max_workers=max(1, judge_policy.worker_count),
        thread_name_prefix="accumulation-judge-window",
    ) as judge_executor:
        future_to_window: dict[Any, WindowCase] = {}
        judge_futures: dict[Any, WindowCase] = {}
        for index, window in enumerate(windows, start=1):
            print(f"[submitted {index}/{len(windows)}] {window.window_case_id}", flush=True)
            future = submit_inherited_context(
                bundle_executor,
                window_runner,
                window,
                source=selection.source_index[window.source_id],
                run_root=run_root,
                shard_id=shard_id,
                mechanism_execution_mode=mechanism_execution_mode,
                mechanism_filter=mechanism_filter,
                skip_existing=skip_existing,
            )
            future_to_window[future] = window
        for future in as_completed(future_to_window):
            window = future_to_window[future]
            try:
                payload = future.result()
            except Exception as exc:
                payload = _window_result_payload(
                    window,
                    mechanisms={
                        mechanism_key: _mechanism_failure_payload(mechanism_key, error=str(exc))
                        for mechanism_key in MECHANISM_KEYS
                    },
                )
            window_results[payload["window_case_id"]] = payload
            _json_dump(_window_payload_path(run_root, shard_id, payload["window_case_id"]), payload)
            print(f"[completed] {payload['window_case_id']}", flush=True)
            judge_future = submit_inherited_context(
                judge_executor,
                _judge_probes_for_window,
                window,
                selection=selection,
                run_root=run_root,
                shard_id=shard_id,
                judge_mode=judge_mode,
                judge_execution_mode=judge_execution_mode,
                skip_existing=skip_existing,
                document_cache=document_cache,
                document_cache_lock=document_cache_lock,
            )
            judge_futures[judge_future] = window
        for future in as_completed(judge_futures):
            window = judge_futures[future]
            try:
                results_by_probe_id.update(future.result())
            except Exception as exc:
                unit_result = window_results.get(window.window_case_id) or _build_window_result_from_existing_bundles(run_root=run_root, window=window)
                for probe in selection.probes_by_window.get(window.window_case_id, []):
                    probe_targets = [target_name for target_name, ids in selection.target_probe_ids.items() if probe.probe_id in ids]
                    failure = _probe_failure_result(
                        probe,
                        probe_targets=probe_targets,
                        window=window,
                        unit_result=unit_result,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    results_by_probe_id[probe.probe_id] = failure
                    _json_dump(_probe_payload_path(run_root, shard_id, probe.probe_id), failure)
    summary["window_count"] = len(window_results)
    summary["probe_count"] = len(results_by_probe_id)
    summary["llm_usage"] = _write_shard_usage_summary(run_root, shard_id=shard_id)
    return summary


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--formal-manifest", default=str(DEFAULT_FORMAL_MANIFEST))
    parser.add_argument("--runs-root", default=str(DEFAULT_RUNS_ROOT))
    parser.add_argument("--run-id", default="")
    parser.add_argument("--stage", choices=STAGE_VALUES, default="all")
    parser.add_argument("--shard-id", default="default")
    parser.add_argument("--target-slice", choices=TARGET_SLICE_VALUES, default="both")
    parser.add_argument("--judge-mode", choices=["llm", "none"], default="llm")
    parser.add_argument("--mechanism-execution-mode", choices=["serial", "parallel"], default="parallel")
    parser.add_argument("--judge-execution-mode", choices=["serial", "parallel"], default="serial")
    parser.add_argument("--mechanism-filter", choices=MECHANISM_FILTER_VALUES, default="both")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--unit-workers", type=int, default=0)
    parser.add_argument("--judge-workers", type=int, default=0)
    parser.add_argument("--case-workers", type=int, default=0)
    parser.add_argument("--window-case-id", action="append", default=[])
    parser.add_argument("--probe-id", action="append", default=[])
    parser.add_argument("--probe-ids", default="")
    parser.add_argument("--worker-payload", default="", help=argparse.SUPPRESS)
    parser.add_argument("--worker-result", default="", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    if args.worker_payload:
        if not args.worker_result:
            raise ValueError("--worker-result is required when --worker-payload is set")
        return _run_payload_worker(Path(args.worker_payload).resolve(), Path(args.worker_result).resolve())
    window_case_ids = [item.strip() for item in args.window_case_id if item.strip()]
    probe_ids = [item.strip() for item in args.probe_id if _clean_text(item)]
    if args.probe_ids:
        probe_ids.extend([item.strip() for item in str(args.probe_ids).split(",") if item.strip()])
    summary = run_benchmark(
        formal_manifest_path=Path(args.formal_manifest).resolve(),
        runs_root=Path(args.runs_root).resolve(),
        run_id=args.run_id or None,
        stage=args.stage,
        shard_id=args.shard_id,
        target_slice=args.target_slice,
        probe_ids=probe_ids or None,
        judge_mode=args.judge_mode,
        mechanism_execution_mode=args.mechanism_execution_mode,
        judge_execution_mode=args.judge_execution_mode,
        case_workers=args.case_workers or None,
        window_case_ids=window_case_ids or None,
        mechanism_filter=args.mechanism_filter,
        skip_existing=bool(args.skip_existing),
        unit_workers=args.unit_workers or None,
        judge_workers=args.judge_workers or None,
    )
    print(json.dumps(summary.get("aggregate", summary), ensure_ascii=False, indent=2))
    print(f"run_root={summary['run_root']}")
    if summary.get("report_path"):
        print(f"report_path={summary['report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
