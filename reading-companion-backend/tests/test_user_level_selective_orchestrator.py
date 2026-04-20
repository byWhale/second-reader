from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "orchestrate_user_level_selective_eval.py"
SPEC = importlib.util.spec_from_file_location("user_level_selective_orchestrator", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
orchestrator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = orchestrator
SPEC.loader.exec_module(orchestrator)


class _FakeProcess:
    def __init__(self, exit_code: int) -> None:
        self._exit_code = exit_code

    def poll(self):
        return self._exit_code


def test_filter_plans_by_shard_keys_keeps_requested_subset() -> None:
    plans = [
        orchestrator.ShardPlan(
            segment_id="seg_a",
            source_id="source_a",
            book_title="Book A",
            covered_note_count=2,
            mechanism_key="attentional_v2",
            target_id="target_a",
            shard_run_id="run/shards/source_a__attentional_v2",
        ),
        orchestrator.ShardPlan(
            segment_id="seg_a",
            source_id="source_a",
            book_title="Book A",
            covered_note_count=2,
            mechanism_key="iterator_v1",
            target_id="target_b",
            shard_run_id="run/shards/source_a__iterator_v1",
        ),
    ]

    filtered = orchestrator._filter_plans_by_shard_keys(plans, {"source_a::iterator_v1"})

    assert [plan.shard_key for plan in filtered] == ["source_a::iterator_v1"]


def test_wait_for_shards_retries_retryable_failure_once(monkeypatch, tmp_path: Path) -> None:
    plan = orchestrator.ShardPlan(
        segment_id="seg_a",
        source_id="source_a",
        book_title="Book A",
        covered_note_count=2,
        mechanism_key="attentional_v2",
        target_id="target_a",
        shard_run_id="run/shards/source_a__attentional_v2",
    )
    run_root = tmp_path / "run"
    log_path = run_root / "logs" / "source_a__attentional_v2.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("ReaderLLMError: Request timed out or interrupted.\n", encoding="utf-8")

    relaunched: list[str] = []

    monkeypatch.setattr(orchestrator, "_log_path_for_plan", lambda **kwargs: log_path)
    monkeypatch.setattr(
        orchestrator,
        "_reset_failed_shard_outputs",
        lambda _plan, preserve_output_dir=None: None,
    )
    monkeypatch.setattr(orchestrator.time, "sleep", lambda _seconds: None)

    def _relaunch(**kwargs):
        relaunched.append(kwargs["plan"].shard_key)
        return _FakeProcess(0)

    monkeypatch.setattr(orchestrator, "_launch_shard", _relaunch)

    exit_codes = orchestrator._wait_for_shards(
        processes={plan.shard_key: _FakeProcess(1)},
        plan_by_key={plan.shard_key: plan},
        manifest_path=tmp_path / "manifest.json",
        judge_mode="llm",
        run_root=run_root,
        max_attempts=2,
        retry_backoff_seconds=0,
        reuse_output_dirs={},
    )

    assert exit_codes == {plan.shard_key: 0}
    assert relaunched == [plan.shard_key]


def test_completed_output_dir_from_seed_runs_only_reuses_completed_outputs(tmp_path: Path, monkeypatch) -> None:
    plan = orchestrator.ShardPlan(
        segment_id="seg_a",
        source_id="source_a",
        book_title="Book A",
        covered_note_count=2,
        mechanism_key="iterator_v1",
        target_id="target_a",
        shard_run_id="target_run/shards/source_a__iterator_v1",
    )
    monkeypatch.setattr(orchestrator, "RUNS_ROOT", tmp_path)
    incomplete = (
        tmp_path
        / "seed_incomplete"
        / "shards"
        / "source_a__iterator_v1"
        / "outputs"
        / "seg_a"
        / "iterator_v1"
    )
    incomplete.joinpath("_runtime").mkdir(parents=True)
    incomplete.joinpath("_runtime", "run_state.json").write_text('{"status":"deep_reading"}\n', encoding="utf-8")
    completed = (
        tmp_path
        / "seed_completed"
        / "shards"
        / "source_a__iterator_v1"
        / "outputs"
        / "seg_a"
        / "iterator_v1"
    )
    completed.joinpath("_runtime").mkdir(parents=True)
    completed.joinpath("_runtime", "run_state.json").write_text('{"status":"completed"}\n', encoding="utf-8")

    selected = orchestrator._completed_output_dir_from_seed_runs(
        plan=plan,
        seed_run_ids=("seed_incomplete", "seed_completed"),
    )

    assert selected == completed


def test_completed_output_dir_from_same_run_reuses_completed_current_output(tmp_path: Path, monkeypatch) -> None:
    plan = orchestrator.ShardPlan(
        segment_id="seg_a",
        source_id="source_a",
        book_title="Book A",
        covered_note_count=2,
        mechanism_key="attentional_v2",
        target_id="target_a",
        shard_run_id="target_run/shards/source_a__attentional_v2",
    )
    monkeypatch.setattr(orchestrator, "RUNS_ROOT", tmp_path)
    completed = tmp_path / "target_run" / "shards" / "source_a__attentional_v2" / "outputs" / "seg_a" / "attentional_v2"
    completed.joinpath("_runtime").mkdir(parents=True)
    completed.joinpath("_runtime", "run_state.json").write_text('{"status":"completed"}\n', encoding="utf-8")

    selected = orchestrator._completed_output_dir_from_same_run(plan=plan)

    assert selected == completed


def test_reset_failed_shard_outputs_preserves_reuse_output_dir(tmp_path: Path, monkeypatch) -> None:
    plan = orchestrator.ShardPlan(
        segment_id="seg_a",
        source_id="source_a",
        book_title="Book A",
        covered_note_count=2,
        mechanism_key="attentional_v2",
        target_id="target_a",
        shard_run_id="target_run/shards/source_a__attentional_v2",
    )
    monkeypatch.setattr(orchestrator, "RUNS_ROOT", tmp_path)
    shard_root = tmp_path / "target_run" / "shards" / "source_a__attentional_v2"
    preserved_output_dir = shard_root / "outputs" / "seg_a" / "attentional_v2"
    preserved_output_dir.mkdir(parents=True)
    (preserved_output_dir / "payload.json").write_text("{}", encoding="utf-8")
    (shard_root / "summary").mkdir(parents=True)
    (shard_root / "summary" / "aggregate.json").write_text("{}", encoding="utf-8")

    orchestrator._reset_failed_shard_outputs(plan, preserve_output_dir=preserved_output_dir)

    assert preserved_output_dir.exists()
    assert not (shard_root / "summary").exists()
