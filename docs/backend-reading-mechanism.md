# Backend Reading Mechanism

Purpose: define the shared backend mechanism platform, ownership boundaries, and routing between shared mechanism docs and per-mechanism docs.
Use when: deciding what is universal across reader mechanisms, where mechanism internals should be documented, or which doc owns a given backend reading concept.
Not for: one mechanism's private reading loop, upload/start/resume lifecycle rules, public schema authority, or endpoint-level aggregation responsibilities.
Update when: shared mechanism boundaries, status model, mechanism catalog routing, or documentation ownership rules materially change.

Use `docs/backend-sequential-lifecycle.md` for the job-level workflow over time. Use `docs/backend-state-aggregation.md` for how runtime artifacts become public payloads. Use `docs/backend-reading-mechanisms/README.md` for the mechanism catalog and authoring rules. Use this file when the question is "what is shared across reading mechanisms?" or "which mechanism doc owns this topic?"

## Why This Doc Exists
- The backend no longer assumes one permanent reader mechanism.
- Shared runtime infrastructure, shared parsed-book substrate, and shared public-state boundaries now exist separately from any one mechanism's internal ontology.
- This file is the shared mechanism-platform authority.
- Mechanism-specific reading logic belongs in `docs/backend-reading-mechanisms/<mechanism_key>.md`.

## Shared Mechanism Boundary
- Shared substrate
  - `public/book_document.json` is the only shared parsed-book truth.
  - It contains canonical chapter order, paragraph records, sentence records, and locators.
  - The sentence layer is a parse-time, source-order, mechanism-neutral substrate, not a mechanism-private traversal plan.
  - It must not embed one mechanism's traversal ontology.
- Shared runtime shell
  - `src/reading_runtime/` owns mechanism registration, runtime routing, and shared artifact layout authority.
  - Shared canonical parse/provisioning helpers and shared sequential manifest/run-state builders also live under `src/reading_runtime/`.
  - The shared backend LLM invocation gateway, provider registry, and standard/debug trace contract also live under `src/reading_runtime/`.
  - Project-owned prompt-to-provider calls should use that shared gateway rather than instantiating provider clients inside one mechanism package or one-off eval code.
  - Top-level `public/` and `_runtime/` are shared cross-mechanism territory.
  - `_mechanisms/<mechanism_key>/` is mechanism-owned territory.
  - Internal mechanism selection may be carried through shared job/runtime plumbing by `mechanism_key`, even when the public HTTP contract still exposes only the current analysis routes.
- Shared public-state surface
  - Public API and websocket surfaces are allowed to expose stable compatibility fields such as `segment_ref`.
  - Internal mechanism structure must be adapted into shared public-state surfaces instead of leaking through directly.
- Shared evaluation seam
  - Mechanisms are compared through the shared evaluation frame and normalized runtime outputs, not by forcing one internal ontology.

## Content Ownership Rules
- Shared docs may define:
  - shared substrate and runtime boundaries
  - shared artifact ownership rules
  - shared public-state projection rules
  - shared evaluation frame
  - mechanism status and documentation-routing rules
- Shared docs must not define one mechanism's ontology as universal backend truth.
- Per-mechanism docs must own:
  - ontology and core primitives
  - reading loop and progression logic
  - prompt/context packaging
  - memory model
  - mechanism-private artifacts
  - fallback and drift notes
- Design-only mechanisms belong in the same stable mechanism-doc system as implemented mechanisms, but must be clearly labeled `design-only`.
- Experimental mechanisms should document their live parse/read entrypoints, runtime artifact root, and any intentionally unsupported modes such as legacy `book_analysis`.

## Terminology Discipline
- Shared docs should prefer neutral terms such as:
  - `book document`
  - `mechanism`
  - `current default mechanism`
  - `current attention target`
  - `mechanism-private artifact`
- Terms such as `section`, `subsegment`, `attention frontier`, or other mechanism-shaped primitives belong to the specific mechanism doc that owns them.
- Shared docs may mention mechanism-specific terms only when:
  - referring to a current compatibility surface
  - describing a specific mechanism by name
  - contrasting shared vs mechanism-private ownership

## Mechanism Status Model
- `default`
  - the current live/default mechanism for normal product runs
- `experimental`
  - implemented but not the default mechanism
- `design-only`
  - stable design documentation exists, but no live implementation is claimed
- `archived`
  - no longer the active direction, preserved for historical or migration reasons

## Current Catalog Snapshot
- Current catalog authority lives in `docs/backend-reading-mechanisms/README.md`.
- Current entries are:
  - `iterator_v1`
    - status: `default`
    - doc: `docs/backend-reading-mechanisms/iterator_v1.md`
    - artifact root: `_mechanisms/iterator_v1/`
  - `attentional_v2`
    - status: `experimental`
    - doc: `docs/backend-reading-mechanisms/attentional_v2.md`
    - artifact root: `_mechanisms/attentional_v2/`

## Routing Guide
- Read this file when the question is:
  - what is shared across reader mechanisms?
  - where should a mechanism concept be documented?
  - which artifact boundaries are universal vs mechanism-private?
  - how do statuses and defaults work across mechanisms?
- Read `docs/backend-reading-mechanisms/README.md` when the question is:
  - which mechanisms exist?
  - which one is default, experimental, design-only, or archived?
  - what structure must a new mechanism doc follow?
- Read `docs/backend-reading-mechanisms/iterator_v1.md` when the question is:
  - how does the current default mechanism actually read?
  - what does `section` or `subsegment` mean in the live system?
  - how does `iterator_v1` package prompts, memory, and progress?
- Read `docs/backend-reading-mechanisms/attentional_v2.md` when the question is:
  - how does the experimental non-default attention-frontier mechanism parse and read today?
  - what ontology or control loop does that mechanism own?

## Maintenance Rules
- Shared mechanism-boundary changes update this file.
- Mechanism catalog, status, or authoring-rule changes update `docs/backend-reading-mechanisms/README.md`.
- One mechanism's internal changes update only that mechanism doc plus any affected shared docs.
- Adding a new mechanism requires:
  - one new `docs/backend-reading-mechanisms/<mechanism_key>.md` file
  - one new catalog entry in `docs/backend-reading-mechanisms/README.md`
- Changing the default mechanism requires updating:
  - this file
  - `docs/backend-reading-mechanisms/README.md`
  - `docs/workspace-overview.md`
  - `docs/backend-sequential-lifecycle.md`
  - `docs/backend-state-aggregation.md`
  - `reading-companion-backend/AGENTS.md`
  - `docs/history/decision-log.md`

## Relationship To Other Docs
- `docs/backend-sequential-lifecycle.md`
  - owns the job lifecycle, start/resume behavior, and stage semantics
- `docs/backend-state-aggregation.md`
  - owns which persisted artifacts feed public backend surfaces
- `docs/backend-reader-evaluation.md`
  - owns the stable evaluation constitution across mechanisms
- `docs/backend-reading-mechanisms/README.md`
  - owns mechanism catalog details and authoring rules
- `docs/backend-reading-mechanisms/<mechanism_key>.md`
  - owns one mechanism's internal reading design
