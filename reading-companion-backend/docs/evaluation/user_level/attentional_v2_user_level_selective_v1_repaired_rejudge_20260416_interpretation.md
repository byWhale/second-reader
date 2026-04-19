# User-Level Selective V1 Repaired Rejudge Interpretation

- Run ID: `attentional_v2_user_level_selective_v1_repaired_rejudge_20260416`
- Status: `completed`
- Surface: `user-level selective v1`
- Dataset root used by the run:
  - `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1_repaired_20260416`
- Important pointer boundary:
  - the current active dataset pointer still remains:
    - `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1`
  - this repaired rerun is therefore the current **formal evidence bundle**, not a silent promotion of the active dataset pointer

## Top-Line Result

- total note cases in this formal evidence run: `203`
- `attentional_v2`
  - note recall: `0.0`
  - exact match: `0`
  - focused hit: `0`
  - incidental cover: `0`
  - miss: `203`
- `iterator_v1`
  - note recall: `0.2118`
  - exact match: `13`
  - focused hit: `30`
  - incidental cover: `19`
  - miss: `141`
- pairwise delta:
  - `attentional_v2 - iterator_v1 = -0.2118`

## Interpretation

- This run is the first completed strict source-span formal evidence bundle on the repaired sibling package.
- The repaired package matters because it preserves the active body-start policy while also restoring one additional aligned note case that the active `202`-case package does not currently carry.
- The result is currently stark:
  - `iterator_v1` produces usable source-grounded evidence on this surface
  - `attentional_v2` produces none under the repaired strict source-span contract
- This should be read as a real formal evaluation result for the repaired package, not as an in-flight retry or a partially running job.

## What This Run Does And Does Not Mean

- It **does mean**:
  - the current formal judged evidence lane for `user-level selective v1` is no longer "still running"
  - the repaired sibling package is now backed by a completed formal run with aggregate and report outputs
- It **does not mean**:
  - the repaired sibling package has automatically replaced the active dataset pointer
  - the active `202`-case package has been retired

## Primary Evidence

- [aggregate.json](../../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_repaired_rejudge_20260416/summary/aggregate.json)
- [report.md](../../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_repaired_rejudge_20260416/summary/report.md)
- [active package manifest](../../../state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/manifest.json)
- [repaired sibling manifest](../../../state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1_repaired_20260416/manifest.json)
