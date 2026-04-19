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
| `user-level selective v1` | `attentional_v2_user_level_selective_v1_repaired_rejudge_20260416` | `attentional_v2` vs `iterator_v1` | `current formal evidence on repaired sibling package` | The active local/user-level benchmark definition still points at the `202`-case `attentional_v2_user_level_selective_v1` package, but the current formal evidence bundle is the completed repaired rejudge on the `203`-case repaired sibling package. | [active manifest](../../eval/manifests/splits/attentional_v2_user_level_selective_v1_draft.json) · [active dataset](../../state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/manifest.json) · [aggregate](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_repaired_rejudge_20260416/summary/aggregate.json) · [report](../../eval/runs/attentional_v2/attentional_v2_user_level_selective_v1_repaired_rejudge_20260416/summary/report.md) · [interpretation](./user_level/attentional_v2_user_level_selective_v1_repaired_rejudge_20260416_interpretation.md) · [surface index](./user_level/README.md) |
| `target-centered long-span accumulation v2` | `attentional_v2_accumulation_benchmark_v2_frozen` | no formal judged run yet | `active methodology + frozen seed set` | The active long-span methodology now centers each case on one target point plus a prepared long-range thread. It has a `12`-case frozen seed set, while judged comparison remains a future explicit step. | [design](./long_span/target_centered_accumulation_v2_design.md) · [surface index](./long_span/README.md) · [frozen manifest](../../eval/manifests/splits/attentional_v2_accumulation_benchmark_v2_frozen.json) |
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
