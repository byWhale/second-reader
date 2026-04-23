# AI-Native Workflow Retrospective

Purpose: 作为 Reading Companion case study 的入口，概括“驾驭 AI / AI Harness”方法论体系，并指向更细的分析文档。
Use when: 复盘个人 AI 协同能力、准备方法论材料、规划下一阶段复杂 AI 产品项目的工作方式。
Not for: 产品运行时权威说明、机制规格、评测契约、简历 bullet 或面试话术成稿。

This document is a case-study gateway. It deliberately does not update product behavior, runtime behavior, task status, mechanism authority, or benchmark authority.

## Core Thesis

Reading Companion 最值得沉淀的 AI-native workflow，不是“用 AI 更快写代码”，而是逐步形成了一套 repo-first、证据驱动、可恢复的 AI Harness。

这里的 Harness 指的是围绕 AI 协作建立的外部控制系统：意图如何被界定、上下文如何被装载、工具如何被约束、长任务如何被恢复、评测如何被校准、证据如何进入文档、下一轮学习如何发生。

从这个角度看，你已经不是在单纯“提示 AI”。你已经在做三件更长期有效的事：

- 把 AI 从 executor 提升为 co-designer，但不给它无边界漂移空间。
- 把复杂项目的记忆、证据、任务、决策和评测放进 repo，而不是留在聊天线程里。
- 把每一次实现、失败、评测和路线调整都尽量转化为下一轮 AI 更容易接住的结构。

下一步最值得补强的能力也很清楚：从“项目内证据系统”升级为“个人 AI Harness 系统”。也就是在每个复杂任务开始前，先定义 evidence contract、上下文预算、工具权限、执行轨迹、评测路径、人工校准点和复盘入口。

## Document Map

| Document | Job |
| --- | --- |
| [Frontier Harness Landscape](ai-native-workflow/frontier-harness-landscape.md) | 用当前官方文档、实践者系统和社区信号综合出 AI Harness Stack。 |
| [Reading Companion Gap Map](ai-native-workflow/reading-companion-gap-map.md) | 把项目现有做法映射到 AI Harness Stack，标出 strong / partial / missing。 |
| [Playbook](ai-native-workflow/playbook.md) | 把可复用工作流整理成从意图澄清到复盘学习的操作手册。 |
| [Improvement Roadmap](ai-native-workflow/improvement-roadmap.md) | 规划近中长期最值得补强的 AI 协同能力。 |
| [Evidence Index](ai-native-workflow/evidence-index.md) | 汇总项目证据、外部来源、来源类型、耐久性和纳入原因。 |

建议阅读顺序：

1. 先读 [Frontier Harness Landscape](ai-native-workflow/frontier-harness-landscape.md)，建立“前沿方法论长什么样”的参照系。
2. 再读 [Reading Companion Gap Map](ai-native-workflow/reading-companion-gap-map.md)，看 Reading Companion 已经做到什么、缺什么。
3. 然后读 [Playbook](ai-native-workflow/playbook.md)，把经验转成下次可执行的流程。
4. 最后读 [Improvement Roadmap](ai-native-workflow/improvement-roadmap.md)，决定下一阶段训练什么能力。

## One-Page Answer

### 截止目前已经形成的有效方法

第一，你已经形成了 repo-first memory。项目的工作规则、文档路由、当前状态、任务注册、决策历史和评测证据都在 repo 中有位置。证据包括 [AGENTS.md](../../AGENTS.md)、[source-of-truth map](../source-of-truth-map.md)、[current state](../current-state.md) 和 [task registry](../tasks/registry.md)。

第二，你已经会用 AI 做产品意图和技术机制的共同澄清，而不是只让 AI 产出方案。产品从较窄的 blind-spot 叙事稳定到 living co-reader mind，并被写入 [product overview](../product-overview.md) 和 [reader evaluation constitution](../backend-reader-evaluation.md)。这让后续机制、评测、前端体验都能围绕同一个上游目标展开。

第三，你已经在复杂机制设计里建立了 omission-control system。新阅读机制不是靠聊天记忆推进，而是通过 source mirror、design capture、requirement ledger、execution tracker、validation matrix 分层推进，见 [source mirror](../implementation/new-reading-mechanism/source-mirror.md)、[requirement ledger](../implementation/new-reading-mechanism/requirement-ledger.md) 和 [validation matrix](../implementation/new-reading-mechanism/validation-matrix.md)。

第四，你已经把评测从 scoreboard 变成学习回路。项目要求 dual diagnosis，区分机制弱、数据弱、harness 弱，并把有意义的结果转成 causal interpretation、selective implementation 或 explicit deferment。证据包括 [backend reader evaluation](../backend-reader-evaluation.md)、[mechanism pattern ledger](../implementation/new-reading-mechanism/mechanism-pattern-ledger.md) 和 [decision log](../history/decision-log.md) 中的 `DEC-030`、`DEC-035`、`DEC-036`、`DEC-064`、`DEC-076`。

第五，你已经把长任务和失败恢复纳入 AI 协同系统。job registry、watchdog、run id、artifact-staged `bundle -> judge -> merge`、expected outputs 和 recovery posture 让任务可以跨线程接力，而不是靠一个聊天窗口记住。证据包括 [source-of-truth map](../source-of-truth-map.md)、[current state](../current-state.md)、[decision log](../history/decision-log.md) 的 `DEC-037`、`DEC-050`、`DEC-063`。

第六，你已经开始区分短期工具技巧和长期原则。比如某个模型、某个 watchdog interval、某个上下文窗口大小都是阶段性策略；repo-first memory、typed context、source-grounded evaluation、durable task registry、decision-bearing docs 则是更长期有效的工作原则。

### 最值得继续补强的 AI 协同能力

最值得补强的是“预先定义证据与执行轨迹”的能力。

项目已经很强地把结果写成证据，但很多高成本问题仍然来自开工前的 evidence contract 不够显式：这一轮到底回答什么问题，什么证据足以改变决策，哪些 artifact 只是 diagnostic，什么时候应停止、重跑、缩小范围或废弃路线。

如果继续做复杂 AI 产品项目，下一阶段应把每个 AI 协作任务都包进一层轻量 harness：

- 任务开始前写清 intent、scope、non-goal、decision owner。
- 开工前定义 evidence contract、artifact path、invalidity criteria、stop condition。
- 执行中保留 run id、tool path、subagent boundary、context budget 和 recovery command。
- 评测后必须写 post-run interpretation，区分 result、cause、harness validity、action / defer。
- 定期把外部 AI workflow 前沿材料纳入 source monitoring，而不是等到工具变化后临时适应。

这不是要把每个任务变重，而是要让高风险、高成本、高不确定性的任务一开始就拥有可审计的协作结构。

## Evidence Links

更完整证据见 [Evidence Index](ai-native-workflow/evidence-index.md)。核心项目证据入口包括：

- [AGENTS.md](../../AGENTS.md)
- [Source Of Truth Map](../source-of-truth-map.md)
- [Task Registry](../tasks/registry.md)
- [Current State](../current-state.md)
- [Decision Log](../history/decision-log.md)
- [Backend Reader Evaluation](../backend-reader-evaluation.md)
- [Mechanism Pattern Ledger](../implementation/new-reading-mechanism/mechanism-pattern-ledger.md)
- [Claude Code context-management research](../../reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md)
