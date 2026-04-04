# Question-Aligned Case Construction

Purpose: define the concrete Phase 2 design for building evaluation cases, datasets, and fixture inputs from managed books without relying on coarse fixed-window heuristics.
Use when: implementing the next dataset-platform phase, designing evaluation-case generation, or deciding what the unattended loop should depend on.
Not for: final benchmark decisions, public API behavior, or one-off case review outcomes.
Update when: the case-construction artifacts, target-profile model, adequacy scoring, or loop handoff contract changes.

## Why This Phase Exists
- The project already has strong machinery for:
  - managed source intake
  - canonical parsing
  - source screening
  - dataset packaging
  - packetized audit, adjudication, import, and archive
- The weakest current layer is the semantic construction of evaluation cases.
- The current excerpt builder still leans too much on:
  - fixed windows inside otherwise good chapters
  - role-based bucket preference tables
  - coarse position heuristics such as early/middle/late chapter placement
- That is not strong enough for the current product and evaluation goal:
  - create cases that answer explicit reader-evaluation questions
  - expose meaningful mechanism differences
  - remain judgeable, reviewable, and replaceable

## Naming
- Phase 2 should be called:
  - `Question-Aligned Case Construction`
- The later full automation phase should be called:
  - `Closed-Loop Benchmark Curation`
- Avoid `smart builder` as the primary name.
  - it is too vague
  - it does not reveal what the system is actually trying to optimize

## Design Goal
The system should construct benchmark assets from source books by answering this question:

`What case should exist because it helps evaluate one explicit reader-quality question under judgeable conditions?`

This is stronger than:
- "what passages look interesting?"
- "what windows are easy to extract?"
- "what book categories do we still need more of?"

## Core Principles
- Question first, dataset second.
- Phenomenon first, window second.
- Judgeability is required, not optional.
- Keep deterministic infrastructure where reproducibility matters.
- Use LLMs where semantic detection, ambiguity checking, and case shaping are genuinely needed.
- Reuse current review outcomes instead of rebuilding from zero each round.
- Preserve the current case schema where it is already good.
- Keep decision-bearing promotion, freeze, and cutover actions human-owned.

## Scope
Question-Aligned Case Construction should eventually support four benchmark-asset families:
- excerpt cases
- chapter corpora
- runtime / resume fixtures
- compatibility / durable-trace fixtures

The first implementation focus should be:
- excerpt cases

Because excerpt cases are where:
- the current heuristic weakness is strongest
- the benchmark hardening loop already exists
- review feedback is richest

## First Landing
The first live implementation is now landed on the managed local supplement path, and it now has a reusable scratch-safe build mode for validation runs.

The current dataset ids still use `private_library` for continuity with existing evidence and review artifacts, but that naming is now historical rather than a preferred platform boundary.

Current code entrypoints:
- `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
- `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py`

Current private-library outputs:
- candidate datasets:
  - `attentional_v2_private_library_excerpt_en_question_aligned_v1`
  - `attentional_v2_private_library_excerpt_zh_question_aligned_v1`
- scratch-safe candidate datasets:
  - `attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__<run_id>`
  - `attentional_v2_private_library_excerpt_zh_question_aligned_v1__scratch__<run_id>`
- durable intermediate artifacts under `reading-companion-backend/state/dataset_build/`:
  - `target_profiles/`
  - `opportunity_maps/`
  - `candidate_cases/`
  - `reserve_cases/`
  - `adequacy_reports/`
- scratch build runs keep their own artifact and manifest namespace under:
  - `reading-companion-backend/state/dataset_build/build_runs/<run_id>/`
  - this includes:
    - `target_profiles/`
    - `opportunity_maps/`
    - `candidate_cases/`
    - `reserve_cases/`
    - `adequacy_reports/`
    - `manifests/`
    - `build_summary.json`
    - `build_summary.md`

Current feedback source:
- the live reviewed local-only datasets stay separate and are read as feedback truth:
  - `attentional_v2_private_library_excerpt_en_v2`
  - `attentional_v2_private_library_excerpt_zh_v2`
- this means the first landing does not overwrite the current review-truth datasets while the new construction path is still being validated
- feedback can also be disabled or overridden explicitly when a scratch run needs to test construction behavior in isolation

## Human-Notes-Guided Dataset V1
An isolated notes-guided dataset line is now landed on top of the same question-aligned builder instead of creating a second review stack.

Current code entrypoints:
- `reading-companion-backend/eval/attentional_v2/library_notes.py`
- `reading-companion-backend/eval/attentional_v2/register_library_notes.py`
- `reading-companion-backend/eval/attentional_v2/human_notes_guided_dataset.py`
- `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py`

Current managed notes assets:
- catalog:
  - `reading-companion-backend/state/dataset_build/library_notes_catalog.json`
  - `reading-companion-backend/state/dataset_build/library_notes_catalog.md`
- storage:
  - `reading-companion-backend/state/library_notes/raw_exports/`
  - `reading-companion-backend/state/library_notes/entries/`
- current line shape:
  - exactly `5` notes assets linked to the requested `5` books
  - `The Value of Others` reuses the existing managed source instead of duplicating the EPUB
  - `纳瓦尔宝典` stays a distinct zh source because the note alignment depends on that edition rather than on the older English Naval source

Current notes-guided builder behavior:
- human notes are treated as strong priors, not benchmark truth
- final case ids remain chapter-scoped even when cluster resolution expands across adjacent short chapters
- the notes-guided mode now resolves against the full chapter pool of each selected source, not only the `screen_source_book` top-6 candidate chapters
- contiguous short-chapter windows now fall back to numeric `chapter_id` order when `chapter_number` is absent or always `0`
- two different notes-guided clusters may intentionally keep the same `chapter_case_id` when they represent different selection groups
  - this matters for `The Value of Others`, where both dense page bands currently resolve to the same chapter but still need separate case construction surfaces

Current isolated scratch evidence:
- run id:
  - `human_notes_guided_dataset_v1_20260404`
- summary:
  - `reading-companion-backend/state/dataset_build/build_runs/human_notes_guided_dataset_v1_20260404/build_summary.json`
- cluster resolution:
  - `reading-companion-backend/state/dataset_build/build_runs/human_notes_guided_dataset_v1_20260404/cluster_resolutions/attentional_v2_human_notes_guided_dataset_v1_excerpt_scope__scratch__human_notes_guided_dataset_v1_20260404.json`
- current selected cluster count:
  - `8`
- current scratch outputs:
  - English candidate cases: `16`
  - English reserves: `4`
  - Chinese candidate cases: `47`
  - Chinese reserves: `10`
- current known shortfall:
  - `nawaer_baodian_private_zh__wealth` currently tops out at `7` candidate cases with no reserve rows, so the line is construction-usable but not yet freeze-complete

Current governance:
- this dataset line is intentionally isolated from the active clustered benchmark v1
- do not repoint the active benchmark based on this line alone
- the first reviewed freeze decision now exists for the freeze-eligible clusters:
  - draft:
    - `docs/implementation/new-reading-mechanism/human-notes-guided-dataset-v1-freeze-draft.md`
  - frozen local reviewed slices:
    - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_en_reviewed_cluster_freeze_20260404`
    - `reading-companion-backend/state/eval_local_datasets/excerpt_cases/attentional_v2_human_notes_guided_dataset_v1_excerpt_zh_reviewed_cluster_freeze_20260404`
  - current frozen reviewed rows:
    - `49` across `7 / 8` selection groups
  - current held cluster:
    - `nawaer_baodian_private_zh__wealth`
- the next decision point is now narrow repair on the held cluster, not automatic merge or promotion

## Latest Scratch Evidence
The first real quality-fix wave is now landed in the builder and audit reconstruction paths:
- `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
- `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`

Current bounded fixes:
- preserve the full excerpt span in stored sentence ids instead of collapsing to anchor/support bounds
- stitch parser-fragment splits and expand windows around broken edges before rendering the final excerpt
- stitch Chinese continuation fragments without injecting synthetic spaces into the rendered excerpt
- strip invisible Unicode format characters and normalize non-breaking whitespace before builder-facing excerpt text and anchor lines are emitted into cases or packet review
- require explicit backward-link markers for callback candidates
- reject obvious reported-speech false positives for anchored-reaction candidates
- penalize context-dependent fragment anchors
- reject paratext / bibliographic windows
- keep low-priority profile-order filler candidates from outranking much stronger same-chapter opportunities
- penalize `reconsolidation_later_reinterpretation` candidates that have no explicit later / reinterpretation cue instead of letting late-scene preference alone carry them
- suppress feedback/deficit boosts when cue-free weak Chinese narrative candidates would otherwise be promoted only because a profile is sparse
- require explicit local tension cues for Chinese narrative `tension_reversal` candidates instead of letting atmospheric scene-setting masquerade as reversal pressure
- skip sub-threshold second-pass chapter fillers instead of force-filling every chapter with a weak case
- store fragment-aware anchor lines by reusing the merged readable line when the raw anchor sentence is only a parser fragment

Current real-run evidence:
- narrow English builder validation:
  - `reading-companion-backend/state/dataset_build/build_runs/scratch_validation_en_qualityfix_20260330/build_summary.json`
  - result: `4` English candidate cases and `4` reserves from `education_of_henry_adams_public_en`
- narrow English bounded full smoke after the fix:
  - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
  - result: `keep = 2`, `revise = 2`, `drop = 0`
  - this replaced the earlier narrow-English result of `drop = 2`, `revise = 2`, `keep = 0`
- broader English bounded full smoke:
  - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
  - result: `keep = 4`, `revise = 4`, `drop = 0`
- bilingual scratch sequence:
  - `closed_loop_full_smoke_bilingual_qualityfix_20260330`
    - English `revise = 4`
    - Chinese `drop = 1`
    - diagnosis: Chinese still selected publication metadata instead of literary prose
  - `closed_loop_full_smoke_bilingual_paratextfix_20260330`
    - English `keep = 2`, `revise = 2`
    - Chinese `revise = 1`
    - diagnosis: front-matter selection was fixed, but the chosen Chinese excerpt still carried residual edge noise
  - `closed_loop_full_smoke_bilingual_selectionfix_20260330`
    - English `revise = 4`
    - Chinese `keep = 1`
    - diagnosis:
      - the Chinese lane improved again because `tension_reversal` displaced the weaker early filler case
      - the English source rows stayed identical to the previous bilingual rerun, but the regenerated audit inputs changed on all `4` English cases and the final adjudication moved with them
  - `closed_loop_full_smoke_bilingual_broader_selectionfix_20260330`
    - English `keep = 6`, `revise = 2`
    - Chinese `keep = 1`, `revise = 3`, `drop = 1`
    - diagnosis:
      - English case quality improved materially on the broader sample
      - the shared English cases still showed `source_input_drift = 0` and `audit_input_drift = 3`
      - Chinese still carried one weak dropped scene-description case plus a revise-heavy tail
  - `closed_loop_full_smoke_zh_cuegate_20260330`
    - Chinese `keep = 1`, `revise = 1`, `drop = 0`
    - diagnosis:
      - the weak `chenlun` reconsolidation scene-description cases disappeared from the candidate set
      - the surviving `chenlun_public_zh__4__callback_bridge__seed_v1` is structurally real but still needs a longer lookback bridge target in the excerpt window
  - `scratch_validation_zh_cueguard_20260330`
    - Chinese builder-only validation over `beiying_public_zh` + `chenlun_public_zh`
    - result: `2` active candidate cases and `4` reserves instead of the earlier `5` active Chinese cases on the same two-book slice
    - diagnosis:
      - `beiying_public_zh__2__tension_reversal__seed_v1` stayed strong
      - the weak `chenlun` scene-description / no-cue reconsolidation candidates disappeared from the active case set
      - the active `chenlun` case shifted onto `chenlun_public_zh__4__callback_bridge__seed_v1`
  - `closed_loop_zh_cueguard_20260330`
    - Chinese `keep = 1`, `revise = 1`, `drop = 0`
    - diagnosis:
      - the cue-guard patch held through the full scratch packet audit/adjudication/import loop
      - the active Chinese packet stayed on `背影` plus the stronger `chenlun_public_zh__4__callback_bridge__seed_v1` case instead of the earlier weak scene-setting / reconsolidation tail
  - `closed_loop_full_smoke_en_broader_auditcoherencefix_20260330`
    - English `keep = 3`, `revise = 5`, `drop = 0`
    - interpretation:
      - this run is useful as the first post-fix packet, but comparing it directly to the pre-fix broader bilingual packet is not a clean reproducibility verdict because the audit contract changed
      - the reproducibility question now needs a same-config repeat pair, not only a pre-fix versus post-fix comparison
  - `closed_loop_full_smoke_en_broader_auditcoherencefix_repeat_20260330`
    - English `keep = 1`, `revise = 7`, `drop = 0`
    - diagnosis:
      - the same-config repeat still held `source_input_drift = 0` while changing all `8` audit rows and `2` final actions
      - this confirms the score-direction bug was only one part of the audit instability
  - `closed_loop_full_smoke_bilingual_broader_auditcoherencefix_20260330`
    - English `keep = 4`, `revise = 4`
    - Chinese `keep = 1`, `revise = 1`, `drop = 0`
    - diagnosis:
      - the Chinese tail got materially cleaner after the cue-guard repair
      - the shared English cases still held `source_input_drift = 0` while all `8` audit rows changed again, so the remaining blocker is audit/adjudication reproducibility rather than source-case construction alone
- adjudication reproducibility tooling is now landed:
  - `reading-companion-backend/eval/attentional_v2/auto_review_packet.py`
  - `reading-companion-backend/eval/attentional_v2/compare_packet_adjudication_runs.py`
  - the compare output on the real English bilingual pair now shows:
    - `source_input_drift = 0`
    - `audit_input_drift = 4`
    - `action_drift = 2`
    - `confidence_drift = 2`
    - `problem_type_drift = 3`
  - follow-up hardening is now landed in code:
    - packet adjudication consumes a compact structured audit summary instead of free-text audit notes / challenge prose
    - placeholder audit rows are rejected before downstream adjudication
    - callback-bridge construction now requires a resolved antecedent and carries explicit `prior_context_sentence_ids` / `prior_context_text`
    - the audit context builder now prefers those builder-supplied prior-context ids over the older generic `start-3` lookback heuristic
    - the closed-loop variability guard now compares adjacent same-source adjudication runs even when the regenerated audit changed the packet fingerprint
  - fresh live audit-pair follow-up on current code:
    - `closed_loop_full_smoke_en_broader_auditpair_20260331`
      - English `keep = 5`, `revise = 3`, `drop = 0`
    - `closed_loop_full_smoke_bilingual_broader_auditpair_20260331`
      - English `keep = 3`, `revise = 5`, `drop = 0`
      - Chinese `keep = 1`, `revise = 1`, `drop = 0`
    - persisted compare artifact:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditpair_20260331/case_audit_compare_against_bilingual.json`
    - compare result on the shared English case-audit runs:
      - `same_run_audit_prompt_input_fingerprint = true`
      - `source_input_drift = 0`
      - `audit_input_drift = 0`
      - `primary_decision_drift = 2`
      - `primary_confidence_drift = 2`
      - `primary_problem_type_drift = 5`
      - `primary_score_drift = 8`
      - `adversarial_risk_drift = 2`
    - diagnosis:
      - the remaining live English instability is now narrowed to same-input audit-stage output variance rather than builder/input drift
      - the next narrow hardening move belongs in audit-stage reproducibility, not in source-row reconstruction or case/context assembly
  - first audit-stage hardening patch now landed in code:
    - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
      - `AUDIT_PROMPT_CONTRACT_VERSION` is now `case_design_audit_v2`
      - the primary audit prompt now asks for `strong|adequate|weak` axis bands instead of raw `1-5` scoring
      - primary normalization maps those bands back into canonical numeric scores for downstream compatibility
    - `reading-companion-backend/eval/attentional_v2/auto_review_packet.py`
      - compact adjudication inputs now prefer explicit normalized band fields when they are present
    - completed validation:
      - `bgjob_closed_loop_en_broader_auditcontractv2_20260331`
      - `bgjob_closed_loop_bilingual_broader_auditcontractv2_20260331`
      - same-input English audit drift remained builder-stable but not audit-stable:
        - `audit_input_drift = 0`
        - `primary_decision_drift = 5`
        - `primary_problem_type_drift = 6`
        - `primary_score_drift = 7`
      - the stricter all-strong keep gate made the primary audit more brittle to single-axis `4 -> 3` wobble instead of narrowing the blocker
  - second audit-stage hardening patch now landed in code:
    - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
      - `AUDIT_PROMPT_CONTRACT_VERSION` is now `case_design_audit_v3`
      - `keep` now means no weak axis and at most one adequate axis
      - normalized primary decisions and minimal problem types are now derived deterministically from the normalized axis scores
    - completed validation:
      - `bgjob_closed_loop_en_broader_auditcontractv3_20260331`
      - `bgjob_closed_loop_bilingual_broader_auditcontractv3_20260331`
      - same-input English audit drift improved relative to `auditcontractv2` but remained too high for unattended widening:
        - `audit_input_drift = 0`
        - `primary_decision_drift = 4`
        - `primary_problem_type_drift = 5`
        - `primary_score_drift = 5`
      - the softer keep gate helped, but it did not fully stabilize the audit
  - third audit-stage hardening patch now landed in code:
    - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
      - primary audit now runs `3` zero-temperature replicas per case
      - the final normalized primary review is selected by deterministic consensus
      - this keeps the repair inside audit-stage reproducibility instead of changing builder inputs again
    - validation:
      - `bgjob_closed_loop_en_broader_auditconsensusv3_20260331`
      - `bgjob_closed_loop_bilingual_broader_auditconsensusv3_20260331`
      - both reruns completed cleanly and now show that consensus narrows same-input audit-stage variance more effectively than the softer keep gate alone:
        - `audit_input_drift = 0`
        - `primary_decision_drift = 2`
        - `primary_problem_type_drift = 2`
        - `primary_score_drift = 4`
      - this is the best current audit reproducibility candidate
  - bounded quota-recovery follow-up now landed locally:
    - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
      - quota-only failed cases now receive up to `2` extra whole-case recovery passes before the audit leaves them failed
      - per-run audit summaries now expose quota-recovery attempted/succeeded/remaining counts so operational cooldown pressure is visible at the controller layer
    - focused validation:
      - `reading-companion-backend/tests/test_case_design_audit.py`
      - `reading-companion-backend/tests/test_case_design_audit_reproducibility.py`
      - `reading-companion-backend/tests/test_closed_loop_benchmark_curation.py`
      - `36 passed`
  - one remaining English outlier still exposed a builder-side text-sanitation defect even after the audit-input fingerprints matched:
    - `education_of_henry_adams_public_en__16__anchored_reaction_selectivity__seed_v1`
    - the emitted excerpt and selection-reason text still carried invisible Unicode whitespace from the source sentence
  - a bounded builder-side follow-up is now landed:
    - `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
      - rendered excerpt text now strips invisible format characters and normalizes non-breaking whitespace
      - builder-facing anchor lines and selection-reason text now reuse the cleaned line
    - deterministic validation:
      - `reading-companion-backend/state/dataset_build/build_runs/scratch_validation_en_whitespacefix_20260331/build_summary.json`
      - the Henry Adams anchored-reaction row now emits clean `excerpt_text` and `selection_reason`
    - narrow closed-loop confirmation:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_henry_whitespacefix_20260331/closed_loop_benchmark_curation_summary.json`
      - English `keep = 3`, `revise = 1`, `drop = 0`
      - the previously corrupted `education_of_henry_adams_public_en__16__anchored_reaction_selectivity__seed_v1` case now exits as `keep` instead of failing on text integrity
    - broader English confirmation:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_whitespacefix_20260331/closed_loop_benchmark_curation_summary.json`
      - English `keep = 7`, `revise = 1`, `drop = 0`
      - the only remaining English holdout in that two-source slice is a bounded callback-breadth / mixed-focus revise, not a builder text-corruption defect
  - wave-closeout status:
    - `auditconsensusv3` remains the best current audit reproducibility candidate versus `auditpair`, `auditcontractv2`, and `auditcontractv3`
    - the last persisted queue checkpoint is still `generated_at = 2026-03-30T20:05:14.323982Z` with `active_packet_count = 0`
    - the broader bilingual post-fix validation is now completed:
      - `bgjob_closed_loop_bilingual_broader_whitespacefix_20260331`
      - English `keep = 6`, `revise = 1`, `drop = 1`
      - Chinese `keep = 1`, `revise = 1`, `drop = 0`
      - the remaining regressions are concentrated in `callback_bridge` cases rather than across the whole builder path
    - a bounded callback-bridge repair is now landed:
      - callback-bridge `judge_focus` now asks for a traceable earlier bridge with clear attribution
      - nearby resolved antecedents are now inlined into the main excerpt instead of being left only in `prior_context_text`
      - focused validation passed:
        - `tests/test_question_aligned_case_construction.py`
        - `tests/test_case_design_audit.py`
        - `tests/test_case_design_audit_reproducibility.py`
        - `tests/test_packet_adjudication_reproducibility.py`
        - `tests/test_closed_loop_benchmark_curation.py`
        - `71 passed`
    - the callback-bridge follow-up validation is now completed:
      - `bgjob_closed_loop_bilingual_broader_callbackbridgefix_20260331`
      - English `keep = 6`, `revise = 2`, `drop = 0`
      - Chinese `keep = 1`, `revise = 1`, `drop = 0`
      - case-level interpretation:
        - `education_of_henry_adams_public_en__29__callback_bridge__seed_v1` improved from `drop` to `revise`
        - `on_liberty_public_en__5__callback_bridge__seed_v1` stayed `revise`
        - `chenlun_public_zh__4__callback_bridge__seed_v1` stayed `revise`
      - diagnosis:
        - the bounded callback repair cleared replacement-level failure but did not yet make the surviving callback excerpts fully self-contained
        - the remaining work is still excerpt shaping and antecedent carry-forward, not a global rebuild of the case-construction stack
    - the callback antecedent-quality follow-up is now completed:
      - `bgjob_closed_loop_bilingual_broader_callbackcontentfix_20260331`
      - English `keep = 4`, `revise = 4`, `drop = 0`
      - Chinese `keep = 1`, `revise = 0`, `drop = 0`
      - diagnosis:
        - this pass usefully removed the weak Chinese callback baggage
        - it also degraded the English lane relative to `callbackbridgefix`, so it is useful negative evidence rather than the final callback-shaping answer
    - a narrower inferential callback backlink patch is now landed locally:
      - English callback markers now recognize inferential backlink phrases such as `from this` and `from that`
      - `_english_inferential_callback_score(...)` helps real inferential callbacks resolve against immediately prior evidence even when lexical overlap is weak
      - English generic overlap is tightened further by adding `home` to `CALLBACK_GENERIC_OVERLAP_TERMS_EN`
      - builder-only scratch validation:
        - `reading-companion-backend/state/dataset_build/build_runs/scratch_validation_callback_qualitycheck_20260331/build_summary.json`
        - `on_liberty_public_en__5__callback_bridge__opp_2` is restored in the English opportunity map
        - the weak Henry `return home` callback no longer survives as the active callback export
        - the weak Chinese `chenlun_public_zh__4__callback_bridge__seed_v1` row remains absent from the active candidate set
    - one follow-up validation run is currently active:
      - `bgjob_closed_loop_bilingual_broader_callbackinferencefix_20260331`
      - completed result:
        - English `keep = 5`, `revise = 3`, `drop = 0`
        - Chinese `keep = 1`, `revise = 0`, `drop = 0`
      - case-level interpretation:
        - `education_of_henry_adams_public_en__29__callback_bridge__seed_v1` remains `revise`
        - `on_liberty_public_en__10__callback_bridge__seed_v1` is now a clean `keep`
        - `on_liberty_public_en__4__callback_bridge__seed_v1` remains `revise`
        - no weak Chinese callback row returns to the active packet
    - one narrower callback-focus follow-up is now landed locally:
      - callback cases now carry the resolved earlier bridge target directly into `selection_reason` and `judge_focus`
      - focused validation:
        - `tests/test_question_aligned_case_construction.py`
        - `tests/test_case_design_audit.py`
        - `tests/test_case_design_audit_reproducibility.py`
        - `tests/test_packet_adjudication_reproducibility.py`
        - `tests/test_closed_loop_benchmark_curation.py`
        - `72 passed`
    - the current live narrow reproducibility lane is the callback slice:
      - original job: `bgjob_callbackslice_auditv4_packet_20260331`
      - retry job: `bgjob_callbackslice_auditv4_packet_retry_quota_20260331`
    - the first callbackslice run finished with Henry completed and `on_liberty_public_en__10__callback_bridge__seed_v1` failed under pre-patch quota exhaustion
    - the retry under the new quota-recovery path completed with `keep = 1`, `revise = 1`
    - `education_of_henry_adams_public_en__29__callback_bridge__seed_v1` now clears as `keep` / `reviewed_active`
    - `on_liberty_public_en__10__callback_bridge__seed_v1` remains the one bounded `revise`, so the live callback blocker shifts to argumentative focus clarity rather than quota instability or Henry-specific breadth
    - one bounded argumentative callback drafting follow-up is now landed locally:
      - argumentative / reference-heavy callback cases now draft explicit anchor-to-earlier-target bridge language with visible author/work attribution
      - focused validation:
        - `tests/test_question_aligned_case_construction.py`
        - `tests/test_case_design_audit.py`
        - `tests/test_case_design_audit_reproducibility.py`
        - `tests/test_closed_loop_benchmark_curation.py`
        - `70 passed`
    - one narrow one-source follow-up is now completed:
      - run: `closed_loop_on_liberty_callbackpromptfix_20260331`
      - result: English `keep = 3`, `revise = 1`, `drop = 0`
      - `on_liberty_public_en__4__callback_bridge__seed_v1` now clears as `keep`
      - `on_liberty_public_en__10__callback_bridge__reserve_v1` stays in reserve with the sharper callback drafting
      - the remaining revise on this narrow slice is `on_liberty_public_en__5__anchored_reaction_selectivity__seed_v1`, not another callback row

Current interpretation:
- the excerpt-boundary / fragment-quality bug was real and materially important
- English question-aligned construction improved materially
- Chinese construction also improved materially and can now produce a real prose `keep`
- the next blocker for wider automation is no longer intake plumbing; it is now the combination of:
  - same-input audit/adjudication reproducibility under the live audit variants
  - one more callback-bridge-specific excerpt-shaping pass to handle the remaining bilingual outliers on the cleaned English path and the still-narrow Chinese callback slice
- the current direct measurement lanes are now:
  - `auditconsensusv3` as the best current same-input audit-stability lane
  - the completed Henry Adams, broader-English, broader-bilingual whitespace-fix, and broader-bilingual callbackbridgefix follow-ups as proof that the remaining issue has narrowed from text corruption to one bounded callback excerpt-shaping family
  - the surviving `revise` cases as the direct targets for the next narrow builder refinement

## What We Keep
Preserve these current strengths:
- managed source intake from `state/library_inbox/`
- canonical source catalog under `state/dataset_build/source_catalog.json`
- canonical parsing and screening in `reading-companion-backend/eval/attentional_v2/corpus_builder.py`
- tracked/local dataset row schema fields such as:
  - `question_ids`
  - `phenomena`
  - `selection_reason`
  - `judge_focus`
- review-state fields such as:
  - `benchmark_status`
  - `review_status`
  - `review_history`
  - `review_latest`
- mechanical packet review lifecycle in:
  - `generate_revision_replacement_packet.py`
  - `run_case_design_audit.py`
  - `auto_review_packet.py`
  - `import_dataset_review_packet.py`
  - `run_dataset_review_pipeline.py`

## What Must Change
Replace or heavily refactor the current excerpt-creation layer:
- fixed-window excerpt candidate generation
- bucket preference logic driven mainly by role and position
- fallback filling that does not yet reason from explicit target-case semantics

The new construction layer should create intermediate semantic artifacts before it creates final benchmark rows.

## Five Construction Layers
### 1. Source Screening
This layer stays mostly as it is now.

Responsibilities:
- canonical parse
- language control
- structural normalization
- chapter viability
- source-level tags and metadata
- chapter candidate screening

Outputs:
- screened source records
- candidate chapter list

### 2. Opportunity Mapping
This is the new missing middle layer.

An `opportunity card` is not yet a benchmark case.
It is a structured candidate reading pressure discovered inside a chapter.

Responsibilities:
- scan one chapter or meaning-unit sequence for target-relevant signals
- identify the local anchor lines and required prior context
- describe why this pressure may be benchmark-worthy
- estimate whether the opportunity is judgeable and discriminative

Outputs:
- opportunity cards for one source/chapter pair

### 3. Target Profiles
Each evaluation target should be a first-class profile, not an inferred bucket.

Each `target_profile` should define:
- `target_profile_id`
- supported `question_ids`
- expected `phenomena`
- what evidence shape makes the case strong
- what ambiguity patterns make the case weak
- required prior-context rules
- preferred excerpt-length and context policy
- case-shaping guidance for `selection_reason`
- case-shaping guidance for `judge_focus`
- replacement strategy if review later says `revise` or `drop`

Initial excerpt-focused profiles:
- `distinction_definition`
- `tension_reversal`
- `callback_bridge`
- `anchored_reaction_selectivity`
- `reconsolidation_later_reinterpretation`

This profile layer should stay extensible so future evaluation targets can be added without redesigning the builder.

### 4. Case Assembly
This layer turns opportunity cards into actual dataset rows.

Responsibilities:
- choose final excerpt boundaries
- include enough context for fair judging
- dedupe exact same-source same-profile excerpt windows before they become active or reserve rows
- assign `question_ids`
- assign `phenomena`
- write concrete `selection_reason`
- write concrete `judge_focus`
- set reserve candidates and replacement lineage

This is where a benchmark case becomes an evaluation asset instead of a raw semantic hint.

### 5. Dataset Curation And Adequacy
This layer selects from assembled cases into benchmark packages.

Responsibilities:
- enforce target-profile quotas
- enforce English/Chinese balance
- enforce source diversity
- enforce holdout/reserve structure
- calculate adequacy for the current dataset family
- surface where replacement or additional mining is still needed

## Opportunity Card Schema
The opportunity card should be durable enough to drive review and later regeneration, but still remain a local operational artifact rather than a tracked benchmark truth layer.

Recommended fields:
- `opportunity_id`
- `source_id`
- `chapter_id`
- `language_track`
- `target_profile_ids`
- `anchor_sentence_ids`
- `support_sentence_ids`
- `prior_context_sentence_ids`
- `prior_context_excerpt_text`
- `anchor_excerpt_text`
- `context_excerpt_text`
- `phenomenon_evidence`
- `judgeability_score`
- `discriminative_power_score`
- `ambiguity_risk`
- `construction_priority`
- `selection_reason_draft`
- `judge_focus_draft`
- `rejection_reasons`
- `reserve_rank`
- `derived_from_review_feedback`

Recommended storage territory:
- `reading-companion-backend/state/dataset_build/opportunity_maps/`

These artifacts are:
- reproducible from current sources plus code
- useful for debugging and regeneration
- not the final benchmark truth layer

`callback_bridge` opportunities have one extra rule:
- a local backward marker is not enough on its own
- the builder should resolve one bounded earlier antecedent and either:
  - expand the main excerpt when that antecedent is still close
  - or store explicit prior-context ids/text when the antecedent is farther back
- if no real antecedent can be resolved, the opportunity should be rejected rather than carried as a cue-only bridge

## Target Profile Contract
Each target profile should have two parts.

### Semantic definition
- what kind of reading pressure it is
- what makes it genuinely present
- what makes it absent or too weak

### Construction policy
- how much prior context is usually needed
- whether the case should prefer a tight local span or broader setup
- whether later reinterpretation is required
- whether multiple reading moves might still be fair
- how strict the ambiguity filter should be

That separation matters because:
- one profile may be semantically clear
- but still need careful packaging to become a fair benchmark case

## Detection Methods
The system should not rely on one mining trick.
Use several methods together.

### Phenomenon-first detection
- ask directly whether a passage contains a target phenomenon
- this is the primary method

### Contrastive-difference detection
- prefer cases likely to reveal a meaningful mechanism difference
- avoid cases that every reasonable reader would handle identically

### Review-feedback mining
- use `needs_revision`, `needs_replacement`, review rationales, and adjudication outcomes to guide the next search
- replacements should learn from why the previous case failed

### Reserve-family mining
- mine nearby or sibling opportunities from the same source and chapter family
- keep replacement supply close to the current case rather than restarting the whole search

### Trajectory-aware chapter selection
- for chapter corpora and later fixture families, prefer chapters that support accumulation, callbacks, and later reinterpretation
- do not optimize only for chapter length or position

## Division Of Labor: Deterministic Rules vs LLMs
### Deterministic rules should own
- source discovery
- file and manifest handling
- canonical parsing
- language and storage-policy routing
- structural boundary extraction
- dedupe and quota enforcement
- dataset manifest generation
- packet orchestration
- final deterministic adequacy summaries

### LLMs should own
- semantic opportunity detection
- ambiguity checking
- discriminative-power estimation
- drafting `selection_reason`
- drafting `judge_focus`
- adversarial case-quality critique
- replacement suggestions when a case is dropped

This split gives us stronger semantics without sacrificing reproducibility where it matters.

## Quality Gates For One Case
A constructed case should pass all of these gates before it is promoted into a benchmark package:
- `text_grounded`
  - the phenomenon is clearly answerable to the source text
- `judgeable`
  - a reviewer can explain why the case exists and what a strong/weak reading would look like
- `nontrivial`
  - the case is not too easy or too generic
- `discriminative`
  - there is plausible room for mechanisms to differ meaningfully
- `bounded`
  - the excerpt is not so broad that judgment becomes diffuse
- `context_sufficient`
  - enough prior context is included for fair evaluation
- `reviewable`
  - if the case later fails review, the system can revise or replace it without guessing blindly

## Adequacy For A Dataset Family
Adequacy should not be just row count.

The adequacy report for one dataset family should include:
- total case counts by language
- total case counts by target profile
- reviewed-active counts by language and profile
- open weak-case counts by language and profile
- reserve depth by profile
- source diversity
- chapter diversity
- unresolved ambiguity concentration

Recommended output territory:
- `reading-companion-backend/state/dataset_build/adequacy_reports/`

## Relationship To Review
Question-Aligned Case Construction should feed the existing review machinery, not replace it.

The intended loop is:
- construction creates cases and reserves
- packet review audits case design
- adjudication/import updates benchmark truth
- review outcomes guide the next opportunity search and case replacement

This means review is not a sidecar.
It is part of the construction feedback system.

## Relationship To The Unattended Loop
We should define the unattended-loop contract now, but not fully design or implement the full controller yet.

### What should be designed now
- the artifact contract between construction and orchestration
- the target-profile system
- the opportunity-card system
- adequacy report outputs
- replacement lineage and reserve handling
- the stop-condition inputs the future loop will read

### What should wait until after the construction layer lands
- the full long-running unattended scheduler
- retry and resume policy across many build/review iterations
- automatic regeneration budgeting
- parallel fanout strategy across long-running mining/review waves
- loop-level recovery behavior after partial failures

### Why this split is better
- if we automate too early, we will automate today's weaker heuristics
- the loop should orchestrate stable construction artifacts, not define them by accident
- once opportunity cards, target profiles, and adequacy reports are real code artifacts, the unattended loop becomes much easier to specify correctly

So the right answer is:
- design the loop boundary now
- implement the full unattended loop after the construction layer is stable enough to be worth automating

## Initial Implementation Sequence
### Phase 2A
- define target-profile configs
- define opportunity-card schema
- create one local operational artifact layout under `state/dataset_build/`

### Phase 2B
- replace fixed-window excerpt mining with opportunity mapping
- generate candidate cases for the five current excerpt target profiles

### Phase 2C
- add ambiguity filtering, reserve-family generation, and adequacy reporting
- connect review outcomes back into replacement ranking

### Phase 2D
- extend the same method to:
  - chapter corpora
  - runtime / resume fixtures
  - compatibility / durable-trace fixtures

### Phase 3
- build the unattended controller around the stabilized Phase 2 artifacts
- current first controller landing:
  - `reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py`
  - root surface:
    - `make closed-loop-benchmark-curation`
  - current scope:
    - construct scratch datasets
    - export initial `--only-unreviewed` packets
    - audit, adjudicate, import, archive
    - optionally run one bounded revision/replacement repair wave
    - refresh the queue summary
    - emit one final stop-and-summarize report
  - current boundary:
    - this is a first bounded controller, not the final unattended multi-iteration scheduler

## Immediate Next Code Targets
- `reading-companion-backend/eval/attentional_v2/corpus_builder.py`
  - carve out the current excerpt-generation logic behind a cleaner interface
- new question-aligned construction helpers under:
  - `reading-companion-backend/eval/attentional_v2/`
- current local/private supplement build path:
  - `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py`
  - keep it using the managed source catalog while the new construction layer is added
  - keep validating the scratch-safe build namespace before promoting that path into the unquestioned default for real source runs
- first closed-loop controller path:
  - `reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py`
  - validate it on real managed inputs, then widen its stop-condition and regeneration policy only after the scratch build outputs look trustworthy

## Non-Goals For This Phase
- do not reopen benchmark promotion automatically
- do not freeze reviewed slices automatically
- do not redesign the packet-review machinery
- do not redesign the whole LLM gateway or provider-routing layer
- do not let Phase 3 orchestration pressure collapse the semantic design quality of Phase 2
