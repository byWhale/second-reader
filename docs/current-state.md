# Current State

Purpose: capture the canonical repo-local view of current project status for agent switching and human recovery.
Use when: onboarding a new coding agent, resuming work without chat history, or checking which initiative is current now.
Not for: long-form rationale, full historical detail, or session-only scratch notes.
Update when: the current objective, active tasks, blockers, active jobs, open decisions, risks, or recommended reading path change.

This file is authoritative for durable current status. Do not keep unique active-state information only in `docs/agent-handoff.md`.

Last verified: `2026-03-31T11:46:43Z`

## Current Objective
- Keep Phase 9 of the new reading mechanism project recoverable and decision-ready:
  - inspect the completed English two-case evidence rerun without converting it into an automatic mechanism or promotion decision
  - work from the recovered private-library local-only datasets rather than the stale seed-reset narrative
  - preserve the remaining benchmark-hardening backlog and human-owned gate decisions in repo-local state
- In parallel, keep the dataset-platform route moving from landing to evidence-driven refinement:
  - use the recovered managed source catalog on this checkout instead of treating missing-catalog recovery as the active blocker
  - use the real scratch builder/controller evidence to improve case quality and bilingual reproducibility before widening automation further

## Current Strategy
- The project is no longer trying to perfect the dataset builder before resuming comparison work.
- Dataset quality work, builder work, and automation work remain necessary, but they are support systems for cross-mechanism evaluation rather than replacement goals.
- Current builder/controller work is in bounded-hardening mode only.
  - the active builder-side reasons to continue are:
    - callback-bridge excerpt shaping
    - audit/adjudication reproducibility on same-input frozen cases
- After each bounded repair wave, freeze the affected slice and return to mechanism comparison cadence before opening another builder wave.
- Unattended automation should not widen further until it demonstrably shortens the loop back to trusted frozen-slice comparison.
- Durable-trace / re-entry and runtime-viability lanes remain decisive pending evaluation work and must stay visible instead of disappearing behind dataset-platform activity.

## Now
- Treat `attentional_v2` as experimental and `iterator_v1` as the current default mechanism.
- The English chapter-core retry-2 closeout remains the last broader multi-case comparison baseline, and the completed backup-tier substantive rerun is now the latest focused two-case mechanism-evidence checkpoint:
  - run:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round2_microselectivity_retry2_20260328/`
  - round-1 vs retry-2 shift:
    - English `local_impact` improved from `0/4` win-or-tie to `2/4` win-or-tie
    - English `system_regression` improved from `2/4` wins to `3/4` wins
  - verified interpretation:
    - the landed micro-selectivity repair helped most on argumentative / expository English chapters
    - the remaining local gap is now concentrated on narrative / reference-heavy English cases rather than on the whole pack
  - live queue record:
    - `docs/implementation/new-reading-mechanism/mechanism-pattern-ledger.md`
    - `docs/implementation/new-reading-mechanism/execution-tracker.md`
  - focused two-case substantive rerun:
    - job id:
      - `bgjob_en_chapter_core_rerun_round3_caseiso_judged_substantive_backup_20260331`
    - summary:
      - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_caseiso_judged_substantive_backup_20260331/summary/aggregate.json`
    - result:
      - `local_impact`: split `1-1`, average scores `4.1` vs `3.7` in favor of `attentional_v2`
      - `system_regression`: `iterator_v1 = 1`, `tie = 1`, average scores `2.7` vs `3.2`
    - interpretation:
      - the backup-tier rerun removed the earlier quota-stop and preserved the real mixed mechanism picture instead of changing project direction
      - `up_from_slavery_public_en__10` improved on local passage reading but still lost on chapter-scale accumulation
      - `walden_205_en__10` held as a chapter-spanning strength without converting into a clean overall system-regression win
- The bounded narrative/reference-heavy Phase 4 repair is landed in code for:
  - `up_from_slavery_public_en__10`
  - `walden_205_en__10`
  - landed mechanism change:
    - deterministic local cue packets now include `actor_intention`, `social_pressure`, and `causal_stakes`
    - short spans may synthesize one bounded local candidate from those cues when the local gate is genuinely open
    - zoom/closure/emission prompts now prefer one grounded why-now observation or question over retrospective summary in those moments
  - local verification:
    - `reading-companion-backend/tests/test_attentional_v2_nodes.py`
    - `13` node tests passed on `2026-03-28`
- The temporary seed-reset / missing-review-state problem is no longer current:
  - English cleanup recovery completed successfully:
    - archive:
      - `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_en_recovery_20260329/`
    - summary:
      - `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_en_recovery_20260329/dataset_review_pipeline_summary.json`
    - live English local-only dataset counts:
      - `7` `reviewed_active`
      - `3` `needs_revision`
      - `6` `needs_replacement`
      - `154` `unset`
    - live open English cases:
      - `fooled_by_randomness_private_en__14__seed_2`
      - `evicted_private_en__10__seed_1`
      - `evicted_private_en__17__seed_2`
      - `poor_charlies_almanack_private_en__10__seed_1`
      - `poor_charlies_almanack_private_en__10__seed_2`
      - `steve_jobs_private_en__24__seed_1`
      - `steve_jobs_private_en__24__seed_2`
      - `steve_jobs_private_en__17__seed_1`
      - `supremacy_private_en__13__seed_1`
  - Chinese cleanup recovery completed successfully:
    - archive:
      - `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_zh_recovery_20260329/`
    - summary:
      - `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_zh_recovery_20260329/dataset_review_pipeline_summary.json`
    - live Chinese local-only dataset counts:
      - `13` `reviewed_active`
      - `1` `needs_revision`
      - `2` `needs_replacement`
      - `40` `unset`
    - live open Chinese cases:
      - `kangxi_hongpiao_private_zh__12__seed_2`
      - `kangxi_hongpiao_private_zh__27__seed_1`
      - `zouchu_weiyi_zhenliguan_private_zh__8__seed_1`
  - both recovery summaries explicitly recorded `decision_bearing_followup_launched: false`
- The audit reproducibility wave is now fully complete in durable repo evidence:
  - the canonical wave-end checkpoint still lives in `reading-companion-backend/eval/review_packets/review_queue_summary.json`
  - `generated_at = 2026-03-30T20:05:14.323982Z`
  - `active_packet_count = 0`
  - this stable queue checkpoint reflects the completed `auditpair`, `auditcontractv2`, `auditcontractv3`, `auditconsensusv3`, the narrow Henry Adams whitespace-fix follow-up, and the broader English plus broader bilingual whitespace-fix runs, all of which refreshed with `changed = false`
  - this remains packet-local work only:
    - no promotion, reviewed-slice freezing, runtime-viability, or default-cutover work was auto-launched
- The post-fix broader English validation is now completed:
  - job id:
    - `bgjob_closed_loop_en_broader_whitespacefix_20260331`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_whitespacefix_20260331/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 7`, `revise = 1`, `drop = 0`
    - post-import English benchmark counts: `reviewed_active = 7`, `needs_revision = 1`
  - diagnosis:
    - the Henry Adams anchored-reaction outlier now stays clean and benchmark-ready end to end
    - the only remaining English holdout in this two-source slice is `education_of_henry_adams_public_en__29__callback_bridge__seed_v1`, which is still a bounded callback breadth / mixed-focus issue rather than a text-integrity failure
- The broader bilingual post-fix validation is now completed:
  - job id:
    - `bgjob_closed_loop_bilingual_broader_whitespacefix_20260331`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_whitespacefix_20260331/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 6`, `revise = 1`, `drop = 1`
    - Chinese `keep = 1`, `revise = 1`, `drop = 0`
  - diagnosis:
    - Chinese held steady at the current narrow baseline rather than regressing
    - the remaining English instability is now concentrated in `callback_bridge` cases rather than in the whole cleaned builder path:
      - `education_of_henry_adams_public_en__29__callback_bridge__seed_v1` degraded from `revise` to `drop`
      - `on_liberty_public_en__5__callback_bridge__seed_v1` degraded from `keep` to `revise`
    - the next bounded repair belongs in callback-bridge shaping rather than in another global text-sanitization or audit-plumbing pass
- A bounded callback-bridge repair is now landed in code:
  - code:
    - `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
    - `reading-companion-backend/tests/test_question_aligned_case_construction.py`
  - bounded changes:
    - callback-bridge `judge_focus` now asks for a traceable earlier bridge with clear attribution instead of the looser "honestly and for the right reason" wording
    - when a resolved callback antecedent falls only a small gap before the excerpt window, the builder now inlines that antecedent into the main excerpt instead of leaving it only in `prior_context_text`
  - local validation:
    - `reading-companion-backend/tests/test_question_aligned_case_construction.py`
    - `reading-companion-backend/tests/test_case_design_audit.py`
    - `reading-companion-backend/tests/test_case_design_audit_reproducibility.py`
    - `reading-companion-backend/tests/test_packet_adjudication_reproducibility.py`
    - `reading-companion-backend/tests/test_closed_loop_benchmark_curation.py`
    - focused result: `71 passed`
- The callback-bridge follow-up validation is now completed:
  - job id:
    - `bgjob_closed_loop_bilingual_broader_callbackbridgefix_20260331`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_callbackbridgefix_20260331/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 6`, `revise = 2`, `drop = 0`
    - Chinese `keep = 1`, `revise = 1`, `drop = 0`
    - post-import English benchmark counts: `reviewed_active = 6`, `needs_revision = 2`
    - post-import Chinese benchmark counts: `reviewed_active = 1`, `needs_revision = 1`
  - diagnosis:
    - the bounded callback repair cleared the last English `drop`, so the broader bilingual slice no longer has a replacement-level failure
    - `education_of_henry_adams_public_en__29__callback_bridge__seed_v1` improved from `drop` to `revise`, but it still reads as broad or mixed because the callback evidence is present yet not fully self-contained in the excerpt window
    - `on_liberty_public_en__5__callback_bridge__seed_v1` remains `revise` because the bridge is real but still too compressed to read as benchmark-ready on its own
    - `chenlun_public_zh__4__callback_bridge__seed_v1` remains `revise` because the backward-link target is still not explicit enough inside the excerpt itself
    - the next bounded move belongs in callback excerpt shaping and antecedent carry-forward, not in audit plumbing, queue orchestration, or another global sanitization pass
- The callback antecedent-quality follow-up is now completed:
  - job id:
    - `bgjob_closed_loop_bilingual_broader_callbackcontentfix_20260331`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_callbackcontentfix_20260331/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 4`, `revise = 4`, `drop = 0`
    - Chinese `keep = 1`, `revise = 0`, `drop = 0`
    - post-import English benchmark counts: `reviewed_active = 4`, `needs_revision = 4`
    - post-import Chinese benchmark counts: `reviewed_active = 1`
  - diagnosis:
    - this pass successfully removed the weak Chinese callback baggage
    - it also demoted the earlier weak `on_liberty_public_en__5__callback_bridge__seed_v1` callback export, but the overall English quality regressed from the stronger `callbackbridgefix` checkpoint
    - `callbackcontentfix` is therefore useful negative evidence, not the final callback-shaping answer
- A tighter inferential callback backlink follow-up is now landed in code:
  - code:
    - `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
    - `reading-companion-backend/tests/test_question_aligned_case_construction.py`
  - bounded changes:
    - English callback markers now treat inferential backlink phrases such as `from this` and `from that` as callback signals
    - `_english_inferential_callback_score(...)` now helps real inferential callbacks resolve against the immediately prior evidence even when lexical overlap is weak
    - English generic overlap is tightened further by adding `home` to `CALLBACK_GENERIC_OVERLAP_TERMS_EN`
  - builder-only validation:
    - `reading-companion-backend/state/dataset_build/build_runs/scratch_validation_callback_qualitycheck_20260331/build_summary.json`
    - `on_liberty_public_en__5__callback_bridge__opp_2` is restored in the opportunity map
    - the weak Henry `return home` callback no longer survives as the active callback candidate
    - the weak Chinese `chenlun_public_zh__4__callback_bridge__seed_v1` row remains absent from the active candidate set
- The callback inference follow-up is now completed:
  - job id:
    - `bgjob_closed_loop_bilingual_broader_callbackinferencefix_20260331`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_callbackinferencefix_20260331/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 5`, `revise = 3`, `drop = 0`
    - Chinese `keep = 1`, `revise = 0`, `drop = 0`
    - post-import English benchmark counts: `reviewed_active = 5`, `needs_revision = 3`
    - post-import Chinese benchmark counts: `reviewed_active = 1`
  - diagnosis:
    - this run recovered useful English quality from the weaker `callbackcontentfix` checkpoint while preserving the cleaner Chinese lane
    - `education_of_henry_adams_public_en__29__callback_bridge__seed_v1` remains `revise` because the callback target is real but still described too generically
    - `on_liberty_public_en__10__callback_bridge__seed_v1` is now a clean `keep`
    - `on_liberty_public_en__4__callback_bridge__seed_v1` remains `revise` because the callback target is present but the judge focus is still too broad or mixed
    - no weak Chinese callback row returned to the active packet
- A bounded callback target-specific focus patch is now landed locally:
  - code:
    - `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
    - `reading-companion-backend/tests/test_question_aligned_case_construction.py`
  - bounded changes:
    - callback cases now carry the resolved earlier bridge target directly into `selection_reason` and `judge_focus`
    - the callback prompt no longer uses one generic "specific earlier material" phrase for every callback case
  - local validation:
    - `reading-companion-backend/tests/test_question_aligned_case_construction.py`
    - `reading-companion-backend/tests/test_case_design_audit.py`
    - `reading-companion-backend/tests/test_case_design_audit_reproducibility.py`
    - `reading-companion-backend/tests/test_packet_adjudication_reproducibility.py`
    - `reading-companion-backend/tests/test_closed_loop_benchmark_curation.py`
    - focused result: `72 passed`
- The callback-focus follow-up is now completed:
  - job id:
    - `bgjob_closed_loop_bilingual_broader_callbackfocusfix_20260331`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_callbackfocusfix_20260331/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 7`, `revise = 1`, `drop = 0`
    - Chinese `keep = 1`, `revise = 0`, `drop = 0`
    - post-import English benchmark counts: `reviewed_active = 7`, `needs_revision = 1`
    - post-import Chinese benchmark counts: `reviewed_active = 1`
  - diagnosis:
    - this is the current strongest narrow callback-quality checkpoint on the shared four-source bilingual slice
    - explicit callback target naming improved the remaining callback lane without reopening weak Chinese rows
    - this stayed scratch-safe evidence only; no promotion, reviewed-slice freezing, runtime-viability, or default-cutover work was auto-launched
- A bounded tension-turn follow-up is now landed in code:
  - code:
    - `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
    - `reading-companion-backend/tests/test_question_aligned_case_construction.py`
  - bounded changes:
    - English `tension_reversal` windows now expand around argumentative `whether this...` openings when the local follow-through is clearly part of the same turn
    - leading `Whether this/that/...` openers now pull in the immediately preceding sentence as required context
    - `selection_reason` and `judge_focus` now name the specific tension under review instead of using only the generic profile wording
  - local validation:
    - `reading-companion-backend/tests/test_question_aligned_case_construction.py`
    - `reading-companion-backend/tests/test_case_design_audit.py`
    - `reading-companion-backend/tests/test_case_design_audit_reproducibility.py`
    - `reading-companion-backend/tests/test_packet_adjudication_reproducibility.py`
    - `reading-companion-backend/tests/test_closed_loop_benchmark_curation.py`
    - focused result: `78 passed`
- The direct English tension-window follow-up is now completed:
  - run id:
    - `closed_loop_full_smoke_en_broader_tensionwindowfix_20260331`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_tensionwindowfix_20260331/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 5`, `revise = 3`, `drop = 0`
  - diagnosis:
    - the intended `on_liberty_public_en__5__tension_reversal__seed_v1` case now clears as `keep`
    - the broader English packet still looked mixed because unchanged callback cases drifted at audit/adjudication, not because the tension-window repair damaged those builder rows
- The broader bilingual tension-focus follow-up is now completed:
  - job id:
    - `bgjob_closed_loop_bilingual_broader_tensionfocusfix_20260331`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_tensionfocusfix_20260331/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 6`, `drop = 1`, `unclear = 1`, `revise = 0`
    - Chinese `keep = 1`, `revise = 0`, `drop = 0`
  - diagnosis:
    - the intended `on_liberty_public_en__5__tension_reversal__seed_v1` win held in the broader bilingual slice
    - the mixed packet outcome was not a clean builder regression signal:
      - unchanged callback cases drifted during audit/adjudication even when the callback builder inputs themselves did not materially change
      - the next blocker is bounded audit/review reproducibility on those unchanged callback cases before broader unattended widening
- A bounded callback audit-reproducibility hardening wave is now landed in code:
  - code:
    - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
    - `reading-companion-backend/tests/test_case_design_audit.py`
    - `reading-companion-backend/tests/test_case_design_audit_reproducibility.py`
  - bounded changes:
    - the audit prompt contract is now `case_design_audit_v4`
    - callback audit prompts now carry `target_profile_id`, `selection_role`, and any carried `prior_context_text` instead of only the narrower case fields
    - primary/adversarial audit guidance now explicitly allows inline callback antecedents when the bridge remains sharply traceable, instead of treating inline placement as automatically defective
- A bounded audit quota-recovery follow-up is now landed locally:
  - code:
    - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
    - `reading-companion-backend/tests/test_case_design_audit.py`
  - bounded changes:
    - case audit now gives a quota-only failed case up to `2` extra whole-case recovery passes before freezing it as failed
    - audit summaries now record quota-recovery attempted/succeeded/remaining counts instead of leaving that evidence only inside per-case traces
    - this keeps temporary primary-tier cooldown exhaustion from being mistaken for callback-case quality truth
  - local validation:
    - `reading-companion-backend/tests/test_case_design_audit.py`
    - `reading-companion-backend/tests/test_case_design_audit_reproducibility.py`
    - `reading-companion-backend/tests/test_closed_loop_benchmark_curation.py`
    - focused result: `36 passed`
- Root-launched backend path resolution is now hardened:
  - code:
    - `reading-companion-backend/src/config.py`
    - `reading-companion-backend/tests/test_llm_gateway.py`
  - operator-facing docs:
    - `README.md`
    - `docs/runtime-modes.md`
  - bounded change:
    - relative `BACKEND_RUNTIME_ROOT` values now resolve from `reading-companion-backend/`, matching the existing relative LLM config path behavior
    - this stops workspace-root runtime spill such as accidental `state/llm_gateway/providers/*.lock` files when backend scripts are launched from the workspace root
- The substantive-evidence rerun lane is now completed under durable tracking:
  - the unregistered highspeed attempt:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_caseiso_judged_substantive_20260331/`
  - current disposition:
    - `up_from_slavery_public_en__10` completed, but the run stopped before producing a trustworthy summary because `attentional_v2` hit `runtime_reader_default` quota-wait exhaustion while the shared `MiniMax-M2.7-highspeed` cooldown was still active
    - this was an operational quota/tier-selection stop, not a new judged mechanism conclusion
  - replacement registered job:
    - `bgjob_en_chapter_core_rerun_round3_caseiso_judged_substantive_backup_20260331`
  - replacement run:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_caseiso_judged_substantive_backup_20260331/`
  - terminal status:
    - registry now reports `status = completed`, `exit_code = 0`, and `ended_at = 2026-03-31T03:47:46.607780Z`
    - the rerun stayed whole-job pinned to the generic `backup` tier and finished cleanly without mid-run target switching
  - landed outputs:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_caseiso_judged_substantive_backup_20260331/summary/report.md`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_caseiso_judged_substantive_backup_20260331/summary/aggregate.json`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_caseiso_judged_substantive_backup_20260331/summary/case_results.jsonl`
  - current interpretation:
    - the rerun confirms the operational tier-routing fix worked and should be treated as evidence only
    - `up_from_slavery_public_en__10` still exposes the chapter-arc / accumulation weakness in `attentional_v2`
    - `walden_205_en__10` still preserves a chapter-spanning reading strength, but not a decisive system-regression win
- The bounded callback reproducibility retry is now completed under durable tracking:
  - original registered job:
    - `bgjob_callbackslice_auditv4_packet_20260331`
  - packet:
    - `attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__callbackslice_auditv4_20260331`
  - source dataset:
    - `attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_broader_tensionfocusfix_20260331`
  - targeted cases:
    - `education_of_henry_adams_public_en__29__callback_bridge__seed_v1`
    - `on_liberty_public_en__10__callback_bridge__seed_v1`
  - live audit run:
    - `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__callbackslice_auditv4_20260331__20260331-014454/`
  - current disposition:
    - the original pre-patch run failed with `completed_case_count = 1` and `failed_case_count = 1`
    - `education_of_henry_adams_public_en__29__callback_bridge__seed_v1` completed under the v4 contract
    - `on_liberty_public_en__10__callback_bridge__seed_v1` failed under primary-tier quota exhaustion before the new case-audit quota-recovery patch existed
  - replacement registered job:
    - `bgjob_callbackslice_auditv4_packet_retry_quota_20260331`
  - replacement audit run:
    - `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__callbackslice_auditv4_20260331__20260331-020431/`
  - final archive:
    - `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__callbackslice_auditv4_20260331/`
  - launch policy:
    - full mechanical packet lifecycle only (`generate -> audit -> adjudicate -> import -> refresh -> summarize`)
    - explicit worker caps stay at `audit=1`, `review=1` so this packet can share the LLM budget safely with the active mechanism rerun
    - this is bounded reproducibility evidence only; no wider unattended automation or decision-bearing phase was auto-launched
    - inline-target callback cases now trigger a bounded primary-review replica escalation (`3` base replicas plus `2` extra replicas) before consensus is frozen
  - result:
    - retry action counts: `keep = 1`, `revise = 1`, `drop = 0`, `unclear = 0`
    - post-import benchmark counts: `reviewed_active = 7`, `needs_revision = 1`
    - queue summary returned to `active_packet_count = 0`
  - interpretation:
    - the failed first run is pre-patch operational evidence, not final callback-quality truth
    - the retry under the new audit quota-recovery path imported `education_of_henry_adams_public_en__29__callback_bridge__seed_v1` as `keep` / `reviewed_active`
    - the same retry left `on_liberty_public_en__10__callback_bridge__seed_v1` as `revise` / `needs_revision`, which re-framed the live callback holdout as argumentative focus clarity rather than quota instability or Henry-specific breadth
  - local validation:
    - `reading-companion-backend/tests/test_case_design_audit.py`
    - `reading-companion-backend/tests/test_case_design_audit_reproducibility.py`
    - focused result before the quota-recovery follow-up: `26 passed`
- A bounded argumentative callback attribution patch is now landed locally:
  - code:
    - `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
    - `reading-companion-backend/tests/test_question_aligned_case_construction.py`
  - bounded changes:
    - argumentative / reference-heavy callback cases now draft `selection_reason` and `judge_focus` as an explicit anchor-to-earlier-target bridge instead of only naming generic "specific earlier material"
    - those callback drafts now keep source attribution explicit for the author/work so argumentative callback cases stay source-grounded instead of reading like commentary
  - local validation:
    - `reading-companion-backend/tests/test_question_aligned_case_construction.py`
    - `reading-companion-backend/tests/test_case_design_audit.py`
    - `reading-companion-backend/tests/test_case_design_audit_reproducibility.py`
    - `reading-companion-backend/tests/test_closed_loop_benchmark_curation.py`
    - focused result: `70 passed`
- The narrow On Liberty callback-prompt follow-up is now completed:
  - run id:
    - `closed_loop_on_liberty_callbackpromptfix_20260331`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_on_liberty_callbackpromptfix_20260331/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 3`, `revise = 1`, `drop = 0`
    - post-import English benchmark counts: `reviewed_active = 3`, `needs_revision = 1`
  - diagnosis:
    - the repaired argumentative callback drafting now clears `on_liberty_public_en__4__callback_bridge__seed_v1` as a real `keep` on a one-source scratch slice
    - `on_liberty_public_en__10__callback_bridge__reserve_v1` remains available as a sharpened reserve rather than the active callback export for this source slice
    - the remaining revise in this narrow run is no longer callback-specific: `on_liberty_public_en__5__anchored_reaction_selectivity__seed_v1` still needs tighter focus framing
- The broader English callback-prompt follow-up is now completed:
  - job id:
    - `bgjob_closed_loop_en_broader_callbackpromptfix_20260331`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_callbackpromptfix_20260331/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 7`, `revise = 1`, `drop = 0`
    - post-import English benchmark counts: `reviewed_active = 7`, `needs_revision = 1`
  - diagnosis:
    - the repaired argumentative callback drafting now holds across the broader two-source English slice rather than only on the one-source On Liberty probe
    - the remaining English holdout is still a bounded focus-framing issue, not a callback-prompt collapse
- A bounded mechanism evidence-control mode is now landed in code:
  - code:
    - `reading-companion-backend/eval/attentional_v2/run_chapter_comparison.py`
    - `reading-companion-backend/tests/test_run_chapter_comparison.py`
  - bounded changes:
    - chapter comparison now supports `--judge-evidence-mode standard|substantive`
    - `substantive` mode filters lifecycle / operational attention events such as `parse`, `waiting`, `error`, `transition`, `segment_complete`, and `chapter_complete` out of the judge-facing bundle summary only
    - full mechanism bundles and persisted run-local bundle artifacts remain unchanged; only the judge input is filtered
  - local validation:
    - `reading-companion-backend/tests/test_run_chapter_comparison.py`
    - focused result: `5 passed`
- Root-launched local LLM config resolution is now hardened:
  - code:
    - `reading-companion-backend/src/reading_runtime/llm_registry.py`
    - `reading-companion-backend/tests/test_llm_gateway.py`
  - bounded change:
    - relative `LLM_TARGETS_PATH`, `LLM_PROFILE_BINDINGS_PATH`, and the older registry-path surface now resolve from the backend root instead of the caller's current working directory
    - this closes the validation hole where root-launched backend CLIs could miss `config/llm_targets.local.json` even though the same config worked from the backend directory
  - local validation:
    - `reading-companion-backend/tests/test_llm_gateway.py::test_relative_target_binding_paths_resolve_from_backend_root`
    - result: `passed`
- The focused English round-3 narrative/reference rerun is no longer running:
  - job id:
    - `bgjob_en_chapter_core_rerun_round3_parallel_20260329`
  - run dir:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_20260329/`
  - log:
    - `reading-companion-backend/state/job_registry/logs/bgjob_en_chapter_core_rerun_round3_parallel_20260329.log`
  - terminal status:
    - registry now reports `status = failed`, `exit_code = 1`, and `ended_at = 2026-03-29T03:22:18.900454Z`
    - the log ends with `ReaderLLMError: malformed json payload`
  - recovered partial outputs:
    - `up_from_slavery_public_en__10` has a case artifact, but its `attentional_v2` entry incorrectly points at the `walden_205_en__10` output directory, so the packaged comparison is not trustworthy as-is
    - `walden_205_en__10` never received a case artifact or final summary artifacts
    - `walden_205_en__10` `iterator_v1` activity shows repeated `network_blocked` stalls before the terminal malformed-JSON failure on `Visitors.13`
- The first malformed-JSON recovery rerun is no longer active:
  - job id:
    - `bgjob_20260329_035257_e6069f7e`
  - run dir:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_jsonfix_20260329/`
  - log:
    - `reading-companion-backend/state/job_registry/logs/bgjob_20260329_035257_e6069f7e.log`
  - terminal status:
    - registry now reports `status = abandoned` and `ended_at = 2026-03-29T04:18:48.646303Z`
    - the rerun was stopped intentionally after confirming the same parallel case path could still cross-wire isolated output directories
- The first case-isolation rerun did not finish cleanly:
  - job id:
    - `bgjob_20260329_041914_5de2c4c4`
  - run dir:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_20260329/`
  - log:
    - `reading-companion-backend/state/job_registry/logs/bgjob_20260329_041914_5de2c4c4.log`
  - terminal status:
    - registry now reports `status = abandoned` and `ended_at = 2026-03-29T04:24:43.447157Z`
    - the log stops after initial submit/skip lines, with no traceback and no summary outputs
  - launcher diagnosis:
    - the wrapper was launched from the Codex shell session and appears to have been terminated externally before it could record an exit code or traceback
    - the missing wrapper launch banner in the earlier failed log was consistent with the wrapper being killed before its buffered write flushed
- A detached-launch follow-up rerun completed successfully after the malformed-JSON recovery patch, the packaging isolation repair, and the launcher hardening:
  - job id:
    - `bgjob_en_chapter_core_rerun_round3_parallel_caseiso_detached_20260329_125043`
  - run dir:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_detached_20260329_125043/`
  - log:
    - `reading-companion-backend/state/job_registry/logs/bgjob_en_chapter_core_rerun_round3_parallel_caseiso_detached_20260329_125043.log`
  - current state:
    - the wrapper was launched via `scripts/launch_registered_job_detached.py`
    - registry now reports `status = completed`, `exit_code = 0`, and `ended_at = 2026-03-29T06:30:08.986637Z`
    - both case artifacts now point at their own output directories instead of cross-wiring `up_from_slavery` into `walden`
    - `summary/report.md`, `summary/aggregate.json`, and `summary/case_results.jsonl` were written successfully
    - the run used `--judge-mode none`, so the reported `tie: 2` outcome is placeholder evidence with `judge_unavailable`, not real judged comparison evidence
    - the rerun remains evidence-only and does not change promotion or default-cutover policy automatically
  - diagnosis/fix summary:
    - the prior `up_from_slavery` -> `walden` mispackaging is consistent with process-wide `resolve_output_dir` patching during parallel case execution
    - `run_chapter_comparison.py` now uses context-local output-dir overrides plus per-case subprocess isolation when parallel case workers are used
    - `run_registered_job.py` now flushes its launch banner, isolates the wrapped command into a new session, and records signal-based abandonment explicitly
    - `scripts/launch_registered_job_detached.py` is now the reliable path for launching long-running registered jobs from agent/non-interactive shells
- No benchmark promotion reopening, reviewed-slice freezing, durable-trace, re-entry, runtime-viability, or default-cutover work has been launched automatically after recovery.
- The new cleanup follow-up packet pair is now completed and archived:
  - English follow-up:
    - job id: `bgjob_private_library_cleanup_en_followup_after_recovery_20260329_launch`
    - packet id: `attentional_v2_private_library_cleanup_en_followup_after_recovery_20260329`
    - archived summary: `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_en_followup_after_recovery_20260329/dataset_review_pipeline_summary.json`
    - import result:
      - `drop = 6`
      - `revise = 3`
      - `keep = 0`
    - post-import counts remain:
      - `7` `reviewed_active`
      - `3` `needs_revision`
      - `6` `needs_replacement`
      - `154` `unset`
  - Chinese follow-up:
    - job id: `bgjob_private_library_cleanup_zh_followup_after_recovery_20260329_launch`
    - packet id: `attentional_v2_private_library_cleanup_zh_followup_after_recovery_20260329`
    - archived summary: `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_zh_followup_after_recovery_20260329/dataset_review_pipeline_summary.json`
    - import result:
      - `drop = 2`
      - `revise = 1`
      - `keep = 0`
    - post-import counts remain:
      - `13` `reviewed_active`
      - `1` `needs_revision`
      - `2` `needs_replacement`
      - `40` `unset`
- The coordination lane closeout is complete:
  - `eval/review_packets/review_queue_summary.json` was refreshed once after both imports
  - both archived follow-up packets now have `dataset_review_pipeline_summary.json`
- The judged mechanism-evidence rerun is now completed:
  - job id: `bgjob_en_chapter_core_rerun_round3_parallel_caseiso_judged_20260329`
  - run id: `attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_20260329`
  - registry status:
    - `completed`
    - `exit_code = 0`
    - `ended_at = 2026-03-29T09:44:07.582602Z`
  - landed summary artifacts:
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_20260329/summary/report.md`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_20260329/summary/aggregate.json`
    - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_20260329/summary/case_results.jsonl`
  - current top-line result:
    - `local_impact`: split `1-1`, `attentional_v2` win-or-tie rate `0.5`, average score parity `3.8` vs `3.8`
    - `system_regression`: split `1-1`, `attentional_v2` win-or-tie rate `0.5`, average scores `2.6` vs `3.0` in favor of `iterator_v1`
  - current interpretation to carry forward:
    - `walden_205_en__10` is a real narrative/reference-heavy win for `attentional_v2`
      - the win came from keeping one live interpretive axis active across the chapter instead of restarting from scratch on each local moment
    - `up_from_slavery_public_en__10` still favors `iterator_v1`
      - `attentional_v2` under-covered the chapter too sparsely and too late for a long narrative/reference-heavy case
      - the judge also distrusted the chapter targeting because the displayed chapter numbering is ambiguous, even though the underlying corpus row appears internally consistent
- The earlier "10 more books" note now appears to have been a misunderstanding rather than a separate visible intake wave:
  - the repo-visible private-library source pool still matches the tracked `29`-book supplement
  - that supplement already includes the known `16`-book `/Users/baiweijiang/Documents/BOOK/` batch plus the earlier `13` private Downloads books
  - `state/library_sources/` has no extra private EPUBs beyond that tracked manifest
  - no separate new 10-book wave is currently visible to the private-library builder
- The managed source catalog is now recovered on this checkout through the intake compatibility path:
  - intake run:
    - `reading-companion-backend/state/dataset_build/source_intake_runs/bootstrap_existing_sources_20260330.json`
  - current result:
    - `56` existing managed source files were cataloged from `state/library_sources/`
    - `5` `.normalized.epub` files were skipped as non-canonical managed sources
    - `reading-companion-backend/state/dataset_build/source_catalog.json` now exists and is usable by the managed supplement builder
- The first real managed-local scratch builder validation is now completed:
  - build summary:
    - `reading-companion-backend/state/dataset_build/build_runs/scratch_validation_en_qualityfix_20260330/build_summary.json`
  - current result:
    - selected source: `education_of_henry_adams_public_en`
    - `4` English excerpt cases
    - `4` English reserve cases
    - adequacy next action: `construct_and_review`
    - scratch manifests and dataset ids stayed namespaced under the run id
- The question-aligned builder quality-fix wave is now landed in code:
  - primary code paths:
    - `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
    - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
  - bounded behaviors landed:
    - case `start_sentence_id` / `end_sentence_id` now preserve the whole rendered excerpt window instead of only the anchor/support subset
    - excerpt rendering now stitches parser-fragment splits such as `Mr.` / initials / lowercase continuations and expands windows around broken edges
    - Chinese continuation fragments now stitch without synthetic spaces in the rendered excerpt
    - callback selection now requires explicit backward-link markers instead of generic lexical overlap
    - anchored-reaction selection now rejects obvious reported-speech false positives
    - context-dependent fragment anchors are penalized instead of being treated as stable standalone cases
    - paratext / bibliographic windows are filtered out
    - weak profile-order filler candidates no longer outrank much stronger same-chapter opportunities during the primary auto-selection pass
    - `reconsolidation_later_reinterpretation` candidates without explicit later / reinterpretation cues are now penalized instead of letting late-scene preference alone carry them
    - cue-free weak Chinese narrative candidates no longer get resurrected by feedback / deficit boosts
    - Chinese `tension_reversal` candidates now need an explicit local cue instead of atmospheric scene-setting alone
    - second-pass chapter fill now respects the minimum selection threshold instead of force-filling weak chapters
    - fragmentary anchor lines now reuse the merged readable line in `selection_reason`
    - `callback_bridge` candidates now require a resolved antecedent instead of surviving on a local backward marker alone
    - callback cases now carry explicit `prior_context_sentence_ids` / `prior_context_text` so longer-lookback bridge evidence survives into audit and packet review
    - exact same-source same-profile excerpt duplicates are now filtered before they become active or reserve rows, so near-identical packet slots such as the duplicated `on_liberty` callback excerpt do not keep resurfacing as separate benchmark seeds
- The bounded closed-loop controller now has real scratch evidence beyond the first plumbing landing:
  - earlier baseline evidence remains useful:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_construct_smoke_20260330/closed_loop_benchmark_curation_run_state.json`
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_20260330/closed_loop_benchmark_curation_summary.json`
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_repair_smoke_en_20260330/closed_loop_benchmark_curation_summary.json`
  - English-only quality improved materially after the builder fixes:
    - initial narrow English full smoke after the fix:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
      - result: `keep = 2`, `revise = 2`, `drop = 0`
      - this replaced the earlier narrow-English outcome of `drop = 2`, `revise = 2`, `keep = 0`
    - broader English scratch validation after the same fix:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
      - result: `keep = 4`, `revise = 4`, `drop = 0`
  - bilingual scratch validation exposed the next bottleneck more clearly:
    - first bilingual quality-fix run:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
      - result: English `revise = 4`, Chinese `drop = 1`
      - diagnosis: the Chinese case was still pure publication metadata, so the failure was builder quality rather than only review strictness
    - first bilingual paratext-filter rerun:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_paratextfix_20260330/closed_loop_benchmark_curation_summary.json`
      - result: English `keep = 2`, `revise = 2`; Chinese `revise = 1`
      - diagnosis: the publication-history/front-matter miss was fixed, but the selected Chinese excerpt still carried residual edge noise and was not yet benchmark-ready
    - second bilingual selection-floor rerun:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_selectionfix_20260330/closed_loop_benchmark_curation_summary.json`
      - result: English `revise = 4`; Chinese `keep = 1`
      - diagnosis:
        - the Chinese lane improved again because the stronger `tension_reversal` opportunity now displaced the weaker early `distinction_definition` filler
        - the English `cases.source.jsonl` rows stayed identical to the previous bilingual rerun, but regenerated case-audit inputs changed on all `4` English cases and the final LLM adjudication shifted from `keep = 2`, `revise = 2` to `revise = 4`
    - broader bilingual validation after the same builder wave:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_selectionfix_20260330/closed_loop_benchmark_curation_summary.json`
      - result: English `keep = 6`, `revise = 2`; Chinese `keep = 1`, `revise = 3`, `drop = 1`
      - diagnosis:
        - English case quality on the broader two-book sample improved materially beyond the earlier four-case bilingual pair
        - the remaining shared-case English instability still came from regenerated audit content rather than source-row drift:
          - `source_input_drift = 0`
          - `audit_input_drift = 3`
          - `action_drift = 1`
        - Chinese still has one residual low-quality case plus a revise-heavy tail, so builder shaping is not fully done there
    - focused Chinese cue-gate probe after the broader bilingual run:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_zh_cuegate_20260330/closed_loop_benchmark_curation_summary.json`
      - result: Chinese `keep = 1`, `revise = 1`, `drop = 0`
      - diagnosis:
        - the weak `chenlun` reconsolidation scene-description cases disappeared from the candidate set
        - the surviving `chenlun_public_zh__4__callback_bridge__seed_v1` is structurally real but still needs a longer lookback bridge target in the excerpt window
    - focused Chinese cue-guard builder validation:
      - `reading-companion-backend/state/dataset_build/build_runs/scratch_validation_zh_cueguard_20260330/build_summary.json`
      - result: `2` active Chinese candidate cases and `4` reserves on the `beiying_public_zh` + `chenlun_public_zh` slice
      - diagnosis:
        - `beiying_public_zh__2__tension_reversal__seed_v1` stayed strong
        - the active `chenlun` case shifted onto `chenlun_public_zh__4__callback_bridge__seed_v1`
  - a bounded audit-score coherence repair is now landed for the case-design audit stage:
    - code:
      - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
      - `reading-companion-backend/tests/test_case_design_audit.py`
      - `reading-companion-backend/eval/attentional_v2/case_audit_runs.py`
      - `reading-companion-backend/tests/test_dataset_review_pipeline.py`
    - bounded behaviors:
      - the primary audit prompt now defines the `1-5` score direction explicitly
      - impossible `keep` payloads no longer propagate `1` / `2` scores on bucket fit, focus clarity, or excerpt strength into downstream adjudication
      - semantically unusable audit placeholders now trigger bounded stage retries instead of being accepted as completed evidence on the first pass
      - if a case still cannot produce a usable primary or adversarial audit payload after those retries, the audit command now exits nonzero and downstream pipeline resume logic no longer treats that run as a completed audit
      - focused audit/reproducibility/controller tests passed after the repair
  - adjudication reproducibility tooling is now landed:
    - code:
      - `reading-companion-backend/eval/attentional_v2/auto_review_packet.py`
      - `reading-companion-backend/eval/attentional_v2/compare_packet_adjudication_runs.py`
      - `reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py`
    - bounded behaviors:
      - each adjudication run now writes per-case artifacts plus run-local `manifest.json`, `summary.json`, and `report.md` under `llm_review_runs/<run_id>/`
      - adjudication fingerprints now normalize to prompt-relevant input content instead of audit wrapper metadata such as timings or run ids
      - the compare tool now surfaces source-input drift separately from audit-input drift
      - final packet adjudication now consumes a compact structured audit summary instead of free-text audit notes or challenge prose
      - packet adjudication now rejects placeholder / unusable audit rows instead of silently normalizing them into downstream review evidence
      - the closed-loop variability guard now compares adjacent same-source adjudication runs even when regenerated audit inputs changed the packet fingerprint
    - current real English pair diagnosis:
      - compare result:
        - `same_packet_input_fingerprint = false`
        - `source_input_drift = 0`
        - `audit_input_drift = 4`
        - `action_drift = 2`
        - `confidence_drift = 2`
        - `problem_type_drift = 3`
      - current interpretation:
        - the remaining bilingual instability is not a pure same-input adjudication wobble
        - the English source rows held constant, but the regenerated audit judgments did not
  - current interpretation:
    - English builder quality improved materially and remains clearly better than the first narrow-English baseline
    - Chinese builder quality also improved materially: it no longer selects pure front matter and can now produce at least one real prose `keep`
    - the next blocker for unattended widening is now validation after the landed hardening rather than missing plumbing:
      - Chinese callback cases no longer package a cue-only bridge without showing the earlier bridge target
      - English adjudication no longer treats audit prose-only drift as canonical downstream input
      - the next bounded move is to rerun broader English and focused/broader Chinese scratch validation to see how much source-equal drift remains after the compact-adjudication and callback-antecedent patches
  - a compact adjudication-summary hardening patch is now landed for packet review runs:
    - code:
      - `reading-companion-backend/eval/attentional_v2/auto_review_packet.py`
      - `reading-companion-backend/tests/test_packet_adjudication_reproducibility.py`
    - bounded behaviors:
      - `llm_review_runs/<run_id>/` now uses a short storage id instead of repeating the full packet id in the filesystem path
      - auxiliary trace-file lookup is now non-fatal, so missing or unreadable trace files do not crash the whole packet adjudication pass
      - the long-path failure seen on the broader English repeat is now covered by a regression test
  - the first broader English compact-adjudication rerun is now completed:
    - job id:
      - `bgjob_closed_loop_en_broader_compactadjudication_20260330`
    - summary:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_compactadjudication_20260330/closed_loop_benchmark_curation_summary.json`
    - result:
      - English `keep = 3`, `revise = 5`, `drop = 0`
  - the first Chinese callback-lookback rerun is now completed:
    - job id:
      - `bgjob_closed_loop_zh_callbacklookback_20260330`
    - summary:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_zh_callbacklookback_20260330/closed_loop_benchmark_curation_summary.json`
    - result:
      - Chinese `keep = 1`, `revise = 1`, `drop = 0`
    - diagnosis:
      - the surviving `chenlun_public_zh__4__callback_bridge__seed_v1` was structurally real, but its `prior_context_sentence_ids` were still empty
      - the archived review still rejected it as a cue-only bridge because the packet showed no earlier bridge target
  - the follow-up Chinese callback prior-context rerun is now completed:
    - job id:
      - `bgjob_closed_loop_zh_callbackpriorcontext_20260330`
    - summary:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_zh_callbackpriorcontext_20260330/closed_loop_benchmark_curation_summary.json`
    - result:
      - Chinese `keep = 1`, `revise = 1`, `drop = 0`
    - diagnosis:
      - `chenlun_public_zh__4__callback_bridge__seed_v1` now carries non-empty `prior_context_sentence_ids` and `prior_context_text`
      - the archived review no longer says the case lacks prior context; it now asks for a stronger excerpt boundary that makes the callback salience more evident
      - the Chinese blocker has narrowed from missing bridge evidence to excerpt-boundary quality
  - the broader English compact-adjudication repeat first failed and then was resumed successfully:
    - original failed job:
      - `bgjob_closed_loop_en_broader_compactadjudication_repeat_20260330`
      - failure: `auto_review_packet.py` hit `OSError: [Errno 63] File name too long` while building the packet-review trace path
    - resumed recovery job:
      - `bgjob_closed_loop_en_broader_compactadjudication_repeat_resume_20260330`
      - result:
        - English `keep = 2`, `revise = 6`, `drop = 0`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330/closed_loop_benchmark_curation_summary.json`
      - archived packet review:
        - `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330__initial_review__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330/llm_review_report.md`
  - current compact-adjudication English pair diagnosis:
    - compare result:
      - `same_packet_input_fingerprint = false`
      - `source_input_drift = 3`
      - `audit_input_drift = 8`
      - `action_drift = 3`
      - `confidence_drift = 2`
      - `problem_type_drift = 4`
    - interpretation:
      - the path-length bug is fixed and no longer blocks the controller
      - the pair is still not trustworthy as reproducibility evidence because three English source rows drifted and all eight audit inputs changed
      - the source drift is now understood more clearly:
        - the repeat reused the same source books but not the same feedback state
        - the first compact run imported its packet into the live English feedback dataset before the repeat rebuilt the scratch packet
        - this means the repeat pair mixes builder-feedback adaptation with audit/adjudication variability instead of isolating one reproducibility layer cleanly
      - the next blocker is now reproducibility isolation plus audit stability rather than packet orchestration
  - the frozen-packet adjudication probe wave is now completed:
    - target packet:
      - `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330__initial_review__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330/`
    - first frozen-input probe:
      - job id:
        - `bgjob_packet_adjudication_probe_en_compactrepeat_20260330`
      - run id:
        - `llm_review__20260330-154948__ae50caff2084`
      - compare against the archived non-probe run `llm_review__20260330-153904__ae50caff2084`:
        - `same_packet_input_fingerprint = true`
        - `source_input_drift = 0`
        - `audit_input_drift = 0`
        - `action_drift = 6`
        - `confidence_drift = 6`
        - `problem_type_drift = 3`
      - interpretation:
        - this was the first clean proof that final adjudication itself could drift heavily even when both source rows and compact audit inputs were frozen
    - compact-audit-v2 probe:
      - job id:
        - `bgjob_packet_adjudication_probe_en_compactrepeat_compactauditv2_20260330`
      - run id:
        - `llm_review__20260330-160343__ae50caff2084`
      - compare against the archived non-probe run:
        - `same_packet_input_fingerprint = false`
        - `source_input_drift = 0`
        - `audit_input_drift = 8`
        - `action_drift = 3`
      - interpretation:
        - this run did not preserve the original frozen adjudication input contract because the compact audit summary logic changed again
        - it was still useful as evidence that the narrowed compact-audit contract could move the action mix toward `keep = 5`, `revise = 3`
        - it was not valid same-input adjudication-only evidence
    - replayed frozen-input probe after the probe-only replay hardening:
      - direct run id:
        - `llm_review__20260330-163116__ae50caff2084`
      - summary:
        - `input_payload_source = reused_prior_run`
        - `reused_input_run_id = llm_review__20260330-153904__ae50caff2084`
        - `adjudication_input_fingerprint = 1737d8aa13f7786bd8cff08648dce90ff3d0e889122aabe2e7ca969926e05edd`
      - compare against the archived non-probe run:
        - `same_packet_input_fingerprint = true`
        - `source_input_drift = 0`
        - `audit_input_drift = 0`
        - `action_drift = 1`
        - `confidence_drift = 2`
        - `problem_type_drift = 3`
      - compare against the first frozen-input probe:
        - `same_packet_input_fingerprint = true`
        - `action_drift = 5`
        - `confidence_drift = 5`
        - `problem_type_drift = 4`
      - interpretation:
        - `auto_review_packet.py --probe-only` can now replay stored adjudication inputs from the packet's prior run instead of silently regenerating them from newer compaction logic
        - the latest same-input replay landed much closer to the archived baseline than the first probe did
        - adjudication variance is still material across repeated same-input probes, so the next blocker remains final adjudication hardening rather than wider controller automation
    - current code hardening after that diagnosis:
      - `reading-companion-backend/eval/attentional_v2/auto_review_packet.py` now performs a bounded serial recovery pass for quota-only adjudication failures before finalizing `unclear` rows
      - the adjudication prompt now strips builder workflow metadata such as scratch status, review history, internal builder scores, and other non-case-quality bookkeeping from the case JSON it shows the final adjudicator
      - the packet-adjudication scope now also passes its worker demand into target-tier selection so scope-start routing can honor job concurrency needs more explicitly
      - focused reproducibility tests for both replayed inputs and quota-failure recovery now pass in `reading-companion-backend/tests/test_packet_adjudication_reproducibility.py`
  - a second adjudication-stability hardening wave is now landed:
    - code:
      - `reading-companion-backend/eval/attentional_v2/auto_review_packet.py`
      - `reading-companion-backend/tests/test_packet_adjudication_reproducibility.py`
    - bounded behaviors:
      - `ADJUDICATION_CONTRACT_VERSION` is now `packet_adjudication_rubric_v4`
      - replayed saved-input probes now recompute the active adjudication contract identity before recording comparison metadata, so older saved payloads are not mislabeled as same-contract evidence after rubric edits
      - the final adjudication prompt now explicitly says to judge the excerpt case rather than workflow-stage bookkeeping, to default to `keep` for strong/clean/low-risk cases, and not to penalize `callback_bridge` simply because adjacent phenomena are also present
      - `_apply_adjudication_precedence(...)` now enforces a strong-clean-low-risk `keep` precedence plus a narrower callback-bridge `revise` precedence when the primary audit already says the callback case is broad or ambiguous
      - focused reproducibility tests passed for replayed saved inputs plus the new precedence guards
  - the frozen-input adjudication v4 probe pair is now completed:
    - target packet:
      - `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330__initial_review__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330/`
    - run ids:
      - `llm_review__20260330-174858__ae50caff2084`
      - `llm_review__20260330-175048__ae50caff2084`
    - compare result:
      - `same_packet_input_fingerprint = true`
      - `source_input_drift = 0`
      - `audit_input_drift = 0`
      - `action_drift = 0`
      - `confidence_drift = 1`
      - `problem_type_drift = 2`
      - both runs kept the same `action_counts`: `keep = 5`, `revise = 3`
    - interpretation:
      - same-input final-action stability is now materially better under rubric v4
      - the remaining noise on frozen packet inputs is confidence/problem-type jitter rather than action flips
  - the broader v4 live validation wave is now completed:
    - broader English scratch validation:
      - job id:
        - `bgjob_closed_loop_en_broader_adjudicationv4_20260331`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_adjudicationv4_20260331/closed_loop_benchmark_curation_summary.json`
      - result:
        - English `keep = 6`, `revise = 2`, `drop = 0`
    - broader bilingual scratch validation:
      - job id:
        - `bgjob_closed_loop_bilingual_broader_adjudicationv4_20260331`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_adjudicationv4_20260331/closed_loop_benchmark_curation_summary.json`
      - result:
        - English `keep = 5`, `revise = 3`, `drop = 0`
        - Chinese `keep = 1`, `revise = 1`, `drop = 0`
    - shared-English compare against the bilingual v4 run:
      - `source_input_drift = 0`
      - `audit_input_drift = 5`
      - `action_drift = 3`
      - `confidence_drift = 4`
      - `problem_type_drift = 4`
    - interpretation:
      - the adjudication bottleneck has shifted from frozen same-input action instability to live regenerated audit-input drift across English-only versus bilingual contexts
      - the next dataset-platform narrowing step should focus on why the shared English case audits still change when the source rows stay constant
  - case-audit reproducibility tooling is now landed:
    - code:
      - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
      - `reading-companion-backend/eval/attentional_v2/compare_case_audit_runs.py`
      - `reading-companion-backend/tests/test_case_design_audit.py`
    - bounded behaviors:
      - each case-audit row now persists a stable prompt-input payload plus `audit_prompt_input_fingerprint`
      - case-audit summaries now persist a run-level audit-input fingerprint built from the per-case prompt fingerprints
      - `compare_case_audit_runs.py` can now separate same-input audit drift from input drift across two audit runs
    - interpretation:
      - future English-only versus bilingual audit comparisons no longer need to guess whether the divergence came from prompt inputs or from the audit model output itself
  - the fresh detached audit-pair live-stability wave is now completed on current code:
    - broader English-only rerun:
      - job id:
        - `bgjob_closed_loop_en_broader_auditpair_20260331`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditpair_20260331/closed_loop_benchmark_curation_summary.json`
      - result:
        - English `keep = 5`, `revise = 3`, `drop = 0`
    - broader bilingual rerun:
      - job id:
        - `bgjob_closed_loop_bilingual_broader_auditpair_20260331`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_auditpair_20260331/closed_loop_benchmark_curation_summary.json`
      - result:
        - English `keep = 3`, `revise = 5`, `drop = 0`
        - Chinese `keep = 1`, `revise = 1`, `drop = 0`
    - shared-English case-audit compare result:
      - artifact:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditpair_20260331/case_audit_compare_against_bilingual.json`
      - result:
        - `same_run_audit_prompt_input_fingerprint = true`
        - `source_input_drift = 0`
        - `audit_input_drift = 0`
        - `primary_decision_drift = 2`
        - `primary_confidence_drift = 2`
        - `primary_problem_type_drift = 5`
        - `primary_score_drift = 8`
        - `adversarial_risk_drift = 2`
    - interpretation:
      - the remaining live English instability is now narrowed to same-input audit-stage output variance, not builder-side case/context drift
      - the next selective hardening move belongs in audit-stage reproducibility rather than in source-row reconstruction or builder plumbing
  - the first audit-stage reproducibility hardening patch is now landed in code:
    - code:
      - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
      - `reading-companion-backend/eval/attentional_v2/auto_review_packet.py`
      - `reading-companion-backend/tests/test_case_design_audit.py`
    - bounded changes:
      - `AUDIT_PROMPT_CONTRACT_VERSION` is now `case_design_audit_v2`
      - the primary audit prompt now asks for `strong|adequate|weak` axis bands instead of raw `1-5` scoring
      - primary audit normalization now maps those bands back into canonical numeric scores for downstream compatibility
      - adjudication-side compact audit inputs now prefer explicit normalized bands when they are present
  - the detached audit-contract-v2 validation wave is now completed:
    - broader English-only rerun:
      - job id:
        - `bgjob_closed_loop_en_broader_auditcontractv2_20260331`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditcontractv2_20260331/closed_loop_benchmark_curation_summary.json`
      - result:
        - English `keep = 4`, `revise = 3`, `unclear = 1`, `drop = 0`
    - broader bilingual rerun:
      - job id:
        - `bgjob_closed_loop_bilingual_broader_auditcontractv2_20260331`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_auditcontractv2_20260331/closed_loop_benchmark_curation_summary.json`
      - result:
        - English `keep = 5`, `revise = 3`, `unclear = 0`, `drop = 0`
        - Chinese `keep = 1`, `revise = 1`, `unclear = 0`, `drop = 0`
    - shared-English case-audit compare result:
      - artifact:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditcontractv2_20260331/case_audit_compare_against_bilingual.json`
      - result:
        - `same_run_audit_prompt_input_fingerprint = true`
        - `source_input_drift = 0`
        - `audit_input_drift = 0`
        - `primary_decision_drift = 5`
        - `primary_confidence_drift = 3`
        - `primary_problem_type_drift = 6`
        - `primary_score_drift = 7`
        - `adversarial_risk_drift = 3`
    - interpretation:
      - the stricter all-strong keep gate made the primary audit more brittle to single-axis `4 -> 3` wobble instead of narrowing same-input drift
      - the blocker is still audit-stage reproducibility, not builder/input drift
  - the second audit-stage reproducibility hardening patch is now landed in code:
    - code:
      - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
      - `reading-companion-backend/tests/test_case_design_audit.py`
    - bounded changes:
      - `AUDIT_PROMPT_CONTRACT_VERSION` is now `case_design_audit_v3`
      - the primary audit keep gate now treats one adequate axis as still benchmark-usable when no axis is weak
      - primary normalization now derives the normalized decision and minimal problem-type set deterministically from the normalized axis scores while preserving the malformed-keep repair path
  - the detached audit-contract-v3 validation wave is now completed:
    - broader English-only rerun:
      - job id:
        - `bgjob_closed_loop_en_broader_auditcontractv3_20260331`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditcontractv3_20260331/closed_loop_benchmark_curation_summary.json`
      - result:
        - English `keep = 4`, `revise = 4`, `unclear = 0`, `drop = 0`
    - broader bilingual rerun:
      - job id:
        - `bgjob_closed_loop_bilingual_broader_auditcontractv3_20260331`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_auditcontractv3_20260331/closed_loop_benchmark_curation_summary.json`
      - result:
        - English `keep = 5`, `revise = 3`, `unclear = 0`, `drop = 0`
        - Chinese `keep = 2`, `revise = 0`, `unclear = 0`, `drop = 0`
    - shared-English case-audit compare result:
      - artifact:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditcontractv3_20260331/case_audit_compare_against_bilingual.json`
      - result:
        - `same_run_audit_prompt_input_fingerprint = true`
        - `source_input_drift = 0`
        - `audit_input_drift = 0`
        - `primary_decision_drift = 4`
        - `primary_confidence_drift = 5`
        - `primary_problem_type_drift = 5`
        - `primary_score_drift = 5`
        - `adversarial_risk_drift = 1`
    - interpretation:
      - the softer keep gate improved the audit relative to `auditcontractv2`, especially on score drift and adversarial-risk drift
      - the blocker still remains inside same-input audit reproducibility, because `primary_decision_drift = 4` is still too high for unattended widening
  - the third audit-stage reproducibility hardening patch is now landed in code:
    - code:
      - `reading-companion-backend/eval/attentional_v2/run_case_design_audit.py`
      - `reading-companion-backend/tests/test_case_design_audit.py`
    - bounded changes:
      - the primary audit now runs `3` zero-temperature replicas per case
      - the final normalized primary review is selected by deterministic consensus:
        - majority vote on the normalized action
        - median axis scores
        - conservative tie-breaks
        - majority or exemplar-backed problem types
      - this keeps the repair inside audit-stage reproducibility rather than changing builder inputs again
  - the detached audit-consensus-v3 validation wave is now completed:
    - broader English-only rerun:
      - job id:
        - `bgjob_closed_loop_en_broader_auditconsensusv3_20260331`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditconsensusv3_20260331/closed_loop_benchmark_curation_summary.json`
      - result:
        - English `keep = 5`, `revise = 3`, `unclear = 0`, `drop = 0`
    - broader bilingual rerun:
      - job id:
        - `bgjob_closed_loop_bilingual_broader_auditconsensusv3_20260331`
      - summary:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_auditconsensusv3_20260331/closed_loop_benchmark_curation_summary.json`
      - result:
        - English `keep = 5`, `revise = 3`, `unclear = 0`, `drop = 0`
        - Chinese `keep = 1`, `revise = 1`, `unclear = 0`, `drop = 0`
    - shared-English case-audit compare result:
      - artifact:
        - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditconsensusv3_20260331/case_audit_compare_against_bilingual.json`
      - result:
        - `same_run_audit_prompt_input_fingerprint = true`
        - `source_input_drift = 0`
        - `audit_input_drift = 0`
        - `primary_decision_drift = 2`
        - `primary_confidence_drift = 2`
        - `primary_problem_type_drift = 2`
        - `primary_score_drift = 4`
        - `adversarial_risk_drift = 2`
    - interpretation:
      - replica consensus is the first audit-stage hardening move that brought same-input English `primary_decision_drift` back down to the earlier `auditpair` baseline while also improving problem-type and score stability beyond that baseline
      - the English-only and bilingual runs now align on final English `keep = 5` / `revise = 3`, so the blocker has moved from narrow audit reproducibility toward broader validation and unattended-loop boundary work
  - a builder-side invisible-whitespace normalization patch is now landed in code:
    - code:
      - `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
      - `reading-companion-backend/tests/test_question_aligned_case_construction.py`
    - bounded changes:
      - rendered excerpt text now strips invisible Unicode format characters and normalizes non-breaking whitespace before the final case text is emitted
      - builder-facing anchor text and selection-reason lines now reuse the cleaned text instead of leaking zero-width / non-breaking whitespace noise into packet review
    - deterministic validation:
      - `reading-companion-backend/state/dataset_build/build_runs/scratch_validation_en_whitespacefix_20260331/build_summary.json`
      - the previously corrupted `education_of_henry_adams_public_en__16__anchored_reaction_selectivity__seed_v1` row now emits clean `excerpt_text` and `selection_reason` with no invisible whitespace artifacts
    - narrow closed-loop confirmation:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_henry_whitespacefix_20260331/closed_loop_benchmark_curation_summary.json`
      - result: English `keep = 3`, `revise = 1`, `drop = 0`
      - the previously corrupted Henry Adams anchored-reaction case no longer fails on text integrity
      - it now lands as a confident `keep` on the cleaned packet path
    - broader English confirmation:
      - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_whitespacefix_20260331/closed_loop_benchmark_curation_summary.json`
      - result: English `keep = 7`, `revise = 1`, `drop = 0`
      - the cleaned builder path now holds across the current two-source English slice instead of only on the narrow Henry Adams proof
  - all bounded controller runs still stopped with summaries only:
    - no benchmark promotion, reviewed-slice freeze, runtime-viability, or default-cutover work was launched automatically
- The post-patch broader English scratch validation is now completed:
  - job id:
    - `bgjob_closed_loop_en_broader_auditcoherencefix_20260330`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditcoherencefix_20260330/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 3`, `revise = 5`, `drop = 0`
  - diagnosis:
    - the audit-score coherence repair did remove the earlier impossible `keep + 1/1/1` primary-audit pattern
    - comparing this packet directly against the pre-fix broader bilingual packet is not yet a clean reproducibility verdict because the audit contract changed
- A same-config repeat of the broader English post-fix run is now completed:
  - job id:
    - `bgjob_closed_loop_en_broader_auditcoherencefix_repeat_20260330`
  - run id:
    - `closed_loop_full_smoke_en_broader_auditcoherencefix_repeat_20260330`
  - result:
    - English `keep = 1`, `revise = 7`, `drop = 0`
  - diagnosis:
    - even under the same post-fix audit contract and worker caps, the English repeat pair still held `source_input_drift = 0` while all `8` audit rows changed
    - the earlier impossible-score bug is fixed, but audit reproducibility is still not good enough for unattended widening
- The broader bilingual post-fix validation is now completed:
  - job id:
    - `bgjob_closed_loop_bilingual_broader_auditcoherencefix_20260330`
  - summary:
    - `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_auditcoherencefix_20260330/closed_loop_benchmark_curation_summary.json`
  - result:
    - English `keep = 4`, `revise = 4`, `drop = 0`
    - Chinese `keep = 1`, `revise = 1`, `drop = 0`
  - diagnosis:
    - the Chinese cue-guard shaping held through the broader bilingual packet lifecycle and removed the earlier dropped Chinese tail
    - the shared English rows still showed `source_input_drift = 0`, `audit_input_drift = 8`, and `action_drift = 5` against the post-fix English-only run
- The judged two-case mechanism follow-up rerun is now completed:
  - job id:
    - `bgjob_en_chapter_core_rerun_round3_caseiso_judged_followup_20260330`
  - run id:
    - `attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_followup_20260330`
  - registry status:
    - `completed`
    - `exit_code = 0`
    - `ended_at = 2026-03-30T13:46:45.547987Z`
  - current top-line result:
    - `local_impact`: `attentional_v2` wins both cases, win-or-tie rate `1.0`, average scores `4.4` vs `3.6`
    - `system_regression`: `attentional_v2` wins both cases, win-or-tie rate `1.0`, average scores `4.0` vs `2.4`
  - interpretation to carry forward:
    - the bounded follow-up repair preserved the `walden_205_en__10` strength
    - `up_from_slavery_public_en__10` also flipped in favor of `attentional_v2`, so the next mechanism step is selective generalization and overfitting checks rather than emergency rescue
- The next guarded dataset-platform rerun is now completed:
  - job id:
    - `bgjob_closed_loop_en_broader_auditsemanticretry_20260330`
  - run id:
    - `closed_loop_full_smoke_en_broader_auditsemanticretry_20260330`
  - registry status:
    - `completed`
    - `exit_code = 0`
    - `ended_at = 2026-03-30T13:29:35.050505Z`
  - result:
    - English `keep = 4`, `revise = 4`, `drop = 0`
    - post-import English benchmark counts: `reviewed_active = 4`, `needs_revision = 4`
    - `variability_guard_triggered = false`
  - interpretation to carry forward:
    - the guarded rerun completed cleanly and reproduced the broader English `4 keep / 4 revise` split
    - the next dataset-platform step is comparison and reproducibility diagnosis, not more queue plumbing
- There are currently no active offline background jobs.
  - the broader English callback-prompt rerun finished cleanly at `7 keep / 1 revise`
  - the later bilingual `callbackpromptfix` launch was retired as superseded scratch work after exporting packets because later callback/tension follow-ups already produced stronger durable bilingual evidence
  - the retired scratch packets were moved out of the live pending queue into the run-local state area, and the visible review queue remains at `active_packet_count = 0`
- The dataset-platform route is now underway, and it should keep reusing the machinery already landed rather than replace it:
  - keep the current strengths:
    - manifest-driven source promotion and canonical parsing from `corpus_builder.py`
    - explicit case metadata fields such as `question_ids`, `phenomena`, `selection_reason`, and `judge_focus`
    - the mechanical review packet lifecycle in `run_dataset_review_pipeline.py`
    - optional reviewed-slice freezing in `freeze_reviewed_dataset_slice.py`
  - Phase 1 managed intake is now landed:
    - operator drop folders under `reading-companion-backend/state/library_inbox/`
    - intake CLI:
      - `reading-companion-backend/eval/attentional_v2/ingest_library_sources.py`
    - root operator surface:
      - `make library-source-intake`
    - durable source catalog outputs under `reading-companion-backend/state/dataset_build/`
    - compatibility recovery is now also landed:
      - `make library-source-intake LIBRARY_SOURCE_INTAKE_ARGS="--bootstrap-library-sources --run-id <run_id>"`
      - this seeds the managed source catalog from existing `state/library_sources/` files plus tracked manifest metadata when inbox-driven intake has not been used yet
    - new canonical managed copies now live under one language-rooted `state/library_sources/` layout instead of a public/private folder split
    - `visibility` remains only as compatibility metadata and should not drive normal product-side intake or dataset-platform decisions
    - the current private-library supplement builder now consumes that managed source catalog and canonical local source copies instead of external `/BOOK` or `Downloads` roots
  - build the next dataset platform as one closed loop:
    - managed source intake and project-owned artifact layout
    - question-aligned case construction
    - packetized audit, adjudication, import, and archive
    - adequacy checks plus targeted rebuild/replacement until the dataset is strong enough or the source pool is exhausted
  - the concrete Phase 2 design now lives in:
    - `docs/implementation/new-reading-mechanism/question-aligned-case-construction.md`
  - the first live Phase 2 landing is now in code:
    - `reading-companion-backend/eval/attentional_v2/question_aligned_case_construction.py`
    - `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py`
    - the current historical `private_library` builder family now behaves as a managed local supplement lane rather than as a distribution-driven policy lane
    - it writes question-aligned excerpt candidate datasets to:
      - `state/eval_local_datasets/excerpt_cases/attentional_v2_private_library_excerpt_en_question_aligned_v1/`
      - `state/eval_local_datasets/excerpt_cases/attentional_v2_private_library_excerpt_zh_question_aligned_v1/`
    - the builder also emits durable intermediate artifacts under:
      - `state/dataset_build/target_profiles/`
      - `state/dataset_build/opportunity_maps/`
      - `state/dataset_build/candidate_cases/`
      - `state/dataset_build/reserve_cases/`
      - `state/dataset_build/adequacy_reports/`
    - the existing live `attentional_v2_private_library_excerpt_en_v2` and `attentional_v2_private_library_excerpt_zh_v2` datasets are now used as feedback inputs for adequacy and replacement pressure instead of being overwritten by this new construction path
  - the builder now also supports scratch-safe validation runs:
    - run-scoped manifests and build artifacts go under `state/dataset_build/build_runs/<run_id>/`
    - scratch excerpt datasets use run-scoped ids under `state/eval_local_datasets/`
  - the first bounded Phase 3 controller is now landed in code:
    - `reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py`
    - root operator surface:
      - `make closed-loop-benchmark-curation`
    - current scope:
      - construct scratch datasets
      - export initial `--only-unreviewed` packets
      - audit, adjudicate, import, archive
      - optional one-wave revision/replacement repair
      - refresh queue summary
      - emit one final stop-and-summarize report
    - current boundary:
      - this is a first bounded controller, not yet the final unattended multi-iteration scheduler
  - the unattended loop boundary is now more concrete, but the final scheduler should still wait until real scratch runs confirm the Phase 2 artifacts and first bounded controller are trustworthy
- Use the task registry plus the execution tracker as the route back into detailed mechanism work.

## Next
- Use the completed backup-tier substantive rerun as the parked focused mechanism-evidence checkpoint:
  - preserve the `walden_205_en__10` chapter-spanning threading behavior as a protected strength
  - keep `up_from_slavery_public_en__10` as the bounded chapter-arc weakness instead of reopening mechanism-eval fanout automatically
- Use the cleanup follow-up summaries as the new benchmark-hardening truth:
  - the extra cleanup pass did not produce any `keep` decisions
  - the English `9` and Chinese `3` open cases were reaffirmed as `revise` / `drop` rather than promoted into `reviewed_active`
- Use the new managed intake layer for any future book additions instead of external `/BOOK` or `Downloads` roots:
  - drop books into `reading-companion-backend/state/library_inbox/`
  - use nested folders only for optional batch organization
  - run `make library-source-intake`
- Use the latest scratch evidence to stabilize case quality and reproducibility rather than adding new platform plumbing:
  - keep the broader English adjudication-v4 result (`keep = 6`, `revise = 2`) as the strongest current English scratch result
  - keep the broader bilingual adjudication-v4 result (`en: keep = 5 / revise = 3`, `zh: keep = 1 / revise = 1`) as the current cross-language baseline
  - keep the completed Chinese callback-priorcontext rerun as proof that `chenlun` bridge evidence now survives into packet review
  - shift the Chinese follow-up from “add prior context” to “tighten callback excerpt boundaries so the bridge is more legible as a benchmark case”
  - keep replayed frozen-input `auto_review_packet.py --probe-only` runs as the clean adjudication-only measurement path, because the v4 pair now shows `action_drift = 0` on frozen inputs
  - use the completed `auditpair` compare artifact as the narrow live-stability baseline, because it shows `audit_input_drift = 0` with only `primary_decision_drift = 2` on the shared English cases
  - treat the completed `auditcontractv2` compare result as proof that the stricter all-strong keep gate did not solve the blocker and in fact widened `primary_decision_drift` to `5`
  - treat the completed `auditcontractv3` compare result as a partial improvement rather than a finish line, because it reduced `primary_score_drift` to `5` and `primary_decision_drift` to `4` but still left the audit too unstable for unattended widening
  - treat the completed `auditconsensusv3` compare result as the new live reproducibility baseline, because it brought `primary_decision_drift` back down to `2`, reduced `primary_problem_type_drift` to `2`, and aligned English final action counts across the English-only and bilingual runs
  - keep the new builder-side invisible-whitespace normalization as the current English case-quality repair, because it removed the zero-width / non-breaking whitespace corruption that was still leaking into the Henry Adams anchored-reaction case
  - keep the completed Henry Adams and broader-English whitespace-fix follow-ups as proof that the same anchored-reaction case now reviews as `keep` on the cleaned path and that the remaining English issue is a bounded callback-breadth outlier, not text corruption
- Use the completed callback-focus and tension-focus follow-ups as the new narrow builder-quality truth:
  - keep `callbackfocusfix` as the strongest current four-source bilingual callback checkpoint (`en: 7 keep / 1 revise`, `zh: 1 keep`)
  - keep the new tension-specific window/focus patch, because it turned `on_liberty_public_en__5__tension_reversal__seed_v1` into a real `keep`
  - treat the mixed `tensionfocusfix` bilingual packet as audit/adjudication drift on unchanged callback cases until the reproducibility tooling says otherwise
- Keep the bounded controller as the active automation surface, but use the new callback-audit hardening before the next broader validation wave:
  - the completed v4 frozen-input pair is already the clean proof that final-action instability is no longer the primary blocker
  - the remaining uncertainty is broader-slice generalization and any surviving focus drift, not missing controller plumbing
  - the callback retry plus the one-source On Liberty callback-prompt follow-up now clear the narrow callback blocker on the targeted slice
  - the completed broader English callback-prompt rerun now proves the repair holds on the full two-source English slice
  - the next automatic controller-side step is the bounded reproducibility repair wave on the unchanged callback rows exposed by `tensionfocusfix`, not another broad rerun by default
  - only after that reproducibility check holds should we consider another bilingual widening pass
  - only if `on_liberty_public_en__5__anchored_reaction_selectivity__seed_v1` still survives after that should it become the next bounded focus-framing follow-up
- Keep the dataset-platform route phased rather than monolithic:
  - source-book intake and intermediate-artifact governance is now landed
  - the first Question-Aligned Case Construction landing on top of the current corpus/review schema is now landed
  - the first bounded closed-loop controller is now landed and has completed one real scratch smoke plus one repair wave
  - the multi-iteration unattended scheduler still remains after a broader set of real scratch validations above
- Keep the prior failed `bgjob_en_chapter_core_rerun_round3_parallel_20260329` artifacts as debugging evidence:
  - treat `up_from_slavery_public_en__10` as packaging-corrupted because the `attentional_v2` case entry points at `walden` outputs
  - treat `walden_205_en__10` as incomplete because no case artifact or summary artifacts were written
- Work from the recovered live local-only excerpt datasets:
  - the current follow-up cleanup pass has now dispositioned those cases mechanically, but it did not clear the open benchmark-status backlog
  - the `auditpair`, `auditcontractv2`, `auditcontractv3`, and `auditconsensusv3` waves all completed cleanly and their compare artifacts now form the durable audit-hardening evidence ladder
  - the review queue remains empty (`active_packet_count = 0`), and the later callback/tension follow-ups also finished with no active packet left open after import/archive
- Prepare a human-owned post-cleanup gate review from the recovered counts, the two new follow-up packet summaries, and the still-open benchmark statuses.
- Keep benchmark promotion, reviewed-slice freezing, durable-trace, re-entry, runtime-viability, and any default-cutover decision paused until a human explicitly asks for them.

## Blocked
- Formal curated promotion from the modern private-library supplement remains paused until the remaining open cases are dispositioned and a human explicitly reopens the post-recovery gate discussion.
- Reviewed-slice freezing remains paused until a human explicitly chooses to freeze a slice.
- Durable-trace, re-entry, and runtime-viability remain intentionally queued until the post-recovery benchmark gate becomes an explicit human-owned decision.
- The later frontend/API retirement of section-first chapter/detail and marks surfaces remains blocked on benchmark stabilization plus stable doc promotion timing.
- `Q10` remains open: when the detailed `attentional_v2` working design should be promoted from temp docs into stable mechanism docs.

## Open Decisions
- `OD-PRIVATE-LIBRARY-POST-RESCUE-GATE`
  - The live reviewed state has been restored, and the extra cleanup/review pass is now complete. The new follow-up packet summaries did not add any `keep` decisions, so the remaining human-owned question is whether promotion should stay closed until a more substantive backlog-clearing move is chosen.
- `OD-BENCHMARK-SIZE`
  - Is the current benchmark family already large enough for high-confidence cross-mechanism judgment, or should the benchmark expand before any default-cutover decision?
- `Q10`
  - When should the detailed `attentional_v2` working design be promoted from temporary implementation docs into stable mechanism docs?

## Active Risks
- The new question-aligned private-library builder now keeps the live `v2` review-truth datasets as feedback input instead of overwriting them, but the new question-aligned outputs are still seed candidates rather than reviewed benchmark truth.
- Pre-fix parallel comparison artifacts can misassign case-to-output mappings, so partial outputs from the earlier round-3 reruns must be sanity-checked before they are treated as evidence.
- Malformed-JSON handling in the reading path can still terminate a bounded rerun after substantial partial output has already been written.
- Launching `run_registered_job.py` from a transient agent shell without the detached launcher can leave long-running jobs looking `abandoned` even when the wrapped command itself never raised a Python traceback.
- Judged rerun parent logs can look sparse while case workers are still making progress, so future health checks should look at per-case runtime files and local LLM traces rather than only the top-level job log.
- The completed detached two-case rerun used `--judge-mode none`, so its `tie: 2` aggregate can be mistaken for a real comparison result unless we keep the placeholder nature explicit.
- The managed source catalog now drives both intake and the current private-library supplement build on this checkout, but the first real scratch evidence says the next bottleneck is case quality rather than source-input plumbing.
- The first real scratch builder/controller runs were intentionally narrow: the earliest English baseline still yielded no `keep` outcomes, but the later quality-fix runs improved that materially; the remaining narrowness is now bilingual stability rather than the mere absence of `keep` results.
- The last bilingual English pair held source rows constant but still regenerated materially different audit judgments, so current bilingual widening is constrained by audit/adjudication reproducibility as well as by builder quality.
- The adjudication-v4 frozen-input pair removed same-input action drift, but the broader English-only versus broader bilingual v4 runs still show `source_input_drift = 0`, `audit_input_drift = 5`, and `action_drift = 3` on the shared English case set.
- The fresh audit-pair compare artifact now shows `audit_input_drift = 0` but `primary_score_drift = 8`, so the remaining live instability is audit-stage model variance rather than builder/input drift.
- One remaining English outlier had invisible Unicode whitespace inside the emitted excerpt and selection-reason text even though the audit input fingerprints matched across runs; the builder-side normalization patch fixed that defect on the current builder path.
- The current strongest narrow callback result is `callbackfocusfix`, but the later tension follow-up showed that unchanged callback rows can still drift at audit/adjudication time even when the builder-side callback inputs stay effectively fixed.
- Historical compatibility paths under `state/library_sources/<language>/private/...` are now cataloged successfully, but they remain compatibility inputs rather than the intended future operator workflow.
- Historical `private_library` naming still appears in dataset ids, manifests, and older evidence files; future agents should treat that as compatibility naming rather than as a strategic instruction to optimize around public/private separation.
- Current public chapter/detail surfaces still carry section-shaped compatibility assumptions that may not fit the new mechanism directly.
- Route mismatches between frontend routes and backend-returned targets can still regress the canonical product path.
- Resume behavior remains sensitive to artifact placement under `reading-companion-backend/output/` and `reading-companion-backend/state/`.
- Benchmark confidence can look stronger than it really is if corpus growth, promotion, and reviewed-slice confidence gates drift apart.

## Active Task IDs
- `TASK-BENCH-BACKLOG-RESCUE`
- `TASK-DATASET-QUESTION-ALIGNED-CASE-CONSTRUCTION`
- `TASK-DATASET-FULL-AUTOMATION`

## Active Job IDs
- none

## Recommended Reading Path
1. `AGENTS.md`
2. `README.md`
3. `docs/current-state.md`
4. relevant child `AGENTS.md`
5. `docs/tasks/registry.md`
6. `docs/implementation/new-reading-mechanism/question-aligned-case-construction.md`
7. `reading-companion-backend/eval/review_packets/review_queue_summary.json`
8. `reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_bilingual_broader_callbackfocusfix_20260331.json`
9. `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_callbackfocusfix_20260331/closed_loop_benchmark_curation_summary.json`
10. `reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_bilingual_broader_tensionfocusfix_20260331.json`
11. `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_tensionfocusfix_20260331/closed_loop_benchmark_curation_summary.json`
12. `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_callbackpromptfix_20260331/closed_loop_benchmark_curation_summary.json`
13. `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_en_broader_callbackpromptfix_20260331__initial_review__closed_loop_full_smoke_en_broader_callbackpromptfix_20260331__20260331-042216/run_state.json`
14. `reading-companion-backend/state/dataset_build/build_runs/closed_loop_on_liberty_callbackpromptfix_20260331/closed_loop_benchmark_curation_summary.json`
15. `reading-companion-backend/state/job_registry/jobs/bgjob_en_chapter_core_rerun_round3_caseiso_judged_substantive_backup_20260331.json`
16. `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_caseiso_judged_substantive_backup_20260331/summary/aggregate.json`
17. `docs/implementation/new-reading-mechanism/private-library-promotion-round2.md`

## Machine-Readable Appendix
```json
{
  "updated_at": "2026-03-31T11:46:43Z",
  "last_updated_by": "codex",
  "active_task_ids": [
    "TASK-BENCH-BACKLOG-RESCUE",
    "TASK-DATASET-QUESTION-ALIGNED-CASE-CONSTRUCTION",
    "TASK-DATASET-FULL-AUTOMATION"
  ],
  "blocked_task_ids": [],
  "active_job_ids": [],
  "open_decision_ids": [
    "OD-PRIVATE-LIBRARY-POST-RESCUE-GATE",
    "OD-BENCHMARK-SIZE",
    "Q10"
  ],
  "detail_refs": [
    "docs/implementation/new-reading-mechanism/execution-tracker.md",
    "docs/implementation/new-reading-mechanism/private-library-promotion-round2.md",
    "docs/implementation/new-reading-mechanism/evaluation-question-map.md",
    "docs/implementation/new-reading-mechanism/evaluation-corpus-requirements.md",
    "docs/implementation/new-reading-mechanism/dataset-platform-closed-loop.md",
    "docs/implementation/new-reading-mechanism/question-aligned-case-construction.md",
    "reading-companion-backend/eval/attentional_v2/ingest_library_sources.py",
    "reading-companion-backend/tests/test_source_intake.py",
    "reading-companion-backend/state/dataset_build/source_intake_runs/bootstrap_existing_sources_20260330.json",
    "reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py",
    "reading-companion-backend/tests/test_private_library_supplement.py",
    "reading-companion-backend/state/dataset_build/build_runs/scratch_validation_en_qualityfix_20260330/build_summary.json",
    "reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py",
    "reading-companion-backend/tests/test_closed_loop_benchmark_curation.py",
    "reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_qualityfix_20260330/closed_loop_benchmark_curation_summary.json",
    "reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_qualityfix_20260330/closed_loop_benchmark_curation_summary.json",
    "reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_qualityfix_20260330/closed_loop_benchmark_curation_summary.json",
    "reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_paratextfix_20260330/closed_loop_benchmark_curation_summary.json",
    "reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_selectionfix_20260330/closed_loop_benchmark_curation_summary.json",
    "reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_selectionfix_20260330/closed_loop_benchmark_curation_summary.json",
    "reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_auditcoherencefix_20260330/closed_loop_benchmark_curation_summary.json",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_zh_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_selectionfix_20260330__initial_review__closed_loop_full_smoke_bilingual_selectionfix_20260330/llm_review_report.md",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_paratextfix_20260330__initial_review__closed_loop_full_smoke_bilingual_paratextfix_20260330/llm_review_report.md",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_selectionfix_20260330__initial_review__closed_loop_full_smoke_bilingual_selectionfix_20260330/llm_review_report.md",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_broader_selectionfix_20260330__initial_review__closed_loop_full_smoke_bilingual_broader_selectionfix_20260330/llm_review_runs/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_broader_selectionfix_20260330__initial_review__closed_loop_full_smoke_bilingual_broader_selectionfix_20260330__llm_review__20260330-121645/report.md",
    "reading-companion-backend/eval/attentional_v2/run_case_design_audit.py",
    "reading-companion-backend/tests/test_case_design_audit.py",
    "reading-companion-backend/state/job_registry/jobs/bgjob_en_chapter_core_rerun_round3_caseiso_judged_followup_20260330.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_en_chapter_core_rerun_round3_caseiso_judged_followup_20260330.log",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_en_broader_auditpair_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_en_broader_auditpair_20260331.log",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_bilingual_broader_auditpair_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_bilingual_broader_auditpair_20260331.log",
    "reading-companion-backend/eval/attentional_v2/compare_case_audit_runs.py",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_en_broader_auditcontractv2_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_en_broader_auditcontractv2_20260331.log",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_bilingual_broader_auditcontractv2_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_bilingual_broader_auditcontractv2_20260331.log",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_en_broader_auditcontractv3_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_en_broader_auditcontractv3_20260331.log",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_bilingual_broader_auditcontractv3_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_bilingual_broader_auditcontractv3_20260331.log",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_en_broader_auditconsensusv3_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_en_broader_auditconsensusv3_20260331.log",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_bilingual_broader_auditconsensusv3_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_bilingual_broader_auditconsensusv3_20260331.log",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_en_broader_auditcoherencefix_repeat_20260330.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_en_broader_auditcoherencefix_repeat_20260330.log",
    "reading-companion-backend/state/job_registry/jobs/bgjob_en_chapter_core_rerun_round3_parallel_caseiso_judged_20260329.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_en_chapter_core_rerun_round3_parallel_caseiso_judged_20260329.log",
    "reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_20260329/summary/report.md",
    "reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_20260329/summary/aggregate.json",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_en_followup_after_recovery_20260329/dataset_review_pipeline_summary.json",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_zh_followup_after_recovery_20260329/dataset_review_pipeline_summary.json",
    "reading-companion-backend/state/job_registry/jobs/bgjob_en_chapter_core_rerun_round3_parallel_caseiso_detached_20260329_125043.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_en_chapter_core_rerun_round3_parallel_caseiso_detached_20260329_125043.log",
    "reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_detached_20260329_125043/summary/report.md",
    "reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_detached_20260329_125043/summary/aggregate.json",
    "reading-companion-backend/state/job_registry/jobs/bgjob_en_chapter_core_rerun_round3_parallel_20260329.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_en_chapter_core_rerun_round3_parallel_20260329.log",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_en_recovery_20260329/dataset_review_pipeline_summary.json",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_zh_recovery_20260329/dataset_review_pipeline_summary.json",
    "reading-companion-backend/state/job_registry/jobs/bgjob_en_chapter_core_rerun_round3_caseiso_judged_substantive_backup_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_en_chapter_core_rerun_round3_caseiso_judged_substantive_backup_20260331.log",
    "reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_caseiso_judged_substantive_backup_20260331/summary/report.md",
    "reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_caseiso_judged_substantive_backup_20260331/summary/aggregate.json",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_en_broader_callbackpromptfix_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_en_broader_callbackpromptfix_20260331.log",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_en_broader_adjudicationv4_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_en_broader_adjudicationv4_20260331.log",
    "reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_adjudicationv4_20260331/closed_loop_benchmark_curation_summary.json",
    "reading-companion-backend/state/job_registry/jobs/bgjob_closed_loop_bilingual_broader_adjudicationv4_20260331.json",
    "reading-companion-backend/state/job_registry/logs/bgjob_closed_loop_bilingual_broader_adjudicationv4_20260331.log",
    "reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_broader_adjudicationv4_20260331/closed_loop_benchmark_curation_summary.json",
    "reading-companion-backend/eval/attentional_v2/compare_case_audit_runs.py",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330__initial_review__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330/llm_review_runs/llm_review__20260330-174858__ae50caff2084/summary.json",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330__initial_review__closed_loop_full_smoke_en_broader_compactadjudication_repeat_20260330/llm_review_runs/llm_review__20260330-175048__ae50caff2084/summary.json"
  ],
  "truth_refs": [
    "docs/source-of-truth-map.md",
    "docs/product-overview.md",
    "docs/backend-reading-mechanism.md",
    "docs/backend-reader-evaluation.md",
    "docs/runtime-modes.md",
    "docs/tasks/registry.json"
  ]
}
```
