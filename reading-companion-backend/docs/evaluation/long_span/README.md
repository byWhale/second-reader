# Long-Span Evaluation Reports

This directory now has two layers:

- historical bounded long-span judged reports from `accumulation benchmark v1`
- active design and working materials for `target-centered long-span accumulation v2`

## Conventions

- One formal judged run should land one human interpretation report.
- Secondary follow-up reflection or redesign memos may sit beside the interpretation report when one judged run leads to later mechanism analysis or implementation-direction notes.
- Report filenames follow `<run_id>_interpretation.md`.
- Machine outputs remain under `reading-companion-backend/eval/runs/.../summary/`.
- Use [../README.md](../README.md) as the cross-surface entry point.

## Historical Durable Evidence

The current durable long-span evidence bundle is the cleaned April 7 rerun:

- Run ID: `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407`
- Status: `completed`
- Compared mechanisms: `attentional_v2` vs `iterator_v1`
- Current interpretation:
  - `iterator_v1` wins the overall bounded long-span surface on retrospective bridging and window-end closure.
  - `attentional_v2` still shows stronger main-thread fidelity on some single-chapter probes.

Do not use the older April 6 lane as current mechanism evidence; it remains historical machine output, but it was diagnosed as an invalid harness/materialization lane rather than a clean long-span comparison artifact.

## Active V2 Design

- Active methodology pointer:
  - `target-centered long-span accumulation v2`
- Stable design document:
  - [target_centered_accumulation_v2_design.md](./target_centered_accumulation_v2_design.md)
- Current implementation scaffolding:
  - [accumulation_benchmark_v2.py](../../../eval/attentional_v2/accumulation_benchmark_v2.py)
  - [run_accumulation_evaluation_v2.py](../../../eval/attentional_v2/run_accumulation_evaluation_v2.py)
- Split manifests:
  - [attentional_v2_accumulation_benchmark_v2_frozen.json](../../../eval/manifests/splits/attentional_v2_accumulation_benchmark_v2_frozen.json)
  - retained implementation mirror:
    - [attentional_v2_accumulation_benchmark_v2_draft.json](../../../eval/manifests/splits/attentional_v2_accumulation_benchmark_v2_draft.json)

`v2` is now the active long-span method definition. It reuses the repaired active user-level window substrate at:

- [attentional_v2_user_level_selective_v1_repaired_20260416](../../../state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1_repaired_20260416/manifest.json)

It has a first frozen reviewed seed set, but it still does not have a completed formal judged run.

Current frozen seed-set truth:
- `12` frozen cases total
- `悉达多`: `6`
- `活出生命的意义`: `4`
- `芒格之道`: `2`
- `The Value of Others`: deferred to a later architecture-first pass
- one additional `芒格之道` line remains held back as experimental only

## Reports

| Report title | Run ID | Surface | Compared mechanisms | Status | One-line conclusion | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Long-Span 正式 judged eval 详细解读 | `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407` | `bounded long-span accumulation comparison` | `attentional_v2` vs `iterator_v1` | `completed` | `iterator_v1` wins the current durable long-span surface overall; attentional_v2 is cleaner on some single-chapter main-thread probes but still trails on retrospective long-span closure.` | [aggregate](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/aggregate.json) · [report](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/report.md) · [interpretation](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_interpretation.md) |
| Long-Span 正式 judged eval 后续反思与机制重设计备忘 | `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407` | `post-eval mechanism reflection` | `attentional_v2` vs `iterator_v1` | `ongoing` | `The first completed probe-level reflection already suggests that attentional_v2 should replace heuristic semantic triggering with one Reading Agent organized around the two actions navigate and read, while realigning span visibility with span-closing authority.` | [interpretation](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_interpretation.md) · [reaction appendix](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_score_impact_reaction_appendix.md) · [follow-up memo](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_followup_reflection_and_decisions.md) |

## Working Memos

- [Target-centered candidate review](./target_centered_candidate_review.md): current unified v2 review and freeze record. It captures the `12`-case frozen seed set across `悉达多`, `活出生命的意义`, and the first two `芒格之道` lines, while keeping `The Value of Others` deferred and one weaker `芒格` line held back.
- [Target-centered 芒格 experimental review](./target_centered_mangge_experimental_review.md): source-specific companion for `芒格之道`. Keep it only as a per-book supplement; use the unified candidate review above as the main review entry.
- [Historical pre-curation substrate memo](./archive/long_span_substrate_candidate_memo.md): archived mining memo from the earlier pre-freeze substrate pass. Keep it as historical curation context only, not as a current working entry.
