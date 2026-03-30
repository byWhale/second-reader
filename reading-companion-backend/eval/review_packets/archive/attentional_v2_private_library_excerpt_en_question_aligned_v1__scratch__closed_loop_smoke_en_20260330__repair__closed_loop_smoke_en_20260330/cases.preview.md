# Revision/Replacement Packet `attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_smoke_en_20260330__repair__closed_loop_smoke_en_20260330`

This packet was generated automatically from cases whose current `benchmark_status` requires another hardening round.

## Dataset
- dataset_id: `attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_smoke_en_20260330`
- family: `excerpt_cases`
- language_track: `en`
- version: `2`
- targeted_statuses: `needs_revision|needs_replacement|needs_revision|needs_replacement`

## Review Actions
- `keep`
- `revise`
- `drop`
- `unclear`

## Confidence
- `high`
- `medium`
- `low`

## 1. `education_of_henry_adams_public_en__16__callback_bridge__seed_v1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `The Education of Henry Adams`
- author: `Henry Adams`
- chapter: `XI: The Battle of the Rams (1863)` (`16`)
- question_ids: `EQ-CM-002|EQ-CM-004|EQ-AV2-004`
- phenomena: `bridge_potential|callback|cross_span_link`
- selection_reason: Selected because the passage invites a backward bridge or callback that should remain source-grounded rather than associative. Anchor line: Again and again, in afterlife, he went back over the ground to see whether he could detect error on either side.
- judge_focus: Does the mechanism connect the current line to earlier material honestly and for the right reason?
- latest_review_action: `revise`
- latest_problem_types: `source_parse_problem|weak_excerpt`
- latest_revised_bucket: ``
- latest_notes: The excerpt is truncated—missing the first two sentences that establish the Confederate plan to 'break up the Union' and the American Minister's diplomatic triumph. The factual audit confirms the source contains five sentences but only three are included. More critically, all context fields (lookback_sentences, lookahead_sentences) are empty, making it impossible to evaluate the 'backward bridge or callback' mechanism the case claims to test. A proper callback_bridge case requires visible source material that the anchor line references. The archaic phrase 'in afterlife' also risks misinterpretation (post-war reflection vs. literal afterlife). Revision requires restoring the full excerpt and adding at minimum the preceding 2-3 sentences that the callback connects to.

```text
They had persisted for two years and a half in their plan for breaking up the Union, and had yielded at last only in the jaws of war.
After a long and desperate struggle, the American Minister had trumped their best card and won the game.
Again and again, in afterlife, he went back over the ground to see whether he could detect error on either side.
He found none.
At every stage the steps were both probable and proved.
```

## 2. `education_of_henry_adams_public_en__29__anchored_reaction_selectivity__seed_v1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `The Education of Henry Adams`
- author: `Henry Adams`
- chapter: `XXIV: Indian Summer (1898–1899)` (`29`)
- question_ids: `EQ-CM-002|EQ-AV2-005`
- phenomena: `reaction_anchor|selective_legibility|visible_thought`
- selection_reason: Selected because the passage contains a line that seems reaction-worthy but still demands selective, anchored reading. Anchor line: Constantly he repulsed argument: “Adams, you reason too much!”
- judge_focus: Is the visible reaction anchored to the actual line and genuinely worth preserving?
- latest_review_action: `revise`
- latest_problem_types: `weak_excerpt|source_parse_problem`
- latest_revised_bucket: ``
- latest_notes: The factual audit reveals the excerpt is missing the first sentence describing Okakura's thought running 'as a stream runs through grass'—the vivid visible_thought metaphor that sets up the reaction anchor. The stored excerpt_text appears complete but the reconstruction shows the source parsing dropped this crucial context sentence. The anchor line 'Adams, you reason too much!' is thin on its own; the preceding metaphor is what makes this passage valuable for testing selective legibility. Recommend re-extracting the source to capture the full excerpt with the Okakura description intact before benchmark entry.

```text
As he said of his friend Okakura, his thought ran as a stream runs through grass, hidden perhaps but always there; and one felt often uncertain in what direction it flowed, for even a contradiction was to him only a shade of difference, a complementary color, about which no intelligent artist would dispute.
Constantly he repulsed argument: “Adams, you reason too much!”
was one of his standing reproaches even in the mild discussion of rice and mangoes in the warm night of Tahiti dinners.
```

## 3. `education_of_henry_adams_public_en__7__distinction_definition__seed_v1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `The Education of Henry Adams`
- author: `Henry Adams`
- chapter: `II: Boston (1848–1854)` (`7`)
- question_ids: `EQ-CM-002|EQ-AV2-002|EQ-AV2-005`
- phenomena: `distinction|definition_pressure|anchored_reaction`
- selection_reason: The passage draws a precise distinction between Charles Francis Adams's relationship with State Street and Edward Everett's, with the former being 'more natural' yet resulting in deliberate aloofness and renewed conflict. However, the excerpt as currently constructed is too truncated—starting mid-sentence with a dangling fragment—and lacks sufficient surrounding context for readers to ground the comparison.
- judge_focus: Does the reader correctly identify the comparison being made between Adams and Everett regarding their relations to State Street, and trace how the 'natural' relation paradoxically leads to alienation rather than alignment?
- latest_review_action: `revise`
- latest_problem_types: `weak_excerpt|source_parse_problem|text_noise`
- latest_revised_bucket: `distinction`
- latest_notes: The excerpt text mismatch (factual audit) combined with truncation starting mid-sentence ('Everett, his seniors.') indicates a source parse problem. The distinction mechanism itself (Adams vs. Everett and State Street) is conceptually sound but operationally unanchored without lookback/lookahead context. The case needs fuller surrounding sentences establishing who 'him' refers to, what State Street symbolizes, and why 'the old war since 1700' matters. Without this, the reading move is not sufficiently answerable to the passage.

```text
Everett, his seniors.
Between him and State Street the relation was more natural than between Edward Everett and State Street; but instead of doing so, Charles Francis Adams drew himself aloof and renewed the old war which had already lasted since 1700.
He could not help it.
```

## 4. `education_of_henry_adams_public_en__8__tension_reversal__seed_v1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `The Education of Henry Adams`
- author: `Henry Adams`
- chapter: `III: Washington (1850–1854)` (`8`)
- question_ids: `EQ-CM-002|EQ-AV2-003|EQ-AV2-005`
- phenomena: `tension_reversal|controller_move_quality|anchored_reaction`
- selection_reason: The passage contains a clear tension_reversal: the effort to build a Washington monument failed, yet people still make pilgrimages to Mount Vernon despite the difficult journey. This paradox between stated failure and persistent practice captures the reversal phenomenon effectively.
- judge_focus: Does the mechanism stay with the reversal—acknowledging both the failed monument effort and the continued Mount Vernon pilgrimages—instead of flattening it into a generic summary that erases the tension between failure and persistence?
- latest_review_action: `revise`
- latest_problem_types: `source_parse_problem|weak_excerpt`
- latest_revised_bucket: ``
- latest_notes: The excerpt_text is missing the opening sentence ('People made pilgrimages to Mount Vernon and made even an effort to build Washington a monument.') that exists in the source, causing a source_parse_problem. Additionally, the excerpt ends mid-sentence with 'Mr.' indicating truncation. The passage is too brief (even when complete) to provide adequate material for reading mechanism evaluation. Fix the missing sentence inclusion and extend the excerpt to capture more context around this tension_reversal. Also remove extraneous phenomena tags (controller_move_quality, anchored_reaction) that are not clearly demonstrated—retain only tension_reversal.

```text
People made pilgrimages to Mount Vernon and made even an effort to build Washington a monument.
The effort had failed, but one still went to Mount Vernon, although it was no easy trip.
Mr.
```
