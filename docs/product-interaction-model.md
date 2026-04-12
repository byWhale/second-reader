# Product Interaction Model

Purpose: define the canonical product journey, page responsibilities, and interaction rules.
Use when: changing user flow, canonical frontend routes, page responsibilities, or compatibility-path behavior.
Not for: the stable product-purpose definition, field-level API schemas, endpoint wiring details, or temporary migration notes.
Update when: the primary product path, page responsibilities, or interaction model changes.

## Core Product Promise
- Stable product-purpose authority lives in `docs/product-overview.md`.
- This product's canonical interaction model assumes:
  - a living co-reader mind rather than a report generator
  - visible thought while reading rather than only after-the-fact outputs
  - marks and later return paths as part of the main experience rather than side utilities, while the chapter deep-read scene remains the primary place users return to
- Use this document for how that product purpose becomes journey, routes, page roles, and interaction rules.

## Primary Product Path
### 1. Landing
- Canonical route: `/`
- Role: introduce the product, frame the reading experience, and route users into the book workflow.
- Ownership: frontend-owned experience; it is not a backend compatibility surface.

### 2. Bookshelf
- Canonical route: `/books`
- Role: bookshelf, library management surface, and the main operational entry point into reading.
- Responsibilities:
  - show the user's available books and top-level reading states
  - host the primary upload entry for adding new books
  - route into a book home or directly back into active reading

### 3. Upload Entry
- Canonical entry point: `/books?upload=1`
- Role: let the user bring a book into the system through the bookshelf-hosted upload modal, which currently defaults to deferred outline parsing.
- `/upload` remains a compatibility redirect, not the primary product path.

### 4. Analysis Start And Resume
- Landing upload currently starts analysis immediately from the landing-hosted upload dialog.
- Bookshelf upload currently defaults to deferred outline parsing first.
- Deferred upload stops after chapter-level structure parsing.
- The bookshelf flow presents the `start now / later` decision only after the book reaches `ready`.
- `analysis/start` and `analysis/resume` perform semantic segmentation and continue the deep-reading workflow on the main long-task surface.
- That long-task surface now defaults to `attentional_v2`.
- `iterator_v1` remains a backend-level fallback and legacy-resume path rather than the primary product reader.

### 5. Book Overview
- Canonical route: `/books/:id`
- Role: main control center for an in-progress or completed book.
- Responsibilities:
  - show current analysis state
  - surface current reading activity
  - expose resume/continue actions
  - provide chapter access, book-scoped marks context, and dispatch into the chapter deep-read scene
  - preserve a consistent book-level identity across reading states, with a shared header and shared book navigation
  - shift the main stage between live reading activity while a book is in progress and structure/result entry once the book is completed
  - keep chapter-level structure and chapter-internal semantic sections clearly distinguished in visible naming

### 6. Chapter Deep Read
- Canonical route: `/books/:id/chapters/:chapterId`
- Role: chapter deep-read main page for reading, review, and return-to-context.
- This is the primary surface for consuming chapter-level deep-reading output, revisiting a finished chapter, and re-entering the active reading scene later.

### 7. Global Marks
- Canonical route: `/marks`
- Role: provide a cross-book saved-reaction list for things the user chose to keep.
- This page is a recall-and-jump surface into books and chapters, not the primary reading scene.

## Page Responsibilities
- Landing:
  - frame the experience
  - preview the product
  - route users into books/upload
- Bookshelf:
  - act as the operational entrypoint for library management and new uploads
  - route into book homes and active reading return paths
- Bookshelf upload flow:
  - default to deferred outline parsing, then offer `start now / later` once the book is ready
- Landing upload:
  - provide the immediate-start upload shortcut from the marketing/preview surface
- Book overview:
  - act as the adaptive home for progress, controls, state panels, and chapter navigation
  - route users back into the current or chosen chapter reading scene
- Chapter page:
  - act as the main chapter reading scene for deep-read output, later review, and return-to-context
  - be the default destination when the user wants to get back to "where the reading happened"
- Marks page:
  - act as the global saved-reaction list and cross-book recall surface
  - link users back into the relevant chapter scene without replacing it
- Compatibility analysis routes:
  - preserve legacy deep-reading entry and resume behavior
  - remain compatibility pages rather than the main V2-native design target

## Interaction Rules
- The canonical user journey is `landing -> books -> upload -> analysis -> book overview -> chapter -> marks`.
- Later re-entry should normally converge on `/books/:id/chapters/:chapterId` as the reading scene, whether the user starts again from `/books`, `/books/:id`, or `/marks`.
- Backend `target_url`, `result_url`, and `open_target` values should send users into canonical frontend routes.
- Compatibility routes may remain as redirects, but they should not become the primary user path without updating this document and `docs/api-contract.md`.
- Live analysis behavior depends on both the live snapshot (`analysis-state.current_reading_activity`) and the historical mindstream activity feed.

## Product Defaults
- `sequential` deep reading is the primary product mode and default optimization target.
- `book_analysis` is a shelved legacy capability preserved only as compatibility debt; it should not drive default product or architecture decisions.
- Do not reintroduce backend-owned landing or sample-browser flows unless that is an intentional product change.
- Do not broaden the default experience into a generic book-summary product without an explicit product decision.
