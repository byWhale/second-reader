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
- When working on cross-mechanism comparison or repair-oriented evaluation tasks, preserve both:
  - adoption candidates worth carrying forward from any mechanism
  - failure modes / anti-patterns worth avoiding later
  - do not let evaluation end at winner/loser language if the run exposed transferable strengths or repeatable mistakes
- If a meaningful evaluation or repair pass reveals transferable strengths, causal drivers, or repeatable failures, update the relevant docs in the same task:
  - the stable rule lives in `../docs/backend-reader-evaluation.md`
  - the living record lives in `../docs/implementation/new-reading-mechanism/mechanism-pattern-ledger.md`
  - if the finding changes project direction or would be hard to reconstruct later, also update `../docs/history/decision-log.md`
- Long-running eval or dataset-creation work must be registered durably instead of being tracked only in chat.
  - Use `state/job_registry/jobs/<job_id>.json` as the canonical source of truth for registered product and offline jobs.
  - Use `state/job_registry/active_jobs.json` and `state/job_registry/active_jobs.md` as the derived operator-facing views for offline long-running work.
  - Register jobs that are expected to run longer than roughly `10-15` minutes.
  - Before starting overlapping long-running work, refresh the registry first with the checker script.
  - Optimize for efficiency and automation by default when quality, reproducibility, and isolation can still be assured.
  - Independent offline jobs may be launched concurrently when they use isolated packets, datasets, run dirs, and job records.
  - The registry refresh is for overlap awareness and coordination, not a default instruction to serialize unrelated work.
  - If concurrent jobs converge on one shared global summary, schedule one follow-up refresh step after the concurrent jobs finish instead of treating that shared summary as the ownership of multiple parallel jobs.
- Do not stop at storing findings in docs.
  - After each meaningful evaluation round, investigate what specifically contributed to the result and turn the highest-value findings into a selective implementation plan.
  - Either implement a small number of fitting improvements in the current approved mechanism, or record an explicit defer reason.
  - Do not let findings accumulate as a passive backlog with no disposition.
- When explaining a meaningful evaluation result to the user, include the selective improvement strategy by default.
  - State the result, the likely contributing causes, and the next implementation moves together unless the user explicitly asks for analysis only.
- Do not synthesize mechanisms mechanically.
  - Keep the approved mechanism's overall framework, ontology, loop, and control strategy intact unless the task explicitly changes them.
  - Adopt only the strengths that fit that framework cleanly.
  - Reject or defer locally attractive behaviors that would distort the approved mechanism or reintroduce known anti-patterns.
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
- Keep the shared LLM provider registry, invocation gateway, and cross-runtime/eval trace contract in `src/reading_runtime/`.
- Keep mechanism-internal ontology local to the mechanism that owns it; do not force future readers to reuse `section` / `subsegment` concepts unless they genuinely fit.
- Prefer wrapping the current `iterator_reader` behind shared mechanism boundaries over copying API/job wiring into each new reader.
- Backend-wide infrastructure must not depend on `src.iterator_reader.models`; shared code should import neutral types from `src.reading_core/`.
- Treat `state/uploads/` as transient user-upload intake, not as the durable source library for manually curated books.
- Treat `state/library_inbox/` as the operator drop-zone for future source-book additions before they are canonically ingested.
- Treat `state/library_sources/` as the local durable source-library territory for repeated backend imports, demos, and evaluation preparation.
- Do not let public/private distribution handling become a primary organizer for dataset-platform work unless the task is explicitly about export, distribution, or legacy recovery.
- Treat `state/dataset_build/` as the durable dataset-platform coordination territory for source catalogs, intake summaries, and later build-loop control artifacts.
- Treat `state/eval_local_datasets/` as the local-only mirror for evaluation packages derived from private books; use it when excerpt/chapter packages should not be checked into the repo.
- Treat `state/job_registry/` as durable agent/eval background-job tracking territory for long-running offline work such as evaluation, packet audits, and dataset creation.
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
