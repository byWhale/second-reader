# Historical Pre-Curation Long-Span Substrate Candidate Memo

Date: `2026-04-16`

## Scope

- This memo is a historical rolling candidate pool from the earlier bounded long-span substrate mining pass.
- Discovery source is restricted to the current excerpt/user-level window raw text under `segment_sources/*.txt`.
- `note cases`, `excerpt cases`, and old long-span probes were not used to discover candidates. They may be used later only for cross-checking.
- This memo is not a current dataset curation artifact. It predates the frozen target-centered v2 seed set and now survives only as archived pre-curation context.
- Line numbers below are taken from `nl -ba` on the current window source files.

## Summary Table

| Book | Window | Candidate count | Priority types | Current strongest candidate | Fit judgment |
| --- | --- | ---: | --- | --- | --- |
| 《悉达多》 | `xidaduo_private_zh__segment_1` | 3 | `叙事型故事脉络` / `概念/区分澄清线` | `不会爱 -> 因儿子变成完全的世人 -> 爱戴敬重众人` | `very high` |
| 《活出生命的意义》 | `huochu_shengming_de_yiyi_private_zh__segment_1` | 4 | `叙事型故事脉络` / `论证型论证线` | `失去未来感 -> 责任感/不可替代性 -> 知道为何而活` | `very high` |
| *The Value of Others* | `value_of_others_private_en__segment_1` | 5 | `论证型论证线` / `概念/区分澄清线` | `relationship as value medium -> rules/laws -> game of relationships` | `very high` |
| 《芒格之道》 | `mangge_zhi_dao_private_zh__segment_1` | 4 | `论证型论证线` / `概念/区分澄清线` | `no prediction -> circle of competence -> safety margin / don’t earn the last penny` | `high` |
| 《纳瓦尔宝典》 | `nawaer_baodian_private_zh__segment_1` | 5 | `论证型论证线` / `概念/区分澄清线` | `wealth vs money/status -> don’t rent time -> sleep-income assets` | `high` |

## 《悉达多》

Source window: `xidaduo_private_zh__segment_1`  
Source file: `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/segment_sources/xidaduo_private_zh__segment_1.txt`

### `xidaduo_c1_self_knowledge_beyond_teaching`

- `candidate_id`: `xidaduo_c1_self_knowledge_beyond_teaching`
- `book / window`: 《悉达多》 / `xidaduo_private_zh__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 父师和经典无法直接交付阿特曼，后来的法义与苦修也仍不够，直到他承认必须亲身走完整条愚行与迷途之路。
- `status`: `strong`
- `why_accumulation`: 后段的“必须亲历愚行与沉沦”只有带着前面的求道挫败和中段的学说不满足感，才会读成真正的 carryforward，而不是一句一般性的自我感悟。
- `EARLY`
> “他开始感到，他可敬的父亲和其他智慧的婆罗门已将他们大部分思想传授给他，而他依旧灵魂不安，心灵不宁……人必须找到它。内在‘我’之源泉，必须拥有自己的阿特曼！其他一切都只是寻觅、走弯路和误入歧途。”
- `MID`
> “我一直渴慕知识，充满疑惑。年复一年，我求教婆罗门，求教神圣的吠陀。年复一年，我求教虔诚的沙门……长久以来我耗费时间，现在仍未停止耗费，只为了获悉，哦，乔文达，人无法学会任何东西！”
- `LATE`
> “为了重新成为孩子，为从头再来，我必须变蠢、习恶、犯错。必须经历厌恶、失望、痛苦……为了重新找到内在的阿特曼，我必须先成为愚人。为了再活，我必须犯罪。”
- `原文定位`: `lines 19-21`, `lines 183-183`, `lines 783-795`
- `what_it_tests`: 是否能持续追踪“知识/修习/亲历”之间的关系重估，而不是把全书读成模糊的灵修主题。
- `distinct_from_neighbors`: 这条测的是“法义与亲历”的关系，不是父子情，也不是对世人的感同身受。
- `risk_notes`: `MID` 到 `LATE` 之间跨度很大，回答者若只记得“悉达多最后看开了”，容易把这条读成一般性成长叙事。

### `xidaduo_c2_love_turns_sage_into_worldling`

- `candidate_id`: `xidaduo_c2_love_turns_sage_into_worldling`
- `book / window`: 《悉达多》 / `xidaduo_private_zh__segment_1`
- `type`: `叙事型故事脉络`
- `one-line chain`: 他曾把自己和会爱的世人区分开来，但因儿子的到来陷入盲目的爱与屈辱，最终也正因这道伤口而理解并爱戴众人。
- `status`: `strong`
- `why_accumulation`: 这条链有清楚的 before/after reversal。后段“爱戴敬重众人”并不是突然发生，而是父爱之苦把他真正拉进了世人的生命逻辑。
- `EARLY`
> “大多数人，迦摩罗，仿佛一片落叶，在空中翻滚、飘摇，最后踉跄着归于尘土。有的人，极少数，如同天际之星，沿着固定的轨迹运行……你依然是个沙门。你并不爱我，也不爱任何人……如孩童般的世人才会爱。这是他们的秘密。”
- `MID`
> “他不禁突然记起年轻时迦摩罗曾对他说过：‘你不会爱。’……可是自从儿子出现，他悉达多却成了完全的世人。苦恋着，在爱中迷失；因为爱，而成为愚人……对儿子盲目的爱，是一种极为人性的激情。”
- `LATE`
> “如今，他见到那些常客——孩童般的世人，商人、兵士、妇人，不再感到陌生：他理解他们……他不再嘲笑他们的虚荣、欲望和荒谬，反而通晓他们，爱戴敬重他们。”
- `原文定位`: `lines 649-660`, `lines 985-987`, `lines 1027-1027`
- `what_it_tests`: 是否能记住人物早先对“爱”与“世人”的区分，并在后段读出这一区分如何被儿子打碎和改写。
- `distinct_from_neighbors`: 这条主要测“爱的能力如何改变人物对世人的理解”，不是“法义是否能教会人”。
- `risk_notes`: `EARLY` 带有迦摩罗对悉达多的外部评语，如果回答者只抓“你不会爱”而忽略他当时如何看世人，可能会把链条压得过窄。

### `xidaduo_c3_everyone_must_walk_his_own_path`

- `candidate_id`: `xidaduo_c3_everyone_must_walk_his_own_path`
- `book / window`: 《悉达多》 / `xidaduo_private_zh__segment_1`
- `type`: `叙事型故事脉络`
- `one-line chain`: 少年时他逼父亲放自己出走，后来却想阻止儿子走自己的路，最终在河水里看见父亲、自己和儿子的宿命轮回。
- `status`: `strong`
- `why_accumulation`: 这是非常清楚的父子回返结构。后段如果忘了早段的“出走”和中段的“不能替他走”，就读不出最终河水中的宿命闭合。
- `EARLY`
> “乔文达意识到：时候到了，悉达多要去走自己的路。他的命运即将萌发……‘你即将步入林中成为一名沙门。’”
- `MID`
> “你果真相信，你的蠢行，能免除他的蠢行？难道你通过教育、祈祷和劝诫，能保他免于轮回？……人独自行过生命，蒙受玷污，承担罪过，痛饮苦酒，寻觅出路。”
- `LATE`
> “难道父亲不是为他受苦，如同他现在为儿子受苦？……这难道不是一幕奇异又荒谬的谐剧？不是一场宿命的轮回？……父亲、自己和儿子的形象交汇……所有声音、目标、渴望、痛苦、欲念，所有善与恶合为一体，构成世界。”
- `原文定位`: `lines 45-45`, `lines 979-979`, `lines 1035-1057`
- `what_it_tests`: 是否能追踪跨代重复与回返，而不是只把“儿子出走”读成独立情节。
- `distinct_from_neighbors`: 这条测的是“命运与独自行路”，不是“爱如何改变他”。
- `risk_notes`: `LATE` 比较宏阔，容易被回答者泛化成“万物统一”；好的回答需要明确点出父亲/自己/儿子的三层回返。

## 《活出生命的意义》

Source window: `huochu_shengming_de_yiyi_private_zh__segment_1`  
Source file: `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/segment_sources/huochu_shengming_de_yiyi_private_zh__segment_1.txt`

### `huochu_c1_terror_numb_derealization`

- `candidate_id`: `huochu_c1_terror_numb_derealization`
- `book / window`: 《活出生命的意义》 / `huochu_shengming_de_yiyi_private_zh__segment_1`
- `type`: `叙事型故事脉络`
- `one-line chain`: 入营时的极度惊恐，经由适应期的保护性麻木，最终在解放时表现为无法真实感到自由的“人格解体”。
- `status`: `strong`
- `why_accumulation`: 这不是三句同主题心理描写，而是作者明确给出的三阶段心理轨迹；后段的解放反应只有连着前面的惊恐和麻木才真正成立。
- `EARLY`
> “除了极度惊恐，我没有其他感觉。从那一刻起，我们不得不逐渐适应这种极度恐慌的状态，直至习以为常。”
- `MID`
> “冷漠、迟钝、对任何事情都漠不关心是囚徒第二阶段心理反应的表现……正是由于这种冷漠外壳的包裹，囚徒们才能真正地保护自己。”
- `LATE`
> “从心理学的角度讲，得到解放的犯人最初的感觉叫‘人格解体’。一切都显得不真实、不可能，像是在梦中一样。我们不能相信这是真的。”
- `原文定位`: `lines 35-35`, `lines 121-121`, `lines 449-449`
- `what_it_tests`: 是否能把长段回忆组织成一个心理阶段弧线，而不是只抓住单个强烈句子。
- `distinct_from_neighbors`: 这条测的是阶段性心理变化，不是意义论证，也不是道德区分。
- `risk_notes`: `LATE` 是第三阶段的起点而非终点，但闭合度已经足够强。

### `huochu_c2_future_responsibility_against_collapse`

- `candidate_id`: `huochu_c2_future_responsibility_against_collapse`
- `book / window`: 《活出生命的意义》 / `huochu_shengming_de_yiyi_private_zh__segment_1`
- `type`: `论证型论证线`
- `one-line chain`: 失去未来感的人会沉沦，而把自己系到不可替代的责任与目标上，才知道为何继续活下去。
- `status`: `strong`
- `why_accumulation`: 这条线从经验征兆，推进到机制分析，再推进到责任性答案，层次非常清楚，适合检验模型能否保持论证主线。
- `EARLY`
> “每当看到狱友吸烟时，我们就知道他已失去了生活下去的勇气。勇气一旦失去，几乎就不可能再挽回。”
- `MID`
> “看不到未来的人之所以自甘沉沦，是因为他发现自己老在回忆……看不到生活有任何意义、任何目标，因此觉得活着无谓的人是可怜的，这样的人很快就会死掉。”
- `LATE`
> “一旦他意识到自己是不可替代的，那他就会充分意识到自己的责任……他知道自己存在是‘为了什么’，也就知道‘如何’继续活下去。”
- `原文定位`: `lines 27-27`, `lines 359-387`, `lines 403-403`
- `what_it_tests`: 是否能追踪作者如何把“失去勇气”的经验观察上升成关于目标、责任与生存意志的系统论证。
- `distinct_from_neighbors`: 这条强调的是“未来/责任感”的动力结构，不是“苦难本身如何有意义”。
- `risk_notes`: `EARLY` 更像症状性观察；好的回答需要把它和后面的系统解释连起来。

### `huochu_c3_suffering_as_task_and_meaning`

- `candidate_id`: `huochu_c3_suffering_as_task_and_meaning`
- `book / window`: 《活出生命的意义》 / `huochu_shengming_de_yiyi_private_zh__segment_1`
- `type`: `论证型论证线`
- `one-line chain`: 苦难先被提升为生命意义的一部分，继而被个体化为无人能替代的任务，最后被提升为绝境中的生存伦理。
- `status`: `strong`
- `why_accumulation`: 这条线不是简单重复“苦难有意义”，而是从抽象命题推进到个体责任，再推进到集体性的劝勉。
- `EARLY`
> “如果说生命有意义，那么遭受苦难也有意义。苦难、厄运和死亡是生活不可剥离的组成部分。没有苦难和死亡，人的生命就不完整。”
- `MID`
> “如果你发现经受磨难是命中注定的，那你就应当把经受磨难作为自己独特的任务……没有人能够解除你的磨难，替代你的痛苦。”
- `LATE`
> “在任何情况下，人的生命都不会没有意义，而且生命的无限意义就包含着苦难、剥夺和死亡……他们一定不能丧失希望，而应当鼓起勇气，坚持斗争，始终保持尊严，坚守生命的意义。”
- `原文定位`: `lines 335-335`, `lines 393-397`, `lines 419-421`
- `what_it_tests`: 是否能识别作者如何把意义从抽象哲学推进成在极端处境里可操作的伦理立场。
- `distinct_from_neighbors`: 这条关注“如何理解并承担苦难”，不同于 `future/responsibility` 那条对生存动机的分析。
- `risk_notes`: `MID` 与 `LATE` 词面接近，容易被误判为重复；需要回答者指出两者功能不同。

### `huochu_c4_dehumanization_vs_inner_moral_freedom`

- `candidate_id`: `huochu_c4_dehumanization_vs_inner_moral_freedom`
- `book / window`: 《活出生命的意义》 / `huochu_shengming_de_yiyi_private_zh__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 极端环境会把人推向“更不像人”的状态，但最终区分人的不是身份阵营，而是是否保住内在自由与道德品质。
- `status`: `strong`
- `why_accumulation`: 前段强调制度性非人化，中段提出仍取决于内心决定，后段再把“囚犯/看守”二分改写为“高尚/龌龊”二分。
- `EARLY`
> “犯人们觉得自己的生死取决于看守的情绪，这使得他们更不像人。”
- `MID`
> “犯人最终成为什么样的人，仍然取决于他自己内心的决定……即便在集中营，他也能保持自己作为人的尊严。”
- `LATE`
> “世界上有（且只有）两类人——高尚的和龌龊的。任何地方都有这两类人，人类社会的所有团体中也都有这两类人。”
- `原文定位`: `lines 273-273`, `lines 405-405`, `lines 437-437`
- `what_it_tests`: 是否能读出作者对环境决定论的抵抗，以及他如何重新划定真正的道德分界线。
- `distinct_from_neighbors`: 这条不是“未来”也不是“苦难意义”，而是“人性判断的真正标准”。
- `risk_notes`: `LATE` 很像一句名言；如果忘了中段的“内在决定”，容易被读成独立结论句。

## *The Value of Others*

Source window: `value_of_others_private_en__segment_1`  
Source file: `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/segment_sources/value_of_others_private_en__segment_1.txt`

### `value_c1_relationships_as_value_media`

- `candidate_id`: `value_c1_relationships_as_value_media`
- `book / window`: *The Value of Others* / `value_of_others_private_en__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 人与人靠交换价值走向彼此，关系因此成为价值交易的媒介，进而生成 rules, laws, and games 的整套框架。
- `status`: `strong`
- `why_accumulation`: 这是全书理论框架的骨架之一；后面的 “laws” 和 “game” 只有带着前面的 relationship definition 才有意义。
- `EARLY`
> “A relationship is the medium in which value is transacted. Where value is transacted, a relationship exists. Conversely, where no value is transacted, no relationship exists.”
- `MID`
> “In order to effect a transaction, that which is given must be valued similarly to that which is received… relationships must be negotiated – not just at their inception but through their entire duration, as well.”
- `LATE`
> “These relationship rules and laws… collectively give rise to the game of relationships… A game is anything with rules and a goal. And under this definition, human relationships are games.”
- `原文定位`: `lines 17-17`, `lines 23-25`, `lines 29-33`
- `what_it_tests`: 是否能把作者的定义、约束条件与总框架连成一条理论线，而不是只记得“关系是交易”这一句。
- `distinct_from_neighbors`: 这条是总框架，不是“价值如何变成情绪”的内部机制。
- `risk_notes`: 如果回答者只复述“relationships are transactional”，会把这条压得过平，错过后面的 rules/laws/game 层级。

### `value_c2_value_engine_to_emotion`

- `candidate_id`: `value_c2_value_engine_to_emotion`
- `book / window`: *The Value of Others* / `value_of_others_private_en__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 价值不是静态客观量，而是隐蔽计算的产物；这个计算结果不会直接显露，而是被转译成情绪。
- `status`: `strong`
- `why_accumulation`: 这条线构成作者理论的“引擎”。后段的 desire/disgust 只有在前面的 covert valuation engine 下才是系统结论，而不是随口命名。
- `EARLY`
> “Value is neither static nor objective. As we’ll see, it exists solely in the mind of the valuer… this valuation typically occurs beneath the threshold of awareness.”
- `MID`
> “The calculated value coefficient is transformed into an emotion. This emotion contains the personally relevant significance of the value coefficient.”
- `LATE`
> “The emotion into which this value coefficient is transmuted is desire… value and desire are the same thing experienced in different ways.”
- `原文定位`: `lines 21-21`, `lines 81-85`, `lines 119-123`
- `what_it_tests`: 是否能保留作者关于 valuation process 的中间机制，而不是把后面的情绪结论读成普通常识。
- `distinct_from_neighbors`: 这条讲的是“价值如何变成情绪”；`game of games` 那条讲的是目标层级和择偶位置。
- `risk_notes`: 英文术语较密，模型可能会退化成关键词摘抄；好的回答应明确交代 covert process -> coefficient -> emotion 的顺序。

### `value_c3_goal_hierarchy_game_of_games`

- `candidate_id`: `value_c3_goal_hierarchy_game_of_games`
- `book / window`: *The Value of Others* / `value_of_others_private_en__segment_1`
- `type`: `论证型论证线`
- `one-line chain`: 关系价值必须放回 personally relevant goals 与 exemplars 来理解，进入 sexual relationships 后，这套结构被抬到 nested hierarchy 中的 “game of games”。
- `status`: `strong`
- `why_accumulation`: 这条线清楚展示作者如何从一般目标论推进到 sexual relationships 的高位框架，是典型的层级建构。
- `EARLY`
> “To understand why individuals enter into relationships with certain people… it is extremely useful to identify the goal they are attempting to achieve.”
- `MID`
> “We also seem to possess exemplars… associated with specific types of relationship partners… the less important the goal… the lower this individual’s selection threshold will be.”
- `LATE`
> “The game of mating and dating ranks very highly in most people’s nested hierarchy of games… In many respects, it is the game of games: the game that makes all other games possible.”
- `原文定位`: `lines 91-95`, `lines 97-101`, `lines 103-107`
- `what_it_tests`: 是否能追踪作者如何一层层把局部择偶判断抬升为更上位的理论框架。
- `distinct_from_neighbors`: 这条测“目标层级”；不是 `relationship as medium` 的底层定义，也不是 `goal conflation` 的后续动态。
- `risk_notes`: 后段很醒目，容易被单独摘出来；如果忘了前面的 goal/exemplar 铺垫，会读得过于口号化。

### `value_c4_goal_conflation_and_emotional_outputs`

- `candidate_id`: `value_c4_goal_conflation_and_emotional_outputs`
- `book / window`: *The Value of Others* / `value_of_others_private_en__segment_1`
- `type`: `论证型论证线`
- `one-line chain`: 关系价值会随着 goals 的排序变化而波动，而当多个目标被压进同一关系时，trade-offs 与冲突就会持续重估价值并输出不同情绪。
- `status`: `strong`
- `why_accumulation`: 这条候选要求模型持续记住前面的 goal hierarchy，才能读懂后面的 conflation、desire、disgust 和 approach-avoidance conflict。
- `EARLY`
> “We can now appreciate why those with whom we enter into sexual relationships can be among the most valuable people in our lives – and why that value can fluctuate so dramatically over the course of a relationship.”
- `MID`
> “We can call this goal conflation, which occurs when a single means… is used to pursue multiple goals… there aren’t any solutions, only trade-offs.”
- `LATE`
> “Our emotional response to the perception of a high-value individual is desire… to a low-value individual is disgust… if both our desire and our disgust are active at the same time… this is called an approach-avoidance conflict.”
- `原文定位`: `lines 109-111`, `lines 113-117`, `lines 129-129`
- `what_it_tests`: 是否能保留“目标混叠 -> 价值波动 -> 情绪输出”的连续逻辑，而不是把高/低价值读成静态标签。
- `distinct_from_neighbors`: 这条主要测关系动态，不是 `valuation algorithm` 的来源问题。
- `risk_notes`: `LATE` 容易被读成单纯定义题；若不带上 `goal conflation`，就会失去真正的 long-span 压力。

### `value_c5_unconscious_valuation_model_failure`

- `candidate_id`: `value_c5_unconscious_valuation_model_failure`
- `book / window`: *The Value of Others* / `value_of_others_private_en__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 人往往不知道自己真正看重什么，因此直接自述并不可靠；更深层的 valuation algorithm 则由文化与家庭样本共同训练出来。
- `status`: `strong`
- `why_accumulation`: 这条线让前面的 valuation theory 向更深的解释层推进，说明为什么“我想要什么”的主观报告会持续失灵。
- `EARLY`
> “People will be unaware of precisely what they value and the extent to which they value those things… it is generally useless to directly ask people what they want in a sexual partner.”
- `MID`
> “We can call the evolving outcome of this interdependent system the valuation algorithm when it is concerned with determining the instrumentality of perceived objects to our self-relevant goals.”
- `LATE`
> “Children principally train their valuation algorithm on the data collected by observing the relationships of their primary caregivers… We could call this the law of small numbers as applied to relationships.”
- `原文定位`: `lines 139-145`, `lines 149-149`, `lines 151-155`
- `what_it_tests`: 是否能在长段理论叙述中保留作者关于“模型失灵”与“训练数据偏差”的解释路径。
- `distinct_from_neighbors`: 这条是元层解释，讲理论为何会在人身上产生偏差；不同于前面的 goals / emotions / trade-offs。
- `risk_notes`: 术语密度高，且与常见心理学表述相似；回答者容易抽象泛化而丢掉 `law of small numbers` 这一具体闭合。

## 《芒格之道》

Source window: `mangge_zhi_dao_private_zh__segment_1`  
Source file: `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/segment_sources/mangge_zhi_dao_private_zh__segment_1.txt`

### `mangge_c1_circle_of_competence_and_safety_margin`

- `candidate_id`: `mangge_c1_circle_of_competence_and_safety_margin`
- `book / window`: 《芒格之道》 / `mangge_zhi_dao_private_zh__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 不预测未来并不等于无原则收缩，而是逐步收束为知道自己边界、留足安全边际、甚至拒绝赚最后一个铜板的老派哲学。
- `status`: `strong`
- `why_accumulation`: 这条跨年份重复不是简单复述，而是从“不知道未来”推进到“能力圈”与“安全边际”的稳定哲学。
- `EARLY`
> “我们根本没有预知未来的能力……大多数时候，我们什么都不做。即使是出手的时候，我们也是如履薄冰，对可能承担的风险感到不安。”
- `MID`
> “我们很清楚自己的不足，很清楚有很多事我们做不到，所以我们谨小慎微地留在我们的‘能力圈’之中……我们只在已知的圆圈内活动。”
- `LATE`
> “我们老派而保守，总是留有充足的安全边际……不赚最后一个铜板。例如，我们会规定：参照高信用等级的标准收益率，如果某品种的收益率高出0.125%，则禁止投资。”
- `原文定位`: `lines 121-127`, `lines 1121-1129`, `lines 1185-1199 & 1245-1249`
- `what_it_tests`: 是否能从多场讲话中抽取同一哲学骨架，并识别它如何被不同表达持续加固。
- `distinct_from_neighbors`: 这条是“风险与边界”主线，不是“利益扭曲建议”那条。
- `risk_notes`: 因为跨年重复较多，回答者可能只摘一句“能力圈”；好的回答应指出不预测、能力边界、安全边际之间的递进关系。

### `mangge_c2_self_interest_distorts_advice`

- `candidate_id`: `mangge_c2_self_interest_distorts_advice`
- `book / window`: 《芒格之道》 / `mangge_zhi_dao_private_zh__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 给人建议时，人总会从自身利益出发；这条洞见从鱼钩故事、销售制度一路延伸到商学院与大公司的共谋盲点。
- `status`: `strong`
- `why_accumulation`: 这条线非常适合当前窗口，因为它不是同义复述，而是同一底层哲学在不同制度场景中的一次次再显影。
- `EARLY`
> “我问他：‘你这鱼钩五颜六色的，鱼是不是更容易上钩啊？’他回答道：‘查理，我这鱼钩又不是卖给鱼的。’……自己用不用理发，别问理发师。”
- `MID`
> “制定一套奖励丰厚的销售制度，招聘一批高智商的员工……这些销售员能不拼吗？肯定都挖空了心思，把储贷机构忽悠得团团转。”
- `LATE`
> “商学院需要大公司的捐赠，商学院的毕业生需要到大公司就业……它们已经嫁给了大公司，有些事情，只能睁一只眼闭一只眼。”
- `原文定位`: `lines 193-203`, `lines 1121-1125`, `lines 1153-1155`
- `what_it_tests`: 是否能跨多个实例记住“激励扭曲认知”这一底层原则，而不是把这些例子当成彼此孤立的吐槽。
- `distinct_from_neighbors`: 这条测的是判断何时被利益结构污染；不是“如何配置资本”的主线。
- `risk_notes`: 例子太生动，回答者容易停在故事层；需要明确抽出共同哲学。

### `mangge_c3_real_manager_without_glamour_premium`

- `candidate_id`: `mangge_c3_real_manager_without_glamour_premium`
- `book / window`: 《芒格之道》 / `mangge_zhi_dao_private_zh__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 不为管理层光环支付溢价，但真正好的管理者仍然稀缺；这套判断最后落实为 owner-like、诚实正直而非快进快出的经营哲学。
- `status`: `secondary`
- `why_accumulation`: 这条线更 subtle，不是同一句话重复，而是管理者观从“不给溢价”走到“什么样的人值得长期共担”。
- `EARLY`
> “沃伦对优秀的管理层青睐有加，但是在他的投资过程中，他从来没有因为管理层很优秀，而支付高于资产的价格……也许有人愿意为管理层支付溢价，而且还做得很成功，但那不是我们的风格。”
- `MID`
> “在巴菲特眼中，优秀的管理者是这样的：你把他从火车上扔下去……他在这个小镇上诚实本分地经营，用不了多长时间，又发家致富了。”
- `LATE`
> “一家子公司，管理层诚实正直，在行业中表现中规中矩，但盈利能力不让人满意……但是，我们不会把它卖掉。我们不会像打牌一样，抓一张、扔一张。”
- `原文定位`: `lines 83-91`, `lines 97-97`, `lines 1289-1289`
- `what_it_tests`: 是否能把“不给管理层光环溢价”和“真正的 owner-like 管理哲学”区分开来并重新接上。
- `distinct_from_neighbors`: 这条不是机会稀缺时的守势，而是“如何评价人与如何与人长期共担”。
- `risk_notes`: 由于中后段不如其他候选那样显眼，这条更依赖回答者能读出管理哲学的一致性。

### `mangge_c4_waiting_and_not_doing_deals_for_show`

- `candidate_id`: `mangge_c4_waiting_and_not_doing_deals_for_show`
- `book / window`: 《芒格之道》 / `mangge_zhi_dao_private_zh__segment_1`
- `type`: `论证型论证线`
- `one-line chain`: 真正好的机会稀缺时，宁可守势与等待，也不为了做交易而做交易；后段则把这种耐心对照到管理层的并购冲动上。
- `status`: `strong`
- `why_accumulation`: 这条适合当前窗口，因为它依赖跨年份记住“等待”与“收购热”的反差，而不是单次讲话里的一个判断。
- `EARLY`
> “真正做收购是好事多磨，要熬过辛苦的等待，经历反复的波折……现在股市里好的投资机会没了，收购也很难做，两条路都不好走了，我们只能采取守势。”
- `MID`
> “手握大量现金，我们向威廉·奥斯勒爵士学习。脚踏实地，做好眼前的事，让公司顺其自然地长期发展。”
- `LATE`
> “现在没‘桶里射鱼’那么简单了……现在人们热衷于收购。刷厕所、搬砖头，这些脏活累活没人干。收购多潇洒，大家都抢着干。”
- `原文定位`: `lines 71-81`, `lines 539-541`, `lines 1269-1279`
- `what_it_tests`: 是否能保留“机会稀缺时如何不做错事”的长线经营哲学。
- `distinct_from_neighbors`: 这条强调等待与克制；`能力圈` 那条则更偏认知边界和风险控制。
- `risk_notes`: 这条的 later closure 更偏对照与讽刺，不是特别硬的概念定义；回答者需要主动点出“等”与“并购冲动”的张力。

## 《纳瓦尔宝典》

Source window: `nawaer_baodian_private_zh__segment_1`  
Source file: `reading-companion-backend/state/eval_local_datasets/user_level_benchmarks/attentional_v2_user_level_selective_v1/segment_sources/nawaer_baodian_private_zh__segment_1.txt`

### `nawaer_c1_wealth_money_status_and_sleep_income`

- `candidate_id`: `nawaer_c1_wealth_money_status_and_sleep_income`
- `book / window`: 《纳瓦尔宝典》 / `nawaer_baodian_private_zh__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 财富必须先和金钱、地位区分开来，随后再与“出租时间”区分，最后收束成“睡觉时也能赚钱的资产”。
- `status`: `strong`
- `why_accumulation`: 这是整章最基础的定义线之一。后段的财富定义只有带着前面的三分法和“不出租时间”才能真正闭合。
- `EARLY`
> “追求财富，而不是金钱或地位。财富是指在你睡觉时仍能为你赚钱的资产。金钱是我们转换时间和财富的方式。地位是你在社会等级体系中所处的位置。”
- `MID`
> “依靠出租时间是不可能致富的。你必须拥有股权（企业的部分所有权），才能实现财务自由。”
- `LATE`
> “你真正想要的其实是财富。财富就是在你睡觉时也可以帮你赚钱的资产……所以，我对财富的定义是在睡觉时也能带来收入的企业和资产。”
- `原文定位`: `lines 17-29`, `lines 29-29`, `lines 177-187`
- `what_it_tests`: 是否能把作者的财富定义从口号保留成一个逐步收紧的概念框架。
- `distinct_from_neighbors`: 这条是财富定义本身，不是“怎么致富”的操作性链条。
- `risk_notes`: 因为开头就给出核心定义，回答者可能跳过中段“不出租时间”的必要补充。

### `nawaer_c2_getting_rich_is_know_what_not_just_work_hard`

- `candidate_id`: `nawaer_c2_getting_rich_is_know_what_not_just_work_hard`
- `book / window`: 《纳瓦尔宝典》 / `nawaer_baodian_private_zh__segment_1`
- `type`: `论证型论证线`
- `one-line chain`: 致富不取决于蛮力劳动，而取决于知道做什么、和谁一起做、什么时候做；这条判断最终被压缩到“运用专长，发挥杠杆效应”。
- `status`: `strong`
- `why_accumulation`: 这不是一句励志话，而是后文专长、杠杆与判断力的总入口，适合检验模型能否从总论一路带到后面的操作框架。
- `EARLY`
> “赚钱跟工作的努力程度没什么必然联系……要想获得财富，你就必须知道做什么、和谁一起做、什么时候做。与埋头苦干相比，更重要的是理解和思考。”
- `MID`
> “工作时要拼尽全力，毫无保留。不过，共事的人和工作的内容比努力程度更重要。”
- `LATE`
> “运用专长，发挥杠杆效应，最终你会得到自己应得的。”
- `原文定位`: `lines 5-7`, `lines 149-149`, `lines 161-161`
- `what_it_tests`: 是否能把作者的“努力”降格处理，与“判断/专长/杠杆”重新排序。
- `distinct_from_neighbors`: 这条是总纲；`specific knowledge` 和 `productize yourself` 是它的细化分支。
- `risk_notes`: 这条容易被读成一般创业鸡汤，回答者必须带出后文的结构性支撑。

### `nawaer_c3_social_gap_plus_scale`

- `candidate_id`: `nawaer_c3_social_gap_plus_scale`
- `book / window`: 《纳瓦尔宝典》 / `nawaer_baodian_private_zh__segment_1`
- `type`: `论证型论证线`
- `one-line chain`: 为社会提供“有需求但无从获得”的东西只是起点，真正的致富还要把供给推向规模化，而技术则放大了这一路径。
- `status`: `strong`
- `why_accumulation`: 这条线很适合做系统搭建题，因为它从一句总纲，一路推进到技术、全球供给和规模化生产。
- `EARLY`
> “获得财富的一个途径，就是为社会提供其有需求但无从获得的东西，并实现规模化。”
- `MID`
> “代码和媒体是不需要许可就能使用的杠杆……你可以创建软件和媒体，让它们在你睡觉时为你工作。”
- `LATE`
> “要想在社会上赚到钱，就要为社会提供其有需求但无从获得的东西……下一步是思考如何规模化，因为只提供一个产品或一项服务是远远不够的。”
- `原文定位`: `lines 33-33`, `lines 109-117`, `lines 189-197`
- `what_it_tests`: 是否能追踪作者如何把“社会缺口”变成“规模化供给”的致富路径。
- `distinct_from_neighbors`: 这条重点是“社会需求 + 规模化”，不是财富定义本身。
- `risk_notes`: `MID` 用 permissionless leverage 承接规模化，回答者若只背“代码和媒体”而不接到 `social gap`，会丢掉链条。

### `nawaer_c4_specific_knowledge_and_unique_value`

- `candidate_id`: `nawaer_c4_specific_knowledge_and_unique_value`
- `book / window`: 《纳瓦尔宝典》 / `nawaer_baodian_private_zh__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 专长不是可标准化培训的技能，而是无法替代、无法外包和自动化的能力，最后要回到“你能自然提供什么独特价值”。
- `status`: `strong`
- `why_accumulation`: 这条线把 `specific knowledge` 从口号推进成边界清楚的概念，并在后段回收到“独特价值”。
- `EARLY`
> “专长指的是无法通过培训获得的知识。如果社会可以培训你，那么社会也可以培训他人来取代你。”
- `MID`
> “专长往往具有高度的技术性或创造性，不能被外包或自动化。”
- `LATE`
> “‘把自己产品化’要花几十年——并不是要花几十年执行，而是要把大部分时间用于思考：我能提供什么独特的价值？”
- `原文定位`: `lines 65-65`, `lines 81-81`, `lines 175-175`
- `what_it_tests`: 是否能真正保留作者对 `specific knowledge` 的限定，而不是把它误读成一般技能积累。
- `distinct_from_neighbors`: 这条讲的是“专长是什么”；`productize yourself` 那条讲的是如何把它系统整合出去。
- `risk_notes`: `LATE` 是总结性发问，不是定义句；好的回答要带回前面的不可替代性。

### `nawaer_c5_productize_yourself_as_system_summary`

- `candidate_id`: `nawaer_c5_productize_yourself_as_system_summary`
- `book / window`: 《纳瓦尔宝典》 / `nawaer_baodian_private_zh__segment_1`
- `type`: `概念/区分澄清线`
- `one-line chain`: 专长、责任感与杠杆并不是三条散线，而是最后被“把自己产品化”这一总括重新压缩成一套系统。
- `status`: `strong`
- `why_accumulation`: 这条候选最能体现作者如何把前面的点状原则收回为一个高层总纲，适合做概念系统回收题。
- `EARLY`
> “用专长、责任感和杠杆效应武装自己……培养责任感，勇于以个人名义承担商业风险。社会将根据责任大小、股权多少和杠杆效应回报你。”
- `MID`
> “这句话有两个重点，一个是‘自己’，一个是‘产品化’。‘自己’具有独特性，‘产品化’是发挥杠杆效应；‘自己’具有责任感，‘产品化’需要专长。”
- `LATE`
> “如果想变得富有，你就要弄清楚你能为社会提供哪些其有需求但无从获得的东西，而提供这些东西对你来说又是轻松自然的事情……下一步是思考如何规模化。”
- `原文定位`: `lines 61-97`, `lines 167-175`, `lines 191-197`
- `what_it_tests`: 是否能看出作者如何把多条原则重新压缩成一个更上位的记忆锚点。
- `distinct_from_neighbors`: 这条不是单讲财富定义，也不是单讲专长，而是讲系统整合。
- `risk_notes`: 因为 `MID` 很像 slogan，回答者若不主动带回前面的专长/责任感/杠杆，容易把这条读扁。

## Consistency Check

- All candidates were discovered from the current window raw text, not from note cases or excerpt cases.
- All five books are included.
- Total candidate count in this memo: `21`.
- `悉达多` and `活出生命的意义` include all currently accepted candidate directions from the earlier review round.
- `The Value of Others`, `芒格之道`, and `纳瓦尔宝典` are expanded beyond the earlier coarse shortlist and now include multi-case system-building lines.
- No candidate in this memo requires extending the window start earlier than the current body-start boundary.
- No long-span dataset file, manifest, or eval run artifact was modified in this task.
