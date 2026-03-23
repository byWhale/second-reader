# New Reading Mechanism Validation Matrix

Purpose: define the verification required for each implementation phase so the mechanism does not look finished before its runtime, compatibility, and evaluation obligations are met.
Use when: planning work, defining phase exit gates, or checking whether a phase is genuinely done.
Not for: stable evaluation methodology or ad hoc benchmark results.
Update when: a phase gains new obligations, a check is split out, or acceptance criteria change.

## Validation Classes
- `unit`
  - deterministic helpers, schemas, validators, and state-operation rules
- `integration`
  - multi-component runtime behavior inside the backend
- `compatibility`
  - shared public-surface and adapter behavior
- `runtime`
  - checkpointing, resume, observability, and storage health
- `evaluation`
  - offline quality and mechanism-integrity checks under the shared eval frame
- `docs`
  - long-term doc updates required by landed behavior

## Phase Matrix
| Phase | Required validation | Class | Status |
| --- | --- | --- | --- |
| Phase 0 - Planning and scope lock | Confirm design coverage map exists and every major source block lands in a plan/tracker area. | `docs` | `planned` |
| Phase 1 - Runtime foundation and schemas | Validate core schemas, version surfaces, state-operation helpers, and artifact-root layout under `_mechanisms/<mechanism_key>/`. | `unit` / `integration` | `done` |
| Phase 2 - Sentence substrate and survey orientation | Prove sentence ids, locators, and bounded look-back are available from shared substrate; verify survey does not leak future paragraph-level knowledge. | `integration` / `runtime` | `done` |
| Phase 3 - Deterministic intake, gates, and retrieval scaffolding | Fixture-test trigger outputs, gate transitions, boundary nominations, and deterministic candidate generation. | `unit` / `integration` | `done` |
| Phase 4 - Core interpretive loop | Validate node contract IO for `zoom_read`, `meaning_unit_closure`, `controller_decision`, and `reaction_emission`; capture prompt manifests and prompt versions. | `integration` / `evaluation` | `done` |
| Phase 5 - Knowledge, memory, and bridge resolution | Verify recognition vs reading-warrant separation, source-anchor bridge targeting, relation writes, and knowledge/search policy transitions. | `unit` / `integration` / `evaluation` | `done` |
| Phase 6 - Slow-cycle reasoning and historical integrity | Verify promotion/supersede rules, reconsolidation append-and-link behavior, reaction immutability, and chapter carry-forward discipline. | `integration` / `runtime` / `evaluation` | `done` |
| Phase 7 - Persistence, checkpointing, and resume | Run warm/cold/reconstitution resume fixtures; verify no durable-anchor loss, no visible-reaction loss, and explicit reconstructed-state signaling. | `runtime` / `integration` | `done` |
| Phase 8 - Observability, evaluation, and shared-surface integration | Verify event streams, checkpoint summaries, normalized eval artifacts, and compatibility with analysis-state, activity, chapter, and marks surfaces. | `compatibility` / `runtime` / `evaluation` | `planned` |
| Phase 9 - Migration, stabilization, and default-cutover readiness | Run end-to-end comparison against `iterator_v1`, confirm acceptance ladder, and verify long-term doc promotions for every landed behavior change. | `evaluation` / `compatibility` / `docs` | `planned` |

## Minimum Acceptance Ladder
- `v0_internal`
  - core loop and state work on real text with internal observability
- `v0_resume_safe`
  - checkpointing and resume invariants hold under interruption
- `v0_adapter_safe`
  - shared product surfaces can consume the mechanism through adapters without ontology leakage
- `v1_acceptable`
  - shared evaluation frame shows the mechanism is viable enough for controlled product use

## Notes
- Runtime and evaluation work are not optional cleanup.
- A phase is not done if it only works in logs or only works in isolated prompt demos.
- If a phase changes stable behavior, update the relevant long-term docs in the same task and record it in `stable-doc-impact.md`.
