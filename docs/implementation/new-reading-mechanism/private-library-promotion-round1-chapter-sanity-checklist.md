# Private-Library Promotion Round 1 Chapter Sanity Checklist

Purpose: make the chapter-lane sanity pass execution-ready for the first private-library promotion round.
Use when: validating the selected `8 + 8` chapter candidates before they are used in a formal comparison or promotion pass.
Not for: final promotion decisions or judge outcomes.
Update when: the selected chapter ids, risk ordering, or sanity-check criteria change.

## Current Status
- excerpt review packets already materialized:
  - English: `reading-companion-backend/eval/review_packets/pending/attentional_v2_private_library_promotion_round1_excerpt_en/`
  - Chinese: `reading-companion-backend/eval/review_packets/pending/attentional_v2_private_library_promotion_round1_excerpt_zh/`
- this checklist is the next non-LLM preparation artifact for the same round

## Sanity-Check Contract
For each selected chapter candidate, verify:
- chapter alignment
  - the candidate is real chapter content, not title page, appendix, acknowledgements, or front matter
- boundary cleanliness
  - the chapter opens and closes on a coherent unit, without obvious truncation or parse contamination
- size safety
  - the chapter is not so large that round-1 evaluation becomes noisy or traversal-heavy by default
- role fit
  - the candidate still behaves like the intended `selection_role`
- duplication pressure
  - repeated source books in the same lane are still sufficiently distinct in content and function

## Review Order

### Review First
These should be checked before the rest because they have the highest structural or size risk.

#### English
1. `supremacy_private_en__23`
- role: `argumentative`
- reason: explicit `review_first` candidate and the second `Supremacy` chapter in the same lane
- check focus:
  - confirm it is not too close in argumentative shape to `supremacy_private_en__13`
  - confirm late-book governance/conflict material is still chapter-clean

#### Chinese
1. `kangxi_hongpiao_private_zh__27`
- role: `argumentative`
- sentence count: `924`
- reason: largest selected Chinese chapter; size risk is real even though appendix material was already excluded

2. `fooled_by_randomness_private_zh__19`
- role: `argumentative`
- sentence count: `393`
- reason: explicit override away from front matter; verify this replacement chapter is genuinely clean

3. `zhangzhongmou_zizhuan_private_zh__10`
- role: `narrative_reflective`
- sentence count: `500`
- reason: high narrative value, but large and paired with another chapter from the same source

4. `zhangzhongmou_zizhuan_private_zh__11`
- role: `narrative_reflective`
- sentence count: `500`
- reason: same-source paired narrative candidate; verify distinct pressure from `__10`

### Standard Pass
These should still be checked, but they are not the first-stop risk items.

#### English
- `good_strategy_bad_strategy_private_en__22`
  - role: `expository`
  - sentence count: `166`
- `good_strategy_bad_strategy_private_en__55`
  - role: `expository`
  - sentence count: `286`
  - note: later-book synthesis chapter; verify it is not overly summary-like
- `evicted_private_en__10`
  - role: `expository`
  - sentence count: `250`
- `fooled_by_randomness_private_en__14`
  - role: `argumentative`
  - sentence count: `259`
- `supremacy_private_en__13`
  - role: `argumentative`
  - sentence count: `232`
- `steve_jobs_private_en__17`
  - role: `narrative_reflective`
  - sentence count: `218`
- `steve_jobs_private_en__24`
  - role: `narrative_reflective`
  - sentence count: `264`

#### Chinese
- `kangxi_hongpiao_private_zh__12`
  - role: `argumentative`
  - sentence count: `629`
  - note: still oversized compared with the English lane; verify it is worth keeping despite size
- `meiguoren_de_xingge_private_zh__8`
  - role: `expository`
  - sentence count: `80`
- `biji_de_fangfa_private_zh__13`
  - role: `expository`
  - sentence count: `78`
- `zouchu_weiyi_zhenliguan_private_zh__14`
  - role: `expository`
  - sentence count: `234`

## Execution Notes
- do not promote any chapter candidate directly from this checklist alone
- if a chapter fails sanity review:
  - record the reason
  - fall back to the already-documented reserve/defer logic in [private-library-promotion-round1-execution.md](/Users/baiweijiang/Documents/Projects/reading-companion/docs/implementation/new-reading-mechanism/private-library-promotion-round1-execution.md)
- keep the excerpt packets and the chapter sanity pass separate:
  - excerpt packets can proceed to machine-side case audits
  - chapter candidates should not enter the first formal comparison pack until this sanity pass is complete
