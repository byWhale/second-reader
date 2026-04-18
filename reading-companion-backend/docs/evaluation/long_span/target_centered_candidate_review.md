# Target-Centered Long-Span V2 Candidate Review

Status: main batch is `draft_candidate` only; `芒格之道` appears below as an `experimental_appendix` only. Nothing in this document is frozen, and no eval rerun was performed.

Discovery rule: every candidate below was mined from the active正文窗口原文 (`segment_sources/*.txt`) only. `note cases`, `excerpt cases`, and historical probes were excluded from discovery.

## Overview

| Book | Window | Candidate count | Notes |
| --- | --- | ---: | --- |
| 悉达多 | `xidaduo_private_zh__segment_1` | 6 | Self-learning, world-acceptance, recurrence, and late-stage reinterpretation. |
| 活出生命的意义 | `huochu_shengming_de_yiyi_private_zh__segment_1` | 4 | Multiple scenes or incidents later get explicitly gathered under a sharper stated lesson. |

Thread-type mix in the active main batch:
- `叙事型故事脉络`: `2`
- `概念/区分澄清线`: `5`
- `论证型论证线`: `3`

Review structure:
- Main freeze-candidate batch:
  - `悉达多`
  - `活出生命的意义`
- Experimental appendix:
  - `芒格之道`

Draft artifacts written by this pass:
- Review doc: `reading-companion-backend/docs/evaluation/long_span/target_centered_candidate_review.md`
- Draft case dataset: `reading-companion-backend/state/eval_local_datasets/accumulation_target_cases/attentional_v2_accumulation_benchmark_v2_cases_draft`
- Draft manifest: `reading-companion-backend/eval/manifests/splits/attentional_v2_accumulation_benchmark_v2_draft.json`

## 悉达多

### `xidaduo_seg1_tc01_no_teaching_can_deliver`

- `candidate_id`: `xidaduo_seg1_tc01_no_teaching_can_deliver`
- `book / window`: `悉达多` / `xidaduo_private_zh__segment_1`
- `thread_type`: `概念/区分澄清线`
- `one-line thread`: 求道欲望、修行失败与见佛后的拒绝，最终汇成“解脱不可被他人转交”。
- `target_span`:
```text
您已超拔死亡。您通过探索，求道，通过深观，禅修，通过认知，彻悟而非通过法义修成正果！——这就是我的想法，哦，世尊，没人能通过法义得到解脱！

这就是我为何要继续我的求道之路——并非去寻找更好的法义，我知道它并不存在——而是为摆脱所有圣贤及法义，独自去实现我的目标，或者去幻灭。
```
- `upstream_nodes`:
  - `u1` 早期求道焦灼: 开篇已经怀疑别人指不出真正的道路。
```text
啊，没人能指明这条路。没人认得它。
```
  - `u2` 修行不可学得: 在婆罗门与沙门经验后形成“无法学会”的判断。
```text
长久以来我耗费时间，现在仍未停止耗费，只为了获悉，哦，乔文达，人无法学会任何东西！
```
  - `u3` 面对真正神圣者: 见到佛陀的真实庄严之后仍拒绝追随。
```text
这个人，佛陀，周身上下乃至手指都是真的。这个人是神圣的。
```
- `expected_integration`: target 处应整合出：拒绝追随佛陀是早期怀疑、修行失败和见佛后判断共同压出的结论。
- `why_it_is_long_range`: 从开篇婆罗门之子到佛陀相遇处，天然跨过多个章节团块。
- `span_audit`: paragraphs `10 -> 157` (span `147`)
- `distinct_from_neighbors`: 测的是“解脱不可由他人转交”，不是一般成长叙事。
- `risk_notes`: 最容易被答成空泛的“每个人都要走自己的路”。

### `xidaduo_seg1_tc02_world_not_behind_appearances`

- `candidate_id`: `xidaduo_seg1_tc02_world_not_behind_appearances`
- `book / window`: `悉达多` / `xidaduo_private_zh__segment_1`
- `thread_type`: `概念/区分澄清线`
- `one-line thread`: 从追问阿特曼在哪里，到承认蓝就是蓝、河水就是河水。
- `target_span`:
```text
蓝就是蓝，河水就是河水。在悉达多看来，如果在湛蓝中，在河流中，潜居着独一的神性，那这恰是神性的形式和意义。它就在这儿的灿黄、湛蓝中，在那儿的天空、森林中，在悉达多中。意义和本质绝非隐藏在事物背后，它们就在事物当中，在一切事物当中。
```
- `upstream_nodes`:
  - `u1` 寻找隐藏真理: 开篇把真理想成在事物背后的东西。
```text
可阿特曼在哪里？
```
  - `u2` 苦修把人送回轮回: 以“我”为起点的修行被证明仍旧回到轮回。
```text
这些修行均从“我”出发，终点却总是回归于“我”。尽管悉达多千百次弃绝“我”，逗留在虚无中，化为动物、石头，回归却不可避免。重归于“我”无法摆脱。在阳光中、月华下，在遮荫处和雨中，他重新成为“我”，成为悉达多，重新忍受轮回赋予的折磨。
```
  - `u3` 转向向自己与世界学习: 离开佛陀后决定拜自己为师。
```text
我要拜自己为师。我要认识自己，认识神秘的悉达多。
```
- `expected_integration`: target 处应把“蓝就是蓝”读成对早期形上追索的长程修正，而不是单纯写景。
- `why_it_is_long_range`: 从开头的形上追索跨到离开佛陀后的世界接受，距离明确。
- `span_audit`: paragraphs `10 -> 180` (span `170`)
- `distinct_from_neighbors`: 测的是世界不再被当作障眼法，而不是一般自然赞歌。
- `risk_notes`: 如果只读成景物哲学，前面的形上追索链会丢失。

### `xidaduo_seg1_tc03_samana_skills_redeployed`

- `candidate_id`: `xidaduo_seg1_tc03_samana_skills_redeployed`
- `book / window`: `悉达多` / `xidaduo_private_zh__segment_1`
- `thread_type`: `概念/区分澄清线`
- `one-line thread`: 沙门苦修里的“思考、等待、斋戒”，后来被改造成在世能力。
- `target_span`:
```text
你看，迦摩罗，如果你将一粒石子投入水中，石子会沿着最短的路径沉入水底。恰如悉达多有了目标并下定决心。悉达多什么都不做，他等待、思考、斋戒。他穿行于尘世万物间正如石子飞入水底——不必费力，无需挣扎；他自会被指引，他任凭自己沉落。目标会指引他，因为他禁止任何干扰目标的事情进入他的灵魂。这是悉达多做沙门时学到的。愚人们称其为魔法。愚人以为此乃魔鬼所为。其实，魔鬼无所作为，魔鬼并不存在。每个人都能施展法术。每个人都能实现目标，如果他会思考、等待、斋戒。
```
- `upstream_nodes`:
  - `u1` 苦修的原始目的: 最早把苦修当作自我消灭的路径。
```text
悉达多唯一的目标是堕入空无。无渴慕，无愿望，无梦想。无喜无悲。“我”被去除，不复存在。让空洞的心灵觅得安宁，在无“我”的深思中听便奇迹。这是他的目标。当“我”被彻底征服，当“我”消亡，当渴求和欲望在心中寂灭，那最终的、最深的非“我”存在，那个大秘密，必定觉醒。
```
  - `u2` 苦修失败: 后来明确认定这些修行仍会把人带回轮回。
```text
这些修行均从“我”出发，终点却总是回归于“我”。尽管悉达多千百次弃绝“我”，逗留在虚无中，化为动物、石头，回归却不可避免。重归于“我”无法摆脱。在阳光中、月华下，在遮荫处和雨中，他重新成为“我”，成为悉达多，重新忍受轮回赋予的折磨。
```
  - `u3` 能力被带入城中生活: “思考、等待、斋戒”变成现实资源。
```text
我会思考。我会等待。我会斋戒。
```
- `expected_integration`: target 处应说明：同一套沙门能力先被否定，后又被重部署为理解命运与行动时机的资源。
- `why_it_is_long_range`: 跨越沙门阶段、反省阶段和城中世界。
- `span_audit`: paragraphs `73 -> 274` (span `201`)
- `distinct_from_neighbors`: 测的是旧能力如何被重用，不是单纯的修行失败。
- `risk_notes`: 如果只回忆名句，会漏掉“重部署”这一层。

### `xidaduo_seg1_tc04_become_child_again`

- `candidate_id`: `xidaduo_seg1_tc04_become_child_again`
- `book / window`: `悉达多` / `xidaduo_private_zh__segment_1`
- `thread_type`: `概念/区分澄清线`
- `one-line thread`: 回头看整段人生，悉达多把自己理解成必须先成为愚人，才能重新开始。
- `target_span`:
```text
在这漫长曲折的路上，一个男人成了孩子，一位思考者成了世人。然而这条路又十分美好，然而我胸中之鸣鸟尚未死去。这是怎样的路！为重新成为孩子，为从头再来，我必须变蠢、习恶、犯错。必须经历厌恶、失望、痛苦。可我的心赞许我走这条路，我的眼睛为此欢笑。为收获恩宠，重新听见“唵”，为再次酣睡，适时醒来，我必须走投无路，堕入深渊，直至动了愚蠢的轻生之念。为了重新找到内在的阿特曼，我必须先成为愚人。
```
- `upstream_nodes`:
  - `u1` 知识的极限: 很早就怀疑知识不能真正通向阿特曼。
```text
长久以来我耗费时间，现在仍未停止耗费，只为了获悉，哦，乔文达，人无法学会任何东西！我想，万物中根本没有我们称之为‘修习’的东西。哦，我的朋友，只有一种知识，它无处不在，它就是阿特曼。
```
  - `u2` 转向自我之师: 离开模仿他人的路，开始向自身经验学习。
```text
我要拜自己为师。我要认识自己，认识神秘的悉达多。
```
  - `u3` 轮回中的枯竭: 沉入世俗后感到在荒诞轮回中衰老枯竭。
```text
在这荒诞的轮回中，他疲惫不堪，衰老而虚弱。
```
  - `u4` 唵的回返: 濒临自毁时，被“唵”重新拉回。
```text
“唵！”他自语，“唵！”他又认识了阿特曼，不灭的生命，认识了一切他遗忘的神圣事物。
```
- `expected_integration`: target 处应把“成为孩子/愚人”读成对整段旅程的后见整合，而不是普通挫折教育。
- `why_it_is_long_range`: 从求知危机到濒死回返，时间跨度和意义跨度都很大。
- `span_audit`: paragraphs `92 -> 392` (span `300`)
- `distinct_from_neighbors`: 测的是整段人生的后见重解释。
- `risk_notes`: 最容易被答成鸡汤式成长叙事。

### `xidaduo_seg1_tc05_kamala_death_instant_eternal`

- `candidate_id`: `xidaduo_seg1_tc05_kamala_death_instant_eternal`
- `book / window`: `悉达多` / `xidaduo_private_zh__segment_1`
- `thread_type`: `叙事型故事脉络`
- `one-line thread`: 迦摩罗从欲望对象变成共同生命、死亡现场与永恒感悟的载体。
- `target_span`:
```text
他呆坐着，凝视她长眠的脸，她衰老、疲惫，不再丰满的嘴唇，想起早年自己曾把它比作新鲜开裂的无花果。他呆坐着，凝视她苍白的脸，倦怠的皱纹，仿佛凝视自己苍白倦怠的脸。他看见他们年轻时的容颜，鲜红的嘴唇，炙热的双眼。两种情境交织着充满他，成为永恒。他比以往更深刻地体会到生命不灭，刹那即永恒。
```
- `upstream_nodes`:
  - `u1` 初见迦摩罗: 最初是纯粹欲望与美的震动。
```text
他看见她高高挽起的乌发云髻下一张靓丽、娇柔、聪慧的脸。她美艳的红唇好似新鲜开裂的无花果，精心修饰的眉毛描成高挑的弧形，一双乌黑的明眸聪敏而机智。
```
  - `u2` 生活意义的转移: 城中生活的意义转成“与迦摩罗在一起”。
```text
对于现在的悉达多，生活的意义和价值是能和迦摩罗在一起，而绝非迦摩施瓦弥的生意。
```
  - `u3` 性爱与死亡相邻: 亲密经验里已经出现性与死相近的感受。
```text
她狂热地紧紧拥抱他，流着泪亲他、咬他，仿佛要从虚幻短促的快感中榨取最后一滴甘露。悉达多从未如此明白，性和死是如此相近。
```
  - `u4` 留下儿子: 迦摩罗在死前把共同生命的延续交给悉达多。
```text
你可也认得他？他是你的儿子。
```
- `expected_integration`: target 处应把迦摩罗线串成：欲望、依附、死亡与生命延续被压进同一时刻，因此“刹那即永恒”。
- `why_it_is_long_range`: 横跨整段城中生活到河边重逢。
- `span_audit`: paragraphs `208 -> 466` (span `258`)
- `distinct_from_neighbors`: 测的是迦摩罗线如何在后段被重写。
- `risk_notes`: 如果只说“他很悲伤”，会错过情欲—死亡—孩子—永恒的叠合。

### `xidaduo_seg1_tc06_father_son_voices_to_om`

- `candidate_id`: `xidaduo_seg1_tc06_father_son_voices_to_om`
- `book / window`: `悉达多` / `xidaduo_private_zh__segment_1`
- `thread_type`: `叙事型故事脉络`
- `one-line thread`: 悉达多曾让父亲受苦，后来自己因儿子受苦，在当前之痛中把这条线扩展成众人的共同处境。
- `curator_note`: `525-528` 是理解链完成区，正式 target 取 `528`，避免 `529` 的过度总收束。
- `target_span`:
```text
悉达多加倍专注于倾听。父亲、自己和儿子的形象交汇。还有迦摩罗、乔文达、其他人，他们的形象交汇并融入河水，热切而痛苦地奔向目标。河水咏唱着，满载渴望，满载燃烧的苦痛和无法满足的欲望，奔向目标。悉达多看见由他自己，他热爱的、认识的人，由所有人组成的河水奔涌着，浪花翻滚，痛苦地奔向多个目标，奔向瀑布、湖泊、湍流、大海；抵达目标，又奔向新的目标。水蒸腾，升空，化作雨，从天而降，又变成泉水、小溪、河流，再次融汇，再次奔涌。然而渴求之音有所改变，依旧呼啸，依旧满载痛苦和寻觅，其他声音，喜与悲、善与恶、笑与哀之声，成千上万种声音却加入进来。
```
- `upstream_nodes`:
  - `u1` 离家时父亲的痛: 少年出走时父亲已经承受过无法挽回的儿子之痛。
```text
父亲意识到，悉达多已不在他身边。他已离开家乡，离开他。
```
  - `u2` 自问为何当年不必受此苦: 轮到自己做父亲时开始追问这份痛。
```text
是谁保护沙门悉达多免于罪孽、贪婪和愚昧？是他父亲的虔诚，老师的规劝，还是他自己的学识和求索？人独自行过生命，蒙受玷污，承担罪过，痛饮苦酒，寻觅出路。
```
  - `u3` 父子之苦对照: 终于承认父亲当年也曾这样受苦。
```text
难道父亲不是为他受苦，如同他现在为儿子受苦？难道父亲不是再没见到儿子，早已孤零零地死去？这难道不是一幕奇异又荒谬的谐剧？不是一场宿命的轮回？
```
  - `u4` 河中听见无数父子: 个人故事被普遍化为无数代际哀歌。
```text
他看见孤单的父亲哀念着儿子，孤单的自己囚禁在对远方儿子的思念中；他看见孤单年少的儿子贪婪地疾进在炽烈的欲望之路上。每个人都奔向目标，被折磨，受苦难。河水痛苦地歌唱着，充满渴望地歌唱着，不断涌向目标，如泣如诉。
```
- `expected_integration`: target 处应把父亲、自己、儿子与众人的受苦链条连成一体，读出当下之痛如何回带过去并扩展为普遍处境，而不是只把它读成最终“唵”式圆满。
- `why_it_is_long_range`: 横跨少年离家、成为父亲、失去儿子、河边倾听四个阶段。
- `span_audit`: paragraphs `51 -> 528` (span `477`)
- `distinct_from_neighbors`: 测的是“当下之痛 -> 回带过去 -> 推到普遍处境”的链，而不是最终唵式圆满本身。
- `risk_notes`: 若把目标点放得过晚，容易直接坍缩成总收束；因此正式 target 前移到段 528。

## 活出生命的意义

### `huochu_seg1_tc01_love_beyond_presence`

- `candidate_id`: `huochu_seg1_tc01_love_beyond_presence`
- `book / window`: `活出生命的意义` / `huochu_shengming_de_yiyi_private_zh__segment_1`
- `thread_type`: `论证型论证线`
- `one-line thread`: 前面多种失去与想念的经验，最后被“爱超越在场”这一命题统摄。
- `target_span`:
```text
忽然间，我一生中第一次领悟到一个真理，它曾被诗人赞颂，被思想家视为绝顶智慧。这就是：爱是人类终身追求的最高目标。我理解了诗歌、思想和信仰所传达的伟大秘密的真正含义：拯救人类要通过爱与被爱。我知道世界上一无所有的人只要有片刻的时间思念爱人，那么他就可以领悟幸福的真谛。在荒凉的环境中，人们不能畅所欲言，唯一正确的做法就是忍受痛苦，以一种令人尊敬的方式去忍受，在这种处境中的人们也可以通过回忆爱人的形象获得满足。我生平第一次理解这句话 “天使存在于无比美丽的永恒思念中”。

即使我知道妻子已死去，也不会影响我对她的殷切思念，我与她的精神对话同样生动，也同样令人满足。“心就像被上了封条，一切如昨”。
```
- `upstream_nodes`:
  - `u1` 家人作为求生动力: 最开始，对家人的牵挂与求生和互助直接绑定。
```text
为了家中等待着他归来的亲人，他必须要活下来并保护自己的朋友。
```
  - `u2` 思念的吞噬性: 后来这种思念强烈到足以吞噬人。
```text
对家乡和家庭的无限思念，有时强烈到足以将其吞噬。
```
  - `u3` 死者视角中的城市: 作者重新看世界时已像阴间人般隔绝。
```text
我明显感觉自己是在用阴间人的眼光看我童年生活的街道、广场和房屋，俯瞰着这个令人毛骨悚然的城市。
```
- `expected_integration`: target 处应说明：爱的领悟是在求生动力、思念折磨与死亡式隔绝之后才成立的，爱不再依赖现实在场。
- `why_it_is_long_range`: 从入营早期跨到晚段关于妻子的领悟。
- `span_audit`: paragraphs `8 -> 105` (span `97`)
- `distinct_from_neighbors`: 代表这本书典型的“事迹/场景 -> 后置点题”写法。
- `risk_notes`: 容易被压平为一般性的“爱能跨越距离”，要保留前面具体场景的支撑力。

### `huochu_seg1_tc02_humor_art_weapon`

- `candidate_id`: `huochu_seg1_tc02_humor_art_weapon`
- `book / window`: `活出生命的意义` / `huochu_shengming_de_yiyi_private_zh__segment_1`
- `thread_type`: `论证型论证线`
- `one-line thread`: 前面关于营中处境与自我调适的多个场景，最后被“幽默是一种精神武器”点题收束。
- `target_span`:
```text
幽默是灵魂保存自我的另一件武器。大家都知道，幽默比人性中的其他任何成分更能够使人漠视困苦，从任何境遇中超脱出来，哪怕只是几秒种。
```
- `upstream_nodes`:
  - `u1` 冷酷幽默萌生: 最早的极端环境里已经出现冷酷幽默。
```text
大多数人开始被冷酷的幽默感战胜。此刻，我们知道，除了赤裸裸的身躯之外自己真的是一无所有了。淋浴时，我们尽情地开玩笑，既取笑自己也取笑别人，也为真正的水从浴室的喷头里流出来而深感庆幸。
```
  - `u2` 笑作为唯一反应: 个体在极端羞辱中只能笑。
```text
我笑了笑，我相信任何处在我这个位置上的人也都只能如此。
```
  - `u3` 主动练习玩笑: 后来囚徒有意识地用歌、诗和玩笑训练这种距离感。
```text
大家唱歌、做诗、开玩笑，间或隐晦地讽刺一下集中营。所有这一切都是为了帮助我们忘却，当然这也的确管用。
```
  - `u4` 艺术造成超越间隙: 小提琴与夜色提供了短暂离开现实的经验。
```text
突然间，一阵沉寂，一把小提琴向夜空奏出了绝望而悲伤的探戈舞曲，因为演奏得很流畅，所以曲子听上去很美。提琴在哭泣，我身体的一部分也在哭泣，因为那天正好是某人的24岁生日。
```
- `expected_integration`: target 处应把“幽默是武器”读成一条长线：从冷酷讽刺、无奈之笑，到主动练习，并与艺术共同组成灵魂防卫术。
- `why_it_is_long_range`: 跨过早期生存反应、中段集体练习和晚段理论概括。
- `span_audit`: paragraphs `41 -> 114` (span `73`)
- `distinct_from_neighbors`: 测的是多个局部经验如何在后段被同一道理重新照亮。
- `risk_notes`: 如果只记住幽默这句话，会漏掉它为何在极端处境里成立。

### `huochu_seg1_tc03_future_goal_responsibility`

- `candidate_id`: `huochu_seg1_tc03_future_goal_responsibility`
- `book / window`: `活出生命的意义` / `huochu_shengming_de_yiyi_private_zh__segment_1`
- `thread_type`: `论证型论证线`
- `one-line thread`: 人的生命力与责任、未来任务和“知道为何而活”被一条长线串起来。
- `target_span`:
```text
只要有可能，你就应该告诉病人为什么要活下去，一个目标就足以增强他们战胜疾病的内在力量。

认识到自己对所爱的人或者未竟的事业的责任，也就永远不会抛弃自己的生命。他知道自己存在是 “为了什么”，也就知道 “如何”继续活下去。
```
- `upstream_nodes`:
  - `u1` 手稿作为求生理由: 起初把保存手稿当作活下来的唯一希望。
```text
手稿是我活下来的唯一希望。要相信命运，但我无法控制自己，我要不惜一切代价保留这个耗尽我毕生精力的手稿。
```
  - `u2` 心里继续写作/演讲: 在病与劳累中仍靠未来讲述和写作任务维持意识。
```text
为了避免昏迷，我也和其他人一样尽量在夜里保持清醒。我需要在脑海里用几个钟头组织语言，重新构思我在奥斯维辛传染病房里丢失的手稿，或者干脆用速记法在小纸片上记下关键词。
```
  - `u3` 未来讲台的想象: 把自己想成未来的讲者，把当前痛苦对象化。
```text
突然，我看到自己站在明亮、温暖而欢快的讲台上，面前坐着专注的听众。我在给他们讲授集中营心理学！那一刻，我从科学的角度客观地观察和描述着折磨我的一切。通过这个办法，我成功地超脱出当时的境遇和苦难，好像所有这些都成了过去。我和我的痛苦都成为自己心理学研究的有趣对象。
```
  - `u4` 未来崩塌导致死亡: 朋友因预言未兑现而绝望死去。
```text
我朋友最终的死因是预言没有如期兑现，他绝望了。这使他身体抵抗力急剧减弱，导致潜伏的伤寒感染发作。他对未来的希望和活下去的意志都没有了，身体也就成为疾病的牺牲品——虽然他梦里声音所说的最终都应验了。
```
- `expected_integration`: target 处应明确：作者的“why/how”不是口号，而是由自己的未来任务线和朋友的未来崩塌共同支撑起来的责任论。
- `why_it_is_long_range`: 从入营时对手稿的执念跨到后段医学式概括。
- `span_audit`: paragraphs `34 -> 202` (span `168`)
- `distinct_from_neighbors`: 测的是前面零散的生存心理观察如何在后面被统合为一个原则。
- `risk_notes`: 容易被答成宽泛励志命题，要保留前面责任/未来感/具体人例的支撑。

### `huochu_seg1_tc06_noble_vs_base_across_roles`

- `candidate_id`: `huochu_seg1_tc06_noble_vs_base_across_roles`
- `book / window`: `活出生命的意义` / `huochu_shengming_de_yiyi_private_zh__segment_1`
- `thread_type`: `概念/区分澄清线`
- `one-line thread`: 前面关于囚徒、看守与营中角色的多重事迹，最后被“高贵与卑劣跨越角色分布”点题。
- `target_span`:
```text
世界上有 （且只有）两类人——高尚的和龌龊的。任何地方都有这两类人，人类社会的所有团体中也都有这两类人。没有哪个团体纯粹由高尚的人或者龌龊的人组成。从这个意义上说，不存在纯粹类型的团体。因此，即使在集中营看守当中，你偶尔也能发现一个高尚的人。
```
- `upstream_nodes`:
  - `u1` 囚头比看守更残忍: 最早就打破了“只有看守恶”的简单图式。
```text
与看守相比，这些人更为凶狠，在鞭打囚徒时更为残忍。
```
  - `u2` 残酷外表下的善意: 曾经粗暴的看守却一次次帮他保命。
```text
他还是竭尽全力想保住我的性命 （他也的确挽救了我许多次）。
```
  - `u3` 在分汤小事中守住公平: 有人在很小的行动里表现出真正的高尚。
```text
他是唯一一个不看人下菜碟、能做到均等分汤的厨子，他也从不照顾自己的朋友或同胞。其他厨子不是这样，他们给朋友或同胞捞土豆，只给其他犯人从上面舀清汤。
```
  - `u4` 面包与人性一闪: 递来一片面包时的神情也让高尚显影。
```text
我记得有一天，一个监工悄悄给了我一片面包，那一定是他从早饭中省下来的。当时我感动得热泪盈眶，不只是因为一块面包，他所给我的还有一份人性，跟礼物相伴的是他温暖的话语和仁慈的表情。
```
- `expected_integration`: target 处应说明“高尚/龌龊”这个新分类建立在多次跨角色反例上，而不是抽象人性论。
- `why_it_is_long_range`: 它依赖多处远距离具体案例来支撑一个后段概念重构。
- `span_audit`: paragraphs `4 -> 219` (span `215`)
- `distinct_from_neighbors`: 测的是道德分类如何由多个叙事实例推导出来，而不是单一轶事。
- `risk_notes`: 如果只说“人性复杂”，会丢掉作者真正的分类修正力度。

## Deferred Cases

- `The Value of Others` current four draft cases have been removed from the active main batch.
- Current posture: `deferred / architecture-first`. If this book re-enters long-span curation later, it should do so only after a separate theory-architecture pass rather than by promoting the current local-detail candidates.
- `芒格之道` remains outside the active main batch and appears below only as an experimental appendix, not as a main-batch freeze candidate.

## Experimental Appendix

### 《芒格之道》

Appendix status: `experimental_appendix` only. These candidates are kept for secondary review and possible future reserve use; they are not part of the active `10`-case main batch and should not be frozen together with the main batch.

### `mangge_seg1_exp_tc01_competence_circle_to_safety_margin`

- `candidate_id`: `mangge_seg1_exp_tc01_competence_circle_to_safety_margin`
- `book / window`: `《芒格之道》` / `mangge_zhi_dao_private_zh__segment_1`
- `thread_type`: `概念/区分澄清线`
- `one-line thread`: 从“不预测未来、如履薄冰”到“清楚自己能力的大小”，再到小能力圈与“不赚最后一个铜板”的安全边际纪律。
- `target_span`:
```text
目前，商业票据还没造成太大的损失，但是，不排除商业票据出现集中违约的可能性。赚尽最后一个铜板，这是银行和储贷机构犯过的错误。如今，货币市场基金重蹈覆辙，也想赚钱赚到尽。

在伯克希尔的不同时期，我们制定过管理闲置资金的各种规定。为了防范风险，我们制定的规矩，恰恰是不赚最后一个铜板。例如，我们会规定：参照高信用等级的标准收益率，如果某品种的收益率高出0.125%，则禁止投资。一笔投资，利率超出了正常水平，我们绝对不碰。另外，对于发行人，我们也有限制条件，只投资符合条件的发行人的品种。
```
- `upstream_nodes`:
  - `u1` 早期的不预测与不安:
```text
我要是真知道如何复制过去的成功，那可好了。其实，大多数时候，我们什么都不做。我们出手的时候很少。即使是出手的时候，我们也是如履薄冰，对可能承担的风险感到不安。以前的投资机会让我们感到踏实，现在我们觉得不踏实。
```
  - `u2` “谦卑”被重写成清楚能力与限制:
```text
用“谦卑”这个词也许不太恰当，可能用“务实”这个词更合适。我们能取得今时今日的成就，不是因为我们的能力比别人高出多少，而是我们比别人更清楚自己能力的大小。清楚自己能力的大小，这个品质应该不能说是“谦卑”。

充分认清客观条件的限制，充分认识自身能力的限制，谨小慎微地在限制范围内活动，这是赚钱的诀窍。这个诀窍，与其说是“谦卑”，不如说是“有克制的贪婪”。
```
  - `u3` 能力圈的小圆圈:
```text
好在本·格雷厄姆是个天才，在我们遇到的人中，很少有像他那么聪明的。另外，我们很清楚自己的不足，很清楚有很多事我们做不到，所以我们谨小慎微地留在我们的“能力圈”之中。“能力圈”是沃伦提出的概念。沃伦和我都认为，我们的“能力圈”是一个非常小的圆圈。

我年轻时，有个朋友说：“芒格只研究自己生意里的那点事，和他的生意无关的事，他一概不知。”在自己的已知与未知之间，我们画出明确的界线，我们只在已知的圆圈内活动。
```
- `expected_integration`: target 处应把“不赚最后一个铜板”读成前面整条认知边界哲学的晚期制度化落点，而不是一条孤立的风险偏好格言。
- `why_it_is_long_range`: 从 1987 年的“不预测未来”一直跨到 1990 年的“安全边际/不赚最后一个铜板”，横跨多个讲话年份与不同场景。
- `span_audit`: paragraphs `62 -> 624` (span `562`)
- `distinct_from_neighbors`: 这条测的是风险边界如何逐步定型；不是一般“要保守”。
- `risk_notes`: 容易被回答者压扁成单一“能力圈”名词；好的反应应把“不预测未来 -> 清楚限制 -> 小能力圈 -> 不赚最后一个铜板”串起来。

### `mangge_seg1_exp_tc02_self_interest_distorts_advice`

- `candidate_id`: `mangge_seg1_exp_tc02_self_interest_distorts_advice`
- `book / window`: `《芒格之道》` / `mangge_zhi_dao_private_zh__segment_1`
- `thread_type`: `概念/区分澄清线`
- `one-line thread`: 从鱼钩故事与“别问理发师”，到投行卖方信息，再到商学院对大公司的结构性失明，同一条“利益扭曲判断”底层哲学不断再显影。
- `target_span`:
```text
商学院需要大公司的捐赠，商学院的毕业生需要到大公司就业。所以说，从自己的利益出发，商学院不可能谴责大公司的不良行为，除非一家大公司已经遭到全社会的谴责，那商学院倒是可以跟着进行批判。即使是在商学院的象牙塔中，受利益驱使，也不能完全保持客观公正。

本·富兰克林说过：“结婚之前，擦亮双眼。结婚之后，睁一只眼闭一只眼。”商学院就是这么做的。它们已经嫁给了大公司，有些事情，只能睁一只眼闭一只眼。
```
- `upstream_nodes`:
  - `u1` 鱼钩故事与“别问理发师”:
```text
多年以前，我在帕萨迪纳市有个朋友，是做渔具生意的。他出售的鱼钩五颜六色的。我以前从没见过色彩这么丰富的鱼钩。我问他：“你这鱼钩五颜六色的，鱼是不是更容易上钩啊？”

他回答道：“查理，我这鱼钩又不是卖给鱼的。”

你们笑归笑，所有人都有这个倾向。所有人的潜意识里都有这样的偏见：给别人提建议时，以为是在为别人考虑，其实是从自己的利益出发。

自己用不用理发，别问理发师。从自己利益出发的，不仅仅是券商。
```
  - `u2` 卖方信息天然带利益:
```text
监管人员：您讲的话切中要害，这里的风险很难排查。在检查时，我们看到的信息都是投行提供的，而投行是证券化产品的卖方，它们在里面有自己的利益。
```
- `expected_integration`: target 处应把对商学院的批评读成同一条“利益结构使人无法保持客观”的再显影，而不是一段脱离前文的新吐槽。
- `why_it_is_long_range`: 1988 年已经用鱼钩故事明确提出原则，1990 年才把这原则推到制度与知识共同体层面。
- `span_audit`: paragraphs `99 -> 578` (span `479`)
- `distinct_from_neighbors`: 这条测的是“利益如何扭曲判断”；不是资本配置或风险边界那条主线。
- `risk_notes`: 例子非常生动，回答者容易停在鱼钩故事或商学院批评本身，而漏掉“同一底层哲学重复显影”的目标。

### `mangge_seg1_exp_tc03_waiting_against_dealmaking`

- `candidate_id`: `mangge_seg1_exp_tc03_waiting_against_dealmaking`
- `book / window`: `《芒格之道》` / `mangge_zhi_dao_private_zh__segment_1`
- `thread_type`: `论证型论证线`
- `one-line thread`: 好机会稀缺时宁愿守势、等待、做好眼前的事，最后落实为反对为做交易而做交易，也反对像打牌一样轻率买卖公司。
- `target_span`:
```text
现在要想买到好公司、价格还合适，非常难，用现金收购更难。如果自己公司的股票是高估的，用自己公司的股票收购同行，倒也不吃亏。至于像我们这样用现金收购的，那就难了。特别是最近一段时间，非常难。

现在人们热衷于收购。刷厕所、搬砖头，这些脏活累活没人干。收购多潇洒，大家都抢着干。管理层喜欢四处收购。再说花的又不是自己的钱，为了把收购做成，管理层总能编出很多理由。

西科不会随意卖出子公司。伯克希尔不会因为旗下的子公司遇到了困境，就一卖了之。只有当子公司出现我们根本无法解决的问题时，我们才会卖出。一家子公司，管理层诚实正直，在行业中表现中规中矩，但盈利能力不让人满意。遇到这样的情况，我们就吸取教训，以后不做类似的投资了。但是，我们不会把它卖掉。我们不会像打牌一样，抓一张、扔一张。
```
- `upstream_nodes`:
  - `u1` 早期收购哲学就是等待:
```text
有的人做收购，请来一群投行员工，以为听他们的建议，就能做成一笔又一笔完美的收购。对于这种做法，我实在不敢苟同。即使是投资机会很多的时候，我们辛辛苦苦地研究和跟踪各个机会，一年也只能做成一笔收购。

有些人钱多得烫手，四处收购，一笔接一笔的。这种收购方法，我不认同，很难有好结果。真正做收购是好事多磨，要熬过辛苦的等待，经历反复的波折。

以前，收购难做，我们还有别的出路。股市有好的投资机会，我们可以先投资股票。在等待收购某家公司的过程中，我们可以把资金先用于投资股票。我们西科以前一直是这么做的。我们在股市里投资过通用食品（General Foods）和埃克森（Exxon）这样的大公司，也投资过许多名不见经传的小公司。现在股市里好的投资机会没了，收购也很难做，两条路都不好走了，我们只能采取守势。
```
  - `u2` 中段把“等待”接成经营方式:
```text
我们始终把眼前所有的投资机会进行比较，力求找到当下最合理的投资逻辑，这才是重中之重。找到了最合理的投资逻辑之后，无论周期波动如何剧烈，是顺境还是逆境，我们都泰然自若。这就是我们的投资之道。我们不去做各种短期预测，我们追求的是长期的良好结果。

威廉·奥斯勒爵士（Sir William Osler）一砖一瓦地建成了世界著名的约翰斯·霍普金斯大学医学院（The Johns Hopkins University School of Medicine）。威廉·奥斯勒爵士信奉托马斯·卡莱尔（Thomas Carlyle）的一句名言：“与其为朦胧的未来而烦恼忧虑，不如脚踏实地，做好眼前的事。”这同样是伯克希尔的经营哲学。

手握大量现金，我们向威廉·奥斯勒爵士学习。脚踏实地，做好眼前的事，让公司顺其自然地长期发展。我们是一家特立独行的公司。
```
- `expected_integration`: target 处应把对收购热和“不随意卖子公司”的判断，读成同一条“不要为了做交易而做交易”的长期哲学，而不是几段分散的经营感想。
- `why_it_is_long_range`: 这条线从 1987 年的守势与等待，跨到 1989 年的“做好眼前的事”，再到 1990 年对收购热和随手卖公司的批评。
- `span_audit`: paragraphs `38 -> 645` (span `607`)
- `distinct_from_neighbors`: 这条强调等待与反交易冲动；不同于“能力圈/安全边际”那条认知边界线。
- `risk_notes`: 后段更像经营风格的重复显影，不如前两条那样凝聚，因此更适合作为 `secondary` 实验候选而不是优先保留项。

### Appendix Recommendation

- `mangge_seg1_exp_tc01_competence_circle_to_safety_margin` 和 `mangge_seg1_exp_tc02_self_interest_distorts_advice` 可以保留为实验储备。
- `mangge_seg1_exp_tc03_waiting_against_dealmaking` 可继续保留为次级实验项，但不建议进入当前主批次。
- 本附录只用于 review，不自动进入 active draft case dataset，也不和前面的 `10` 条主批次一起冻结。
