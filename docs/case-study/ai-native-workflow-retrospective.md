# AI-Native Workflow Retrospective

Purpose: 复盘 Reading Companion 项目中可复用的 AI 协同工作方法。
Use when: 总结 AI-native workflow、准备 case study、改进未来复杂 AI 产品项目的协作方式。
Not for: 产品运行时权威说明、机制规格、评测契约、简历 bullet 或面试话术成稿。

## Core Thesis

Reading Companion 目前最有价值的 AI-native workflow，不是“用 AI 更快写代码”，而是把 AI 放进一个 repo-first、证据驱动、可恢复的协作系统里。

这个系统的核心是：

- 用 AI 帮你澄清产品目的、拆解机制设计、比较架构方案、生成和修复代码、设计评测、解释结果。
- 同时用稳定文档、任务注册、决策记录、job registry、run artifact、validation gate 来约束 AI 的漂移。
- 让每一轮 AI 工作尽量留下可被下一个线程接住的证据，而不是只留下“当时聊明白了”的聊天记忆。

截止目前，你已经形成的有效 AI 协同方法可以概括为：

- 把 AI 当作 co-designer，而不是单纯的 executor。
- 把模糊问题先转成文档化边界，再让 AI 在边界内执行。
- 把评测结果转成因果解释、选择性实现或明确 defer，而不是只收集分数。
- 把长任务、后台任务、失败任务和被废弃路径都纳入可追踪的 evidence system。
- 把文档当作 AI agent 的上下文接口，而不是人类事后整理材料。

如果继续提升，最值得补强的是：更早为每一轮 AI 工作定义 evidence contract。也就是在开工前明确：

- 这一轮到底要回答什么问题
- 什么证据足够改变决策
- 哪些 artifact 只是 diagnostic evidence
- 哪些输出会更新 stable docs / task registry / decision log
- 什么时候应该停止、重跑、缩小范围或废弃当前路线

项目后期已经形成了这套意识，但前期很多成本来自边做边发现 benchmark、runner、dataset lane、long-span 方法本身的证据边界不够清楚。

## Observed Workflow Patterns

### 1. 用 AI 做需求澄清：从功能描述走向产品本质

项目早期不是把 Reading Companion 固定成“总结器”或“找 blind spots 的工具”，而是反复借助 AI 对产品目的做重新表述，最后稳定成“a genuinely curious, self-propelled co-reading mind”。

具体证据：

- [`docs/product-overview.md`](../product-overview.md) 把产品本质定义为“让读者接触一个活的、好奇的共读心智”，并明确不是 summary engine。
- [`docs/history/decision-log.md`](../history/decision-log.md) 中 `DEC-012` 记录了从较窄的 blind-spot 叙事转向 living co-reader mind。
- `DEC-013` 进一步把 product purpose 从 interaction-model 文档中拆出来，成为独立 stable authority。
- [`docs/backend-reader-evaluation.md`](../backend-reader-evaluation.md) 又把这个产品目的翻译成 evaluation constitution，避免评测被某个实现形态绑架。

这说明你已经在使用 AI 做一件很高级的事：不是让 AI 直接给产品 slogan，而是让 AI 参与“概念边界整理”，再把整理结果固化为后续机制、评测、UI 决策的上游约束。

可复用方法：

- 先让 AI 展开多个可能的产品解释。
- 再让 AI 帮你识别哪一种解释能统一后续机制、评测和体验设计。
- 一旦选择，就写入 stable doc，而不是停留在 chat。
- 后续所有技术方案都要反问：它是否服务这个产品本质？

### 2. 用 AI 做问题拆解：把大设计拆成可追踪工程系统

新阅读机制不是从一份 Notion 设计直接跳到代码实现。项目中间建立了一整套“设计到执行”的转换层。

关键材料：

- [`docs/implementation/new-reading-mechanism/source-mirror.md`](../implementation/new-reading-mechanism/source-mirror.md)
  - 保存 upstream Notion 设计的 source-faithful mirror，目标是防止细节被摘要吞掉。
- [`docs/implementation/new-reading-mechanism/design-capture.md`](../implementation/new-reading-mechanism/design-capture.md)
  - 把源设计整理成 implementation-oriented skeleton。
- [`docs/implementation/new-reading-mechanism/requirement-ledger.md`](../implementation/new-reading-mechanism/requirement-ledger.md)
  - 把设计点拆成 atomic requirements，并要求每一项有 disposition。
- [`docs/implementation/new-reading-mechanism/implementation-plan.md`](../implementation/new-reading-mechanism/implementation-plan.md)
  - 把机制实现拆成 phases、dependencies、exit criteria。
- [`docs/implementation/new-reading-mechanism/validation-matrix.md`](../implementation/new-reading-mechanism/validation-matrix.md)
  - 定义每个阶段需要的 unit / integration / compatibility / runtime / evaluation / docs 验证。

这是一种典型的 AI-native 复杂项目方法：AI 很擅长综合与实现，但也容易在大设计里无声遗漏。因此你没有只让 AI“理解一下然后开写”，而是建立了 omission-control system。

长期有效的原则不是某个具体文档名，而是这个分层：

- source-faithful mirror：保留原始意图
- normalized design capture：整理成可执行结构
- atomic requirement ledger：防止遗漏
- implementation tracker：驱动执行
- validation matrix：防止“看起来完成”
- stable docs：承载最后的长期权威

### 3. 用 AI 做架构迭代：先建立边界，再比较机制

Reading Companion 的架构演进不是简单地“V2 比 V1 好，所以替换”。更准确地说，是先用 AI 协助建立可比较的机制边界，再在同一产品目标下比较机制。

关键演进：

- `DEC-015` / `DEC-016`
  - 从单一 `iterator_reader` 走向 shared runtime shell 与 canonical `book_document.json`。
- `DEC-020`
  - 把机制私有 artifact 移到 `_mechanisms/<mechanism_key>/`，避免顶层 runtime 结构继续被一个机制污染。
- `DEC-021`
  - 把 backend reading doc 拆成 shared mechanism-platform doc 和 per-mechanism docs。
- `DEC-029`
  - 让 `attentional_v2` 从 design-only 变成 experimental end-to-end runtime path。
- `DEC-055`
  - 完成 compatibility-first default cutover，让 `attentional_v2` 成为正常产品 deep-reading path，同时保留 `iterator_v1` fallback。

这体现出一个很强的方法：你不是让 AI 在旧架构里无限 patch，而是先要求 AI 帮你识别“哪些东西是 shared shell，哪些东西是 mechanism-private ontology”。这使得后续机制比较更公平，也更容易由多个 agent 接力。

### 4. 用 AI 做技术方案比较：不止比较 winner，而是抽取可迁移模式

项目中很重要的一步，是把评测结果从“谁赢了”升级为“什么能力值得保留、什么失败模式要避免”。

证据：

- [`docs/implementation/new-reading-mechanism/mechanism-pattern-ledger.md`](../implementation/new-reading-mechanism/mechanism-pattern-ledger.md)
  - 记录 `iterator_v1` 的 local micro-selectivity、`attentional_v2` 的 chapter-scale thematic threading，以及各自失败模式。
- `DEC-035`
  - 明确要求 evaluation preserve portable strengths and repeatable failures，而不是只有 winner/loser conclusion。
- `DEC-036`
  - 要求每轮 meaningful evaluation 都闭环到 causal interpretation、selective implementation 或 explicit deferment。

这是一种成熟的 AI 协作方式：AI 不只是跑比较，还要帮助你从比较中抽取“机制设计知识”。这使得旧机制不会被粗暴丢弃，新机制也不会机械吞并旧机制所有行为。

可复用原则：

- 好结果不等于照抄。
- 坏结果不等于全盘否定。
- 每个发现都要有 disposition：
  - adopt now
  - defer for later synthesis
  - reject as misaligned
  - avoid
  - diagnostic only

### 5. 用 AI 管理 prompt 与上下文：从 prompt 文本走向 context architecture

项目没有把 prompt 当成一堆散落的字符串，而是逐渐把 prompt ownership、context packet、state digest 变成架构边界。

证据：

- `DEC-022` 把 prompt ownership 按边界拆分：
  - shared prompt fragments
  - capability-scoped prompts
  - mechanism-private prompts
  - legacy shims
- [`docs/backend-reading-mechanisms/attentional_v2.md`](../backend-reading-mechanisms/attentional_v2.md) 记录了 `state_packet.v1`、`concept_digest`、`thread_digest`、carry-forward context、supplemental recall / look-back 等机制。
- [`reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md`](../../reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md) 直接从 coding agent 的上下文管理中提炼启发：
  - index-first memory
  - compaction + re-injection
  - side-context isolation
  - session continuity
- `DEC-069` 甚至把 coding agent 的经验迁移到 detour 设计里：使用 maps、handles、stepwise narrowing，而不是沉重的预计算 semantic recall。

这说明你已经形成了一条长期有效原则：复杂 AI 产品不能依赖一个越来越大的 prompt blob。它需要 typed state、索引、摘要、按需检索、prompt packet，以及明确的 always carry / selective carry / not carry 规则。

### 6. 用 AI 探索评测方法：评测也是产品设计对象

项目的评测不是静态 scoreboard，而是一个不断被 AI 协助重构的系统。

关键模式：

- [`docs/backend-reader-evaluation.md`](../backend-reader-evaluation.md) 定义了 product-first、mechanism-agnostic 的 evaluation constitution。
- `DEC-030` 把 benchmark quality 提升为一等问题，并要求 dual diagnosis。
- `DEC-031` 在人工 review 稀缺时，用 multi-prompt LLM adjudication 替代默认人工阻塞，同时保留 human review 作为更高信任升级路径。
- `DEC-064` 因为 candidate retrieval 使用 string similarity 而不是 source-span overlap，直接 invalidated April 15 retry2 run。
- `DEC-076` 在 target-centered accumulation v2 被修好之后，仍然把它从 active Long Span 方法中 retired，因为项目问题已经转向 Memory Quality / Spontaneous Callback / False Visible Integration。

这体现出很强的 AI-native 判断：你不是把 LLM-as-judge 当作绝对裁判，而是把 judge prompt、candidate retrieval、source alignment、review policy、run validity 都当作可被审查和改进的系统组件。

### 7. 用 AI 做实现、调试和回归：把执行变成可恢复系统

项目后期明显形成了“AI 执行 + durable registry + staged artifacts + recovery”的工作方式。

证据：

- `DEC-037`
  - 引入 durable registry for long-running eval and dataset background jobs。
- `DEC-063`
  - 引入 registry-level long-horizon auto-recovery，不只依赖 gateway retry 或 orchestrator-local retry。
- `DEC-050`
  - 把 comparison work artifact-staged 成 `bundle -> judge -> merge`。
- `DEC-051`
  - 不再保护 sunk cost，而是检查已有 run 是否产生可复用 artifact 后决定是否 restart。
- `DEC-052`
  - 把 throughput 当作 Phase 9 gate，而不是单纯 operator inconvenience。
- `DEC-053`
  - 用 chapter-unit readiness 替代 whole-surface smoke gate。
- [`docs/tasks/registry.json`](../tasks/registry.json)
  - 记录 task status、decision refs、job refs、evidence refs、next action。
- [`docs/current-state.md`](../current-state.md)
  - 记录 active jobs、run ids、watchdogs、commands、expected outputs、recovery posture。

这是一种高价值协作模式：AI 不只是“执行命令”，而是把长任务组织成可被重启、审计、归档和接力的工程对象。

### 8. 用 AI 维护文档、任务注册和交接：文档是 agent-memory API

Reading Companion 的文档系统已经明显不只是“写给人看的说明”。它是 AI agent 接力工作的上下文接口。

证据：

- [`AGENTS.md`](../../AGENTS.md)
  - 规定 load matrix、doc routing、trigger matrix、cross-doc update rules。
- [`docs/source-of-truth-map.md`](../source-of-truth-map.md)
  - 把 durable information 映射到 canonical location、machine-readable companion、validation command、update trigger。
- [`docs/current-state.md`](../current-state.md)
  - 保存当前 objective、active tasks、jobs、blockers、recommended reading path。
- [`docs/tasks/registry.md`](../tasks/registry.md) 和 [`registry.json`](../tasks/registry.json)
  - 保存 task router、status、priority、job refs、decision refs、evidence refs。
- [`docs/history/decision-log.md`](../history/decision-log.md)
  - 保存未来 agent 很难从代码直接恢复的关键决策和 rejected alternatives。

这套系统的本质是：让未来 AI 不必“相信上一个聊天线程”，而是从 repo 中恢复项目状态。

## Effective Practices

### Repo-First Memory

你已经建立了一个很强的习惯：聊天可以孵化想法，但 durable truth 必须进 repo。

有效之处：

- active work 不依赖单个线程
- 新 agent 可以按 load matrix 进入上下文
- 决策可以从 decision log 和 evidence refs 恢复
- scratch notes 被明确降级，不会长期冒充 truth

### Boundary-First Collaboration

在让 AI 动手前，项目经常先明确边界：

- product purpose vs interaction model
- shared runtime vs mechanism-private ontology
- public API normalization vs internal artifact
- prompt ownership vs capability ownership
- stable docs vs history vs temporary handoff
- factual dataset truth vs benchmark judgment target

这显著降低了 AI 修改错层、抽象错层或过度泛化的风险。

### Dual Diagnosis

项目不是把坏结果直接归因给机制，也不是把坏结果都归因给 benchmark。它要求同时检查：

- mechanism weakness
- dataset / case / harness weakness
- benchmark size adequacy

这是评测复杂 AI 系统时非常关键的长期原则。

### Selective Synthesis

你没有把机制比较变成“谁赢谁全拿”。例如 `iterator_v1` 的 local micro-selectivity 被保留为 adoption candidate，但没有因此回到 section-first 架构。

这是很成熟的 AI-native synthesis：吸收行为背后的 causal strength，而不是复制表面形态。

### Evidence-Gated Execution

项目后期越来越少做“再完整跑一遍看看”，而是倾向于：

- 小 slice 验证
- staged runner
- explicit shard ownership
- resume / skip-existing
- root merge ownership
- watchdog recovery
- diagnostic vs formal evidence 区分

这让 AI 执行从“努力跑完”变成“带着证据边界地推进”。

### AI-Assisted Review With Provenance

multi-prompt LLM adjudication 是一个务实选择，但项目没有把它神化。它同时记录：

- review origin
- review policy
- prompt/rubric identity
- same-input reproducibility
- final adjudicator input shape
- quota-only failures

这说明你已经把 AI reviewer 当成一个需要治理的系统，而不是绝对权威。

### Long-Running Work As Durable State

长任务有 job id、run id、command、log、expected outputs、watchdog、recovery policy。这对 AI 协作特别重要，因为 AI agent 最容易丢的是“后台还有什么没结束，以及这个 job 当初为什么跑”。

## Failure Modes / Anti-Patterns

### 1. 先跑 benchmark，再发现 benchmark 问错了问题

`DEC-064` 是典型案例：user-level selective v1 本应测试 source-span grounded note recall，但 runner 曾经通过 string similarity 放入候选，导致 run 的问题变成“有没有说类似的话”。这个 run 必须 invalidated。

教训：

- LLM judge 前面的 candidate gate 比 judge prompt 本身还重要。
- 解释 run 之前，要先验证 harness 测的是否还是原问题。

### 2. Dataset / infrastructure lane 容易变成主项目

`DEC-047` 记录了这个风险：builder、packet review、closed-loop controller、manifest、automation 都很有价值，但如果没有边界，它们会拖住真正的 mechanism comparison。

教训：

- dataset platform 是 enabling system，不是独立成功目标。
- 一旦某个 slice 足够诊断，就应该回到 frozen-slice comparison，而不是无限优化 builder。

### 3. 机制节点过度拆分会制造责任漂移

`Read -> Express` 曾经有用，因为它帮助隔离 visible wording 和 surfaced semantics。但后续 `DEC-067` / `DEC-068` / `DEC-071` 说明它不是最终形态，项目最后把 surfaced reactions 重新收回 `Read`。

教训：

- 多一个 AI 节点不一定更清晰。
- 如果节点之间重复理解、重复表述或转移 ownership，复杂度会变成机制噪音。

### 4. Chat memory 曾经不足以承载长任务

`DEC-037`、`DEC-040`、`DEC-063` 共同说明，长任务如果只靠 handoff note 或聊天记忆，会丢失：

- 是否仍在运行
- 检查命令
- 决策背景
- run output 是否可复用
- 失败后是否应自动恢复

项目通过 job registry 和 current-state/task registry 解决了大部分问题。

### 5. Current truth、evidence truth、historical truth 容易混淆

user-level selective v1 曾经出现 active dataset pointer 与 formal evidence bundle 不一致的 dual-pointer posture。项目后来显式记录并最终退休该姿态。

教训：

- “当前 active dataset”
- “最新 formal evidence”
- “superseded prior package”
- “diagnostic failed run”

这些身份必须分开写清楚，否则后续 AI 很容易引用错证据。

### 6. 工具阶段技巧容易伪装成长期原则

以下是阶段性技巧：

- 当前模型作为 judge
- 当前 provider tier / worker cap
- 当前 watchdog interval
- 当前 same-key concurrency 假设
- 当前 Codex / Claude Code 的 context window 行为
- 当前某个 orchestration script 的参数形态

它们有用，但不能当作长期原则。

长期原则是：

- model choice 必须显式
- prompt / rubric / profile 必须可追踪
- run scope 内语义上下文要 pinned
- 失败要分类
- artifact 要可复用
- evidence identity 要清楚

### 7. LLM-as-judge 自身会漂移

评测文档已经记录了 same-input audit drift、rubric direction、adjudicator input shape、quota-only failures 等问题。

教训：

- LLM judge 不是“更聪明的 assert”。
- 它需要 replay、fingerprint、rubric identity、structured inputs、bounded retry、human calibration。

## Reusable Principles

### 1. 先外部化上下文，再扩大 AI 执行规模

复杂 AI 项目不能依赖一个长聊天线程。上下文必须外部化为：

- stable docs
- current-state docs
- task registries
- job registries
- manifests
- decision logs
- evidence reports

### 2. 每类信息只能有一个主要权威位置

项目文档层已经证明这个原则很有效：

- current status -> `docs/current-state.md`
- task routing -> `docs/tasks/registry.*`
- design history -> `docs/history/decision-log.md`
- mechanism internals -> per-mechanism docs
- eval constitution -> `docs/backend-reader-evaluation.md`
- session scratch -> `docs/agent-handoff.md`

这让 AI 不需要猜“该相信哪个文件”。

### 3. 把模糊协作变成 contract

AI 适合在 contract 内高效工作。复杂问题应尽快形成：

- product thesis
- mechanism boundary
- prompt packet contract
- judge rubric
- artifact ownership rule
- source-span matching rule
- phase exit criteria
- doc update trigger

### 4. 评测系统也要被评测

在 AI 产品里，评测 harness 也是 AI 系统的一部分。候选检索、judge prompt、rubric、case provenance、source alignment、summary merge 都可能出错。

因此 run result 不是第一手真相；run validity 才是第一道门。

### 5. 失败路径要保留，但要贴标签

项目保留了大量 failed、invalidated、superseded、diagnostic evidence。这个习惯非常重要。失败 run 如果身份清楚，就是未来决策的资产；如果身份不清楚，就是未来 AI 的陷阱。

### 6. 不机械合并机制优点

比较机制时，长期目标不是赢者通吃，而是提取 causal design strength。任何 adoption 都要问：

- 是否符合当前 approved mechanism 的 ontology？
- 是否破坏 control loop？
- 是否只是表面 prompt style？
- 是否会重新引入已知 anti-pattern？

### 7. 长任务必须默认可恢复

任何超过一个普通 session 的任务都应有：

- job id
- run id
- command
- output path
- status checker
- expected artifact
- recovery posture
- 它要服务的 decision

这不是流程负担，而是 AI 协作的安全基础设施。

### 8. 区分工具技巧和 AI-native 原则

长期可复用的是：

- repo-first memory
- evidence-gated decisions
- source-grounded evaluation
- typed context / index-first memory
- explicit task routing
- provider/model policy as config
- evaluation-to-implementation loop

阶段性的是：

- 当前模型
- 当前 prompt wording
- 当前 provider setup
- 当前 worker counts
- 当前 automation script
- 当前 UI / CLI 工具能力

未来项目应迁移原则，而不是复刻所有战术细节。

## Improvement Suggestions

### 1. 更早写 evidence contract

每个较大 AI 任务开工前，建议先写一个短 contract：

- 这轮要回答什么问题
- 最小可接受证据是什么
- 什么结果会改变决策
- 什么结果只是 diagnostic
- 哪些文档可能需要更新
- stop / restart / narrow-scope 条件是什么

这能减少后续“这个 run 到底算不算 formal evidence”的不确定性。

### 2. 在大实现前加入显式 red-team pass

项目已经擅长 eval 后 dual diagnosis。下一步可以把部分 adversarial thinking 前移：

- 这个设计最可能错在哪里？
- 哪个 hidden compatibility surface 会被影响？
- 哪个 benchmark 可能被这个变化误导？
- 哪个 doc layer 可能被写错？
- 如果这个方案失败，最小证据会是什么？

### 3. 为高影响 LLM judge 建立小规模 human calibration

multi-prompt LLM review 很适合当前速度要求，但高影响评测仍需要少量人工校准样本。

优先校准：

- user-level selective note recall 的边界案例
- Long Span `Memory Quality` probe rubrics
- `False Visible Integration` 的 borderline cases

目标不是人工审完全部，而是定期检查 LLM judge 是否还在测同一个问题。

### 4. 为 AI workflow 单独保留轻量过程记录

现有 decision log 很适合工程与产品 inflection。未来可以在 `docs/case-study/` 或 `docs/process/` 下保留更轻量的 workflow log，记录：

- 什么时候引入某种 agent-memory pattern
- 什么时候从人工 review 转向 LLM adjudication
- 哪次 job registry / watchdog 明显救回了工作
- 哪次 micro-slice 替代 broad rerun 明显提高效率
- 哪个 AI 协作方式后来证明是阶段性技巧

这样后续写 case study 会更轻，不必每次重新考古工程文档。

### 5. 给 AI 生成的文档设置 retirement / authority 规则

项目文档很强，但文档量本身会成为上下文成本。未来新增过程文档时，建议默认写清：

- owner / purpose
- update trigger
- not-for
- authority level
- validation command 或使用方式
- temporary doc 的退休条件

这能防止 AI 生成的好文档慢慢变成长期上下文负担。

### 6. 固化 post-run interpretation 模板

每次重要评测结束后，可以统一输出：

- what ran
- what changed from prior evidence
- valid evidence
- diagnostic-only evidence
- mechanism findings
- dataset / harness findings
- likely causal factors
- implementation actions
- defer / reject reasons
- next smallest rerun

项目已经经常这么做，但模板化后会更利于多 agent 接力。

### 7. 继续保持模型独立性

不要让某个模型的当前风格变成隐藏基础设施。Prompt、judge rubric、profile binding、provider config、trace output 都应保持 versioned / replayable。

对未来复杂 AI 产品来说，模型会变，principle 要留下。

### 8. 继续把 AI 当作共同设计者

你最强的 AI 协作不是“让 AI 帮忙干活”，而是持续让 AI 参与这些问题：

- 这个产品真正要保留的体验是什么？
- 这个机制的真实控制单元是什么？
- 这个评测到底在测什么？
- 哪些证据足够改变方向？
- 哪些失败模式未来不能再重复？
- 下一个 agent 需要从哪里接住？

这就是这套 workflow 最值得继续强化的核心能力。

## Evidence Links

核心工作流与 agent memory：

- [`AGENTS.md`](../../AGENTS.md)
- [`docs/source-of-truth-map.md`](../source-of-truth-map.md)
- [`docs/current-state.md`](../current-state.md)
- [`docs/tasks/registry.md`](../tasks/registry.md)
- [`docs/tasks/registry.json`](../tasks/registry.json)
- [`docs/agent-handoff.md`](../agent-handoff.md)
- [`docs/history/decision-log.md`](../history/decision-log.md)

产品与评测框架：

- [`docs/product-overview.md`](../product-overview.md)
- [`docs/product-interaction-model.md`](../product-interaction-model.md)
- [`docs/backend-reader-evaluation.md`](../backend-reader-evaluation.md)
- [`reading-companion-backend/docs/evaluation/README.md`](../../reading-companion-backend/docs/evaluation/README.md)
- [`reading-companion-backend/docs/evaluation/user_level/README.md`](../../reading-companion-backend/docs/evaluation/user_level/README.md)
- [`reading-companion-backend/docs/evaluation/long_span/README.md`](../../reading-companion-backend/docs/evaluation/long_span/README.md)

机制设计、拆解与验证：

- [`docs/backend-reading-mechanism.md`](../backend-reading-mechanism.md)
- [`docs/backend-reading-mechanisms/attentional_v2.md`](../backend-reading-mechanisms/attentional_v2.md)
- [`docs/backend-reading-mechanisms/iterator_v1.md`](../backend-reading-mechanisms/iterator_v1.md)
- [`docs/history/reading-agent-evolution-roadmap.md`](../history/reading-agent-evolution-roadmap.md)
- [`docs/implementation/new-reading-mechanism/design-capture.md`](../implementation/new-reading-mechanism/design-capture.md)
- [`docs/implementation/new-reading-mechanism/source-mirror.md`](../implementation/new-reading-mechanism/source-mirror.md)
- [`docs/implementation/new-reading-mechanism/source-mirror-top-level.md`](../implementation/new-reading-mechanism/source-mirror-top-level.md)
- [`docs/implementation/new-reading-mechanism/source-mirror-contracts.md`](../implementation/new-reading-mechanism/source-mirror-contracts.md)
- [`docs/implementation/new-reading-mechanism/requirement-ledger.md`](../implementation/new-reading-mechanism/requirement-ledger.md)
- [`docs/implementation/new-reading-mechanism/implementation-plan.md`](../implementation/new-reading-mechanism/implementation-plan.md)
- [`docs/implementation/new-reading-mechanism/validation-matrix.md`](../implementation/new-reading-mechanism/validation-matrix.md)
- [`docs/implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md`](../implementation/new-reading-mechanism/new-reading-mechanism-execution-tracker.md)
- [`docs/implementation/new-reading-mechanism/mechanism-pattern-ledger.md`](../implementation/new-reading-mechanism/mechanism-pattern-ledger.md)
- [`docs/implementation/new-reading-mechanism/attentional_v2_structural_rework_plan.md`](../implementation/new-reading-mechanism/attentional_v2_structural_rework_plan.md)

Prompt、context 与 AI-agent 设计参考：

- [`reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md`](../../reading-companion-backend/docs/research/claude_code_context_management_research_20260412.md)

代表性 decision-log entries：

- `DEC-008`: layered documentation system
- `DEC-011` / `DEC-014`: product-first, mechanism-agnostic evaluation constitution
- `DEC-021`: shared mechanism doc plus per-mechanism docs
- `DEC-022`: prompt ownership by boundary
- `DEC-030` / `DEC-031`: dataset quality, packet review, and LLM adjudication
- `DEC-035` / `DEC-036`: portable strengths, anti-patterns, and evaluation-to-implementation loop
- `DEC-037` / `DEC-040` / `DEC-063`: durable agent/job memory and auto-recovery
- `DEC-050` / `DEC-051` / `DEC-052` / `DEC-053`: staged execution, restart gates, throughput gates, and unit readiness
- `DEC-055`: compatibility-first default cutover to `attentional_v2`
- `DEC-057` through `DEC-072`: structural rework and dead-path cleanup
- `DEC-076`: retirement of target-centered accumulation v2 as active Long Span methodology
