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
| Q1 | Does this design supersede `attentional_v2`, or does it need a new mechanism key? | File layout, docs, runtime registration, and migration naming all depend on this. | Phase 0 | `open` |
| Q2 | Does `public/book_document.json` already expose sentence-level ids and locators in the shape this mechanism needs? | The entire sentence-order loop, bounded look-back, and anchor precision depend on this substrate. | Phase 2 | `open` |
| Q3 | What is the exact artifact and schema split between shared `_runtime/` state and `_mechanisms/<mechanism_key>/` state for this mechanism? | Prevents ontology leakage into shared runtime surfaces. | Phase 1 | `open` |
| Q4 | How should a non-section runtime locus map to the current public surfaces that still expose compatibility fields such as `segment_ref`? | Needed for analysis-state, activity, and chapter/detail compatibility. | Phase 8 | `open` |
| Q5 | What is the initial reaction persistence mapping from anchored reactions to the current reaction storage and mark flows? | Needed to avoid breaking marks, activity, and chapter surfaces. | Phase 6 / 8 | `open` |
| Q6 | How much of search behavior belongs in version one versus a later increment, given the design's rare-search posture? | Affects node inventory, policy defaults, and implementation scope. | Phase 5 | `open` |
| Q7 | What exact bounded recent source window should `cold_resume` and `reconstitution_resume` reread? | Needed for honest state reconstruction and predictable runtime cost. | Phase 7 | `open` |
| Q8 | Which observability fields are required in standard mode versus debug-only mode? | Needed to keep evaluation useful without exploding runtime storage. | Phase 8 | `open` |
| Q9 | What dataset slices and acceptance thresholds will be used for mechanism-integrity and end-to-end evaluation? | Needed before comparing against `iterator_v1` or considering default promotion. | Phase 8 / 9 | `open` |
| Q10 | When should the detailed design be promoted from temporary docs into stable `docs/backend-reading-mechanisms/<mechanism>.md`? | Prevents stable docs from becoming a working notebook while also avoiding long-term drift. | Phase 0 / 9 | `open` |

## Resolved Questions
- None yet.

## Promotion Rule
- Resolve a question here first when the answer is still implementation-local or provisional.
- Promote the answer into a stable doc when:
  - it changes shared mechanism boundaries
  - it changes one mechanism's stable ontology or runtime behavior
  - it changes public state surfaces or evaluation methodology
  - it becomes a real decision-bearing direction
