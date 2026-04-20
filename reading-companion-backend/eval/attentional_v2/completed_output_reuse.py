"""Shared helpers for rebuilding normalized bundles from completed reading outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.attentional_v2.evaluation import build_normalized_eval_bundle as build_attentional_v2_normalized_eval_bundle
from src.iterator_reader.storage import existing_structure_file, load_json as load_iterator_json, load_structure
from src.reading_mechanisms.iterator_v1 import _normalized_eval_bundle as build_iterator_v1_normalized_eval_bundle


def run_state_status(output_dir: Path) -> str:
    run_state_path = output_dir / "_runtime" / "run_state.json"
    if not run_state_path.exists():
        return ""
    payload = load_iterator_json(run_state_path)
    return str(payload.get("status") or payload.get("stage") or "")


def rebuild_normalized_bundle_from_completed_output(
    *,
    mechanism_key: str,
    source_output_dir: Path,
    segment_id: str,
) -> dict[str, Any]:
    """Rebuild one normalized eval bundle from an existing completed reading output."""

    if not source_output_dir.exists():
        raise FileNotFoundError(f"reuse output dir does not exist: {source_output_dir}")
    status = run_state_status(source_output_dir)
    if status != "completed":
        raise RuntimeError(f"reuse output dir is not completed: {source_output_dir} status={status or 'missing'}")

    if mechanism_key == "attentional_v2":
        bundle = build_attentional_v2_normalized_eval_bundle(source_output_dir)
        mechanism_label = "Attentional V2 scaffold (Phase 1-8)"
    elif mechanism_key == "iterator_v1":
        structure = load_structure(existing_structure_file(source_output_dir))
        bundle = build_iterator_v1_normalized_eval_bundle(
            output_dir=source_output_dir,
            structure=structure,
            config_payload={"reuse_output_dir": str(source_output_dir), "segment_id": segment_id},
        )
        mechanism_label = "Current Iterator-Reader implementation"
    else:
        raise ValueError(f"unsupported mechanism for reuse output: {mechanism_key}")

    return {
        "mechanism_label": mechanism_label,
        "normalized_eval_bundle": bundle,
    }
