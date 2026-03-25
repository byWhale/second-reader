# Reading Companion Backend Agent Guide

Purpose: define backend-local engineering constraints for API, runtime, prompt, and artifact changes.
Use when: changing backend code, prompt flow, runtime behavior, artifact layout, or API payload shaping.
Not for: canonical product flow, public contract authority, or workspace-level document routing.
Update when: backend-local constraints, recurring pitfalls, or stable implementation boundaries change.

## Scope
- This directory contains the FastAPI API, the shared reading runtime shell, the current default `iterator_reader` implementation, and runtime artifacts.
- Use `../docs/product-overview.md` for product purpose and reader-quality target.
- Use `../docs/product-interaction-model.md` for product flow and `../docs/api-contract.md` for the public contract.
- Use `../docs/backend-reading-mechanism.md` for shared backend mechanism-platform boundaries and documentation routing.
- Use `../docs/backend-reading-mechanisms/iterator_v1.md` for the current default mechanism's inner reader-unit selection, prompt assembly, and live attention-projection semantics.
- Use `../docs/backend-reader-evaluation.md` for reader-quality goals, evaluation layers, and offline eval methodology.

## Stable Defaults
- Default to improving `sequential` deep-reading quality.
- Treat `book_analysis` as a secondary capability unless the task explicitly prioritizes it.
- Treat `iterator_reader` as the current default mechanism, not as the only permanent backend architecture.
- Treat `attentional_v2` as the current experimental non-default mechanism: it now has a live parse/read path, but it must not silently become the default or inherit unsupported `book_analysis` behavior.
- If product intent is unclear, preserve the feeling of a thoughtful co-reader rather than drifting toward a generic summary product.
- When working on benchmark or evaluation tasks, apply dual diagnosis:
  - inspect mechanism weakness
  - inspect dataset / case / harness weakness
  - do not blame one side by default
- Current dataset-hardening rule:
  - use multi-prompt LLM adjudication as the default packet reviewer unless the user explicitly requests manual human review
  - treat manual human review as optional future escalation for higher-trust `gold` slices, not as the default blocker for current benchmark hardening

## Local Structure Rules
- Keep each major LangGraph or workflow node as an independent function when possible.
- Keep shared prompt fragments and cross-mechanism capability prompt families under `src/prompts/`.
- Keep mechanism-private prompt bundles with the mechanism implementation that owns them.
- Keep tool definitions under `src/tools/`.
- Keep canonical book substrate, shared runtime contracts, and cross-mechanism normalized output types in `src/reading_core/`.
- Put shared runtime/mechanism boundaries in backend-level infrastructure instead of burying them inside one mechanism package.
- Keep shared canonical parse/provisioning and shared sequential manifest/run-state builders in `src/reading_runtime/`.
- Keep mechanism-internal ontology local to the mechanism that owns it; do not force future readers to reuse `section` / `subsegment` concepts unless they genuinely fit.
- Prefer wrapping the current `iterator_reader` behind shared mechanism boundaries over copying API/job wiring into each new reader.
- Backend-wide infrastructure must not depend on `src.iterator_reader.models`; shared code should import neutral types from `src.reading_core/`.
- Treat `state/uploads/` as transient user-upload intake, not as the durable source library for manually curated books.
- Treat `state/library_sources/` as the local durable source-library territory for repeated backend imports, demos, and evaluation preparation.
- Treat `state/eval_local_datasets/` as the local-only mirror for evaluation packages derived from private books; use it when excerpt/chapter packages should not be checked into the repo.
- Treat `eval/datasets/` and `eval/manifests/` as evaluation-package territory; do not use transient uploads as the benchmark corpus by default.
- Avoid new abstractions unless they clearly improve the current sequential workflow or future multi-mechanism comparability.

## Platform Direction
- The backend is evolving toward one shared runtime shell plus multiple mechanism-specific reader implementations.
- `iterator_reader` remains the current default mechanism until another mechanism is explicitly wired through the same shared boundary.
- `attentional_v2` is now wired through that shared boundary as an experimental end-to-end runner, but remains non-default.
- `docs/backend-reading-mechanism.md` is authoritative for shared mechanism-platform rules.
- `docs/backend-reading-mechanisms/iterator_v1.md` is authoritative for current `iterator_reader` internals.

## Current Default Mechanism Path
- `main.py`
- `src/reading_core/`
- `src/reading_runtime/`
- `src/reading_mechanisms/iterator_v1.py`
- `src/iterator_reader/parse.py`
- `src/iterator_reader/iterator.py`
- `src/iterator_reader/reader.py`

## Runtime And Artifact Constraints
- Preserve existing checkpoints, resume behavior, budget controls, and output artifact conventions unless the task is explicitly migrating them.
- Treat `public/book_document.json` as the only shared parsed-book truth.
- Keep top-level `public/` limited to cross-mechanism, product-facing artifacts.
- Keep top-level `_runtime/` limited to cross-mechanism live shell state.
- Keep anything that depends on `section`, `subsegment`, planner state, reader memory, or mechanism-specific diagnostics under `_mechanisms/<mechanism_key>/`.
- Shared backend code must use neutral storage/runtime helpers instead of hardcoding `iterator_reader`-specific artifact paths.
- Public aggregation may read mechanism-private artifacts through adapters or helpers, but it must not treat them as universal substrate.
- Normal product runs must not persist normalized comparison bundles; mechanism export files such as `_mechanisms/<mechanism_key>/exports/normalized_eval_bundle.json` are reserved for explicit eval runs.
- Compatibility fallback for older output directories is required until an explicit cleanup or migration step removes it.
- Keep public API naming and normalization concerns at the API layer when internal runtime artifacts still use older names or identifiers.
- Be conservative about changes that mainly benefit `book_analysis` but add complexity to the main sequential path.
- Keep one stable doc per mechanism under `../docs/backend-reading-mechanisms/`, named by mechanism key.
- When one mechanism's internals change, update that mechanism doc in the same task.

## Language Governance
- Follow `../docs/language-governance.md`.
- Backend owns content language, not full UI localization.
- When a system-state message must drive primary UI decisions, expose structured keys/params in addition to raw text.
- Raw activity/program-log text may remain backend-authored for compatibility and debugging.
