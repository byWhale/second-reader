# Reading Companion Backend Agent Guide

Purpose: define backend-local engineering constraints for API, runtime, prompt, and artifact changes.
Use when: changing backend code, prompt flow, runtime behavior, artifact layout, or API payload shaping.
Not for: canonical product flow, public contract authority, or workspace-level document routing.
Update when: backend-local constraints, recurring pitfalls, or stable implementation boundaries change.

## Scope
- This directory contains the FastAPI API, sequential deep-reading engine, and runtime artifacts.
- Use `../docs/product-interaction-model.md` for product flow and `../docs/api-contract.md` for the public contract.
- Use `../docs/backend-reading-mechanism.md` for inner reader-unit selection, prompt assembly, and live attention-projection semantics.

## Stable Defaults
- Default to improving `sequential` deep-reading quality.
- Treat `book_analysis` as a secondary capability unless the task explicitly prioritizes it.
- If product intent is unclear, preserve the feeling of a thoughtful co-reader rather than drifting toward a generic summary product.

## Local Structure Rules
- Keep each major LangGraph or workflow node as an independent function when possible.
- Keep prompt templates under `src/prompts/`.
- Keep tool definitions under `src/tools/`.
- Prefer extending the current `iterator_reader` main path instead of introducing parallel architectures.
- Avoid adding new abstractions unless they clearly improve the current sequential deep-reading workflow.

## Current Main Path
- `main.py`
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
