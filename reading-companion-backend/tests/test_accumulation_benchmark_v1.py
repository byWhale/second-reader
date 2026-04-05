from __future__ import annotations

import json
from pathlib import Path

from eval.attentional_v2.accumulation_benchmark_v1 import (
    DRAFT_MANIFEST_PATH,
    PROBE_DRAFT_DATASET_DIR,
    PROBE_FROZEN_DATASET_DIR,
    WINDOW_DATASET_DIR,
    build_draft_manifest_payload,
    build_probe_rows,
    build_window_rows,
    freeze_probe_rows,
    write_frozen_probe_dataset,
    write_draft_artifacts,
)
from eval.attentional_v2.run_accumulation_comparison import _target_probe_ids_from_manifest


def test_build_window_rows_matches_expected_v1_windows() -> None:
    rows = build_window_rows()
    ids = [row["window_case_id"] for row in rows]

    assert ids == [
        "supremacy_private_en__13",
        "steve_jobs_private_en__17",
        "value_of_others_private_en__8_10",
        "xidaduo_private_zh__13_15",
        "huochu_shengming_de_yiyi_private_zh__8",
        "huochu_shengming_de_yiyi_private_zh__13_16",
    ]
    assert all(bool(row["contiguous_chapters"]) for row in rows)
    assert sum(1 for row in rows if row["window_kind"] == "cross_chapter") == 3
    assert all(bool(row["output_language"]) for row in rows)
    assert all(bool(row["benchmark_line"]) for row in rows)
    assert all(bool(row["selection_reason"]) for row in rows)
    assert all(int(row["sentence_count"]) > 0 for row in rows)


def test_build_probe_rows_is_bounded_and_grouped_per_window() -> None:
    probe_rows = build_probe_rows()
    counts: dict[str, int] = {}
    for row in probe_rows:
        counts[row["window_case_id"]] = counts.get(row["window_case_id"], 0) + 1

    assert [row["probe_id"] for row in probe_rows] == [
        "huochu_shengming_de_yiyi_private_zh__13_16__probe_1",
        "huochu_shengming_de_yiyi_private_zh__13_16__probe_2",
        "huochu_shengming_de_yiyi_private_zh__8__probe_1",
        "huochu_shengming_de_yiyi_private_zh__8__probe_2",
        "steve_jobs_private_en__17__probe_1",
        "supremacy_private_en__13__probe_1",
        "value_of_others_private_en__8_10__probe_1",
        "xidaduo_private_zh__13_15__probe_1",
        "xidaduo_private_zh__13_15__probe_2",
    ]
    assert counts == {
        "huochu_shengming_de_yiyi_private_zh__13_16": 2,
        "huochu_shengming_de_yiyi_private_zh__8": 2,
        "steve_jobs_private_en__17": 1,
        "supremacy_private_en__13": 1,
        "value_of_others_private_en__8_10": 1,
        "xidaduo_private_zh__13_15": 2,
    }
    assert all(len(row["anchor_refs"]) >= 2 for row in probe_rows)
    assert all(bool(row["start_sentence_id"]) for row in probe_rows)
    assert all(bool(row["end_sentence_id"]) for row in probe_rows)
    assert all(bool(row["case_title"]) for row in probe_rows)
    assert all(bool(row["selection_role"]) for row in probe_rows)
    assert all(bool(row["chapter_title"]) for row in probe_rows)
    assert any(row["note_provenance"] for row in probe_rows)
    assert any(int(row["support_excerpt_case_count"]) == 0 for row in probe_rows)
    assert any(int(row["support_excerpt_case_count"]) >= 2 for row in probe_rows)


def test_freeze_probe_rows_keeps_repaired_short_budgets_without_review() -> None:
    frozen_rows, saturation = freeze_probe_rows(build_probe_rows())

    assert len(frozen_rows) == 9
    assert saturation["huochu_shengming_de_yiyi_private_zh__13_16"]["selected_count"] == 2
    assert saturation["huochu_shengming_de_yiyi_private_zh__8"]["selected_count"] == 2
    assert saturation["steve_jobs_private_en__17"]["selected_count"] == 1
    assert saturation["supremacy_private_en__13"]["selected_count"] == 1
    assert saturation["value_of_others_private_en__8_10"]["selected_count"] == 1
    assert saturation["xidaduo_private_zh__13_15"]["selected_count"] == 2
    assert saturation["steve_jobs_private_en__17"]["saturation_reason"] == "honest_short_repaired_probe_budget"
    assert all(
        row["freeze_metadata"]["freeze_reason"] == "builder_curated_fallback"
        for row in frozen_rows
    )


def test_write_draft_artifacts_writes_local_datasets_and_manifest() -> None:
    summary = write_draft_artifacts()

    assert summary["window_count"] == 6
    assert summary["probe_count"] == 9
    assert (WINDOW_DATASET_DIR / "manifest.json").exists()
    assert (WINDOW_DATASET_DIR / "windows.jsonl").exists()
    assert (PROBE_DRAFT_DATASET_DIR / "manifest.json").exists()
    assert (PROBE_DRAFT_DATASET_DIR / "probes.jsonl").exists()
    assert Path(summary["draft_manifest_path"]).exists()

    manifest = build_draft_manifest_payload()
    assert manifest["quota_status"]["window_cases"]["ready_now"] == 6
    assert manifest["quota_status"]["accumulation_probes"]["target_total"] == 9
    assert manifest["quota_status"]["accumulation_probes"]["ready_now"] == 9
    assert manifest["splits"]["accumulation_probes_frozen_draft"]["all"]
    assert manifest["splits"]["insight_and_clarification_subset_frozen_draft"]["all"]


def test_draft_manifest_resolves_probe_ids_for_runner_target_slices() -> None:
    manifest = build_draft_manifest_payload()

    selected = _target_probe_ids_from_manifest(manifest, target_slice="both")

    assert len(selected["coherent_accumulation"]) == 9
    assert len(selected["insight_and_clarification"]) == 9


def test_write_frozen_probe_dataset_updates_manifest_to_frozen_probe_dataset() -> None:
    write_draft_artifacts()
    summary = write_frozen_probe_dataset()

    assert summary["probe_count"] == 9
    assert (PROBE_FROZEN_DATASET_DIR / "manifest.json").exists()
    assert (PROBE_FROZEN_DATASET_DIR / "probes.jsonl").exists()

    manifest = json.loads(Path(DRAFT_MANIFEST_PATH).read_text(encoding="utf-8"))
    assert manifest["source_refs"]["accumulation_probe_datasets"] == [
        "state/eval_local_datasets/accumulation_probes/attentional_v2_accumulation_benchmark_v1_probes_frozen_draft"
    ]
    assert len(manifest["splits"]["accumulation_probes_frozen_draft"]["all"]) == 9
    assert manifest["splits"]["insight_and_clarification_subset_frozen_draft"]["all"]
