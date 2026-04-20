from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "orchestrate_accumulation_v2_eval.py"
SPEC = importlib.util.spec_from_file_location("accumulation_v2_orchestrator", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
orchestrator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = orchestrator
SPEC.loader.exec_module(orchestrator)


def test_completed_output_dir_from_seed_runs_only_reuses_completed_outputs(tmp_path: Path, monkeypatch) -> None:
    plan = orchestrator.ShardPlan(
        segment_id="segment_a",
        source_id="source_a",
        book_title="Book A",
        case_count=2,
        mechanism_key="iterator_v1",
        target_id="target_a",
        shard_run_id="target_run/shards/source_a__iterator_v1",
    )
    monkeypatch.setattr(orchestrator, "RUNS_ROOT", tmp_path)
    incomplete = tmp_path / "seed_incomplete" / "shards" / "source_a__iterator_v1" / "outputs" / "segment_a" / "iterator_v1"
    incomplete.joinpath("_runtime").mkdir(parents=True)
    incomplete.joinpath("_runtime", "run_state.json").write_text('{"status":"deep_reading"}\n', encoding="utf-8")
    completed = tmp_path / "seed_completed" / "shards" / "source_a__iterator_v1" / "outputs" / "segment_a" / "iterator_v1"
    completed.joinpath("_runtime").mkdir(parents=True)
    completed.joinpath("_runtime", "run_state.json").write_text('{"status":"completed"}\n', encoding="utf-8")

    selected = orchestrator._completed_output_dir_from_seed_runs(
        plan=plan,
        seed_run_ids=("seed_incomplete", "seed_completed"),
    )

    assert selected == completed


def test_merge_shards_merges_case_payloads_by_mechanism(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(orchestrator, "RUNS_ROOT", tmp_path)
    selection = type(
        "Selection",
        (),
        {
            "dataset_dir": tmp_path / "dataset",
            "segments": [type("Segment", (), {"segment_id": "segment_a"})()],
            "cases": [type("Case", (), {"case_id": "case_a"})()],
            "formal_manifest_path": tmp_path / "manifest.json",
        },
    )()
    monkeypatch.setattr(
        orchestrator,
        "_load_case_ids_by_segment",
        lambda _manifest_path: ({"segment_a": ["case_a"]}, selection),
    )
    monkeypatch.setattr(orchestrator, "write_llm_usage_summary", lambda *args, **kwargs: None)

    shard_a = orchestrator.ShardPlan(
        segment_id="segment_a",
        source_id="source_a",
        book_title="Book A",
        case_count=1,
        mechanism_key="attentional_v2",
        target_id="target_a",
        shard_run_id="run/shards/source_a__attentional_v2",
    )
    shard_b = orchestrator.ShardPlan(
        segment_id="segment_a",
        source_id="source_a",
        book_title="Book A",
        case_count=1,
        mechanism_key="iterator_v1",
        target_id="target_b",
        shard_run_id="run/shards/source_a__iterator_v1",
    )
    for plan, mechanism_key in ((shard_a, "attentional_v2"), (shard_b, "iterator_v1")):
        shard_root = tmp_path / "run" / "shards" / f"source_a__{mechanism_key}"
        (shard_root / "summary").mkdir(parents=True, exist_ok=True)
        (shard_root / "summary" / "aggregate.json").write_text(
            json.dumps({"case_count": 1}, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (shard_root / "cases").mkdir(parents=True, exist_ok=True)
        (shard_root / "cases" / "case_a.json").write_text(
            json.dumps(
                {
                    "case_id": "case_a",
                    "output_language": "en",
                    "mechanism_results": {
                        mechanism_key: {
                            "status": "completed",
                            "judgment": {
                                "quality_score": 4,
                                "callback_score": 1,
                                "thread_built": "built",
                                "reason": "ok",
                            },
                        }
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    aggregate = orchestrator._merge_shards(
        run_id="run",
        manifest_path=tmp_path / "manifest.json",
        plans=[shard_a, shard_b],
        mechanism_keys=("attentional_v2", "iterator_v1"),
        selection=selection,
    )

    assert aggregate["case_count"] == 1
    assert aggregate["derived_comparison"]["winner_counts"] == {"tie": 1}
