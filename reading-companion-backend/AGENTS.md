# Reading Companion Agent Guide

## Purpose
This file is for coding agents working in this repository.
It defines the current product focus, implementation boundaries, and code organization rules.
It is not the full product design document.

## Source of Truth
- Product design and positioning: Notion product page
- Current implementation truth: repository code
- This file: working rules and priorities for coding agents

## Current Product Focus
The current priority is to improve and productize the `sequential` deep-reading mode.

Primary user value:
- Help readers discover viewpoints, tensions, and blind spots they did not notice while reading nonfiction.
- The output should feel like a thoughtful co-reader, not a summary generator.

## Modes
### `sequential`
This is the primary mode and the default optimization target.

Goal:
- Produce high-signal, natural reading reactions
- Preserve the feeling of "AI thinking while reading"

### `book_analysis`
This mode exists, but it is not the current optimization focus.

Use it as a secondary capability for future development.
Do not prioritize it over sequential-mode quality unless the user explicitly asks.

## In Scope
When making product or code decisions by default, prioritize:
- better segment-level reading reactions
- better prompt quality and context packing
- stronger chapter-level coherence
- better search supplementation for genuine curiosity
- clearer evaluation of reading quality and cognitive increment
- reliability features such as checkpoint, resume, and budget control

## Out of Scope By Default
Do not treat these as current top priorities unless explicitly requested:
- expanding `book_analysis`
- designing new high-level modes
- building full product UI flows
- broadening into a generic "book summary" product
- reviving older architecture ideas that are no longer part of the current main path

## Implementation Rules
- Keep each major LangGraph or workflow node as an independent function when possible.
- Keep prompt templates under `src/prompts/`.
- Keep tool definitions under `src/tools/`.
- Prefer extending the current `iterator_reader` main path instead of introducing parallel architectures.
- Avoid adding new abstractions unless they clearly improve the current sequential deep-reading workflow.
- Preserve existing checkpoints, budgets, and output artifact conventions unless there is a strong reason to change them.

## Architecture Notes
Current main path:
- `main.py`
- `src/iterator_reader/parse.py`
- `src/iterator_reader/iterator.py`
- `src/iterator_reader/reader.py`

Sequential mode is the main product path.
`book_analysis` is a secondary path and should not drive default design decisions.

## Evaluation Focus
When improving the system, optimize for:
- whether reactions feel natural and non-mechanical
- whether output surfaces non-obvious insights
- whether search adds meaningful context instead of noise
- whether chapter notes are worth reading as co-reading artifacts
- whether the system remains stable under long-text execution

## Notes for Coding Agents
If product intent is unclear, default to improving the sequential deep-reading experience.
If a proposed change mainly benefits `book_analysis` but adds complexity to the main path, be conservative.
If the Notion product page and old repository wording conflict, prefer:
1. current Notion direction
2. current code reality
3. old wording only if still consistent with both
