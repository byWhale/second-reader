# Case Study Docs

Purpose: define the minimal long-lived job-search documentation set and its maintenance boundary.
Use when: recording design trade-offs or evidence that would be hard to reconstruct later from code and stable docs alone.
Not for: reusable interview scripts, one-page summaries, architecture restatements, or source-of-truth engineering behavior.
Update when: the retained case-study files change, their maintenance rules change, or their allowed evidence sources change.

This directory is intentionally minimal. It only keeps information that is easy to forget and expensive to reconstruct later.

## What Belongs Here
- `decisions.md`: key product or engineering trade-offs, especially rejected alternatives and why the chosen path won
- `evidence.md`: the strongest evidence worth citing later, with links back to raw reports, commands, or artifacts

## What Does Not Belong Here
- summaries that can be regenerated later from stable docs and code
- architecture overviews that mostly restate engineering docs
- interview notes or talk tracks that can be generated on demand during interview prep
- implementation facts that are already authoritative in `docs/` or straightforward to recover from code

## Reading Order
1. `decisions.md`
2. `evidence.md`

## Allowed Sources
All factual claims in this directory must trace back to one or more of these sources:
1. stable docs under `docs/`
2. code and tests in the repo
3. evaluation reports under `reading-companion-backend/docs/evaluation/`
4. repeatable command output such as `make test`, `make contract-check`, or `make e2e`

## Writing Rules
- Do not redefine engineering authority here. Link back to stable docs when a fact is already defined there.
- If a point can be regenerated later from stable docs and code with low effort, do not store it here.
- Prefer recording why a decision was made or why a piece of evidence matters over repeating implementation details.
- Every claim in `evidence.md` should point to a real file, command, output sample, or evaluation report.

## Maintenance Defaults
- Default engineering tasks should not load this directory.
- Only update this directory when a major trade-off or a later-worthy evidence artifact would otherwise be lost.
- Narrow bugfixes, routine refactors, and summary-level project changes do not need to update this directory.
