# AI-Native Workflow Playbook

Purpose: 将 Reading Companion 中可复用的 AI 协同方法整理成操作手册。
Use when: 启动复杂 AI 产品任务、组织多轮 AI 协作、设计评测闭环、准备交接或复盘。
Not for: 产品运行时权威、机制规格、任务状态更新、简历 bullet 或对任何单一工具的固定教程。

This playbook is methodology guidance. It should be adapted to task risk: small changes should stay light; high-cost, high-risk, ambiguous work should use more of the checklist.

## Stage 1: Intent Framing

Goal: 先确定任务真正要回答什么，而不是马上让 AI 开始做。

Rules:

- 用一句话写清当前问题，不要混入解决方案。
- 写出 non-goals，防止 AI 自动扩大范围。
- 明确这轮是 product clarification、architecture comparison、implementation、evaluation、repair、documentation 还是 handoff。
- 写出谁拥有决策：用户、稳定文档、评测结果、还是当前工程约束。
- 如果任务涉及产品方向，先链接 product / evaluation authority。

Checklist:

- What question are we answering?
- What would count as done?
- What is explicitly out of scope?
- What tradeoff is acceptable?
- What stable doc or prior decision constrains this task?
- What would make us stop or change direction?

Reading Companion pattern:

- Product purpose was stabilized through [Product Overview](../../product-overview.md) and [Backend Reader Evaluation](../../backend-reader-evaluation.md), then later mechanism work had to align to that purpose.

## Stage 2: Evidence Contract

Goal: 在开工前定义这轮 AI 工作需要留下什么证据。

This is the biggest improvement opportunity. Reading Companion often did this after the fact; future work should do it earlier.

Template:

```markdown
## Evidence Contract

Question:
- What exact decision or uncertainty should this task resolve?

Expected artifacts:
- Code paths:
- Docs:
- Eval outputs:
- Logs / traces:
- Screenshots / reports:

Validity criteria:
- What must be true for the evidence to count?
- What would invalidate the run?
- What must be source-grounded or reproducible?

Decision rule:
- If evidence shows X, we will do Y.
- If evidence shows Z, we will defer / rerun / redesign.

Stop condition:
- When do we stop expanding scope?
- When do we abandon this route?
```

Rules:

- Define artifact paths before running expensive jobs.
- Define invalidation criteria before seeing scores.
- Separate diagnostic evidence from current formal evidence.
- If LLM-as-judge is involved, define what the judge may and may not decide.
- If human review is scarce, say what level of LLM adjudication is acceptable and what remains lower trust.

Reading Companion pattern:

- `DEC-064` invalidated a run because source-span eligibility was wrong. That is a strong after-the-fact evidence contract. The next step is writing equivalent invalidation rules before the run.

## Stage 3: Context / Memory Setup

Goal: 给 AI 足够上下文，但不把上下文窗口变成垃圾抽屉。

Rules:

- Start with the required load matrix.
- Load only task-relevant stable docs after that.
- Treat `AGENTS.md` as routing, not a manual for every detail.
- Move durable facts into source-of-truth docs, not chat.
- Use subagents or side-context for high-volume exploration.
- Do not paste information the agent can retrieve from the repo with `rg`.
- Keep scratch notes temporary; promote durable facts before closing.

Checklist:

- What must be in the main context?
- What can be retrieved on demand?
- What should be delegated to a read-only side context?
- What information is already visible in code or docs?
- What unique decision or preference must be written down?

Reading Companion pattern:

- [AGENTS.md](../../../AGENTS.md) defines load matrix and routing.
- [Source Of Truth Map](../../source-of-truth-map.md) defines where durable information belongs.
- [Claude Code context-management research](../../../reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md) explicitly imported index-first memory, compaction plus re-injection, and side-context isolation.

## Stage 4: Implementation Orchestration

Goal: 让 AI 执行变成可恢复工程流程，而不是一次性大赌注。

Rules:

- Keep the change scoped to the ownership boundary.
- Use staged artifacts when work is expensive.
- Register long-running jobs before or immediately after launch.
- Record run id, command, expected outputs, and recovery posture.
- Prefer deterministic scripts for repeatable control flow.
- Let AI handle ambiguity and synthesis; let code handle fixed orchestration.
- Do not protect sunk cost unless the existing run has reusable artifacts.

Checklist:

- What files or modules are owned by this task?
- What artifacts are produced at each stage?
- Can a failed stage be resumed without redoing earlier stages?
- Is there a job id, run id, log path, and check command?
- Are generated outputs ignored or intentionally preserved?
- Is there a merge/report stage separate from shard-local work?

Reading Companion pattern:

- `bundle -> judge -> merge` made evaluation restarts an evidence-based decision.
- Job registry and watchdogs made long-running work recoverable across agent handoffs.

## Stage 5: Evaluation And Error Analysis

Goal: 不只问“结果好不好”，还问“这个结果是不是由正确 harness 测出来的”。

Rules:

- Use dual diagnosis: mechanism weakness and harness/data weakness must both be inspected.
- Treat benchmark-size adequacy as a gate when making promotion/default decisions.
- Make source grounding explicit when evaluation depends on source location.
- Do not use LLM-as-judge to repair an upstream eligibility bug.
- Preserve invalidated runs as diagnostic evidence, but keep them out of current formal evidence.
- Run error analysis before switching models.

Post-run interpretation template:

```markdown
## Post-Run Interpretation

Run:
- run id:
- command:
- input dataset / split:
- model / provider:

Top-line result:
- What happened?

Validity:
- Did the run test the intended question?
- Any invalidation risks?
- Any missing artifacts?

Causal read:
- What likely caused the result?
- Is it mechanism, dataset, harness, provider, or operator issue?

Decision:
- adopt now:
- defer:
- reject / invalidate:
- rerun condition:

Follow-up:
- code:
- docs:
- eval:
- task registry / current-state if applicable:
```

Reading Companion pattern:

- [Backend Reader Evaluation](../../backend-reader-evaluation.md) defines dual diagnosis and source-span rules.
- [Evidence Catalog](../../../reading-companion-backend/docs/evaluation/evidence_catalog.md) separates current, historical, superseded, failed, and invalidated evidence.

## Stage 6: Recovery And Handoff

Goal: 让下一个 AI thread 能恢复工作，而不是重新考古。

Rules:

- Active state belongs in current-state / registry, not only chat.
- Long jobs need job records, active views, logs, and check commands.
- If a task creates durable decisions, update decision log when appropriate.
- If a run is invalidated, preserve why.
- If a path is retired, preserve it as history or diagnostic evidence rather than silently deleting context.
- End with a clear next action, not just a summary.

Checklist:

- What is running?
- What is blocked?
- What was decided?
- What evidence was produced?
- What evidence is invalidated or diagnostic only?
- What should the next agent read first?

Reading Companion pattern:

- [Current State](../../current-state.md) records active jobs, commands, expected outputs, and recovery posture.
- [Task Registry](../../tasks/registry.md) links active tasks to decisions, jobs, and evidence.
- [Decision Log](../../history/decision-log.md) preserves hard-to-reconstruct inflections.

## Stage 7: Retrospective Learning

Goal: 把一次 AI 协作的经验变成下一次 AI 协作的结构。

Rules:

- Do not write vague lessons such as “be careful”.
- Convert lessons into one of:
  - stable rule
  - checklist item
  - test
  - script
  - eval case
  - source-monitoring note
  - defer reason
- Keep tactical tips separate from durable principles.
- Remove context rules that are not failure-backed.
- Do not let pattern ledgers become passive archives; every high-value insight needs disposition.

Checklist:

- What failure did this prevent or reveal?
- What would have caught it earlier?
- Is the lesson tool-specific or durable?
- Should it become a rule, test, eval case, or roadmap item?
- Should it be deleted from context because it is enforceable elsewhere?

Reading Companion pattern:

- [Mechanism Pattern Ledger](../../implementation/new-reading-mechanism/mechanism-pattern-ledger.md) stores strengths, failure modes, dispositions, and next actions.
- `DEC-035` and `DEC-036` require evaluation to preserve portable patterns and close the loop to implementation or deferment.

## Lightweight Mode

Not every task needs the full harness. For small tasks, use this compressed version:

- Intent: one-sentence question and non-goal.
- Context: required docs only.
- Execution: scoped edit and validation command.
- Evidence: final diff plus test result.
- Learning: only write a new rule if a real failure surfaced.

## Full Harness Mode

Use the full playbook when the task has any of these signs:

- ambiguous product direction
- new architecture or mechanism boundary
- long-running eval or dataset job
- LLM-as-judge or benchmark promotion
- model/provider changes
- cross-agent handoff
- irreversible operation
- broad generated artifacts
- high risk of confusing diagnostic evidence with formal evidence

The principle is simple: make the harness proportional to uncertainty and blast radius.
