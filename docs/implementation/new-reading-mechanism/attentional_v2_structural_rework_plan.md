# Attentional_v2 Structural Rework Plan

Purpose: turn the completed Phase 9 evaluation findings into an executable backend implementation plan for structurally reworking `attentional_v2`.
Use when: deciding backend implementation order, checking which mechanism changes belong in the rework, or converting eval findings into concrete code slices.
Not for: stable mechanism authority, frontend redesign planning, per-probe evidence, or final project history.
Update when: the backend implementation sequence, code-slice boundaries, success criteria, or rollout posture materially changes.

Status: `in_progress`

Mechanism key: `attentional_v2`

Scope: `post-Phase-9 backend structural rework under the existing attentional_v2 mechanism key`

Implementation checkpoint:

- `Phase A` is landed:
  - trigger output no longer gates whether正文 text gets formal reading
  - the live control skeleton is now `navigate.unitize -> read -> navigate.route`
  - span authority now matches the exact chosen unit
- `Phase B` is landed:
  - `read` now owns the authoritative unit packet on the live path
  - bounded `carry-forward context` is now the default continuity path into `read`
  - `read` may request one bounded `active recall` or `look-back` supplement
  - legacy `raw_reaction` fields still exist on the read packet as a compatibility shell
  - this is now treated as an intermediate baseline rather than the final ownership contract
- `Phase C.1` is landed:
  - live prompt inputs now flow through a bounded internal `state_packet.v1` seam
  - `navigate.unitize` now receives a packetized `navigation_context`
  - `read` now receives a packetized read-context view with explicit continuity / working-state / reflective / focus / anchor-bank separation
  - persisted runtime files and public compatibility surfaces remain unchanged
- `Phase C.2` is landed as the first state-territory slice:
  - live state packets now derive a bounded `concept_digest` from the current `motif_index + unresolved_reference_index`
  - live state packets now derive a bounded `thread_digest` from the current `trace_links + unresolved_reference_index`
  - `navigate.unitize` and `read` now both receive those small concept/thread digests through the packet layer
  - persisted runtime files and public compatibility surfaces remain unchanged
- `Phase C.3` is landed as the direct main-state cutover:
  - new runs now treat `working_state / concept_registry / thread_trace / reflective_frames / anchor_bank` as the primary runtime and checkpoint truth
  - `working_pressure / anchor_memory / reflective_summaries` were demoted to legacy load/projection territory during the cutover
  - `active_recall` now surfaces first-class `concepts` and `threads` from the new state layers
  - newly written checkpoints now use only the new primary state keys, while resume still accepts both old and new runtime/checkpoint shapes
  - public compatibility surfaces remain unchanged
- `Phase C.4` is landed as the helper-contract cutover and live legacy-state retirement slice:
  - sentence-intake / bridge / slow-cycle now consume and write the new primary state layers directly
  - the live runner no longer projects new state into `working_pressure / anchor_memory / reflective_summaries` to execute helpers
  - live runtime loading and resume now reject pre-`Phase C.3` runtime directories and checkpoints instead of migrating them on the live path
  - public compatibility surfaces remain unchanged
- `Phase D` is now landed as the continuity / recall / resume polish slice:
  - `read` now supports a budget-bounded multi-step supplemental loop
  - runtime state and full checkpoints now persist a lightweight `continuation capsule` with rehydration entrypoints
  - warm resume now restores the latest usable continuation capsule together with new-format runtime/checkpoint state
  - `look_back` now resolves one bounded earlier source span, and `read_audit` now records per-step supplemental activity plus stop reasons
  - public compatibility surfaces remain unchanged
- `Phase E1` is now landed:
  - the new `Read -> Express` contract is frozen in the stable mechanism doc and this implementation plan
- the first compatibility-first `Phase E2` slice is now also landed:
  - the live runner now routes `read -> express(if needed) -> navigate.route`
  - `read` now emits `unit_delta`, `pressure_signals`, and `express_signal`
  - `Express` now owns visible-reaction wording on the live path
  - old family handling now survives only through a thin compatibility adapter posture rather than as the live prompt ontology
- `Phase E3` is now landed:
  - persisted `reaction_records` now keep `Express`-native surfaced semantics first
  - slow-cycle compatibility projection and normalized eval export now derive old family labels through one compat helper rather than treating legacy `type` as the internal truth
  - the bounded fallback from missing `ExpressResult` to legacy `read.raw_reaction` is now explicitly marked as compatibility-only
- next after `Phase E3`:
  - validate quality on the new persistence/export baseline
  - then decide whether later slices should expose surfaced-reaction structure more natively above the current compatibility envelopes

Primary upstream evidence:

- [long-span after-eval follow-up memo](../../../reading-companion-backend/docs/evaluation/long_span/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_followup_reflection_and_decisions.md)
- [excerpt interpretation report](../../../reading-companion-backend/docs/evaluation/excerpt/attentional_v2_excerpt_surface_v1_1_judged_20260406_interpretation.md)
- [Claude Code context-management research note](../../../reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md)
- [stable live mechanism doc](../../backend-reading-mechanisms/attentional_v2.md)

## 1. Why This Plan Exists

The long-span after-eval memo now captures the main mechanism failures and redesign conclusions, but it is not a good implementation surface.

It is:

- evidence-backed mechanism reflection
- a record of why certain redesign choices were made
- a source document for later stable decisions

It is not:

- a code-facing build plan
- a phased backend slice map
- a clean statement of what to preserve, what to replace, and what to defer

This document exists to provide that missing implementation layer.

## 2. Working Position

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

### 2.2 Treat this as a new post-Phase-9 backend line

This work should not be forced back into the old `Phase 0-9` checklist.

Why:

- Phase 9 already answered a different question:
  - can `attentional_v2` become the default mechanism and produce formal excerpt/long-span evidence?
- this new line answers a new question:
  - how should the default mechanism be structurally reworked in response to those formal eval findings?

So the right framing is:

- `Post-Phase-9`
- `attentional_v2 structural rework`
- backend-only

### 2.3 This plan is backend-only

This plan should not absorb the current frontend lane.

Why:

- the current frontend direction and page-responsibility work already live in their own documents and tasks
- the long-span after-eval memo is about mechanism behavior, not frontend presentation
- mixing frontend implementation details into this plan would blur ownership and make the backend rework harder to execute cleanly

Implication:

- frontend work may continue in parallel
- but frontend planning remains outside this document
- this plan only owns backend mechanism rework and the backend-facing compatibility discipline needed while that rework lands

### 2.4 Do not treat the after-eval memo as the execution plan

The long-span follow-up memo remains the mechanism reflection source.

This plan is the execution source.

### 2.5 Do not start with compaction or multi-agent orchestration

The first implementation focus should be:

- control-shape repair
- continuity-carrying read behavior
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

## 5. Rework Scope And Explicit Non-Goals

### 5.1 In scope

- replace heuristic semantic permission gating
- replace the current fragmented local control shape with `navigate.unitize + read + navigate.route`
- align span visibility and span authority
- make `read` carry forward prior context and expose prior-material use as an observational result rather than a separate mechanism action
- restructure state and prompt packetization so long-distance continuity becomes more reliable
- move visible-reaction wording out of `read` and into `Express` while keeping `read` responsible for expression-worthiness judgment
- preserve existing compatibility behavior where practical while the backend shape changes

### 5.2 Explicitly out of scope for this plan

- frontend route, component, or page-redesign planning
- reopening excerpt surface composition work
- reopening dataset retuning by default
- making compaction a first-class subsystem in the first implementation wave
- introducing multi-sub-agent reading orchestration
- minting a new `attentional_v3` mechanism key

## 6. Current V2 To New Shape Mapping

The rework should be understood as a controlled remap of current V2 responsibilities, not as an unstructured rewrite.

| Current V2 element | Problem now | New home / treatment |
| --- | --- | --- |
| heuristic `trigger` | wrongly acts as permission gate over whether text deserves real LLM reading | remove its authority over正文 reading; replace with mandatory coverage read plus `navigate.unitize` boundary choice |
| `zoom_read` | currently carries too much of the real reading responsibility but only opens on gated cases | absorb its reading semantics into `read` |
| `meaning_unit_closure` | closure authority is entangled with partial visibility windows | split into `read` boundary evidence plus `navigate.route` close / continue judgment |
| `controller_decision` | one more control surface in an already over-fragmented chain | absorb into `navigate.route` |
| `reaction_emission` | thins out already-formed reading truth | replace it with a narrow `Express` node that owns surfaced wording while `read` keeps the underlying uptake and expression-worthiness judgment |
| lazy bridge retrieval / `bridge_resolution` | useful in principle, but too downstream to carry continuity by itself | keep only as optional execution path beneath `carry-forward context` and `active recall / look-back` |
| `working_pressure` | useful hot-state concept, but currently mixed with older local-cycle shape | evolve into `working_state` |
| `anchor_memory` | useful evidence territory, but too easy to over-expand conceptually | evolve into `anchor_bank` only |
| `knowledge_activations` | currently too easy to treat as a durable memory layer | keep only as in-read immediate external-knowledge activation, not as a main state layer |

## 7. Backend Implementation Phases

The mechanism rework should be executed in bounded phases.

### 7.1 Phase A — Replace permission gating with a new control skeleton

Goal:

- remove heuristic trigger authority over whether正文 text gets a real LLM reading turn
- establish the new top-level control shape:
  - `navigate.unitize`
  - `read`
  - `navigate.route`

This phase should land the minimum viable structural change that fixes the long-span "important text never truly got read" failure.

#### Concrete design target

The minimum viable loop after Phase A should be:

1. canonical sentence stream defines position
2. `navigate.unitize` looks ahead within bounded forward text
3. one coverage unit is chosen
4. `read` runs once on that coverage unit
5. `navigate.route` decides:
   - `commit`
   - `continue / extend`
   - `bridge_back`
   - `reframe`
   - `persist_raw_reaction`

This phase is not yet trying to perfect long-distance memory. It is trying to eliminate the class of failure where important text never becomes a real reading event.

#### Unitization policy that should already be respected in Phase A

`navigate.unitize` should not degrade into "fixed sentence count" or "always stop at paragraph end."

The first viable unitization policy should already preserve the boundary discipline established in the after-eval review:

- author structure remains the first skeleton
- semantic judgment only refines inside that skeleton
- deterministic code may expose structure and budget, but must not replace semantic boundary judgment

The boundary hierarchy should be:

1. hard boundaries
   - chapter
   - section / subsection
   - sentence
2. strong boundaries
   - paragraph
   - speaker switch
   - list-item switch
   - obvious scene switch
3. semantic close signals
   - a definition has completed
   - a local contrast has landed
   - a question-answer move has locally closed
   - one narrative or argumentative move has relatively completed
4. continuation signals
   - unresolved reference
   - unfinished enumeration
   - concession / turn that has only opened
   - the same local move is still being completed

The preview policy should be:

- never cross chapter
- by default do not cross section / subsection
- use paragraph as the default semantic shell
- default preview baseline:
  - current paragraph remainder
  - plus the next paragraph in the same section
- only widen further when:
  - the current paragraph is very short
  - the current paragraph is obviously unfinished
  - there is strong continuation pressure into the next paragraph

The coverage-unit policy should be:

- target one paragraph by default
- allow two short adjacent paragraphs only when they clearly belong to one local move
- keep a soft cap around `6-8` sentences
- keep a hard cap around `10-12` sentences
- if a long paragraph must be split, split only on sentence boundaries and prefer a natural semantic close
- if a unit is capped rather than naturally closed, preserve explicit continuation pressure instead of pretending closure

#### Minimum unitization audit contract

Phase A does not need a full final artifact suite yet, but `navigate.unitize` should already emit enough information that later debugging can answer why it stopped where it stopped.

The minimum audit payload should include:

- `start_sentence_id`
- `preview_range`
- `end_sentence_id`
- `boundary_type`
  - for example:
    - `paragraph_end`
    - `intra_paragraph_semantic_close`
    - `cross_paragraph_continuation`
    - `section_end`
    - `budget_cap`
- `evidence_sentence_ids`
- one short reason
- whether continuation pressure remains

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
- `reading-companion-backend/src/attentional_v2/state_ops.py`
- `reading-companion-backend/src/reading_mechanisms/attentional_v2.py`

#### Suggested code slices

- `A1. skeleton and naming`
  - introduce explicit `navigate_unitize`, `read_unit`, and `navigate_route` boundaries in code
  - do not yet fully delete legacy helpers if adapters keep migration safer
- `A2. mandatory coverage read`
  - remove heuristic trigger authority over whether正文 text gets real LLM reading
  - preserve deterministic watch / substrate logic only where it does not replace reading
- `A3. bounded unitization`
  - implement the first bounded forward semantic unitization policy
  - keep preview bounded by author structure
- `A4. span authority alignment`
  - ensure the span being judged is the span actually being read / closed / extended
- `A5. compatibility guard`
  - keep enough runtime/public compatibility that current frontend surfaces do not break while internals change

#### Validation target

- the mechanism should no longer depend on heuristic trigger approval for正文 text to enter LLM reading
- the new loop should preserve sentence-order honesty
- no regression to section-first traversal
- no reintroduction of large hidden spans closed by smaller tail windows

### 7.2 Phase B — Rebuild read-context integration and continuity behavior

Status:

- landed on April 12, 2026 as the current read-context baseline under the existing `attentional_v2` key

Goal:

- make `read` explicitly responsible for reading the current unit together with carried-forward context
- separate default carry-forward continuity from exceptional recall / look-back behavior

This phase should make long-distance continuity part of the normal `read` act instead of a late side effect.

It should not introduce a standalone `reuse` node or a separately executed "reuse action."

If the current unit draws on earlier material, that should show up as a natural consequence of the `read` result, not as an extra mechanism step.

#### Concrete design target

`read` should stop being merely "local interpretation of current text" and become:

- the one place that formally reads the current unit
- the one place that produces `implicit uptake`
- the one place that can report whether prior material materially informed the current understanding
- the one place from which a genuine `raw reaction` can emerge

`read` should also be allowed to request more help when the default carried-forward packet is insufficient:

- `active recall`
- `look-back`

The mechanism does not need a hard-coded runtime taxonomy for how prior material was used.

If later auditing benefits from lightweight labels such as:

- `continuation`
- `clarification`
- `answer`
- `contrast`
- `callback`
- `reframe`
- `escalation`

those labels should stay optional observational aids only.

They should not become execution authority or a fixed branching logic.

#### Expected outputs

- `carry-forward context`
- optional `active recall / look-back`
- `read` packet that clearly reports:
  - what the current unit did locally
  - what implicit uptake it produced
  - whether prior material materially informed the current understanding, and if so, a short explanation of how
  - whether more recall / look-back is needed
  - whether a raw reaction genuinely emerged

`carry-forward context` should be treated as the default continuity path.

`active recall / look-back` should remain the narrower path for cases where the carried-forward packet is insufficient.

The intended default is:

- carry forward a small, usable packet
- let `read` naturally connect current text with that packet
- escalate only when the current unit genuinely needs more than the default packet provides

That landed baseline solved one class of thinning-out failure, but it also exposed a new voice problem:

- when `read` carries too much control and continuity responsibility, the surfaced output tends to sound like mechanism-authored summary rather than reading-time reaction

The approved next step is therefore not to make `read` rewrite better visible prose.

It is to split visible reaction back out into a dedicated `Express` node while keeping `read` responsible for the underlying uptake and expression-worthiness judgment.

#### Suggested code slices

- `B1. read packet contract`
  - define a structured packet returned from `read`
  - include:
    - `unit_delta`
    - `implicit_uptake`
    - `pressure_signals`
    - `express_signal`
    - focal text / anchor evidence
    - optional `context_request`
- `B2. carry-forward first`
  - default continuity should come from a small carried-forward packet, not from repeated heavy retrieval
- `B3. active recall / look-back`
  - add a narrower explicit path for cases where carry-forward context is insufficient
- `B4. route integration`
  - make `navigate.route` consume the new read packet instead of older closure/controller fragments

#### Runtime discipline

Phase B should keep semantic freedom in the model and keep hard-coded logic narrow.

Deterministic code may still own:

- recall / look-back budget limits
- safety rails
- persistence
- audit serialization

Deterministic code should not hard-code a semantic taxonomy of "allowed reuse types" and branch on it as if that were the reading process itself.

#### Validation target

- earlier material should remain available through carry-forward and bounded recall without adding a standalone `reuse` action
- the mechanism should behave more like "carry forward by default, recall specifically only when needed"
- no automatic collapse back into a giant memory blob

#### Landed baseline

- the live runner now builds a small `carry-forward context` from persisted state before each unit read
- the authoritative live read path is now:
  - build carry-forward context
  - `read`
  - optional budget-bounded supplemental looping through `active recall` or `look-back`
  - rerun `read` while supplemental budget remains and the current unit still explicitly asks for more context
  - deterministic `navigate.route`
- `read` now owns:
  - current-unit reading
  - `implicit_uptake`
  - optional `context_request`
- private `read_audit` records now capture:
  - carry-forward refs used
  - whether supplemental context was requested and satisfied
  - final raw-reaction presence

#### Follow-up interpretation

The current Phase B baseline is still valuable, but it is no longer the intended end state for visible reaction ownership.

The approved next-shape interpretation is:

- `read` should keep:
  - current-unit reading
  - `unit_delta`
  - `implicit_uptake`
  - `pressure_signals`
  - `should_express` / `express_signal`
  - optional `context_request`
- `read` should stop being the final owner of visible reaction wording
- visible reaction wording should move into a dedicated `Express` node

### 7.3 Phase C — Restructure state and prompt packetization

Goal:

- keep V2's typed-state advantages
- recover V1's stronger memory usability

This phase should implement the new state shape and the derived prompt-input layer.

Status:

- `Phase C.1` landed on April 12, 2026 as the first packetization seam
- `Phase C.2` also landed on April 12, 2026 as the first state-territory slice
  - live packets now include bounded `concept_digest` and `thread_digest` views derived from the current persisted indexes
- `Phase C.3` also landed on April 12, 2026 as the direct main-state cutover
  - new runs now write and resume against `working_state / concept_registry / thread_trace / reflective_frames / anchor_bank` as the primary runtime/checkpoint truth
  - legacy `working_pressure / anchor_memory / reflective_summaries` are still accepted on load and are still projected for helper compatibility, but they no longer own the live semantic state
  - `active_recall` now exposes first-class `concepts` and `threads` from the new layers
- `Phase C.4` also landed on April 12, 2026 as the helper-contract cutover
  - sentence-intake / bridge / slow-cycle now operate directly on `working_state / concept_registry / thread_trace / reflective_frames / anchor_bank`
  - live helper execution no longer depends on `project_legacy_*` adapters or migrate-back round trips
  - live runtime loading and resume now reject pre-`Phase C.3` runtime/checkpoint shapes
- `Phase C` is now complete, and the next open work is `Phase D`

#### Concrete design target

Keep V2's typed-state base, but stop exposing it to the model as an unstructured pile of stores.

#### State target

- `working_state`
- `concept_registry`
- `thread_trace`
- `reflective_frames`
- `anchor_bank`

#### State semantics that should be explicit in Phase C

- `working_state`
  - hot state needed by the next immediate reading step
  - current focus, open questions, active tensions, bridge pull, local unresolved items
- `concept_registry`
  - object memory
  - people, places, institutions, terms, abstract concepts, key objects
  - answers what this thing is, why it matters in this book, and which threads it touches
- `thread_trace`
  - plot / argument / relationship / question trace
  - answers where this line currently stands and whether the present unit continues, turns, answers, counters, or closes it
- `reflective_frames`
  - slower chapter-level and book-level understanding
  - durable chapter understandings, book frames, and stable definitions
- `anchor_bank`
  - source-grounded evidence base only
  - retained anchors, typed relations, revisit / bridge support
  - not a generic semantic memory bucket

#### Current V2 state disposition that should guide migration

Keep and rename or tighten:

- `working_pressure` -> `working_state`
- `anchor_memory` -> `anchor_bank`
- `reflective_summaries` -> `reflective_frames`

Merge or absorb:

- `motif_index`
  - absorb into `concept_registry` plus `anchor_bank` link structure
- `trace_links`
  - absorb into `thread_trace`
- `unresolved_reference_index`
  - hot unresolved items into `working_state`
  - cross-unit unresolved items into `thread_trace`

Keep only as helper territory, not as a competing main memory layer:

- retrieval helpers
- index-like lookup structures

Do not preserve as future main semantic entry points:

- `trigger_state`
- `gate_state`
- `local_buffer`
- semantics tied to `no_zoom / monitor / zoom_now`
- semantics tied to the older closure/controller chain

#### Packetization target

- bottom-layer state remains typed
- model-facing packet becomes query-aware and task-aware
- detailed state should not be blindly injected in full
- prompt input should be a derived view, not raw state dumped verbatim
- `navigate.unitize`, `read`, and `navigate.route` should use distinct prompt families even if they share the same model target

#### Load strategy target

The packetization layer should already assume an index-first loading policy.

`always reload` should stay very small and should carry only:

- the current `session continuity capsule`
- the current `working_state`
- the current chapter's short `reflective frame`
- a very small active `concept / thread digest`

`on-demand retrieval` should carry the heavier layers:

- detailed `concept_registry` entries
- detailed `thread_trace` milestones
- source evidence from `anchor_bank`
- historical raw reactions / evidence bundles
- long original excerpts

#### Suggested code slices

- `C1. state territory migration`
  - map current state helpers into:
    - `working_state`
    - `concept_registry`
    - `thread_trace`
    - `reflective_frames`
    - `anchor_bank`
- `C2. prompt packet derivation`
  - derive a small query-aware packet from those state layers for `navigate.unitize`, `read`, and `navigate.route`
- `C3. knowledge activation narrowing`
  - restrict `knowledge_activations` to immediate in-read use
- `C4. anchor-bank tightening`
  - keep `anchor_bank` as evidence territory only, not generic memory
- `C5. continuity-focused memory usability`
  - recover V1's practical memory-packet strength without regressing to V1's looser ontology

#### Landed packetization seam

- live prompt inputs no longer need to assemble context ad hoc inside each caller
- an internal `state_packet.v1` layer now derives bounded prompt inputs from current persisted stores
- `navigate.unitize` now receives a packetized `navigation_context`
- `read` now receives a packetized read-context view that explicitly separates:
  - `session_continuity_capsule`
  - `working_state_digest`
  - `chapter_reflective_frame`
  - `active_focus_digest`
  - `concept_digest`
  - `thread_digest`
  - `anchor_bank_digest`
- the current implementation intentionally keeps legacy compatibility aliases alongside the new packet fields so existing helpers and audits do not break while the deeper state migration is still pending
- the current Phase C.2 slice keeps persisted file names unchanged and derives the new concept/thread packet views from the existing:
  - `motif_index`
  - `unresolved_reference_index`
  - `trace_links`

#### Deterministic versus semantic boundary

Phase C should also make the execution boundary explicit.

Deterministic code should continue to own:

- sentence substrate
- locator and persistence work
- budget tracking
- observability
- resume / recovery
- safety guardrails

Deterministic code should not continue to own:

- semantic trigger worthiness
- semantic closure judgment
- semantic bridge worthiness

`navigate.unitize`, `read`, and `navigate.route` may decide what the mechanism believes, but durable state application should still happen through deterministic executors rather than turning one LLM call into an all-powerful state machine.

#### Validation target

- the mechanism should become better at long-distance continuity without turning back into one giant memory blob
- source-grounded evidence should stay intact
- excerpt-local pressure fidelity must still remain strong

### 7.4 Phase D — Recall, persistence, resume, and compaction polish

Goal:

- polish the system after the new reading loop and state shape are already real

This phase is intentionally later.

It should only happen after the earlier phases prove stable enough to justify additional complexity.

#### Landed scope

- `read` now requests supplemental context one bounded step at a time, while the runner may continue resolving those requests inside a budget-bounded multi-step loop rather than stopping after one extra pass
- runtime state and full checkpoints now persist a lightweight `continuation capsule`
  - the capsule carries bounded continuity digests plus explicit `rehydration entrypoints`
  - it is not a replacement summary for the full primary state layers
- warm resume remains `new-format only`, but it now restores the latest usable continuation capsule together with the new-format runtime/checkpoint state
- `look_back` remains exact-source only and now resolves at most one bounded earlier span
- private `read_audit` now records per-step supplemental activity, stop reasons, and budget exhaustion

#### Resulting posture

- Phase D strengthened continuity and resume without reopening the main control skeleton
- compaction still remains intentionally lighter than a full central compactor
- the next follow-up is now concretized as the `Read -> Express` split and compatibility migration rather than left implicit

### 7.5 Phase E — Read / Express split and visible-reaction contract cleanup

Landed status so far:

- `Phase E1` is landed.
- the first compatibility-first `Phase E2` slice is landed.
- `Phase E3` is landed.

Goal:

- keep `Read` centered on actual reading and implicit uptake
- move user-visible reaction wording into a dedicated `Express` node
- keep old reaction-family expectations only as compatibility adapters while the runtime and evaluation chain catch up

This phase is intentionally split. It should not be implemented as one giant sweep.

Why:

- the current live path, slow-cycle aggregation, eval exports, and compatibility projections still assume old-family reaction records in several places
- a one-shot rewrite would simultaneously change:
  - runtime packet shape
  - visible-reaction ownership
  - slow-cycle aggregation inputs
  - normalized eval exports
  - compatibility/UI adapters
- high-quality landing therefore depends on freezing the contract first, then cutting the live path, then cleaning the compatibility chain

#### Phase E1 — Contract freeze

Status: `landed`

Freeze the approved next-shape contract before code mutation.

- `Read vNext` should expose:
  - `unit_delta`
  - `implicit_uptake`
  - `pressure_signals`
  - `express_signal`
  - optional `context_request`
  - `anchor_evidence`
- `Express` should:
  - use one unified prompt rather than family-specific prompt branching
  - receive the exact current unit plus one narrow `express_signal`
  - emit at most one visible reaction in the first implementation slice
  - return:
    - `decision`
    - `anchor_quote`
    - `content`
    - optional `prior_link`
    - optional `outside_link`
    - optional `search_intent`
- old `highlight / association / curious / discern / retrospect / silent` family labels should be demoted to compatibility vocabulary only
  - `silent` becomes the `withhold` outcome of `Express`
  - `retrospect` becomes one adapter interpretation of surfaced `prior_link`

#### Phase E2 — Live-path cutover

Status: `first compatibility-first slice landed`

Cut the live runner over to the new ownership split.

- change the live path from:
  - `read.raw_reaction -> navigate.route`
- to:
  - `read -> express(if needed) -> navigate.route`
- `Read` should stop returning the final visible reaction payload on the live path
- `Navigate.route` should consume `pressure_signals` rather than a semantically over-decided `move_hint`
- `Express` should not own:
  - memory update
  - route choice
  - supplemental recall
- landed first-slice posture:
  - `Read` still carries legacy compatibility fields such as `raw_reaction`, `move_hint`, and `prior_material_use`
  - live visible-reaction persistence now comes from `ExpressResult`, not from `read.raw_reaction`
  - thin adapter mapping still projects `ExpressResult` back into old family-shaped reaction records for downstream compatibility

#### Phase E3 — Compatibility adapters and evaluation repair

Status: `landed`

Keep the old family only where the rest of the system still needs it.

- persisted visible reactions now keep surfaced semantics first:
  - `thought`
  - `prior_link`
  - `outside_link`
  - `search_intent`
- slow-cycle aggregation now derives compatibility family labels from persisted surfaced semantics rather than treating legacy `type` as the record truth
- eval / normalized bundles now emit legacy family labels as compat projections from those same native records
- UI/current-activity compatibility surfaces may continue to project old-family vocabulary temporarily
- those adapters are now thin mappings from persisted surfaced reaction records rather than a runner-side downcast from `ExpressResult`
- the adapter layer must not re-enter the prompt contract and redefine how `Express` thinks
- the narrow fallback from missing `ExpressResult` to legacy `read.raw_reaction` remains available only as a marked compatibility/exception path

#### Validation target

- visible reactions should sound like reading-time reactions again rather than mechanism-authored summaries
- `Read` should become easier to explain as reading plus implicit uptake rather than as a control super-node
- old-family compatibility should continue working long enough to avoid breaking slow-cycle/eval/public adapters during the transition
- persisted reaction truth should now be inspectable in native `Express` terms without reconstructing it from legacy family labels
- implementation should land in the required order:
  1. freeze contract
  2. cut live path
  3. clean compatibility / evaluation chain

## 8. Backend Compatibility Guardrails During Rework

This plan is backend-only, but it must not ignore existing frontend dependence.

The rule is:

- do not move frontend planning into this document
- but do keep backend changes compatibility-aware enough that parallel frontend work is not broken by surprise

Current guardrails:

- preserve current compatibility envelopes unless a later explicit contract change is intentionally staged
- avoid backend-only ontology changes that silently invalidate current public/state adapters
- prefer additive backend truth and adapter updates over abrupt surface breakage during the rework

## 9. Documentation Routing During This Initiative

To avoid document sprawl, each doc should keep one job.

### 9.1 Evaluation follow-up memo

File:

- [attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_followup_reflection_and_decisions.md](../../../reading-companion-backend/docs/evaluation/long_span/attentional_v2_accumulation_benchmark_v1_judged_rerun_20260407_followup_reflection_and_decisions.md)

Role:

- mechanism evidence and design reasoning source

### 9.2 This plan document

Role:

- implementation blueprint for the backend structural rework

### 9.3 Execution tracker

File:

- [new-reading-mechanism-execution-tracker.md](./new-reading-mechanism-execution-tracker.md)

Role:

- progress tracker
- current phase / checkpoint summary
- links to the current implementation plan

### 9.4 Stable docs

Examples:

- [docs/backend-reading-mechanisms/attentional_v2.md](../../backend-reading-mechanisms/attentional_v2.md)
- [docs/backend-reading-mechanism.md](../../backend-reading-mechanism.md)
- [docs/backend-state-aggregation.md](../../backend-state-aggregation.md)
- [docs/api-contract.md](../../api-contract.md)

Role:

- only update when real behavior lands

### 9.5 History decision log

File:

- [docs/history/decision-log.md](../../history/decision-log.md)

Role:

- record later inflection points once the rework becomes a real project-direction change in implemented behavior, not just a planning intention

## 10. Immediate Next Steps

The next concrete move should be:

1. treat `Phase A` and `Phase B` as the landed backend baseline rather than as open design questions
2. define the code-facing contract for `Phase C`:
   - typed state restructuring
   - carry-forward packet derivation that is easier to use and audit
   - clearer separation between always-carried continuity and on-demand exact recall
3. preserve current compatibility surfaces while Phase C lands
4. keep existing frontend work tracked in its own documents and tasks rather than under this plan

## 11. Success Criteria For This Plan

We should consider this rework direction on track only if all of the following remain true:

- long-span failures are addressed without regressing to section-first reading
- V2's excerpt strengths are preserved:
  - local pressure fidelity
  - anchored local reading
  - source-groundedness
- continuity improves without turning the system into one giant memory prompt
- backend changes stay compatible enough that parallel frontend work is not destabilized by surprise
