"""Validate the secondary notes-guided excerpt eval manifest."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "eval" / "manifests" / "splits" / "attentional_v2_human_notes_guided_excerpt_eval_v1_draft.json"
)
DATASET_DIRS = (
    ROOT
    / "state"
    / "eval_local_datasets"
    / "excerpt_cases"
    / "attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404",
    ROOT
    / "state"
    / "eval_local_datasets"
    / "excerpt_cases"
    / "attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_complete_20260404",
)


def _load_cases(dataset_dir: Path) -> list[dict[str, object]]:
    manifest = json.loads((dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    primary_file = dataset_dir / str(manifest["primary_file"])
    return [
        json.loads(line)
        for line in primary_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_notes_guided_excerpt_eval_manifest_matches_reviewed_freeze_counts() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for dataset_dir in DATASET_DIRS:
        rows.extend(_load_cases(dataset_dir))

    all_ids = [str(row["case_id"]) for row in rows]
    subset_ids = [
        str(row["case_id"])
        for row in rows
        if str(row.get("target_profile_id", "")) in {"distinction_definition", "tension_reversal", "callback_bridge"}
    ]

    assert payload["quota_status"]["excerpt_primary"]["ready_now"] == 55
    assert payload["quota_status"]["insight_and_clarification_subset"]["ready_now"] == 38
    manifest_all_ids = payload["splits"]["excerpt_core_primary_frozen_draft"]["all"]
    manifest_subset_ids = payload["splits"]["insight_and_clarification_subset_frozen_draft"]["all"]

    assert len(manifest_all_ids) == len(all_ids)
    assert len(set(manifest_all_ids)) == len(manifest_all_ids)
    assert set(manifest_all_ids) == set(all_ids)

    assert len(manifest_subset_ids) == len(subset_ids)
    assert len(set(manifest_subset_ids)) == len(manifest_subset_ids)
    assert set(manifest_subset_ids) == set(subset_ids)
    assert set(manifest_subset_ids).issubset(set(manifest_all_ids))


def test_notes_guided_excerpt_eval_manifest_uses_reviewed_freeze_datasets_only() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    dataset_paths = payload["source_refs"]["excerpt_case_datasets"]

    assert len(dataset_paths) == 2
    assert all("__scratch__" not in str(path) for path in dataset_paths)
    assert any(str(path).endswith("attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404") for path in dataset_paths)
    assert any(
        str(path).endswith("attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_complete_20260404")
        for path in dataset_paths
    )
