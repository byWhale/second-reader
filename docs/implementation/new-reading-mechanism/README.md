# New Reading Mechanism Implementation Workspace

Purpose: hold the temporary working docs for implementing the new reading mechanism described in Notion.
Use when: planning, sequencing, tracking, or resolving design-to-code questions during the implementation project.
Not for: stable mechanism authority, public API authority, or final historical record.
Update when: the design capture, plan, tracker, or open-question set changes during implementation.

## Authority And Scope
- Upstream working design source(reading through MCP):
  - `https://www.notion.so/new-reading-mechanism-design-32ad8f1822a5805e9864cf1c3cd0551b`
- Stable project rules still come from:
  - root `AGENTS.md`
  - `reading-companion-backend/AGENTS.md`
  - `docs/backend-reading-mechanism.md`
  - `docs/backend-reading-mechanisms/README.md`
  - `docs/backend-reading-mechanisms/attentional_v2.md`
  - `docs/backend-reader-evaluation.md`
  - `docs/backend-state-aggregation.md`
  - `docs/backend-sequential-lifecycle.md`
- This folder is a temporary implementation workspace. It is allowed to be more operational and more detailed than the stable docs.
- When a conclusion becomes stable system behavior or a decision-bearing direction, promote it into the relevant long-term docs instead of leaving it here forever.

## Working Files
- `source-mirror.md`
  - full-fidelity repo-local mirror of the Notion design, organized by source section
  - should preserve detail before normalization
- `source-mirror-top-level.md`
  - source-faithful mirror of the top-level design blocks
- `source-mirror-contracts.md`
  - source-faithful mirror of the contract blocks and prompt-versioning rules
- `coverage-policy.md`
  - omission-control rules for this implementation project
- `design-capture.md`
  - repo-local structured capture of the Notion design
  - includes the source-to-workstream coverage map so scope does not disappear
- `requirement-ledger.md`
  - atomic traceability ledger mapping design points to implementation, deferral, rejection, or stable-doc promotion
- `implementation-plan.md`
  - the phased execution order, dependency chain, and exit criteria
- `execution-tracker.md`
  - the live checklist and progress tracker for the implementation effort
- `open-questions.md`
  - unresolved design and integration questions, plus temporary working assumptions
- `decision-log.md`
  - temporary implementation decisions, reversals, and promotion status
- `validation-matrix.md`
  - required verification by phase, including runtime, evaluation, and compatibility checks
- `evaluation-question-map.md`
  - question-first bridge between evaluation design and later dataset/corpus curation
  - separates cross-mechanism comparison, attentional-specific attribution, and runtime/compatibility gate questions
- `evaluation-corpus-requirements.md`
  - source-book and corpus-quality requirements for the future benchmark datasets
  - separates what curation can solve from what the source books must already satisfy
- `stable-doc-impact.md`
  - map of which long-term docs must be updated when each workstream lands
- `runtime-artifact-map.md`
  - concrete Phase 1 ownership split between shared `_runtime/` and `_mechanisms/attentional_v2/`
  - use this when adding new state files or checking whether one artifact belongs to the shell or the mechanism

## Working Rules
- Do not treat this folder as a replacement for the stable docs.
- Do not begin real implementation from the normalized digest alone when omission risk matters; first anchor the work to the source mirror and requirement ledger.
- Keep the design capture aligned to the Notion page, but normalize its hierarchy for implementation.
- Keep every major design block mapped to a workstream or tracker item.
- Every design point must end in exactly one explicit disposition:
  - implemented
  - explicitly deferred
  - explicitly rejected
  - promoted into stable docs
- Record implementation discoveries here first, then promote repeated stable facts into the long-term docs.
- Keep the new mechanism non-default until its acceptance gates, migration work, and public-surface adapters are complete.
- Do not let temporary tracker language silently redefine stable product or runtime behavior.

## Recommended Reading Order For This Project
1. `design-capture.md`
2. `coverage-policy.md`
3. `requirement-ledger.md`
4. `implementation-plan.md`
5. `execution-tracker.md`
6. `open-questions.md`
7. `evaluation-question-map.md`
8. `evaluation-corpus-requirements.md`
9. `runtime-artifact-map.md`
10. Stable docs listed above, as required by the task at hand
