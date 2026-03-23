# New Reading Mechanism Open Questions

Purpose: track unresolved design and integration questions that must be answered during implementation.
Use when: a task depends on a design choice that is not yet fixed in stable docs or code.
Not for: stable mechanism authority or final history.
Update when: a question is added, resolved, deferred, or replaced by a stable documented rule.

## Temporary Working Assumptions
- The new mechanism remains non-default during implementation.
- The public API contract stays stable until an intentional adapter or contract migration is ready.
- Prompt wording remains implementation-owned and versioned; contracts and invariants remain the design boundary.
- The repo-local design capture mirrors the Notion design as of `2026-03-23` and should be kept current enough for implementation planning.

## Open Questions
| ID | Question | Why it matters | Target phase | Current status |
| --- | --- | --- | --- | --- |
| Q3 | What is the exact artifact and schema split between shared `_runtime/` state and `_mechanisms/<mechanism_key>/` state for this mechanism? | Prevents ontology leakage into shared runtime surfaces. | Phase 1 | `open` |
| Q4 | How should a non-section runtime locus map to the current public surfaces that still expose compatibility fields such as `segment_ref`? | Needed for analysis-state, activity, and chapter/detail compatibility. | Phase 8 | `open` |
| Q5 | What is the initial reaction persistence mapping from anchored reactions to the current reaction storage and mark flows? | Needed to avoid breaking marks, activity, and chapter surfaces. | Phase 6 / 8 | `open` |
| Q6 | How much of search behavior belongs in version one versus a later increment, given the design's rare-search posture? | Affects node inventory, policy defaults, and implementation scope. | Phase 5 | `open` |
| Q7 | What exact bounded recent source window should `cold_resume` and `reconstitution_resume` reread? | Needed for honest state reconstruction and predictable runtime cost. | Phase 7 | `open` |
| Q8 | Which observability fields are required in standard mode versus debug-only mode? | Needed to keep evaluation useful without exploding runtime storage. | Phase 8 | `open` |
| Q9 | What dataset slices and acceptance thresholds will be used for mechanism-integrity and end-to-end evaluation? | Needed before comparing against `iterator_v1` or considering default promotion. | Phase 8 / 9 | `open` |
| Q10 | When should the detailed design be promoted from temporary docs into stable `docs/backend-reading-mechanisms/<mechanism>.md`? | Prevents stable docs from becoming a working notebook while also avoiding long-term drift. | Phase 0 / 9 | `open` |

## Resolved Questions
- `Q1` resolved on `2026-03-23`
  - Decision:
    - the new Notion design should be implemented under the existing `attentional_v2` mechanism key
    - it supersedes and deepens the earlier design-only `attentional_v2` description rather than creating a separate mechanism family
  - Why:
    - the stable `attentional_v2` doc already describes the same core direction:
      - sentence-order reading
      - meaning-unit reasoning
      - unresolved interpretive pressure under coverage discipline
      - survey orientation
      - dynamic non-section traversal
      - non-default future mechanism status
    - the new design adds tiered state, explicit operations, richer contracts, reconsolidation, observability, and evaluation traceability, but those are best understood as a more complete design for the same mechanism, not a rename-worthy break
  - Implementation effect:
    - use `_mechanisms/attentional_v2/`
    - keep `docs/backend-reading-mechanisms/attentional_v2.md` as the stable mechanism doc to be updated later under `Q10`
    - do not create a second design-only mechanism key unless a later design fork becomes intentionally distinct
- `Q2` resolved on `2026-03-23`
  - Audit basis:
    - shared docs currently define `public/book_document.json` as chapter order plus paragraph records and locators, not sentence records
    - shared types currently model chapter headings, paragraph records, and paragraph-span locators only
    - the current parser writes paragraph-classified chapters into `book_document.json` and does not persist sentence ids or sentence locators
    - the current `iterator_v1` reader does have runtime-local sentence splitting and sentence-indexed subsegments, but that logic is mechanism-private and is not part of the shared parsed-book substrate
  - Decision:
    - `public/book_document.json` is not sufficient as-is for the new mechanism's sentence-order loop
    - Phase 2 must upgrade the shared parsed-book substrate instead of relying on iterator-private sentence slicing
    - `public/book_document.json` should remain the one shared parsed-book truth, but it should be extended to carry a neutral shared sentence layer
    - sentence ids and sentence locators should not live only inside `_mechanisms/attentional_v2/`
    - a second parallel shared parsed-book truth artifact is not the primary plan
  - Why:
    - the new mechanism needs stable source-order sentence traversal, anchor precision, bounded look-back, and honest resume/reconstitution inputs
    - paragraph locators are useful prerequisites, but they do not by themselves provide canonical sentence ids, sentence-order cursors, or stable sentence-to-locator mappings
    - a sentence-order mechanism should not depend on non-canonical runtime-local splitting inside another mechanism
    - sentence is a mechanism-neutral substrate concept, unlike `section`, `subsegment`, or frontier-specific runtime state
    - keeping the shared sentence layer inside `book_document.json` preserves the current rule that the repo has one shared parsed-book truth instead of two competing shared text authorities
  - Implementation effect:
    - preserve existing chapter and paragraph records as shared substrate for compatibility
    - generate the shared sentence layer during canonical parse so sentence ids and cursors are stable across resume, evaluation, and multi-mechanism use
    - add a canonical shared sentence layer with stable ids, source-order indexing, and sentence-to-paragraph back-reference
    - extend locator support beyond today's paragraph-only shape so sentence spans can be anchored honestly enough for reactions, bridge targets, and resume reconstruction
    - treat any future companion sentence export as a derived optimization only if implementation proves it necessary; it should not become the primary authority without an explicit shared-doc change
  - Minimum schema direction:
    - add a neutral chapter-level sentence inventory
    - give each sentence record a stable `sentence_id`
    - preserve chapter-local source order
    - map each sentence back to one paragraph or paragraph span
    - carry sentence-span locator data precise enough for anchor and look-back use, including offsets when paragraph-level locators alone are not sufficient

## Promotion Rule
- Resolve a question here first when the answer is still implementation-local or provisional.
- Promote the answer into a stable doc when:
  - it changes shared mechanism boundaries
  - it changes one mechanism's stable ontology or runtime behavior
  - it changes public state surfaces or evaluation methodology
  - it becomes a real decision-bearing direction
