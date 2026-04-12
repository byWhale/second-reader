# Claude Code 上下文管理调研与对 Reading Companion 的启发

日期：2026-04-12

## 1. 调研对象与证据范围

这篇文章的目标，不是复述 Claude Code 的产品新闻，而是提炼它在上下文管理上的可借鉴机制，并判断这些机制对 Reading Companion 当前的新阅读机制设计有没有直接帮助。

本文综合使用了三类材料：

- 官方文档与官方公开仓库：
  - [How Claude remembers your project](https://code.claude.com/docs/en/memory)
  - [Explore the context window](https://code.claude.com/docs/en/context-window)
  - [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works)
  - [Create custom subagents](https://code.claude.com/docs/en/sub-agents)
  - [anthropics/claude-code](https://github.com/anthropics/claude-code)
- 泄露后分析资料：
  - [liuup/claude-code-analysis](https://github.com/liuup/claude-code-analysis)
  - 其中重点参考：
    - [04-agent-memory.md](https://github.com/liuup/claude-code-analysis/blob/main/analysis/04-agent-memory.md)
    - [04f-context-management.md](https://github.com/liuup/claude-code-analysis/blob/main/analysis/04f-context-management.md)
    - [04i-session-storage-resume.md](https://github.com/liuup/claude-code-analysis/blob/main/analysis/04i-session-storage-resume.md)
- 其他公开解读文章，只作为辅助交叉验证，不作为本文核心依据。

本文不把“官方公开版”和“泄露版”当成两个不同产品。它们描述的是同一个应用，但暴露的是不同深度的实现切面：

- 官方材料更适合确认 Claude Code 对外已经明确的行为，例如 memory 如何加载、`/compact` 后什么会重新进入上下文、subagent 是否使用独立上下文。
- 泄露实现与反编译分析更适合理解内部组织方式，例如 session transcript 如何存储、memory 目录如何被索引、resume/rehydrate 可能如何工作。

为了保持正文可读性，本文不做“官方篇 / 泄露篇”分栏，而是在关键结论里使用轻量标记：

- `官方已明确`：可以直接从 Anthropic 官方文档或官方公开仓库确认。
- `内部实现显示`：从泄露实现与多方分析中可较稳定看出的内部组织方式。
- `设计启发`：对 Reading Companion 有启发，但不应当机械照抄。

## 2. Claude Code 如何管理上下文

### 2.1 它不是把一切都塞进同一个上下文里

Claude Code 最值得学的第一点，不是某个神秘 prompt，而是它明显在把不同性质的上下文拆层处理。

`官方已明确`：

- 每次 session 启动时，Claude Code 会把 `CLAUDE.md`、auto memory、系统指令、技能描述等一起装入上下文。
- `CLAUDE.md` 是用户自己维护的持久指令层。
- auto memory 是 Claude Code 自己写下来的项目记忆层。

这说明 Claude Code 的基本态度不是“让模型背着完整历史一直往前走”，而是先区分几类不同来源的上下文，再决定它们何时进入窗口。

对 Reading Companion 来说，这和我们当前已经讨论出来的方向高度一致：阅读状态也不应再被做成一个“大而混的总记忆块”，而应该拆成性质不同的层，例如：

- `working_state`
- `concept_registry`
- `thread_trace`
- `reflective_frames`
- `anchor_bank`

### 2.2 它的长期记忆是 index-first，而不是 blob-first

Claude Code 在上下文管理上最醒目的一个设计，是把长期记忆做成“入口索引 + 详细主题文件”的形式，而不是每次启动都把所有记忆全量注入。

`官方已明确`：

- auto memory 目录使用 `MEMORY.md` 作为入口。
- 每次启动时，只会加载 `MEMORY.md` 的前 `200` 行，或者前 `25KB`，以先到者为准。
- 更详细的 topic files 不会在启动时自动进入上下文，而是按需读取。

这意味着它的长期记忆不是一个“越写越胖的总摘要”，而更像一个分层索引系统：

- `MEMORY.md` 负责告诉模型“重要的长期记忆有哪些、分别在哪里”
- 详细内容只在真正需要时再被拉进上下文

`内部实现显示`：

- 泄露后的分析基本都指向同一个结构：`MEMORY.md` 作为索引，topic files 作为正文，运行时通过相关性召回读取需要的主题。

这是对 Reading Companion 最直接的一条启发。

我们当前刚形成的新状态设计，如果仍然把全部 `concept_registry`、全部 `thread_trace`、全部 `reflective_frames` 整包塞给每次 Read 调用，实际上仍然是在走旧式“大 blob 上下文”路径。Claude Code 的做法提示我们，更合理的方向应该是：

- `concept_registry` 有一个短索引，详细词条按需调取
- `thread_trace` 有一个活跃脉络摘要，详细 milestone 按需展开
- `reflective_frames` 保持简短，只作为较稳定理解的入口视图
- `anchor_bank` 不常驻 prompt，而是作为证据底座按需检索

### 2.3 它把 compaction 做成“压缩 + 重注入”，而不是一次性总结

很多系统的上下文压缩，实质上只是“做一段摘要，然后继续聊”。Claude Code 给出的更强思路，是把压缩和重注入结合起来。

`官方已明确`：

- `/compact` 会把对话历史压缩成结构化 summary。
- 压缩后，project-root `CLAUDE.md` 会从磁盘重新读取并重新注入上下文。
- auto memory 也会重新进入上下文。
- 某些 path-scoped 规则或内容会在再次命中相应路径时再懒加载。

这说明它对上下文压缩的理解不是“彻底丢掉旧内容，留下一个摘要”，而是：

1. 先把高体积历史压缩掉
2. 再把真正应该持续存在的持久上下文重新装回窗口

`内部实现显示`：

- 泄露后的分析进一步指向：compaction 后并不只是保存一段自然语言总结，还会重建部分运行态依赖的上下文入口。

`设计启发`：

Reading Companion 后面如果做长书阅读中的压缩、章节切换恢复、长 session resume，也不应该只留下一个“阅读总结”。更合理的是显式区分：

- 哪些状态是 `always reload`
- 哪些状态是 `on-demand retrieval`
- 哪些原文证据只在 `bridge / revisit` 发生时才需要再取

如果没有这层“可回水化”的设计，压缩就很容易变成一次不可逆的信息损失。

### 2.4 它把 subagent 的核心价值放在“隔离上下文”

Claude Code 的另一个关键点，是把 subagent 设计成独立上下文窗口中的工作者，而不是只把它当成并行 worker。

`官方已明确`：

- 每个 subagent 运行在自己的 context window 中。
- 它完成工作后，只把结果摘要返回主线程。
- 这样做的一个核心收益，就是把大文件读取、长日志分析、资料搜索等高 token 行为隔离在侧上下文中。

这对 Reading Companion 很有帮助，因为我们后面很可能也会遇到几类“高体积但不应污染主阅读线程”的动作：

- backward evidence search
- long look-back
- bridge verification
- 外部知识核对
- 某一条 thread 的专门回看

这些工作如果都直接放进主阅读上下文，很容易让阅读线程过快膨胀。Claude Code 的启发是：不要怕有 side context，关键是要让主线程只带回“够用的结果”，而不是把整个搜证过程也背在身上。

### 2.5 它把会话连续性外置成可恢复材料

Claude Code 不是把连续性全部寄托在当前窗口里。它显然也在把 session continuity 外置出来。

`官方已明确`：

- Claude Code 会把 session transcript 存到本地目录下，以支持 resume、fork 等能力。

`内部实现显示`：

- 泄露分析高度一致地指出，它把 transcript 视为 append-only JSONL 事件流。
- 主线程 transcript 和 subagent transcript 是分开的 sidechain 文件。
- resume 时会重新读取 transcript，并对 compact、snip、parallel tool result 等造成的链路缺口做恢复与重建。

即使具体实现以后还会变，这条设计思路本身也非常重要：

- 写入层尽量简单
- 恢复层承担复杂性

`设计启发`：

Reading Companion 未来如果要支持真正强的长时阅读 continuity，也许需要把“当前会话连续性”单独作为一层来设计，而不是混进 durable reading memory 里。换句话说：

- durable memory 负责“这本书已经建立了什么对象和脉络”
- session continuity 负责“当前这一轮阅读正在延续什么局部焦点和局部工作”

这两件事不完全一样。

## 3. 官方公开面与泄露内部面的关系

围绕 Claude Code 的一个常见误解是：既然官方仓库已经公开，那泄露材料是不是只是“重复了一份源码”？

更准确的理解是：它们属于同一个应用，但暴露的是不同层级的源码面。

### 3.1 它们不是两个应用

这点是明确的。无论是官方公开仓库、官方文档，还是泄露后被分析出的内部实现，讨论的都是 Claude Code 这个终端 coding agent。

所以从产品身份上说，不存在“官方版 Claude Code”和“泄露版 Claude Code”两个不同东西。

### 3.2 但它们暴露的深度不同

`官方已明确`：

- 官方公开仓库 [anthropics/claude-code](https://github.com/anthropics/claude-code) 是正式对外可见的代码面。
- 但它的定位更像 public surface：文档、脚本、插件、命令与对外扩展结构都能看到。
- 官方文档还明确公开了大量行为层事实，例如 memory 如何加载、`/compact` 之后什么会重新进入上下文、subagent 是否有独立上下文窗口。

`内部实现显示`：

- 泄露后的资料之所以信息量更大，不是因为它描述了另一个产品，而是因为它把更深一层的内部实现也暴露出来了。
- 比如：
  - transcript 如何落盘
  - `MEMORY.md` 如何扮演索引
  - resume/rehydrate 如何组织
  - sidechain transcript 如何和主线程分离

因此，如果只回答“泄露版是不是更详细”，答案基本是：

- `是，它对内部实现的细节明显更详细。`

但如果把这个结论再说完整一点，应当是：

- 官方材料更适合回答“Claude Code 明确承诺了什么行为”
- 泄露实现更适合回答“Claude Code 内部大概率是怎么把这些行为做出来的”

这不是“真假”的差别，而是“行为契约层”和“内部组织层”的差别。

### 3.3 对我们来说，最好的使用方式不是二选一

如果只看官方资料，我们能看到很多高层原则，但看不到内部组织到底有多分层。

如果只看泄露资料，我们会更容易理解实现结构，但也容易把内部细节误认为稳定接口。

对 Reading Companion 来说，更好的姿势是把两者结合起来：

- 用官方资料确认 Claude Code 上下文管理的原则性轮廓
- 用泄露后的内部实现线索帮助我们看清哪些设计不是概念，而是真实落地的工程结构

## 4. 对 Reading Companion 的直接启发

如果把 Claude Code 的上下文管理经验映射到 Reading Companion 当前的新机制设计，我认为最值得吸收的有六点。

### 4.1 继续坚持 typed state，不回退到 summary blob

Claude Code 说明，成熟系统不会把所有连续性都压成一个自然语言摘要大块。它会把不同性质的上下文分层存放。

这对我们是正向确认：

- `working_state`
- `concept_registry`
- `thread_trace`
- `reflective_frames`
- `anchor_bank`

这样的分层方向是对的，应继续在 V2 的 typed spine 上推进，而不是回退到一个大的“memory_text blob”。

### 4.2 但 typed state 不能只是“很多桶”，还要有入口索引

我们当前的新设计已经比旧机制清楚很多，但如果每一层都持续膨胀，它仍然会变成复杂的大系统。

Claude Code 的启发是：`不是每一层都直接进 prompt，而是先有 index。`

对我们来说，更合适的推进方式应当是：

- `concept_registry`
  - 一个短 index 列出当前最重要的人物、机构、地点、概念
  - 详细词条按需读取
- `thread_trace`
  - 一个活跃 thread digest 列出当前最重要的叙事线 / 论证线
  - milestone 细节按需读取
- `reflective_frames`
  - 保持短，只保留章级 / 书级理解入口
- `anchor_bank`
  - 不做 prompt 常驻层，只作为证据底座

也就是说，我们不只是要“分层”，还要“分层后再分入口视图和详细层”。

### 4.3 应该单独引入 `session continuity memory`

这是这轮调研对我们最重要的新启发之一。

我们之前讨论的 `working_state`、`concept_registry`、`thread_trace`、`reflective_frames`，已经足以覆盖很多阅读状态，但它们还没有专门承载“当前这一轮阅读会话的连续性”。

Claude Code 的 transcript / resume 设计提示我们，可以把这件事再明确一层：

- `session continuity memory`
  - 只负责当前 session 的局部连续性
  - 例如当前正在追的局部问题、最近一段的推理势能、当前未关闭的 bridge pressure、最近一次压缩前的 continuation capsule

这样可以避免把“当前这一轮的阅读续航”错误地混进全书 durable memory。

### 4.4 应该提前设计 `always reload` 与 `on-demand retrieval`

Claude Code 的强点不只是“有 memory”，而是对 memory 的载入时机有明确策略。

这对我们后面很重要，因为阅读机制迟早会遇到上下文预算问题。相比事后被动压缩，更好的做法是现在就明确：

- `always reload`
  - 当前章或当前阅读窗口必须持续存在的少量状态
  - 当前 session continuity capsule
  - 极短的 concept/thread active digest
- `on-demand retrieval`
  - 详细 concept entries
  - 详细 thread milestones
  - 大段原文锚点
  - 历史 reaction bundles

如果这个边界不提前定，后面实现时很容易把所有结构都重新走回“常驻上下文”的老路。

### 4.5 `anchor_bank` 应坚持做证据底座，不做泛化记忆

Claude Code 的经验还从反面提醒了我们：有些层必须清晰守边界，否则系统会变得越来越乱。

对 Reading Companion 来说，`anchor_bank` 最适合承担的角色是：

- 书内 source-linked anchor 的存放处
- anchor 与 anchor 之间 typed relation 的底座
- bridge / revisit 时的证据召回入口

它不应该承担：

- “人物是谁”
- “这个概念是什么意思”
- “整本书大致讲到哪里”

这些分别应留给：

- `concept_registry`
- `thread_trace`
- `reflective_frames`

这样系统的语义边界才清楚。

### 4.6 高体积回看动作应优先进入 side context

Claude Code 把 subagent 主要用来隔离上下文，这一点非常值得我们吸收。

对 Reading Companion 来说，后面如果某个动作满足下面任一条件，就应优先考虑 side context：

- 需要大段回看原文
- 需要在多个历史 anchor 之间做搜证
- 需要专门核对某条 thread 是否闭合
- 需要引入外部知识进行低频核查

主阅读线程更像“持续向前读的意识流”，而 side context 更像“为了验证、回看、整理而短暂开的偏旁工作区”。这样才能让主线程保持清晰。

## 5. 明确不照搬的部分

Claude Code 很强，但它是 coding agent。Reading Companion 不是 coding agent，所以有几类东西不适合直接平移。

### 5.1 不照搬 instruction hierarchy 本身

Claude Code 的 `CLAUDE.md`、rules、hooks、commands、skills 体系，是围绕 coding workflow 设计的。

Reading Companion 当然也需要规则和机制文档，但我们的核心问题不是“如何管理开发规范”，而是“如何维护文本理解状态”。所以不能把 Claude Code 的 instruction hierarchy 当作阅读机制本身。

### 5.2 不照搬权限壳、工作流壳与 IDE 壳

Claude Code 的很多设计都服务于它作为 coding tool 的运行环境：

- 终端命令
- 文件系统权限
- git workflow
- IDE 集成
- 插件与 hooks

这些能力可以启发“控制层怎么组织”，但不能直接回答“阅读状态该如何表示”。

### 5.3 不照搬过重的多 agent 编排

Claude Code 里与 subagent、agent teams 相关的设计，对上下文管理很有价值，但对 Reading Companion 来说，过早引入复杂的多 agent 团队编排会使系统迅速变重。

更合适的做法是：

- 先吸收“side context 用于隔离高体积工作”这个原则
- 暂时不把整个阅读机制设计成一个多 agent orchestration 系统

### 5.4 不把内部实现细节误写成我们的设计目标

Claude Code 泄露后最容易诱发的一种误区，是把某些具体内部结构当成“先进系统的标准答案”。

对 Reading Companion 来说，更好的方法是：

- 学设计原则
- 学层次边界
- 学载入时机
- 学恢复机制

而不是照抄某个目录结构、某个内部函数名或某个具体日志格式。

## 6. 结论

如果把这次调研压缩成一句话，那么 Claude Code 给 Reading Companion 的最大启发是：

**真正好的上下文管理，不是让模型始终背着越来越多的历史，而是把“应该永远带着的”“可以按需再取的”“只在当前会话里续航的”三类东西分开。**

对我们当前的新阅读机制而言，这条启发可以落成下面几项具体方向：

- 保持 V2 式 typed state 作为底座
- 在 typed state 之上增加 index-first 的入口层
- 单独引入 `session continuity memory`
- 为 `always reload` 和 `on-demand retrieval` 提前定义边界
- 让 `anchor_bank` 严格回到证据底座角色
- 把高体积回看、搜证、核桥动作隔离到 side context

这几条都不是“抄 Claude Code”，而是借它来帮助我们把自己的阅读机制做得更清楚、更有工程弹性。
