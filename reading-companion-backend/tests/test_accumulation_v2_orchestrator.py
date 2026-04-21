from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "orchestrate_accumulation_v2_eval.py"
SPEC = importlib.util.spec_from_file_location("accumulation_v2_orchestrator", SCRIPT_PATH)
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


def test_assign_targets_balances_each_mechanism_across_targets() -> None:
    selected_segments = [
        {
            "segment_id": "seg_xidaduo",
            "source_id": "xidaduo",
            "book_title": "Xidaduo",
            "case_count": 6,
        },
        {
            "segment_id": "seg_huochu",
            "source_id": "huochu",
            "book_title": "Huochu",
            "case_count": 4,
        },
        {
            "segment_id": "seg_mangge",
            "source_id": "mangge",
            "book_title": "Mangge",
            "case_count": 2,
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


def test_wait_for_shards_fails_fast_and_stops_remaining_processes(monkeypatch, tmp_path: Path) -> None:
    failed_plan = orchestrator.ShardPlan(
        segment_id="segment_failed",
        source_id="source_failed",
        book_title="Book Failed",
        case_count=2,
        mechanism_key="attentional_v2",
        target_id="target_a",
        shard_run_id="run/shards/source_failed__attentional_v2",
    )
    running_plan = orchestrator.ShardPlan(
        segment_id="segment_running",
        source_id="source_running",
        book_title="Book Running",
        case_count=2,
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
        pending_plans=None,
        manifest_path=tmp_path / "manifest.json",
        judge_mode="llm",
        run_root=run_root,
        max_attempts=1,
        retry_backoff_seconds=0,
        reuse_output_dirs={},
    )

    assert exit_codes == {failed_plan.shard_key: 1}
    assert running_process.terminated is True


def test_wait_for_shards_waits_for_reuse_ready_before_launch(monkeypatch, tmp_path: Path) -> None:
    pending_plan = orchestrator.ShardPlan(
        segment_id="segment_pending",
        source_id="source_pending",
        book_title="Book Pending",
        case_count=2,
        mechanism_key="attentional_v2",
        target_id="target_a",
        shard_run_id="run/shards/source_pending__attentional_v2",
    )
    reuse_dir = tmp_path / "seed" / "outputs"
    calls = {"count": 0}
    launched: list[tuple[str, Path | None]] = []
    sleeps: list[int] = []

    def _fake_resolve_ready_reuse_output_dir(*, plan, seed_run_ids):
        assert plan == pending_plan
        assert seed_run_ids == ("seed_run",)
        calls["count"] += 1
        if calls["count"] < 2:
            return None
        return reuse_dir

    monkeypatch.setattr(orchestrator, "_resolve_ready_reuse_output_dir", _fake_resolve_ready_reuse_output_dir)
    monkeypatch.setattr(orchestrator.time, "sleep", lambda seconds: sleeps.append(int(seconds)))
    monkeypatch.setattr(
        orchestrator,
        "_launch_shard",
        lambda *, plan, manifest_path, judge_mode, run_root, reuse_output_dir=None: launched.append(
            (plan.shard_key, reuse_output_dir)
        )
        or _FakeProcess(0),
    )

    exit_codes = orchestrator._wait_for_shards(
        processes={},
        plan_by_key={},
        pending_plans={pending_plan.shard_key: pending_plan},
        manifest_path=tmp_path / "manifest.json",
        judge_mode="llm",
        run_root=tmp_path / "run",
        max_attempts=1,
        retry_backoff_seconds=0,
        reuse_output_dirs={},
        seed_run_ids=("seed_run",),
        wait_for_reuse_ready=True,
        reuse_ready_poll_seconds=7,
    )

    assert exit_codes == {pending_plan.shard_key: 0}
    assert launched == [(pending_plan.shard_key, reuse_dir)]
    assert sleeps == [7]


def test_update_catalog_only_for_complete_mechanism_set(monkeypatch, tmp_path: Path) -> None:
    upserts: list[dict] = []
    monkeypatch.setattr(orchestrator, "build_entry", lambda **kwargs: {"entry": kwargs})
    monkeypatch.setattr(orchestrator, "upsert_catalog_entry", lambda entry: upserts.append(entry))

    aggregate = {
        "dataset_dir": str(tmp_path / "dataset"),
        "manifest_path": str(tmp_path / "manifest.json"),
        "mechanisms": {
            "attentional_v2": {"average_quality_score": 2.5},
            "iterator_v1": {"average_quality_score": 3.0},
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
        mechanism_keys=("iterator_v1",),
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
    assert upserts[0]["entry"]["surface"] == "target_centered_accumulation_v2"
    assert upserts[0]["entry"]["status"] == "current_formal_evidence"
    assert "3.0" in upserts[0]["entry"]["one_line_conclusion"]
