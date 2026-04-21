# Evaluation Report Index

This directory is the checked-in home for reviewed, human-readable evaluation reports.

## Layers

- Stable evaluation methodology lives in [docs/backend-reader-evaluation.md](../../../docs/backend-reader-evaluation.md).
- Machine-generated run artifacts live in `reading-companion-backend/eval/runs/`.
- Reviewed human interpretation reports live here under surface-specific subdirectories.

This split is intentional:

- `eval/runs/...` is the canonical raw run output.
- `docs/evaluation/...` is the human-facing interpretation/archive layer.

## Active Benchmark Pointers And Formal Evidence

| Surface | Run ID | Compared mechanisms | Status | One-line conclusion | Evidence |
| --- | --- | --- | --- | --- | --- |
| `user-level selective v1` | `attentional_v2_user_level_selective_v1_active_rerun_20260419` | `attentional_v2` vs `iterator_v1` | `current formal evidence on active repaired package` | The active local/user-level benchmark pointer uses the repaired `203`-case package. In the April 19 formal rerun, `attentional_v2` led on note recall (`0.3498` vs `0.1232`). | [active manifest](../../eval/manifests/splits/attentional_v2_user_level_selective_v1_draft.json) · [active dataset](../../state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1_repaired_20260416/manifest.json) · [aggregate](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_active_rerun_20260419/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_active_rerun_20260419/summary/report.md) · [surface index](./user_level/README.md) |
| `target-centered long-span accumulation v2` | `attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419` | `attentional_v2` vs `iterator_v1` | `current formal evidence on frozen seed set` | The active long-span methodology completed its first formal rerun over `12` frozen target cases; `iterator_v1` led on average quality score (`3.083` vs `2.583`). | [design](./long_span/target_centered_accumulation_v2_design.md) · [surface index](./long_span/README.md) · [frozen manifest](../../eval/manifests/splits/attentional_v2_accumulation_benchmark_v2_frozen.json) · [aggregate](../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419/summary/report.md) |
| `bounded long-span accumulation comparison` | `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407` | `attentional_v2` vs `iterator_v1` | `historical durable evidence` | `iterator_v1` won the current durable bounded long-span evidence lane on retrospective bridging and window-end closure; attentional_v2 still showed stronger main-thread fidelity on some single-chapter probes.` | [aggregate](../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/report.md) · [surface index](./long_span/README.md) · [interpretation](./long_span/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_interpretation.md) |

## Surface Directories

- [user_level/](./user_level/README.md)
  - active note-aligned benchmark definition, current formal evidence, and preserved failed attempts
- [excerpt/](./excerpt/README.md)
  - superseded excerpt-surface reports kept as historical evidence
- [long_span/](./long_span/README.md)
  - active target-centered long-span review/freeze materials plus historical bounded reports

## Historical / Legacy Checked-In Reports

These files remain useful historical reference, but they predate the current surface-index pattern and should not be mistaken for the current formal evidence entry points.

- `subsegment/`
  - older subsegment-era comparison reports
- `highlight_comparison_ch1.md`
- `highlight_comparison_ch2.md`
- `highlight_comparison_ch3.md`
- `highlight_comparison_ch3_before_prompt_tuning.md`

## Conventions

- One formal judged run should land one human interpretation report.
- Formal interpretation files follow `<run_id>_interpretation.md`.
- Each recurring formal surface should keep its own `README.md` index.
- This root `README.md` is the cross-surface discovery index, not the canonical machine output.
