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
| D-005 | 2026-03-23 | `accepted` | Treat the new Notion design as the continuation and superseding working design of `attentional_v2`; do not mint a new mechanism key. | The stable `attentional_v2` doc already matches the same core identity: sentence-order intake, meaning-unit reasoning, unresolved interpretive pressure, survey orientation, dynamic focus, and non-default design-only status. The new design deepens and operationalizes that direction rather than defining a separate mechanism family. | `aligned_with_existing_stable_doc` |
| D-006 | 2026-03-23 | `accepted` | Keep `public/book_document.json` as the one shared parsed-book truth, but extend it with a neutral shared sentence layer; do not leave sentence traversal private to `attentional_v2` and do not introduce a second primary shared text artifact as the default plan. | The shared docs, shared types, parser, and representative test payloads show that `public/book_document.json` is paragraph-level today. Paragraph records and paragraph-span locators exist, and `iterator_v1` has sentence logic internally, but the shared substrate does not provide canonical sentence ids, sentence-order cursors, or sentence-to-locator mappings. The new mechanism needs stable sentence-order traversal, bounded look-back, and source-anchor precision, and sentence is a mechanism-neutral substrate concept rather than mechanism-private ontology. | `likely_shared_doc_promotion_after_phase_2` |

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
