"""Tests for the managed-catalog private-library supplement wiring."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from eval.attentional_v2 import build_private_library_supplement as builder_module
from eval.attentional_v2.build_private_library_supplement import (
    CLUSTERED_BENCHMARK_CHAPTER_CASE_IDS,
    CLUSTERED_BENCHMARK_MODE,
    CLUSTERED_CASES_PER_CHAPTER,
    CLUSTERED_RESERVES_PER_CHAPTER,
    HUMAN_NOTES_GUIDED_BENCHMARK_MODE,
    SupplementBuildOptions,
    build_private_library_splits,
    load_private_library_source_items,
    resolve_build_config,
)
from eval.attentional_v2.corpus_builder import CandidateSpec
from eval.attentional_v2.human_notes_cluster_planning import (
    resolve_human_notes_guided_cluster_plan,
)
from eval.attentional_v2.human_notes_guided_dataset import (
    HUMAN_NOTES_GUIDED_CASES_PER_CLUSTER,
    HUMAN_NOTES_GUIDED_RESERVES_PER_CLUSTER,
    HUMAN_NOTES_GUIDED_SOURCE_IDS,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: object) -> None:
    _write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def test_load_private_library_source_items_uses_catalog_paths_and_manifest_fallbacks(tmp_path: Path) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "fooled_by_randomness.epub"
    _write(source_path, "demo")

    catalog_path = root / "state" / "dataset_build" / "source_catalog.json"
    _write_json(
        catalog_path,
        {
            "records": [
                {
                    "source_id": "fooled_by_randomness_private_en",
                    "title": "Fooled by Randomness",
                    "author": "Nassim Nicholas Taleb",
                    "language": "en",
                    "visibility": "private",
                    "origin": "manual_library_inbox",
                    "relative_local_path": "state/library_sources/en/fooled_by_randomness.epub",
                    "original_filename": "Fooled by Randomness.epub",
                    "selection_priority": 9999,
                    "type_tags": [],
                    "role_tags": [],
                    "notes": [],
                    "ingest_batch_ids": ["catalog_batch_a"],
                    "acquisition": {
                        "kind": "manual_library_inbox",
                        "ingest_batch_id": "catalog_batch_a",
                    },
                }
            ]
        },
    )

    tracked_manifest_path = root / "eval" / "manifests" / "source_books" / "attentional_v2_private_library_screen_v2.json"
    _write_json(
        tracked_manifest_path,
        {
            "books": [
                {
                    "source_id": "fooled_by_randomness_private_en",
                    "selection_priority": 6,
                    "type_tags": ["psychology_decision", "modern_nonfiction"],
                    "role_tags": ["argumentative", "reference_heavy"],
                    "notes": ["Legacy private source retained."],
                    "acquisition_batch_id": "legacy_private_downloads_v1",
                }
            ]
        },
    )

    items = load_private_library_source_items(
        root=root,
        catalog_path=catalog_path,
        tracked_manifest_path=tracked_manifest_path,
    )

    assert len(items) == 1
    item = items[0]
    spec = item["spec"]
    assert spec.source_id == "fooled_by_randomness_private_en"
    assert spec.promoted_local_path == "en/fooled_by_randomness.epub"
    assert spec.selection_priority == 6
    assert spec.type_tags == ["psychology_decision", "modern_nonfiction"]
    assert spec.role_tags == ["argumentative", "reference_heavy"]
    assert spec.notes == ["Legacy private source retained."]
    assert item["source_path"] == source_path
    assert item["acquisition_batch_id"] == "legacy_private_downloads_v1"


def test_load_private_library_source_items_prefers_explicit_catalog_metadata_and_ignores_visibility_gating(tmp_path: Path) -> None:
    root = tmp_path
    private_source = root / "state" / "library_sources" / "zh" / "case_a.epub"
    public_source = root / "state" / "library_sources" / "en" / "case_b.epub"
    _write(private_source, "a")
    _write(public_source, "b")

    catalog_path = root / "state" / "dataset_build" / "source_catalog.json"
    _write_json(
        catalog_path,
        {
            "records": [
                {
                    "source_id": "case_a_private_zh",
                    "title": "案例A",
                    "author": "作者A",
                    "language": "zh",
                    "visibility": "private",
                    "origin": "manual_library_inbox",
                    "relative_local_path": "state/library_sources/zh/case_a.epub",
                    "selection_priority": 3,
                    "type_tags": ["history"],
                    "role_tags": ["argumentative"],
                    "notes": ["Catalog metadata wins."],
                    "original_filename": "case_a.epub",
                },
                {
                    "source_id": "case_b_public_en",
                    "title": "Case B",
                    "author": "Author B",
                    "language": "en",
                    "visibility": "public",
                    "origin": "manual_library_inbox",
                    "relative_local_path": "state/library_sources/en/case_b.epub",
                    "selection_priority": 1,
                    "type_tags": ["business"],
                    "role_tags": ["expository"],
                    "notes": ["Visibility should not exclude this managed source."],
                    "original_filename": "case_b.epub",
                },
            ]
        },
    )

    items = load_private_library_source_items(root=root, catalog_path=catalog_path, tracked_manifest_path=root / "missing.json")

    assert len(items) == 2
    specs = {item["spec"].source_id: item["spec"] for item in items}
    assert specs["case_a_private_zh"].selection_priority == 3
    assert specs["case_a_private_zh"].type_tags == ["history"]
    assert specs["case_a_private_zh"].role_tags == ["argumentative"]
    assert specs["case_a_private_zh"].notes == ["Catalog metadata wins."]
    assert specs["case_b_public_en"].selection_priority == 1
    assert specs["case_b_public_en"].type_tags == ["business"]
    assert specs["case_b_public_en"].role_tags == ["expository"]
    assert specs["case_b_public_en"].notes == ["Visibility should not exclude this managed source."]


def test_build_private_library_splits_adds_dynamic_batch_groups() -> None:
    source_records = [
        {
            "source_id": "legacy_en",
            "language": "en",
            "corpus_lane": "chapter_corpus_eligible",
            "acquisition_batch_id": "legacy_private_downloads_v1",
        },
        {
            "source_id": "new_zh",
            "language": "zh",
            "corpus_lane": "excerpt_only",
            "acquisition_batch_id": "batch_20260330",
        },
        {
            "source_id": "reject_en",
            "language": "en",
            "corpus_lane": "reject",
            "acquisition_batch_id": "",
        },
    ]

    splits = build_private_library_splits(source_records)

    assert splits["all_private_library_sources"] == {
        "en": ["legacy_en", "reject_en"],
        "zh": ["new_zh"],
    }
    assert splits["chapter_corpus_eligible"]["en"] == ["legacy_en"]
    assert splits["excerpt_only"]["zh"] == ["new_zh"]
    assert splits["reject_this_pass"]["en"] == ["reject_en"]
    assert splits["legacy_private_downloads_v1"]["en"] == ["legacy_en"]
    assert splits["batch_20260330"]["zh"] == ["new_zh"]


def test_resolve_build_config_scratch_redirects_ids_and_paths(tmp_path: Path) -> None:
    config = resolve_build_config(
        SupplementBuildOptions(
            scratch=True,
            run_id="scratch demo",
            feedback_dataset_ids={},
        ),
        root=tmp_path,
        manifest_root=tmp_path / "eval" / "manifests",
        local_dataset_root=tmp_path / "state" / "eval_local_datasets",
    )

    assert config.run_id == "scratch_demo"
    assert config.run_root == tmp_path / "state" / "dataset_build" / "build_runs" / "scratch_demo"
    assert config.manifest_root == config.run_root / "manifests"
    assert config.dataset_build_artifact_root == config.run_root
    assert config.ids.question_aligned_scope_id.endswith("__scratch__scratch_demo")
    assert (
        config.ids.package_ids["excerpt_cases"]["en"]
        == "attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__scratch_demo"
    )
    assert config.feedback_dataset_ids == {}


def test_resolve_build_config_clustered_mode_uses_cluster_defaults(tmp_path: Path) -> None:
    config = resolve_build_config(
        SupplementBuildOptions(
            benchmark_mode=CLUSTERED_BENCHMARK_MODE,
            scratch=True,
            run_id="clustered_demo",
            feedback_dataset_ids={},
        ),
        root=tmp_path,
        manifest_root=tmp_path / "eval" / "manifests",
        local_dataset_root=tmp_path / "state" / "eval_local_datasets",
    )

    assert config.benchmark_mode == CLUSTERED_BENCHMARK_MODE
    assert config.chapter_case_ids == CLUSTERED_BENCHMARK_CHAPTER_CASE_IDS
    assert config.cases_per_chapter == CLUSTERED_CASES_PER_CHAPTER
    assert config.reserves_per_chapter == CLUSTERED_RESERVES_PER_CHAPTER
    assert config.max_chapters_per_source == 0
    assert (
        config.ids.package_ids["excerpt_cases"]["en"]
        == "attentional_v2_clustered_benchmark_v1_excerpt_en__scratch__clustered_demo"
    )


def test_resolve_build_config_human_notes_mode_uses_isolated_namespace(tmp_path: Path) -> None:
    config = resolve_build_config(
        SupplementBuildOptions(
            benchmark_mode=HUMAN_NOTES_GUIDED_BENCHMARK_MODE,
            scratch=True,
            run_id="notes_demo",
            feedback_dataset_ids={},
        ),
        root=tmp_path,
        manifest_root=tmp_path / "eval" / "manifests",
        local_dataset_root=tmp_path / "state" / "eval_local_datasets",
    )

    assert config.benchmark_mode == HUMAN_NOTES_GUIDED_BENCHMARK_MODE
    assert config.max_chapters_per_source == 0
    assert config.target_profile_ids == builder_module.CLUSTERED_TARGET_PROFILE_ORDER
    assert config.source_ids == HUMAN_NOTES_GUIDED_SOURCE_IDS
    assert config.cases_per_chapter == HUMAN_NOTES_GUIDED_CASES_PER_CLUSTER
    assert config.reserves_per_chapter == HUMAN_NOTES_GUIDED_RESERVES_PER_CLUSTER
    assert config.feedback_dataset_ids == {}
    assert (
        config.ids.package_ids["excerpt_cases"]["en"]
        == "attentional_v2_human_notes_guided_dataset_v1_excerpt_en__scratch__notes_demo"
    )
    assert (
        config.ids.source_manifest_id
        == "attentional_v2_human_notes_guided_dataset_v1_source_books__scratch__notes_demo"
    )


def test_human_notes_cluster_planning_resolves_six_to_eight_clusters_and_selection_groups() -> None:
    chapter_rows_by_language = {
        "en": [
            {
                "chapter_case_id": f"book_{index}_en__1",
                "source_id": f"book_{index}_en",
                "book_title": f"Book {index}",
                "language_track": "en",
                "chapter_id": "1",
                "chapter_number": 1,
                "chapter_title": "Chapter 1",
            }
            for index in range(1, 4)
        ]
        + [
            {
                "chapter_case_id": f"book_{index}_en__2",
                "source_id": f"book_{index}_en",
                "book_title": f"Book {index}",
                "language_track": "en",
                "chapter_id": "2",
                "chapter_number": 2,
                "chapter_title": "Chapter 2",
            }
            for index in range(1, 4)
        ],
        "zh": [
            {
                "chapter_case_id": f"book_{index}_zh__1",
                "source_id": f"book_{index}_zh",
                "book_title": f"书 {index}",
                "language_track": "zh",
                "chapter_id": "1",
                "chapter_number": 1,
                "chapter_title": "第一章",
            }
            for index in range(4, 6)
        ]
        + [
            {
                "chapter_case_id": f"book_{index}_zh__2",
                "source_id": f"book_{index}_zh",
                "book_title": f"书 {index}",
                "language_track": "zh",
                "chapter_id": "2",
                "chapter_number": 2,
                "chapter_title": "第二章",
            }
            for index in range(4, 6)
        ],
    }
    source_index = {
        "book_1_en": {
            "source_id": "book_1_en",
            "title": "Book 1",
            "language": "en",
            "selection_priority": 1,
            "notes": ["Alpha notes"],
            "human_notes_guidance": {
                "summary": "Alpha",
                "cluster_proposals": [
                    {
                        "cluster_id": "b1c1",
                        "chapter_id": "1",
                        "selection_group": "definition",
                        "summary": "Alpha chapter",
                    },
                    {
                        "cluster_id": "b1c2",
                        "chapter_id": "2",
                        "selection_group": "bridge",
                        "cross_chapter_window": {
                            "start_chapter_id": "1",
                            "end_chapter_id": "2",
                        },
                    },
                ],
            },
        },
        "book_2_en": {
            "source_id": "book_2_en",
            "title": "Book 2",
            "language": "en",
            "selection_priority": 2,
            "notes": ["Beta notes"],
            "human_notes_guidance": {
                "cluster_proposals": [
                    {"cluster_id": "b2c1", "chapter_id": "1", "selection_group": "tension"},
                    {"cluster_id": "b2c2", "chapter_id": "2", "selection_group": "bridge"},
                ],
            },
        },
        "book_3_en": {
            "source_id": "book_3_en",
            "title": "Book 3",
            "language": "en",
            "selection_priority": 3,
            "notes": ["Gamma notes"],
            "human_notes_guidance": {
                "cluster_proposals": [
                    {"cluster_id": "b3c1", "chapter_id": "1", "selection_group": "reaction"},
                    {"cluster_id": "b3c2", "chapter_id": "2", "selection_group": "clarification"},
                ],
            },
        },
        "book_4_zh": {
            "source_id": "book_4_zh",
            "title": "书 4",
            "language": "zh",
            "selection_priority": 4,
            "notes": ["Delta notes"],
            "human_notes_guidance": {
                "cluster_proposals": [
                    {"cluster_id": "b4c1", "chapter_id": "1", "selection_group": "tension"},
                    {"cluster_id": "b4c2", "chapter_id": "2", "selection_group": "bridge"},
                ],
            },
        },
        "book_5_zh": {
            "source_id": "book_5_zh",
            "title": "书 5",
            "language": "zh",
            "selection_priority": 5,
            "notes": ["Epsilon notes"],
            "human_notes_guidance": {
                "cluster_proposals": [
                    {"cluster_id": "b5c1", "chapter_id": "1", "selection_group": "definition"},
                    {"cluster_id": "b5c2", "chapter_id": "2", "selection_group": "clarification"},
                ],
            },
        },
    }

    plan = resolve_human_notes_guided_cluster_plan(chapter_rows_by_language, source_index)

    selected_clusters = plan["selected_clusters"]
    selected_counts = Counter(cluster["source_id"] for cluster in selected_clusters)
    assert 6 <= len(selected_clusters) <= 8
    assert len(selected_counts) == 5
    assert min(selected_counts.values()) == 1
    assert max(selected_counts.values()) == 2
    assert plan["resolution_summary"]["selected_cluster_count"] == len(selected_clusters)
    assert "definition" in plan["selection_groups"]
    assert "bridge" in plan["selection_groups"]
    assert any(cluster.get("cross_chapter_window") for cluster in selected_clusters)


def test_collect_source_build_state_honors_explicit_chapter_case_ids(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "demo.epub"
    _write(source_path, "demo")

    monkeypatch.setattr(
        builder_module,
        "load_private_library_source_items",
        lambda **_kwargs: [
            {
                "spec": CandidateSpec(
                    source_id="demo_private_en",
                    title="Demo Book",
                    author="Demo Author",
                    language="en",
                    origin="managed-library-source",
                    storage_mode="local-only",
                    promoted_local_path="en/demo.epub",
                    acquisition={"kind": "managed_source_catalog"},
                    type_tags=["essay"],
                    role_tags=["argumentative"],
                    selection_priority=1,
                    notes=[],
                ),
                "source_path": source_path,
                "acquisition_batch_id": "batch_a",
                "origin_filename": "demo.epub",
                "relative_local_path": "state/library_sources/en/demo.epub",
            }
        ],
    )
    monkeypatch.setattr(
        builder_module,
        "screen_source_book",
        lambda **_kwargs: {
            "source_id": "demo_private_en",
            "title": "Demo Book",
            "author": "Demo Author",
            "language": "en",
            "type_tags": ["essay"],
            "role_tags": ["argumentative"],
            "relative_local_path": "state/library_sources/en/demo.epub",
            "sha256": "abc",
            "file_size": 4,
            "output_dir": "outputs/demo_private_en",
            "corpus_lane": "chapter_corpus_eligible",
            "selection_priority": 1,
            "candidate_chapters": [
                {
                    "chapter_id": "17",
                    "chapter_number": 17,
                    "chapter_title": "Keep Me",
                    "sentence_count": 80,
                    "paragraph_count": 16,
                    "position_bucket": "middle",
                    "score": 4.5,
                },
                {
                    "chapter_id": "24",
                    "chapter_number": 24,
                    "chapter_title": "Drop Me",
                    "sentence_count": 84,
                    "paragraph_count": 20,
                    "position_bucket": "late",
                    "score": 4.2,
                },
            ],
        },
    )

    config = resolve_build_config(
        SupplementBuildOptions(
            scratch=True,
            run_id="clustered_chapter_filter",
            benchmark_mode=CLUSTERED_BENCHMARK_MODE,
            chapter_case_ids=("demo_private_en__17",),
            feedback_dataset_ids={},
        ),
        root=root,
        manifest_root=root / "eval" / "manifests",
        local_dataset_root=root / "state" / "eval_local_datasets",
    )

    state = builder_module.collect_source_build_state(config)

    assert [row["chapter_case_id"] for row in state.chapter_rows_by_language["en"]] == [
        "demo_private_en__17"
    ]


def test_collect_source_build_state_human_notes_mode_uses_full_book_chapter_pool(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "demo.epub"
    _write(source_path, "demo")
    monkeypatch.setattr(builder_module, "HUMAN_NOTES_GUIDED_SOURCE_IDS", ("value_of_others_private_en",))

    monkeypatch.setattr(
        builder_module,
        "load_private_library_source_items",
        lambda **_kwargs: [
            {
                "spec": CandidateSpec(
                    source_id="value_of_others_private_en",
                    title="The Value of Others",
                    author="Demo Author",
                    language="en",
                    origin="managed-library-source",
                    storage_mode="local-only",
                    promoted_local_path="en/demo.epub",
                    acquisition={"kind": "managed_source_catalog"},
                    type_tags=["essay"],
                    role_tags=["argumentative"],
                    selection_priority=1,
                    notes=[],
                ),
                "source_path": source_path,
                "acquisition_batch_id": "batch_a",
                "origin_filename": "demo.epub",
                "relative_local_path": "state/library_sources/en/demo.epub",
            }
        ],
    )
    monkeypatch.setattr(
        builder_module,
        "screen_source_book",
        lambda **_kwargs: {
            "source_id": "value_of_others_private_en",
            "title": "The Value of Others",
            "author": "Demo Author",
            "language": "en",
            "type_tags": ["essay"],
            "role_tags": ["argumentative"],
            "relative_local_path": "state/library_sources/en/demo.epub",
            "sha256": "abc",
            "file_size": 4,
            "output_dir": "outputs/value_of_others_private_en",
            "corpus_lane": "chapter_corpus_eligible",
            "selection_priority": 1,
            "candidate_chapters": [
                {
                    "chapter_id": "2",
                    "chapter_number": 2,
                    "chapter_title": "Screened Only",
                    "sentence_count": 70,
                    "paragraph_count": 14,
                    "position_bucket": "middle",
                    "score": 4.2,
                }
            ],
        },
    )
    monkeypatch.setattr(
        builder_module,
        "load_book_document",
        lambda _path: {
            "chapters": [
                {
                    "id": "1",
                    "chapter_number": 1,
                    "title": "Chapter 1",
                    "paragraphs": [{}, {}],
                    "sentences": [{"text": "A"}, {"text": "B"}],
                },
                {
                    "id": "2",
                    "chapter_number": 2,
                    "title": "Chapter 2",
                    "paragraphs": [{}, {}, {}],
                    "sentences": [{"text": "A"}, {"text": "B"}, {"text": "C"}],
                },
                {
                    "id": "3",
                    "chapter_number": 3,
                    "title": "Chapter 3",
                    "paragraphs": [{}],
                    "sentences": [{"text": "A"}],
                },
            ]
        },
    )

    config = resolve_build_config(
        SupplementBuildOptions(
            scratch=True,
            run_id="human_notes_full_pool",
            benchmark_mode=HUMAN_NOTES_GUIDED_BENCHMARK_MODE,
            feedback_dataset_ids={},
        ),
        root=root,
        manifest_root=root / "eval" / "manifests",
        local_dataset_root=root / "state" / "eval_local_datasets",
    )

    state = builder_module.collect_source_build_state(config)

    assert [row["chapter_case_id"] for row in state.chapter_rows_by_language["en"]] == [
        "value_of_others_private_en__1",
        "value_of_others_private_en__2",
        "value_of_others_private_en__3",
    ]
    assert all(row["selection_status"] == "human_notes_guided_candidate_v1" for row in state.chapter_rows_by_language["en"])


def test_main_wires_question_aligned_excerpt_outputs_without_using_old_seed_builder(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "demo.epub"
    _write(source_path, "demo")
    _write_json(
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / "attentional_v2_private_library_excerpt_en_v2"
        / "cases.jsonl",
        [],
    )
    legacy_feedback_path = (
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / "attentional_v2_private_library_excerpt_en_v2"
        / "cases.jsonl"
    )
    legacy_feedback_path.write_text(
        json.dumps(
            {
                "case_id": "legacy_en_case",
                "target_profile_id": "distinction_definition",
                "benchmark_status": "needs_revision",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(builder_module, "ROOT", root)
    monkeypatch.setattr(builder_module, "MANIFEST_ROOT", root / "eval" / "manifests")
    monkeypatch.setattr(builder_module, "STATE_LOCAL_DATASET_ROOT", root / "state" / "eval_local_datasets")
    monkeypatch.setattr(
        builder_module,
        "load_private_library_source_items",
        lambda **_kwargs: [
            {
                "spec": CandidateSpec(
                    source_id="demo_private_en",
                    title="Demo Book",
                    author="Demo Author",
                    language="en",
                    origin="managed-library-source",
                    storage_mode="local-only",
                    promoted_local_path="en/demo.epub",
                    acquisition={"kind": "managed_source_catalog"},
                    type_tags=["essay"],
                    role_tags=["argumentative"],
                    selection_priority=1,
                    notes=[],
                ),
                "source_path": source_path,
                "acquisition_batch_id": "batch_a",
                "origin_filename": "demo.epub",
                "relative_local_path": "state/library_sources/en/demo.epub",
            }
        ],
    )
    monkeypatch.setattr(
        builder_module,
        "screen_source_book",
        lambda **_kwargs: {
            "source_id": "demo_private_en",
            "title": "Demo Book",
            "author": "Demo Author",
            "language": "en",
            "type_tags": ["essay"],
            "role_tags": ["argumentative"],
            "relative_local_path": "state/library_sources/en/demo.epub",
            "sha256": "abc",
            "file_size": 4,
            "output_dir": "outputs/demo_private_en",
            "corpus_lane": "chapter_corpus_eligible",
            "selection_priority": 1,
            "candidate_chapters": [
                {
                    "chapter_id": "1",
                    "chapter_number": 1,
                    "chapter_title": "Chapter 1",
                    "sentence_count": 6,
                    "paragraph_count": 3,
                    "position_bucket": "middle",
                    "score": 4.5,
                }
            ],
        },
    )
    monkeypatch.setattr(
        builder_module,
        "load_book_document",
        lambda _path: {
            "chapters": [
                {
                    "id": "1",
                    "sentences": [
                        {
                            "sentence_id": "c1-s1",
                            "text": "Rather than chasing applause, the author defines integrity as refusing the easy comfort everyone else wants him to accept.",
                        },
                        {
                            "sentence_id": "c1-s2",
                            "text": "But that confidence turns out fragile, and the chapter suddenly asks why the speaker needed public praise after claiming independence.",
                        },
                        {
                            "sentence_id": "c1-s3",
                            "text": "Again the writer returns to the same promise from earlier, comparing this hesitation with the first vow to stand apart.",
                        },
                        {
                            "sentence_id": "c1-s4",
                            "text": "Only then does the chapter admit that the decision would matter differently later, after the public failure had already exposed its weakness.",
                        },
                    ],
                }
            ]
        },
    )
    monkeypatch.setattr(
        builder_module,
        "make_runtime_fixtures",
        lambda rows: [{"fixture_id": row["chapter_case_id"]} for row in rows],
    )
    monkeypatch.setattr(
        builder_module,
        "make_compatibility_fixtures",
        lambda rows: [{"fixture_id": row["chapter_case_id"]} for row in rows],
    )

    builder_module.main(["--no-bootstrap-catalog-if-missing"])

    new_dataset_dir = (
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / "attentional_v2_private_library_excerpt_en_question_aligned_v1"
    )
    cases_path = new_dataset_dir / "cases.jsonl"
    manifest_path = new_dataset_dir / "manifest.json"
    adequacy_path = (
        root
        / "state"
        / "dataset_build"
        / "adequacy_reports"
        / "attentional_v2_private_library_excerpt_question_aligned_v1.json"
    )

    assert cases_path.exists()
    assert manifest_path.exists()
    assert adequacy_path.exists()

    cases = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    adequacy = json.loads(adequacy_path.read_text(encoding="utf-8"))

    assert len(cases) == 1
    assert cases[0]["target_profile_id"]
    assert manifest["feedback_source_dataset_id"] == "attentional_v2_private_library_excerpt_en_v2"
    assert any(
        ref.endswith("attentional_v2_private_library_excerpt_en_question_aligned_v1.jsonl")
        for ref in manifest["dataset_build_artifact_refs"]
    )
    assert adequacy["recommended_next_action"] == "review_existing_cases"


def test_main_scratch_build_writes_run_scoped_outputs_without_touching_live_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "demo.epub"
    _write(source_path, "demo")
    legacy_feedback_path = (
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / "attentional_v2_private_library_excerpt_en_v2"
        / "cases.jsonl"
    )
    legacy_feedback_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_feedback_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(builder_module, "ROOT", root)
    monkeypatch.setattr(builder_module, "MANIFEST_ROOT", root / "eval" / "manifests")
    monkeypatch.setattr(builder_module, "STATE_LOCAL_DATASET_ROOT", root / "state" / "eval_local_datasets")
    monkeypatch.setattr(
        builder_module,
        "load_private_library_source_items",
        lambda **_kwargs: [
            {
                "spec": CandidateSpec(
                    source_id="demo_private_en",
                    title="Demo Book",
                    author="Demo Author",
                    language="en",
                    origin="managed-library-source",
                    storage_mode="local-only",
                    promoted_local_path="en/demo.epub",
                    acquisition={"kind": "managed_source_catalog"},
                    type_tags=["essay"],
                    role_tags=["argumentative"],
                    selection_priority=1,
                    notes=[],
                ),
                "source_path": source_path,
                "acquisition_batch_id": "batch_a",
                "origin_filename": "demo.epub",
                "relative_local_path": "state/library_sources/en/demo.epub",
            }
        ],
    )
    monkeypatch.setattr(
        builder_module,
        "screen_source_book",
        lambda **_kwargs: {
            "source_id": "demo_private_en",
            "title": "Demo Book",
            "author": "Demo Author",
            "language": "en",
            "type_tags": ["essay"],
            "role_tags": ["argumentative"],
            "relative_local_path": "state/library_sources/en/demo.epub",
            "sha256": "abc",
            "file_size": 4,
            "output_dir": "outputs/demo_private_en",
            "corpus_lane": "chapter_corpus_eligible",
            "selection_priority": 1,
            "candidate_chapters": [
                {
                    "chapter_id": "1",
                    "chapter_number": 1,
                    "chapter_title": "Chapter 1",
                    "sentence_count": 6,
                    "paragraph_count": 3,
                    "position_bucket": "middle",
                    "score": 4.5,
                }
            ],
        },
    )
    monkeypatch.setattr(
        builder_module,
        "load_book_document",
        lambda _path: {
            "chapters": [
                {
                    "id": "1",
                    "sentences": [
                        {
                            "sentence_id": "c1-s1",
                            "text": "Rather than chasing applause, the author defines integrity as refusing the easy comfort everyone else wants him to accept.",
                        },
                        {
                            "sentence_id": "c1-s2",
                            "text": "But that confidence turns out fragile, and the chapter suddenly asks why the speaker needed public praise after claiming independence.",
                        },
                        {
                            "sentence_id": "c1-s3",
                            "text": "Again the writer returns to the same promise from earlier, comparing this hesitation with the first vow to stand apart.",
                        },
                        {
                            "sentence_id": "c1-s4",
                            "text": "Only then does the chapter admit that the decision would matter differently later, after the public failure had already exposed its weakness.",
                        },
                    ],
                }
            ]
        },
    )
    monkeypatch.setattr(
        builder_module,
        "make_runtime_fixtures",
        lambda rows: [{"fixture_id": row["chapter_case_id"]} for row in rows],
    )
    monkeypatch.setattr(
        builder_module,
        "make_compatibility_fixtures",
        lambda rows: [{"fixture_id": row["chapter_case_id"]} for row in rows],
    )

    builder_module.main(
        ["--scratch", "--run-id", "scratch_demo", "--no-bootstrap-catalog-if-missing"]
    )

    scratch_dataset_id = "attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__scratch_demo"
    scratch_dataset_dir = (
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / scratch_dataset_id
    )
    run_root = root / "state" / "dataset_build" / "build_runs" / "scratch_demo"
    live_dataset_dir = (
        root
        / "state"
        / "eval_local_datasets"
        / "excerpt_cases"
        / "attentional_v2_private_library_excerpt_en_question_aligned_v1"
    )
    tracked_manifest_path = (
        root / "eval" / "manifests" / "source_books" / "attentional_v2_private_library_screen_v2.json"
    )
    summary_path = run_root / "build_summary.json"
    adequacy_path = (
        run_root
        / "adequacy_reports"
        / "attentional_v2_private_library_excerpt_question_aligned_v1__scratch__scratch_demo.json"
    )
    source_manifest_path = (
        run_root
        / "manifests"
        / "source_books"
        / "attentional_v2_private_library_screen_v2__scratch__scratch_demo.json"
    )

    assert scratch_dataset_dir.exists()
    assert (scratch_dataset_dir / "cases.jsonl").exists()
    assert not live_dataset_dir.exists()
    assert not tracked_manifest_path.exists()
    assert summary_path.exists()
    assert adequacy_path.exists()
    assert source_manifest_path.exists()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    manifest = json.loads((scratch_dataset_dir / "manifest.json").read_text(encoding="utf-8"))
    assert summary["scratch"] is True
    assert summary["dataset_ids"]["excerpt_cases"]["en"] == scratch_dataset_id
    assert manifest["feedback_source_dataset_id"] == "attentional_v2_private_library_excerpt_en_v2"


def test_main_human_notes_guided_mode_writes_note_guided_artifacts_and_isolated_ids(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    captured: dict[str, object] = {}

    monkeypatch.setattr(builder_module, "ROOT", root)
    monkeypatch.setattr(builder_module, "MANIFEST_ROOT", root / "eval" / "manifests")
    monkeypatch.setattr(builder_module, "STATE_LOCAL_DATASET_ROOT", root / "state" / "eval_local_datasets")

    source_specs = [
        ("book_1_en", "Book 1", "en", 1),
        ("book_2_en", "Book 2", "en", 2),
        ("book_3_en", "Book 3", "en", 3),
        ("book_4_zh", "书 4", "zh", 4),
        ("book_5_zh", "书 5", "zh", 5),
    ]
    selected_source_ids = [source_id for source_id, *_rest in source_specs]
    monkeypatch.setattr(builder_module, "HUMAN_NOTES_GUIDED_SOURCE_IDS", tuple(selected_source_ids))
    items = []
    for source_id, title, language, priority in source_specs:
        source_path = root / "state" / "library_sources" / language / f"{source_id}.epub"
        _write(source_path, "demo")
        items.append(
            {
                "spec": CandidateSpec(
                    source_id=source_id,
                    title=title,
                    author=f"{title} Author",
                    language=language,
                    origin="managed-library-source",
                    storage_mode="local-only",
                    promoted_local_path=f"{language}/{source_id}.epub",
                    acquisition={"kind": "managed_source_catalog"},
                    type_tags=["essay"],
                    role_tags=["argumentative"],
                    selection_priority=priority,
                    notes=[f"{title} notes"],
                ),
                "source_path": source_path,
                "acquisition_batch_id": "notes_batch",
                "origin_filename": f"{source_id}.epub",
                "relative_local_path": f"state/library_sources/{language}/{source_id}.epub",
                "human_notes_guidance": {
                    "summary": f"{title} summary",
                    "artifact_refs": [f"notes/{source_id}.md"],
                    "cluster_proposals": [
                        {
                            "cluster_id": f"{source_id}__cluster_1",
                            "chapter_id": "1",
                            "selection_group": "definition" if priority % 2 else "tension",
                            "summary": f"{title} first cluster",
                        },
                        {
                            "cluster_id": f"{source_id}__cluster_2",
                            "chapter_id": "2",
                            "selection_group": "bridge" if priority <= 3 else "clarification",
                            "summary": f"{title} second cluster",
                            "cross_chapter_window": {
                                "start_chapter_id": "1",
                                "end_chapter_id": "2",
                                "summary": f"{title} window",
                            },
                        },
                    ],
                },
            }
        )

    monkeypatch.setattr(builder_module, "load_private_library_source_items", lambda **_kwargs: items)

    def _screen_source_book(**kwargs):
        spec = kwargs["spec"]
        return {
            "source_id": spec.source_id,
            "title": spec.title,
            "author": spec.author,
            "language": spec.language,
            "type_tags": ["essay"],
            "role_tags": ["argumentative"],
            "relative_local_path": kwargs["relative_local_path"],
            "sha256": f"sha-{spec.source_id}",
            "file_size": 4,
            "output_dir": f"outputs/{spec.source_id}",
            "corpus_lane": "chapter_corpus_eligible",
            "selection_priority": spec.selection_priority,
            "notes": list(spec.notes),
            "candidate_chapters": [
                {
                    "chapter_id": "1",
                    "chapter_number": 1,
                    "chapter_title": "Chapter 1",
                    "sentence_count": 24,
                    "paragraph_count": 8,
                    "position_bucket": "middle",
                    "score": 4.8,
                },
                {
                    "chapter_id": "2",
                    "chapter_number": 2,
                    "chapter_title": "Chapter 2",
                    "sentence_count": 28,
                    "paragraph_count": 9,
                    "position_bucket": "late",
                    "score": 4.6,
                },
            ],
        }

    monkeypatch.setattr(builder_module, "screen_source_book", _screen_source_book)
    monkeypatch.setattr(
        builder_module,
        "load_book_document",
        lambda _path: {
            "chapters": [
                {
                    "id": "1",
                    "chapter_number": 1,
                    "title": "Chapter 1",
                    "paragraphs": [{}, {}],
                    "sentences": [{"text": "A"}, {"text": "B"}],
                },
                {
                    "id": "2",
                    "chapter_number": 2,
                    "title": "Chapter 2",
                    "paragraphs": [{}, {}, {}],
                    "sentences": [{"text": "A"}, {"text": "B"}, {"text": "C"}],
                },
            ]
        },
    )

    def _build_question_aligned_excerpt_scope(**kwargs):
        chapter_rows_by_language = kwargs["chapter_rows_by_language"]
        captured["chapter_rows_by_language"] = chapter_rows_by_language
        cases_by_language = {
            language: [
                {
                    "case_id": f"{row['chapter_case_id']}__tension_reversal__seed_1",
                    "chapter_case_id": row["chapter_case_id"],
                    "target_profile_id": "tension_reversal",
                    "selection_group_id": row.get("selection_group_id", ""),
                }
                for row in rows
            ]
            for language, rows in chapter_rows_by_language.items()
        }
        opportunity_cards = [
            {
                "case_id": f"{row['chapter_case_id']}__opportunity",
                "chapter_case_id": row["chapter_case_id"],
                "language_track": language,
            }
            for language, rows in chapter_rows_by_language.items()
            for row in rows
        ]
        return {
            "scope_id": kwargs["scope_id"],
            "target_profiles": [{"target_profile_id": "tension_reversal"}],
            "opportunity_cards": opportunity_cards,
            "cases_by_language": cases_by_language,
            "reserve_cases_by_language": {"en": [], "zh": []},
            "adequacy_report": {
                "scope_id": kwargs["scope_id"],
                "recommended_next_action": "review_existing_cases",
            },
        }

    monkeypatch.setattr(
        builder_module,
        "build_question_aligned_excerpt_scope",
        _build_question_aligned_excerpt_scope,
    )
    monkeypatch.setattr(
        builder_module,
        "build_human_notes_guided_cluster_plan",
        lambda **_kwargs: {
            "selected_source_ids": list(selected_source_ids),
            "selected_chapter_case_ids": [
                "book_1_en__1",
                "book_1_en__2",
                "book_2_en__1",
                "book_2_en__2",
                "book_3_en__1",
                "book_4_zh__1",
                "book_5_zh__1",
                "book_5_zh__2",
            ],
            "selected_chapter_rows_by_language": {
                "en": [
                    {
                        "chapter_case_id": "book_1_en__1",
                        "source_id": "book_1_en",
                        "book_title": "Book 1",
                        "author": "Book 1 Author",
                        "language_track": "en",
                        "chapter_id": "1",
                        "chapter_number": 1,
                        "chapter_title": "Chapter 1",
                        "sentence_count": 24,
                        "selection_group_id": "book_1_en__cluster_1",
                        "selection_group_kind": "notes_guided_cluster",
                        "selection_group_label": "Book 1 cluster 1",
                    },
                    {
                        "chapter_case_id": "book_1_en__2",
                        "source_id": "book_1_en",
                        "book_title": "Book 1",
                        "author": "Book 1 Author",
                        "language_track": "en",
                        "chapter_id": "2",
                        "chapter_number": 2,
                        "chapter_title": "Chapter 2",
                        "sentence_count": 28,
                        "selection_group_id": "book_1_en__cluster_1",
                        "selection_group_kind": "notes_guided_cluster",
                        "selection_group_label": "Book 1 cluster 1",
                    },
                    {
                        "chapter_case_id": "book_2_en__1",
                        "source_id": "book_2_en",
                        "book_title": "Book 2",
                        "author": "Book 2 Author",
                        "language_track": "en",
                        "chapter_id": "1",
                        "chapter_number": 1,
                        "chapter_title": "Chapter 1",
                        "sentence_count": 24,
                        "selection_group_id": "book_2_en__cluster_1",
                        "selection_group_kind": "notes_guided_cluster",
                        "selection_group_label": "Book 2 cluster 1",
                    },
                    {
                        "chapter_case_id": "book_2_en__2",
                        "source_id": "book_2_en",
                        "book_title": "Book 2",
                        "author": "Book 2 Author",
                        "language_track": "en",
                        "chapter_id": "2",
                        "chapter_number": 2,
                        "chapter_title": "Chapter 2",
                        "sentence_count": 28,
                        "selection_group_id": "book_2_en__cluster_2",
                        "selection_group_kind": "notes_guided_cluster",
                        "selection_group_label": "Book 2 cluster 2",
                    },
                    {
                        "chapter_case_id": "book_3_en__1",
                        "source_id": "book_3_en",
                        "book_title": "Book 3",
                        "author": "Book 3 Author",
                        "language_track": "en",
                        "chapter_id": "1",
                        "chapter_number": 1,
                        "chapter_title": "Chapter 1",
                        "sentence_count": 24,
                        "selection_group_id": "book_3_en__cluster_1",
                        "selection_group_kind": "notes_guided_cluster",
                        "selection_group_label": "Book 3 cluster 1",
                    },
                ],
                "zh": [
                    {
                        "chapter_case_id": "book_4_zh__1",
                        "source_id": "book_4_zh",
                        "book_title": "书 4",
                        "author": "书 4 Author",
                        "language_track": "zh",
                        "chapter_id": "1",
                        "chapter_number": 1,
                        "chapter_title": "Chapter 1",
                        "sentence_count": 24,
                        "selection_group_id": "book_4_zh__cluster_1",
                        "selection_group_kind": "notes_guided_cluster",
                        "selection_group_label": "书4 cluster 1",
                    },
                    {
                        "chapter_case_id": "book_5_zh__1",
                        "source_id": "book_5_zh",
                        "book_title": "书 5",
                        "author": "书 5 Author",
                        "language_track": "zh",
                        "chapter_id": "1",
                        "chapter_number": 1,
                        "chapter_title": "Chapter 1",
                        "sentence_count": 24,
                        "selection_group_id": "book_5_zh__cluster_1",
                        "selection_group_kind": "notes_guided_cluster",
                        "selection_group_label": "书5 cluster 1",
                    },
                    {
                        "chapter_case_id": "book_5_zh__2",
                        "source_id": "book_5_zh",
                        "book_title": "书 5",
                        "author": "书 5 Author",
                        "language_track": "zh",
                        "chapter_id": "2",
                        "chapter_number": 2,
                        "chapter_title": "Chapter 2",
                        "sentence_count": 28,
                        "selection_group_id": "book_5_zh__cluster_2",
                        "selection_group_kind": "notes_guided_cluster",
                        "selection_group_label": "书5 cluster 2",
                    },
                ],
            },
            "selected_rows_by_language": {},
            "selected_clusters": [
                {
                    "cluster_id": "book_1_en__cluster_1",
                    "cluster_label": "Book 1 cluster 1",
                    "source_id": "book_1_en",
                    "language_track": "en",
                    "chapter_case_ids": ["book_1_en__1", "book_1_en__2"],
                },
                {
                    "cluster_id": "book_2_en__cluster_1",
                    "cluster_label": "Book 2 cluster 1",
                    "source_id": "book_2_en",
                    "language_track": "en",
                    "chapter_case_ids": ["book_2_en__1"],
                },
                {
                    "cluster_id": "book_2_en__cluster_2",
                    "cluster_label": "Book 2 cluster 2",
                    "source_id": "book_2_en",
                    "language_track": "en",
                    "chapter_case_ids": ["book_2_en__2"],
                },
                {
                    "cluster_id": "book_3_en__cluster_1",
                    "cluster_label": "Book 3 cluster 1",
                    "source_id": "book_3_en",
                    "language_track": "en",
                    "chapter_case_ids": ["book_3_en__1"],
                },
                {
                    "cluster_id": "book_4_zh__cluster_1",
                    "cluster_label": "Book 4 cluster 1",
                    "source_id": "book_4_zh",
                    "language_track": "zh",
                    "chapter_case_ids": ["book_4_zh__1"],
                },
                {
                    "cluster_id": "book_5_zh__cluster_1",
                    "cluster_label": "Book 5 cluster 1",
                    "source_id": "book_5_zh",
                    "language_track": "zh",
                    "chapter_case_ids": ["book_5_zh__1"],
                },
                {
                    "cluster_id": "book_5_zh__cluster_2",
                    "cluster_label": "Book 5 cluster 2",
                    "source_id": "book_5_zh",
                    "language_track": "zh",
                    "chapter_case_ids": ["book_5_zh__2"],
                },
                {
                    "cluster_id": "book_1_en__cluster_2",
                    "cluster_label": "Book 1 cluster 2",
                    "source_id": "book_1_en",
                    "language_track": "en",
                    "chapter_case_ids": ["book_1_en__2"],
                },
            ],
            "cluster_proposals": [{"cluster_id": "book_1_en__cluster_1", "proposal_status": "eligible"}],
            "selection_groups": {
                "book_1_en__cluster_1": {
                    "selection_group_id": "book_1_en__cluster_1",
                    "chapter_case_ids": ["book_1_en__1", "book_1_en__2"],
                }
            },
            "source_note_summaries": [
                {
                    "source_id": source_id,
                    "note_artifact_refs": [f"state/library_notes/raw_exports/{source_id}/raw_export.md"],
                    "selected_cluster_ids": [f"{source_id}__cluster_1"],
                }
                for source_id in selected_source_ids
            ],
            "resolution_summary": {
                "selected_cluster_count": 8,
            },
            "skipped_sources": [],
        },
    )
    monkeypatch.setattr(
        builder_module,
        "make_runtime_fixtures",
        lambda rows: [{"fixture_id": row["chapter_case_id"]} for row in rows],
    )
    monkeypatch.setattr(
        builder_module,
        "make_compatibility_fixtures",
        lambda rows: [{"fixture_id": row["chapter_case_id"]} for row in rows],
    )

    builder_module.main(
        [
            "--benchmark-mode",
            HUMAN_NOTES_GUIDED_BENCHMARK_MODE,
            "--scratch",
            "--run-id",
            "human_notes_demo",
            "--no-feedback",
            "--no-bootstrap-catalog-if-missing",
        ]
    )

    run_root = root / "state" / "dataset_build" / "build_runs" / "human_notes_demo"
    summary = json.loads((run_root / "build_summary.json").read_text(encoding="utf-8"))
    en_manifest = json.loads(
        (
            root
            / "state"
            / "eval_local_datasets"
            / "excerpt_cases"
            / "attentional_v2_human_notes_guided_dataset_v1_excerpt_en__scratch__human_notes_demo"
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    splits_manifest = json.loads(
        (
            run_root
            / "manifests"
            / "splits"
            / "attentional_v2_human_notes_guided_dataset_v1_splits__scratch__human_notes_demo.json"
        ).read_text(encoding="utf-8")
    )

    selected_rows = captured["chapter_rows_by_language"]
    assert isinstance(selected_rows, dict)
    selected_counts = Counter(
        row["source_id"]
        for rows in selected_rows.values()
        for row in rows
    )
    assert len(selected_counts) == 5
    assert min(selected_counts.values()) == 1
    assert max(selected_counts.values()) == 2
    assert summary["note_guided_selected_cluster_count"] == 8
    assert len(summary["selected_chapter_case_ids"]) == 8
    assert summary["dataset_ids"]["excerpt_cases"]["en"] == (
        "attentional_v2_human_notes_guided_dataset_v1_excerpt_en__scratch__human_notes_demo"
    )
    assert any("cluster_proposals" in ref for ref in en_manifest["dataset_build_artifact_refs"])
    assert any("selection_group_maps" in ref for ref in en_manifest["dataset_build_artifact_refs"])
    assert any("cluster_resolutions" in ref for ref in summary["note_guided_artifact_refs"].values())
    assert splits_manifest["benchmark_shape"]["kind"] == "human_notes_guided_chapter_clusters"
    assert len(splits_manifest["selected_chapter_clusters"]) == 8
    assert "book_1_en__cluster_1" in splits_manifest["selection_groups"]


def test_builder_auto_bootstraps_source_catalog_when_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path
    source_path = root / "state" / "library_sources" / "en" / "walden_205.epub"
    _write(source_path, "demo")
    _write_json(
        root / "eval" / "manifests" / "source_books" / "attentional_v2_public_benchmark_pool_v2.json",
        {
            "books": [
                {
                    "source_id": "walden_205_en",
                    "title": "Walden",
                    "author": "Henry David Thoreau",
                    "language": "en",
                    "origin": "public-open-access",
                    "source_url": "https://www.gutenberg.org/ebooks/205",
                    "relative_local_path": "state/library_sources/en/walden_205.epub",
                    "type_tags": ["essay"],
                    "role_tags": ["argumentative"],
                    "selection_priority": 1,
                    "notes": ["Tracked public source."],
                }
            ]
        },
    )

    monkeypatch.setattr(builder_module, "ROOT", root)
    monkeypatch.setattr(builder_module, "MANIFEST_ROOT", root / "eval" / "manifests")
    monkeypatch.setattr(builder_module, "STATE_LOCAL_DATASET_ROOT", root / "state" / "eval_local_datasets")
    monkeypatch.setattr(
        builder_module,
        "screen_source_book",
        lambda **_kwargs: {
            "source_id": "walden_205_en",
            "title": "Walden",
            "author": "Henry David Thoreau",
            "language": "en",
            "type_tags": ["essay"],
            "role_tags": ["argumentative"],
            "relative_local_path": "state/library_sources/en/walden_205.epub",
            "sha256": "abc",
            "file_size": 4,
            "output_dir": "outputs/walden_205_en",
            "corpus_lane": "chapter_corpus_eligible",
            "selection_priority": 1,
            "candidate_chapters": [
                {
                    "chapter_id": "1",
                    "chapter_number": 1,
                    "chapter_title": "Where I Lived",
                    "sentence_count": 6,
                    "paragraph_count": 3,
                    "position_bucket": "middle",
                    "score": 4.5,
                }
            ],
        },
    )
    monkeypatch.setattr(
        builder_module,
        "load_book_document",
        lambda _path: {
            "chapters": [
                {
                    "id": "1",
                    "sentences": [
                        {
                            "sentence_id": "c1-s1",
                            "text": "Rather than chasing applause, the author defines integrity as refusing the easy comfort everyone else wants him to accept.",
                        },
                        {
                            "sentence_id": "c1-s2",
                            "text": "But that confidence turns out fragile, and the chapter suddenly asks why the speaker needed public praise after claiming independence.",
                        },
                        {
                            "sentence_id": "c1-s3",
                            "text": "Again the writer returns to the same promise from earlier, comparing this hesitation with the first vow to stand apart.",
                        },
                        {
                            "sentence_id": "c1-s4",
                            "text": "Only then does the chapter admit that the decision would matter differently later, after the public failure had already exposed its weakness.",
                        },
                    ],
                }
            ]
        },
    )
    monkeypatch.setattr(
        builder_module,
        "make_runtime_fixtures",
        lambda rows: [{"fixture_id": row["chapter_case_id"]} for row in rows],
    )
    monkeypatch.setattr(
        builder_module,
        "make_compatibility_fixtures",
        lambda rows: [{"fixture_id": row["chapter_case_id"]} for row in rows],
    )

    builder_module.main(["--scratch", "--run-id", "bootstrap_demo"])

    source_catalog_path = root / "state" / "dataset_build" / "source_catalog.json"
    summary_path = root / "state" / "dataset_build" / "build_runs" / "bootstrap_demo" / "build_summary.json"
    assert source_catalog_path.exists()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["source_catalog_bootstrap"] is not None
    assert summary["source_catalog_bootstrap"]["mode"] == "bootstrap_library_sources"
