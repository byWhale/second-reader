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
- `design-capture.md`
  - repo-local structured capture of the Notion design
  - includes the source-to-workstream coverage map so scope does not disappear
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
- `stable-doc-impact.md`
  - map of which long-term docs must be updated when each workstream lands

## Working Rules
- Do not treat this folder as a replacement for the stable docs.
- Keep the design capture aligned to the Notion page, but normalize its hierarchy for implementation.
- Keep every major design block mapped to a workstream or tracker item.
- Record implementation discoveries here first, then promote repeated stable facts into the long-term docs.
- Keep the new mechanism non-default until its acceptance gates, migration work, and public-surface adapters are complete.
- Do not let temporary tracker language silently redefine stable product or runtime behavior.

## Recommended Reading Order For This Project
1. `design-capture.md`
2. `implementation-plan.md`
3. `execution-tracker.md`
4. `open-questions.md`
5. Stable docs listed above, as required by the task at hand
