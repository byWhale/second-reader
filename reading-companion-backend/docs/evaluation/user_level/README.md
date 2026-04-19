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

Current formal evidence bundle:

- run id:
  - `attentional_v2_user_level_selective_v1_repaired_rejudge_20260416`
- repaired sibling dataset root used by that run:
  - [manifest.json](../../../state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1_repaired_20260416/manifest.json)
- checked-in interpretation:
  - [attentional_v2_user_level_selective_v1_repaired_rejudge_20260416_interpretation.md](./attentional_v2_user_level_selective_v1_repaired_rejudge_20260416_interpretation.md)
- machine outputs:
  - [aggregate.json](../../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_repaired_rejudge_20260416/summary/aggregate.json)
  - [report.md](../../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_repaired_rejudge_20260416/summary/report.md)

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
  - `nawaer_baodian_private_zh` remains included after repairing the library-notes alignment fallback and then rebuilding the active package with a stricter body-start rule
  - current package size:
    - `5` reading segments
    - `202` note cases
  - current formal evidence bundle size:
    - `5` reading segments
    - `203` note cases
    - this count belongs to the repaired sibling package used by `attentional_v2_user_level_selective_v1_repaired_rejudge_20260416`
    - it does not silently replace the active `202`-case dataset pointer
  - every note case includes `source_span_slices` in the rendered segment coordinate system used by the reader runtime

## Body-Start Rule

- active `reading_segment`s start at the first real body unit, not at the absolute beginning of the source file
- the builder should skip front matter such as:
  - disclaimers
  - recommendation / preface / foreword / prologue material
  - editor or author notes about the book
  - timeline pages
  - part / chapter title stubs that do not yet begin the actual body reading
- a benchmark-local explicit body-start override is allowed when one known source still defeats the stable heuristic
- current active exception:
  - `nawaer_baodian_private_zh`
  - active body start is pinned to `c13` (`认识财富创造的原理`)
  - the old preface-side note at `c6` no longer participates in the active package
  - retained `nawaer` note cases still preserve their original aligned source spans; they were rebuilt, not trimmed

## Dataset Form

The active user-level dataset is stored as local JSON/JSONL plus rendered source text:

- `manifest.json`
- `segments.jsonl`
- `note_cases.jsonl`
- `segment_sources/*.txt`

For human auditing, a local-only Markdown export is now available:

- renderer:
  - [render_user_level_selective_audit.py](../../../eval/attentional_v2/render_user_level_selective_audit.py)
- default command:
  - `cd reading-companion-backend && .venv/bin/python eval/attentional_v2/render_user_level_selective_audit.py`
- default output directory:
  - `state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/audit_human_readable/`
- output shape:
  - `index.md`
  - `windows/<segment_id>.md`
- display note:
  - audit Markdown renders chapter titles as the human-facing “正文单元” label
  - raw `source_chapter_ids` are still shown separately as internal canonical-parse ids
  - those internal ids may include front matter offsets, so a book's visible first part/chapter can legitimately carry an internal id like `8`
  - these source ids are parse coordinates, not visible chapter numbers
- audit export is local-only and should not be treated as checked-in benchmark evidence

## Repair Workflow For Stale Note Alignment

If a note's `note_text` is clearly longer than its `source_span_text`, the first thing to suspect is stale managed-note alignment rather than missing source text.

- refresh managed notes assets in place:
  - `cd reading-companion-backend && .venv/bin/python eval/attentional_v2/refresh_library_notes_assets.py --linked-source-id huochu_shengming_de_yiyi_private_zh`
  - repeat `--linked-source-id` for multiple books, or use `--all`
- build a repaired dataset package without disturbing the active split manifest:
  - `cd reading-companion-backend && .venv/bin/python eval/attentional_v2/user_level_selective_v1.py --dataset-dir state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1_repaired_YYYYMMDD --dataset-id attentional_v2_user_level_selective_v1_repaired_YYYYMMDD --dataset-version YYYY-MM-DD --skip-split-manifest`
- render human-readable audit docs for that repaired package:
  - `cd reading-companion-backend && .venv/bin/python eval/attentional_v2/render_user_level_selective_audit.py --dataset-dir state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1_repaired_YYYYMMDD`

This repair path is intentionally split in two:

- managed `library_notes` entries are the durable alignment truth
- benchmark packages should be rebuilt from that truth
- if a judged run is currently using the active dataset package, prefer rebuilding into a versioned sibling path first instead of rewriting the active package in place

## Chapter Identity In This Benchmark

- public/product chapter identity still follows the global contract:
  - `chapter_id` = stable parsed-book chapter key
  - `chapter_number` = optional visible numeric ordinal
  - `chapter_ref` = human-facing reference label
- this benchmark package uses `source_chapter_id` / `source_chapter_ids` instead of bare `chapter_id` because its job is provenance and auditability, not public routing
- human audit exports should therefore show:
  - 正文单元标题
  - internal/source chapter id
  - never treat the internal/source id as the book's visible chapter number
- compatibility note:
  - the active runner and audit renderer currently accept both legacy `chapter_id` / `chapter_ids` and the converged `source_chapter_id` / `source_chapter_ids`
  - this keeps in-flight judged runs stable during the naming migration window
  - the next dataset rebuild should write only the `source_*` form

## Formal Runs

Current formal evidence bundle:

- completed repaired strict source-span rejudge:
  - run id:
    - `attentional_v2_user_level_selective_v1_repaired_rejudge_20260416`
  - status:
    - `completed`
  - dataset root:
    - `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1_repaired_20260416`
  - summary:
    - `attentional_v2` note recall: `0.0`
    - `iterator_v1` note recall: `0.2118`
  - interpretation:
    - [attentional_v2_user_level_selective_v1_repaired_rejudge_20260416_interpretation.md](./attentional_v2_user_level_selective_v1_repaired_rejudge_20260416_interpretation.md)

Historical execution and recovery chain:

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
- failed strict rejudge/reuse attempt:
  - job id:
    - `bgjob_user_level_selective_v1_rejudge_reuse_20260416`
  - run id:
    - `attentional_v2_user_level_selective_v1_rejudge_reuse_20260416`
  - status:
    - `failed`
  - watchdog:
    - `bgjob_job_registry_auto_recovery_watchdog_20260416` (`failed / stopped`)
  - expected behavior:
    - `8` shards use completed reading-output reuse
    - `2` `attentional_v2` shards re-read because their old outputs stopped at `deep_reading`

When an additional judged run lands, add it here with:

- run id
- compared mechanisms
- status
- one-line conclusion
- links to aggregate, report, and any checked-in interpretation

## Historical Predecessor

The older chapter-scoped `excerpt surface v1.1` reports remain available under [../excerpt/README.md](../excerpt/README.md), but that line is now historical / superseded rather than the active user-level pointer.
