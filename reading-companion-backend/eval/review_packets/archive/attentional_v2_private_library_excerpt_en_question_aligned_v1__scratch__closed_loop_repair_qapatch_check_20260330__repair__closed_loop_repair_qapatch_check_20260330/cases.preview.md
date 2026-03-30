# Revision/Replacement Packet `attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_repair_qapatch_check_20260330__repair__closed_loop_repair_qapatch_check_20260330`

This packet was generated automatically from cases whose current `benchmark_status` requires another hardening round.

## Dataset
- dataset_id: `attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_repair_qapatch_check_20260330`
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
- selection_reason: Selected because the passage contains Adams's reflective retrospective on his own diplomatic actions, where the narrator examines his own past decisions after the fact. The 'he' pronoun is ambiguous—referring to Adams himself as the American Minister—which creates interpretive work around narrative identity in a memoir.
- judge_focus: Does the passage clearly establish that Adams (the narrator) is looking back at his own earlier diplomatic actions as 'the American Minister,' rather than confating different persons or events? Is the retrospective judgment 'He found none' traceable to a specific prior action or decision that the excerpt itself grounds?
- latest_review_action: `revise`
- latest_problem_types: `ambiguous_focus|weak_excerpt|source_parse_problem`
- latest_revised_bucket: `callback`
- latest_notes: The adversarial review correctly identifies that the excerpt lacks explicit bridging language connecting Adams's retrospective lookback to specific earlier content about Seward or Russell. The bucket labels (bridge_potential, cross_span_link) overstate what the excerpt demonstrates—it shows reflective memoir mode but no textual callback anchor. The 'he' in 'he went back over the ground' is ambiguous (Adams vs. American Minister) without clear disambiguation within the five sentences. The case should be revised to either (a) add surrounding context clarifying the referent and bridging language, or (b) reclassify as a simpler narrative-reflective case without cross-span claims.

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
- selection_reason: Selected because the passage crystallizes an intellectual paradox: Whistler's theatrical, declamatory performance contained genuine substantive truth. Adams's visible thought is the analytical distinction between expressive style and underlying veracity—not a visceral personal reaction to the anchor line.
- judge_focus: Does the visible thought demonstrate Adams's capacity to distinguish theatrical performance from substantive truth, making the paradox (declamation containing truth) worth preserving for evaluation?
- latest_review_action: `revise`
- latest_problem_types: `ambiguous_focus|wrong_bucket`
- latest_revised_bucket: `paradox_observation`
- latest_notes: The excerpt's strongest analytical feature is the paradox-noting (bombast containing truth) rather than a visceral reaction to Whistler's line. Adams reports agreeing with Whistler 'as a matter of course'—a thin reaction that doesn't clearly demonstrate the targeted anchored reaction_selectivity profile. The alternative bucket 'paradox_observation' better fits the text's actual strength: Adams's intellectual discernment between style and substance. Relabeling and refocusing the judge question would clarify evaluation criteria and improve bucket coherence.

```text
At that moment the Boer War was raging, and, as everyone knows, on that subject Whistler raged worse than the Boers.
For two hours he declaimed against England﻿—witty, declamatory, extravagant, bitter, amusing, and noisy; but in substance what he said was not merely commonplace﻿—it was true!
That is to say, his hearers, including Adams and, as far as he knew, La Farge, agreed with it all, and mostly as a matter of course; yet La Farge was silent, and this difference of expression was a difference of art.
```

## 3. `education_of_henry_adams_public_en__7__distinction_definition__seed_v1`

- benchmark_status: `needs_revision`
- review_status: `llm_reviewed`
- book: `The Education of Henry Adams`
- author: `Henry Adams`
- chapter: `II: Boston (1848–1854)` (`7`)
- question_ids: `EQ-CM-002|EQ-AV2-002|EQ-AV2-005`
- phenomena: `distinction|definition_pressure|anchored_reaction`
- selection_reason: The excerpt demonstrates a clear distinction between Charles Francis Adams's 'more natural' political relation with State Street versus his deliberate choice to 'draw himself aloof' and renew an inherited family conflict. This contrast between inherited potential and chosen alienation tests a genuine distinction-reading move, but the compressed historical framing and 'He could not help it' line create ambiguity about mechanism targets that requires clarification through revised judge focus.
- judge_focus: Does the mechanism identify the natural/unnatural relational distinction cleanly and answer whether Charles Francis Adams's withdrawal was a chosen strategic act rather than an inevitable inheritance?
- latest_review_action: `revise`
- latest_problem_types: `text_noise|ambiguous_focus`
- latest_revised_bucket: ``
- latest_notes: The primary review correctly identifies the core distinction, but the adversarial review raises legitimate concerns about ambiguity between distinction (chosen alienation) and anchored_reaction/inherited_determinism (inevitable repetition). The 'He could not help it' line injects causal uncertainty that could pull reading moves away from the cleaner natural/unnatural distinction toward a deterministic inheritance reading. Minor text_noise (line break artifacts like 'Webster and Mr.' / 'Everett, his seniors.') should be cleaned. Revision should tighten the judge_focus to anchor the mechanism to the distinction rather than the determinism ambiguity.

```text
Those of the generation of 1812 had mostly disappeared in 1850; death had cleared that score; the quarrels of John Adams, and those of John Quincy Adams were no longer acutely personal; the game was considered as drawn; and Charles Francis Adams might then have taken his inherited rights of political leadership in succession to Mr. Webster and Mr. Everett, his seniors.
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
- selection_reason: Selected because the passage contains a pressure point or reversal that should reward a proportionate, text-grounded move. Anchor line: The effort had failed, but one still went to Mount Vernon, although it was no easy trip.
- judge_focus: Does the mechanism stay with the reversal or tension instead of flattening it into generic summary?
- latest_review_action: `revise`
- latest_problem_types: `weak_excerpt|too_easy`
- latest_revised_bucket: ``
- latest_notes: The tension_reversal is legitimate but the excerpt's compressed structure undermines it: the 'but' conjunction states the reversal outright, and the failed monument/pilgrimage are sequential observations rather than an active expectation-reversal mid-course. The subsequent 'Virginia education' point is thematically disconnected from the tension, diluting focus. A stronger excerpt would let the reversal develop organically over more sentences, allowing readers to notice the tension building before the contradiction resolves. Consider expanding to include more of the surrounding context to deepen interpretive challenge.

```text
People made pilgrimages to Mount Vernon and made even an effort to build Washington a monument.
The effort had failed, but one still went to Mount Vernon, although it was no easy trip.
Mr. Adams took the boy there in a carriage and pair, over a road that gave him a complete Virginia education for use ten years afterwards.
```
