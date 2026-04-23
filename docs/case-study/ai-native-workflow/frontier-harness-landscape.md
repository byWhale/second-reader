# Frontier Harness Landscape

Purpose: 综合当前 AI agent / AI harness / AI coding workflow 的前沿方法论，定义可复用的 AI Harness Stack。
Use when: 需要判断“先进 AI 协同系统应该包含哪些层”，或需要把 Reading Companion 的经验放进更大的方法论参照系。
Not for: Reading Companion 产品机制权威、运行时规范、某个外部工具的完整教程，或对单一社区观点的背书。

Source check date: 2026-04-23.

This document uses three evidence tiers:

- `official/frontier docs`: 官方文档、标准规格、平台工程博客。用作结构锚点。
- `practitioner systems`: 高质量实践者框架和工作流文章。用作方法补充。
- `fast-moving signals`: Reddit / X / HN-style 讨论和工具信号。只作为趋势雷达，不作为权威结论。

Every external source is classified in [Evidence Index](evidence-index.md). The core distinction is:

- `durable principle`: 工具换代后仍大概率有效。
- `current tactical`: 当前工具阶段很有用，但可能随平台变化。
- `speculative signal`: 值得观察，但不能单独作为方法论基础。

## Why Harness, Not Just Prompting

前沿 agent 实践的共同趋势是：真正提升复杂 AI 工作质量的，不是再写一个更长的 prompt，而是把模型放进一个可控的系统。

这个系统通常包含：

- 清晰的目标和退出条件。
- 可被模型安全使用的工具和上下文。
- 独立上下文或 subagent，用来隔离高噪声探索。
- 可恢复的执行环境、run state、checkpoint 或 snapshot。
- trace、eval、feedback、human approval 的闭环。
- prompt injection、权限、凭证隔离、不可逆操作保护。
- 把每轮失败转成下一轮的规则、测试、dataset 或 harness 改进。

这也是为什么这里使用 `AI Harness Stack`，而不是只说 prompt engineering、agent framework 或 coding assistant workflow。

## AI Harness Stack

### 1. Intent Harness

Intent Harness 负责把人的模糊意图变成 AI 可执行、可评测、可拒绝的任务边界。

它包含：

- problem framing
- success criteria
- scope and non-goals
- tradeoffs
- decision owner
- stop / retry / abandon condition

外部参照：

- Anthropic 的 agent 指南强调先选择最简单可行方案，并区分 workflow 与 agent。
- OpenAI 的 agent guide 把 run loop、exit condition、handoff 和 structured output 放在 agent 编排的核心位置。
- Microsoft orchestration patterns 强调不同阶段可以混用 sequential、concurrent、handoff、group chat 等模式，而不是强行套一个统一形态。

长期原则：

- AI 不能替代意图界定。
- 复杂任务必须先定义“什么算完成”和“什么证据会改变决策”。
- 多 agent 或复杂 harness 只有在任务不确定性、并行度或工具边界需要时才值得引入。

### 2. Context Harness

Context Harness 负责决定哪些信息进入模型、何时进入、以什么粒度进入，以及哪些内容必须留在 repo / memory / index 中。

它包含：

- source-of-truth docs
- memory routing
- context budgets
- compaction and re-injection
- subagent isolation
- index-first retrieval
- path-scoped rules

外部参照：

- Claude Code memory docs 将项目记忆、规则、imports、path-scoped rules、skills 做分层。
- Claude Code subagents docs 和 Anthropic blog 都强调 subagent 的独立 context window 和主会话降噪价值。
- 实践者和社区讨论反复提醒：上下文越多不一定越好，过多通用规则会挤占真正稀缺的 attention budget。

长期原则：

- 不要把所有记忆变成一个越来越大的 blob。
- Context file 应该像 routing table，而不是百科全书。
- 可从代码或工具直接恢复的信息，不必重复写进 agent memory。
- 高体积探索适合放进隔离上下文，只把结论回传主线。

### 3. Tool / Environment Harness

Tool / Environment Harness 负责让 AI 使用稳定、明确、可审计的工具和运行环境。

它包含：

- stable tool schema
- sandbox
- permission model
- tool reliability
- environment manifests
- dependency availability
- credential separation
- MCP-style resources / prompts / tools boundary

外部参照：

- MCP specification 把 resources、prompts、tools、lifecycle、authorization 等边界拆开，并建立 JSON-RPC 消息形态。
- OpenAI Agents SDK 的最新 harness / sandbox 方向强调 controlled workspace、portable environment manifest、snapshot / rehydration、harness 与 compute 分离。
- Anthropic 的 agent 指南提醒，很多 agent 成败来自 tool design，而不是 prompt 本身。

长期原则：

- Tool shape 是 prompt 的一部分。
- AI 使用工具时，路径、权限、凭证、输出目录和失败模式都应该明确。
- 对高风险操作，sandbox、审批和不可逆动作保护比“让模型更小心”可靠。

### 4. Execution Harness

Execution Harness 负责把 AI 协作从一次对话变成可恢复、可重放、可并行、可交接的执行系统。

它包含：

- deterministic workflow where possible
- scoped agents
- staged artifacts
- durable execution
- run ids
- retry / resume / watchdog
- pause and recovery
- ownership boundaries

外部参照：

- OpenAI agent guide 把 agent run 描述成循环，直到 final output、tool call、error 或 max turns 等退出条件出现。
- Microsoft Agent Framework 和 orchestration docs 强调持久状态、错误处理、retries、recovery、multi-agent coordination。
- HumanLayer 的 12-factor agents 更偏实践派：让 LLM 输出下一步 JSON / tool call，再由普通程序 switch / reducer 控制流程。

长期原则：

- 能确定的流程交给代码，不要交给模型即兴发挥。
- Agent 的价值在处理不确定判断和语言/工具选择，而不是替代所有控制流。
- 大任务要拆成 artifact stages，这样失败后可以决定 reuse、resume、rejudge 或 restart。

### 5. Evaluation Harness

Evaluation Harness 负责让 AI 系统在不确定输出下仍然可以被改进。

它包含：

- datasets
- trace grading
- offline and online evals
- LLM-as-judge
- human calibration
- regression gates
- error analysis
- continuous evaluation

外部参照：

- OpenAI evaluation best practices 强调 objective、dataset、metric、run / compare、continuous evaluation，以及不要依赖 vibe-based evals。
- OpenAI agent evals 将 agent workflow 的 trajectory、tool call 和最终结果都纳入评测视野。
- Hamel Husain 的 eval 方法论强调 domain-specific evals、trace review、error analysis，且不把 model switching 当成第一反应。

长期原则：

- 先做 error analysis，再决定换模型、改 prompt、改工具还是改数据。
- LLM-as-judge 需要人类校准和不可能组合校验。
- 输出分数不够，必须检查 harness 是否测试了正确问题。

### 6. Observability Harness

Observability Harness 负责回答“这次 agent 到底做了什么，以及为什么结果可信或不可信”。

它包含：

- traces
- spans / runs
- run ids
- metadata
- artifacts
- provenance
- dashboards
- execution-path inspection
- trace-to-eval-to-review linkage

外部参照：

- LangSmith 把 trace 定义为一次操作下多个 run / span 的集合，并支持 metadata、tags、feedback。
- Microsoft Foundry / Agent Framework 方向强调 multi-agent observability、OpenTelemetry、tool invocation visibility。
- 社区讨论的高频痛点是：很多团队有 trace、eval 和 approval，但很难把“输入 -> 工具 -> artifact -> 人工审批 -> 可复现 rerun”连成一条干净链。

长期原则：

- 最终输出不是唯一证据。
- 复杂 agent 需要 execution path eval，而不只是 output eval。
- 评审决策应绑定 run id、trace snapshot、artifact version 和 reviewer decision。

### 7. Governance Harness

Governance Harness 负责管理 AI 的权限、安全、不可逆行为和供应商/模型变化。

它包含：

- guardrails
- approval gates
- prompt injection and exfiltration assumptions
- tool safety
- credential isolation
- model/provider pinning
- audit policy
- escalation rules

外部参照：

- OpenAI Agents SDK sandbox announcement 明确强调 prompt injection / exfiltration assumptions，以及 harness 与 compute 分离以保护凭证。
- Claude Code docs 暴露了 permission modes、tool restrictions、subagent capabilities 等治理面。
- Microsoft enterprise agent material 把 observability、durability、compliance、governance 作为 multi-agent production 的核心问题。

长期原则：

- 不能只靠模型自律。
- 工具权限应按任务、子代理、环境和风险分级。
- 模型和 provider 升级要有 protocol，而不是感觉“新模型更强”就切。

### 8. Learning Harness

Learning Harness 负责把每次 AI 协作的经验变成下一轮更好的结构。

它包含：

- pattern ledger
- decision log
- retrospectives
- failure-backed rules
- source monitoring
- improvement roadmap
- model / prompt / tool upgrade lessons

外部参照：

- Hamel-style eval practice 把 traces 和 error analysis 变成 dataset 与改进循环。
- 社区信号显示，很多先进个人工作流都在从“每次手动提醒 AI”转向 hooks、skills、slash commands、memory files、source monitoring、run-history diffing。
- Augment Code 的 context essay 提醒：不是每条规则都值得写入 agent memory，规则应当能解释它预防了哪个真实失败。

长期原则：

- 能被测试、lint、hook、script 执行的规则，不应长期占据模型上下文。
- 保留 failure-backed rules，删除 aspirational rules。
- 学习不是多写总结，而是把总结转成下一轮 harness 的入口。

## What Is Tactical vs Durable

| Category | Examples | How to use |
| --- | --- | --- |
| Current tactical | Claude Code subagent behavior, OpenAI Agents SDK sandbox providers, current MCP revision, current context-window limits, current permission modes | 适合短中期采用，但要预期工具会变化。 |
| Durable principle | simple composable workflows, context budgets, typed tools, staged artifacts, eval/error-analysis flywheel, trace provenance, approval gates | 可以沉淀成个人方法论和项目规则。 |
| Speculative signal | X threads about auto-memory, Reddit discussions about AGENTS.md stubs, new process-mining tools, emerging memory-first harness claims | 作为观察雷达；只有被官方文档、开源工具或多方实践重复印证后再写入强规则。 |

## Reading Companion Implication

Reading Companion 已经在 Intent、Context、Execution、Evaluation、Learning 这几层做得很强。更明显的缺口在：

- general-purpose Tool / Environment governance
- visual / queryable Observability
- prompt-injection / permission / provider-upgrade Governance
- systematic source monitoring for frontier AI workflow ideas

这些缺口不是项目失败，而是下一阶段从“项目内 AI 协同”升级到“个人 AI Harness”的自然方向。
