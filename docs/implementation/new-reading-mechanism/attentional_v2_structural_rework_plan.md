# Attentional_v2 Structural Rework Plan

Purpose: turn the completed Phase 9 evaluation findings into an executable post-Phase-9 implementation plan for `attentional_v2`.
Use when: deciding implementation order, coordinating backend/frontend work, or checking what belongs in the rework versus in later polish.
Not for: stable mechanism authority, per-probe evidence, or final project history.
Update when: the implementation sequence, track boundaries, success criteria, or rollout posture materially changes.

Status: `planning`

Mechanism key: `attentional_v2`

Scope: `post-Phase-9 structural rework under the existing attentional_v2 mechanism key`

Primary upstream evidence:

- [long-span after-eval follow-up memo](../../../reading-companion-backend/docs/evaluation/long_span/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_followup_reflection_and_decisions.md)
- [excerpt interpretation report](../../../reading-companion-backend/docs/evaluation/excerpt/attentional_v2_excerpt_surface_v1_1_judged_20260406_interpretation.md)
- [Claude Code context-management research note](../../../reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md)

## 1. Why This Plan Exists

The long-span after-eval memo now captures the main mechanism failures and redesign conclusions, but it is not a good implementation surface.

It is:

- evidence-backed mechanism reflection
- a record of why certain redesign choices were made
- a source document for later stable decisions

It is not:

- a phased build plan
- a code-facing task breakdown
- a clean guide for coordinating backend mechanism work with frontend follow-through

This document exists to provide that missing implementation layer.

## 2. Core Working Decisions

These decisions are now treated as execution baselines for the rework.

### 2.1 Evolve `attentional_v2` in place

This rework should stay under the existing `attentional_v2` mechanism key.

Why:

- the mechanism's core identity is still right:
  - sentence-order fidelity
  - local pressure-driven reading
  - typed state
  - source-grounded evidence
- the failures exposed by formal eval are structural failures inside that direction, not proof that the direction itself should be discarded
- introducing `attentional_v3` now would create unnecessary mechanism-catalog, runtime, resume, and documentation churn before we know that a separate long-lived mechanism family is warranted

### 2.2 Treat this as a new post-Phase-9 implementation line

This work should not be forced back into the old `Phase 0-9` checklist.

Why:

- Phase 9 already answered a different question:
  - can `attentional_v2` become the default mechanism and produce formal excerpt/long-span evidence?
- this new line answers a new question:
  - how should the default mechanism be structurally reworked in response to those formal eval findings?

So the right framing is:

- `Post-Phase-9`
- `attentional_v2 structural rework`

### 2.3 Run one initiative with two coordinated tracks

We should implement this as one initiative with two tracks:

- `Track A: mechanism rework`
- `Track B: frontend / integration follow-through`

The mechanism track is primary.

The frontend track should follow the mechanism, but it should still be planned now so that backend changes do not drift away from product presentation needs.

### 2.4 Do not treat the after-eval memo as the execution plan

The long-span follow-up memo remains the mechanism reflection source.

This plan is the execution source.

### 2.5 Do not start with compaction or multi-agent orchestration

The first implementation focus should be:

- control-shape repair
- continuity reuse
- state usability

Not:

- explicit compaction as a first-class subsystem
- multi-sub-agent reading orchestration

## 3. What Must Be Preserved From Current V2

This rework is not a license to accidentally destroy the current strengths that helped `attentional_v2` win the excerpt surface.

The following are explicit preservation targets.

### 3.1 Sentence-order fidelity

The reader should continue to read in source order and remain close to the sentence substrate rather than regressing to section-first traversal.

### 3.2 Local pressure discipline

The mechanism should continue to read by following local unresolved pressure rather than by mechanically stepping through fixed large containers.

### 3.3 Dynamic unitization

The system should keep dynamic, semantically bounded reading units rather than falling back to one fixed chunking scheme.

### 3.4 Typed-state spine

The bottom layer should remain typed and structurally clear rather than collapsing back into one large memory blob.

### 3.5 Source-grounded evidence discipline

Bridges, reactions, and memory promotions should remain anchored to source evidence instead of drifting into free-floating summary behavior.

### 3.6 Default no-search honesty

Routine reading should remain text-first.

External search or heavy auxiliary expansion should stay rare and explicitly justified.

### 3.7 Exact local textual-pressure attention

The new `read` contract must preserve V2's best excerpt behavior:

- noticing distinctions
- actor intention
- social pressure
- concrete causal stakes
- textual reversals

The rework must not flatten local reading back into generic scene summary.

## 4. Problems This Plan Is Meant To Fix

The rework centers on five high-value failures already exposed by the completed eval review.

### 4.1 Semantic permission gating drops important text

The old heuristic trigger can stop important text from ever entering formal LLM reading.

### 4.2 Span visibility and span authority are misaligned

Small visible windows can currently close larger open spans.

### 4.3 Long-distance continuity is weaker than `iterator_v1`

`attentional_v2` does not yet reuse earlier material as stably as `iterator_v1`.

### 4.4 Reading output responsibilities are too fragmented

The current split across trigger, zoom, closure, controller, and reaction gate makes it too hard to explain, debug, and evolve the mechanism honestly.

### 4.5 Raw reaction truth is too easy to thin out

The mechanism can form local understanding that later becomes harder to see because reaction truth is not cleanly owned by the core reading step.

## 5. Workstream Overview

| Track | Goal | Priority | Notes |
| --- | --- | --- | --- |
| `A. mechanism rework` | Repair the control loop and continuity model while preserving V2's local-reading strengths | `primary` | backend-owned, but may require additive integration fields later |
| `B. frontend / integration follow-through` | Keep product surfaces honest as the mechanism changes, then progressively expose the new reading shape | `secondary` | should follow mechanism checkpoints rather than front-running them |

## 6. Track A: Mechanism Rework

Track A should be executed in bounded phases.

### 6.1 Phase A — Replace permission gating with a new control skeleton

Goal:

- remove heuristic trigger authority over whether正文 text gets a real LLM reading turn
- establish the new top-level control shape:
  - `navigate.unitize`
  - `read`
  - `navigate.route`

This phase should land the minimum viable structural change that fixes the long-span "important text never truly got read" failure.

#### Expected outputs

- a new control skeleton inside `attentional_v2`
- mandatory coverage read for正文 text
- the first version of bounded semantic unitization
- explicit alignment between:
  - what span is being read
  - what span can be extended
  - what span can be closed

#### Likely backend touch points

- `reading-companion-backend/src/attentional_v2/runner.py`
- `reading-companion-backend/src/attentional_v2/nodes.py`
- `reading-companion-backend/src/attentional_v2/prompts.py`
- `reading-companion-backend/src/attentional_v2/schemas.py`
- `reading-companion-backend/src/reading_mechanisms/attentional_v2.py`

#### Validation target

- the mechanism should no longer depend on heuristic trigger approval for正文 text to enter LLM reading
- the new loop should preserve sentence-order honesty
- no regression to section-first traversal

### 6.2 Phase B — Rebuild continuity and read-contract behavior

Goal:

- make `read` explicitly responsible for how the current unit uses earlier material
- separate default carry-forward continuity from exceptional look-back behavior

This phase should make long-distance reuse a first-class reading responsibility instead of a late side effect.

#### Expected outputs

- `carry-forward context`
- `active recall / look-back`
- `continuity / reuse result`
- `read` packet that clearly reports:
  - what the current unit did
  - how it used prior material
  - what implicit uptake it produced
  - whether a raw reaction genuinely emerged

#### Validation target

- earlier material reuse should become visible in the core reading packet rather than only in occasional bridge or retrospect moments
- the mechanism should behave more like "carry forward by default, recall specifically only when needed"

### 6.3 Phase C — Restructure state and prompt packetization

Goal:

- keep V2's typed-state advantages
- recover V1's stronger memory usability

This phase should implement the new state shape and the derived prompt-input layer.

#### State target

- `working_state`
- `concept_registry`
- `thread_trace`
- `reflective_frames`
- `anchor_bank`

#### Packetization target

- bottom-layer state remains typed
- model-facing packet becomes query-aware and task-aware
- detailed state should not be blindly injected in full

#### Validation target

- the mechanism should become better at long-distance continuity without turning back into one giant memory blob
- source-grounded evidence should stay intact

### 6.4 Phase D — Recall, persistence, resume, and compaction polish

Goal:

- polish the system after the new reading loop and state shape are already real

This phase is intentionally later.

It should only happen after the earlier phases prove stable enough to justify additional complexity.

#### Candidate scope

- optional refinement of `active recall / look-back`
- optional reduction or retirement of legacy `reaction_emission`
- continuation capsule design
- compaction / rehydration boundary work
- resume alignment against the new state model

#### Validation target

- polish should clarify and strengthen the new mechanism
- it must not become a substitute for landing the earlier structural work

## 7. Track B: Frontend / Integration Follow-Through

This track should move with Track A, but not at the same depth or speed.

### 7.1 Phase B0 — Protect compatibility while Track A changes

Goal:

- keep existing product surfaces honest during the rework
- avoid accidental frontend breakage while backend internals are in motion

Expected posture:

- preserve current compatibility envelopes where needed
- prefer additive fields over premature surface rewrites
- keep the chapter scene and marks surfaces usable even while mechanism internals evolve

### 7.2 Phase B1 — Expose the new reading truth incrementally

Goal:

- once Track A produces stable reading packets, expose the most valuable additive truth first

Likely targets:

- clearer current reading locus
- continuity / move-type visibility where product-helpful
- better anchor-native reaction truth

### 7.3 Phase B2 — Resume the V2-native presentation lane on top of the new mechanism

Goal:

- once the reworked mechanism stabilizes, resume the deeper chapter / marks redesign using the improved reading shape rather than the old compatibility shell

Important boundary:

- frontend work should not invent a second conceptual model of reading that contradicts the reworked mechanism

## 8. Documentation Routing During This Initiative

To avoid document sprawl, each doc should keep one job.

### 8.1 Evaluation follow-up memo

File:

- [attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_followup_reflection_and_decisions.md](../../../reading-companion-backend/docs/evaluation/long_span/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_followup_reflection_and_decisions.md)

Role:

- mechanism evidence and design reasoning source

### 8.2 This plan document

Role:

- implementation blueprint for the structural rework

### 8.3 Execution tracker

File:

- [new-reading-mechanism-execution-tracker.md](./new-reading-mechanism-execution-tracker.md)

Role:

- progress tracker
- current phase / checkpoint summary
- links to the current implementation plan

### 8.4 Stable docs

Examples:

- [docs/backend-reading-mechanisms/attentional_v2.md](../../backend-reading-mechanisms/attentional_v2.md)
- [docs/backend-reading-mechanism.md](../../backend-reading-mechanism.md)
- [docs/backend-state-aggregation.md](../../backend-state-aggregation.md)
- [docs/api-contract.md](../../api-contract.md)

Role:

- only update when real behavior lands

### 8.5 History decision log

File:

- [docs/history/decision-log.md](../../history/decision-log.md)

Role:

- record later inflection points once the rework becomes a real project-direction change in implemented behavior, not just a planning intention

## 9. Immediate Next Steps

The next concrete move should be:

1. define the code-facing contract for `Phase A`
2. identify the smallest backend slice that can land:
   - `navigate.unitize`
   - `read`
   - `navigate.route`
   without yet forcing the whole new state model to exist
3. preserve current compatibility surfaces while that slice lands
4. only after `Phase A` is real, open the first frontend/integration follow-through work item that depends on it

## 10. Success Criteria For This Plan

We should consider this rework direction on track only if all of the following remain true:

- long-span failures are addressed without regressing to section-first reading
- V2's excerpt strengths are preserved:
  - local pressure fidelity
  - anchored local reading
  - source-groundedness
- continuity improves without turning the system into one giant memory prompt
- backend and frontend remain coordinated under one initiative without becoming one tangled implementation block
