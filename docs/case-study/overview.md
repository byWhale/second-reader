# Case Study Overview

Purpose: provide a one-page, interview-ready summary of the project.
Use when: introducing the project in a portfolio, resume supplement, demo walkthrough, or recruiter conversation.
Not for: detailed API behavior, source-of-truth product rules, or low-level implementation specifics.
Update when: the project's positioning, primary path, showcase value, or completion status materially changes.

## Project Positioning
- Reading Companion is an AI-assisted nonfiction reading product.
- Its core promise is to help readers notice viewpoints, tensions, and blind spots they might miss on their own.
- The intended feel is "AI thinking while reading," not a generic book-summary tool.

## Target User
- A thoughtful nonfiction reader who wants deeper engagement than highlights or summaries alone provide.
- A demo viewer or interviewer should be able to see both the product value and the engineering depth in one walkthrough.

## Core Value
- Upload a book, analyze it, inspect chapter-level deep-reading output, and save meaningful reactions as marks.
- The product is designed around a co-reader experience rather than a one-shot report.

## Main Path
- Landing: `/`
- Upload entry: `/books?upload=1`
- Analysis start/resume: long-task workflow driven by upload, `analysis/start`, and `analysis/resume`
- Book overview: `/books/:id`
- Chapter deep read: `/books/:id/chapters/:chapterId`
- Global marks: `/marks`

## Current Showcase Status
- The primary implementation target is the `sequential` deep-reading path.
- The frontend is wired to a backend API contract instead of a mock-only experience.
- The backend supports long-running analysis with progress state, restart semantics, and resume/recovery rules.
- The project includes evaluation artifacts that compare agent output with human highlights.

## Best 5 Showcase Points
- A real end-to-end book workflow exists: upload -> analysis -> book overview -> chapter deep read -> marks.
- The system separates stable outer orchestration from higher-variance inner reading behavior.
- Resume and recovery are treated as product features, not just internal implementation details.
- The web layer is contract-driven, with stable public routes, IDs, and payload expectations documented and validated.
- Prompt/output quality is supported by explicit evaluation artifacts instead of chat-only intuition.
