# Reading Companion Backend Agent Guide

Purpose: define backend-local engineering constraints for API, runtime, prompt, and artifact changes.
Use when: changing backend code, prompt flow, runtime behavior, artifact layout, or API payload shaping.
Not for: canonical product flow, public contract authority, or workspace-level document routing.
Update when: backend-local constraints, recurring pitfalls, or stable implementation boundaries change.

## Scope
- This directory contains the FastAPI API, the shared reading runtime shell, the current default `iterator_reader` implementation, and runtime artifacts.
- Use `../docs/product-overview.md` for product purpose and reader-quality target.
- Use `../docs/product-interaction-model.md` for product flow and `../docs/api-contract.md` for the public contract.
- Use `../docs/backend-reading-mechanism.md` for inner reader-unit selection, prompt assembly, and live attention-projection semantics.
- Use `../docs/backend-reader-evaluation.md` for reader-quality goals, evaluation layers, and offline eval methodology.

## Stable Defaults
- Default to improving `sequential` deep-reading quality.
- Treat `book_analysis` as a secondary capability unless the task explicitly prioritizes it.
- Treat `iterator_reader` as the current default mechanism, not as the only permanent backend architecture.
- If product intent is unclear, preserve the feeling of a thoughtful co-reader rather than drifting toward a generic summary product.

## Local Structure Rules
- Keep each major LangGraph or workflow node as an independent function when possible.
- Keep prompt templates under `src/prompts/`.
- Keep tool definitions under `src/tools/`.
- Keep canonical book substrate, shared runtime contracts, and cross-mechanism normalized output types in `src/reading_core/`.
- Put shared runtime/mechanism boundaries in backend-level infrastructure instead of burying them inside one mechanism package.
- Keep mechanism-internal ontology local to the mechanism that owns it; do not force future readers to reuse `section` / `subsegment` concepts unless they genuinely fit.
- Prefer wrapping the current `iterator_reader` behind shared mechanism boundaries over copying API/job wiring into each new reader.
- Backend-wide infrastructure must not depend on `src.iterator_reader.models`; shared code should import neutral types from `src.reading_core/`.
- Avoid new abstractions unless they clearly improve the current sequential workflow or future multi-mechanism comparability.

## Platform Direction
- The backend is evolving toward one shared runtime shell plus multiple mechanism-specific reader implementations.
- `iterator_reader` remains the current default mechanism until another mechanism is explicitly wired through the same shared boundary.
- `docs/backend-reading-mechanism.md` remains authoritative for the current `iterator_reader` internals, not for every possible future reader mechanism.

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
- Keep public API naming and normalization concerns at the API layer when internal runtime artifacts still use older names or identifiers.
- Be conservative about changes that mainly benefit `book_analysis` but add complexity to the main sequential path.

## Language Governance
- Follow `../docs/language-governance.md`.
- Backend owns content language, not full UI localization.
- When a system-state message must drive primary UI decisions, expose structured keys/params in addition to raw text.
- Raw activity/program-log text may remain backend-authored for compatibility and debugging.
