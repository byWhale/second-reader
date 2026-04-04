from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from eval.attentional_v2 import freeze_reviewed_dataset_slice as module


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_main_filters_reviewed_slice_by_selection_group_id(tmp_path: Path, monkeypatch) -> None:
    local_root = tmp_path / "state" / "eval_local_datasets"
    source_dir = local_root / "excerpt_cases" / "source_dataset"
    _write_json(
        source_dir / "manifest.json",
        {
            "dataset_id": "source_dataset",
            "family": "excerpt_cases",
            "storage_mode": "local-only",
            "primary_file": "cases.jsonl",
        },
    )
    _write_jsonl(
        source_dir / "cases.jsonl",
        [
            {
                "case_id": "case_keep_g1",
                "benchmark_status": "reviewed_active",
                "review_status": "llm_reviewed",
                "selection_group_id": "group_1",
            },
            {
                "case_id": "case_revise_g1",
                "benchmark_status": "needs_revision",
                "review_status": "llm_reviewed",
                "selection_group_id": "group_1",
            },
            {
                "case_id": "case_keep_g2",
                "benchmark_status": "reviewed_active",
                "review_status": "llm_reviewed",
                "selection_group_id": "group_2",
            },
        ],
    )

    monkeypatch.setattr(module, "LOCAL_DATASET_ROOT", local_root)
    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: Namespace(
            source_dataset_id="source_dataset",
            target_dataset_id="target_dataset",
            family="excerpt_cases",
            storage_mode="local-only",
            include_status=["reviewed_active"],
            selection_group_id=["group_1"],
            case_id=[],
            allow_empty=False,
        ),
    )

    assert module.main() == 0

    target_dir = local_root / "excerpt_cases" / "target_dataset"
    manifest = json.loads((target_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (target_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()]

    assert [row["case_id"] for row in rows] == ["case_keep_g1"]
    assert manifest["freeze_criteria"] == {
        "include_status": ["reviewed_active"],
        "selection_group_ids": ["group_1"],
    }
    assert manifest["review_queue_summary"]["row_count"] == 1


def test_main_filters_reviewed_slice_by_explicit_case_id(tmp_path: Path, monkeypatch) -> None:
    local_root = tmp_path / "state" / "eval_local_datasets"
    source_dir = local_root / "excerpt_cases" / "source_dataset"
    _write_json(
        source_dir / "manifest.json",
        {
            "dataset_id": "source_dataset",
            "family": "excerpt_cases",
            "storage_mode": "local-only",
            "primary_file": "cases.jsonl",
        },
    )
    _write_jsonl(
        source_dir / "cases.jsonl",
        [
            {
                "case_id": "case_keep_a",
                "benchmark_status": "reviewed_active",
                "review_status": "llm_reviewed",
                "selection_group_id": "group_1",
            },
            {
                "case_id": "case_keep_b",
                "benchmark_status": "reviewed_active",
                "review_status": "human_reviewed",
                "selection_group_id": "group_2",
            },
        ],
    )

    monkeypatch.setattr(module, "LOCAL_DATASET_ROOT", local_root)
    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: Namespace(
            source_dataset_id="source_dataset",
            target_dataset_id="target_dataset",
            family="excerpt_cases",
            storage_mode="local-only",
            include_status=["reviewed_active"],
            selection_group_id=[],
            case_id=["case_keep_b"],
            allow_empty=False,
        ),
    )

    assert module.main() == 0

    target_dir = local_root / "excerpt_cases" / "target_dataset"
    manifest = json.loads((target_dir / "manifest.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (target_dir / "cases.jsonl").read_text(encoding="utf-8").splitlines()]

    assert [row["case_id"] for row in rows] == ["case_keep_b"]
    assert manifest["freeze_criteria"] == {
        "include_status": ["reviewed_active"],
        "case_ids": ["case_keep_b"],
    }
    assert manifest["review_queue_summary"]["review_status_counts"] == {"human_reviewed": 1}
