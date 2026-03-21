# <Mechanism Name>

Purpose: describe one backend reading mechanism's internal ontology and runtime behavior.
Use when: changing this mechanism's reading logic, prompt/context assembly, memory behavior, or mechanism-private artifacts.
Not for: shared platform boundaries, public schema authority, or other mechanisms' internals.
Update when: this mechanism's ontology, progression logic, context packaging, memory model, or artifact behavior changes.

- Status: `<default | experimental | design-only | archived>`
- Mechanism key: `<mechanism_key>`
- Defaultness: `<current default | not default | former default>`
- Artifact root: `<_mechanisms/<mechanism_key>/ or planned path>`
- Authority scope: `<what this document owns>`

Use `docs/backend-reading-mechanism.md` for shared platform boundaries. Use `docs/backend-state-aggregation.md` for shared public-state surfaces.

## Purpose And Status
- Describe what this mechanism is for.
- State whether it is live, experimental, design-only, or archived.

## Core Primitives / Ontology
- Name the mechanism's private units and what each one means.
- Clarify which concepts are shared-platform dependencies vs mechanism-private primitives.

## Reading Progression Logic
- Describe how the mechanism moves through a book.
- Describe default movement, local dwell behavior, revisits, and fallback behavior.

## LLM Call Schedule
- Describe when the main LLM is called.
- Describe any planner, consolidation, or trigger-specific calls.

## Context Packaging
- Describe what text and memory the mechanism sends into each call.
- Clarify what local context, shared context, and retrieved history are included.

## Memory And Revisit Logic
- Describe how the mechanism stores continuity over time.
- Describe how earlier text becomes newly relevant and how the mechanism revisits it.

## Runtime Artifacts
- Describe mechanism-private derived, runtime, internal, and optional export artifacts.
- Keep shared `public/` and `_runtime/` rules out of this section except as dependencies.

## Public-State Projection
- Describe how this mechanism projects its internal state into shared public surfaces such as `current_reading_activity`.
- Clarify any compatibility fields that remain adapter-owned rather than native mechanism terms.

## Known Limits / Drift Notes
- Capture important limitations, unresolved questions, and areas where code may drift from the document over time.
