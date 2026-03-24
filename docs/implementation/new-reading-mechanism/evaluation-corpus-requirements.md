# New Reading Mechanism Evaluation Corpus Requirements

Purpose: define the source-book standards and curation-process standards that must be satisfied before building the real `attentional_v2` benchmark datasets and evaluation corpus.
Use when: deciding what books to gather, what the corpus must cover, or what requirements can be solved during curation versus what must already be true of the source books.
Not for: stable evaluation constitution, final benchmark results, or one-off case notes.
Update when: evaluation-question coverage changes, the source-policy changes, or new corpus-quality requirements appear.

## Requirement Flow
- The direction should always be:
  - evaluation question
  - required evidence shape
  - dataset / corpus package
  - source-book requirements
- We should not start from "what books do we happen to have?"
- The books are inputs to the evaluation design, not the design itself.

## Ownership Split
### What I can satisfy during data/corpus curation
- select chapters and excerpts from the available books
- package excerpt cases directly into tracked datasets
- build balanced slices by question family
- deduplicate near-duplicate cases
- annotate case purpose and provenance
- create tuning vs holdout splits
- freeze manifests, fingerprints, and dataset versions
- derive runtime/resume fixtures and persisted compatibility fixtures
- reject weak chapters/excerpts even if they came from otherwise good books

### What the source books must already satisfy
- legal local availability for evaluation use
- machine-readable text that can be parsed reliably
- stable chapter structure or other usable long-form segmentation
- enough phenomenon richness to support the intended evaluation questions
- enough diversity across books so one book or style does not dominate the corpus

## Global Source-Book Requirements
These are requirements for the books themselves, before curation.

### Required
- `accessible_local_source`
  - You can provide the book locally.
  - I need stable filesystem access to the source material.
- `machine_readable_text`
  - EPUB preferred.
  - Extractable text is required.
  - Avoid scan-only or image-only books.
- `parseable_structure`
  - The book should have usable chapter or chapter-like boundaries.
  - Unchaptered long-form prose is possible, but it is worse for the first evaluation corpus.
- `prose_dominant`
  - Prefer prose books for the first corpus.
  - Poetry, highly fragmented aphorism collections, heavily tabular books, or image-dominant books should not dominate the initial corpus.
- `language_control`
  - For the first serious benchmark corpus, prefer one primary language.
  - Recommendation: English-first for the first corpus to reduce evaluation noise.
- `reasonable_text_quality`
  - Avoid severely corrupted EPUBs, OCR-noisy text, or malformed files that would turn the benchmark into a parser-quality test.

### Strongly Preferred
- `chapter_length_variety`
  - The pool should include short, medium, and longer chapters.
  - This helps runtime, resume, and span-trajectory evaluation.
- `phenomenon_richness`
  - The pool should include books with:
    - conceptual distinctions
    - reversals or tensions
    - callbacks
    - allusions or references
    - later reinterpretation opportunities
- `style_diversity`
  - The pool should not all come from one authorial voice or one narrow genre.
- `moderate_judgeability`
  - Avoid making the first corpus depend on deep domain expertise to understand whether a passage was read well.
  - Some specialized books are useful, but not if only a specialist could evaluate them fairly.

## Corpus-Level Coverage Requirements
These are requirements for the corpus as a whole. Some can be satisfied during curation, but only if the source-book pool is rich enough.

### Cross-Mechanism Chapter Corpus
The chapter corpus should collectively provide:
- at least `12` evaluable chapters for the first real comparison pass
- target distribution:
  - `3` expository chapters
  - `3` argumentative chapters
  - `3` narrative or reflective chapters
  - `3` reference-heavy or allusion-dense chapters
- no single book should dominate the comparison corpus
  - recommendation:
    - avoid taking more than `2` evaluation chapters from the same book in the first pass
- enough cross-span richness for:
  - coherent accumulation
  - callback quality
  - chapter-end consolidation
  - durable-trace usefulness

### Excerpt-Case Dataset
The excerpt dataset should collectively provide strong cases for:
- definition or distinction
- tension or reversal
- callback or bridge
- identity-critical reference or allusion
- reconsolidation-worthy later reinterpretation

Not every book must provide every case type.
But the overall pool must make it possible to curate all of them.

### Runtime / Resume Fixture Set
The source books should allow fixtures for:
- warm resume
- cold resume
- reconstitution resume
- early / middle / late chapter positions
- chapters long enough that reread-window policy is meaningful

### Durable-Trace / Re-entry Audit Set
The source material should support:
- multiple genuinely mark-worthy reactions
- later return value
- enough semantic specificity that a reader can judge whether the saved trail still helps on re-entry

## Per Evaluation Family: What The Books Must Enable
### `cross_mechanism_product_comparison`
Books must collectively enable:
- realistic whole-chapter reading comparison
- meaningful differences in reading quality
- chapter-scale coherence judgment
- durable-trace comparison

Book-level signals that help:
- long-form argumentative or reflective development
- callbacks
- recurring motifs
- passages where one mechanism could plausibly outperform another

### `attentional_specific_attribution`
Books must collectively enable:
- sentence-level trigger-worthy moments
- strong meaning-unit closure opportunities
- backward bridge opportunities
- later reinterpretation opportunities
- anchored reaction-worthy lines

Book-level signals that help:
- dense local turns
- subtle reversals
- conceptual pressure
- passages where earlier lines become newly important later

### `runtime_and_compatibility_gate`
Books must collectively enable:
- clean parsing
- stable chapter selection
- enough sentence count for resume windows
- real chapter outputs and marks-compatible payloads

Book-level signals that help:
- ordinary prose EPUB structure
- reliable chapter boundaries
- no major formatting corruption

## What I Need From You
For the real corpus-building step, the most helpful input is:

### Preferred book pool
- ideally `6-10` candidate books for the first corpus-building pass
- EPUB preferred
- primarily English prose for the first corpus
- a mix of:
  - expository
  - argumentative
  - narrative / reflective
  - reference-heavy / allusion-dense

### For each book, useful metadata
- title
- author
- file path
- language
- whether it is okay to store inside the repo or should stay private/local only
- rough type tags such as:
  - `expository`
  - `argumentative`
  - `narrative_reflective`
  - `reference_heavy`
- any chapters you already suspect are especially rich
- any known parsing problems

## Recommended Source Policy
- `repo_tracked`
  - only for books or excerpts we are comfortable storing in the repo
- `private_local_corpus`
  - for the real chapter-level comparison corpus when rights or sensitivity make repo storage undesirable
- `hybrid`
  - recommended default:
    - tracked excerpt datasets and manifests
    - private local full-book corpus when needed

## Immediate Next Step
- Gather a candidate book pool that satisfies the source-book requirements above.
- Then I can do the next layer:
  - corpus intake screening
  - chapter/excerpt selection
  - dataset split proposal
  - fixture-package design for each evaluation family
