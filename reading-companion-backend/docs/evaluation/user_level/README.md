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
  - candidate retrieval is strict `segment_source_v1` source-span overlap
  - text similarity and semantic similarity do not admit candidates
  - `exact_match` auto-counts only when canonical char spans are identical
  - non-exact source-overlap candidates go to judge
  - broad semantic-segment fallback spans may enter judge, but never auto-count as `exact_match`
  - only `focused_hit` also counts toward recall
  - `incidental_cover` stays supporting-only
  - visible reactions without usable source locators fail the run instead of falling back to string matching
- current eligible source count:
  - `5 / 5`
  - `nawaer_baodian_private_zh` is now included after repairing the library-notes alignment fallback and re-registering its managed notes asset
  - current package size:
    - `5` reading segments
    - `203` note cases
  - every note case includes `source_span_slices` in the rendered segment coordinate system used by the reader runtime

## Formal Runs

The first judged run for this surface should now use the strict source-span rejudge/reuse path:

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
- invalidated retry2 attempt:
  - `bgjob_user_level_selective_v1_failed_shards_retry2_20260415`
  - stopped on April 15 after discovering that the runner admitted candidates by string similarity rather than strict source-span overlap
  - retained only as bug-diagnostic evidence and must not be used as V1/V2 mechanism evidence
- reusable reading outputs:
  - all `5 / 5` `iterator_v1` shards have completed reading output and should be re-scored after rebuilding `segment_source_v1` locators
  - `attentional_v2` has completed reusable output for:
    - `huochu_shengming_de_yiyi_private_zh`
    - `nawaer_baodian_private_zh`
    - `value_of_others_private_en`
  - `attentional_v2` must re-read only:
    - `mangge_zhi_dao_private_zh`
    - `xidaduo_private_zh`
- rejudge-only behavior:
  - completed shards are rebuilt from old `outputs/<segment>/<mechanism>` directories without calling `read_book`
  - old scoring summaries remain invalid; the next formal result must regenerate `note_cases`, aggregate summary, and report under a new run id
- active strict rejudge/reuse run:
  - job id:
    - `bgjob_user_level_selective_v1_rejudge_reuse_20260416`
  - run id:
    - `attentional_v2_user_level_selective_v1_rejudge_reuse_20260416`
  - status:
    - `running`
  - watchdog:
    - `bgjob_job_registry_auto_recovery_watchdog_20260416`
  - expected behavior:
    - `8` shards use completed reading-output reuse
    - `2` `attentional_v2` shards re-read because their old outputs stopped at `deep_reading`

When the first judged run lands, add it here with:

- run id
- compared mechanisms
- status
- one-line conclusion
- links to aggregate, report, and any checked-in interpretation

## Historical Predecessor

The older chapter-scoped `excerpt surface v1.1` reports remain available under [../excerpt/README.md](../excerpt/README.md), but that line is now historical / superseded rather than the active user-level pointer.
