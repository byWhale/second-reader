# New Reading Mechanism Execution Tracker

Purpose: track live implementation progress for the new reading mechanism across phases, code areas, docs, and evaluation work.
Use when: starting work, updating progress, or checking what is blocked next.
Not for: stable authority or long-form rationale.
Update when: status changes, blockers appear, or phases complete.

## Status Legend
- `planned`
- `in_progress`
- `blocked`
- `done`

## Current Summary
- Overall status:
  - `in_progress`
- Current phase:
  - `Phase 9: Migration, Stabilization, And Default-Cutover Readiness`
- Current blockers:
  - final end-to-end comparison still waits on:
    - actual evaluation runs over the tracked `v2` benchmark family
    - later frontend/API retirement of section-first chapter/detail and marks surfaces
    - later stable-doc promotion timing under `Q10`

## Phase Tracker
| Phase | Status | Exit gate |
| --- | --- | --- |
| Phase 0 - Planning and scope lock | `in_progress` | temp docs live, design coverage mapped, open questions recorded |
| Phase 1 - Runtime foundation and schemas | `done` | mechanism shell, core schemas, policy/version surfaces defined |
| Phase 2 - Sentence substrate and survey orientation | `done` | sentence-order substrate verified, survey artifacts working |
| Phase 3 - Deterministic intake, gates, and retrieval scaffolding | `done` | trigger pipeline, boundary nomination, candidate generation working |
| Phase 4 - Core interpretive loop | `done` | `zoom_read`, `meaning_unit_closure`, `controller_decision`, emission gate working |
| Phase 5 - Knowledge, memory, and bridge resolution | `done` | activation lifecycle, anchor relations, bridge resolution working |
| Phase 6 - Slow-cycle reasoning and historical integrity | `done` | promotion, reconsolidation, chapter consolidation working |
| Phase 7 - Persistence, checkpointing, and resume | `done` | warm/cold/reconstitution resume working |
| Phase 8 - Observability, evaluation, and shared-surface integration | `done` | event/checkpoint contracts and public adapters working |
| Phase 8.5 - Live runner integration | `done` | real parse/read path works through shared runtime, CLI, and async jobs |
| Phase 9 - Migration, stabilization, and default-cutover readiness | `in_progress` | acceptance ladder reached and stable docs promoted |

## Detailed Checklist

### Phase 0 - Planning And Scope Lock
- [x] Create repo-local temporary implementation workspace
- [x] Seed the source-block inventory from the Notion page
- [x] Create full-fidelity source mirror of the Notion design
- [x] Capture the Notion design into a repo-local implementation document
- [x] Create atomic requirement ledger
- [x] Create phased implementation plan
- [x] Create progress tracker
- [x] Create open-questions register
- [x] Create temporary decision log
- [x] Create validation matrix
- [x] Create stable-doc impact map
- [x] Decide target mechanism key and naming path
- [x] Audit current shared parsed-book substrate for sentence-level readiness
- [x] Resolve the shared `_runtime/` vs `_mechanisms/<mechanism_key>/` boundary
- [ ] Decide when stable `attentional_v2` doc should be updated from working design

### Phase 1 - Runtime Foundation And Schemas
- [x] Add new mechanism shell under shared runtime boundary
- [x] Define artifact layout under `_mechanisms/<mechanism_key>/`
- [x] Define `working_pressure` schema
- [x] Define `anchor_memory` schema
- [x] Define `reflective_summaries` schema
- [x] Define `knowledge_activations` schema
- [x] Define `move_history` and `reconsolidation_records` schemas
- [x] Define `reader_policy` schema and versioning
- [x] Define event envelope and checkpoint-summary schemas
- [x] Implement explicit state-operation helpers

### Phase 2 - Sentence Substrate And Survey Orientation
- [x] Audit sentence ids and locators in shared parsed-book substrate
- [x] Close parser or substrate gaps needed for sentence-order reading
- [x] Implement `book_survey`
- [x] Persist survey artifacts
- [x] Validate non-cheating survey constraints

### Phase 3 - Deterministic Intake, Gates, And Retrieval Scaffolding
- [x] Implement sentence ingest and mark-seen flow
- [x] Implement local buffer maintenance
- [x] Implement qualitative gate state machine
- [x] Implement candidate-boundary signals
- [x] Implement trigger ensemble
- [x] Emit trigger output schema
- [x] Implement deterministic `candidate_generation`
- [x] Implement bounded look-back source retrieval

### Phase 4 - Core Interpretive Loop
- [x] Implement `zoom_read`
- [x] Implement `meaning_unit_closure`
- [x] Implement `controller_decision`
- [x] Implement node handoff protocol
- [x] Implement `reaction_emission` gate
- [x] Add prompt manifests and prompt versioning for behavior-defining nodes

### Phase 5 - Knowledge, Memory, And Bridge Resolution
- [x] Implement knowledge-activation lifecycle
- [x] Implement knowledge-use mode switching
- [x] Implement search-policy state handling
- [x] Implement anchor retention and typed relations
- [x] Implement motif and unresolved-reference indexes
- [x] Implement `bridge_resolution`
- [x] Implement bridge-driven state updates

### Phase 6 - Slow-Cycle Reasoning And Historical Integrity
- [x] Persist mechanism-authored anchored reaction records as the source of truth
- [x] Implement `reflective_promotion`
- [x] Implement `reconsolidation`
- [x] Implement `chapter_consolidation`
- [x] Implement backward sweep
- [x] Implement cooling and carry-forward writes
- [x] Implement optional chapter reaction flow
- [x] Project persisted reactions into current compatibility reaction cards without making them primary truth
- [x] Preserve immutable `reaction_id` identity across reconsolidation and marks reuse

### Phase 7 - Persistence, Checkpointing, And Resume
- [x] Persist reading cursor and local continuity state
- [x] Persist durable tiered state and resume metadata
- [x] Implement `warm_resume`
- [x] Implement `cold_resume`
- [x] Implement `reconstitution_resume`
- [x] Implement checkpoint summaries at all required boundaries
- [x] Validate resume compatibility checks and fallbacks
  - Q7 policy is fixed:
    - `warm_resume`: reread `0` sentences
    - `cold_resume`: target `8`, hard cap `12`, chapter-local, expand backward to the start of the active meaning unit when needed
    - `reconstitution_resume`: target `24`, hard cap `30`, up to `3` meaning units, chapter-local

### Phase 8 - Observability, Evaluation, And Shared-Surface Integration
- [x] Emit required event types with version metadata
- [x] Emit checkpoint summaries with required fields
- [x] Resolve the standard-vs-debug observability split for shared vs private runtime artifacts
- [x] Wire standard checkpoint/resume events plus debug-only diagnostics scaffolding
- [x] Produce normalized eval artifacts
- [x] Add mechanism-integrity checks
- [x] Adapt new mechanism state into shared public surfaces
- [x] Verify compatibility with analysis-state and activity surfaces
- [x] Verify marks and reaction persistence compatibility
- [x] Land the first additive backend/public-contract refinements for mechanism-valued fields such as:
  - `primary_anchor`
  - `related_anchors`
  - reconsolidation lineage via `supersedes_reaction_id`
  - span-based or sentence-based live locus via `reading_locus`
  - current move type such as `advance`, `dwell`, `bridge`, or `reframe`

### Phase 8.5 - Live Runner Integration
- [x] Extract shared canonical parse/provisioning helpers under `src/reading_runtime/`
- [x] Extract shared sequential manifest/run-state helpers under `src/reading_runtime/`
- [x] Propagate optional `mechanism_key` through internal job launchers
- [x] Preserve mechanism selection across manual resume, auto-resume, and incompatible fresh rerun
- [x] Keep public HTTP routes unchanged while allowing backend-internal non-default mechanism rollout
- [x] Reject `attentional_v2 + book_analysis` explicitly
- [x] Implement `attentional_v2.parse_book` as a real parse-stage entrypoint
- [x] Implement `attentional_v2.read_book` as a real sequential runner
- [x] Register `AttentionalV2Mechanism()` as a built-in experimental mechanism
- [x] Keep `IteratorV1Mechanism()` as the default mechanism
- [x] Make shared aggregation and compatibility paths work without requiring `iterator_v1` `structure.json`
- [x] Validate the live runner through backend tests and `make contract-check`

### Phase 9 - Migration, Stabilization, And Default-Cutover Readiness
- [x] Freeze the evaluation-question map before dataset/corpus design begins
- [x] Freeze the corpus-requirements doc before requesting or screening books
- [x] Freeze the dataset-organization rule and family-first folder layout before populating benchmark packages
- [x] Separate cross-mechanism comparison questions from attentional-specific attribution questions and runtime/compatibility gate questions
- [x] Screen and fetch the first bilingual public-domain seed source pool into the durable local source library
- [x] Build tracked source-book, corpus, split, and local-ref manifests for the first bilingual public-domain seed corpus
- [x] Build the first seed dataset packages for chapter, runtime, excerpt, and compatibility work
- [x] Add the local-only evaluation-package mirror for private/copyrighted source books
- [x] Screen the first private Downloads EPUB pool, promote the selected books into `state/library_sources/`, and build the first local-only seed package mirror under `state/eval_local_datasets/`
- [x] Screen the public-first large bilingual candidate pool against the documented source-book requirements
- [x] Promote the selected public/open-access books into the tracked benchmark pool through the manifest-driven builder
- [x] Freeze the tracked `v2` source-book, corpus, split, and local-ref manifests for the combined public benchmark family
- [x] Run mechanism-integrity evaluation
- [x] Add the dataset-quality hardening workflow before broader semantic comparison work
- [x] Build an offline case-audit workflow for curated excerpt cases
- [x] Run the first machine-side case audit on the first weak-bucket review packet
- [x] Prepare the next English weak-case review packet
- [x] Run the machine-side case audit on the next English weak-case packet
- [x] Strengthen dataset status/provenance fields for later reviewed-slice freezing
- [x] Add a machine-readable active-packet queue summary for review operations
- [ ] Review and harden the weakest local buckets:
  - `callback_bridge`
  - `reconsolidation_later_reinterpretation`
- [ ] Review and harden the weakest Chinese local cases before trusting broader semantic comparison
- [ ] Freeze a reviewed local benchmark slice after case hardening
- [ ] Rerun mechanism-integrity on the reviewed local slice
- [ ] Run local-reading and span-trajectory evaluation
- [ ] Run durable-trace and re-entry evaluation
- [ ] Run runtime-viability evaluation
- [ ] Migrate the frontend and stable API away from section-first chapter/detail and marks surfaces once the section model is intentionally retired
- [x] Curate the first excerpt-case dataset packs for local/behind-the-mechanism questions
- [x] Curate the tracked `attentional_v2` benchmark datasets and the later chapter-level evaluation corpus before any real end-to-end comparison
- [x] Curate the chapter corpus for cross-mechanism span/end-to-end comparison
- [x] Curate runtime/resume and persisted compatibility fixture packs for gate and migration audits
- [ ] Compare against `iterator_v1`
- [ ] Promote landed behavior into stable docs
- [ ] Record decision-bearing changes in history doc when needed
- [ ] Make explicit default-cutover decision

## Notes Log
- `2026-03-23`
  - Created the temporary implementation workspace and seeded the plan, tracker, and question log from the current Notion design plus the stable repo rules.
  - Added omission-control docs, a source-block inventory, and seed coverage rows so untracked design areas stay visible.
  - Completed the split source mirror and moved the ledger from source-block seed coverage into an initial atomic expansion layer.
  - Completed the Q2 substrate audit: the current shared `public/book_document.json` shape is paragraph-level, so Phase 2 must add a shared sentence layer before the new mechanism can rely on sentence-order traversal, bounded look-back, and precise source anchoring.
  - Resolved the Q3 runtime boundary: shared `_runtime/` is a thin compatibility shell, while `attentional_v2` keeps mechanism-authored core reading artifacts and private control machinery under `_mechanisms/attentional_v2/`.
  - Started Phase 1 implementation in code: added shared runtime-shell contracts and helpers, created the `attentional_v2` schema and storage scaffold, and wrote the concrete runtime artifact map for later phases.
  - Finished the remaining Phase 1 helper slice: added pure `attentional_v2` state-operation helpers for gate, pressure, anchor, reflective, activation, move, reconsolidation, and policy updates.
  - Landed the shared sentence substrate in code: canonical parse now writes chapter-level sentence inventories into `public/book_document.json`, sentence locators now carry character offsets, and older paragraph-only book documents are backfilled with sentence records when reloaded.
  - Synced the stable backend docs and history log so the shared substrate is now documented as paragraph-plus-sentence canonical truth rather than paragraph-only truth.
  - Completed the Phase 2 survey layer: `attentional_v2` now writes orientation-only `survey_map.json` and `revisit_index.json` artifacts from title, TOC, chapter boundaries, openings, closings, and structural pivots, with tests guarding the non-cheating boundary.
  - Completed the deterministic Phase 3 scaffold: added explicit `local_buffer` and `trigger_state` schemas, sentence-intake and gate helpers, and memory-first bounded look-back candidate generation with focused tests.
  - Completed the Phase 4 interpretive-node layer: added typed `zoom_read`, `meaning_unit_closure`, `controller_decision`, and `reaction_emission` nodes, wired the `zoom -> closure -> controller -> optional emission` handoff, and persisted node-level prompt manifests with explicit prompt versions.
  - Resolved Q6 and completed Phase 5: the mechanism now has a real knowledge-activation lifecycle, explicit rare-search policy handling, typed bridge judgment over deterministic candidates, and durable anchor-memory updates including relations, motif indexes, unresolved-reference indexes, and move-history writes.
  - Resolved Q5: durable visible thought will be persisted first as mechanism-authored anchored reaction truth, then projected into compatibility reaction cards for current chapter/API/marks surfaces; future top-layer/API refinements are now explicitly captured in the temp docs instead of only in chat.
  - Completed Phase 6: `attentional_v2` now has slow-cycle node contracts for `reflective_promotion`, `reconsolidation`, and `chapter_consolidation`, a durable `reaction_records.json` source of truth, append-and-link reconsolidation behavior, chapter-end carry-forward helpers, and a mechanism-private chapter-result compatibility projection that preserves original reaction truth while feeding current envelope fields.
  - Resolved Q7: Phase 7 resume reconstruction will stay bounded and chapter-local, with `warm_resume` rereading `0` sentences, `cold_resume` targeting `8` recent sentences with a `12`-sentence cap and meaning-unit backfill, and `reconstitution_resume` targeting `24` recent sentences with a `30`-sentence cap and up to `3` meaning units.
  - Completed Phase 7: `attentional_v2` now persists `local_continuity.json` and `resume_metadata.json`, writes full mechanism checkpoints plus shared checkpoint summaries, restores warm/cold/reconstitution resume state through the shared sentence substrate, and marks reconstructed hot state explicitly instead of pretending non-warm resume is warm.
  - Resolved Q4 and landed the first Phase 8 shared-surface slice: public schemas and backend aggregation now expose additive `reading_locus`, `primary_anchor`, `related_anchors`, `supersedes_reaction_id`, `move_type`, and runtime-shell-backed active reaction references while keeping `section_ref` / `segment_ref` as compatibility sidecars.
  - Recorded future migration work explicitly instead of leaving it implicit: the frontend and stable API still need a later intentional cut from section-first chapter/detail and marks surfaces toward chapter text plus anchored reactions as the primary model.
  - Resolved Q8 and landed the first observability split: shared runtime shell and checkpoint summaries now carry `observability_mode`, standard checkpoint/resume events now write to `_runtime/activity.jsonl`, and debug-only diagnostics now remain under `_mechanisms/attentional_v2/internal/diagnostics/events.jsonl`.
  - Recorded future Phase 8 work explicitly instead of leaving it implicit: once the live parse/read path exists, node-level observability still needs to be wired across the local loop, bridge cycle, and slow-cycle nodes before the phase can claim full live-run coverage.
  - Resolved Q9: the project now has a staged evaluation pack, explicit acceptance thresholds, and an explicit future task to curate the real `attentional_v2` benchmark datasets and chapter corpus before any meaningful end-to-end comparison or default-promotion discussion.
  - Landed the remaining current-scope Phase 8 evaluation slice in code: `attentional_v2` can now build and explicitly persist a normalized eval bundle from persisted artifacts, and it now has structural integrity checks over shared cursor resolution, anchored reaction ids/locators, reconsolidation links, Q7 resume-policy bounds, and compatibility projection fidelity.
  - Added the explicit Phase 8.5 live-runner workstream to reflect the real dependency chain more honestly: minimal runner wiring was not enough, so the project now tracks shared provisioning extraction, mechanism-key job propagation, real `attentional_v2` parse/read entrypoints, non-default experimental registration, and non-iterator compatibility aggregation as their own completed slice.
  - Completed Phase 8.5: `attentional_v2` now runs end to end through the shared runtime, CLI, and existing async job lifecycle; resume and incompatible fresh reruns preserve `mechanism_key`; the backend rejects legacy `book_analysis` for `attentional_v2` explicitly; and stable/temp docs now treat `attentional_v2` as experimental instead of design-only.
  - Added the explicit evaluation-question layer before dataset design: stable cross-mechanism questions now live in `docs/backend-reader-evaluation.md`, stable attentional-specific proof questions now live in `docs/backend-reading-mechanisms/attentional_v2.md`, and the temporary `evaluation-question-map.md` now records exactly which questions this implementation project still has to answer, including the cross-mechanism comparison work that remains part of the current `attentional_v2` job.
  - Added the corpus-requirements layer before book collection: `evaluation-corpus-requirements.md` now separates what the future data process can satisfy during curation from what the source books themselves must already satisfy, and it records the source-policy recommendation plus the concrete book-pool requirements for the first serious benchmark build.
  - Promoted source-book organization into the stable project docs: the workspace/backend/evaluation docs and backend agent guide now distinguish transient uploads, durable local source-library books, runtime book copies, and evaluation-package territory, and the history log now records that storage-boundary decision explicitly.
  - Froze the dataset-organization rule before population: stable docs now require a family-first dataset layout under `eval/datasets/`, the backend `eval` README now defines the package contract, the temp implementation docs now define the first bilingual `attentional_v2` package plan, and the dataset/manifests folder skeleton now exists on disk.
  - Built the first bilingual public-domain seed corpus locally under `state/library_sources/` from Project Gutenberg sources, then ran it through canonical parse and used that parsed substrate to generate tracked source manifests plus the first seed dataset packages under `reading-companion-backend/eval/`.
  - Important honesty note for later work: the seed chapter and runtime packages are directly grounded in parsed substrate, but the seed excerpt packages are still auto-extracted and require manual curation before benchmark promotion, while the compatibility package is still spec-level until live attentional runtime outputs are generated for those books.
  - Tightened the storage rule for private books: stable and temp docs now reserve `state/eval_local_datasets/` as the family-first local-only mirror for excerpt/chapter/runtime/compatibility packages derived from private books, while tracked manifests in `eval/manifests/` now point to both local source books and local package roots.
  - Screened the first private Downloads EPUB pool against the corpus rules, promoted `9` selected books into `state/library_sources/en/private/` and `state/library_sources/zh/private/`, recorded the full keep/reserve/reject screen in tracked source manifests, and built the first local-only private seed package mirror under `state/eval_local_datasets/`.
  - Curated the first benchmark-quality excerpt layer on top of the seed pool: the excerpt benchmark family now has both `storage_mode = tracked` and `storage_mode = local-only` packages, with explicit case-purpose metadata and a curated split manifest instead of relying on raw auto-extracted seed windows.
  - Important nuance for later evaluation work: the curated English excerpt family is now strong enough for first-pass local evaluation, but within the Chinese excerpt family the `tracked` slice is still intentionally thin because the current public-domain Chinese seed quality was much weaker than the manually added supplement, so later corpus work should expand public-safe Chinese sources if we want a larger tracked slice of that same benchmark family.
- `2026-03-24`
  - Completed the public-first large corpus expansion at the dataset-build layer: added a manifest-driven corpus builder plus validator, screened `24` new public/open-access candidates, promoted `12` of them, and froze the combined tracked public benchmark pool in `v2` manifests and dataset packages.
  - Landed the tracked `v2` bilingual benchmark family with:
    - `18` English chapter rows
    - `18` Chinese chapter rows
    - `36` English runtime fixtures
    - `36` Chinese runtime fixtures
    - `16` English curated excerpt cases
    - `16` Chinese curated excerpt cases
    - `36` shared compatibility fixtures
  - Closed the earlier Chinese tracked-curation gap enough for real evaluation work by expanding the public-source pool and allowing controlled normalization of structurally weak but text-valuable public Chinese sources into synthetic segmented EPUBs before screening.
  - Shifted the default next step for Phase 9 from corpus bootstrapping to actual evaluation execution; later book acquisition is now gap-filling only unless real evaluation evidence reveals a benchmark-coverage hole.
  - Ran the first full `mechanism_integrity` pass over the tracked curated `v2` excerpt packs with the new local benchmark harness. The authoritative run is `attentional_v2_integrity_v2_20260324-152539` under `reading-companion-backend/eval/runs/attentional_v2/`, with `32` cases, `0` structural failures, and judged averages of `text_groundedness 3.594`, `meaning_unit_quality 3.500`, `move_quality 3.500`, `reaction_quality 3.594`, and `case_fit 3.094`.
  - Important first-pass result: the benchmark layer is viable, but `attentional_v2` is not yet at the planned local acceptance line. The English slice is mixed-but-closer, the Chinese slice is clearly below target, and the weakest buckets are `callback_bridge` and `reconsolidation_later_reinterpretation`.
  - Important harness note: the first attempted judged run exposed a score-scale bug in the rubric prompt, so the earlier run with all-`1.0` averages is superseded. The authoritative first-pass result is the corrected run above, after fixing sentence-id ordering in structural checks and the rubric scale contract.
  - Important interpretation note for next work: every evaluated local case still chose `advance`, which suggests the excerpt harness is currently best at testing closure and anchored selectivity but still under-exercises meaningful `dwell` / `bridge` / `reframe` diversity. The next evaluation step should keep the current run result, but also refine bridge and reconsolidation case pressure before treating local move quality as mature evidence.
  - Landed the dataset-quality hardening workflow as executable project infrastructure rather than just a note: the stable evaluation docs now require dual diagnosis of mechanism problems versus dataset/harness problems, the backend agent guide now reminds future coding agents about that rule, and the backend now has packet-based export/import tooling for human review of benchmark cases without a frontend UI.
  - Promoted dataset-quality hardening into its own explicit Phase 9 work item. The project now treats benchmark-case review as a first-class task rather than a quiet background assumption, and the immediate recommendation is to harden the local excerpt slice before trusting broader semantic comparison work too much.
- `2026-03-25`
  - Generated the first real human-review packet for weak local hardening: `attentional_v2_zh_weak_buckets_round1` under `reading-companion-backend/eval/review_packets/pending/`. It contains the tracked Chinese `callback_bridge` and `reconsolidation_later_reinterpretation` cases from the curated `v2` excerpt family.
  - Ran the first machine-side case-design audit on that same packet at `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_zh_weak_buckets_round1__20260325-003459/`. Result: `0` factual failures, but only `1 keep`, `4 revise`, and `1 drop`, with low average bucket-fit / focus-clarity / excerpt-strength scores. The machine-side audit therefore agrees that the weakest local slice likely has real case-design problems, not only mechanism problems.
  - Generated the next English weak-case packet: `attentional_v2_en_weak_cases_round1` under `reading-companion-backend/eval/review_packets/pending/`. It contains the six non-pass English local cases from the first corrected `mechanism_integrity` run.
  - Ran the companion machine-side case audit on that English packet at `reading-companion-backend/eval/runs/attentional_v2/case_audits/attentional_v2_en_weak_cases_round1__20260325-004347/`. Result: `0` factual failures, `4 keep`, and `2 revise`, which suggests the English weak slice is stronger than the Chinese weak slice but still not clean enough to skip review entirely.
  - Strengthened the curated excerpt datasets for later reviewed-slice freezing: added baseline review/provenance metadata to both tracked curated `v2` excerpt packs, added `backfill_case_review_metadata.py`, and added `freeze_reviewed_dataset_slice.py` so later human-reviewed subsets can be frozen into explicit reviewed benchmark packages instead of being managed ad hoc.
  - Tightened the reviewed-slice state model before any human packet is imported: packet imports now distinguish `reviewed_active` from `needs_revision`, baseline review/provenance metadata has been backfilled across the tracked and local-only curated excerpt datasets, and a queue summary snapshot now lives under `reading-companion-backend/eval/review_packets/review_queue_summary.{json,md}` so the active hardening queue is visible without reconstructing it from chat.
  - The immediate next path is now concrete rather than implied:
    - review the active packet or packets
      - `attentional_v2_zh_weak_buckets_round1`
      - `attentional_v2_en_weak_cases_round1`
    - consult `reading-companion-backend/eval/review_packets/review_queue_summary.md` for the current packet queue and latest machine-side audit summaries
    - import the reviewed packet(s)
    - freeze the reviewed local slice
    - rerun `mechanism_integrity`
    - only then decide whether broader semantic comparison should proceed unchanged
