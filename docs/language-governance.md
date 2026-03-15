# Language Governance

## Purpose
- Prevent mixed-language UI drift.
- Keep content language, interface language, and brand language separate.
- Make key terminology and key product copy maintainable over time.

## Default Policy
- App interface locale defaults to `en`.
- Brand name stays fixed as `书虫`.
- AI-generated reading output keeps following backend content language rules:
  - `output_language=auto -> book_language`

## Text Classes
### 1. Content text
- Examples:
  - source book text
  - AI reading reactions
  - reading notes
  - chapter summaries
  - quotes
  - book titles, chapter titles, author names
- Owner: backend content pipeline
- Rule: follows book/content language, not `appLocale`

### 2. Interface and control text
- Examples:
  - buttons
  - labels
  - tabs
  - page titles
  - tooltips
  - empty states
  - dialog titles
  - settings labels
- Owner: frontend locale layer
- Rule: must follow `appLocale`

### 3. System events and program-state text
- Examples:
  - upload progress
  - parse status
  - blocking reasons
  - resume prompts
  - error summaries
  - activity items from program execution
- Owner: split responsibility
- Rule:
  - Text that enters primary UI decision surfaces must be localizable through structured keys.
  - Raw program-log/activity text may remain backend-authored and unlocalized.

### 4. Fixed brand and governed terminology
- Examples:
  - `书虫`
  - reaction-type names
  - navigation labels
  - status words
  - mode names
- Owner: brand lexicon + product lexicon
- Rule: do not handwrite variants in components

## Governed Assets
### Product lexicon
- Purpose: maintain key terminology
- Minimum fields:
  - `key`
  - `en`
  - `zh`
  - `definition`
  - `usage_note`
  - optional `forbidden_alternatives`

### Controlled copy catalog
- Purpose: maintain key sentence-level UI copy
- Minimum fields:
  - `key`
  - `en`
  - `zh`
  - `intent`
  - `tone_note`
  - `usage_scope`

## Maintenance Rules
- Before adding any visible text, classify it into one of the four classes above.
- Do not place key terminology directly in components.
- Do not handwrite key product copy directly in components.
- Backend should not own UI localization except for content text itself.
- For system-state UI, prefer structured `message_key`/`message_params` style fields and keep raw `message` as compatibility fallback.

## Mindstream Language Split
- `Reading mindstream` uses three distinct language layers that must not be mixed:
  - **Live process language**
    - Purpose: say what the reader is doing right now
    - Owner: structured runtime snapshot (`current_reading_activity`) + controlled live copy
    - Tone: in-progress, clear, lightly lyrical
  - **History trace language**
    - Purpose: say what kind of thought just surfaced
    - Owner: frontend trace-copy layer driven by reaction results
    - Tone: soft, already-happened trace language
  - **Reaction labels**
    - Purpose: fixed product taxonomy (`Highlight`, `Discern`, `Association`, `Curious`, `Retrospect`)
    - Owner: product lexicon
    - Tone: purely classificatory
- Live process language must never be derived by reusing reaction labels.
- History trace language may be guided by reaction-type families, but it must remain separate from the fixed labels.

## Current Scope
- Governance is mandatory for main-path UI surfaces:
  - `/books`
  - `/books/:id`
  - `/books/:id/chapters/:chapterId`
  - `/marks`
  - upload flow
