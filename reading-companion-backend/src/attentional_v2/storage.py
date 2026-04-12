"""Artifact and state helpers for the attentional_v2 mechanism."""

from __future__ import annotations

import json
from pathlib import Path

from src.reading_runtime import artifacts as runtime_artifacts
from src.reading_runtime.shell_state import build_checkpoint_summary, ensure_runtime_shell, write_checkpoint_summary

from .schemas import (
    ATTENTIONAL_V2_MECHANISM_VERSION,
    ATTENTIONAL_V2_POLICY_VERSION,
    ATTENTIONAL_V2_SCHEMA_VERSION,
    build_default_reader_policy,
    build_empty_anchor_memory,
    build_empty_local_buffer,
    build_empty_local_continuity,
    build_empty_knowledge_activations,
    build_empty_move_history,
    build_empty_reaction_records,
    build_empty_reconsolidation_records,
    build_empty_reflective_summaries,
    build_empty_resume_metadata,
    build_empty_trigger_state,
    build_empty_working_pressure,
)


ATTENTIONAL_V2_MECHANISM_KEY = "attentional_v2"


def derived_dir(output_dir: Path) -> Path:
    """Return the mechanism-owned derived-artifact directory."""

    return runtime_artifacts.mechanism_derived_dir(output_dir, ATTENTIONAL_V2_MECHANISM_KEY)


def runtime_dir(output_dir: Path) -> Path:
    """Return the mechanism-owned runtime-state directory."""

    return runtime_artifacts.mechanism_runtime_dir(output_dir, ATTENTIONAL_V2_MECHANISM_KEY)


def internal_dir(output_dir: Path) -> Path:
    """Return the mechanism-owned internal-artifact directory."""

    return runtime_artifacts.mechanism_internal_dir(output_dir, ATTENTIONAL_V2_MECHANISM_KEY)


def diagnostics_dir(output_dir: Path) -> Path:
    """Return the mechanism-owned diagnostics directory."""

    return runtime_artifacts.mechanism_internal_diagnostics_dir(output_dir, ATTENTIONAL_V2_MECHANISM_KEY)


def prompt_manifests_dir(output_dir: Path) -> Path:
    """Return the directory for node-level prompt manifests."""

    return internal_dir(output_dir) / "prompt_manifests"


def checkpoints_dir(output_dir: Path) -> Path:
    """Return the mechanism-owned full-checkpoint directory."""

    return runtime_dir(output_dir) / "checkpoints"


def survey_map_file(output_dir: Path) -> Path:
    """Return the future survey-map artifact path."""

    return derived_dir(output_dir) / "survey_map.json"


def revisit_index_file(output_dir: Path) -> Path:
    """Return the future revisit-index artifact path."""

    return derived_dir(output_dir) / "revisit_index.json"


def working_pressure_file(output_dir: Path) -> Path:
    """Return the current working-pressure path."""

    return runtime_dir(output_dir) / "working_pressure.json"


def local_buffer_file(output_dir: Path) -> Path:
    """Return the rolling local-buffer path."""

    return runtime_dir(output_dir) / "local_buffer.json"


def trigger_state_file(output_dir: Path) -> Path:
    """Return the cheap trigger-state path."""

    return runtime_dir(output_dir) / "trigger_state.json"


def local_continuity_file(output_dir: Path) -> Path:
    """Return the compact continuity-state path used for checkpointing and resume."""

    return runtime_dir(output_dir) / "local_continuity.json"


def anchor_memory_file(output_dir: Path) -> Path:
    """Return the anchor-memory path."""

    return runtime_dir(output_dir) / "anchor_memory.json"


def reflective_summaries_file(output_dir: Path) -> Path:
    """Return the reflective-summaries path."""

    return runtime_dir(output_dir) / "reflective_summaries.json"


def knowledge_activations_file(output_dir: Path) -> Path:
    """Return the knowledge-activations path."""

    return runtime_dir(output_dir) / "knowledge_activations.json"


def move_history_file(output_dir: Path) -> Path:
    """Return the move-history path."""

    return runtime_dir(output_dir) / "move_history.json"


def reaction_records_file(output_dir: Path) -> Path:
    """Return the durable anchored-reaction ledger path."""

    return runtime_dir(output_dir) / "reaction_records.json"


def reconsolidation_records_file(output_dir: Path) -> Path:
    """Return the reconsolidation-records path."""

    return runtime_dir(output_dir) / "reconsolidation_records.json"


def reader_policy_file(output_dir: Path) -> Path:
    """Return the reader-policy path."""

    return runtime_dir(output_dir) / "reader_policy.json"


def resume_metadata_file(output_dir: Path) -> Path:
    """Return the resume-metadata path."""

    return runtime_dir(output_dir) / "resume_metadata.json"


def full_checkpoint_file(output_dir: Path, checkpoint_id: str) -> Path:
    """Return one mechanism-owned full-checkpoint path."""

    slug = str(checkpoint_id or "").strip() or "latest"
    return checkpoints_dir(output_dir) / f"{slug}.json"


def event_stream_file(output_dir: Path) -> Path:
    """Return the mechanism-private deep event-stream path."""

    return diagnostics_dir(output_dir) / "events.jsonl"


def unitization_audit_file(output_dir: Path) -> Path:
    """Return the mechanism-private unitization-audit stream path."""

    return runtime_dir(output_dir) / "unitization_audit.jsonl"


def read_audit_file(output_dir: Path) -> Path:
    """Return the mechanism-private read-audit stream path."""

    return runtime_dir(output_dir) / "read_audit.jsonl"


def prompt_manifest_file(output_dir: Path, node_name: str) -> Path:
    """Return one node-level prompt-manifest path."""

    slug = str(node_name or "").strip() or "unknown"
    return prompt_manifests_dir(output_dir) / f"{slug}.json"


def chapter_result_compatibility_file(output_dir: Path, chapter_id: int) -> Path:
    """Return one mechanism-private current-contract compatibility chapter payload path."""

    return derived_dir(output_dir) / "chapter_result_compatibility" / f"chapter-{int(chapter_id):03d}.json"


def normalized_eval_bundle_file(output_dir: Path) -> Path:
    """Return the explicit normalized eval export path for eval runs."""

    return runtime_artifacts.mechanism_export_file(output_dir, ATTENTIONAL_V2_MECHANISM_KEY, "normalized_eval_bundle.json")


def artifact_map(output_dir: Path) -> dict[str, str]:
    """Return the Phase 1 artifact map relative to one output directory."""

    return {
        "runtime_shell": str(runtime_artifacts.runtime_shell_file(output_dir).relative_to(output_dir)),
        "shared_checkpoint_summaries": str(runtime_artifacts.checkpoint_summaries_dir(output_dir).relative_to(output_dir)),
        "survey_map": str(survey_map_file(output_dir).relative_to(output_dir)),
        "revisit_index": str(revisit_index_file(output_dir).relative_to(output_dir)),
        "local_buffer": str(local_buffer_file(output_dir).relative_to(output_dir)),
        "trigger_state": str(trigger_state_file(output_dir).relative_to(output_dir)),
        "local_continuity": str(local_continuity_file(output_dir).relative_to(output_dir)),
        "working_pressure": str(working_pressure_file(output_dir).relative_to(output_dir)),
        "anchor_memory": str(anchor_memory_file(output_dir).relative_to(output_dir)),
        "reflective_summaries": str(reflective_summaries_file(output_dir).relative_to(output_dir)),
        "knowledge_activations": str(knowledge_activations_file(output_dir).relative_to(output_dir)),
        "move_history": str(move_history_file(output_dir).relative_to(output_dir)),
        "reaction_records": str(reaction_records_file(output_dir).relative_to(output_dir)),
        "reconsolidation_records": str(reconsolidation_records_file(output_dir).relative_to(output_dir)),
        "reader_policy": str(reader_policy_file(output_dir).relative_to(output_dir)),
        "resume_metadata": str(resume_metadata_file(output_dir).relative_to(output_dir)),
        "chapter_result_compatibility": str(chapter_result_compatibility_file(output_dir, 1).parent.relative_to(output_dir)),
        "normalized_eval_bundle": str(normalized_eval_bundle_file(output_dir).relative_to(output_dir)),
        "full_checkpoints": str(checkpoints_dir(output_dir).relative_to(output_dir)),
        "event_stream": str(event_stream_file(output_dir).relative_to(output_dir)),
        "debug_event_stream": str(event_stream_file(output_dir).relative_to(output_dir)),
        "read_audit": str(read_audit_file(output_dir).relative_to(output_dir)),
        "prompt_manifests": str(prompt_manifests_dir(output_dir).relative_to(output_dir)),
    }


def save_json(path: Path, payload: object) -> None:
    """Write one UTF-8 JSON artifact."""

    runtime_artifacts.ensure_mechanism_manifest_for_artifact_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_json(path: Path, payload: object) -> None:
    """Persist one JSON artifact only when it does not already exist."""

    if path.exists():
        return
    save_json(path, payload)


def load_json(path: Path) -> dict[str, object]:
    """Load one JSON dictionary artifact."""

    return json.loads(path.read_text(encoding="utf-8"))


def append_jsonl(path: Path, payload: object) -> None:
    """Append one UTF-8 JSONL line."""

    runtime_artifacts.ensure_mechanism_manifest_for_artifact_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False))
        file.write("\n")


def initialize_artifact_tree(
    output_dir: Path,
    *,
    mechanism_version: str = ATTENTIONAL_V2_MECHANISM_VERSION,
    policy_version: str = ATTENTIONAL_V2_POLICY_VERSION,
) -> dict[str, object]:
    """Initialize the shared shell and mechanism-private Phase 1 artifacts."""

    runtime_artifacts.ensure_mechanism_manifest(output_dir, ATTENTIONAL_V2_MECHANISM_KEY)
    reader_policy = build_default_reader_policy(
        mechanism_version=mechanism_version,
        policy_version=policy_version,
    )
    observability_mode = str(reader_policy.get("logging", {}).get("observability_mode", "standard") or "standard")
    ensure_runtime_shell(
        output_dir,
        mechanism_key=ATTENTIONAL_V2_MECHANISM_KEY,
        mechanism_version=mechanism_version,
        policy_version=policy_version,
        observability_mode="debug" if observability_mode == "debug" else "standard",
    )
    write_checkpoint_summary(
        output_dir,
        build_checkpoint_summary(
            checkpoint_id="bootstrap",
            mechanism_key=ATTENTIONAL_V2_MECHANISM_KEY,
            mechanism_version=mechanism_version,
            policy_version=policy_version,
            observability_mode="debug" if observability_mode == "debug" else "standard",
        ),
    )
    ensure_json(
        survey_map_file(output_dir),
        {
            "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
            "mechanism_version": mechanism_version,
            "status": "not_started",
            "chapters": [],
        },
    )
    ensure_json(
        revisit_index_file(output_dir),
        {
            "schema_version": ATTENTIONAL_V2_SCHEMA_VERSION,
            "mechanism_version": mechanism_version,
            "anchors": {},
            "motifs": {},
        },
    )
    ensure_json(local_buffer_file(output_dir), build_empty_local_buffer(mechanism_version=mechanism_version))
    ensure_json(trigger_state_file(output_dir), build_empty_trigger_state(mechanism_version=mechanism_version))
    ensure_json(local_continuity_file(output_dir), build_empty_local_continuity(mechanism_version=mechanism_version))
    ensure_json(working_pressure_file(output_dir), build_empty_working_pressure(mechanism_version=mechanism_version))
    ensure_json(anchor_memory_file(output_dir), build_empty_anchor_memory(mechanism_version=mechanism_version))
    ensure_json(
        reflective_summaries_file(output_dir),
        build_empty_reflective_summaries(mechanism_version=mechanism_version),
    )
    ensure_json(
        knowledge_activations_file(output_dir),
        build_empty_knowledge_activations(mechanism_version=mechanism_version),
    )
    ensure_json(move_history_file(output_dir), build_empty_move_history(mechanism_version=mechanism_version))
    ensure_json(reaction_records_file(output_dir), build_empty_reaction_records(mechanism_version=mechanism_version))
    ensure_json(
        reconsolidation_records_file(output_dir),
        build_empty_reconsolidation_records(mechanism_version=mechanism_version),
    )
    ensure_json(
        reader_policy_file(output_dir),
        reader_policy,
    )
    ensure_json(
        resume_metadata_file(output_dir),
        build_empty_resume_metadata(
            mechanism_version=mechanism_version,
            policy_version=policy_version,
        ),
    )
    event_stream_file(output_dir).parent.mkdir(parents=True, exist_ok=True)
    if not event_stream_file(output_dir).exists():
        event_stream_file(output_dir).write_text("", encoding="utf-8")
    return {
        "mechanism_key": ATTENTIONAL_V2_MECHANISM_KEY,
        "mechanism_version": mechanism_version,
        "policy_version": policy_version,
        "artifact_map": artifact_map(output_dir),
    }
