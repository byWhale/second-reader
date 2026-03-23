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
  - `Phase 8: Observability, Evaluation, And Shared-Surface Integration`
- Current blockers:
  - observability split `Q8` is still open for standard-vs-debug event and checkpoint detail
  - evaluation-slice and threshold question `Q9` is still open before later comparison and promotion work

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
| Phase 8 - Observability, evaluation, and shared-surface integration | `in_progress` | event/checkpoint contracts and public adapters working |
| Phase 9 - Migration, stabilization, and default-cutover readiness | `planned` | acceptance ladder reached and stable docs promoted |

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
- [ ] Emit required event types with version metadata
- [ ] Emit checkpoint summaries with required fields
- [ ] Produce normalized eval artifacts
- [ ] Add mechanism-integrity checks
- [x] Adapt new mechanism state into shared public surfaces
- [x] Verify compatibility with analysis-state and activity surfaces
- [x] Verify marks and reaction persistence compatibility
- [x] Land the first additive backend/public-contract refinements for mechanism-valued fields such as:
  - `primary_anchor`
  - `related_anchors`
  - reconsolidation lineage via `supersedes_reaction_id`
  - span-based or sentence-based live locus via `reading_locus`
  - current move type such as `advance`, `dwell`, `bridge`, or `reframe`
- [ ] Migrate the frontend and stable API away from section-first chapter/detail and marks surfaces once the section model is intentionally retired

### Phase 9 - Migration, Stabilization, And Default-Cutover Readiness
- [ ] Run mechanism-integrity evaluation
- [ ] Run local-reading and span-trajectory evaluation
- [ ] Run durable-trace and re-entry evaluation
- [ ] Run runtime-viability evaluation
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
