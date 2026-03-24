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
| Phase 8 - Observability, evaluation, and shared-surface integration | Verify additive anchor/locus public fields, event streams, checkpoint summaries, normalized eval artifacts, and compatibility with analysis-state, activity, chapter, and marks surfaces. | `compatibility` / `runtime` / `evaluation` | `done` |
| Phase 8.5 - Live runner integration | Verify shared provisioning/job propagation, real `attentional_v2` parse/read runs, resume/recovery mechanism-key continuity, non-iterator compatibility aggregation, and unchanged public contract gates. | `integration` / `compatibility` / `runtime` / `docs` | `done` |
| Phase 9 - Migration, stabilization, and default-cutover readiness | Run end-to-end comparison against `iterator_v1`, confirm acceptance ladder, and verify long-term doc promotions for every landed behavior change. | `evaluation` / `compatibility` / `docs` | `in_progress` |

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
- The first Phase 8 landing now requires focused compatibility tests for:
  - `analysis-state.current_reading_activity.reading_locus`
  - runtime-shell-backed additive locus projection
  - additive `primary_anchor` preservation across chapter, activity, and marks payloads
- The next Phase 8 landing now also requires runtime validation for:
  - shared runtime shell carrying `observability_mode`
  - shared checkpoint summaries carrying `observability_mode`
  - standard checkpoint/resume events being written to `_runtime/activity.jsonl`
  - debug diagnostics events appearing only when debug mode is enabled
- The current Q9 landing now also requires evaluation/runtime validation for:
  - normalized eval bundle export from persisted `attentional_v2` artifacts
  - structural integrity checks over cursor sentence ids, anchor locators, reconsolidation links, Q7 resume-policy bounds, and compatibility projections
- The new Phase 8.5 landing now also requires integration/runtime validation for:
  - shared `mechanism_key` propagation through launch, resume, auto-resume, and incompatible fresh rerun flows
  - live `attentional_v2` parse/read entrypoints without iterator `structure.json`
  - explicit `attentional_v2 + book_analysis` failure behavior
  - `make contract-check` staying green after the runner integration
- Before any Phase 9 dataset curation, freeze the evaluation-question map so dataset design stays question-driven instead of convenience-driven.
- Before screening or collecting the real source-book pool, freeze the corpus-requirements doc so source-book selection is standards-driven instead of ad hoc.
- The public-first large `v2` build now satisfies the dataset-layer prerequisite for serious evaluation:
  - tracked chapter corpora:
    - `18` English
    - `18` Chinese
  - tracked runtime fixtures:
    - `36` English
    - `36` Chinese
  - tracked curated excerpt cases:
    - `16` English
    - `16` Chinese
  - tracked shared compatibility fixtures:
    - `36`
- Future Phase 9 validation should treat the tracked `v2` benchmark family as the default benchmark input set unless a later gap-filling pass explicitly supersedes it.
- Future Phase 8 / 9 work still needs explicit validation for the eventual removal of section-first chapter/detail and marks assumptions.
- Future Phase 9 work still needs deeper node-level observability validation once standard/debug traces are expanded across the full live interpretive loop.
