# New Reading Mechanism Coverage Policy

Purpose: prevent silent loss of design detail during planning and implementation of the new reading mechanism.
Use when: deciding whether the prep is complete enough to begin implementation, or checking whether a design point is fully accounted for.
Not for: stable mechanism authority or implementation rationale.
Update when: the omission-control process changes.

## Core Promise
- We should not rely on memory, summaries, or chat context to preserve this design.
- Every meaningful design point from the original Notion page must be made explicit and traceable inside the repo before implementation proceeds deeply.

## Required Layers
- `source-mirror.md`
  - full-fidelity working mirror of the Notion page
  - preserves detail before normalization
- `design-capture.md`
  - normalized implementation digest
  - groups the design into execution-friendly structure
- `requirement-ledger.md`
  - atomic traceability layer
  - each requirement receives an explicit disposition and tracking fields

## Disposition Rule
- Every atomic design point must end in exactly one active disposition:
  - `planned_for_implementation`
  - `implemented`
  - `explicitly_deferred`
  - `explicitly_rejected`
  - `promoted_to_stable_docs`
- `missing` is not an allowed steady-state disposition.

## Traceability Rule
- Each atomic design point should have:
  - a stable requirement ID
  - a source section reference
  - a concise statement of the requirement
  - its disposition
  - linked implementation phase or task
  - validation expectation
  - stable-doc impact, if any

## Pre-Implementation Gate
- Before major coding begins, confirm all of the following:
  - the Notion design has a repo-local source mirror
  - the normalized digest exists
  - the requirement ledger exists
  - every major source block has at least one ledger entry
  - no major design block remains unclassified
  - open questions are explicit, not implicit holes

## Anti-Drift Rules
- Do not mark a requirement as “covered” only because it resembles another item.
- Do not merge multiple design ideas into one tracker item if that hides whether each one was actually implemented.
- Do not let implementation progress outrun the ledger.
- When a design point is intentionally deferred or rejected, record that decision explicitly instead of letting it disappear.

## Current Assessment
- `design-capture.md` is useful, but by itself is not enough to guarantee omission control.
- The omission-control foundation now exists:
  - split source mirror files preserve source ordering and contract detail
  - the requirement ledger has moved past seed coverage into atomic expansion
- Remaining refinement should add detail or split rows further where implementation needs it; it should not rebuild the omission-control foundation from scratch.
