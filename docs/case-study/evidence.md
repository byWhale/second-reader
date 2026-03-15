# Case Study Evidence

Purpose: index the strongest factual evidence that supports project claims in demos, portfolio writeups, and interviews.
Use when: you need proof for architecture, quality, validation, or runtime claims.
Not for: long-form narrative explanation or source-of-truth product definitions.
Update when: new evaluation evidence, validation results, output examples, or measurable checkpoints become worth citing.

## Evaluation Reports
- Human-highlight comparison reports for three chapters plus one prompt-tuning before/after reference:
  - `reading-companion-backend/docs/evaluation/highlight_comparison_ch1.md`
  - `reading-companion-backend/docs/evaluation/highlight_comparison_ch2.md`
  - `reading-companion-backend/docs/evaluation/highlight_comparison_ch3.md`
  - `reading-companion-backend/docs/evaluation/highlight_comparison_ch3_before_prompt_tuning.md`
- Why it matters:
  - These files turn output quality discussion into something inspectable.
  - They identify recurring miss patterns such as perception density issues, role blind spots, and segmentation problems.

## Before / After Evidence
- `highlight_comparison_ch3_before_prompt_tuning.md` vs `highlight_comparison_ch3.md`
- Why it matters:
  - This pair gives a concrete "before and after" anchor for prompt and output-quality improvements.
  - It is stronger interview evidence than saying prompt quality was improved without artifacts.

## Stable Contract And Validation
- `docs/api-contract.md`
- `README.md` validation commands:
  - `make contract-check`
  - `make e2e`
  - `make test`
- Why it matters:
  - These show that the project cares about contract stability and canonical route behavior, not just local happy paths.

## Runtime And Recovery Evidence
- `docs/runtime-modes.md`
- `docs/api-contract.md` sections covering analysis state and job polling
- Why it matters:
  - These documents encode runtime-mode differences, resume semantics, and long-task surface expectations as explicit system behavior.

## Example Output And Demo Surfaces
- Canonical product surfaces:
  - `/`
  - `/books?upload=1`
  - `/books/:id`
  - `/books/:id/chapters/:chapterId`
  - `/marks`
- Output artifacts and examples remain under `reading-companion-backend/output/`
- Why it matters:
  - The project can be shown as a real product loop instead of a prompt-only prototype.

## Quantitative Anchors
- Evaluation reports expose chapter-level counts for:
  - human highlights
  - agent notes
  - hits
  - misses
  - agent-only findings
- Why it matters:
  - These numbers are limited in scope, but they are still more credible than unsupported quality claims.

## Usage Rule
- When citing project quality or engineering maturity in interviews, prefer referencing one or two concrete items from this file instead of making broad unsupported claims.
