from __future__ import annotations

import importlib.util
import io
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


class _RunningProcess:
    def __init__(self, exit_code_after_stop: int = -15) -> None:
        self._exit_code = None
        self._exit_code_after_stop = exit_code_after_stop
        self.terminated = False
        self.killed = False
        self._codex_log_handle = io.BytesIO()

    def poll(self):
        return self._exit_code

    def terminate(self) -> None:
        self.terminated = True
        self._exit_code = self._exit_code_after_stop

    def wait(self, timeout=None):
        return self._exit_code

    def kill(self) -> None:
        self.killed = True
        self._exit_code = -9


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


def test_assign_targets_balances_each_mechanism_across_targets() -> None:
    selected_segments = [
        {
            "segment_id": "seg_value",
            "source_id": "value",
            "book_title": "Value",
            "covered_note_count": 94,
        },
        {
            "segment_id": "seg_huochu",
            "source_id": "huochu",
            "book_title": "Huochu",
            "covered_note_count": 40,
        },
        {
            "segment_id": "seg_mangge",
            "source_id": "mangge",
            "book_title": "Mangge",
            "covered_note_count": 25,
        },
        {
            "segment_id": "seg_nawaer",
            "source_id": "nawaer",
            "book_title": "Nawaer",
            "covered_note_count": 24,
        },
        {
            "segment_id": "seg_xidaduo",
            "source_id": "xidaduo",
            "book_title": "Xidaduo",
            "covered_note_count": 20,
        },
    ]

    plans = orchestrator._assign_targets(
        selected_segments=selected_segments,
        mechanism_keys=("attentional_v2", "iterator_v1"),
        target_ids=("target_a", "target_b"),
        run_id="demo_run",
    )

    by_mechanism: dict[str, set[str]] = {}
    for plan in plans:
        by_mechanism.setdefault(plan.mechanism_key, set()).add(plan.target_id)

    assert by_mechanism["attentional_v2"] == {"target_a", "target_b"}
    assert by_mechanism["iterator_v1"] == {"target_a", "target_b"}


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


def test_wait_for_shards_fails_fast_and_stops_remaining_processes(monkeypatch, tmp_path: Path) -> None:
    failed_plan = orchestrator.ShardPlan(
        segment_id="seg_failed",
        source_id="source_failed",
        book_title="Book Failed",
        covered_note_count=2,
        mechanism_key="attentional_v2",
        target_id="target_a",
        shard_run_id="run/shards/source_failed__attentional_v2",
    )
    running_plan = orchestrator.ShardPlan(
        segment_id="seg_running",
        source_id="source_running",
        book_title="Book Running",
        covered_note_count=2,
        mechanism_key="iterator_v1",
        target_id="target_b",
        shard_run_id="run/shards/source_running__iterator_v1",
    )
    run_root = tmp_path / "run"
    failed_log_path = run_root / "logs" / "source_failed__attentional_v2.log"
    failed_log_path.parent.mkdir(parents=True, exist_ok=True)
    failed_log_path.write_text("Error code: 529 - overloaded_error\n", encoding="utf-8")
    running_log_path = run_root / "logs" / "source_running__iterator_v1.log"
    running_log_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        orchestrator,
        "_log_path_for_plan",
        lambda **kwargs: failed_log_path if kwargs["plan"].shard_key == failed_plan.shard_key else running_log_path,
    )
    monkeypatch.setattr(orchestrator.time, "sleep", lambda _seconds: None)

    running_process = _RunningProcess()
    exit_codes = orchestrator._wait_for_shards(
        processes={
            failed_plan.shard_key: _FakeProcess(1),
            running_plan.shard_key: running_process,
        },
        plan_by_key={
            failed_plan.shard_key: failed_plan,
            running_plan.shard_key: running_plan,
        },
        manifest_path=tmp_path / "manifest.json",
        judge_mode="llm",
        run_root=run_root,
        max_attempts=1,
        retry_backoff_seconds=0,
        reuse_output_dirs={},
    )

    assert exit_codes == {failed_plan.shard_key: 1}
    assert running_process.terminated is True


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


def test_update_catalog_only_for_complete_mechanism_set(monkeypatch, tmp_path: Path) -> None:
    upserts: list[dict] = []
    monkeypatch.setattr(orchestrator, "build_entry", lambda **kwargs: {"entry": kwargs})
    monkeypatch.setattr(orchestrator, "upsert_catalog_entry", lambda entry: upserts.append(entry))

    aggregate = {
        "dataset_dir": str(tmp_path / "dataset"),
        "manifest_path": str(tmp_path / "manifest.json"),
        "mechanisms": {
            "attentional_v2": {"note_recall": 0.3},
            "iterator_v1": {"note_recall": 0.1},
        },
    }

    orchestrator._update_catalog_or_warn(
        run_id="run_full",
        run_root=tmp_path / "run_full",
        aggregate=aggregate,
        mechanism_keys=("attentional_v2", "iterator_v1"),
        full_scope=True,
    )
    orchestrator._update_catalog_or_warn(
        run_id="run_filtered",
        run_root=tmp_path / "run_filtered",
        aggregate=aggregate,
        mechanism_keys=("attentional_v2",),
        full_scope=True,
    )
    orchestrator._update_catalog_or_warn(
        run_id="run_partial",
        run_root=tmp_path / "run_partial",
        aggregate=aggregate,
        mechanism_keys=("attentional_v2", "iterator_v1"),
        full_scope=False,
    )

    assert len(upserts) == 1
    assert upserts[0]["entry"]["surface"] == "user_level_selective_v1"
    assert upserts[0]["entry"]["status"] == "current_formal_evidence"
    assert "0.3" in upserts[0]["entry"]["one_line_conclusion"]
