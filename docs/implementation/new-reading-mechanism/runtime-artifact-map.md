# New Reading Mechanism Runtime Artifact Map

Purpose: define the concrete Phase 1 artifact ownership split between shared `_runtime/` and `_mechanisms/attentional_v2/`.
Use when: implementing state schemas, adding new files, or checking whether one artifact belongs to the universal shell or to the mechanism-private layer.
Not for: stable long-term runtime authority or public API contract authority.
Update when: the artifact layout, ownership boundary, or shell-envelope rule changes during implementation.

## Boundary Principle
- Shared `_runtime/` is a thin compatibility shell.
- `_mechanisms/attentional_v2/` owns the actual reading-mind state.
- The shell may add envelopes, ids, and compatibility sidecars.
- The shell must not replace original mechanism-authored reactions or thought objects with shell-invented wrappers.

## Shared `_runtime/`
- `_runtime/runtime_shell.json`
  - thin mechanism-neutral shell envelope
  - source of truth for:
    - mechanism key
    - mechanism version
    - policy version
    - high-level status and phase
    - shared cursor on shared substrate
    - references to original mechanism-authored objects
    - last checkpoint pointer
- `_runtime/checkpoint_summaries/*.json`
  - thin shared checkpoint summaries
  - source of truth for:
    - checkpoint id
    - cursor snapshot
    - resume kind
    - visible reaction ids
    - references to original mechanism-authored objects
- Existing compatibility files remain shared but are not yet redefined by this Phase 1 work:
  - `_runtime/run_state.json`
  - `_runtime/activity.jsonl`
  - `_runtime/parse_state.json`

## Mechanism `_mechanisms/attentional_v2/`
### Derived
- `_mechanisms/attentional_v2/derived/survey_map.json`
  - planned orientation artifact
- `_mechanisms/attentional_v2/derived/revisit_index.json`
  - planned retrieval index artifact
- `_mechanisms/attentional_v2/derived/chapter_result_compatibility/*.json`
  - mechanism-private current-contract compatibility projections built from original anchored reaction truth

### Runtime State
- `_mechanisms/attentional_v2/runtime/local_buffer.json`
- `_mechanisms/attentional_v2/runtime/local_continuity.json`
- `_mechanisms/attentional_v2/runtime/trigger_state.json`
- `_mechanisms/attentional_v2/runtime/working_pressure.json`
- `_mechanisms/attentional_v2/runtime/anchor_memory.json`
- `_mechanisms/attentional_v2/runtime/reflective_summaries.json`
- `_mechanisms/attentional_v2/runtime/knowledge_activations.json`
- `_mechanisms/attentional_v2/runtime/move_history.json`
- `_mechanisms/attentional_v2/runtime/reaction_records.json`
- `_mechanisms/attentional_v2/runtime/reconsolidation_records.json`
- `_mechanisms/attentional_v2/runtime/reader_policy.json`
- `_mechanisms/attentional_v2/runtime/resume_metadata.json`
- `_mechanisms/attentional_v2/runtime/checkpoints/*.json`
  - full mechanism-owned checkpoints

### Internal
- `_mechanisms/attentional_v2/internal/diagnostics/events.jsonl`
  - deep mechanism-private trace
- `_mechanisms/attentional_v2/internal/prompt_manifests/*.json`
  - node-level prompt manifests and versions

### Exports
- `_mechanisms/attentional_v2/exports/normalized_eval_bundle.json`
  - explicit eval-run export only
  - shared comparison surface built from persisted runtime, reaction, compatibility, and reflective artifacts

## Ownership Rule
- Shared `_runtime/` may own a field only if it can be described in mechanism-neutral terms.
- If a field needs `attentional_v2` ontology such as trigger, gate, pressure, bridge, reframe, promotion, or anchor-memory semantics, it belongs under `_mechanisms/attentional_v2/`.
- Product-core reading artifacts should remain mechanism-authored truth even when shared `_runtime/` points to them.

## Phase 1 Notes
- Phase 1 creates the artifact map and default state files.
- Phase 1 does not yet claim that `attentional_v2` parse or read execution is complete.
- Later phases fill these artifacts with real runtime behavior; Phase 6 adds durable reaction truth and mechanism-private chapter-result compatibility projections, and Phase 7 adds compact local continuity, resume metadata, full checkpoint payloads, and bounded warm/cold/reconstitution resume helpers without yet making `attentional_v2` a live parse/read path.
