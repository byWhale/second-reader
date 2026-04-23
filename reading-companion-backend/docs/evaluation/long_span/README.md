# Long-Span Evaluation Reports

This directory now has three layers:

- historical bounded long-span judged reports from `accumulation benchmark v1`
- discontinued `target-centered accumulation v2` design and diagnostic evidence
- the new active Long Span direction, whose phase-1 implementation is now landed but not yet promoted to formal benchmark authority

## Conventions

- One formal judged run should land one human interpretation report.
- Secondary follow-up reflection or redesign memos may sit beside the interpretation report when one judged run leads to later mechanism analysis or implementation-direction notes.
- Report filenames follow `<run_id>_interpretation.md`.
- Machine outputs remain under `reading-companion-backend/eval/runs/.../summary/`.
- Use [../README.md](../README.md) as the narrative cross-surface entry point.
- Use [../evidence_catalog.md](../evidence_catalog.md) as the durable evidence catalog across current, historical, superseded, audit, and diagnostic runs.
- After a full root-level long-span merge/report completes, update the catalog through `scripts/update_evaluation_catalog.py`; shard-filtered recovery outputs must not own catalog updates.

## Current Active Direction

The current active Long Span direction is no longer `target-centered accumulation v2`.

The active direction is now a design-frozen three-metric line:

- `Memory Quality`
  - sample probe points inside one continuous reading window
  - judge the current memory/state snapshot holistically
  - do not predeclare gold sentences or hard-bind human notes into the contract
- `Spontaneous Callback`
  - audit all visible reactions in a completed reading window
  - count and interpret reactions that naturally recall or connect prior material
- `False Visible Integration`
  - audit callback-like reactions for overclaim, hard-linking, vague theme-only similarity, or memory drift

Current implementation posture:

- active substrate:
  - the repaired `user-level selective v1` reading windows
- methodology status:
  - active design direction
  - design frozen
  - phase-1 implementation landed
    - runner:
      - [run_long_span_vnext.py](../../../eval/attentional_v2/run_long_span_vnext.py)
    - V2 probe export:
      - [benchmark_probes.py](../../../src/attentional_v2/benchmark_probes.py)
    - phase-1 scope:
      - `Memory Quality`: `attentional_v2` only
      - reaction audit: `attentional_v2` vs `iterator_v1`
    - output sourcing:
      - `attentional_v2` is freshly read or same-run resumed so `Memory Quality` probe snapshots exist
      - unchanged `iterator_v1` windows reuse April 19 completed normalized outputs for reaction audit
      - `iterator_v1` is re-read only when the active window fingerprint differs from the reuse source
      - fingerprint checks cover `segment_id / start_sentence_id / end_sentence_id / source_chapter_ids / source_text_sha256`
- formal evidence status:
  - there is no completed formal Long Span benchmark run yet under this new direction

## Historical Durable Evidence

The cleaned April 7 rerun remains the durable bounded long-span historical bundle:

- Run ID: `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407`
- Status: `historical durable evidence`
- Compared mechanisms: `attentional_v2` vs `iterator_v1`
- Current interpretation:
  - `iterator_v1` wins the overall bounded long-span surface on retrospective bridging and window-end closure.
  - `attentional_v2` still shows stronger main-thread fidelity on some single-chapter probes.

Do not use the older April 6 lane as current mechanism evidence; it remains historical machine output, but it was diagnosed as an invalid harness/materialization lane rather than a clean long-span comparison artifact.

## Discontinued Target-Centered V2

`target-centered accumulation v2` is no longer the active Long Span methodology.

It is preserved because it still matters as design history and diagnostic evidence:

- stable archived design document:
  - [target_centered_accumulation_v2_design.md](./target_centered_accumulation_v2_design.md)
- implementation artifacts kept readable:
  - [accumulation_benchmark_v2.py](../../../eval/attentional_v2/accumulation_benchmark_v2.py)
  - [run_accumulation_evaluation_v2.py](../../../eval/attentional_v2/run_accumulation_evaluation_v2.py)
  - [attentional_v2_accumulation_benchmark_v2_frozen.json](../../../eval/manifests/splits/attentional_v2_accumulation_benchmark_v2_frozen.json)
  - retained implementation mirror:
    - [attentional_v2_accumulation_benchmark_v2_draft.json](../../../eval/manifests/splits/attentional_v2_accumulation_benchmark_v2_draft.json)

Why it was discontinued:

- the April 22 rejudge repaired the old target-visible evidence contract, so the method became internally more correct
- but the project later concluded that the product question itself had shifted
- current priority is no longer “did the mechanism visibly reconstruct the prepared thread at one target point?”
- current priority is:
  - did the reader form high-quality memory under continuous reading?
  - did it naturally callback prior material?
  - were those callbacks grounded rather than forced?

That means the April 22 rejudge is preserved as the last corrected diagnostic for the discontinued target-centered route, not as the authority for the current Long Span direction.

Target-centered frozen-set context remains readable:

- frozen seed-set truth:
  - `12` frozen cases total
  - `悉达多`: `6`
  - `活出生命的意义`: `4`
  - `芒格之道`: `2`
  - `The Value of Others`: deferred to a later architecture-first pass
  - one additional `芒格之道` line remains held back as experimental only

Discontinued route evidence:

- contract-fix rejudge:
  - run id:
    - `attentional_v2_accumulation_benchmark_v2_frozen_rejudge_contract_fix_20260422`
  - status:
    - `invalidated diagnostic`
  - interpretation:
    - this run fixed the old target-visible evidence contract so only target-near mechanism evidence could score
    - it remains useful to understand why the old route changed, but it no longer represents the current active Long Span methodology
  - machine outputs:
    - [aggregate](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_rejudge_contract_fix_20260422/summary/aggregate.json)
    - [report](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_rejudge_contract_fix_20260422/summary/report.md)
  - case audit:
    - [longspan_rejudge_audit_20260422](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_rejudge_contract_fix_20260422/analysis/longspan_rejudge_audit_20260422/README.md)

- first formal rerun under the old contract:
  - run id:
    - `attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419`
  - status:
    - `invalidated diagnostic`
  - issue:
    - the first judge contract could give credit from the target passage itself or from pre-target callbacks, even when the mechanism produced no target-visible accumulation evidence
  - machine outputs:
    - [aggregate](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419/summary/aggregate.json)
    - [report](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419/summary/report.md)

## Reports

| Report title | Run ID | Surface | Compared mechanisms | Status | One-line conclusion | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Discontinued target-centered accumulation v2 contract-fix rejudge | `attentional_v2_accumulation_benchmark_v2_frozen_rejudge_contract_fix_20260422` | `target-centered accumulation v2` | `attentional_v2` vs `iterator_v1` | `invalidated diagnostic` | `This run repaired the old target-visible evidence contract, but the underlying product question was later retired in favor of Memory Quality / Spontaneous Callback / False Visible Integration.` | [aggregate](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_rejudge_contract_fix_20260422/summary/aggregate.json) · [report](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_rejudge_contract_fix_20260422/summary/report.md) · [audit](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_rejudge_contract_fix_20260422/analysis/longspan_rejudge_audit_20260422/README.md) |
| Discontinued target-centered accumulation v2 first formal rerun | `attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419` | `target-centered accumulation v2` | `attentional_v2` vs `iterator_v1` | `invalidated diagnostic` | `Preserved to diagnose the old judge-contract flaw; no longer used as current Long Span mechanism evidence.` | [aggregate](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419/summary/aggregate.json) · [report](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v2_frozen_active_rerun_20260419/summary/report.md) |
| Long-Span 正式 judged eval 详细解读 | `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407` | `bounded long-span accumulation comparison` | `attentional_v2` vs `iterator_v1` | `historical durable evidence` | `iterator_v1` wins the current durable bounded long-span surface overall; attentional_v2 is cleaner on some single-chapter main-thread probes but still trails on retrospective long-span closure.` | [aggregate](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/aggregate.json) · [report](../../../eval/runs/attentional_v2/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407/summary/report.md) · [interpretation](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_interpretation.md) |
| Long-Span 正式 judged eval 后续反思与机制重设计备忘 | `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407` | `post-eval mechanism reflection` | `attentional_v2` vs `iterator_v1` | `ongoing` | `The first completed probe-level reflection already suggests that attentional_v2 should replace heuristic semantic triggering with one Reading Agent organized around the two actions navigate and read, while realigning span visibility with span-closing authority.` | [interpretation](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_interpretation.md) · [reaction appendix](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_score_impact_reaction_appendix.md) · [follow-up memo](./attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_followup_reflection_and_decisions.md) |

## Working Memos

- [Target-centered candidate review](./target_centered_candidate_review.md): preserved review/freeze record for the discontinued target-centered v2 route. Keep it readable as design history, not as a current active benchmark authoring entry.
- [Target-centered 芒格 experimental review](./target_centered_mangge_experimental_review.md): source-specific companion for `芒格之道`. Keep it only as a per-book supplement for the discontinued route.
- [Historical pre-curation substrate memo](./archive/long_span_substrate_candidate_memo.md): archived mining memo from the earlier pre-freeze substrate pass. Keep it as historical curation context only.
