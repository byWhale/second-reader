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
  - eligible frozen clusters: `7 / 8`
  - held clusters: `1 / 8`
  - frozen reviewed excerpt rows: `49`
    - EN: `14`
    - ZH: `35`
- Frozen local reviewed-slice packages:
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_20260404`

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
| `nawaer_baodian_private_zh__wealth` | `纳瓦尔宝典` | 4 | 2 | 1 | 0 | `hold_repair` | only cluster below the honest-short floor; no reserve safety net |

## Held Cluster
- Held selection group:
  - `nawaer_baodian_private_zh__wealth`
- Current status:
  - `reviewed_active = 4`
  - `needs_revision = 2`
  - `needs_replacement = 1`
  - scratch reserve rows = `0`
- Current failure shape:
  - two anchored-reaction rows remain usable in principle but need tighter focus framing:
    - `nawaer_baodian_private_zh__13__anchored_reaction_selectivity__seed_2`
    - `nawaer_baodian_private_zh__13__anchored_reaction_selectivity__seed_3`
  - one tension row is not a real reversal and should be replaced rather than patched:
    - `nawaer_baodian_private_zh__13__tension_reversal__seed_1`
- Practical interpretation:
  - this is no longer a whole-dataset problem
  - it is one local cluster-repair problem
  - the next move should be a narrow builder / curation repair targeted at `nawaer_baodian_private_zh__wealth`, not a new broad review wave

## Membership Source Of Truth
- Frozen EN reviewed slice:
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404/manifest.json`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404/cases.jsonl`
- Frozen ZH reviewed slice:
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_20260404/manifest.json`
  - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_20260404/cases.jsonl`

## Working Rule
- Keep the frozen `49`-row reviewed slice stable while repairing the held cluster.
- Do not reopen a general bilingual builder wave for this line.
- Do not merge this line into the active benchmark until the held cluster question is resolved intentionally.
