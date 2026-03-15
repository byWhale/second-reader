# Case Study Docs

Purpose: define the project's job-search and portfolio documentation set, its allowed evidence sources, and its maintenance rules.
Use when: preparing interview materials, packaging the project for demos, extracting highlights, or updating project-story assets after major changes.
Not for: source-of-truth product behavior, public API authority, runtime semantics, or temporary migration notes.
Update when: this case-study doc set changes, its writing rules change, or the allowed evidence sources change.

This directory is the project's case-study layer. It sits between stable engineering docs and archive/reference material.

## What Belongs Here
- `overview.md`: one-page project summary for demos and external introductions
- `architecture.md`: system shape, main-path modules, and architecture evolution
- `decisions.md`: interview-worthy design trade-offs and why they were made
- `evidence.md`: hard evidence index for evals, tests, examples, and measurable checkpoints
- `interview-notes.md`: concise talk tracks and common follow-up answers

## Reading Order
1. `overview.md`
2. `architecture.md`
3. `decisions.md`
4. `evidence.md`
5. `interview-notes.md`

## Allowed Sources
All factual claims in this directory must trace back to one or more of these sources:
1. stable docs under `docs/`
2. code and tests in the repo
3. evaluation reports under `reading-companion-backend/docs/evaluation/`
4. repeatable command output such as `make test`, `make contract-check`, or `make e2e`

## Writing Rules
- Do not redefine engineering authority here. Link back to stable docs when a fact is already defined there.
- Prefer short, interview-usable summaries over long narrative reports.
- Every claim in `evidence.md` should point to a real file, command, output sample, or evaluation report.
- `interview-notes.md` may be more narrative, but it must not invent facts that do not already exist in the other files here.

## Maintenance Defaults
- Default engineering tasks should not load this directory.
- Major changes to product framing, architecture, trade-offs, or showcase evidence should update the relevant file here in the same task.
- Narrow bugfixes and routine refactors do not need to update this directory unless they materially change the project story.
