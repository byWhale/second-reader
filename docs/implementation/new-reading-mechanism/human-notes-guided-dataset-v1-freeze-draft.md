# Human-Notes-Guided Dataset V1 Freeze Draft

Purpose: record the first explicit reviewed freeze decision for the isolated human-notes-guided dataset line.
Use when: checking which notes-guided clusters are already stable enough to freeze, which cluster is still held for repair, or locating the frozen local reviewed slices.
Not for: active benchmark-pointer decisions, public evaluation constitution, or final merge / replace decisions.
Update when: the held cluster is repaired, the frozen slice membership changes, or this isolated line is promoted beyond support-lane status.

## Status
- Dataset posture:
  - this line remains isolated from the active clustered benchmark v1
  - do not repoint the active benchmark based on this line alone
- Scratch construction source of truth:
  - run id:
    - `human_notes_guided_dataset_v1_20260404`
  - build summary:
    - `reading-companion-backend/state/dataset_build/build_runs/human_notes_guided_dataset_v1_20260404/build_summary.json`
  - cluster resolution:
    - `reading-companion-backend/state/dataset_build/build_runs/human_notes_guided_dataset_v1_20260404/cluster_resolutions/attentional_v2_human_notes_guided_dataset_v1_excerpt_scope__scratch__human_notes_guided_dataset_v1_20260404.json`
- First-review closeout:
  - EN packet:
    - `human_notes_guided_dataset_v1_excerpt_en_first_review_20260404`
    - result: `14 keep`, `2 revise`, `0 drop`
  - ZH packet:
    - `human_notes_guided_dataset_v1_excerpt_zh_first_review_20260404`
    - result: `39 keep`, `7 revise`, `1 drop`
- Current reviewed freeze state:
  - eligible frozen clusters: `8 / 8`
  - held clusters: `0 / 8`
  - frozen reviewed excerpt rows: `55`
    - EN: `14`
    - ZH: `41`
- Frozen local reviewed-slice packages:
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_complete_20260404`
- Narrow repair closeout:
  - `human_notes_guided_dataset_v1_excerpt_zh_wealth_repair_review_20260404`
    - result: `1 keep`, `1 revise`
  - `human_notes_guided_dataset_v1_excerpt_zh_wealth_repair_review_retry1_20260404`
    - result: `1 keep`, `0 revise`
  - post-repair ZH scratch counts:
    - `reviewed_active = 41`
    - `needs_revision = 5`
    - `needs_replacement = 1`

## Freeze Rule
- Freeze only rows whose `benchmark_status = reviewed_active`.
- Do not freeze `needs_revision` or `needs_replacement`.
- Default per-cluster primary target is `8`.
- Honest short freeze is allowed at `6+` reviewed-active rows when the cluster is otherwise structurally valid.
- Reserve rows are not part of this freeze yet.
  - current reserve rows are still scratch outputs, not reviewed benchmark truth

## Cluster Decisions
| Selection Group | Book | Reviewed Active | Needs Revision | Needs Replacement | Scratch Reserves | Decision | Note |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `value_of_others_private_en__dense_band_41_100` | `The Value of Others` | 7 | 1 | 0 | 2 | `freeze_short` | strong cluster; one remaining revise is `ambiguous_focus`, not a freeze blocker |
| `value_of_others_private_en__dense_band_161_200` | `The Value of Others` | 7 | 1 | 0 | 2 | `freeze_short` | same chapter, different notes-guided band; stable enough as a separate surface |
| `huochu_shengming_de_yiyi_private_zh__camp_experience` | `活出生命的意义` | 8 | 0 | 0 | 2 | `freeze_full` | clean full cluster |
| `mangge_zhi_dao_private_zh__speeches_2007_2010` | `芒格之道` | 6 | 2 | 0 | 2 | `freeze_short` | reached the honest-short floor; revised tail is weak/ambiguous rather than core-cluster collapse |
| `mangge_zhi_dao_private_zh__speeches_2019_2020` | `芒格之道` | 6 | 2 | 0 | 2 | `freeze_short` | same reasoning as the earlier speeches cluster |
| `nawaer_baodian_private_zh__judgment` | `纳瓦尔宝典` | 7 | 1 | 0 | 2 | `freeze_short` | cluster is viable; one anchored-reaction row remains focus-ambiguous |
| `xidaduo_private_zh__late_book` | `悉达多` | 8 | 0 | 0 | 2 | `freeze_full` | clean full cluster |
| `nawaer_baodian_private_zh__wealth` | `纳瓦尔宝典` | 6 | 0 | 1 | 0 | `freeze_short` | narrow anchored-reaction repair yielded two keeps; one tension row remains replacement-only but no longer blocks the cluster |

## Resolved Repair Closeout
- Former held selection group:
  - `nawaer_baodian_private_zh__wealth`
- Final status:
  - `reviewed_active = 6`
  - `needs_revision = 0`
  - `needs_replacement = 1`
  - scratch reserve rows = `0`
- Repair packets:
  - `human_notes_guided_dataset_v1_excerpt_zh_wealth_repair_review_20260404`
    - `nawaer_baodian_private_zh__13__anchored_reaction_selectivity__seed_2` moved to `keep`
    - `nawaer_baodian_private_zh__13__anchored_reaction_selectivity__seed_3` remained `revise`
  - `human_notes_guided_dataset_v1_excerpt_zh_wealth_repair_review_retry1_20260404`
    - `nawaer_baodian_private_zh__13__anchored_reaction_selectivity__seed_3` moved to `keep`
- Practical interpretation:
  - the cluster now reaches the honest-short freeze floor without reopening a broad builder wave
  - the remaining `tension_reversal` replacement row does not block cluster freeze because it is outside the frozen reviewed-active slice
  - this closes the only held-cluster repair question for the isolated notes-guided line

## Membership Source Of Truth
- Frozen EN reviewed slice:
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404/manifest.json`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404/cases.jsonl`
- Frozen ZH reviewed slice:
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_complete_20260404/manifest.json`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_complete_20260404/cases.jsonl`
- Historical intermediate ZH freeze:
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_20260404/manifest.json`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_20260404/cases.jsonl`

## Working Rule
- Keep the completed `55`-row reviewed freeze stable.
- Do not reopen a general bilingual builder wave for this line.
- Do not merge this line into the active benchmark until an explicit later merge / replace decision is made.
