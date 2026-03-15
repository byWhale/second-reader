# Reading Companion Frontend

Purpose: provide frontend-local run commands and clarify that workspace-level docs remain the primary entrypoint.
Use when: running the frontend in isolation or checking frontend-local reference files.
Not for: repo-wide rules, product flow authority, or public API contract authority.
Update when: frontend-local commands or frontend entrypoint expectations change.

This directory contains the Reading Companion web client.

## Primary Entry Point
- Start with `../AGENTS.md` for workspace rules and document routing.
- Use `AGENTS.md` in this directory for frontend-local engineering constraints.
- Use `ATTRIBUTIONS.md` only for license and attribution reference.

## Running Locally
- From the workspace root, prefer:
  - `make dev-frontend`
  - `make dev`
- From this directory only:
  - `npm install`
  - `npm run dev`
  - `npm run build`
