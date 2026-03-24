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
- assign the right `storage_mode` for each package without changing its benchmark meaning
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
  - Support two primary languages:
    - English
    - Chinese
  - Keep them as parallel evaluation tracks rather than one mixed scoring pool.
  - Do not mix English and Chinese chapters inside the same pairwise/rubric comparison slice unless a later explicit multilingual methodology is defined.
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
For future gap-filling or replacement acquisition passes, the most helpful input is:

### Preferred book pool
For the completed public-first large pass, the target pool was:
- `24` public/open-access candidates screened
  - `12` English
  - `12` Chinese
- `12` promoted into the tracked benchmark pool
  - `6` English
  - `6` Chinese

For future gap-filling acquisition, prefer smaller targeted additions rather than another blind large pass.

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

Important conceptual rule:
- source policy and `storage_mode` should not create separate benchmark concepts when the evaluation question is the same
- they only decide how the package is stored and shared

## Source-Book Organization
We should organize books by role and lifecycle, not by "all EPUBs in one folder."

### Five storage territories
1. `transient_uploads`
- Purpose:
  - raw user-upload intake
- Current home:
  - `reading-companion-backend/state/uploads/`
- Rules:
  - job-scoped, not library-scoped
  - may be temporary
  - should not be treated as the authoritative evaluation corpus
  - should not become the long-term manually curated source library by accident

2. `runtime_book_copies`
- Purpose:
  - the source asset actually attached to one analyzed book run
- Current home:
  - copied into the per-book runtime/output area and surfaced through the book manifest
- Rules:
  - book-instance scoped
  - belongs to one output/book identity
  - may originate from either manual import or user upload
  - this is the right place for one run to remain reproducible after intake

3. `durable_source_library`
- Purpose:
  - manually prepared books that we intentionally keep available for repeated backend use
  - especially useful for evaluation, demos, fixture building, and repeated mechanism work
- Recommended home:
  - private local source-library root, separate from transient uploads
  - for example:
    - `reading-companion-backend/state/library_sources/`
    - or another explicit local-only path outside the repo if preferred
- Rules:
  - organized by stable source identity, not by job id
  - should carry metadata such as language, rights/storage policy, and coarse type tags
  - this is where manually added English/Chinese books should primarily live

4. `evaluation_packages`
- Purpose:
  - tracked benchmark definitions, excerpt datasets, manifests, fixture references, and reports
- Current / recommended home:
  - tracked manifests and excerpt datasets:
    - `reading-companion-backend/eval/datasets/`
  - evaluation code:
    - `reading-companion-backend/eval/`
  - local full-book corpus for chapter-level evaluation:
    - keep private/local and reference it by manifest rather than treating runtime copies as the corpus
- Rules:
  - excerpt datasets can be repo-tracked
  - full-book evaluation corpus should usually be referenced by manifest and local path, not duplicated into runtime output directories

5. `private_local_evaluation_packages`
- Purpose:
  - `storage_mode = local-only` excerpt, chapter, runtime, or compatibility packages derived from books whose text-bearing packages should stay outside the tracked repo dataset tree
- Recommended home:
  - `reading-companion-backend/state/eval_local_datasets/`
- Rules:
  - mirror the same family-first package layout used under `reading-companion-backend/eval/datasets/`
  - keep text-bearing private packages local instead of checking them into the repo
  - point to them through tracked manifests under `reading-companion-backend/eval/manifests/local_refs/`
  - use this territory when the source books are valuable for evaluation but not appropriate for repo-tracked datasets

### Core identity rule
We should keep these identities separate:
- `source_asset`
  - one concrete file you provide
- `work_or_edition`
  - the bibliographic work/edition identity
- `runtime_book`
  - one ingested/analyzed book in the product runtime
- `evaluation_case`
  - one excerpt/chapter fixture derived from a source

The most important practical rule is:
- never use runtime `book_id` as the long-term identity of the source book itself

### Promotion rule
- A user-uploaded book should stay in `transient_uploads` plus its runtime copy by default.
- It should only become part of the durable source library or evaluation corpus if we explicitly promote it.
- Promotion should be intentional because:
  - rights/storage policy may differ
  - evaluation suitability must be screened
  - not every uploaded book is a good benchmark source

### Recommended future metadata
For durable library and evaluation use, each source book should eventually carry:
- stable source id
- title
- author
- language
- file path
- storage policy:
  - repo-tracked
  - private-local
- origin:
  - manual-import
  - user-upload-promoted
  - fixture
  - public-domain-source
- rough type tags
- parsing notes
- evaluation suitability notes

### What this means operationally
- User uploads:
  - keep using `state/uploads/` and per-book runtime copies
- Manually added backend books:
  - place them in a durable source-library territory, not in `state/uploads/`
- Evaluation corpus:
  - build it from screened durable sources
- do not treat ad hoc runtime outputs or uploads as the benchmark corpus
- Private or copyrighted evaluation packages:
  - build them under `state/eval_local_datasets/`
  - keep only manifests and references tracked in the repo
- When the benchmark role is the same, treat tracked and local-only packages as the same benchmark family with different storage modes rather than as different conceptual datasets.
- Repo fixtures:
  - keep minimal and intentional under `tests/fixtures/` or tracked `eval/datasets/`

## Book Search Strategy
The search strategy should be driven by coverage, not by famous-title collecting.

### Two-track acquisition plan
- Build two parallel pools:
  - English
  - Chinese
- Keep each language pool internally balanced before trying to enlarge it.
- For the first pass, prefer a smaller high-signal pool over a large random pile.

### Target acquisition shape
For the current public-first large pass, the target shape is:
- `12` English candidates screened
- `12` Chinese candidates screened
- `6` English books promoted
- `6` Chinese books promoted

Per language, the promoted set should still cover:
- `2` expository / philosophical / conceptual nonfiction
- `2` argumentative / essayistic / social-thought books
- `1` narrative / reflective long-form prose book
- `1` reference-heavy / callback-rich / allusion-dense book

After this large pass, future acquisition should be gap-filling:
- add only the books needed to fill a missing role bucket, phenomenon bucket, or quality gap

### Search order
For each language, search in this order:
1. books you already legally own and can provide locally as EPUB
2. public-domain or open-access books with clean machine-readable text
3. only then, additional books bought or gathered specifically for corpus coverage gaps

### What to search for
When searching, prefer books that give us:
- clear chapter boundaries
- prose-dominant text
- dense conceptual turns or interpretive pressure
- callbacks, motifs, or later reinterpretation opportunities
- passages that can reasonably produce strong anchored reactions

Avoid making the first pool depend too much on:
- highly technical specialist books
- image-heavy or scan-only books
- poetry-dominant books
- books with unstable or badly corrupted EPUB conversion
- books that are all the same voice, genre, or period

### English search guidance
- Good first sources:
  - existing local EPUBs you already own
  - Standard Ebooks for clean public-domain EPUBs
  - Project Gutenberg when a Standard Ebooks edition is unavailable
- Good first categories:
  - reflective novels
  - essay collections
  - philosophy / social thought with chapter structure
  - allusion-rich classics

### Chinese search guidance
- Good first sources:
  - existing local EPUBs you already own
  - Chinese public-domain texts with exportable machine-readable text
  - Chinese EPUBs you can provide locally for modern vernacular coverage
- Good first categories:
  - modern vernacular essays or reflective prose
  - chaptered novels with strong callbacks or reinterpretation opportunities
  - classical prose only when the text remains reasonably judgeable for our rubric
- For Chinese, do not let the first pool become only classical terse texts.
  - We want some modern vernacular prose too, if you can provide it.

### Selection rule
If two books look equally good, prefer the one that:
- parses more cleanly
- has stronger chapter boundaries
- adds a missing coverage type
- is easier to keep as a stable evaluation source

### What I should do after you gather candidates
For future gap-filling acquisition, once a new candidate pool exists, I should:
- screen parse quality
- tag each book by evaluation usefulness
- reject weak or redundant candidates
- classify each source into:
  - `chapter_corpus_eligible`
  - `excerpt_only`
  - `reserve`
  - `reject`
- promote only the books that fill a real benchmark gap
- rebuild the affected package families through the manifest-driven corpus builder

## Current Public-First Large `v2` Status
The current public-first large acquisition pass is now complete at the dataset-build layer.

### Current tracked benchmark outcome
- `24` public/open-access books screened
- `12` newly promoted
- `22` books in the combined tracked public pool
- tracked `v2` benchmark packages now exist for:
  - `chapter_corpora`
  - `runtime_fixtures`
  - `excerpt_cases`
  - `compatibility_fixtures`

### Current tracked `v2` package counts
- `18` English chapter rows
- `18` Chinese chapter rows
- `36` English runtime fixtures
- `36` Chinese runtime fixtures
- `54` English seed excerpt cases
- `24` Chinese seed excerpt cases
- `16` English curated excerpt cases
- `16` Chinese curated excerpt cases
- `36` shared compatibility fixtures

### Current implementation entrypoints
- candidate specification:
  - `reading-companion-backend/eval/attentional_v2/public_first_large_candidates.json`
- manifest-driven builder:
  - `reading-companion-backend/eval/attentional_v2/build_public_first_large_corpus.py`
- validator:
  - `reading-companion-backend/eval/attentional_v2/validate_public_first_large_corpus.py`
- shared helper layer:
  - `reading-companion-backend/eval/attentional_v2/corpus_builder.py`

### Important operational nuance
- The tracked public benchmark pool is now strong enough to stop treating book acquisition as the default next step.
- Later book collection should be gap-filling only.
- The local-only supplement remains available when a phenomenon bucket or role bucket is still uncovered, but it does not replace the public-first benchmark goal.
- Weak but text-valuable public Chinese sources may be normalized into synthetic segmented EPUBs when that is necessary to give them fair chapter-level screening.

## Immediate Next Step
- Stop growing the corpus by default.
- Use the current tracked `v2` benchmark family as the primary input to real evaluation runs.
- Return to acquisition only if:
  - a benchmark bucket is still uncovered
  - a language track remains structurally weaker
  - or evaluation evidence shows a specific quality gap in the current corpus
