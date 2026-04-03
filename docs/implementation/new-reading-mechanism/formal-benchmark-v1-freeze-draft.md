# Formal Benchmark V1 Freeze Draft

Historical status: archived benchmark evidence. The active benchmark pointer now lives in `docs/implementation/new-reading-mechanism/clustered-benchmark-v1-draft.md`.

Purpose: preserve the explicit `40`-case freeze draft for the earlier broad formal benchmark and the evidence that closed its last excerpt gaps.
Use when: checking the archived `40 / 40` composition, recovering why those earlier formal gaps were closed, or comparing the older broad freeze against the newer clustered benchmark direction.
Not for: the active benchmark pointer, stable evaluation methodology, default-cutover claims, or one-off packet implementation details.
Update when: the archived record needs clarification or new historical cross-links are added.

## Scope
- Historical formal benchmark targets:
  - `reader_character.selective_legibility`
  - `reader_character.coherent_accumulation`
  - `reader_value.insight_and_clarification`
- Canonical machine-readable companion:
  - `reading-companion-backend/eval/manifests/splits/attentional_v2_formal_benchmark_v1_draft.json`
- Active benchmark successor:
  - `reading-companion-backend/eval/manifests/splits/attentional_v2_clustered_benchmark_v1_draft.json`
- Working rule:
  - this draft freezes explicit case ids instead of relying on auto-core selection
  - source origin remains provenance only and must not define the benchmark shape

## Chapter Core Draft
The chapter lane is frozen in draft form at `16 / 16`.

### `expository`
- EN:
  - `women_and_economics_public_en__6`
  - `varieties_of_religious_experience_public_en__14`
- ZH:
  - `ouyou_zaji_public_zh__4`
  - `gushi_xinbian_public_zh__5`

### `argumentative`
- EN:
  - `on_liberty_public_en__4`
  - `darkwater_public_en__12`
- ZH:
  - `zhaohua_xishi_25271_zh__5`
  - `rulin_waishi_24032_zh__14`

### `narrative_reflective`
- EN:
  - `portrait_of_a_lady_public_en__10`
  - `up_from_slavery_public_en__10`
- ZH:
  - `chenlun_public_zh__4`
  - `ershinian_mudu_public_zh__37`

### `reference_heavy`
- EN:
  - `moby_dick_2701_en__22`
  - `walden_205_en__10`
- ZH:
  - `jinghua_yuan_25377_zh__15`
  - `nahan_27166_zh__5`

Practical interpretation:
- this preserves the required `2 EN + 2 ZH` per role
- it favors one case per source book within each language-role lane where possible
- it avoids treating the current smallest-chapter auto-core as the final formal freeze rule

## Excerpt Core Frozen Draft
The excerpt lane is now frozen in draft form at `24 / 24`.

### `distinction_definition` (`6`)
- `women_and_economics_public_en__6__distinction_definition__v2`
- `women_and_economics_public_en__9__distinction_definition__v2`
- `varieties_of_religious_experience_public_en__6__distinction_definition__v2`
- `gushi_xinbian_public_zh__4__distinction_definition__v2`
- `ouyou_zaji_public_zh__4__distinction_definition__v2`
- `zouchu_weiyi_zhenliguan_private_zh__14__seed_1`

### `tension_reversal` (`6`)
- `darkwater_public_en__9__tension_reversal__v2`
- `darkwater_public_en__12__tension_reversal__v2`
- `rulin_waishi_24032_zh__6__tension_reversal__v2`
- `rulin_waishi_24032_zh__14__tension_reversal__v2`
- `ershinian_mudu_public_zh__17__tension_reversal__v2`
- `education_of_henry_adams_public_en__8__tension_reversal__seed_v1`

### `anchored_reaction_selectivity` (`6`)
- `up_from_slavery_public_en__5__anchored_reaction_selectivity__v2`
- `nahan_27166_zh__5__anchored_reaction_selectivity__v2`
- `zhaohua_xishi_25271_zh__5__anchored_reaction_selectivity__v2`
- `ershinian_mudu_public_zh__37__anchored_reaction_selectivity__v2`
- `steve_jobs_private_en__43__seed_1`
- `education_of_henry_adams_public_en__16__anchored_reaction_selectivity__seed_v1`

### `callback_bridge_or_modest_cross_span_link` (`4`)
- `walden_205_en__6__callback_bridge__v2`
- `on_liberty_public_en__10__callback_bridge__v2`
- `jinghua_yuan_25377_zh__34__callback_bridge__v2`
- `nahan_27166_zh__2__callback_bridge__v2`

### `clarification_wildcard_or_undercovered_pressure` (`2`)
- `evicted_private_en__29__seed_1`
- `meiguoren_de_xingge_private_zh__19__seed_2`

## Clarification Subset Frozen Draft
The `reader_value.insight_and_clarification` lane uses an explicit `16`-case subset of `excerpt_core`.

### Composition
- `distinction_definition = 6`
- `tension_reversal = 6`
- `callback_bridge_or_modest_cross_span_link = 2`
- `clarification_wildcard_or_undercovered_pressure = 2`
- language balance stays `8 EN + 8 ZH`

### Clarification callback choices
- `on_liberty_public_en__10__callback_bridge__v2`
- `jinghua_yuan_25377_zh__34__callback_bridge__v2`

Interpretation:
- the full `excerpt_core` still serves `reader_character.selective_legibility`
- the clarification subset narrows to cases where we expect stronger evidence about definitions, distinctions, tensions, or clarifying bridge work
- `walden_205_en__6__callback_bridge__v2` and `nahan_27166_zh__2__callback_bridge__v2` remain in `excerpt_core` as general bridge/selectivity pressures, but they are not part of the formal clarification subset

## Overflow, Holdouts, And Explicit Non-Selections
### Callback overflow reserve
- `jinghua_yuan_25377_zh__15__callback_bridge__v2`

### Paused durable-trace-adjacent reviewed cases
- `souls_of_black_folk_408_en__4__reconsolidation_later_reinterpretation__v2`
- `souls_of_black_folk_408_en__8__reconsolidation_later_reinterpretation__v2`
- `chenlun_public_zh__4__reconsolidation_later_reinterpretation__v2`

### Explicit non-selections for the current freeze
- `portrait_of_a_lady_public_en__10__anchored_reaction_selectivity__v2`
  - kept as the tracked anchored fallback, but not needed after the cheaper accepted gap-fill wave
- `education_of_henry_adams_public_en__16__callback_bridge__seed_v1`
  - fresh review result was `revise` with `ambiguous_focus`, so it is not eligible for this freeze
- `chenlun_public_zh__4__callback_bridge__seed_v1`
  - still not recommended for the current frozen benchmark

## Freeze Status
Formal benchmark-v1 status is now:
- `chapter_core`: `16 / 16`
- `excerpt_core`: `24 / 24`
- total: `40 / 40`

Excerpt composition after closeout:
- `distinction_definition = 6`
- `tension_reversal = 6`
- `anchored_reaction_selectivity = 6`
- `callback_bridge_or_modest_cross_span_link = 4`
- `clarification_wildcard_or_undercovered_pressure = 2`

## 2026-04-03 Gap-Fill Closeout
The last `6` excerpt slots were filled with fresh formal review evidence, and no fallback reruns were needed.

### EN local reviewed rerun
- job:
  - `bgjob_formal_benchmark_v1_gapfill_en_local_20260403`
- packet:
  - `attentional_v2_formal_benchmark_v1_gapfill_en_local_20260403`
- accepted keeps:
  - `steve_jobs_private_en__43__seed_1`
  - `evicted_private_en__29__seed_1`

### ZH local reviewed rerun
- job:
  - `bgjob_formal_benchmark_v1_gapfill_zh_local_20260403`
- packet:
  - `attentional_v2_formal_benchmark_v1_gapfill_zh_local_20260403`
- accepted keeps:
  - `zouchu_weiyi_zhenliguan_private_zh__14__seed_1`
  - `meiguoren_de_xingge_private_zh__19__seed_2`

### Henry source-scoped scratch rerun
- job:
  - `bgjob_formal_benchmark_v1_gapfill_henry_20260403`
- run:
  - `formal_benchmark_v1_gapfill_henry_20260403`
- relevant accepted keep:
  - `education_of_henry_adams_public_en__8__tension_reversal__seed_v1`
- additional observed outcomes:
  - `education_of_henry_adams_public_en__29__anchored_reaction_selectivity__seed_v1` also reviewed as `keep`, but was surplus to the planned quota fill
  - `education_of_henry_adams_public_en__16__callback_bridge__seed_v1` reviewed as `revise` with `ambiguous_focus`

### Henry explicit single-case anchored rerun
- job:
  - `bgjob_formal_benchmark_v1_gapfill_henry16_anchor_20260403`
- packet:
  - `attentional_v2_formal_benchmark_v1_gapfill_henry16_anchor_20260403`
- accepted keep:
  - `education_of_henry_adams_public_en__16__anchored_reaction_selectivity__seed_v1`

### Unused fallback ladder
- EN `tension_reversal`:
  - `on_liberty_public_en__5__tension_reversal__seed_v1`
- EN `anchored_reaction_selectivity`:
  - `portrait_of_a_lady_public_en__10__anchored_reaction_selectivity__v2`
- ZH `distinction_definition`:
  - `biji_de_fangfa_private_zh__13__seed_1`
- EN clarification wildcard:
  - `good_strategy_bad_strategy_private_en__22__seed_1`
- ZH clarification wildcard:
  - `meiguoren_de_xingge_private_zh__8__seed_1`

Closeout interpretation:
- the plan succeeded with the primary ladder only
- the benchmark is now large enough for the intended bounded interview-legible evidence pass, without reopening broad builder work
- `public/private` stayed operational provenance only; the frozen composition is shaped by pressure, language, and scale rather than source channel

## Operating Rule After Freeze
- treat this `40 / 40` draft as historical evidence only
- the active Phase 9 benchmark pointer now lives at:
  - `reading-companion-backend/eval/manifests/splits/attentional_v2_clustered_benchmark_v1_draft.json`
- the active implementation note now lives at:
  - `docs/implementation/new-reading-mechanism/clustered-benchmark-v1-draft.md`
- do not launch a new general builder wave, promotion reopening, durable-trace work, or runtime-viability work from this closeout alone
- do not relaunch the abandoned formal decisive chapter/excerpt jobs by default now that the active benchmark pointer has moved
- historical note:
  - this archived freeze draft still records the older per-process sharding phase
  - current operator policy has since moved on:
    - `MiniMax-M2.7-personal` and `MiniMax-M2.7-highspeed` are now treated as equivalent `M2.7` targets whose main difference is speed
    - future launches may use both together when throughput helps
    - keep forcing one concrete target only when one run intentionally needs one uniform reviewer surface
