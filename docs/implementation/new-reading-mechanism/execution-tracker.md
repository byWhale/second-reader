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
  - `Phase 1: Runtime Foundation And Schemas`
- Current blockers:
  - shared sentence-substrate schema not yet designed or implemented
  - public-surface adapter strategy not yet decided

## Phase Tracker
| Phase | Status | Exit gate |
| --- | --- | --- |
| Phase 0 - Planning and scope lock | `in_progress` | temp docs live, design coverage mapped, open questions recorded |
| Phase 1 - Runtime foundation and schemas | `in_progress` | mechanism shell, core schemas, policy/version surfaces defined |
| Phase 2 - Sentence substrate and survey orientation | `planned` | sentence-order substrate verified, survey artifacts working |
| Phase 3 - Deterministic intake, gates, and retrieval scaffolding | `planned` | trigger pipeline, boundary nomination, candidate generation working |
| Phase 4 - Core interpretive loop | `planned` | `zoom_read`, `meaning_unit_closure`, `controller_decision`, emission gate working |
| Phase 5 - Knowledge, memory, and bridge resolution | `planned` | activation lifecycle, anchor relations, bridge resolution working |
| Phase 6 - Slow-cycle reasoning and historical integrity | `planned` | promotion, reconsolidation, chapter consolidation working |
| Phase 7 - Persistence, checkpointing, and resume | `planned` | warm/cold/reconstitution resume working |
| Phase 8 - Observability, evaluation, and shared-surface integration | `planned` | event/checkpoint contracts and public adapters working |
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
- [ ] Implement explicit state-operation helpers

### Phase 2 - Sentence Substrate And Survey Orientation
- [x] Audit sentence ids and locators in shared parsed-book substrate
- [ ] Close parser or substrate gaps needed for sentence-order reading
- [ ] Implement `book_survey`
- [ ] Persist survey artifacts
- [ ] Validate non-cheating survey constraints

### Phase 3 - Deterministic Intake, Gates, And Retrieval Scaffolding
- [ ] Implement sentence ingest and mark-seen flow
- [ ] Implement local buffer maintenance
- [ ] Implement qualitative gate state machine
- [ ] Implement candidate-boundary signals
- [ ] Implement trigger ensemble
- [ ] Emit trigger output schema
- [ ] Implement deterministic `candidate_generation`
- [ ] Implement bounded look-back source retrieval

### Phase 4 - Core Interpretive Loop
- [ ] Implement `zoom_read`
- [ ] Implement `meaning_unit_closure`
- [ ] Implement `controller_decision`
- [ ] Implement node handoff protocol
- [ ] Implement `reaction_emission` gate
- [ ] Add prompt manifests and prompt versioning for behavior-defining nodes

### Phase 5 - Knowledge, Memory, And Bridge Resolution
- [ ] Implement knowledge-activation lifecycle
- [ ] Implement knowledge-use mode switching
- [ ] Implement search-policy state handling
- [ ] Implement anchor retention and typed relations
- [ ] Implement motif and unresolved-reference indexes
- [ ] Implement `bridge_resolution`
- [ ] Implement bridge-driven state updates

### Phase 6 - Slow-Cycle Reasoning And Historical Integrity
- [ ] Implement `reflective_promotion`
- [ ] Implement `reconsolidation`
- [ ] Implement `chapter_consolidation`
- [ ] Implement backward sweep
- [ ] Implement cooling and carry-forward writes
- [ ] Implement optional chapter reaction flow

### Phase 7 - Persistence, Checkpointing, And Resume
- [ ] Persist reading cursor and local continuity state
- [ ] Persist durable tiered state and resume metadata
- [ ] Implement `warm_resume`
- [ ] Implement `cold_resume`
- [ ] Implement `reconstitution_resume`
- [ ] Implement checkpoint summaries at all required boundaries
- [ ] Validate resume compatibility checks and fallbacks

### Phase 8 - Observability, Evaluation, And Shared-Surface Integration
- [ ] Emit required event types with version metadata
- [ ] Emit checkpoint summaries with required fields
- [ ] Produce normalized eval artifacts
- [ ] Add mechanism-integrity checks
- [ ] Adapt new mechanism state into shared public surfaces
- [ ] Verify compatibility with analysis-state and activity surfaces
- [ ] Verify marks and reaction persistence compatibility

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
