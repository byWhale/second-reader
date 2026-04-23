# Improvement Roadmap

Purpose: 规划未来继续做复杂 AI 产品项目时，最值得补强的 AI 协同能力。
Use when: 制定个人 AI-native workflow 学习计划、决定下一阶段方法论升级、把 Reading Companion 经验转成可复用系统。
Not for: Reading Companion 当前任务状态、产品机制权威、运行时计划、评测结果权威或简历 bullet。

This roadmap is about improving the way AI is used, not changing Reading Companion product behavior.

## North Star

下一阶段目标不是“更会写 prompt”，而是建立一个个人 AI Operating System：

- 每个复杂任务都有明确 intent 和 evidence contract。
- 每次执行都有可追踪 run path。
- 每个外部 AI 方法论信号都有来源分类和耐久性判断。
- 每次失败都能回流成 checklist、eval、tool rule、context rule 或 explicit defer。
- 模型、工具、上下文、评测、治理都不再靠临时感觉。

## Near-Term Upgrades

### 1. Pre-Task Evidence Contract Template

Why:

- Reading Companion 已经擅长事后解释证据，但很多高成本偏航来自开工前没有显式定义证据边界。

Upgrade:

- 在高风险任务开始前写一个短 evidence contract。
- 明确 question、artifact、validity criteria、decision rule、stop condition。
- 对 eval / long-running job / architecture comparison 强制使用。

Definition of done:

- 任一高风险任务开工前都能回答：
  - What evidence would change my mind?
  - What would invalidate this run?
  - Which output is formal evidence, and which is diagnostic only?

### 2. Post-Run Interpretation Template

Why:

- 目前项目有很多高质量解释，但格式分散在 current-state、decision-log、evaluation reports、research notes 中。

Upgrade:

- 对每个 meaningful run 输出固定解释：
  - top-line result
  - validity
  - causal read
  - decision
  - follow-up

Definition of done:

- 下一个 agent 不需要重新读所有 raw artifacts，也能知道 run 是否有效、支持什么决策、下一步是什么。

### 3. Source-Monitoring Habit

Why:

- AI Harness 方法论变化很快。只靠论文和官方文档会慢，只靠 X / Reddit 又会噪声太大。

Upgrade:

- 建立周期性 source review，按来源类型分层：
  - official/frontier docs
  - practitioner systems
  - open-source harness patterns
  - community signals
- 每条来源都标注：
  - date / recency
  - source type
  - durable takeaway
  - principle / tactic / signal

Definition of done:

- 新工具变化先进入 evidence-index 或 personal source notes，再决定是否改变工作流。

## Mid-Term Upgrades

### 4. Stronger Human Calibration For LLM Judges

Why:

- 项目已经能使用 multi-prompt LLM adjudication，但 LLM judge 仍然需要人类校准，尤其是高影响 benchmark、路线切换、default promotion。

Upgrade:

- 选少量高影响 case 做 human calibration slice。
- 记录 judge-human disagreement 类型，而不只记录一致率。
- 把 disagreement 转成 rubric repair 或 judge prompt invalidation criteria。

Definition of done:

- 对每个重要 judge family，都能说清：
  - 哪些判断 LLM judge 可靠
  - 哪些边界 case 需要 human review
  - 哪些 label 易漂移

### 5. Execution-Path Evals

Why:

- 现在评测主要强在 output / artifact 层，但 agentic workflow 的失败常常发生在路径上：工具选错、上下文取错、重试策略错、早停或晚停、错误 artifact 被 merge。

Upgrade:

- 为长任务和 agent workflow 增加路径级评测：
  - Did it load the right docs?
  - Did it choose the right tool?
  - Did it preserve artifact ownership?
  - Did it respect source grounding?
  - Did it stop or retry at the right time?
  - Did it record approval / invalidation?

Definition of done:

- 对重要 agent run，不只评最终结果，也能评执行路径是否健康。

### 6. Lightweight Workflow Metrics / Dashboarding

Why:

- 项目已经有 run ids、logs、artifacts、`llm_usage`、evidence catalog，但人仍然需要在文件系统中手动拼图。

Upgrade:

- 建一个轻量 run dossier 或 dashboard index：
  - command
  - inputs
  - model/provider config
  - stages
  - retries
  - artifacts
  - eval scores
  - interpretation
  - decision

Definition of done:

- 任一重要 run 都能被一个 index 页面重建，而不是靠 current-state 长段落和人工路径搜索。

## Long-Term Upgrades

### 7. Personal AI Operating System / Harness

Why:

- Reading Companion 的 repo-first memory 很强，但它主要服务这个项目。未来复杂项目需要跨 repo、跨工具、跨模型的个人协作系统。

Upgrade:

- 建立个人级 AI Harness：
  - source monitoring
  - context rules
  - tool governance
  - evidence contract templates
  - eval templates
  - decision log pattern
  - model/provider upgrade protocol
  - reusable subagent roles

Definition of done:

- 换项目时，方法论不从零开始；只需要加载项目特定上下文。

### 8. Reusable Multi-Agent Planning / Execution Pattern

Why:

- 目前多 agent / subagent 更像即时策略。未来应形成稳定模式：什么时候并行探索、什么时候主线执行、什么时候独立审查、什么时候 worker 改代码。

Upgrade:

- 定义 reusable roles：
  - explorer
  - implementer
  - evaluator
  - reviewer
  - evidence librarian
- 定义 delegation rules：
  - sidecar vs critical path
  - read-only vs write scope
  - isolated context vs shared memory
  - merge / review expectations

Definition of done:

- 复杂任务可以快速决定哪些工作留在主线程、哪些交给独立上下文、哪些必须人工决策。

### 9. Model / Provider Upgrade Protocol

Why:

- 前沿模型变化快，但模型升级不能只看榜单或感觉。对复杂 AI 产品和 AI 协作 workflow，模型升级会影响 prompt、judge、工具调用、成本、延迟、上下文策略和失败模式。

Upgrade:

- 建立升级协议：
  - candidate model
  - expected benefit
  - affected workflows
  - smoke eval
  - regression eval
  - judge calibration
  - cost / latency profile
  - fallback plan
  - rollout decision

Definition of done:

- 每次模型/provider 切换都有证据、有回退、有范围，而不是“新模型应该更好”。

## Highest-Leverage Focus

如果只能先补一个能力，优先补：Evidence Contract + Run Dossier。

原因：

- 它直接减少高成本偏航。
- 它能连接 intent、execution、eval、observability、learning。
- 它不依赖某个新工具。
- 它能让 AI 协作本身变成可复盘对象。

The next level is not more automation. The next level is making automation inspectable enough that you can trust it, correct it, and compound what it learns.
