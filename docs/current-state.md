# Current State

Purpose: capture the canonical repo-local view of current project status for agent switching and human recovery.
Use when: onboarding a new coding agent, resuming work without chat history, or checking which initiative is current now.
Not for: long-form rationale, full historical detail, or session-only scratch notes.
Update when: the current objective, active tasks, blockers, active jobs, open decisions, risks, or recommended reading path change.

This file is authoritative for durable current status. Do not keep unique active-state information only in `docs/agent-handoff.md`.

Last verified: `2026-03-30T05:43:23Z`

## Current Objective
- Keep Phase 9 of the new reading mechanism project recoverable and decision-ready:
  - inspect the completed English two-case evidence rerun without converting it into an automatic mechanism or promotion decision
  - work from the recovered private-library local-only datasets rather than the stale seed-reset narrative
  - preserve the remaining benchmark-hardening backlog and human-owned gate decisions in repo-local state
- In parallel, keep the dataset-platform route moving from landing to evidence-driven refinement:
  - use the recovered managed source catalog on this checkout instead of treating missing-catalog recovery as the active blocker
  - use the real scratch builder/controller evidence to improve case quality and bilingual reproducibility before widening automation further

## Now
- Treat `attentional_v2` as experimental and `iterator_v1` as the current default mechanism.
- The English chapter-core retry-2 closeout is still the last completed comparison baseline:
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
- The review queue is empty again:
  - `reading-companion-backend/eval/review_packets/review_queue_summary.json`
  - `active_packet_count = 0`
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
    - callback selection now requires explicit backward-link markers instead of generic lexical overlap
    - anchored-reaction selection now rejects obvious reported-speech false positives
    - context-dependent fragment anchors are penalized instead of being treated as stable standalone cases
    - paratext / bibliographic windows are filtered out
    - weak profile-order filler candidates no longer outrank much stronger same-chapter opportunities during the primary auto-selection pass
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
        - the English packet payload was byte-identical to the previous bilingual rerun, yet LLM adjudication shifted from `keep = 2`, `revise = 2` to `revise = 4`, so review variability is now part of the stability problem
  - current interpretation:
    - English builder quality improved materially and remains clearly better than the first narrow-English baseline
    - Chinese builder quality also improved materially: it no longer selects pure front matter and can now produce at least one real prose `keep`
    - the next blocker for unattended widening is bilingual reproducibility, not intake plumbing:
      - remaining Chinese scene/bucket shaping still matters
      - packet adjudication variability on otherwise identical English packets now needs bounded diagnosis before we trust wider unattended loops
  - all bounded controller runs still stopped with summaries only:
    - no benchmark promotion, reviewed-slice freeze, runtime-viability, or default-cutover work was launched automatically
    - the live review queue is back to `active_packet_count = 0`
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
- Convert the completed judged rerun into one bounded mechanism repair plan:
  - preserve the `walden_205_en__10` single-axis threading behavior as a protected strength
  - inspect `up_from_slavery_public_en__10` for sparse chapter presence and ambiguous chapter-label trust rather than treating it as a generic local-density problem
- Use the cleanup follow-up summaries as the new benchmark-hardening truth:
  - the extra cleanup pass did not produce any `keep` decisions
  - the English `9` and Chinese `3` open cases were reaffirmed as `revise` / `drop` rather than promoted into `reviewed_active`
- Use the new managed intake layer for any future book additions instead of external `/BOOK` or `Downloads` roots:
  - drop books into `reading-companion-backend/state/library_inbox/`
  - use nested folders only for optional batch organization
  - run `make library-source-intake`
- Use the latest bilingual scratch evidence to stabilize case quality and reproducibility rather than adding new platform plumbing:
  - keep the English-only quality-fix evidence as the working proof that the builder improvements are real
  - finish the remaining Chinese shaping work so the selected excerpt stays on the stronger late-scene opportunity without residual edge noise
  - inspect the identical-English bilingual packet pair to decide how much of the remaining instability is LLM adjudication variability rather than construction quality
- Keep the bounded controller as the active automation surface, but defer wider unattended expansion until the bilingual route is more reproducible:
  - broader English and broader bilingual scratch widening should now happen only after the current Chinese/profile and adjudication-stability diagnosis is explicit
  - the multi-iteration unattended scheduler still remains after that stability pass, not before it
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
  - keep the review queue empty unless a deliberate new packet is created
- Prepare a human-owned post-cleanup gate review from the recovered counts, the two new follow-up packet summaries, and the still-open benchmark statuses.
- Keep benchmark promotion, reviewed-slice freezing, durable-trace, re-entry, runtime-viability, and any default-cutover decision paused until a human explicitly asks for them.

## Blocked
- Formal curated promotion from the modern private-library supplement remains paused until the remaining open cases are dispositioned and a human explicitly reopens the post-recovery gate discussion.
- Reviewed-slice freezing remains paused until a human explicitly chooses to freeze a slice.
- Durable-trace, re-entry, and runtime-viability remain intentionally queued until the failed rerun is dispositioned and the post-recovery benchmark gate becomes an explicit human-owned decision.
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
- Repeated bilingual packet adjudication over an identical English packet can still move materially between runs, so current bilingual widening is constrained by review reproducibility as well as by builder quality.
- Historical compatibility paths under `state/library_sources/<language>/private/...` are now cataloged successfully, but they remain compatibility inputs rather than the intended future operator workflow.
- Historical `private_library` naming still appears in dataset ids, manifests, and older evidence files; future agents should treat that as compatibility naming rather than as a strategic instruction to optimize around public/private separation.
- Current public chapter/detail surfaces still carry section-shaped compatibility assumptions that may not fit the new mechanism directly.
- Route mismatches between frontend routes and backend-returned targets can still regress the canonical product path.
- Resume behavior remains sensitive to artifact placement under `reading-companion-backend/output/` and `reading-companion-backend/state/`.
- Benchmark confidence can look stronger than it really is if corpus growth, promotion, and reviewed-slice confidence gates drift apart.

## Active Task IDs
- `TASK-BENCH-BACKLOG-RESCUE`
- `TASK-MECH-EN-RERUN`
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
6. `reading-companion-backend/state/job_registry/jobs/bgjob_en_chapter_core_rerun_round3_parallel_caseiso_judged_20260329.json`
7. `reading-companion-backend/state/job_registry/logs/bgjob_en_chapter_core_rerun_round3_parallel_caseiso_judged_20260329.log`
8. `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_20260329/summary/report.md`
9. `reading-companion-backend/eval/runs/attentional_v2/attentional_v2_vs_iterator_v1_chapter_core_en_round3_narrative_reference_repair_parallel_caseiso_judged_20260329/summary/aggregate.json`
10. `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_en_followup_after_recovery_20260329/dataset_review_pipeline_summary.json`
11. `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_zh_followup_after_recovery_20260329/dataset_review_pipeline_summary.json`
12. `reading-companion-backend/state/job_registry/jobs/bgjob_en_chapter_core_rerun_round3_parallel_caseiso_detached_20260329_125043.json`
13. `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_en_recovery_20260329/dataset_review_pipeline_summary.json`
14. `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_zh_recovery_20260329/dataset_review_pipeline_summary.json`
15. `docs/implementation/new-reading-mechanism/private-library-promotion-round2.md`
16. `docs/implementation/new-reading-mechanism/evaluation-question-map.md`
17. `docs/implementation/new-reading-mechanism/evaluation-corpus-requirements.md`
18. `docs/implementation/new-reading-mechanism/dataset-platform-closed-loop.md`
19. `docs/implementation/new-reading-mechanism/question-aligned-case-construction.md`
20. `reading-companion-backend/state/dataset_build/source_intake_runs/bootstrap_existing_sources_20260330.json`
21. `reading-companion-backend/state/dataset_build/build_runs/scratch_validation_en_qualityfix_20260330/build_summary.json`
22. `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
23. `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_en_broader_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
24. `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_qualityfix_20260330/closed_loop_benchmark_curation_summary.json`
25. `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_paratextfix_20260330/closed_loop_benchmark_curation_summary.json`
26. `reading-companion-backend/state/dataset_build/build_runs/closed_loop_full_smoke_bilingual_selectionfix_20260330/closed_loop_benchmark_curation_summary.json`
27. `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_zh_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_selectionfix_20260330__initial_review__closed_loop_full_smoke_bilingual_selectionfix_20260330/llm_review_report.md`
28. `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_paratextfix_20260330__initial_review__closed_loop_full_smoke_bilingual_paratextfix_20260330/llm_review_report.md`
29. `reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_selectionfix_20260330__initial_review__closed_loop_full_smoke_bilingual_selectionfix_20260330/llm_review_report.md`
30. `reading-companion-backend/eval/attentional_v2/build_private_library_supplement.py`
31. `reading-companion-backend/eval/attentional_v2/run_closed_loop_benchmark_curation.py`
32. `docs/source-of-truth-map.md` when you need to decide where durable information belongs

## Machine-Readable Appendix
```json
{
  "updated_at": "2026-03-30T05:43:23Z",
  "last_updated_by": "codex",
  "active_task_ids": [
    "TASK-BENCH-BACKLOG-RESCUE",
    "TASK-MECH-EN-RERUN",
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
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_zh_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_selectionfix_20260330__initial_review__closed_loop_full_smoke_bilingual_selectionfix_20260330/llm_review_report.md",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_paratextfix_20260330__initial_review__closed_loop_full_smoke_bilingual_paratextfix_20260330/llm_review_report.md",
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_excerpt_en_question_aligned_v1__scratch__closed_loop_full_smoke_bilingual_selectionfix_20260330__initial_review__closed_loop_full_smoke_bilingual_selectionfix_20260330/llm_review_report.md",
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
    "reading-companion-backend/eval/review_packets/archive/attentional_v2_private_library_cleanup_zh_recovery_20260329/dataset_review_pipeline_summary.json"
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
