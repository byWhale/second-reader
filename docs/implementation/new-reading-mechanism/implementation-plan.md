# New Reading Mechanism Implementation Plan

Purpose: define the execution order for implementing the new reading mechanism end to end without losing design scope or violating project boundaries.
Use when: deciding what to build first, what depends on what, or what must be true before later phases begin.
Not for: stable mechanism authority or day-to-day progress logging.
Update when: phase order, dependencies, or exit criteria change.

## Planning Rules
- Implement the mechanism behind the shared runtime and mechanism boundaries. Do not copy `iterator_v1` wiring into a second silo.
- Treat the shared runtime shell as compatibility-oriented, not ontology-imposing.
- Preserve mechanism-authored product artifacts upward whenever possible; add thin envelopes and compatibility sidecars instead of replacing the original thought objects.
- Keep the public API contract stable until an intentional adapter or contract migration is ready.
- Build deterministic scaffolding before prompt-node behavior that depends on it.
- Do not switch the default mechanism during this plan. Default promotion is the final migration decision, not the starting assumption.
- Treat observability and evaluation as required implementation surfaces, not cleanup work.

## Phase 0: Planning And Scope Lock
Purpose:
- Turn the design into an executable project without losing detail.

Main work:
- Decide whether the new design maps to `attentional_v2` or to a new mechanism key.
- Freeze the temporary working-doc set in this folder.
- Build the full-fidelity source mirror.
- Build and maintain the design coverage map.
- Build and maintain the atomic requirement ledger.
- Record initial open questions and working assumptions.
- Seed the temporary decision log.
- Seed the validation matrix.
- Seed the stable-doc impact map.
- Define the cut line between temporary docs and stable docs.

Exit criteria:
- One named target mechanism exists for implementation work.
- The source mirror exists and is far enough along to support trace review.
- All major design blocks are mapped to phases.
- The requirement ledger exists and the omission-control process is active.
- The implementation tracker exists and is ready to drive execution.

## Phase 1: Runtime Foundation And Schemas
Purpose:
- Create the mechanism shell, state schemas, artifact layout, and policy/version surfaces that every later phase depends on.

Main work:
- Add the mechanism adapter skeleton under the shared mechanism boundary.
- Apply the `mechanism-authored core, shell-authored envelope` boundary to the runtime design.
- Define the exact split between shared `_runtime/` envelopes and `_mechanisms/<mechanism_key>/` private state.
- Define mechanism-private artifact roots under `_mechanisms/<mechanism_key>/`.
- Define runtime schemas for:
  - `working_pressure`
  - `anchor_memory`
  - `reflective_summaries`
  - `knowledge_activations`
  - `move_history`
  - `reconsolidation_records`
  - `reader_policy`
  - event envelopes
  - checkpoint summaries
- Define versioning surfaces:
  - `mechanism_version`
  - `policy_version`
  - prompt-set and node-level prompt versions
- Define explicit state-operation primitives.

Depends on:
- Phase 0

Exit criteria:
- The new mechanism can be instantiated by the shared runtime shell.
- Shared envelopes do not overwrite original mechanism-authored thought artifacts.
- Artifact layout and core schemas are concrete enough for later phases to write against.
- No later phase needs to invent its own state encoding ad hoc.

## Phase 2: Sentence Substrate And Survey Orientation
Purpose:
- Make sure the shared parsed-book substrate can actually support sentence-order reading and the survey contract.

Main work:
- Audit whether `public/book_document.json` already exposes sentence-level ids and locators in the right shape.
- Close any parser/substrate gaps needed for sentence-order intake and bounded look-back.
- Implement `book_survey` and its planned survey artifacts.
- Enforce the non-cheating boundary for chapter openings, closings, and table-of-contents orientation.

Depends on:
- Phase 1

Exit criteria:
- The mechanism can read sentence-by-sentence from shared substrate without inventing an iterator-only layer.
- Survey artifacts exist and remain orientation-only.
- Future paragraph-level text is not leaked into live reading state.

## Phase 3: Deterministic Intake, Gates, And Retrieval Scaffolding
Purpose:
- Build the always-on cheap control substrate before the main interpretive nodes.

Main work:
- Sentence ingest and mark-seen flow.
- Local buffer maintenance.
- Qualitative gate state management.
- Candidate-boundary signal pipeline.
- Trigger ensemble and trigger output schema.
- Initial controller-facing pressure summaries.
- Deterministic `candidate_generation` retrieval channels and bounded look-back scaffolding.

Depends on:
- Phase 2

Exit criteria:
- The mechanism can advance through sentences with correct gate changes and boundary nominations.
- Retrieval candidates for bridge work can be produced deterministically and cheaply.
- Later LLM nodes can receive real structured packets rather than placeholders.

## Phase 4: Core Interpretive Loop
Purpose:
- Implement the mechanism's main reading intelligence for local interpretation and move choice.

Main work:
- Implement `zoom_read`.
- Implement `meaning_unit_closure`.
- Implement `controller_decision`.
- Implement node handoff rules between those nodes.
- Implement `reaction_emission` gate for optional visible output persistence.
- Add prompt versioning and manifest capture for these behavior-defining nodes.

Depends on:
- Phase 3

Exit criteria:
- The mechanism can run sentence intake -> optional zoom -> meaning-unit closure -> controller move on real text.
- Closure and controller honor explicit handoff rules.
- Visible reactions remain optional, source-anchored, and quality-gated.

## Phase 5: Knowledge, Memory, And Bridge Resolution
Purpose:
- Make the tiered state actually useful for callbacks, prior knowledge, and source-anchored revisits.

Main work:
- Implement knowledge-activation lifecycle and knowledge-use policy.
- Implement `bridge_resolution` over the deterministic candidate set.
- Implement anchor retention, typed relations, motif indexing, unresolved-reference indexing, and trace links.
- Implement bridge-triggered state updates:
  - strengthen or retain anchors
  - link anchors
  - reactivate hot items
- Add search-policy state even if full external search remains deferred or minimized in early v1.

Depends on:
- Phase 4

Exit criteria:
- The mechanism can make honest bridge decisions without inventing targets.
- Prior knowledge is tracked with separate recognition and warrant.
- Bridge and knowledge behavior are observable and stateful, not prompt-only illusions.

## Phase 6: Slow-Cycle Reasoning And Historical Integrity
Purpose:
- Add the slower, historically meaningful parts of the design that govern durable understanding and revision.

Main work:
- Persist mechanism-authored anchored reaction records as the source of truth for durable visible thought.
- Implement `reflective_promotion`.
- Implement `reconsolidation`.
- Implement `chapter_consolidation`.
- Implement backward sweep, cooling, carry-forward, and optional chapter reaction.
- Preserve immutable earlier reactions plus append-and-link reconsolidation behavior.
- Project persisted reactions into current chapter-result compatibility shapes without letting those wrappers become primary truth.

Depends on:
- Phase 5

Exit criteria:
- Durable understanding can be promoted without over-promotion.
- Later reading can revise current understanding without rewriting history.
- Visible reaction history remains anchored, append-only, and mark-safe.
- Chapter transitions preserve continuity without carry-forward bloat.

## Phase 7: Persistence, Checkpointing, And Resume
Purpose:
- Preserve the identity of the same reading mind across interruption.

Main work:
- Persist reading cursor, local continuity state, durable state, and resume metadata.
- Implement:
  - `warm_resume`
  - `cold_resume`
  - `reconstitution_resume`
- Use the agreed bounded reread policy:
  - `warm_resume`: reread `0` sentences
  - `cold_resume`: target `8` current-chapter sentences, expand to the start of the active meaning unit when needed, hard cap `12`
  - `reconstitution_resume`: target `24` current-chapter sentences, expand backward across up to `3` meaning units when needed, hard cap `30`
  - stay chapter-local by default; if there is not enough earlier text in the chapter, reread from chapter start rather than crossing into the previous chapter
- Rebuild hot state correctly for non-warm resumes.
- Emit checkpoint summaries at required milestones.
- Validate mechanism/source compatibility and fallback behavior.

Depends on:
- Phase 6

Exit criteria:
- The mechanism can stop and resume without losing anchors, visible reactions, or reflective history.
- Reconstructed state is explicitly marked as reconstructed.
- Resume invariants are testable and observable.

## Phase 8: Observability, Evaluation, And Shared-Surface Integration
Purpose:
- Make the mechanism diagnosable, comparable, and adaptable to existing product surfaces.

Main work:
- Implement required event-stream and checkpoint-summary contracts.
- Resolve the observability split as:
  - shared/public `standard`
  - mechanism-private `debug`
- Emit required standard event types with reason summaries and version metadata.
- Keep shared runtime shell and shared checkpoint summaries thin while preserving full resume-correctness checkpoints privately under the mechanism.
- Reserve controller forensics, candidate traces, prompt/node diagnostics, and detailed rejection reasons for debug mode.
- Produce normalized eval artifacts and run metadata compatible with shared evaluation docs.
- Adapt mechanism-private locus into shared public surfaces:
  - `current_reading_activity`
  - `current_excerpt`
  - current chapter position and compatible live-state fields
- Additive top-layer/API refinement planning and implementation for mechanism-valued fields that current surfaces cannot fully express yet, including:
  - reaction `primary_anchor`
  - `related_anchors`
  - reconsolidation lineage
  - span-based or sentence-based live locus
  - current move type such as `advance`, `dwell`, `bridge`, or `reframe`
- Keep `section_ref` / `segment_ref` only as migration sidecars during this phase.
- Record the later intentional migration that still remains:
  - redesign chapter/detail and marks surfaces around chapter text plus anchored reactions
  - remove section-first requirements from the stable API/frontend contract once the frontend has switched to locus/anchor-native rendering
- Record the later observability work that still remains:
  - wire node-level standard/debug observability across the live local loop, bridge cycle, and slow-cycle nodes once the live runner exists
  - keep debug mode optional instead of making deep diagnostics the baseline requirement for normal evaluation runs
- Verify compatibility with current analysis-state, activity, and marks surfaces.

Depends on:
- Phase 7

Exit criteria:
- Every major mechanism move has observable evidence.
- Standard mode is sufficient for trustworthy resume, durable trace, and baseline evaluation.
- Debug mode adds implementation forensics without becoming the default runtime storage posture.
- The mechanism can be evaluated without raw private traces becoming the primary comparison surface.
- The top layer can expose more of the mechanism's real value without forcing the mechanism back into section-first ontology.
- Shared product views can consume the new mechanism through adapters instead of ontology leakage.

## Phase 9: Migration, Stabilization, And Default-Cutover Readiness
Purpose:
- Move from "implemented mechanism" to "mechanism ready for real product use."

Main work:
- Run mechanism-integrity and end-to-end evaluation passes.
- Compare against `iterator_v1` on shared evaluation frame.
- Decide compatibility strategy for:
  - activity surfaces
  - chapter/detail views
  - marks anchoring
  - resume semantics
  - reaction persistence
- Promote stabilized conclusions into long-term docs.
- Record decision-bearing changes in `docs/history/decision-log.md` when appropriate.
- Decide whether and when to promote the mechanism to default.

Depends on:
- Phase 8

Exit criteria:
- Acceptance ladder reaches at least `v1_acceptable`.
- Stable docs are updated for any landed runtime/mechanism/evaluation/public-surface changes.
- Default-cutover decision is explicit rather than implied by code drift.

## Dependency Summary
- Phase 0 before everything.
- Phase 1 before any real runtime code.
- Phase 2 before sentence-order loop work.
- Phase 3 before core prompt nodes.
- Phase 4 before knowledge/bridge logic can be trusted.
- Phase 5 before historical-integrity and chapter-end logic.
- Phase 6 before resume logic is meaningful.
- Phase 7 before shared-surface integration and evaluation are credible.
- Phase 8 before migration or default-cutover decisions.

## Additional Preparation That Should Not Be Skipped
- Substrate audit:
  - confirm sentence ids, locators, and bounded look-back feasibility early
- Mechanism naming decision:
  - avoid implementing half the code under one key and half under another
- Adapter strategy:
  - decide early how non-section runtime state maps to current section-shaped public surfaces
- Prompt traceability:
  - version prompts from the first real behavior-defining node
- Evaluation harness:
  - do not postpone observability and evaluation until after feature work
