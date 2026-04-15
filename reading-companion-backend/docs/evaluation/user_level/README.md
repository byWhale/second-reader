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
  - `bgjob_user_level_selective_v1_judged_parallel_retry1_20260415`
- orchestrator:
  - [orchestrate_user_level_selective_eval.py](../../../scripts/orchestrate_user_level_selective_eval.py)
- execution shape:
  - split by `segment x mechanism`
  - `attentional_v2` and `iterator_v1` now run as independent shards rather than serializing inside one per-book shard
- preserved failed attempt:
  - `bgjob_user_level_selective_v1_judged_parallel_20260414`
  - retained as failed evidence because shard-scoped runs were still evaluating note cases from other segments, which produced `KeyError` during note-case evaluation

When the first judged run lands, add it here with:

- run id
- compared mechanisms
- status
- one-line conclusion
- links to aggregate, report, and any checked-in interpretation

## Historical Predecessor

The older chapter-scoped `excerpt surface v1.1` reports remain available under [../excerpt/README.md](../excerpt/README.md), but that line is now historical / superseded rather than the active user-level pointer.
