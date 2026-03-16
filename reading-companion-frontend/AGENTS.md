# Frontend Agent Guide

Purpose: define frontend-local constraints for routes, API adapters, UI copy, and generated structure.
Use when: changing frontend routes, API integration, locale-driven text, or Figma Make-derived code.
Not for: canonical product flow, public contract authority, or workspace-level document routing.
Update when: frontend-local constraints, recurring pitfalls, or stable implementation boundaries change.

## Scope
- This directory contains the Reading Companion web client.
- Use `../docs/product-interaction-model.md` for product flow and `../docs/api-contract.md` for the public contract.

## Local Rules
- Keep route definitions centralized in `src/app/routes.tsx`.
- Keep raw API requests inside `src/app/lib/api.ts`.
- Do not spread ad-hoc `fetch()` calls across page components.
- Preserve the useful Figma Make-generated structure unless a clear maintenance problem justifies cleanup.
- Prefer preserving the existing visual language unless a task explicitly asks for redesign.
- Keep compatibility routes if backend-returned paths or older links still rely on them.
- For changes that affect visible UI, interaction flows, layout, scrolling, responsiveness, or route behavior, validate the result in a real browser after implementation.
- Prefer using Playwright-based tooling to inspect the actual page state instead of relying only on static code review.
- If browser validation is skipped because the environment blocks it, say so explicitly in the handoff and name the missing verification.

## Integration Constraints
- Do not reintroduce mock data as the primary source of truth.
- Do not change backend contract names on the frontend side without checking the backend.
- Keep route normalization aligned with the canonical frontend routes returned by the backend.
- Avoid large component framework rewrites unless the task explicitly calls for one.

## Language Governance
- Follow `../docs/language-governance.md`.
- Core UI text must come from the locale layer, not ad-hoc string literals in components.
- Key terms must come from the product lexicon.
- Key sentence-level UI copy must come from the controlled copy catalog.
- Only content values may remain in the book/content language; control and status text must follow `appLocale`.
