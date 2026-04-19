# Target-Centered Long-Span Accumulation V2

This document defines the active design for long-span accumulation evaluation after retiring the old bounded `EARLY / MID / LATE` probe method as the active methodology.

`accumulation benchmark v1` remains preserved as historical evidence. `v2` is the active design and implementation direction.

## Goal

The question is no longer:

- did the reader react at an early point?
- did it react again at a middle point?
- did it react again at a late point?

The question is now:

- when the mechanism reaches the prepared target point, does it successfully build the earlier long-range thread there?

The thread may be:

- a story line
- an argumentative line
- a concept-building or distinction-building line

## Case Schema

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

The active coordinate system is `segment_source_v1`, because the mechanisms read the rendered window substrate rather than raw source-book chapter ids during this benchmark.

## Window Substrate

`v2` reuses the active `user-level selective v1` reading windows:

- current window dataset:
  - `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1`

This keeps the reading setup aligned with the repaired body-start rule and avoids maintaining a second long-span-only window family unless later evidence shows that these windows are insufficient.

## Evidence Bundle

The judge consumes a mechanism-agnostic `TargetEvidenceBundle`.

It contains only externalized or normalized evidence:

- `target_local_reactions`
  - the target-zone reactions that overlap the prepared target span
- `explicit_callback_actions`
  - relevant callback / revisit / bridge behavior near the target point
- `short_horizon_followups`
  - the next short sequence of reactions after the target point
- `target_ref`
- `upstream_refs`
- `expected_integration`
- `non_goal_but_tempting_points`

It does **not** directly judge raw mechanism-specific memory/state structures.

Rationale:

- state only matters if it affects observable reading behavior
- raw internal structures are not comparable across mechanisms
- storing something internally without using it at the target point is not meaningful accumulation evidence

## Judge Contract

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

- `quality_score` measures whether the target-point reaction actually reconstructs the prepared thread
- `callback_score` rewards relevant explicit callback evidence
- `short_horizon_followups` support the `quality_score` judgment by showing whether the mechanism keeps using the thread after the target point rather than only saying one lucky sentence

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

`芒格之道` began as a lower-priority experimental surface, but its first two reviewed lines are now inside the frozen seed set while one weaker line remains held back as experimental-only. `纳瓦尔宝典` is currently excluded from the main target dataset unless later review finds clearly stronger target-centered cases.

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
