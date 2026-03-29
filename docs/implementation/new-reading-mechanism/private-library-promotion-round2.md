# Private-Library Promotion Round2

- generated_at: `2026-03-28T02:43:23.176477Z`
- decision: `hold_for_backlog_rescue`
- source_of_truth:
  - EN: `/Users/baiweijiang/Documents/Projects/reading-companion/reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_private_library_excerpt_en_v2/cases.jsonl`
  - ZH: `/Users/baiweijiang/Documents/Projects/reading-companion/reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_private_library_excerpt_zh_v2/cases.jsonl`

## `2026-03-29` Post-Cleanup Gate Update
- gate posture remains: `hold`
- review queue state:
  - `reading-companion-backend/eval/review_packets/review_queue_summary.json`
  - `active_packet_count = 0`
- both follow-up cleanup packet summaries explicitly recorded:
  - `decision_bearing_followup_launched: false`

### Follow-Up Cleanup Results
- EN follow-up:
  - packet id: `attentional_v2_private_library_cleanup_en_followup_after_recovery_20260329`
  - action counts: `{"drop": 6, "revise": 3, "keep": 0}`
- ZH follow-up:
  - packet id: `attentional_v2_private_library_cleanup_zh_followup_after_recovery_20260329`
  - action counts: `{"drop": 2, "revise": 1, "keep": 0}`
- practical interpretation:
  - the extra cleanup pass hardened the backlog mechanically
  - it did not produce any new `keep` decisions
  - so it did not strengthen the promotion gate by itself

### Current Local-Only Excerpt State
- EN:
  - total rows: `170`
  - `reviewed_active`: `7`
  - `needs_revision`: `3`
  - `needs_replacement`: `6`
  - `unset`: `154`
  - open backlog: `9`
- ZH:
  - total rows: `56`
  - `reviewed_active`: `13`
  - `needs_revision`: `1`
  - `needs_replacement`: `2`
  - `unset`: `40`
  - open backlog: `3`
- combined:
  - `reviewed_active`: `20`
  - open backlog: `12`
  - `unset`: `194`

### Gate Interpretation
- English remains the constraining lane:
  - only `7` `reviewed_active`
  - follow-up cleanup added `0` new keeps
- Chinese is healthier, but the gate is bilingual, so English still limits confidence.
- `needs_revision` and `needs_replacement` remain benchmark-hardening statuses, not promotion-ready statuses.
- the raw `unset` volume is not benchmark-ready size; it is only remaining mining headroom.
- the human-owned decisions still open are:
  - `OD-PRIVATE-LIBRARY-POST-RESCUE-GATE`
  - `OD-BENCHMARK-SIZE`
- safe mechanical work may continue:
  - build better replacement candidates
  - generate new revision/replacement packets
  - run audit, adjudication, import, and archive
  - refresh shared queue summaries after those jobs finish
- work still stops before:
  - promotion reopening
  - reviewed-slice freezing
  - durable-trace / re-entry / runtime-viability
  - default-cutover decisions

## Policy
- mode: `hold_if_thin`
- source cap: `2`
- thresholds: `{"en": 7, "zh": 9}`
- Chinese reserve-only handling:
  - conditional reserve: `zhangzhongmou_zizhuan_private_zh`
  - reserve-only: `canglang_zhishui_private_zh`

## Cleanup Packet Outcomes
### EN
- packet_id: `attentional_v2_private_library_cleanup_round3_en_ready`
- archive_dir: `/Users/baiweijiang/Documents/Projects/reading-companion/reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_round3_en_ready`
- action_counts: `{"drop": 2, "keep": 0, "revise": 4, "unclear": 0}`

### ZH
- packet_id: `attentional_v2_private_library_cleanup_round3_zh_ready`
- archive_dir: `/Users/baiweijiang/Documents/Projects/reading-companion/reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_round3_zh_ready`
- action_counts: `{"drop": 0, "keep": 3, "revise": 1, "unclear": 0}`

## Gate Evaluation
### EN
- pass: `False`
- reviewed_active: `6` (baseline `6`, threshold `7`)
- role_coverage_preserved: `True`
- source_breadth_preserved: `True`
- hold_reasons: `reviewed_active below threshold (6 < 7)`

### ZH
- pass: `True`
- reviewed_active: `11` (baseline `8`, threshold `9`)
- role_coverage_preserved: `True`
- source_breadth_preserved: `True`
- non_reserve_broadening: `True`

## Excerpt Survivors
### EN
- reviewed_active: `6`
- by_role: `{"argumentative": 1, "expository": 4, "narrative_reflective": 1}`

- `evicted_private_en` | `Evicted` | roles `{"expository": 1}` | case_ids `evicted_private_en__29__seed_1`
- `fooled_by_randomness_private_en` | `Fooled by Randomness` | roles `{"argumentative": 1}` | case_ids `fooled_by_randomness_private_en__14__seed_1`
- `good_strategy_bad_strategy_private_en` | `Good Strategy/Bad Strategy` | roles `{"expository": 3}` | case_ids `good_strategy_bad_strategy_private_en__22__seed_1, good_strategy_bad_strategy_private_en__22__seed_2, good_strategy_bad_strategy_private_en__55__seed_2`
- `steve_jobs_private_en` | `Steve Jobs` | roles `{"narrative_reflective": 1}` | case_ids `steve_jobs_private_en__43__seed_1`

### ZH
- reviewed_active: `11`
- by_role: `{"argumentative": 2, "expository": 5, "narrative_reflective": 4}`

- `biji_de_fangfa_private_zh` | `笔记的方法` | roles `{"expository": 2}` | case_ids `biji_de_fangfa_private_zh__13__seed_1, biji_de_fangfa_private_zh__15__seed_2`
- `canglang_zhishui_private_zh` | `沧浪之水` | roles `{"narrative_reflective": 1}` | case_ids `canglang_zhishui_private_zh__16__seed_2`
- `fooled_by_randomness_private_zh` | `随机漫步的傻瓜` | roles `{"argumentative": 1}` | case_ids `fooled_by_randomness_private_zh__9__seed_1`
- `kangxi_hongpiao_private_zh` | `康熙的红票：全球化中的清朝` | roles `{"argumentative": 1}` | case_ids `kangxi_hongpiao_private_zh__12__seed_1`
- `meiguoren_de_xingge_private_zh` | `美国人的性格` | roles `{"expository": 2}` | case_ids `meiguoren_de_xingge_private_zh__19__seed_2, meiguoren_de_xingge_private_zh__8__seed_1`
- `zhangzhongmou_zizhuan_private_zh` | `张忠谋自传(1931-1964)` | roles `{"narrative_reflective": 3}` | case_ids `zhangzhongmou_zizhuan_private_zh__10__seed_1, zhangzhongmou_zizhuan_private_zh__10__seed_2, zhangzhongmou_zizhuan_private_zh__4__seed_1`
- `zouchu_weiyi_zhenliguan_private_zh` | `走出唯一真理观` | roles `{"expository": 1}` | case_ids `zouchu_weiyi_zhenliguan_private_zh__14__seed_1`

## Chapter Constraints
- English chapter lane: `keep_current_8`
- Chinese chapter lane: `limit_to_current_2`

### English Eligible Chapter IDs
- `good_strategy_bad_strategy_private_en__22`
- `good_strategy_bad_strategy_private_en__55`
- `evicted_private_en__10`
- `fooled_by_randomness_private_en__14`
- `supremacy_private_en__13`
- `supremacy_private_en__23`
- `steve_jobs_private_en__17`
- `steve_jobs_private_en__24`

### Chinese Eligible Chapter IDs
- `biji_de_fangfa_private_zh__13`
- `zouchu_weiyi_zhenliguan_private_zh__14`

## Formal Excerpt Promotion Shortlist
- status: `withheld_until_gate_passes`
- result: `hold_for_backlog_rescue`
- no formal shortlist is finalized in this slice

## Parked Fix Backlog
### EN
- `evicted_private_en` | `Evicted` | families `replacement` | case_ids `evicted_private_en__10__seed_1`
- `fooled_by_randomness_private_en` | `Fooled by Randomness` | families `parse_noise_boundary` | case_ids `fooled_by_randomness_private_en__14__seed_2`
- `poor_charlies_almanack_private_en` | `Poor Charlie's Almanack` | families `parse_noise_boundary, replacement` | case_ids `poor_charlies_almanack_private_en__10__seed_1, poor_charlies_almanack_private_en__10__seed_2`

### ZH
- `fooled_by_randomness_private_zh` | `随机漫步的傻瓜` | families `parse_noise_boundary` | case_ids `fooled_by_randomness_private_zh__19__seed_2`
- `kangxi_hongpiao_private_zh` | `康熙的红票：全球化中的清朝` | families `parse_noise_boundary, replacement` | case_ids `kangxi_hongpiao_private_zh__12__seed_2, kangxi_hongpiao_private_zh__27__seed_1`
- `zouchu_weiyi_zhenliguan_private_zh` | `走出唯一真理观` | families `parse_noise_boundary` | case_ids `zouchu_weiyi_zhenliguan_private_zh__8__seed_1`
