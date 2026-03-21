# Backend Reading Mechanisms

Purpose: catalog backend reading mechanisms and define the stable authoring rules for mechanism-specific docs.
Use when: checking which mechanisms exist, which one is default, or how a mechanism doc should be structured.
Not for: shared runtime/platform rules, public schema authority, or historical decision logs.
Update when: a mechanism is added, removed, promoted, archived, or when the required structure for mechanism docs changes.

Use `docs/backend-reading-mechanism.md` for shared platform boundaries. Use `docs/backend-reading-mechanisms/<mechanism_key>.md` for one mechanism's actual internals.

## Catalog
| Mechanism key | Status | Defaultness | Doc | Artifact root | Notes |
| --- | --- | --- | --- | --- | --- |
| `iterator_v1` | `default` | current default/live mechanism | `docs/backend-reading-mechanisms/iterator_v1.md` | `_mechanisms/iterator_v1/` | current shipped section/subsegment reader |
| `attentional_v2` | `design-only` | not default | `docs/backend-reading-mechanisms/attentional_v2.md` | `_mechanisms/attentional_v2/` (planned) | future attention-frontier design |

## Status Meanings
- `default`
  - current live/default mechanism for normal product runs
- `experimental`
  - implemented but not default
- `design-only`
  - stable design authority exists, but no live implementation is claimed
- `archived`
  - preserved for history, migration, or rejected-direction context

## Required File Naming
- One stable doc per mechanism.
- The filename must match the mechanism key:
  - `iterator_v1.md`
  - `attentional_v2.md`
- Shared platform rules do not belong here; they belong in `docs/backend-reading-mechanism.md`.

## Required Metadata Block
Every mechanism doc must expose these lines near the top:
- `Status`
- `Mechanism key`
- `Defaultness`
- `Artifact root`
- `Authority scope`

## Required Section Structure
Every mechanism doc must use these top-level sections:
- `Purpose And Status`
- `Core Primitives / Ontology`
- `Reading Progression Logic`
- `LLM Call Schedule`
- `Context Packaging`
- `Memory And Revisit Logic`
- `Runtime Artifacts`
- `Public-State Projection`
- `Known Limits / Drift Notes`

Additional mechanism-specific sections are allowed when they clarify the design, but the shared structure above must remain present.

## Authoring Rules
- Mechanism docs own mechanism-private ontology and runtime behavior.
- Mechanism docs must not claim shared-platform authority.
- Design-only docs must say so explicitly and must not claim live/default behavior.
- If one mechanism depends on shared fields or artifact boundaries, describe the dependency briefly and point back to `docs/backend-reading-mechanism.md` or `docs/backend-state-aggregation.md` instead of redefining them.
- If the mechanism changes in a way that alters shared boundaries or defaultness, update the shared docs in the same task.

## When To Update Which Doc
- Update `docs/backend-reading-mechanism.md` when:
  - shared mechanism boundaries change
  - status categories change
  - routing between shared and per-mechanism docs changes
- Update this file when:
  - a mechanism is added, renamed, archived, or promoted
  - defaultness changes
  - mechanism-doc structure or authoring rules change
- Update one mechanism doc when:
  - that mechanism's ontology, loop, prompts, memory, artifacts, or fallback behavior changes

## Template
- Use `docs/backend-reading-mechanisms/_template.md` when creating a new mechanism doc.
