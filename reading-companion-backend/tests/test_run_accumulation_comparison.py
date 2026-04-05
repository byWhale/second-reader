from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from eval.attentional_v2 import run_accumulation_comparison as accumulation_comparison


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _bootstrap_window_dataset(tmp_path: Path) -> Path:
    dataset_dir = tmp_path / "windows"
    _write_json(
        dataset_dir / "manifest.json",
        {
            "dataset_id": "demo_windows",
            "family": "window_cases",
            "version": "1",
            "primary_file": "windows.jsonl",
        },
    )
    _write_jsonl(
        dataset_dir / "windows.jsonl",
        [
            {
                "window_case_id": "window_a",
                "source_id": "source_a",
                "book_title": "Book A",
                "author": "Author A",
                "output_language": "en",
                "benchmark_line": "demo",
                "window_kind": "single_chapter",
                "chapter_case_ids": ["source_a__1"],
                "chapter_ids": ["1"],
                "chapter_numbers": [1],
                "chapter_titles": ["Chapter 1"],
                "sentence_count": 12,
                "selection_group_id": "window_a",
                "selection_group_label": "Window A",
                "cross_chapter_window": {},
            }
        ],
    )
    return dataset_dir


def _bootstrap_probe_dataset(tmp_path: Path) -> Path:
    dataset_dir = tmp_path / "probes"
    _write_json(
        dataset_dir / "manifest.json",
        {
            "dataset_id": "demo_probes",
            "family": "accumulation_probes",
            "version": "1",
            "primary_file": "probes.jsonl",
        },
    )
    _write_jsonl(
        dataset_dir / "probes.jsonl",
        [
            {
                "probe_id": "probe_a",
                "window_case_id": "window_a",
                "source_id": "source_a",
                "book_title": "Book A",
                "author": "Author A",
                "output_language": "en",
                "probe_type": "carryforward",
                "selection_reason": "Test",
                "judge_focus": "Test",
                "note_provenance": [],
                "anchor_refs": [
                    {
                        "anchor_id": "a1",
                        "anchor_kind": "early",
                        "chapter_id": 1,
                        "start_sentence_id": "c1-s1",
                        "end_sentence_id": "c1-s2",
                        "excerpt_text": "Alpha hinge line. Then the argument turns.",
                    },
                    {
                        "anchor_id": "a2",
                        "anchor_kind": "late",
                        "chapter_id": 1,
                        "start_sentence_id": "c1-s3",
                        "end_sentence_id": "c1-s4",
                        "excerpt_text": "Later the hinge returns with force.",
                    },
                ],
            }
        ],
    )
    return dataset_dir


def _bootstrap_source_manifest(tmp_path: Path) -> Path:
    manifest = tmp_path / "sources.json"
    _write_json(
        manifest,
        {
            "books": [
                {"source_id": "source_a", "relative_local_path": "state/library_sources/source_a.epub"},
            ]
        },
    )
    return manifest


def _bootstrap_formal_manifest(
    tmp_path: Path,
    *,
    window_dataset: Path | None = None,
    probe_dataset: Path | None = None,
    source_manifest: Path | None = None,
    probe_ids: list[str],
) -> Path:
    resolved_window_dataset = window_dataset or (tmp_path / "windows")
    resolved_probe_dataset = probe_dataset or (tmp_path / "probes")
    resolved_source_manifest = source_manifest or (tmp_path / "sources.json")
    manifest = tmp_path / "formal_manifest.json"
    _write_json(
        manifest,
        {
            "source_refs": {
                "window_case_datasets": [str(resolved_window_dataset.resolve())],
                "accumulation_probe_datasets": [str(resolved_probe_dataset.resolve())],
                "source_manifests": [str(resolved_source_manifest.resolve())],
            },
            "splits": {
                "accumulation_probes_frozen_draft": {"all": probe_ids},
                "insight_and_clarification_subset_frozen_draft": {"all": probe_ids},
            },
        },
    )
    return manifest


def _book_document() -> dict[str, Any]:
    return {
        "metadata": {
            "book": "Book A",
            "author": "Author A",
            "book_language": "en",
            "output_language": "en",
            "source_file": "demo.epub",
        },
        "chapters": [
            {
                "id": 1,
                "title": "Chapter 1",
                "chapter_number": 1,
                "level": 1,
                "sentences": [
                    {"sentence_id": "c1-s1", "paragraph_index": 1, "text": "Alpha hinge line."},
                    {"sentence_id": "c1-s2", "paragraph_index": 2, "text": "Then the argument turns."},
                    {"sentence_id": "c1-s3", "paragraph_index": 3, "text": "Later the hinge returns."},
                    {"sentence_id": "c1-s4", "paragraph_index": 4, "text": "The late section sharpens the claim."},
                ],
            }
        ],
    }


def _window_result(window_case_id: str = "window_a") -> dict[str, Any]:
    base_bundle = {
        "reactions": [
            {
                "type": "discern",
                "section_ref": "1.1",
                "anchor_quote": "Alpha hinge line.",
                "content": "Early hinge noted.",
            },
            {
                "type": "return",
                "section_ref": "1.3",
                "anchor_quote": "Later the hinge returns.",
                "content": "Late hinge reuse noted.",
            },
        ],
        "attention_events": [
            {
                "kind": "thought",
                "phase": "thinking",
                "section_ref": "1.1",
                "move_type": "zoom",
                "message": "Early hinge matters.",
                "current_excerpt": "Alpha hinge line.",
            },
            {
                "kind": "thought",
                "phase": "thinking",
                "section_ref": "1.3",
                "move_type": "bridge",
                "message": "The later turn carries the earlier hinge forward.",
                "current_excerpt": "Later the hinge returns.",
            },
        ],
        "chapters": [{"chapter_id": 1, "chapter_ref": "Chapter 1"}],
        "memory_summaries": ["Memory"],
    }
    return {
        "window_case_id": window_case_id,
        "source_id": "source_a",
        "output_language": "en",
        "book_title": "Book A",
        "author": "Author A",
        "chapter_case_ids": ["source_a__1"],
        "mechanisms": {
            "attentional_v2": {
                "status": "completed",
                "mechanism_key": "attentional_v2",
                "mechanism_label": "Attentional V2",
                "output_dir": "/tmp/window_a/attentional_v2",
                "normalized_eval_bundle": base_bundle,
                "bundle_summary": {},
                "error": "",
            },
            "iterator_v1": {
                "status": "completed",
                "mechanism_key": "iterator_v1",
                "mechanism_label": "Iterator V1",
                "output_dir": "/tmp/window_a/iterator_v1",
                "normalized_eval_bundle": base_bundle,
                "bundle_summary": {},
                "error": "",
            },
        },
    }


def test_stage_bundle_only_writes_shard_outputs(monkeypatch, tmp_path: Path) -> None:
    window_dataset = _bootstrap_window_dataset(tmp_path)
    probe_dataset = _bootstrap_probe_dataset(tmp_path)
    source_manifest = _bootstrap_source_manifest(tmp_path)
    formal_manifest = _bootstrap_formal_manifest(
        tmp_path,
        window_dataset=window_dataset,
        probe_dataset=probe_dataset,
        source_manifest=source_manifest,
        probe_ids=["probe_a"],
    )
    monkeypatch.setattr(accumulation_comparison, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))
    monkeypatch.setattr(
        accumulation_comparison,
        "_run_window_bundle",
        lambda window, *, source, run_root, shard_id, mechanism_execution_mode, mechanism_filter, skip_existing: _window_result(window.window_case_id),
    )

    summary = accumulation_comparison.run_benchmark(
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="acc_bundle_demo",
        stage="bundle",
        target_slice="both",
        judge_mode="none",
        mechanism_execution_mode="parallel",
        case_workers=1,
    )

    run_root = Path(summary["run_root"])
    assert summary["window_count"] == 1
    assert (run_root / "shards" / "default" / "units" / "window_a.json").exists()
    assert not (run_root / "summary" / "aggregate.json").exists()


def test_stage_judge_and_merge_use_existing_bundles(monkeypatch, tmp_path: Path) -> None:
    window_dataset = _bootstrap_window_dataset(tmp_path)
    probe_dataset = _bootstrap_probe_dataset(tmp_path)
    source_manifest = _bootstrap_source_manifest(tmp_path)
    formal_manifest = _bootstrap_formal_manifest(
        tmp_path,
        window_dataset=window_dataset,
        probe_dataset=probe_dataset,
        source_manifest=source_manifest,
        probe_ids=["probe_a"],
    )
    run_root = tmp_path / "runs" / "acc_judge_demo"
    _write_json(
        run_root / "shards" / "seed" / "bundles" / "attentional_v2" / "window_a.json",
        _window_result()["mechanisms"]["attentional_v2"],
    )
    _write_json(
        run_root / "shards" / "seed" / "bundles" / "iterator_v1" / "window_a.json",
        _window_result()["mechanisms"]["iterator_v1"],
    )
    monkeypatch.setattr(accumulation_comparison, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))
    monkeypatch.setattr(
        accumulation_comparison,
        "ensure_canonical_parse",
        lambda _book_path, language_mode: SimpleNamespace(book_document=_book_document()),
    )

    judge_summary = accumulation_comparison.run_benchmark(
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="acc_judge_demo",
        stage="judge",
        target_slice="both",
        judge_mode="none",
        judge_workers=1,
    )
    merge_summary = accumulation_comparison.run_benchmark(
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="acc_judge_demo",
        stage="merge",
        target_slice="both",
        judge_mode="none",
    )

    assert judge_summary["probe_count"] == 1
    assert merge_summary["aggregate"]["case_count"] == 1
    assert (run_root / "summary" / "aggregate.json").exists()


def test_skip_existing_reuses_prior_probe_result(monkeypatch, tmp_path: Path) -> None:
    window_dataset = _bootstrap_window_dataset(tmp_path)
    probe_dataset = _bootstrap_probe_dataset(tmp_path)
    source_manifest = _bootstrap_source_manifest(tmp_path)
    formal_manifest = _bootstrap_formal_manifest(
        tmp_path,
        window_dataset=window_dataset,
        probe_dataset=probe_dataset,
        source_manifest=source_manifest,
        probe_ids=["probe_a"],
    )
    run_root = tmp_path / "runs" / "acc_skip_demo"
    _write_json(
        run_root / "shards" / "prior" / "cases" / "probe_a.json",
        {
            "probe_id": "probe_a",
            "window_case_id": "window_a",
            "probe_type": "carryforward",
            "source_id": "source_a",
            "book_title": "Book A",
            "author": "Author A",
            "output_language": "en",
            "probe_targets": ["coherent_accumulation", "insight_and_clarification"],
            "mechanisms": {
                "attentional_v2": {"status": "completed"},
                "iterator_v1": {"status": "completed"},
            },
            "target_results": {
                "coherent_accumulation": {"judgment": {"winner": "tie", "reason": "judge_disabled", "scores": {"attentional_v2": {}, "iterator_v1": {}}, "confidence": "low"}},
                "insight_and_clarification": {"judgment": {"winner": "tie", "reason": "judge_disabled", "scores": {"attentional_v2": {}, "iterator_v1": {}}, "confidence": "low"}},
            },
        },
    )
    monkeypatch.setattr(accumulation_comparison, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))

    judge_summary = accumulation_comparison.run_benchmark(
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="acc_skip_demo",
        stage="judge",
        target_slice="both",
        judge_mode="none",
        skip_existing=True,
    )

    assert judge_summary["probe_count"] == 1


def test_mechanism_filter_single_mechanism_only_writes_one_bundle(monkeypatch, tmp_path: Path) -> None:
    window_dataset = _bootstrap_window_dataset(tmp_path)
    probe_dataset = _bootstrap_probe_dataset(tmp_path)
    source_manifest = _bootstrap_source_manifest(tmp_path)
    formal_manifest = _bootstrap_formal_manifest(
        tmp_path,
        window_dataset=window_dataset,
        probe_dataset=probe_dataset,
        source_manifest=source_manifest,
        probe_ids=["probe_a"],
    )
    monkeypatch.setattr(accumulation_comparison, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))

    accumulation_comparison.run_benchmark(
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="acc_mechanism_filter_demo",
        stage="bundle",
        target_slice="both",
        judge_mode="none",
        mechanism_filter="iterator_v1",
        mechanism_execution_mode="parallel",
        case_workers=1,
    )

    run_root = tmp_path / "runs" / "acc_mechanism_filter_demo"
    assert (run_root / "shards" / "default" / "bundles" / "iterator_v1" / "window_a.json").exists()
    assert not (run_root / "shards" / "default" / "bundles" / "attentional_v2" / "window_a.json").exists()
