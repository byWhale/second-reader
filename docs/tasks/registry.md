# Task Registry

Purpose: provide the canonical workspace task index for agent switching, routing, and traceability.
Use when: choosing what to work on next, recovering a task without chat history, or checking blockers, evidence, and linked truth docs.
Not for: full tracker detail, long-form design rationale, or mutable runtime job state.
Update when: task status, priority, blockers, decision refs, job refs, evidence refs, or next actions change.

This document is the human-readable companion to `docs/tasks/registry.json`.

Last updated: `2026-04-16T00:22:45Z`

## Status Values
- `active`
- `blocked`
- `queued`
- `waiting`
- `parked`
- `done`
- `cancelled`

## Active

### `TASK-USER-LEVEL-SELECTIVE-V1` — Replace the active local/user-level benchmark with the note-aligned selective package
- Status: `active`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/backend-reader-evaluation.md`
- Next: keep the new active local/user-level pointer on `user-level selective v1` and treat the older `excerpt surface v1.1` line as historical / superseded evidence only.
  - landed builder:
    - `reading-companion-backend/eval/attentional_v2/user_level_selective_v1.py`
  - landed runner:
    - `reading-companion-backend/eval/attentional_v2/run_user_level_selective_comparison.py`
  - active split manifest:
    - `reading-companion-backend/eval/manifests/splits/attentional_v2_user_level_selective_v1_draft.json`
  - active dataset package:
    - `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1`
  - current package truth:
    - `5` reading segments
    - `203` note cases
    - `nawaer_baodian_private_zh` is now included after repairing the library-notes alignment fallback and re-registering its managed notes asset
    - every note case now has `segment_source_v1` char-span slices; this is the strict matching coordinate for `Selective Legibility`
  - active metric:
    - `Selective Legibility` only
    - count `exact_match + focused_hit` as note recall
    - keep `incidental_cover` supporting-only
    - candidate retrieval must use source-span overlap, not string similarity or semantic similarity
    - broad semantic-segment fallback spans are judge-only candidates and never auto-count as exact note recall
  - next evaluation move:
    - the first valid strict source-span judged run is now active:
      - job id:
        - `bgjob_user_level_selective_v1_rejudge_reuse_20260416`
      - run id:
        - `attentional_v2_user_level_selective_v1_rejudge_reuse_20260416`
      - auto-recovery watchdog:
        - `bgjob_job_registry_auto_recovery_watchdog_20260416`
      - execution posture:
        - reuse completed reading outputs from the current run on relaunch, then from `retry2` and `retry1`
        - re-score all reusable shards under the strict source-span contract
        - rerun only the incomplete `attentional_v2` reading shards for `mangge_zhi_dao_private_zh` and `xidaduo_private_zh`
    - execution is now split by `segment x mechanism`, so `attentional_v2` and `iterator_v1` run as independent shards instead of serializing inside one per-book shard
    - the first mechanism-parallel attempt is preserved as failed evidence rather than overwritten:
      - `bgjob_user_level_selective_v1_judged_parallel_20260414`
      - failed because shard-scoped runs were still evaluating note cases from other segments, causing `KeyError` during merge-stage note-case evaluation
    - the first retry is also preserved as failed evidence rather than overwritten:
      - `bgjob_user_level_selective_v1_judged_parallel_retry1_20260415`
      - failed after the code bug was fixed because `7 / 10` shards still died on provider-side timeout / quota-cooldown / `520` / `529` instability
    - invalidated retry2 is preserved only as bug-diagnostic evidence:
      - `bgjob_user_level_selective_v1_failed_shards_retry2_20260415`
      - stopped after discovering that the runner admitted candidates by text similarity rather than strict source-span overlap
      - do not use retry2 results as mechanism evidence
    - use the new parallel orchestrator:
      - `reading-companion-backend/scripts/orchestrate_user_level_selective_eval.py`
- Jobs:
  - `bgjob_user_level_selective_v1_rejudge_reuse_20260416` (`running`)
  - `bgjob_job_registry_auto_recovery_watchdog_20260416` (`running`)

### `TASK-ATTENTIONAL-V2-STRUCTURAL-REWORK` — Execute the post-Phase-9 structural rework of `attentional_v2`
- Status: `active`
- Lane: `mechanism_runtime`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/attentional_v2_structural_rework_plan.md`
- Next: continue implementation from the new post-Phase-9 structural rework plan:
  - keep the work under the existing `attentional_v2` mechanism key rather than minting `attentional_v3`
  - treat this plan as backend-only
  - keep the existing frontend lane active in parallel under `TASK-V2-NATIVE-READING-PRESENTATION`
  - `Phase A` is now landed:
    - trigger output no longer suppresses formal正文 reading
    - the live control skeleton is now `navigate.unitize + read + navigate.route`
    - span authority now matches the exact chosen unit
  - `Phase B` is now landed:
    - `read` now owns the authoritative current-unit packet on the live path
    - the live runner now builds bounded carry-forward context and allows bounded `active recall / look-back` supplementation
    - raw reaction truth now comes directly from `read`, with mechanism-private `read_audit` records for context use
  - `Phase C.1` is now landed:
    - live prompt inputs now flow through a bounded internal `state_packet.v1` layer
    - `navigate.unitize` now receives a small `navigation_context`
    - `read` now receives a packetized read context that explicitly separates continuity capsule, working-state digest, reflective frame, active focus, and anchor-bank digest
    - persisted runtime files and public/frontend compatibility surfaces remain unchanged
  - `Phase C.2` is now landed as the first state-territory slice:
    - live state packets now derive a bounded `concept_digest` from the current `motif_index + unresolved_reference_index`
    - live state packets now derive a bounded `thread_digest` from the current `trace_links + unresolved_reference_index`
    - `navigate.unitize` and `read` now both receive those small concept/thread digests without changing persisted runtime files or public surfaces
  - `Phase C.3` is now landed:
    - new runs now treat `working_state / concept_registry / thread_trace / reflective_frames / anchor_bank` as the primary runtime and checkpoint truth
    - old `working_pressure / anchor_memory / reflective_summaries` were demoted to legacy load/projection territory during the cutover
    - `active_recall` now exposes first-class `concepts` and `threads` from the new state layers
    - checkpoint/resume temporarily accepted both old and new state territory during the cutover, while newly written checkpoints already used only the new primary keys
  - `Phase C.4` is now landed:
    - sentence-intake / bridge / slow-cycle now consume and write the new primary state layers directly
    - the live runner no longer projects new state back into `working_pressure / anchor_memory / reflective_summaries` to execute helpers
    - live runtime loading and resume now reject pre-`Phase C.3` runtime directories and checkpoints
    - public/frontend compatibility surfaces remain unchanged
  - `Phase D` is now landed:
    - `read` now supports a budget-bounded multi-step supplemental recall loop instead of a single extra pass
    - runtime state and full checkpoints now persist a lightweight `continuation capsule` with rehydration entrypoints
    - warm resume now restores the latest usable continuation capsule together with new-format runtime/checkpoint state
    - `look_back` now resolves one bounded earlier source span, and `read_audit` now records per-step supplemental activity plus stop reasons
  - next define the post-Phase-D follow-up:
    - review whether slower compaction, reflective promotion, or other continuity polish should become the next bounded slice
    - keep `knowledge_activations` narrowed to helper territory unless a later explicit design pass changes that rule
- Post-Phase-D evaluation posture:
  - the April 12 post-Phase-D smoke is finished and the April 13 targeted judged validation is also finished
  - completed judged runs:
    - `attentional_v2_post_phase_d_longspan_judged_20260413`
    - `attentional_v2_post_phase_d_excerpt_regression_20260413`
  - parent job id:
    - `bgjob_post_phase_d_parallel_judged_eval_retry2_20260413`
  - top-line comparative outcome:
    - `excerpt`:
      - prior formal `attentional_v2_excerpt_surface_v1_1_judged_20260406`
      - current `attentional_v2_post_phase_d_excerpt_regression_20260413`
      - `selective_legibility` changed from `27 / 21 / 11` to `24 / 24 / 11`
      - `insight_and_clarification` changed from `19 / 16 / 8` to `15 / 21 / 7`
    - `long-span`:
      - prior formal `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407`
      - current `attentional_v2_post_phase_d_longspan_judged_20260413`
      - `coherent_accumulation` changed from `2 / 5` to `3 / 4` (`attentional_v2 / iterator_v1`)
      - `insight_and_clarification` changed from `2 / 4 / 1` to `1 / 5 / 1` (`attentional_v2 / iterator_v1 / tie`)
  - current audit direction:
    - treat the next durable output as the cross-run comparative audit set rather than another rerun
    - use these new evidence docs as the audit entrypoint:
      - `reading-companion-backend/docs/research/attentional_v2_post_phase_d_eval_comparative_audit_20260414.md`
      - `reading-companion-backend/docs/research/attentional_v2_post_phase_d_eval_comparative_audit_20260414_longspan_appendix.md`
      - `reading-companion-backend/docs/research/attentional_v2_post_phase_d_eval_comparative_audit_20260414_excerpt_appendix.md`
  - current interpretation constraint:
    - the key hard signal is not only winner movement but `attentional_v2` evidence-density collapse
    - excerpt average matched reactions dropped from `7.0` to `1.0`
    - long-span average matched reactions dropped from `19.71` to `2.29`
  - no active background eval jobs remain in the registry
- Archived diagnostic attempts:
  - `bgjob_value_of_others_ch8_debug_trace_20260413` (`failed`, archived after fixing registry-isolation bug in the launcher)
  - `bgjob_value_of_others_ch8_debug_trace_retry1_20260413` (`failed`, archived after verifying isolated registry load but hitting separate-key `MiniMax-M2.7` plan rejection)
- Evidence addendum:
  - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_post_phase_d_longspan_smoke_20260412/diagnostics/value_of_others_abnormal_call_snapshot_20260413.md`
  - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_post_phase_d_longspan_smoke_20260412/diagnostics/value_of_others_progress_and_latency_check_20260413.md`
  - `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_value_of_others_ch8_debug_legacykey_20260413/analysis/registry_snapshot.json`

### `TASK-V2-NATIVE-READING-PRESENTATION` — Redesign the routed reading surfaces around chapter text and anchored reactions
- Status: `active`
- Lane: `migration`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/phase9-compat-cutover-roadmap.md`
- Next: keep `iterator_v1` section-first presentation in compatibility-only posture and continue the V2-native frontend lane from the new truth baseline. The first bounded truth/visibility slice is now landed and browser-validated:
  - overview fixes completed:
    - contradictory live status labels on `/books/:id`
    - false-empty recent trail when `recent_reactions` exists but mindstream history is sparse
    - live V2 overview chips for:
      - `reading_locus`
      - `move_type`
      - `active_reaction_id`
  - source-reader fixes completed:
    - honest slow-loading message
    - explicit missing-source state
    - explicit timeout/failure state instead of indefinite `Loading source EPUB...`
  - lifecycle/status-truth fixes completed:
    - stale orphan runtime snapshots now project to `paused` instead of fake live `analyzing`
    - routed bookshelf and overview now consume additive `status_reason`
    - paused stale/interrupted books now render last-known reading position honestly
    - resume CTA now stays hidden when `resume_available = false`
  - next redesign the chapter and marks surfaces around anchors and live thought lineage, with these page roles fixed:
    - `/books/:id/chapters/:chapterId` is the main chapter reading scene and default return-to-context page
    - `/marks` is the saved-reaction list plus jump-back surface, not the main reading scene
  - do not open a separate cleanup-only wave for V1 display concepts before this lane
- Jobs: none

## Parked

### `TASK-ATTENTIONAL-V2-NARROW-REPAIR-V1` — Run the bounded local-anchor and callback-bridge repair loop on `attentional_v2`
- Status: `parked`
- Lane: `mechanism_eval`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`
- Next: the April 7 retry landed new `nodes.py` / `prompts.py` / `runner.py` behavior plus the long-span harness support in `run_accumulation_comparison.py`, and the targeted tests all passed. The repair gate run on `attentional_v2_excerpt_micro_slice_v1_smoke_excerpt_repair_laneA_retry1_20260407` finished cleanly, but its judged stage regressed against the April 5 micro-slice baseline. Keep the known misses explicit, but do not reopen this repair lane by default while the product/demo decision is using the completed excerpt formal run as good-enough evidence and long-span smoke is the active priority.
- Jobs: none

### `TASK-RUNTIME-VIABILITY-GATES` — Keep runtime viability and non-mainline comparison lanes paused under the reduced eval scope
- Status: `parked`
- Lane: `mechanism_eval`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`
- Next: reuse the existing runtime-viability and durable-trace evidence; do not relaunch those lanes unless one of the three kept north-star dimensions later requires them or the cost posture changes explicitly
- Jobs:
  - `bgjob_durable_trace_reentry_gate_20260401` (`failed`)
  - `bgjob_durable_trace_reentry_gate_parallel3_20260401` (`completed`)
  - `bgjob_durable_trace_reentry_gate_personal_serial_20260401` (`abandoned`)
  - `bgjob_runtime_viability_gate_20260401` (`completed`)
  - `bgjob_runtime_viability_gate_serialfix_20260401` (`completed`)

## Waiting

### `TASK-DATASET-QUESTION-ALIGNED-CASE-CONSTRUCTION` — Build question-aligned case construction for evaluation datasets
- Status: `waiting`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`
- Next: keep the landed builder available as support infrastructure, but do not open a new general builder wave by default now that the current decisive eval lanes are resolved; broader construction should resume only if later regression work exposes a concrete blocker or if one explicitly scoped audit-stage-only reproducibility pass is requested
- Jobs:
  - `bgjob_closed_loop_en_broader_callbackpromptfix_20260331` (`completed`)
  - `bgjob_closed_loop_zh_callbacklookback_20260330` (`completed`)
  - `bgjob_closed_loop_zh_callbackpriorcontext_20260330` (`completed`)
  - `bgjob_closed_loop_zh_cueguard_20260330` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackbridgefix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackcontentfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackinferencefix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackfocusfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_tensionfocusfix_20260331` (`completed`)
  - `bgjob_callbackslice_auditv4_packet_20260331` (`failed`)
  - `bgjob_callbackslice_auditv4_packet_retry_quota_20260331` (`completed`)
  - `bgjob_callbackslice_probeonly_20260331` (`completed`)
  - `bgjob_callbackslice_auditrerun_20260331` (`completed`)

### `TASK-DATASET-FULL-AUTOMATION` — Make dataset building fully automated as one closed build-review-refine loop
- Status: `waiting`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`
- Next: keep the bounded controller scratch-safe and reusable, but do not widen automation by default now that the current decisive mechanism-eval lane is closed; with current model cost pressure, do not spend on non-mainline comparison support loops unless later work needs one explicitly scoped audit-stage-only reproducibility pass or another concrete support-lane unblocker
- Jobs:
  - `bgjob_closed_loop_en_broader_callbackpromptfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackpromptfix_20260331` (`failed`)
  - `bgjob_callbackslice_auditv4_packet_20260331` (`failed`)
  - `bgjob_callbackslice_auditv4_packet_retry_quota_20260331` (`completed`)
  - `bgjob_callbackslice_probeonly_20260331` (`completed`)
  - `bgjob_callbackslice_auditrerun_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackfocusfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_tensionfocusfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackinferencefix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackcontentfix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_callbackbridgefix_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_whitespacefix_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_whitespacefix_20260331` (`completed`)
  - `bgjob_closed_loop_en_henry_whitespacefix_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_auditconsensusv3_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditconsensusv3_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_auditcontractv3_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditcontractv3_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_auditcontractv2_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditcontractv2_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_auditpair_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditpair_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_adjudicationv4_20260331` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_adjudicationv4_20260331` (`completed`)
  - `bgjob_closed_loop_en_broader_compactadjudication_20260330` (`completed`)
  - `bgjob_closed_loop_en_broader_compactadjudication_repeat_20260330` (`failed`)
  - `bgjob_closed_loop_en_broader_compactadjudication_repeat_resume_20260330` (`completed`)
  - `bgjob_packet_adjudication_probe_en_compactrepeat_20260330` (`completed`)
  - `bgjob_packet_adjudication_probe_en_compactrepeat_compactauditv2_20260330` (`completed`)
  - `bgjob_closed_loop_en_broader_auditsemanticretry_20260330` (`completed`)
  - `bgjob_closed_loop_en_broader_auditcoherencefix_repeat_20260330` (`completed`)
  - `bgjob_closed_loop_bilingual_broader_auditcoherencefix_20260330` (`completed`)

## Queued

### `TASK-FE-SECTION-RETIREMENT` — Retire section-first chapter/detail and marks surfaces
- Status: `queued`
- Lane: `migration`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`
- Blocked by: `TASK-V2-NATIVE-READING-PRESENTATION`
- Next: keep section-first compatibility fields and containers only as migration sidecars; start removal only after the V2-native overview, chapter, and marks surfaces are stable enough that the older presentation model is no longer needed for normal product use

## Done

### `TASK-ACCUMULATION-BENCHMARK-V1` — Build the bounded long-span window benchmark for `coherent_accumulation`
- Status: `done`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`
- Next: keep `attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407` as the durable long-span evidence bundle, treat the April 6 lane as diagnosed invalid harness evidence rather than mechanism evidence, and reopen long-span repair only if a future rerun reproduces bundle/probe materialization failure or schema-invalid judge collapse.
- Jobs:
  - `bgjob_accumulation_benchmark_v1_first_review_20260404` (`completed`)
  - `bgjob_accumulation_benchmark_v1_rejudged_first_review_20260404` (`completed`)
  - `bgjob_accumulation_benchmark_v1_repair_first_review_20260405` (`completed`)
  - `bgjob_accumulation_benchmark_v1_judged_20260406` (`completed`)
  - `bgjob_accumulation_smoke_pair_recovery_20260407` (`completed`)
  - `bgjob_accumulation_benchmark_v1_judged_rerun_20260407` (`completed`)
  - `bgjob_accumulation_value_of_others_iterator_v1_bundle_20260408` (`completed`)
  - `bgjob_accumulation_benchmark_v1_value_of_others_iterator_v1_recovery_20260408` (`completed`)

### `TASK-PHASE9-DECISIVE-EVAL` — Run the split-surface Phase 9 evaluation lanes
- Status: `done`
- Lane: `mechanism_eval`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`
- Next: keep `excerpt surface v1.1` as the current durable excerpt evidence bundle, keep the cleaned long-span rerun as the durable long-span evidence bundle, and do not reopen decisive eval reruns by default unless a later product question or regression reproduces a concrete blocker.
- Jobs:
  - `bgjob_human_notes_excerpt_smoke_light_20260404` (`completed`)
  - `bgjob_human_notes_guided_excerpt_eval_v1_judged_20260404` (`completed`)
  - `bgjob_human_notes_guided_excerpt_eval_v1_judged_personal_rerun_20260405` (`abandoned`)
  - `bgjob_human_notes_excerpt_parallel_smoke_20260405` (`abandoned`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_a_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_b_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_a_retry1_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_b_retry1_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_a_dualpool_recovery_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_b_dualpool_recovery_20260405` (`failed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_a_dualpool_recovery_retry2_20260405` (`abandoned`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_b_dualpool_recovery_retry2_20260405` (`abandoned`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_a_dualpool_recovery_retry3_20260405` (`completed`)
  - `bgjob_human_notes_excerpt_parallel_judged_shard_b_dualpool_recovery_retry3_20260405` (`completed`)
  - `bgjob_attentional_v2_excerpt_micro_slice_smoke_20260405` (`completed`)
  - `bgjob_attentional_v2_excerpt_micro_slice_judged_20260405` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_a_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_b_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_c_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_d_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_eval_orchestrator_unitready_retry1_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_smoke_supremacy_recovery_20260406` (`completed`)
  - `bgjob_accumulation_benchmark_v1_judged_20260406` (`completed`)

### `TASK-PHASE9-COMPAT-CUTOVER` — Finish Phase 9 through compatibility cutover and default-path readiness
- Status: `done`
- Lane: `migration`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/phase9-compat-cutover-roadmap.md`
- Next: keep `attentional_v2` as the default product deep-reading path, keep `iterator_v1` as the explicit fallback/legacy-resume path, and treat later V2-native frontend presentation plus section-first retirement as post-Phase-9 initiatives rather than as unfinished cutover scope.
- Jobs: none

### `TASK-RUNTIME-STALE-PAUSE-TRUTH` — Reconcile stale/interrupted reading truth across backend lifecycle state and routed frontend surfaces
- Status: `done`
- Lane: `migration`
- Priority: `high`
- Detail: `docs/backend-sequential-lifecycle.md`
- Next: keep `status_reason` as the additive explanation layer for paused/error-like runtime states, keep stale-orphan reconciliation in startup/runtime recovery instead of GET paths, and treat restart/rerun UX as a separate future task rather than as part of this truth fix.
- Jobs: none

### `TASK-DOC-Q10` — Decide when to promote `attentional_v2` working design into stable docs
- Status: `done`
- Lane: `documentation`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/open-questions.md`
- Next: keep `docs/backend-reading-mechanisms/attentional_v2.md` as the stable live-mechanism authority, and keep future unfinished migration/cutover work in the Phase 9 tracker instead of reopening this timing question.

### `TASK-BOOK-ANALYSIS-RETIREMENT-CLARITY` — Mark `book_analysis` as retired legacy capability and remove ambiguity from the live deep-reading path
- Status: `done`
- Lane: `documentation`
- Priority: `high`
- Detail: `docs/history/decision-log.md`
- Next: keep the public `/analysis/*` route prefix as compatibility naming for the live deep-reading workflow, keep the legacy `book_analysis` implementation only as marked compatibility debt, and avoid expanding it as if it were an active product lane again.
- Jobs: none

### `TASK-EXCERPT-SURFACE-V1.1` — Retune the next excerpt surface incrementally from the notes-guided freeze
- Status: `done`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/excerpt-surface-v1-1-draft.md`
- Next: keep `excerpt surface v1.1` frozen as historical / superseded evidence with its explicit `5`-case exception on `nawaer_baodian_private_zh__22`; do not use it as the active local/user-level benchmark pointer now that `user-level selective v1` has replaced that role.
- Jobs:
  - `bgjob_excerpt_surface_v1_1_smoke_shard_a_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_smoke_shard_b_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_eval_orchestrator_20260406` (`abandoned`)
  - `bgjob_excerpt_surface_v1_1_eval_orchestrator_reshard4_20260406` (`abandoned`)
  - `bgjob_excerpt_surface_v1_1_eval_orchestrator_unitready_20260406` (`failed`)
  - `bgjob_excerpt_surface_v1_1_eval_orchestrator_unitready_retry1_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_a_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_b_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_c_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_judged_shard_d_20260406` (`completed`)
  - `bgjob_excerpt_surface_v1_1_smoke_supremacy_recovery_20260406` (`completed`)

### `TASK-DATASET-HUMAN-NOTES-GUIDED-V1` — Land the isolated human-notes-guided dataset line from the 5 linked books
- Status: `done`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/human-notes-guided-dataset-v1-freeze-draft.md`
- Next: keep the completed reviewed freeze as historical source material that fed the later excerpt-surface and note-aligned user-level lines; do not treat this task's output as the active benchmark pointer by itself.
- Jobs:
  - `bgjob_human_notes_guided_dataset_v1_scratch_20260404` (`failed`)
  - `bgjob_human_notes_guided_dataset_v1_scratch_retry1_20260404` (`completed`)
  - `bgjob_human_notes_guided_dataset_v1_scratch_retry2_20260404` (`completed`)
  - `bgjob_human_notes_guided_dataset_v1_scratch_retry3_20260404` (`completed`)
  - `bgjob_human_notes_guided_dataset_v1_first_review_en_20260404` (`failed`)
  - `bgjob_human_notes_guided_dataset_v1_first_review_zh_20260404` (`failed`)
  - `bgjob_human_notes_guided_dataset_v1_first_review_en_retry1_20260404` (`failed`)
  - `bgjob_human_notes_guided_dataset_v1_first_review_en_retry2_20260404` (`completed`)
  - `bgjob_human_notes_guided_dataset_v1_first_review_zh_retry1_20260404` (`completed`)

### `TASK-PHASE9-CLUSTERED-BENCHMARK` — Freeze clustered benchmark v1 as the active Phase 9 evaluation surface
- Status: `done`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/clustered-benchmark-v1-draft.md`
- Next: keep the frozen clustered benchmark as the active Phase 9 evaluation surface, preserve the honest `reserve = 7 / 8` shortfall, and move back to decisive mechanism-eval rather than reopening builder widening by default
- Jobs:
  - `bgjob_clustered_benchmark_v1_first_review_en_20260403` (`completed`)
  - `bgjob_clustered_benchmark_v1_first_review_zh_20260403` (`completed`)
  - `bgjob_clustered_benchmark_v1_reserve_review_en_20260404` (`completed`)
  - `bgjob_clustered_benchmark_v1_reserve_review_zh_20260404` (`completed`)

### `TASK-BENCH-BACKLOG-RESCUE` — Apply the round-2 backlog-rescue decision from the modern supplement
- Status: `done`
- Lane: `dataset_growth`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/private-library-promotion-round2.md`
- Next: keep the recorded `hold_for_backlog_rescue` outcome in force, do not reopen promotion without genuinely new benchmark-strengthening evidence, and treat the completed gate review as the route-back-to-mainline checkpoint
- Jobs: none

### `TASK-BENCH-ROUND3-CLEANUP` — Finish private-library cleanup and write the round-2 promotion draft
- Status: `done`
- Lane: `dataset_growth`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`
- Next: use the landed round-2 draft plus the March 29 recovery summaries as the source of truth for the next dataset-growth move
- Jobs: none

### `TASK-BENCH-PROMOTION-ROUND2` — Decide the next benchmark-promotion move from the modern supplement
- Status: `done`
- Lane: `dataset_growth`
- Priority: `medium`
- Detail: `docs/implementation/new-reading-mechanism/private-library-promotion-round2.md`
- Next: keep the recorded `hold_for_backlog_rescue` decision in force until a human explicitly reopens the post-recovery gate discussion
- Jobs: none

### `TASK-MECH-EN-RERUN` — Run the focused English round-3 narrative/reference rerun
- Status: `done`
- Lane: `mechanism_eval`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`
- Next: treat the completed backup-tier substantive rerun as evidence only; preserve the `walden` strength, keep the `up_from_slavery` chapter-arc weakness explicit, and do not launch default-cutover or promotion work automatically
- Jobs:
  - `bgjob_en_chapter_core_rerun_round3_caseiso_judged_followup_20260330` (`completed`)
  - `bgjob_en_chapter_core_rerun_round3_caseiso_judged_substantive_backup_20260331` (`completed`)

### `TASK-AGENT-SWITCHING-SYSTEM` — Land the repo-first agent-switching memory system
- Status: `done`
- Lane: `docs_tooling`
- Priority: `high`
- Detail: `docs/source-of-truth-map.md`
- Next: keep `docs/current-state.md` and `docs/tasks/registry.*` updated whenever live work changes

### `TASK-DATASET-SOURCE-GOVERNANCE` — Make source-book intake and intermediate artifacts clear and durable
- Status: `done`
- Lane: `dataset_platform`
- Priority: `high`
- Detail: `docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`
- Next: keep using the managed inbox plus source catalog as the source of truth for future book additions, and treat public/private only as compatibility metadata instead of a primary workflow branch
- Jobs: none
