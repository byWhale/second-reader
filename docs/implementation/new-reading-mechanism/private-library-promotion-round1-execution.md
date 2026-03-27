# Private-Library Promotion Round 1 Execution

Purpose: turn the round-1 private-library promotion plan into an operational lift list for curation and review.
Use when: preparing the first real promotion packet from the combined private-library `v2` supplement.
Not for: final benchmark promotion decisions or reviewed benchmark results.
Update when: the selected candidate ids, override rules, or next-step workflow changes.

## Round-1 Execution Decision
Use the source-book plan in [private-library-promotion-round1.md](/Users/baiweijiang/Documents/Projects/reading-companion/docs/implementation/new-reading-mechanism/private-library-promotion-round1.md), but apply three execution-time quality overrides:

1. `Poor Charlie's Almanack` stays `excerpt-first` in round 1.
- Its current chapter candidates are oversized (`10096` sentences each) and are not trustworthy enough for the first chapter-level lift.
- To preserve the English argumentative chapter mix, `Supremacy` contributes a second chapter candidate instead.

2. Chinese chapter lift should avoid obvious front matter or oversized first-pass units.
- Use `fooled_by_randomness_private_zh__19`, not `__2` / `__3` front matter and not `__9` for the first chapter pass.
- Keep `kangxi_hongpiao_private_zh__73` and `__76` out of round 1 because they are appendix / acknowledgements territory.

3. Chinese excerpt lift needs one reserve narrative override.
- The priority Chinese set only has one narrative source (`张忠谋自传`), and its seed excerpts provide only `4` distinct narrative windows.
- Use one reserve narrative excerpt from `沧浪之水` to reach the intended `5`-excerpt narrative lane without forcing duplicate text into the first round.

## Lift-First Targets

### Chapters
Target:
- English: `8`
- Chinese: `8`
- per language role mix:
  - `3` expository
  - `3` argumentative
  - `2` narrative_reflective

#### English chapter lift (`8`)
1. `good_strategy_bad_strategy_private_en__22`
- role: `expository`
- why first: clear strategy/causality chapter, clean size

2. `good_strategy_bad_strategy_private_en__55`
- role: `expository`
- why first: late-book synthesis chapter, useful for longer-span coherence

3. `evicted_private_en__10`
- role: `expository`
- why first: strong institution/individual nonfiction grounding

4. `fooled_by_randomness_private_en__14`
- role: `argumentative`
- why first: good probability / anti-induction argument chapter

5. `supremacy_private_en__13`
- role: `argumentative`
- why first: modern AI/business rivalry, clean middle-chapter argumentative unit

6. `supremacy_private_en__23`
- role: `argumentative`
- why first: governance/conflict pressure, replaces the unsafe `Poor Charlie` chapter lane

7. `steve_jobs_private_en__17`
- role: `narrative_reflective`
- why first: biography + technology inflection point

8. `steve_jobs_private_en__24`
- role: `narrative_reflective`
- why first: launch/pressure narrative with strong causal structure

#### Chinese chapter lift (`8`)
1. `kangxi_hongpiao_private_zh__12`
- role: `argumentative`
- why first: strongest early institutional-causality history unit

2. `kangxi_hongpiao_private_zh__27`
- role: `argumentative`
- why first: stronger middle-history argument unit than the appendix materials

3. `fooled_by_randomness_private_zh__19`
- role: `argumentative`
- why first: usable Chinese probability/uncertainty chapter without front-matter contamination

4. `meiguoren_de_xingge_private_zh__8`
- role: `expository`
- why first: compact social-observation chapter with strong claim/evidence structure

5. `biji_de_fangfa_private_zh__13`
- role: `expository`
- why first: clean method/explanation chapter

6. `zouchu_weiyi_zhenliguan_private_zh__14`
- role: `expository`
- why first: concept/dialogue-focused philosophical exposition

7. `zhangzhongmou_zizhuan_private_zh__10`
- role: `narrative_reflective`
- why first: business-biography narrative, moderate size

8. `zhangzhongmou_zizhuan_private_zh__11`
- role: `narrative_reflective`
- why first: same biography lane, late-position narrative pressure

### Excerpts
Target:
- English: `16`
- Chinese: `16`
- per language role mix:
  - `6` expository
  - `5` argumentative
  - `5` narrative_reflective

#### English excerpt lift (`16`)
Expository `6`
1. `good_strategy_bad_strategy_private_en__22__seed_1`
2. `good_strategy_bad_strategy_private_en__22__seed_2`
3. `good_strategy_bad_strategy_private_en__55__seed_2`
4. `evicted_private_en__10__seed_1`
5. `evicted_private_en__17__seed_2`
6. `evicted_private_en__29__seed_1`

Argumentative `5`
7. `poor_charlies_almanack_private_en__10__seed_1`
8. `poor_charlies_almanack_private_en__10__seed_2`
9. `fooled_by_randomness_private_en__14__seed_1`
10. `fooled_by_randomness_private_en__14__seed_2`
11. `supremacy_private_en__13__seed_1`

Narrative `5`
12. `steve_jobs_private_en__17__seed_1`
13. `steve_jobs_private_en__17__seed_2`
14. `steve_jobs_private_en__24__seed_1`
15. `steve_jobs_private_en__24__seed_2`
16. `steve_jobs_private_en__43__seed_1`

#### Chinese excerpt lift (`16`)
Argumentative `5`
1. `kangxi_hongpiao_private_zh__12__seed_1`
2. `kangxi_hongpiao_private_zh__12__seed_2`
3. `kangxi_hongpiao_private_zh__27__seed_1`
4. `fooled_by_randomness_private_zh__9__seed_1`
5. `fooled_by_randomness_private_zh__19__seed_2`

Expository `6`
6. `meiguoren_de_xingge_private_zh__8__seed_1`
7. `meiguoren_de_xingge_private_zh__19__seed_2`
8. `biji_de_fangfa_private_zh__13__seed_1`
9. `biji_de_fangfa_private_zh__15__seed_2`
10. `zouchu_weiyi_zhenliguan_private_zh__14__seed_1`
11. `zouchu_weiyi_zhenliguan_private_zh__8__seed_1`

Narrative `5`
12. `zhangzhongmou_zizhuan_private_zh__4__seed_1`
13. `zhangzhongmou_zizhuan_private_zh__4__seed_2`
14. `zhangzhongmou_zizhuan_private_zh__10__seed_1`
15. `zhangzhongmou_zizhuan_private_zh__10__seed_2`
16. `canglang_zhishui_private_zh__16__seed_2`
- note: reserve override used deliberately to avoid duplicated narrative text inside the first Chinese excerpt round

## Review Order

### Review First
These should be checked before the rest because they carry higher structural or duplication risk.

Chapter-first sanity review:
- `supremacy_private_en__23`
- `kangxi_hongpiao_private_zh__27`
- `fooled_by_randomness_private_zh__19`
- `zhangzhongmou_zizhuan_private_zh__10`
- `zhangzhongmou_zizhuan_private_zh__11`

Excerpt-first semantic review:
- all `Good Strategy/Bad Strategy` excerpt lifts
- all `Poor Charlie's Almanack` excerpt lifts
- `kangxi_hongpiao_private_zh__12__seed_2`
- all selected `张忠谋自传` excerpt lifts
- `canglang_zhishui_private_zh__16__seed_2`

Why:
- `Good Strategy` and `Poor Charlie` currently show repeated seed windows across multiple chapter candidates
- `张忠谋自传` shows duplicated seed families across multiple narrative chapters
- `kangxi_hongpiao_private_zh__12__seed_2` includes citation-style noise and should be boundary-checked early
- the `沧浪之水` narrative excerpt is an intentional reserve override and should be judged explicitly rather than slipping in unnoticed

### Reserve / Defer For Round 1

Reserve-first book-level sources:
- English:
  - `antifragile_private_en`
  - `skin_in_the_game_private_en`
  - `black_swan_private_en`
  - `principles_private_en`
  - `shoe_dog_private_en`
  - `snowball_private_en`
  - `naval_almanack_private_en`
  - `making_of_a_manager_private_en`
  - `inspired_private_en`
- Chinese:
  - `canglang_zhishui_private_zh`
  - exception:
    - `canglang_zhishui_private_zh__16__seed_2` is pulled forward only as a narrative excerpt reserve override

Candidate-level defer list:
- all `Poor Charlie's Almanack` chapter candidates
- `kangxi_hongpiao_private_zh__73`
- `kangxi_hongpiao_private_zh__76`
- `fooled_by_randomness_private_zh__2`
- `fooled_by_randomness_private_zh__3`
- `zhangzhongmou_zizhuan_private_zh__4` for the chapter lane
- `zhangzhongmou_zizhuan_private_zh__9`

Why:
- oversized or anthology-like chapter units
- appendix / acknowledgement / front-matter contamination
- weaker first-round value than the chosen lift set

## Materialized Packet Status
The first round-1 excerpt review packets are now materialized and ready for audit/review preparation:

- English packet:
  - `reading-companion-backend/eval/review_packets/pending/attentional_v2_private_library_promotion_round1_excerpt_en/`
- Chinese packet:
  - `reading-companion-backend/eval/review_packets/pending/attentional_v2_private_library_promotion_round1_excerpt_zh/`

Both packets were exported directly from the approved `excerpt_lift.selected_ids` in [private-library-promotion-round1-selection.json](/Users/baiweijiang/Documents/Projects/reading-companion/docs/implementation/new-reading-mechanism/private-library-promotion-round1-selection.json). They should be treated as the canonical excerpt-prep entrypoint for round 1.

The chapter-lane sanity checklist now lives in:
- [private-library-promotion-round1-chapter-sanity-checklist.md](/Users/baiweijiang/Documents/Projects/reading-companion/docs/implementation/new-reading-mechanism/private-library-promotion-round1-chapter-sanity-checklist.md)

## Next Workflow Step
The main agent should treat [private-library-promotion-round1-selection.json](/Users/baiweijiang/Documents/Projects/reading-companion/docs/implementation/new-reading-mechanism/private-library-promotion-round1-selection.json) as the source of truth, then run this workflow:

1. Materialize two bilingual excerpt review packets from the selected excerpt ids:
- one English packet
- one Chinese packet
  - status:
    - done
  - packet ids:
    - `attentional_v2_private_library_promotion_round1_excerpt_en`
    - `attentional_v2_private_library_promotion_round1_excerpt_zh`

2. Run machine-side case audits on those excerpt packets first.
  - status:
    - pending

3. In parallel, do chapter-lane sanity validation on the selected `8 + 8` chapter candidates.
- especially the items listed under `Review First`
  - status:
    - checklist ready
  - use:
    - [private-library-promotion-round1-chapter-sanity-checklist.md](/Users/baiweijiang/Documents/Projects/reading-companion/docs/implementation/new-reading-mechanism/private-library-promotion-round1-chapter-sanity-checklist.md)

4. Only after those two checks should round-1 survivors be promoted into:
- the next curated excerpt review pass
- the next chapter-comparison candidate pack

Important rule:
- do not reselect the round-1 candidates by hand from the raw supplement pool unless this execution file is explicitly revised
