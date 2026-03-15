# Interview Notes

Purpose: provide concise, reusable interview talk tracks that stay grounded in the other case-study docs.
Use when: preparing resume bullets, recruiter summaries, demo intros, or interview answers.
Not for: defining engineering truth or inventing new claims that are not supported elsewhere.
Update when: the project story materially changes, new showcase evidence appears, or new recurring interview questions emerge.

## 30-Second Version
- I built Reading Companion as an AI-assisted nonfiction reading product rather than a generic summary tool.
- The core flow is upload -> analysis -> book overview -> chapter deep read -> marks.
- The most important engineering decisions were narrowing the system to a reliable sequential reading path, keeping a stable public API contract, and treating long-running recovery as part of the product instead of a backend afterthought.

## 2-Minute Version
- The project started from a more ambitious agent-style reading concept, but the strongest version of the product turned out to be a dependable end-to-end workflow.
- On the product side, the goal is to help readers notice tensions and blind spots while reading nonfiction.
- On the engineering side, I split concerns across frontend routes and UX, backend orchestration and payload shaping, and runtime artifact/recovery behavior.
- I also kept explicit evaluation artifacts so quality discussions are backed by inspectable evidence instead of just intuition.

## 5-Minute Walkthrough
1. Start with the landing page and product promise.
2. Show the upload entry and explain why the product uses a long-running analysis flow instead of pretending everything is instant.
3. Walk through the book overview as the control surface for progress, resume, and chapter access.
4. Open a chapter deep-read page and explain the difference between generated reading reactions and saved marks.
5. Close by explaining the contract-driven frontend/backend boundary and the evaluation artifacts that support quality claims.

## STAR Stories
### Story 1: Simplifying Architecture To Strengthen The Product
- Situation: the repo contained evidence of more generalized agent or graph-oriented ideas.
- Task: turn that into a product flow that actually runs, can be demoed, and can be recovered.
- Action: narrowed the main path to the sequential reading workflow and made runtime semantics explicit.
- Result: the project is easier to explain, validate, and demo as a real product loop.

### Story 2: Treating Recovery As Product Behavior
- Situation: book-length analysis is vulnerable to interruption and stale runtime state.
- Task: avoid a fragile "just rerun it" experience.
- Action: documented distinct runtime modes, resume semantics, and compatibility-driven recovery rules.
- Result: recovery became part of the system story rather than a hidden operational detail.

### Story 3: Backing Quality Claims With Evidence
- Situation: prompt quality is easy to talk about vaguely and hard to prove.
- Task: make quality discussion more concrete.
- Action: retained explicit human-highlight comparison reports and indexed them as case-study evidence.
- Result: it is possible to discuss misses, trade-offs, and improvement areas with actual artifacts.

## Common Follow-Up Questions
- Why not keep the more general graph-based path as the default?
  - Because the stronger demo and product story comes from a reliable main path, not from maximum architectural abstraction.
- How do you avoid frontend/backend drift?
  - By treating the API contract as explicit authority and keeping the frontend integration surface centralized.
- What makes this more than a prompt demo?
  - It has a real web flow, a documented public contract, runtime semantics, and quality evidence.
- What would you improve next?
  - More measurable evaluation coverage, stronger multi-book evidence, and more user-facing proof that the reading outputs improve with iteration.

## Guardrail
- If a statement here cannot be supported by `overview.md`, `architecture.md`, `decisions.md`, or `evidence.md`, it should not stay in this file.
