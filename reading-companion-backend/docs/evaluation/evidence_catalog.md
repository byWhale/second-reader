# Evaluation Evidence Catalog

This checked-in catalog indexes meaningful evaluation evidence. Raw machine outputs remain under `eval/runs/`; local/private text-bearing datasets remain under `state/eval_local_datasets/`; human interpretation reports remain under `docs/evaluation/`.

- Schema version: `1`
- Last updated: `2026-04-21T12:17:06.278637Z`

## Status Meanings

- `current_formal_evidence`: current evidence for an active benchmark surface.
- `quality_audit`: focused quality audit that informs mechanism work but is not a formal benchmark score.
- `historical_evidence`: preserved evidence from an older but still valid methodology.
- `superseded`: preserved evidence replaced by a newer active run or benchmark contract.
- `failed_diagnostic` / `invalidated_diagnostic`: failure evidence useful for debugging, not mechanism-quality evidence.

## Current Formal Evidence

| run id | surface | goal | mechanisms | metrics | conclusion | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `attentional_v2_active_benchmark_rerun_20260419` | active_benchmark_bundle | Active benchmark bundle | `attentional_v2`, `iterator_v1` | excerpt=attentional_v2_user_level_selective_v1_active_rerun_20260419; accumulation=attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419 | Active benchmark bundle completed: V2 leads excerpt Selective Legibility; iterator_v1 leads target-centered long-span accumulation. | [run dir](../../eval/runs/attentional_v2/attentional_v2_active_benchmark_rerun_20260419) · [aggregate](../../eval/runs/attentional_v2/attentional_v2_active_benchmark_rerun_20260419/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_active_benchmark_rerun_20260419/summary/report.md) · [analysis 1](../../eval/runs/attentional_v2/attentional_v2_active_benchmark_rerun_20260419/analysis/full_case_audit_20260421/README.md) |
| `attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419` | target_centered_accumulation_v2 | Coherent Accumulation | `attentional_v2`, `iterator_v1` | `attentional_v2` average_quality_score=2.583, average_callback_score=0.25; `iterator_v1` average_quality_score=3.083, average_callback_score=0.333; case_count=12 | Current target-centered long-span v2 rerun: iterator_v1 leads average quality score 3.083 vs attentional_v2 2.583. | [run dir](../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419) · [aggregate](../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419/summary/report.md) |
| `attentional_v2_user_level_selective_v1_active_rerun_20260419` | user_level_selective_v1 | Selective Legibility | `attentional_v2`, `iterator_v1` | `attentional_v2` note_recall=0.3498; `iterator_v1` note_recall=0.1232; note_case_count=203 | Current active user-level selective rerun: attentional_v2 leads note recall 0.3498 vs iterator_v1 0.1232. | [run dir](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_active_rerun_20260419) · [aggregate](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_active_rerun_20260419/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_active_rerun_20260419/summary/report.md) |

## Quality Audits

| run id | surface | goal | mechanisms | metrics | conclusion | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `attentional_v2_f4a_quality_audit_20260419` | attentional_v2_quality_audit | Focused mechanism quality audit | `attentional_v2` | case_count=6; completed_case_count=6; failed_case_count=0 | Focused quality audit found V2 reaction density and reading-time wording recovered, while detour behavior was not exercised. | [run dir](../../eval/runs/attentional_v2/attentional_v2_f4a_quality_audit_20260419) · [aggregate](../../eval/runs/attentional_v2/attentional_v2_f4a_quality_audit_20260419/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_f4a_quality_audit_20260419/summary/report.md) |

## Historical Evidence

| run id | surface | goal | mechanisms | metrics | conclusion | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407` | bounded_longspan_accumulation_v1 | Coherent Accumulation | `attentional_v2`, `iterator_v1` | coherent_accumulation: avg=attentional_v2 2.457, iterator_v1 3.486; wins=attentional_v2 2, iterator_v1 5; insight_and_clarification: avg=attentional_v2 2.457, iterator_v1 3.086; wins=attentional_v2 2, iterator_v1 4, tie 1; case_count=7 | Historical bounded long-span v1 evidence: iterator_v1 won overall on retrospective bridging and window-end closure. | [run dir](../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407) · [aggregate](../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/report.md) |

## Superseded Evidence

| run id | surface | goal | mechanisms | metrics | conclusion | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `attentional_v2_excerpt_surface_v1_1_judged_20260406` | excerpt_surface_v1_1 | Selective Legibility / Insight and Clarification | `attentional_v2`, `iterator_v1` | selective_legibility: avg=attentional_v2 1.98, iterator_v1 1.427; wins=attentional_v2 27, iterator_v1 21, tie 11; insight_and_clarification: avg=attentional_v2 2.2, iterator_v1 1.688; wins=attentional_v2 19, iterator_v1 16, tie 8; case_count=59 | Superseded excerpt surface v1.1 formal evidence retained for historical comparison, no longer active benchmark authority. | [run dir](../../eval/runs/attentional_v2/attentional_v2_excerpt_surface_v1_1_judged_20260406) · [aggregate](../../eval/runs/attentional_v2/attentional_v2_excerpt_surface_v1_1_judged_20260406/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_excerpt_surface_v1_1_judged_20260406/summary/report.md) |
| `attentional_v2_user_level_selective_v1_repaired_rejudge_20260416` | user_level_selective_v1 | Selective Legibility | `attentional_v2`, `iterator_v1` | `attentional_v2` note_recall=0.0; `iterator_v1` note_recall=0.2118; note_case_count=203 | Superseded repaired strict source-span rejudge; replaced by the April 19 active rerun on the repaired 203-case package. | [run dir](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_repaired_rejudge_20260416) · [aggregate](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_repaired_rejudge_20260416/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_repaired_rejudge_20260416/summary/report.md) |

## Failed Diagnostics

| run id | surface | goal | mechanisms | metrics | conclusion | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `attentional_v2_user_level_selective_v1_rejudge_reuse_20260416` | user_level_selective_v1 | Selective Legibility |  |  | Failed diagnostic run retained for the split-manifest contamination and watchdog relaunch failure chain. | [run dir](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_rejudge_reuse_20260416) |

## Invalidated Diagnostics

| run id | surface | goal | mechanisms | metrics | conclusion | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| `attentional_v2_user_level_selective_v1_failed_shards_retry2_20260415` | user_level_selective_v1 | Selective Legibility |  |  | Invalidated diagnostic run stopped after discovering string-similarity candidate retrieval instead of strict source-span overlap. | [run dir](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_failed_shards_retry2_20260415) |
