# Evidence Index

Purpose: 汇总本 case-study 方法论包使用的项目证据和外部方法论来源，并标注来源类型、耐久性和纳入原因。
Use when: 需要追踪某个 AI Harness 判断来自哪里，或需要区分项目证据、官方来源、实践者框架和社区信号。
Not for: 产品运行时权威、机制规格、当前任务状态、完整文献综述或单一外部观点背书。

Source check date: 2026-04-23.

## Source Classification

| Label | Meaning |
| --- | --- |
| `durable principle` | 工具变化后仍大概率有效的方法论原则。 |
| `current tactical` | 当前工具/平台阶段有用，但可能随产品能力变化。 |
| `speculative signal` | 来自社区或新工具信号，只用于观察趋势，不能单独作为方法论权威。 |

## Project Evidence

| Evidence | Area | Why included |
| --- | --- | --- |
| [AGENTS.md](../../../AGENTS.md) | Context Harness / Governance Harness | 定义 load matrix、doc routing、trigger matrix、long-job rules，是 repo-first agent memory 的核心入口。 |
| [Source Of Truth Map](../../source-of-truth-map.md) | Context Harness / Execution Harness | 把 durable information 映射到 canonical location、validation command、update trigger。 |
| [Current State](../../current-state.md) | Execution Harness / Observability Harness | 保存 active jobs、run ids、watchdogs、expected outputs、recovery posture。 |
| [Task Registry](../../tasks/registry.md) | Execution Harness / Context Harness | 记录 task routing、status、priority、decision refs、job refs、evidence refs。 |
| [Product Overview](../../product-overview.md) | Intent Harness | 固化 living co-reader mind 的产品本质，防止 AI 协作漂回 summary engine。 |
| [Backend Reader Evaluation](../../backend-reader-evaluation.md) | Intent Harness / Evaluation Harness / Governance Harness | 定义 product-first、mechanism-agnostic evaluation constitution、dual diagnosis、source-span rules、long-span route change。 |
| [Backend Reading Mechanism](../../backend-reading-mechanism.md) | Tool / Environment Harness | 定义 shared runtime shell、shared substrate、mechanism-private artifact、shared evaluation seam。 |
| [Attentional V2 Mechanism](../../backend-reading-mechanisms/attentional_v2.md) | Context Harness / Observability Harness | 记录 bounded state packets、concept/thread digests、carry-forward context、read audits、continuation capsules。 |
| [Backend Sequential Lifecycle](../../backend-sequential-lifecycle.md) | Execution Harness | 定义 upload/start/resume、job status、checkpoint、stale runtime、resume compatibility。 |
| [Decision Log](../../history/decision-log.md) | Learning Harness / Intent Harness | 保存 `DEC-011`、`DEC-012`、`DEC-013`、`DEC-030`、`DEC-035`、`DEC-036`、`DEC-037`、`DEC-050`、`DEC-063`、`DEC-064`、`DEC-076` 等关键 AI-native workflow inflections。 |
| [Source Mirror](../../implementation/new-reading-mechanism/source-mirror.md) | Context Harness / Intent Harness | 证明复杂设计先被 source-faithful mirror 保存，避免 AI 摘要遗漏。 |
| [Requirement Ledger](../../implementation/new-reading-mechanism/requirement-ledger.md) | Intent Harness / Execution Harness | 用 atomic requirements 和 disposition 防止大设计遗漏。 |
| [Validation Matrix](../../implementation/new-reading-mechanism/validation-matrix.md) | Evaluation Harness / Execution Harness | 定义 unit、integration、compatibility、runtime、evaluation、docs 验证层。 |
| [Execution Tracker](../../implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md) | Execution Harness / Learning Harness | 记录 phased implementation、landed behavior、validation posture、next moves。 |
| [Mechanism Pattern Ledger](../../implementation/new-reading-mechanism/mechanism-pattern-ledger.md) | Learning Harness / Evaluation Harness | 保存 strengths、adoption candidates、failure modes、anti-patterns、status、next action。 |
| [Dataset Platform Closed Loop](../../implementation/new-reading-mechanism/dataset-platform-closed-loop.md) | Evaluation Harness / Execution Harness | 记录 source intake、case generation、packet review、repair loop、stop condition。 |
| [Evaluation Evidence Catalog](../../../reading-companion-backend/docs/evaluation/evidence_catalog.md) | Evaluation Harness / Observability Harness | 分类 current formal evidence、quality audits、historical evidence、superseded、failed、invalidated evidence。 |
| [Long-Span Evaluation README](../../../reading-companion-backend/docs/evaluation/long_span/README.md) | Evaluation Harness | 记录 active Long Span direction 与 discontinued target-centered route 的证据边界。 |
| [Claude Code context-management research](../../../reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md) | Context Harness / Learning Harness | 展示项目如何从 coding-agent context management 提炼 index-first memory、side context、compaction、session continuity。 |

## External Methodology Sources

| Source | Date / recency | Source type | Durable takeaway | Classification |
| --- | --- | --- | --- | --- |
| [Anthropic: Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) | Published 2024-12-19 | official/frontier docs | 优先简单、可组合的 workflow；区分 workflow 与 agent；tool design 往往比 prompt 更关键。 | `durable principle` |
| [Claude Code best practices](https://code.claude.com/docs/en/best-practices) | Current docs, checked 2026-04-23 | official/frontier docs | subagents 用于隔离调查上下文；checkpoint、resume、parallel sessions、non-interactive mode 是 coding harness 的一部分。 | `current tactical` plus `durable principle` |
| [Claude Code memory docs](https://code.claude.com/docs/en/memory) | Current docs, checked 2026-04-23 | official/frontier docs | memory / rules / imports / path-scoped rules / skills 分层，支持 context hygiene。 | `current tactical` plus `durable principle` |
| [Claude Code subagents docs](https://code.claude.com/docs/en/subagents) | Current docs, checked 2026-04-23 | official/frontier docs | subagents 是独立 context window、独立工具权限和专门 system prompt 的隔离单元。 | `current tactical` |
| [Anthropic: How and when to use subagents in Claude Code](https://claude.com/blog/subagents-in-claude-code) | Published 2026-04, checked 2026-04-23 | official/frontier blog | subagents 的核心价值是把探索噪声移出主上下文，只回传结果。 | `current tactical` plus `durable principle` |
| [OpenAI: A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) | Current guide, checked 2026-04-23 | official/frontier docs | agent run loop、exit condition、handoff、prompt templates 和 structured output 是编排核心。 | `durable principle` |
| [OpenAI: Agent evals](https://platform.openai.com/docs/guides/agent-evals) | Current docs, checked 2026-04-23 | official/frontier docs | agent workflow 需要评估 trajectory、tool calls 和最终输出。 | `current tactical` plus `durable principle` |
| [OpenAI: Evaluation best practices](https://platform.openai.com/docs/guides/evaluation-best-practices) | Current docs, checked 2026-04-23 | official/frontier docs | eval objective、dataset、metrics、run/compare、continuous evaluation；避免 vibe-based evals。 | `durable principle` |
| [OpenAI: The next evolution of the Agents SDK](https://openai.com/index/the-next-evolution-of-the-agents-sdk/) | Published 2026-04 | official/frontier announcement | sandbox execution、workspace manifest、snapshot / rehydration、harness 与 compute 分离成为 agent 平台方向。 | `current tactical` |
| [MCP specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/index) | Protocol revision 2025-11-25 | standard / official spec | resources、prompts、tools、lifecycle、authorization 分离，为 tool/context boundary 提供标准语言。 | `durable principle` with `current tactical` details |
| [Microsoft: AI Agent Orchestration Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns) | Microsoft Learn, checked 2026-04-23 | official/frontier docs | sequential、concurrent、group chat、handoff、magentic 等模式应按工作阶段组合。 | `durable principle` |
| [Microsoft: Introducing Microsoft Agent Framework](https://azure.microsoft.com/en-us/blog/introducing-microsoft-agent-framework/) | Published 2025-10-01 | official/frontier announcement | enterprise agent systems 正在收敛到 orchestration、durability、observability、governance、compliance。 | `current tactical` |
| [LangSmith observability concepts](https://docs.langchain.com/langsmith/observability-concepts) | Current docs, checked 2026-04-23 | official/practitioner docs | trace、run/span、thread、metadata、tags、feedback 是 LLM app observability 的基本对象。 | `durable principle` |
| [HumanLayer: 12 Factor Agents](https://www.humanlayer.dev/blog/12-factor-agents) | Published around 2025, checked 2026-04-23 | practitioner system | 小而聚焦的 workflow、LLM-as-next-step parser、普通程序控制流、stateless reducer 值得借鉴。 | `durable principle` |
| [Hamel Husain: Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/index.html) | Published 2024-03-29 | practitioner system | 领域 AI 产品成功依赖 robust eval systems、trace review、human/model eval、快速迭代。 | `durable principle` |
| [Hamel Husain: LLM Evals FAQ](https://hamel.dev/blog/posts/evals-faq/evals-faq.pdf) | Recent FAQ, checked 2026-04-23 | practitioner system | 先做 error analysis，再考虑 model switching；慢且不确定的 LLM judge 不应默认做同步 guardrail。 | `durable principle` |
| [Augment Code: Your agent's context is a junk drawer](https://www.augmentcode.com/blog/your-agents-context-is-a-junk-drawer) | Published 2026-02-27 | practitioner commentary / HN-referenced signal | context files 应少而 failure-backed；不要把代码可见信息重复写成上下文规则。 | `current tactical` plus `durable principle` |
| [Reddit: evals/traces/review approval linkage](https://www.reddit.com/r/AI_Agents/comments/1s41fil/do_you_actually_have_a_clean_way_to_connect/) | Community discussion, March/April 2026 | fast-moving signal | trace、eval、artifact、human approval 往往分散，run_id 到 approval decision 的链路是实际痛点。 | `speculative signal` |
| [Reddit: agent observability/testing tier discussion](https://www.reddit.com/r/AI_Agents/comments/1rfrvcw/whats_your_honest_tier_list_for_agent/) | Community discussion, 2026 | fast-moving signal | 非确定性测试仍未完全解决；schema validation、cheap-model smoke、run-history diffing 是常见实践信号。 | `speculative signal` |
| [Reddit: automated context-window management](https://www.reddit.com/r/ClaudeAI/comments/1r3o8vv/i_built_an_automated_context_window_management/) | Community discussion, 2026 | fast-moving signal | context management 正从个人纪律转向 hooks、routing、subagent isolation 的自动化。 | `speculative signal` |
| [Reddit: pointing CLAUDE.md to AGENTS.md](https://www.reddit.com/r/ClaudeCode/comments/1r9zx34/pointing_claudemd_to_agentsmd/) | Community discussion, 2026 | fast-moving signal | 多工具 AI context 文件正在向 shared AGENTS.md / stub / symlink / import 模式收敛，但具体做法仍不稳定。 | `speculative signal` |
| [Reddit: process mining for agent systems](https://www.reddit.com/r/AI_Agents/comments/1rzd5pn/my_ai_agents_burned_50day_doing_nothing_so_i/) | Community discussion, 2026 | fast-moving signal | 成功 trace 也可能掩盖执行图结构失败；execution-path observability 是新痛点。 | `speculative signal` |
| [X: Letta Context Constitution signal](https://x.com/Letta_AI/status/2039813750879105072) | X post, April 2026 | fast-moving signal | memory-first agent harness 和 context ownership 正成为前沿叙事。 | `speculative signal` |
| [X: runtime-trace learning signal](https://x.com/tetsuoai/status/2032031965575332172) | X post, March 2026 | fast-moving signal | 从 agent runtime traces 中自动发现 prompt/tool/context 失败模式是值得观察的方向。 | `speculative signal` |
| [X: CLI-noise context signal](https://x.com/shidhincr/status/2023771129685397879) | X post, February 2026 | fast-moving signal | 终端噪声过滤和 context compression 是 coding-agent 体验的战术热点。 | `speculative signal` |

## Inclusion Rules

- Official/frontier docs are used for structure, definitions, and durable architecture anchors.
- Practitioner systems are used when they provide clear operational patterns that match multiple official sources or Reading Companion evidence.
- Fast-moving signals are included only as weak trend indicators.
- No single Reddit post, X post, or forum comment is treated as authority.
- If a signal is useful, it should eventually be tested against project experience before becoming a stable rule.

## What This Evidence Supports

The combined evidence supports the AI Harness Stack:

1. Intent Harness
2. Context Harness
3. Tool / Environment Harness
4. Execution Harness
5. Evaluation Harness
6. Observability Harness
7. Governance Harness
8. Learning Harness

It also supports the main gap-map conclusion:

- Reading Companion is already strong in repo-first memory, intent clarification, recoverable execution, evaluation discipline, and learning loops.
- The next frontier is a personal AI Harness with stronger evidence contracts, run dossiers, execution-path observability, tool governance, and source monitoring.
