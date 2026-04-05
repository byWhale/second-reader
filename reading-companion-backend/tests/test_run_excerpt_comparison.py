"""Tests for excerpt-comparison orchestration and excerpt-local evidence matching."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from eval.attentional_v2 import run_excerpt_comparison as excerpt_comparison


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _bootstrap_dataset(tmp_path: Path, rows: list[dict[str, Any]]) -> Path:
    dataset_dir = tmp_path / "dataset"
    _write_json(
        dataset_dir / "manifest.json",
        {
            "dataset_id": "demo_dataset",
            "language_track": "en",
            "version": "1",
            "primary_file": "cases.jsonl",
        },
    )
    _write_jsonl(dataset_dir / "cases.jsonl", rows)
    return dataset_dir


def _bootstrap_source_manifests(tmp_path: Path) -> tuple[Path, Path]:
    public_manifest = tmp_path / "public_manifest.json"
    local_refs_manifest = tmp_path / "local_refs.json"
    _write_json(
        public_manifest,
        {
            "books": [
                {"source_id": "source_a", "relative_local_path": "state/library_sources/source_a.epub"},
                {"source_id": "source_b", "relative_local_path": "state/library_sources/source_b.epub"},
            ]
        },
    )
    _write_json(
        local_refs_manifest,
        {
            "source_refs": [
                {"source_id": "source_local", "relative_local_path": "state/library_sources/source_local.epub"},
            ]
        },
    )
    return public_manifest, local_refs_manifest


def _bootstrap_formal_manifest(tmp_path: Path, *, selective: list[str], clarification: list[str]) -> Path:
    formal_manifest = tmp_path / "formal_manifest.json"
    _write_json(
        formal_manifest,
        {
            "source_refs": {
                "excerpt_case_datasets": ["state/eval_local_datasets/excerpt_cases/demo_dataset"],
                "source_manifests": ["eval/manifests/source_books/demo_sources.json"],
            },
            "splits": {
                "excerpt_core_primary_frozen_draft": {"all": selective},
                "insight_and_clarification_subset_frozen_draft": {"all": clarification},
            }
        },
    )
    return formal_manifest


def _book_document(chapter_id: int, lines: list[str]) -> dict[str, Any]:
    sentences = []
    for index, text in enumerate(lines, start=1):
        sentences.append(
            {
                "sentence_id": f"c{chapter_id}-s{index}",
                "sentence_index": index,
                "sentence_in_paragraph": 1,
                "paragraph_index": index,
                "text": text,
            }
        )
    return {
        "metadata": {
            "book": "Demo Book",
            "author": "Tester",
            "book_language": "en",
            "output_language": "en",
            "source_file": "demo.epub",
        },
        "chapters": [
            {
                "id": chapter_id,
                "title": f"Chapter {chapter_id}",
                "chapter_number": chapter_id,
                "level": 1,
                "sentences": sentences,
            }
        ],
    }


def _provisioned_book(document: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(book_document=document)


def _unit_result(source_id: str, chapter_id: int) -> dict[str, Any]:
    return {
        "unit_key": f"{source_id}__chapter_{chapter_id}",
        "source_id": source_id,
        "chapter_id": chapter_id,
        "output_language": "en",
        "book_title": "Book",
        "author": "Author",
        "mechanisms": {
            "attentional_v2": {
                "status": "completed",
                "mechanism_key": "attentional_v2",
                "mechanism_label": "Attentional V2",
                "output_dir": f"/tmp/{source_id}/{chapter_id}/attentional_v2",
                "normalized_eval_bundle": {
                    "reactions": [
                        {
                            "reaction_id": "a-r1",
                            "type": "discern",
                            "section_ref": f"{chapter_id}.1",
                            "anchor_quote": "Alpha hinge line.",
                            "content": "Observed the hinge.",
                        }
                    ],
                    "attention_events": [
                        {
                            "event_id": "a-e1",
                            "kind": "thought",
                            "phase": "thinking",
                            "section_ref": f"{chapter_id}.1",
                            "move_type": "zoom",
                            "message": "The hinge matters here.",
                            "current_excerpt": "Alpha hinge line.",
                        }
                    ],
                    "chapters": [{"chapter_id": chapter_id, "chapter_ref": f"Chapter {chapter_id}"}],
                    "memory_summaries": ["Memory"],
                },
                "bundle_summary": {},
                "error": "",
            },
            "iterator_v1": {
                "status": "completed",
                "mechanism_key": "iterator_v1",
                "mechanism_label": "Iterator V1",
                "output_dir": f"/tmp/{source_id}/{chapter_id}/iterator_v1",
                "normalized_eval_bundle": {
                    "reactions": [
                        {
                            "reaction_id": "i-r1",
                            "type": "discern",
                            "section_ref": f"{chapter_id}.1",
                            "anchor_quote": "Alpha hinge line.",
                            "content": "Observed the hinge.",
                        }
                    ],
                    "attention_events": [
                        {
                            "event_id": "i-e1",
                            "kind": "thought",
                            "phase": "thinking",
                            "section_ref": f"{chapter_id}.1",
                            "move_type": "zoom",
                            "message": "The hinge matters here.",
                            "current_excerpt": "Alpha hinge line.",
                        }
                    ],
                    "chapters": [{"chapter_id": chapter_id, "chapter_ref": f"Chapter {chapter_id}"}],
                    "memory_summaries": ["Memory"],
                },
                "bundle_summary": {},
                "error": "",
            },
        },
    }


def test_target_case_ids_from_formal_manifest_parses_manifest_subsets(tmp_path: Path) -> None:
    formal_manifest = _bootstrap_formal_manifest(
        tmp_path,
        selective=["case_a", "case_b", "case_c"],
        clarification=["case_b", "case_c"],
    )

    payload = excerpt_comparison._load_formal_manifest(formal_manifest)
    target_case_ids = excerpt_comparison._target_case_ids_from_manifest(payload, target_slice="both")

    assert target_case_ids == {
        "selective_legibility": ["case_a", "case_b", "case_c"],
        "insight_and_clarification": ["case_b", "case_c"],
    }
    assert excerpt_comparison._merge_case_id_order(target_case_ids) == ["case_a", "case_b", "case_c"]


def test_default_dataset_dirs_cover_tracked_and_local_reviewed_without_scratch() -> None:
    default_dirs = [str(path) for path in excerpt_comparison.DEFAULT_DATASET_DIRS]

    assert any(path.endswith("attentional_v2_excerpt_en_curated_v2") for path in default_dirs)
    assert any(path.endswith("attentional_v2_excerpt_zh_curated_v2") for path in default_dirs)
    assert any(path.endswith("attentional_v2_private_library_excerpt_en_v2") for path in default_dirs)
    assert any(path.endswith("attentional_v2_private_library_excerpt_zh_v2") for path in default_dirs)
    assert not any("__scratch__" in path for path in default_dirs)


def test_load_source_index_merges_public_and_local_refs(tmp_path: Path) -> None:
    public_manifest, local_refs_manifest = _bootstrap_source_manifests(tmp_path)

    source_index = excerpt_comparison._load_source_index([public_manifest, local_refs_manifest])

    assert sorted(source_index) == ["source_a", "source_b", "source_local"]
    assert source_index["source_local"]["relative_local_path"] == "state/library_sources/source_local.epub"


def test_manifest_dataset_and_source_refs_can_drive_runner_defaults(tmp_path: Path) -> None:
    formal_manifest = _bootstrap_formal_manifest(
        tmp_path,
        selective=["case_a"],
        clarification=["case_a"],
    )

    payload = excerpt_comparison._load_formal_manifest(formal_manifest)

    dataset_dirs = excerpt_comparison._dataset_dirs_from_manifest(payload)
    source_manifest_paths = excerpt_comparison._source_manifest_paths_from_manifest(payload)

    assert dataset_dirs == [
        (excerpt_comparison.ROOT / "state" / "eval_local_datasets" / "excerpt_cases" / "demo_dataset").resolve()
    ]
    assert source_manifest_paths == [
        (excerpt_comparison.ROOT / "eval" / "manifests" / "source_books" / "demo_sources.json").resolve()
    ]


def test_default_active_benchmark_manifest_tracks_four_selected_chapters() -> None:
    payload = excerpt_comparison._load_formal_manifest(excerpt_comparison.DEFAULT_FORMAL_MANIFEST)
    chapter_case_ids = payload["splits"]["chapter_core_frozen_draft"]["all"]

    assert chapter_case_ids == [
        "supremacy_private_en__13",
        "steve_jobs_private_en__17",
        "zouchu_weiyi_zhenliguan_private_zh__14",
        "meiguoren_de_xingge_private_zh__19",
    ]
    assert payload["quota_status"]["excerpt_primary"]["target_total"] == 40


def test_run_benchmark_reuses_one_unit_run_for_cases_in_same_chapter(monkeypatch, tmp_path: Path) -> None:
    dataset_dir = _bootstrap_dataset(
        tmp_path,
        [
            {
                "case_id": "case_a",
                "source_id": "source_a",
                "book_title": "Book A",
                "author": "Author A",
                "output_language": "en",
                "chapter_id": 1,
                "chapter_title": "Chapter 1",
                "start_sentence_id": "c1-s1",
                "end_sentence_id": "c1-s2",
                "excerpt_text": "Alpha hinge line.\nThen the argument turns.",
                "question_ids": ["Q1"],
                "phenomena": ["distinction"],
                "selection_reason": "One",
                "judge_focus": "One",
                "split": "benchmark",
            },
            {
                "case_id": "case_b",
                "source_id": "source_a",
                "book_title": "Book A",
                "author": "Author A",
                "output_language": "en",
                "chapter_id": 1,
                "chapter_title": "Chapter 1",
                "start_sentence_id": "c1-s1",
                "end_sentence_id": "c1-s2",
                "excerpt_text": "Alpha hinge line.\nThen the argument turns.",
                "question_ids": ["Q2"],
                "phenomena": ["distinction"],
                "selection_reason": "Two",
                "judge_focus": "Two",
                "split": "benchmark",
            },
        ],
    )
    public_manifest, local_refs_manifest = _bootstrap_source_manifests(tmp_path)
    formal_manifest = _bootstrap_formal_manifest(
        tmp_path,
        selective=["case_a", "case_b"],
        clarification=["case_b"],
    )
    monkeypatch.setattr(excerpt_comparison, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))
    run_calls: list[tuple[str, int]] = []

    def fake_run_unit_bundle(
        unit: excerpt_comparison.ChapterUnit,
        *,
        source: dict[str, Any],
        run_root: Path,
        shard_id: str,
        mechanism_execution_mode: str,
        mechanism_filter: str,
        skip_existing: bool,
    ) -> dict[str, Any]:
        assert source["source_id"] == "source_a"
        assert mechanism_execution_mode == "serial"
        assert mechanism_filter == "both"
        assert shard_id == "default"
        assert skip_existing is False
        assert run_root.parent == tmp_path / "runs"
        run_calls.append((unit.source_id, unit.chapter_id))
        return _unit_result(unit.source_id, unit.chapter_id)

    monkeypatch.setattr(excerpt_comparison, "_run_unit_bundle", fake_run_unit_bundle)
    monkeypatch.setattr(
        excerpt_comparison,
        "ensure_canonical_parse",
        lambda _book_path, language_mode: _provisioned_book(
            _book_document(1, ["Alpha hinge line.", "Then the argument turns."])
        ),
    )

    summary = excerpt_comparison.run_benchmark(
        dataset_dirs=[dataset_dir],
        source_manifest_paths=[public_manifest, local_refs_manifest],
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="demo_excerpt_cache",
        stage="all",
        target_slice="both",
        judge_mode="none",
        mechanism_execution_mode="serial",
        judge_execution_mode="serial",
        case_workers=1,
    )

    assert run_calls == [("source_a", 1)]
    run_root = Path(summary["run_root"])
    assert (run_root / "shards" / "default" / "cases" / "case_a.json").exists()
    assert (run_root / "shards" / "default" / "cases" / "case_b.json").exists()


def test_extract_case_local_evidence_records_explicit_match_method() -> None:
    case = excerpt_comparison.ExcerptCase(
        case_id="case_a",
        case_title="case_a",
        split="benchmark",
        source_id="source_a",
        book_title="Book A",
        author="Author A",
        output_language="en",
        chapter_id=1,
        chapter_title="Chapter 1",
        start_sentence_id="c1-s1",
        end_sentence_id="c1-s2",
        excerpt_text="Alpha hinge line.\nThen the argument turns.",
        question_ids=["Q1"],
        phenomena=["distinction"],
        selection_reason="Test",
        judge_focus="Test",
        dataset_id="demo_dataset",
        dataset_version="1",
    )
    bundle = _unit_result("source_a", 1)["mechanisms"]["attentional_v2"]["normalized_eval_bundle"]
    document = _book_document(1, ["Alpha hinge line.", "Then the argument turns."])

    evidence = excerpt_comparison._extract_case_local_evidence(case=case, bundle=bundle, document=document)

    assert evidence["match_method"] == "section_ref_plus_anchor_or_current_excerpt"
    assert evidence["matched_reaction_count"] == 1
    assert evidence["matched_attention_event_count"] == 1
    assert evidence["match_method_counts"]["section_ref_exact"] >= 1
    assert evidence["match_method_counts"]["excerpt_text"] >= 1


def test_run_benchmark_isolates_case_failure_and_still_writes_aggregate(monkeypatch, tmp_path: Path) -> None:
    dataset_dir = _bootstrap_dataset(
        tmp_path,
        [
            {
                "case_id": "case_a",
                "source_id": "source_a",
                "book_title": "Book A",
                "author": "Author A",
                "output_language": "en",
                "chapter_id": 1,
                "chapter_title": "Chapter 1",
                "start_sentence_id": "c1-s1",
                "end_sentence_id": "c1-s2",
                "excerpt_text": "Alpha hinge line.\nThen the argument turns.",
                "question_ids": ["Q1"],
                "phenomena": ["distinction"],
                "selection_reason": "One",
                "judge_focus": "One",
                "split": "benchmark",
            },
            {
                "case_id": "case_b",
                "source_id": "source_b",
                "book_title": "Book B",
                "author": "Author B",
                "output_language": "zh",
                "chapter_id": 2,
                "chapter_title": "Chapter 2",
                "start_sentence_id": "c2-s1",
                "end_sentence_id": "c2-s2",
                "excerpt_text": "Alpha hinge line.\nThen the argument turns.",
                "question_ids": ["Q2"],
                "phenomena": ["distinction"],
                "selection_reason": "Two",
                "judge_focus": "Two",
                "split": "benchmark",
            },
        ],
    )
    public_manifest, local_refs_manifest = _bootstrap_source_manifests(tmp_path)
    formal_manifest = _bootstrap_formal_manifest(
        tmp_path,
        selective=["case_a", "case_b"],
        clarification=["case_b"],
    )
    monkeypatch.setattr(excerpt_comparison, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))
    monkeypatch.setattr(
        excerpt_comparison,
        "_run_unit_bundle",
        lambda unit, *, source, run_root, shard_id, mechanism_execution_mode, mechanism_filter, skip_existing: _unit_result(unit.source_id, unit.chapter_id),
    )
    monkeypatch.setattr(
        excerpt_comparison,
        "ensure_canonical_parse",
        lambda _book_path, language_mode: _provisioned_book(
            _book_document(1 if language_mode == "en" else 2, ["Alpha hinge line.", "Then the argument turns."])
        ),
    )
    original_evaluate_case = excerpt_comparison._evaluate_case

    def fake_evaluate_case(
        case: excerpt_comparison.ExcerptCase,
        *,
        case_targets: list[str],
        unit_result: dict[str, Any],
        document: dict[str, Any],
        run_root: Path,
        judge_mode: str,
        judge_execution_mode: str,
        shard_id: str,
    ) -> dict[str, Any]:
        if case.case_id == "case_b":
            raise RuntimeError("case exploded")
        return original_evaluate_case(
            case,
            case_targets=case_targets,
            unit_result=unit_result,
            document=document,
            run_root=run_root,
            judge_mode=judge_mode,
            judge_execution_mode=judge_execution_mode,
            shard_id=shard_id,
        )

    monkeypatch.setattr(excerpt_comparison, "_evaluate_case", fake_evaluate_case)

    summary = excerpt_comparison.run_benchmark(
        dataset_dirs=[dataset_dir],
        source_manifest_paths=[public_manifest, local_refs_manifest],
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="demo_excerpt_failure_isolation",
        stage="all",
        target_slice="both",
        judge_mode="none",
        mechanism_execution_mode="serial",
        judge_execution_mode="serial",
        case_workers=1,
    )
    merge_summary = excerpt_comparison.run_benchmark(
        dataset_dirs=[dataset_dir],
        source_manifest_paths=[public_manifest, local_refs_manifest],
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="demo_excerpt_failure_isolation",
        stage="merge",
        target_slice="both",
        judge_mode="none",
    )

    run_root = Path(summary["run_root"])
    case_b_payload = json.loads((run_root / "shards" / "default" / "cases" / "case_b.json").read_text(encoding="utf-8"))

    assert merge_summary["aggregate"]["case_count"] == 2
    assert merge_summary["aggregate"]["target_summaries"]["selective_legibility"]["judge_unavailable_count"] == 1
    assert case_b_payload["case_error"] == "RuntimeError: case exploded"
    assert (run_root / "summary" / "aggregate.json").exists()
    assert (run_root / "summary" / "report.md").exists()


def test_stage_bundle_only_writes_shard_unit_and_bundle_outputs(monkeypatch, tmp_path: Path) -> None:
    dataset_dir = _bootstrap_dataset(
        tmp_path,
        [
            {
                "case_id": "case_a",
                "source_id": "source_a",
                "book_title": "Book A",
                "author": "Author A",
                "output_language": "en",
                "chapter_id": 1,
                "chapter_title": "Chapter 1",
                "start_sentence_id": "c1-s1",
                "end_sentence_id": "c1-s2",
                "excerpt_text": "Alpha hinge line.\nThen the argument turns.",
                "question_ids": ["Q1"],
                "phenomena": ["distinction"],
                "selection_reason": "One",
                "judge_focus": "One",
                "split": "benchmark",
            }
        ],
    )
    public_manifest, local_refs_manifest = _bootstrap_source_manifests(tmp_path)
    formal_manifest = _bootstrap_formal_manifest(tmp_path, selective=["case_a"], clarification=["case_a"])
    monkeypatch.setattr(excerpt_comparison, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))
    monkeypatch.setattr(
        excerpt_comparison,
        "_run_unit_bundle",
        lambda unit, *, source, run_root, shard_id, mechanism_execution_mode, mechanism_filter, skip_existing: _unit_result(unit.source_id, unit.chapter_id),
    )

    summary = excerpt_comparison.run_benchmark(
        dataset_dirs=[dataset_dir],
        source_manifest_paths=[public_manifest, local_refs_manifest],
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="stage_bundle_demo",
        stage="bundle",
        target_slice="both",
        judge_mode="none",
        mechanism_execution_mode="parallel",
        unit_workers=1,
    )

    run_root = Path(summary["run_root"])
    assert (run_root / "shards" / "default" / "units" / "source_a__chapter_1.json").exists()
    assert not (run_root / "summary" / "aggregate.json").exists()


def test_stage_judge_reuses_existing_bundles_and_writes_shard_cases(monkeypatch, tmp_path: Path) -> None:
    dataset_dir = _bootstrap_dataset(
        tmp_path,
        [
            {
                "case_id": "case_a",
                "source_id": "source_a",
                "book_title": "Book A",
                "author": "Author A",
                "output_language": "en",
                "chapter_id": 1,
                "chapter_title": "Chapter 1",
                "start_sentence_id": "c1-s1",
                "end_sentence_id": "c1-s2",
                "excerpt_text": "Alpha hinge line.\nThen the argument turns.",
                "question_ids": ["Q1"],
                "phenomena": ["distinction"],
                "selection_reason": "One",
                "judge_focus": "One",
                "split": "benchmark",
            }
        ],
    )
    public_manifest, local_refs_manifest = _bootstrap_source_manifests(tmp_path)
    formal_manifest = _bootstrap_formal_manifest(tmp_path, selective=["case_a"], clarification=["case_a"])
    run_root = tmp_path / "runs" / "stage_judge_demo"
    _write_json(run_root / "shards" / "bundle_shard" / "bundles" / "attentional_v2" / "source_a__chapter_1.json", _unit_result("source_a", 1)["mechanisms"]["attentional_v2"])
    _write_json(run_root / "shards" / "bundle_shard" / "bundles" / "iterator_v1" / "source_a__chapter_1.json", _unit_result("source_a", 1)["mechanisms"]["iterator_v1"])
    monkeypatch.setattr(excerpt_comparison, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))
    monkeypatch.setattr(
        excerpt_comparison,
        "ensure_canonical_parse",
        lambda _book_path, language_mode: _provisioned_book(
            _book_document(1, ["Alpha hinge line.", "Then the argument turns."])
        ),
    )

    summary = excerpt_comparison.run_benchmark(
        dataset_dirs=[dataset_dir],
        source_manifest_paths=[public_manifest, local_refs_manifest],
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="stage_judge_demo",
        stage="judge",
        target_slice="both",
        judge_mode="none",
        judge_workers=1,
    )

    assert summary["case_count"] == 1
    assert (run_root / "shards" / "default" / "cases" / "case_a.json").exists()
    assert not (run_root / "summary" / "aggregate.json").exists()


def test_skip_existing_and_merge_stage_reuse_prior_case_outputs(monkeypatch, tmp_path: Path) -> None:
    dataset_dir = _bootstrap_dataset(
        tmp_path,
        [
            {
                "case_id": "case_a",
                "source_id": "source_a",
                "book_title": "Book A",
                "author": "Author A",
                "output_language": "en",
                "chapter_id": 1,
                "chapter_title": "Chapter 1",
                "start_sentence_id": "c1-s1",
                "end_sentence_id": "c1-s2",
                "excerpt_text": "Alpha hinge line.\nThen the argument turns.",
                "question_ids": ["Q1"],
                "phenomena": ["distinction"],
                "selection_reason": "One",
                "judge_focus": "One",
                "split": "benchmark",
            }
        ],
    )
    public_manifest, local_refs_manifest = _bootstrap_source_manifests(tmp_path)
    formal_manifest = _bootstrap_formal_manifest(tmp_path, selective=["case_a"], clarification=["case_a"])
    run_root = tmp_path / "runs" / "skip_existing_demo"
    _write_json(
        run_root / "shards" / "prior" / "cases" / "case_a.json",
        {
            "case_id": "case_a",
            "case_title": "case_a",
            "source_id": "source_a",
            "chapter_id": 1,
            "chapter_title": "Chapter 1",
            "book_title": "Book A",
            "author": "Author A",
            "output_language": "en",
            "case_targets": ["selective_legibility", "insight_and_clarification"],
            "mechanisms": {
                "attentional_v2": {"status": "completed"},
                "iterator_v1": {"status": "completed"},
            },
            "target_results": {
                "selective_legibility": {"judgment": {"winner": "tie", "reason": "judge_disabled", "scores": {"attentional_v2": {}, "iterator_v1": {}}, "confidence": "low"}},
                "insight_and_clarification": {"judgment": {"winner": "tie", "reason": "judge_disabled", "scores": {"attentional_v2": {}, "iterator_v1": {}}, "confidence": "low"}},
            },
        },
    )
    monkeypatch.setattr(excerpt_comparison, "resolve_worker_policy", lambda **_kwargs: SimpleNamespace(worker_count=1))
    monkeypatch.setattr(
        excerpt_comparison,
        "ensure_canonical_parse",
        lambda _book_path, language_mode: _provisioned_book(
            _book_document(1, ["Alpha hinge line.", "Then the argument turns."])
        ),
    )

    judge_summary = excerpt_comparison.run_benchmark(
        dataset_dirs=[dataset_dir],
        source_manifest_paths=[public_manifest, local_refs_manifest],
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="skip_existing_demo",
        stage="judge",
        target_slice="both",
        judge_mode="none",
        skip_existing=True,
    )
    merge_summary = excerpt_comparison.run_benchmark(
        dataset_dirs=[dataset_dir],
        source_manifest_paths=[public_manifest, local_refs_manifest],
        formal_manifest_path=formal_manifest,
        runs_root=tmp_path / "runs",
        run_id="skip_existing_demo",
        stage="merge",
        target_slice="both",
        judge_mode="none",
    )

    assert judge_summary["case_count"] == 1
    assert merge_summary["aggregate"]["case_count"] == 1
    assert (run_root / "summary" / "aggregate.json").exists()
