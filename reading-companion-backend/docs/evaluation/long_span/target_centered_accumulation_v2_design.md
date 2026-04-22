# Target-Centered Long-Span Accumulation V2

This document is the archived design record for the discontinued `target-centered accumulation v2` long-span method.

It no longer defines the active Long Span methodology. The active direction has moved to:

- `Memory Quality`
- `Spontaneous Callback`
- `False Visible Integration`

`accumulation benchmark v1` remains preserved as historical bounded evidence. `target-centered accumulation v2` remains preserved as design history and diagnostic evidence.

## Status

- Method status:
  - `archived / discontinued`
- Why it was retired:
  - not because the route was still internally buggy after the April 22 contract-fix rejudge
  - but because the product question changed
- What the project now prioritizes instead:
  - whether the Reader forms high-quality memory during continuous reading
  - whether it naturally callbacks earlier material
  - whether those callbacks are grounded rather than forced

Keep this document readable for:

- historical schema/context recovery
- old run interpretation
- preserved implementation ownership

Do not treat it as the current active Long Span authority.

## Historical Goal

At the time this route was active, the question was no longer:

- did the reader react at an early point?
- did it react again at a middle point?
- did it react again at a late point?

The route-specific question became:

- when the mechanism reaches the prepared target point, does it successfully build the earlier long-range thread there?

The thread may be:

- a story line
- an argumentative line
- a concept-building or distinction-building line

## Archived Case Schema

Each `TargetCase` contains:

- `case_id`
- `source_id`
- `book`
- `author`
- `output_language`
- `window_id`
- `thread_type`
  - `叙事型故事脉络`
  - `论证型论证线`
  - `概念/区分澄清线`
- `target_span`
  - one point or small target zone on the rendered window substrate
- `upstream_nodes[]`
  - `2+` prepared earlier nodes
- `expected_integration`
  - the compact plain-language statement of what the reader should build at the target point
- `callback_eligible_spans[]`
  - spans that count as relevant explicit callback evidence
- `non_goal_but_tempting_points[]`
  - nearby but wrong callback targets that judges should not reward
- `long_range_rationale`
  - why this case is genuinely long-range inside the source window
- `curation_status`
  - draft/review/freeze gate state

The route-specific coordinate system is `segment_source_v1`, because the mechanisms read the rendered window substrate rather than raw source-book chapter ids during this benchmark.

## Historical Window Substrate

When this route was active, `v2` reused the then-active `user-level selective v1` reading windows:

- window dataset at route retirement:
  - `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1_repaired_20260422`

- evidence boundary:
  - the completed April 19 formal long-span rerun still reused overlapping outputs from the then-active prior repaired window dataset `attentional_v2_user_level_selective_v1_repaired_20260416`
  - the April 22 Naval-only active-window repair does not change the frozen long-span case set because `《纳瓦尔宝典》` is not in that active v2 batch

This kept the reading setup aligned with the repaired body-start rule and avoided maintaining a second long-span-only window family.

## Archived Evidence Bundle

The judge consumes a mechanism-agnostic `TargetEvidenceBundle`.

It contains only externalized or normalized evidence:

- `target_local_reactions`
  - the target-zone reactions that overlap the prepared target span
- `explicit_callback_actions`
  - target-local or short-horizon post-target callback evidence that visibly returns to an upstream / callback-eligible span
- `short_horizon_followups`
  - the next short sequence of reactions after the target point
- `pre_target_observed_callbacks`
  - audit-only callback-like behavior seen before the target or outside the target-proximal evidence window
- `target_ref`
- `upstream_refs`
- `expected_integration`
- `non_goal_but_tempting_points`

It does **not** directly judge raw mechanism-specific memory/state structures.
It also does **not** treat the case-definition source text as mechanism output evidence:

- `target_ref`, `upstream_refs`, and `expected_integration` define what the case is asking.
- They may orient the judge, but they must not create score by themselves.
- If a mechanism has no target-local reaction, no target-proximal callback, and no short-horizon followup, the case must stay low-scored even when the target passage itself is strong.

Rationale:

- state only matters if it affects observable reading behavior
- raw internal structures are not comparable across mechanisms
- storing something internally without using it at the target point is not meaningful accumulation evidence
- a judge can always infer a beautiful connection from the source text after the fact, but the benchmark is about whether the reader agent made that connection visible near the target

## Archived Judge Contract

`v2` first release only scores:

- `reader_character.coherent_accumulation`

The judge returns an absolute per-mechanism result:

- `quality_score` (`1-5`)
  - primary score
- `callback_score` (`0-2`)
  - secondary bonus score
- `thread_built`
  - `built`
  - `partial`
  - `not_built`
- `reason`

Interpretation:

- `quality_score` measures whether target-local reactions and short-horizon followups semantically recall or use the upstream refs
- `expected_integration` is a high-score orientation, not a rigid checklist or required wording
- `callback_score` rewards relevant explicit callback evidence only when that callback is target-proximal
- `pre_target_observed_callbacks` may be shown in audit docs, but they are not scoring evidence unless later target-near evidence visibly uses the same thread
- `short_horizon_followups` support the `quality_score` judgment only when they continue the thread after target contact; being merely nearby in time is not enough

Contract repair note:

- the April 19 first formal rerun exposed a judge-contract flaw: some cases could be scored from the target passage itself or from callbacks that happened before the target
- the April 22 repaired contract is rejudge-only:
  - reuse completed normalized reading bundles
  - do not call `read_book`
  - rebuild only the evidence bundle and judgments
  - preserve the April 19 result as diagnostic evidence, not current Long Span mechanism evidence

## Scoring And Comparison

Primary output is **absolute per-mechanism scoring**.

Comparison is derived only at the report layer:

1. compare `quality_score`
2. if tied, compare `callback_score`
3. if still tied, record `tie`

There is no separate pairwise LLM judge prompt in `v2`.

## Candidate Review Workflow

`v2` does not freeze cases immediately.

Workflow:

1. mine candidate threads
2. author draft `TargetCase` rows
3. review candidate cases explicitly
4. freeze only approved rows

The first frozen reviewed seed set was approved on `2026-04-19`:

- `12` frozen cases total
- `悉达多`: `6`
- `活出生命的意义`: `4`
- `芒格之道`: `2`
- `The Value of Others`: still deferred to a separate theory-architecture pass

The first mining order that produced the frozen seed set was:

1. `悉达多`
2. `活出生命的意义`
3. `The Value of Others` only after a separate theory-architecture pass

`芒格之道` began as a lower-priority experimental surface, but its first two reviewed lines ended up inside the frozen seed set while one weaker line remained held back as experimental-only. `纳瓦尔宝典` stayed excluded from the main target dataset unless later review would have found clearly stronger target-centered cases.

## Files

Implementation:

- `reading-companion-backend/eval/attentional_v2/accumulation_benchmark_v2.py`
- `reading-companion-backend/eval/attentional_v2/run_accumulation_evaluation_v2.py`

Split manifests:

- `reading-companion-backend/eval/manifests/splits/attentional_v2_accumulation_benchmark_v2_draft.json`
- `reading-companion-backend/eval/manifests/splits/attentional_v2_accumulation_benchmark_v2_frozen.json`

Case datasets:

- `reading-companion-backend/state/eval_local_datasets/accumulation_target_cases/attentional_v2_accumulation_benchmark_v2_cases_draft`
- `reading-companion-backend/state/eval_local_datasets/accumulation_target_cases/attentional_v2_accumulation_benchmark_v2_cases_frozen`

Archived pre-curation memo:

- `reading-companion-backend/docs/evaluation/long_span/archive/long_span_substrate_candidate_memo.md`

## Historical Boundary

Keep these as historical evidence rather than active methodology authority:

- `reading-companion-backend/eval/attentional_v2/accumulation_benchmark_v1.py`
- `reading-companion-backend/eval/attentional_v2/run_accumulation_comparison.py`
- `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407`
