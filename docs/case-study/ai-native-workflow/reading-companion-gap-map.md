# Reading Companion Gap Map

Purpose: 将 Reading Companion 的真实项目做法映射到 AI Harness Stack，判断哪些层已经 strong、哪些 partial、哪些 missing。
Use when: 需要回答“我已经形成了哪些 AI 协同方法”以及“下一步最值得补强什么”。
Not for: 产品运行时权威、机制规格、任务状态更新、评测结论权威或简历 bullet。

This document is evidence-mapped. Every `strong` or `partial` claim includes concrete project evidence. `missing` entries are improvement opportunities, not criticism of current product behavior.

## Summary Table

| Harness layer | Status | Reading Companion evidence | Main gap |
| --- | --- | --- | --- |
| Intent Harness | `strong` | Product purpose, evaluation constitution, decision log | Pre-task evidence contract is not yet a universal habit. |
| Context Harness | `strong` | AGENTS load matrix, source-of-truth map, current state, task registry, context research | Cross-tool personal context budget is still informal. |
| Tool / Environment Harness | `partial` | Shared backend runtime, LLM gateway, job registry, validation scripts | Strong project tooling, weaker generalized AI tool governance. |
| Execution Harness | `strong` | Durable job registry, staged eval runners, watchdogs, run artifacts | Execution-path metrics are not yet visible as one dashboard. |
| Evaluation Harness | `strong` | Dual diagnosis, evidence catalog, LLM adjudication, invalidation rules | Human calibration and execution-path evals need more structure. |
| Observability Harness | `partial` | run ids, artifacts, `llm_usage`, `read_audit`, evidence catalog | Strong provenance, weaker visual/queryable trace layer. |
| Governance Harness | `partial` | Eval governance, source-span invalidation, doc routing, long-job rules | General agent safety, prompt-injection, permission, provider-upgrade protocol are underdeveloped. |
| Learning Harness | `strong` | Pattern ledger, decision log, retrospective package | External source-monitoring habit is not yet systematic. |

## Layer-by-Layer Assessment

### 1. Intent Harness

Status: `strong`

Reading Companion already uses AI to clarify intent before implementation. The clearest evidence is the product reframing from a narrower blind-spot promise to a living co-reader mind, then turning that into stable documents.

Evidence:

- [Product Overview](../../product-overview.md) defines the product as a curious, self-propelled co-reading mind rather than a summary engine.
- [Backend Reader Evaluation](../../backend-reader-evaluation.md) operationalizes that purpose as a mechanism-agnostic evaluation constitution.
- [Decision Log](../../history/decision-log.md) records `DEC-011`, `DEC-012`, and `DEC-013`, which freeze product-first evaluation, living co-reader purpose, and product-purpose authority.

What is strong:

- Product intent became an upstream constraint, not a downstream copy exercise.
- Evaluation is tied to product purpose rather than to one current mechanism shape.
- Design reversals are recorded when the project learns that the old question is no longer the right question.

Gap:

- The project often writes evidence interpretation after the fact, but the pre-task evidence contract is not yet a standard opening move for every high-risk AI task.

Improvement opportunity:

- Add a lightweight `Evidence Contract` step before major AI-assisted design, eval, or implementation work.

### 2. Context Harness

Status: `strong`

The project has a mature repo-first memory system. AI agents are expected to load canonical docs, respect doc layers, and update the right source of truth.

Evidence:

- [AGENTS.md](../../../AGENTS.md) defines workspace rules, load matrix, doc routing, trigger matrix, and cross-doc update rules.
- [Source Of Truth Map](../../source-of-truth-map.md) maps durable information to canonical locations, validation commands, and update triggers.
- [Current State](../../current-state.md) captures current objective, active jobs, recovery posture, and recommended reading path.
- [Task Registry](../../tasks/registry.md) and [registry.json](../../tasks/registry.json) capture task routing, status, decision refs, job refs, and evidence refs.
- [Claude Code context-management research](../../../reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md) explicitly imported lessons such as index-first memory, compaction plus re-injection, side-context isolation, and session continuity.
- [Attentional V2 mechanism doc](../../backend-reading-mechanisms/attentional_v2.md) shows that the product mechanism itself moved toward bounded packets, `state_packet.v1`, `concept_digest`, `thread_digest`, carry-forward context, and supplemental recall.

What is strong:

- Chat is no longer the primary memory.
- Durable state, task state, history, mechanism docs, and temp notes have separate ownership.
- Context architecture ideas from coding agents were transferred into product mechanism design.

Gap:

- The project has strong project-local context routing, but not yet a personal cross-tool context budget protocol for Codex, Claude Code, browser research, local scripts, and subagents together.

Improvement opportunity:

- Maintain a personal `AI context budget checklist`: what must be preloaded, what should be retrieved on demand, what belongs in subagents, and what should be omitted because the tool can inspect it directly.

### 3. Tool / Environment Harness

Status: `partial`

Reading Companion has strong internal tooling, but that tooling is mostly product/eval-specific rather than a generalized personal AI tool governance layer.

Evidence:

- [Backend Reading Mechanism](../../backend-reading-mechanism.md) defines shared runtime shell, shared substrate, mechanism-private artifacts, and shared evaluation seam.
- [Backend Sequential Lifecycle](../../backend-sequential-lifecycle.md) defines upload/start/resume, job records, checkpoint behavior, and recovery semantics.
- [Backend AGENTS.md](../../../reading-companion-backend/AGENTS.md) defines backend-local rules for LLM gateway usage, artifact routing, job registry usage, and generated artifact hygiene.
- [Source Of Truth Map](../../source-of-truth-map.md) records validation commands such as `make agent-check`, `make contract-check`, background-job checks, and source-intake checks.
- [Decision Log](../../history/decision-log.md) records shared substrate and artifact-boundary decisions such as `DEC-015`, `DEC-016`, `DEC-020`, and `DEC-021`.

What is strong:

- Product/runtime tooling has clear ownership boundaries.
- Long-running jobs and generated artifacts have canonical territories.
- Mechanism-private versus shared artifacts are explicit.

Gap:

- There is no generalized AI tool registry that says which external AI tools, MCP servers, browser sources, local scripts, permission modes, or sandbox policies should be used for which kind of personal workflow task.

Improvement opportunity:

- Build a personal tool governance layer: tool inventory, allowed operations, source trust tiers, sandbox defaults, credential rules, and “when to browse / when to inspect repo / when to spawn subagents” rules.

### 4. Execution Harness

Status: `strong`

The project has evolved from ad hoc execution to durable, staged, recoverable execution.

Evidence:

- [Source Of Truth Map](../../source-of-truth-map.md) makes backend job registry the canonical source for long-running job runtime state.
- [Current State](../../current-state.md) preserves active job ids, watchdogs, run ids, commands, expected outputs, and recovery posture.
- [Decision Log](../../history/decision-log.md) records:
  - `DEC-037`: durable registry for long-running eval and dataset background jobs.
  - `DEC-050`: artifact-staged `bundle -> judge -> merge` comparison work.
  - `DEC-051`: restart only when reusable evidence is weak, not because of sunk-cost anxiety.
  - `DEC-053`: chapter-unit readiness instead of whole-surface smoke as the gate.
  - `DEC-063`: registry-level long-horizon auto-recovery.
- [New Reading Mechanism Execution Tracker](../../implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md) records phased implementation progress, landed behavior, validation posture, and next moves.

What is strong:

- AI-assisted execution can survive long jobs, restarts, and agent handoffs.
- Work is staged into artifacts that can be reused, judged, merged, or invalidated.
- Retry and recovery policy moved from chat memory into durable records.

Gap:

- Execution paths are still mostly inspected through files and prose rather than through a unified run dashboard.

Improvement opportunity:

- Add lightweight workflow metrics: stage durations, retry counts, failure categories, token/cost usage, artifact reuse rates, watchdog recovery counts, and post-run decision outcomes.

### 5. Evaluation Harness

Status: `strong`

Reading Companion's evaluation system is one of the strongest parts of the AI-native workflow.

Evidence:

- [Backend Reader Evaluation](../../backend-reader-evaluation.md) defines evaluation constitution, dataset trust model, dual diagnosis, benchmark-size adequacy, source-span matching, and current long-span direction.
- [Evaluation Evidence Catalog](../../../reading-companion-backend/docs/evaluation/evidence_catalog.md) classifies current formal evidence, quality audits, historical evidence, superseded evidence, failed diagnostics, and invalidated diagnostics.
- [Long-Span Evaluation README](../../../reading-companion-backend/docs/evaluation/long_span/README.md) shows a method route change from discontinued target-centered accumulation to `Memory Quality`, `Spontaneous Callback`, and `False Visible Integration`.
- [Decision Log](../../history/decision-log.md) records:
  - `DEC-030`: benchmark quality as first-class and dual diagnosis.
  - `DEC-031`: multi-prompt LLM adjudication as operational default when human review is scarce.
  - `DEC-064`: invalidating a run when source-span eligibility was wrong.
  - `DEC-076`: retiring a repaired but misaligned Long Span method.

What is strong:

- Evaluation checks both mechanism and harness.
- LLM-as-judge is treated as an auditable component, not a magic oracle.
- Invalidated evidence is preserved as diagnostic memory rather than erased.

Gap:

- Human calibration of LLM judges is acknowledged but not yet systematic enough.
- Execution-path evaluation is weaker than output evaluation.

Improvement opportunity:

- Add a small human-calibration slice for high-impact judge rubrics.
- Add evals that grade trajectory quality: tool choice, context retrieval, retry behavior, source-span eligibility, artifact reuse, and stop/retry decisions.

### 6. Observability Harness

Status: `partial`

The project has strong artifact provenance but weaker visual and queryable observability.

Evidence:

- [Current State](../../current-state.md) preserves run ids, job ids, watchdog ids, expected outputs, and recovery posture.
- [Evaluation Evidence Catalog](../../../reading-companion-backend/docs/evaluation/evidence_catalog.md) links runs to aggregates, reports, analyses, and status classes.
- [Attentional V2 mechanism doc](../../backend-reading-mechanisms/attentional_v2.md) records `read_audit`, context use, continuation capsules, probe snapshots, and mechanism-private runtime artifacts.
- [Decision Log](../../history/decision-log.md) records `DEC-050` with `llm_usage.json` summaries and staged runner observability.

What is strong:

- Artifacts are not anonymous. They usually have run ids, job ids, paths, status, and interpretation.
- Invalidated and failed runs remain findable.
- Many runtime internals are captured as files rather than disappearing into logs.

Gap:

- There is no first-class trace viewer or dashboard connecting prompt inputs, model calls, tool calls, artifacts, eval scores, and human decisions.

Improvement opportunity:

- Build a lightweight local “run dossier” format: one index per major run linking command, input dataset, model/provider config, traces, artifacts, eval results, interpretation, decision, and follow-up action.

### 7. Governance Harness

Status: `partial`

The project has strong eval governance, but weaker general AI-agent governance.

Evidence:

- [Backend Reader Evaluation](../../backend-reader-evaluation.md) defines when benchmark evidence is valid, when runs are invalidated, how LLM adjudication is used, and how source-span matching works.
- [AGENTS.md](../../../AGENTS.md) and [Backend AGENTS.md](../../../reading-companion-backend/AGENTS.md) define repository-level and backend-level rules for long jobs, generated artifacts, doc updates, mechanism boundaries, and evaluation follow-up.
- [Decision Log](../../history/decision-log.md) records `DEC-064`, which treats a wrong candidate retrieval gate as benchmark-contract failure, not a weak model result.
- [Source Of Truth Map](../../source-of-truth-map.md) defines canonical locations and validation commands for durable information.

What is strong:

- The project rejects misleading evidence instead of letting it remain in the main comparison pool.
- Agent work is constrained by doc routing and stable source-of-truth boundaries.
- Long jobs must be registered, and generated artifacts must be routed intentionally.

Gap:

- There is no generalized policy for prompt injection, tool permissions, sandboxing, destructive commands, credential exposure, model/provider upgrades, or multi-agent approval gates.

Improvement opportunity:

- Add a personal AI governance checklist for high-risk work:
  - allowed tools
  - forbidden operations
  - approval gates
  - model/provider pinning
  - browse/source trust tier
  - credential boundaries
  - rollback plan

### 8. Learning Harness

Status: `strong`

The project has a real learning loop: evaluation findings, decisions, and failure modes are preserved as working memory.

Evidence:

- [Mechanism Pattern Ledger](../../implementation/new-reading-mechanism/mechanism-pattern-ledger.md) records strengths, adoption candidates, failure modes, anti-patterns, evidence, status, and next action.
- [Decision Log](../../history/decision-log.md) captures design inflections and rejected alternatives that would be hard to recover from code.
- [Claude Code context-management research](../../../reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md) shows cross-domain transfer from coding-agent context management to Reading Companion mechanism design.
- This retrospective package itself is now a case-study layer under [docs/case-study](../ai-native-workflow-retrospective.md).

What is strong:

- The project does not only keep “what happened”; it keeps “what we learned and how that should change future work.”
- Evaluation lessons are given dispositions rather than left as vague notes.
- Historical routes remain readable even when retired.

Gap:

- Source monitoring for fast-moving AI workflow ideas is still ad hoc.

Improvement opportunity:

- Maintain a monthly or milestone-based AI workflow source review:
  - official platform docs
  - open-source agent harness changes
  - practitioner eval / observability methods
  - selected Reddit / HN / X signals
  - internal lessons from recent runs

## The Two Direct Answers

### What effective AI collaboration methods already exist?

You have already formed a strong method around:

- repo-first memory
- intent-before-implementation product clarification
- mechanism boundaries before architecture changes
- staged execution with durable recovery
- eval-driven repair rather than vibes
- dual diagnosis of model / data / harness
- decision logs and pattern ledgers as agent memory
- evidence invalidation instead of score worship

### What is most worth improving next?

The highest-leverage upgrade is an explicit personal AI Harness around evidence and observability.

Practically, that means:

- pre-task evidence contracts
- post-run interpretation templates
- execution-path evals
- trace-to-review linkage
- source-monitoring rhythm
- governance rules for tools, models, permissions, and irreversible actions

Reading Companion already proves you can use AI to move a complex product. The next level is making the way you use AI itself observable, testable, and reusable.
