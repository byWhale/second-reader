# Formal Benchmark V1 Freeze Draft

Purpose: record the first explicit case-id freeze draft for the reduced three-target formal benchmark and make the next excerpt gap-fill wave concrete.
Use when: freezing `chapter_core`, checking which `excerpt_core` cases are already formal-benchmark-ready, or deciding what the next targeted review wave should contain.
Not for: stable evaluation methodology, final promotion claims, or one-off review-packet details.
Update when: the frozen draft changes, a gap-filling wave lands, or the formal benchmark moves from draft to frozen.

## Scope
- Active formal benchmark targets:
  - `reader_character.selective_legibility`
  - `reader_character.coherent_accumulation`
  - `reader_value.insight_and_clarification`
- Canonical machine-readable companion:
  - `reading-companion-backend/eval/manifests/splits/attentional_v2_formal_benchmark_v1_draft.json`
- Working rule:
  - this draft freezes explicit case ids instead of relying on auto-core selection
  - source origin remains provenance only and must not define the benchmark shape

## Chapter Core Draft
The chapter lane is ready to freeze now.

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

## Excerpt Core Frozen Now
The current tracked reviewed slice now supports `18` formal excerpt cases.

### `distinction_definition`
- `women_and_economics_public_en__6__distinction_definition__v2`
- `women_and_economics_public_en__9__distinction_definition__v2`
- `varieties_of_religious_experience_public_en__6__distinction_definition__v2`
- `gushi_xinbian_public_zh__4__distinction_definition__v2`
- `ouyou_zaji_public_zh__4__distinction_definition__v2`

### `tension_reversal`
- `darkwater_public_en__9__tension_reversal__v2`
- `darkwater_public_en__12__tension_reversal__v2`
- `rulin_waishi_24032_zh__6__tension_reversal__v2`
- `rulin_waishi_24032_zh__14__tension_reversal__v2`
- `ershinian_mudu_public_zh__17__tension_reversal__v2`

### `anchored_reaction_selectivity`
- `up_from_slavery_public_en__5__anchored_reaction_selectivity__v2`
- `nahan_27166_zh__5__anchored_reaction_selectivity__v2`
- `zhaohua_xishi_25271_zh__5__anchored_reaction_selectivity__v2`
- `ershinian_mudu_public_zh__37__anchored_reaction_selectivity__v2`

### `callback_bridge_or_modest_cross_span_link`
- `walden_205_en__6__callback_bridge__v2`
- `on_liberty_public_en__10__callback_bridge__v2`
- `jinghua_yuan_25377_zh__34__callback_bridge__v2`
- `nahan_27166_zh__2__callback_bridge__v2`

### Holdouts
- callback overflow reserve:
  - `jinghua_yuan_25377_zh__15__callback_bridge__v2`
- paused durable-trace-adjacent reviewed cases:
  - `souls_of_black_folk_408_en__4__reconsolidation_later_reinterpretation__v2`
  - `souls_of_black_folk_408_en__8__reconsolidation_later_reinterpretation__v2`
  - `chenlun_public_zh__4__reconsolidation_later_reinterpretation__v2`

## Gap Map
Current formal-benchmark-v1 status remains:
- `chapter_core`: `16 / 16`
- `excerpt_core`: `18 / 24`
- total: `34 / 40`

Remaining excerpt gaps:
- `distinction_definition`
  - EN: `0`
  - ZH: `1`
- `tension_reversal`
  - EN: `1`
  - ZH: `0`
- `anchored_reaction_selectivity`
  - EN: `2`
  - ZH: `0`
- `callback_bridge_or_modest_cross_span_link`
  - EN: `0`
  - ZH: `0`
- clarification wildcard / under-covered pressure
  - EN: `1`
  - ZH: `1`

## First Review Wave Plus Bounded Reruns
The first tracked `5`-case builder-active review wave is complete, and the two formatting-blocked reruns are now closed.

### Reviewed packet outcomes
- EN packet:
  - `attentional_v2_formal_benchmark_v1_excerpt_wave1_en_20260402`
  - result: `0 keep`, `2 revise`
- ZH packet:
  - `attentional_v2_formal_benchmark_v1_excerpt_wave1_zh_20260402`
  - result: `2 keep`, `1 revise`

### Direct new promotions from this wave
- `ouyou_zaji_public_zh__4__distinction_definition__v2`
- `ershinian_mudu_public_zh__37__anchored_reaction_selectivity__v2`

### Bounded rerun promotions after the excerpt-normalization repair
- `women_and_economics_public_en__9__distinction_definition__v2`
- `rulin_waishi_24032_zh__6__tension_reversal__v2`

### Still deferred
- `portrait_of_a_lady_public_en__10__anchored_reaction_selectivity__v2`

Closeout interpretation:
- the bounded factual-audit repair now normalizes excerpt text for comparison by stripping harmless formatting characters and collapsing whitespace / newlines
- `women_and_economics_public_en__9__distinction_definition__v2`
  - the rerun cleared factual audit and upgraded the case into the frozen-now slice as a real EN distinction fill
- `rulin_waishi_24032_zh__6__tension_reversal__v2`
  - the rerun also cleared factual audit and upgraded the case into the frozen-now slice as a real ZH tension fill
- `portrait_of_a_lady_public_en__10__anchored_reaction_selectivity__v2`
  - this remains a substantive focus problem rather than a formatting problem:
  - the excerpt still reads as broad visible-thought instead of a sharply testable anchored reaction

## Next After Bounded Reruns
The next move should stay bounded and quota-filling.

### First: promote the stable local Henry Adams reviewed candidates
- `education_of_henry_adams_public_en__8__tension_reversal__seed_v1`
- `education_of_henry_adams_public_en__16__anchored_reaction_selectivity__seed_v1`

Why these first:
- they have repeated `reviewed_active` outcomes across multiple closed-loop scratch runs
- they are the cleanest next route for one EN tension slot and one EN anchored slot
- they keep the next spend on quota-filling evidence instead of reopening broad mining

### Keep one tracked fallback explicit, but deferred
- `portrait_of_a_lady_public_en__10__anchored_reaction_selectivity__v2`

Why not now:
- the case still failed for focus, not for formatting
- we already have a cheaper and cleaner EN support lane through Henry Adams
- this should remain a fallback, not the automatic next spend

### Reserve / overflow candidates
- `on_liberty_public_en__13__distinction_definition__seed_v1`
- `beiying_public_zh__2__tension_reversal__seed_v1`
- `on_liberty_public_en__4__callback_bridge__seed_v1`
- `on_liberty_public_en__5__callback_bridge__seed_v1`
- `education_of_henry_adams_public_en__29__callback_bridge__seed_v1`

Use these only when:
- one of the remaining quota-filling candidates fails review
- or the diversity floor later needs a better swap than the tracked reviewed default

## Final Four Gaps
If the planned Henry Adams local promotions also land, the benchmark should still be missing:
- one ZH `distinction_definition` case
- one EN `anchored_reaction_selectivity` case
- one EN clarification wildcard
- one ZH clarification wildcard

Recommended next-stage targets for those last four gaps:
- EN `anchored_reaction_selectivity` tracked fallback:
  - `portrait_of_a_lady_public_en__10__anchored_reaction_selectivity__v2`
- ZH `distinction_definition` or clarifying-distinction source candidates:
  - `zouchu_weiyi_zhenliguan_private_zh__14__seed_1`
  - `biji_de_fangfa_private_zh__13__seed_1`
  - `meiguoren_de_xingge_private_zh__8__seed_1`
- EN clarification-wildcard source candidates:
  - `evicted_private_en__29__seed_1`
  - `good_strategy_bad_strategy_private_en__22__seed_1`
  - `steve_jobs_private_en__43__seed_1`
- ZH clarification-wildcard source candidates:
  - `kangxi_hongpiao_private_zh__12__seed_1`
  - `meiguoren_de_xingge_private_zh__19__seed_2`
  - `zhangzhongmou_zizhuan_private_zh__4__seed_1`

Interpretation:
- the portrait case is a tracked fallback, not an automatic rerun target
- the other entries are source candidates, not yet frozen formal cases
- use them to finish the last four cells only
- do not reopen broad mining or a general builder wave unless this targeted finish still fails
