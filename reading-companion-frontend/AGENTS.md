# Frontend Agent Guide

## Scope
- This directory contains the Reading Companion web client.
- The app started as a Figma Make export. Preserve the useful generated structure, but treat the backend API as the source of truth for data.

## Local Rules
- Keep route definitions centralized in `src/app/routes.tsx`.
- Keep raw API requests inside `src/app/lib/api.ts`.
- Do not spread ad-hoc `fetch()` calls across page components.
- Prefer preserving the existing visual language unless a task explicitly asks for redesign.
- Keep compatibility routes if backend-returned paths or older links still rely on them.

## Current Priorities
- reliable local integration with the backend
- stable route mapping
- upload, analysis, result, and mark flows backed by real API data

## Avoid By Default
- reintroducing mock data as the primary source of truth
- large component framework rewrites
- changing backend contract names on the frontend side without checking the backend
