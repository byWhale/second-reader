# New Reading Mechanism Temporary Decision Log

Purpose: record implementation-phase decisions, reversals, and temporary working agreements before they are promoted into stable docs.
Use when: a design or execution choice has been made and later work needs a durable record of why.
Not for: stable mechanism authority, public API authority, or informal brainstorming.
Update when: a decision is made, reversed, superseded, or promoted into a long-term doc.

## Working Rules
- Every entry should say whether it is still temporary or has been promoted into a stable doc.
- Use this file for implementation-project decisions, not for shared system rules that already belong elsewhere.
- If an entry becomes stable behavior, update the relevant long-term doc in the same task and mark the promotion here.

## Decision Table
| ID | Date | Status | Decision | Why | Promotion status |
| --- | --- | --- | --- | --- | --- |
| D-001 | 2026-03-23 | `accepted` | Use `docs/implementation/new-reading-mechanism/` as the temporary workspace for this implementation project. | The project is workspace-wide and needs one shared operational control surface. | `temporary_only` |
| D-002 | 2026-03-23 | `accepted` | Keep the new mechanism non-default during implementation. | The runtime shell, public-surface adapters, evaluation, and migration work are not complete yet. | `temporary_only` |
| D-003 | 2026-03-23 | `accepted` | Keep a repo-local structured design capture instead of relying only on the Notion page during implementation. | The upstream design is detailed but too flat for safe execution; the repo needs a hierarchical working mirror. | `temporary_only` |
| D-004 | 2026-03-23 | `accepted` | Do not promote the full working design into stable mechanism docs yet. | Stable docs should not become a running implementation notebook while key integration questions are still open. | `temporary_only` |

## Promotion Checklist
- Promote an entry when it changes:
  - shared mechanism boundaries
  - one mechanism's stable ontology or runtime behavior
  - public-state surface behavior
  - evaluation methodology
  - defaultness or migration direction
- When promoted, add:
  - stable doc path
  - task/date of promotion
  - whether the temporary entry is now obsolete or still useful as project history
