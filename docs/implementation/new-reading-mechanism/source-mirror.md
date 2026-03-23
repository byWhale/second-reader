# New Reading Mechanism Source Mirror

Purpose: keep a repo-local, full-fidelity working mirror of the upstream Notion design so no detailed point depends on memory or a compressed summary.
Use when: verifying exact design intent, checking whether a detail has been captured, or deriving atomic requirements.
Not for: normalized execution planning or stable mechanism authority.
Update when: the upstream Notion design materially changes or when the mirror is incomplete.

## Mirror Policy
- This file should preserve the source design with minimal interpretation.
- The goal is detail preservation first, hierarchy improvement second.
- Normalization belongs in `design-capture.md`, not here.

## Upstream Source
- Notion page:
  - `https://www.notion.so/new-reading-mechanism-design-32ad8f1822a5805e9864cf1c3cd0551b`
- Mirror status:
  - `split_mirror_completed`
- Last checked:
  - `2026-03-23`

## Capture Instructions
- Mirror the source section by section.
- Preserve ordering.
- Preserve important distinctions, invariants, failure conditions, and contract details.
- Avoid rewriting detailed design points into shorter interpretations here.
- If a source block is too long for one clean section, split it into subsections but keep the original order and labeling clear.

## Mirror Files
- `source-mirror.md`
  - index and capture standard
- `source-mirror-top-level.md`
  - source-faithful mirror of the top-level design blocks in original order
- `source-mirror-contracts.md`
  - source-faithful mirror of the behavior-defining contract blocks

## Current Limitation
- The repo currently has a normalized working digest in `design-capture.md`.
- The mirror is now split across dedicated files because the source is too large for one clean mirror file.
- Remaining work should extend or correct the split mirror files when upstream design changes or when implementation uncovers a fidelity gap, not collapse them back into summary form.

## Current Source Outline
The following source blocks were confirmed from the Notion page and must all be accounted for during implementation prep:

### Top-Level Source Blocks
1. Goal
2. First Principles
3. Core Principle
4. What Broad Prior Knowledge Is For
5. Core Runtime Objects
6. Tiered Reading State
7. Working Pressure
8. Anchor Memory
9. Reflective Summaries
10. State Operations
11. Knowledge Activation Objects
12. Knowledge-Use Policy
13. Search Policy
14. Bridge Retrieval
15. Book Survey First
16. Qualitative Escalation Gates
17. Main Reading Loop
18. Controller
19. Version-One Candidate-Boundary Signals
20. How Focus Is Selected
21. Version-One Trigger Ensemble
22. Trigger Ensemble Output Schema
23. When To Zoom To Sentence Level
24. LLM Call Policy
25. Zoom Read Call
26. What Each Interpretive Call Should Return
27. Prompt Packet
28. Non-Cheating Constraint
29. User-Visible Output
30. Reconsolidation
31. Anti-Miss Safeguards
32. Persistence and Resume
33. Relationship To The Existing Mechanism
34. Success Standard
35. Decisions Made So Far
36. Calibration and Configuration Layer
37. Failure Modes And Degradation Patterns
38. Instrumentation and Observability Contract
39. Evaluation Mapping And Acceptance Criteria
40. Open Design Questions

### Behavior-Defining Prompt Contract Blocks
1. `zoom_read` Contract v0
2. `meaning_unit_closure` Contract v0
3. `controller_decision` Contract v0
4. `bridge_resolution` Contract v0
5. `candidate_generation` Contract v0
6. `reaction_emission` Contract v0
7. `reflective_promotion` Contract v0
8. `reconsolidation` Contract v0
9. `book_survey` Contract v0
10. `chapter_consolidation` Contract v0

## Mirror Completion Standard
- We should not call this file a completed full-fidelity mirror until:
  - each top-level source block is mirrored in `source-mirror-top-level.md`
  - each prompt contract block is mirrored in `source-mirror-contracts.md`
  - ordering remains recoverable against the Notion page
  - the requirement ledger can point back to concrete mirror sections instead of only the upstream page
