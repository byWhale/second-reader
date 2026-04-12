# Long-Span Evaluation Reports

This directory archives human interpretation reports for formal bounded long-span evaluations.

## Conventions

- One formal judged run should land one human interpretation report.
- Secondary follow-up reflection or redesign memos may sit beside the interpretation report when one judged run leads to later mechanism analysis or implementation-direction notes.
- Report filenames follow `<run_id>_interpretation.md`.
- Machine outputs remain under `reading-companion-backend/eval/runs/.../summary/`.
- Use [../README.md](../README.md) as the cross-surface entry point.

## Current Durable Evidence

The current durable long-span evidence bundle is the cleaned April 7 rerun:

- Run ID: `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407`
- Status: `completed`
- Compared mechanisms: `attentional_v2` vs `iterator_v1`
- Current interpretation:
  - `iterator_v1` wins the overall bounded long-span surface on retrospective bridging and window-end closure.
  - `attentional_v2` still shows stronger main-thread fidelity on some single-chapter probes.

Do not use the older April 6 lane as current mechanism evidence; it remains historical machine output, but it was diagnosed as an invalid harness/materialization lane rather than a clean long-span comparison artifact.

## Reports

| Report title | Run ID | Surface | Compared mechanisms | Status | One-line conclusion | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Long-Span 正式 judged eval 详细解读 | `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407` | `bounded long-span accumulation comparison` | `attentional_v2` vs `iterator_v1` | `completed` | `iterator_v1` wins the current durable long-span surface overall; attentional_v2 is cleaner on some single-chapter main-thread probes but still trails on retrospective long-span closure.` | [aggregate](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/aggregate.json) · [report](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/report.md) · [interpretation](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_interpretation.md) |
| Long-Span 正式 judged eval 后续反思与机制重设计备忘 | `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407` | `post-eval mechanism reflection` | `attentional_v2` vs `iterator_v1` | `ongoing` | `The first completed probe-level reflection already suggests that attentional_v2 should replace heuristic semantic triggering with one Reading Agent organized around the two actions navigate and read, while realigning span visibility with span-closing authority.` | [interpretation](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_interpretation.md) · [reaction appendix](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_score_impact_reaction_appendix.md) · [follow-up memo](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_followup_reflection_and_decisions.md) |
