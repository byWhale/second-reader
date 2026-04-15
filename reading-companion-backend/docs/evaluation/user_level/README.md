# User-Level Evaluation Reports

This directory is the active checked-in index for the note-aligned local/user-level benchmark.

The current active benchmark is `user-level selective v1`:

- active split manifest:
  - [attentional_v2_user_level_selective_v1_draft.json](../../../eval/manifests/splits/attentional_v2_user_level_selective_v1_draft.json)
- active dataset package:
  - [manifest.json](../../../state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/manifest.json)
  - [segments.jsonl](../../../state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/segments.jsonl)
  - [note_cases.jsonl](../../../state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/note_cases.jsonl)
- active comparison runner:
  - [run_user_level_selective_comparison.py](../../../eval/attentional_v2/run_user_level_selective_comparison.py)

## Current Status

- scope:
  - `reader_character.selective_legibility` only
- active metric:
  - note recall over aligned human notes
- active matching contract:
  - `exact_match` auto-counts
  - non-exact candidates go to judge
  - only `focused_hit` also counts toward recall
  - `incidental_cover` stays supporting-only
- current eligible source count:
  - `5 / 5`
  - `nawaer_baodian_private_zh` is now included after repairing the library-notes alignment fallback and re-registering its managed notes asset
  - current package size:
    - `5` reading segments
    - `203` note cases

## Formal Runs

The first judged run for this surface is now being launched:

- background job:
  - `bgjob_user_level_selective_v1_failed_shards_retry2_20260415`
- orchestrator:
  - [orchestrate_user_level_selective_eval.py](../../../scripts/orchestrate_user_level_selective_eval.py)
- execution shape:
  - split by `segment x mechanism`
  - `attentional_v2` and `iterator_v1` now run as independent shards rather than serializing inside one per-book shard
- preserved failed attempt:
  - `bgjob_user_level_selective_v1_judged_parallel_20260414`
  - retained as failed evidence because shard-scoped runs were still evaluating note cases from other segments, which produced `KeyError` during note-case evaluation
- preserved retry1 partial-failure attempt:
  - `bgjob_user_level_selective_v1_judged_parallel_retry1_20260415`
  - retained as failed evidence because the code bug was fixed but `7 / 10` shards still died on provider-side timeout / quota-cooldown / `520` / `529` instability
- current retry2 posture:
  - rerun only the failed `7` shards
  - reuse the `3` successful retry1 shard outputs during final merge
  - enable automatic shard retry inside the orchestrator for recoverable provider failures
    - `max_shard_attempts = 3`
    - `retry_backoff_seconds = 30`
  - enable registry-level long-horizon auto-recovery for the parent job itself
    - `auto_recovery_mode = recoverable`
    - `auto_recovery_interval_seconds = 300`
    - `auto_recovery_max_relaunches = 0` (`0` means unlimited)
  - live watchdog entrypoint:
    - [check_background_jobs.py](../../../scripts/check_background_jobs.py)
    - run shape:
      - `--watch --auto-recover --interval-seconds 300`
    - live artifacts:
      - `state/job_registry/background_job_watchdog.pid`
      - `state/job_registry/logs/background_job_watchdog.log`

When the first judged run lands, add it here with:

- run id
- compared mechanisms
- status
- one-line conclusion
- links to aggregate, report, and any checked-in interpretation

## Historical Predecessor

The older chapter-scoped `excerpt surface v1.1` reports remain available under [../excerpt/README.md](../excerpt/README.md), but that line is now historical / superseded rather than the active user-level pointer.
