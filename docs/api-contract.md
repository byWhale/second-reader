# API Contract

## Purpose
This document is the current single source of truth for frontend and backend API integration in the Reading Companion workspace.

Use it to align:
- backend response schemas and OpenAPI output
- frontend route assumptions and type definitions
- mark/reaction/book/chapter identifiers exposed to the web client

This document describes the public product contract. It does not require the backend's internal artifact layout or reader pipeline to use the same names internally.

## Source Of Truth
- Canonical public contract: this file
- Backend schema implementation: `reading-companion-backend/src/api/schemas.py`
- Backend route handlers and payload shaping: `reading-companion-backend/src/api/app.py` and `reading-companion-backend/src/library/catalog.py`
- Frontend type layer and route normalization: `reading-companion-frontend/src/app/lib/api-types.ts`, `reading-companion-frontend/src/app/lib/api.ts`, and `reading-companion-frontend/src/app/routes.tsx`

If this file and the code diverge, treat that as a defect. Do not silently "pick one side". Verify both sides and fix the mismatch.

## Reaction Taxonomy

### Canonical Reaction Types
The public UI and API expose exactly five reaction types:

- `highlight`
- `association`
- `discern`
- `retrospect`
- `curious`

No other public reaction type should appear in:
- REST responses
- WebSocket event payloads
- frontend filters
- frontend type definitions
- page labels or route-derived state

### Compatibility Mapping
Some older code and artifacts still use legacy names internally. Public responses must normalize them to the canonical taxonomy above.

Current compatibility mappings:
- legacy frontend `critique` -> `discern`
- legacy frontend `curiosity` -> `curious`
- legacy frontend `insight` -> removed
- legacy backend/internal `connect_back` -> `retrospect`

### Chapter Filter Values
Chapter-page filters only allow:

- `all`
- `highlight`
- `association`
- `discern`
- `retrospect`
- `curious`

The following older conceptual filters are not part of the public contract and should not reappear in the live UI or API:

- `blindspots`
- `cross-chapter`
- `background`

## Canonical Routes

### Canonical Frontend Routes
These are the primary routes the frontend should render and the backend should return in fields such as `open_target`, `target_url`, and `result_url`:

- `/` -> Landing
- `/books` -> Books
- `/books/:id` -> Book overview
- `/books/:id/chapters/:chapterId` -> Chapter deep read
- `/marks` -> Global My Marks

### Compatibility Routes
These may remain as redirects for older links, but they are not canonical:

- `/bookshelf`
- `/book/:bookId`
- `/book/:bookId/chapter/:chapterId`
- `/books/:id/analysis`
- `/analysis/:bookId`
- `/bookshelf/marks`

### Current Implementation Note
`/upload` remains as a compatibility utility route in the frontend, but it now redirects into the bookshelf-hosted upload modal flow (`/books?upload=1`).

## ID Conventions
All public identifiers exposed to the frontend are integers:

- Book ID: integer
- Chapter ID: integer
- Reaction ID: integer
- Mark ID: integer

This applies to:
- REST response payloads
- WebSocket envelopes and event payloads
- route params used by the frontend
- frontend API adapter types

Internal runtime storage may still use string artifact identifiers. That is an implementation detail. Public handlers must translate internal identifiers into stable public integer IDs before returning them.

## Landing Strategy
Landing is a frontend-owned experience in the current implementation.

Current implementation strategy:
- landing copy is hardcoded in the frontend
- the six landing display cards are hardcoded in the frontend
- sample teaser content may be hardcoded in the frontend

This is a product implementation choice, not a general backend capability promise.

## Book Overview Ownership

### Backend-Owned Fields
The backend is responsible for providing these book-overview fields:

- `reaction_counts`
- `chapter_count`
- `completed_chapter_count`
- `segment_count`

`reaction_counts` must be keyed by the five canonical reaction types only.

### Frontend-Derived Metrics
The frontend may derive factual display summaries from backend counts when needed, such as:

- total reactions across a book
- completed chapters out of total chapters

Do not add backend-only convenience fields for opinionated or evaluative frontend metrics unless the current implementation has a concrete dependency that cannot be simplified.

## Marks Contract

### Global Marks
- Endpoint: `GET /api/marks`
- Response shape: paginated flat list
- Frontend responsibility: group by book for display

### Book-Scoped Marks
- Endpoint: `GET /api/books/:id/marks`
- Response shape: marks grouped by chapter
- Frontend responsibility: render the grouped structure directly

### Required Mark Fields
Every returned mark must include at least:

- `mark_id`
- `reaction_id`
- `book_id`
- `chapter_id`
- `mark_type`
- `reaction_type`
- `anchor_quote`
- `created_at`

### Mark Value Rules
- `mark_type` only allows `resonance`, `blindspot`, or `bookmark`
- `reaction_type` must always come from the canonical reaction taxonomy
- UI copy and contract language should consistently use `resonance`, `blindspot`, and `bookmark`

Avoid reintroducing older presentation-only phrases such as:
- `Known`
- `I knew this`

except as migration compatibility text where the underlying value remains in the canonical mark taxonomy.

## Other Stable Envelopes

### Analysis State
`GET /api/books/:id/analysis-state` should continue to expose:

- public integer `book_id`
- chapter tree items with integer `chapter_id`
- parse-stage and deep-reading-stage progress in the same payload
- `current_phase_step`, `resume_available`, and `last_checkpoint_at` when available
- `current_reading_activity` as a live snapshot, not a history event, including:
  - `phase`
  - `started_at`
  - `updated_at`
  - optional `segment_ref`
  - optional `current_excerpt`
  - optional `search_query`
  - optional `thought_family`
  - optional `problem_code`
- `current_state_panel.reaction_counts` keyed only by the five canonical reaction types
- `recent_completed_chapters[].result_url` pointing to canonical frontend routes

### Upload And Job Polling
`POST /api/uploads/epub`, `POST /api/books/:id/analysis/start`, `POST /api/books/:id/analysis/resume`, `GET /api/books/:id/analysis-log`, and `GET /api/jobs/:job_id` are part of the active integration surface.

Stable expectations:
- `job_id` is a string
- `status` is a stable machine-readable job stage and may be `ready` after a deferred upload completes the chapter-level structure parse
- `status` may also be `paused` when automatic recovery budget is exhausted and a manual continue action is required
- `book_id`, when known, is a public integer book id
- `job_url` and `ws_url` remain backend API URLs
- chapter progress fields such as `current_chapter_id` remain integers
- long-running parse/read payloads may expose `current_phase_step`, `resume_available`, and `last_checkpoint_at`
- deferred upload is chapter-outline only; semantic segmentation begins inside `analysis/start` or `analysis/resume` as part of deep-reading preparation

### Bookshelf And Overview Status
Book shelf cards and book detail payloads use these public high-level states:

- `not_started`
- `analyzing`
- `paused`
- `completed`
- `error`

### Error Response Shape
REST failures use the shared error envelope:

- `error_id`
- `code`
- `message`
- `status`
- `retryable`
- `details`

### Activity And WebSocket Events
Activity and realtime payloads must continue to normalize into the public contract:

- activity events use canonical `reaction_types`
- activity `result_url` values use canonical frontend routes
- WebSocket envelopes use integer `book_id` when present
- WebSocket event payloads should not expose legacy route names or legacy reaction taxonomy values

## Compatibility Notes
- Backend no longer exposes landing/sample compatibility endpoints. Landing remains frontend-only by contract.
- Backend internal artifacts may still store `connect_back`; public API payloads must normalize that to `retrospect`, and new runtime outputs should emit `retrospect`.
- Old mock data is not authoritative. If a mock file disagrees with this document, update or remove the mock rather than preserving conflicting terminology.
- Legacy redirect routes are allowed, but new UI code, docs, and backend-returned frontend URLs should use canonical routes only.

## How To Update This Contract
When changing this contract:

1. Update this document first.
2. Update backend schemas and payload mapping.
3. Refresh the committed OpenAPI snapshot and generated frontend types.
4. Update frontend route handling and affected components.
5. Run the shared validation flow from the workspace root.
6. Record any temporary exceptions or unfinished migration work in `docs/agent-handoff.md`.

Do not merge a contract change that only updates documentation or only updates one side of the integration.

## Machine-Readable Appendix
The JSON block below is the machine-readable appendix used by the root contract drift checks.

```json
{
  "reaction_types": [
    "highlight",
    "association",
    "discern",
    "retrospect",
    "curious"
  ],
  "mark_types": [
    "resonance",
    "blindspot",
    "bookmark"
  ],
  "canonical_routes": {
    "landing": "/",
    "books": "/books",
    "book": "/books/:id",
    "chapter": "/books/:id/chapters/:chapterId",
    "marks": "/marks"
  },
  "compat_routes": [
    "/bookshelf",
    "/book/:bookId",
    "/book/:bookId/chapter/:chapterId",
    "/books/:id/analysis",
    "/analysis/:bookId",
    "/bookshelf/marks"
  ],
  "landing_strategy": {
    "owner": "frontend_static",
    "display_card_count": 5,
    "sample_teaser_source": "frontend_static"
  }
}
```
