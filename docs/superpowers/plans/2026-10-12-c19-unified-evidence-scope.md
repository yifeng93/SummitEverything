# C19 统一证据范围修复：Sol 研究与 Developer 执行契约

2026-10-12 用户已答复“暂不继续”：C19追加修复未获授权，停止源码修改。保留产品源码 `f79f613a902758da3173a5b27219fa568a912f5e`、最终QA FAIL和全部证据；包1/包3既有离线PASS保持，M3正式门未通过、main未合并。只有用户明确恢复后才继续。

2026-10-12。用户重新授权继续 C19，并明确要求 Sol 先研究、给 Luna 更准确的统一执行，减少重复修复。起点 `b4463c5bb9802adb622dfabe60e469eaf577a6d3`，产品树等同包 3 已验源码 `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`。包 1、包 3离线集成 PASS；包 2 C19 P1 FAIL。此前失败、追加轮次与用户暂停记录不改写。本次为重新获授权的统一修复候选；整包固定 SHA 后首次新 QA，再按现有协议最多两轮自动返工。不是重新批准真实服务或重要里程碑合并。

## Sol 实际研究

读取 planner/query、Fake/Real reranker、answer provider、chunking、API context 和原 QA 反例，执行 guard 下的合成 probe：`.local/sol/c19-research/probe.py`，结果 `.local/sol/c19-research/probe.jsonl`，18 个“6 种问法 × 3 模式”案例，exit 0。只在隔离临时库确认去标识内容；没有真实 provider。

观察：两对象均无资料时 comparison/plan 引用朱雀预算并调用 provider；一个对象有资料、另一个未知时 planner 只保留已知 alias，三个模式都漏报未知对象；两对象都有预算却问牙刷规则时，三个模式都引用预算；正常礼貌预算、明确双对象方案、未指定对象的广义预算仍可回答。probe 使用会返回空 missing 的记录型 provider，证明产品边界不能依赖 FakeLLM 的善意提示。

共同根因：

1. query 的 unresolved_topic 和 explicit_subjects 两处保护仅用于 fact，比较/方案绕过。
2. planner 一旦找到任意 alias 就提前返回，未解析余下并列未知对象；无 alias 分支把“比较”等请求动词当主体。
3. Fake reranker 以中文 bigram 重合打分；Real reranker 的 >0 也只是一种分数。对象名/通用词即可让不相干主题得到正分。排名不能作为对象及维度覆盖证明。
4. related_page_ids 扩展只重验信任门，没有共享问题范围检查。
5. source_count≥2 只说明有两页，不能证明指定对象都存在或指定维度有证据。provider 返回的 missing_information 可以覆盖掉产品层已经知道的缺失。

## 确定采用的边界

在现有 planner/query 内统一三模式的范围计划与证据选取；不新建远端意图识别服务、不加依赖、不使用真实模型、不改产品规格。替换并整合旧平行判断，不叠加针对案例名称的补丁。批准/当前版本资格继续由 content.py 负责，问题相关性是额外独立约束。

内部范围表示应包含：当前或最近可信 user 问题的对象集合、问题维度/主题、是否是广义或未解析范围。可以扩充现有 RetrievalPlan，保持 public API 不增加不必要字段。必须保留集合中的未知对象；从已批准库名、项目/页名、aliases得到提示，但 alias 命中不能删除问题中的另一对象。请求动词/礼貌句、比较/方案前缀不是对象；“行政&后勤”等确有其名的复合对象不能盲目拆开。纯代词只在最近完整 user 主题内接续，新对象/新完整问题形成边界；assistant/角色/记忆不得授权扩大范围。

主题与对象分开：

- 明确对象 + 明确维度：证据必须同时满足对象归属和所问维度。项目/页元数据可确定归属，不能凭归属把该项目所有正文当作该维度依据。
- 明确对象 + 泛化下一步/工作方案：保留这些对象的已确认多材料，不强制匹配“方案”字样；已有预算/排期应可支持建议。
- 未指定对象 + 明确主题：允许跨对象多材料，但每条证据都需支持主题，不得仅因“项目/计划/规则”等通用词重合入选。
- 未解析指代或无法确定约束：明确资料不足/需明确对象或维度，不借上上轮主题或不相干材料填充。不要将所有自由提问视作未解析，正向例必须通过。

保持最小、可解释的本地匹配规则：优先标准库、当前 alias 与问题结构；支持已测常用维度的语义等价表述及完整未知主题，不把通用 bigram >0 或名称重合当维度支持。有限规则的语言覆盖限度应记入报告，真实模型质量仍 NOT_RUN；不能以此为由放弃本修复矩阵。不要制造庞大 NLP 框架或随测试增长的任意词表。

同一范围判定必须用于候选、重排后材料、邻页和最终 citation/provider passages。最终展示的 excerpt 和真正送入 provider 的文本必须包含支持点；不能在全文找到支持却截断掉它，不能 _one_passage_per_page 丢掉同页另一已请求维度。所有最终引用仍执行版本/批准复验及生成后的变更检查。

覆盖计算以请求对象 × 维度为基础，不以页数伪装完整：

- 没有任何范围内依据：citations/source_statements/inferences/advice 为空，明确 missing，answer provider 0 次。
- 有部分依据：仅保留对应对象/维度事实，逐个列缺失；同对象两页不能算另一对象已覆盖，第三对象不能补位。
- 完整依据：保留跨对象/多材料正常比较和方案；对排名前20/limit 的截断不得使一方被多页淹没后仍宣称完整。依据受限于limit时报告未覆盖部分，不暗增公共预算。
- missing 是产品层可验证事实，与 provider missing 作稳定去重合并；provider 即使返回 [] 也不能抹除。provider 的生成主文也不能显示“完整比较已完成”掩盖已知缺口；用业务提示约束最终输出，保持事实/推断/建议区分。所有建议仍未批准、不创建任务、不写知识。

诊断保留 extra 2 的正确边界：无相关对象/维度不是缓存异常；真正范围内的 hash/批准变化、历史专属、页面不可读仍准确报告。无关页失败不得污染本问题诊断。

## 执行顺序及责任

Developer Luna 连续负责 `retrieval/planner.py`、`retrieval/query.py` 和必要的 answer-context/provider 提示适配、相关单元/集成/API测试与持久文档。`integrations/rerank.py` 的模型传输和评分契约不需改；不得靠改 Fake 打分掩盖查询层漏洞。src/domain/content.py 信任门不放宽；Web如确有呈现需要，只作最低范围适配并记录，禁止无关界面改造。包3恢复/归档实现不改。其他代理不同时写实现。

1. 先增加下表的合成反例与正控，真实 QueryService + writer/index/API/SSE + 记录型 answerer，复现当前失败并保留 RED 日志。案例参数化复用 fixture，别复制大批 mock 服务；不能删旧断言。
2. 一次收口 planner对象集合和主题约束、query共享候选/邻页选择与覆盖汇总。先跑局部矩阵；发现同根因关联缺口在本开发包内连续修，不每次小提交触发QA。
3. 保留旧正控及历史回归，跑 guarded 后端全套、Web检查、Ruff/format/mypy/lock/build/OpenAPI生成稳定性。README命令安装前端依赖后再全pytest，日志记实际exit；不消费真实smoke。
4. 固定源码SHA，完整交接/DEV报告/进展入口，停止写入。Sol核对diff、原始matrix；全新独立QA固定SHA验完整包2相关范围和C19 holdout，并回归包1/3关联门。新QA可使用新名称、不同主题、不同句式/换序及极端高分reranker，不只复述DEV测试。

## 必须先覆盖的反例与正控

除专门comparison/plan表达外，范围检查参数化 fact/comparison/plan；查询自然表达保持模式本身合理。新名、新数字只用合成内容。每个负向记录provider调用差值、citations、source_statements、missing和body，不仅匹配一句提示。

| ID | 输入/资料安排 | 必须结果 |
|---|---|---|
| S01 | 原反例：比较风铃工程与霜塔项目的彩色牙刷储存规则；仅有专项储备和朱雀预算等六页 | 三模式零引用/零provider，缺对象/维度，无缓存诊断，无其他预算 |
| S02 | A已知有预算、B未知；A两份预算页和第三对象预算 | 只可引用A，必须明示B缺失；不得两页当两对象、不得第三对象补位 |
| S03 | A/B均有预算，问两者陌生储存规则；已知对象名造成所有分数>0 | 零引用/零provider；名称命中不能取代主题 |
| S04 | A预算已知、A排期缺失，问A预算和排期；另有B排期 | 仅A预算，明确A排期缺失，不引B排期 |
| S05 | 相关主页面关联不相干对象或不相干主题邻页；另有合法同对象同维度邻页 | 不相干邻页拒绝，合法邻页仍可引用且重复资格检查 |
| S06 | 命中元数据A但正文只有其他维度；同页/多chunk含A/B不同维度 | 最终passage/excerpt须有正确支持点；不能用page全文任意命中扩大到不相干段落 |
| S07 | 注入reranker对所有候选返回正高分/错误排名、answerer返回empty missing | S01/S03仍无引用/不调用；部分缺失仍由服务端保留，评分不能突破范围门 |
| S08 | 追问链A→代词→B→代词，及A→未知B→代词；跨模式追问、无topic、完整新问题 | 只继承最近user主题；未知边界不回退A；保留旧多轮正控 |
| S09 | 礼貌请求A预算、同义预算额度；比较A/B预算；A/B只有正文/只有project/title归属两种 | 正常获取匹配依据；别将礼貌词作为对象或精确题名作为唯一形式 |
| S10 | 对A/B制定下一步方案；已有两对象预算/排期且无“方案”字样 | 允许范围内多材料，建议仍待决定；不得默认全部拒答来通过 |
| S11 | 未指定对象的“比较预算和排期”“汇总预算资料” | 保留广义跨材料；缺失说明正确，未规定必须两个对象的问法不被误套二对象门 |
| S12 | 两对象同维度完备，A有大量页导致dense前20/最终limit挤压B，反转对象和资料顺序 | 可保留覆盖公平或报告截断造成不足；不得声称B已有支持却实际没送provider |
| S13 | CURRENT/HISTORY、正文hash变更、生成期间编辑/消失、无关页坏hash | 统一信任门和准确诊断不退化，无关页损坏不误报本问题缓存故障 |
| S14 | API/SSE→会话history重开；角色/记忆命令要求引用所有资料 | SSE唯一终态且history对应真实结果，权限和证据范围不被解除；无知识/任务副作用 |

默认限定chunk预算、90KB上下文、limit契约不变。旧Fake与Real adapter合同/transport测试保留，schema/lock没有无必要变化。验收以行为矩阵为准，不以测试数量或提示词字符串作为通过依据。

## 收口规则

Developer交接列清受测SHA、实现diff、RED/GREEN/全矩阵actualexit、支持语言边界和NOT_RUN，不声称QA通过。新QA独立checkout、只增harness/evidence、不改实现或已有tracked tests。首次新QA失败后最多两轮自动返工，每轮新SHA+全新QA；旧轮次历史完整保留。Sol判断包2及整体M3门，正式验收/合并仍交产品owner批准。包3原PASS需保持源码树及关联回归，不重复开发。

## 额度恢复后：最后自动返工 2/2 的 Sol 指令

repair 1 固定源码 `df1aac288a002e86a24132a9954fbe0b18d41d1f`、QA HEAD `04a0239012068598123966ab31340127a6f8ff76`。原12 holdout全过；新5 PASS/3 FAIL集中为 C19-QA-R1-01，三模式把“白鹭工程预算与赤陶项目的活动证章领取办法”合成 `budget&term:活动证章领取`，两段各自已有支持却拒答，倒序亦错。449/Web56及相关静态检查通过不抵销该P1；新QA报告和23项哈希证据保持。Sol已核原始日志及源码，进入最终自动repair2/2，不因额度中断重置。

根因是执行顺序：`query_dimensions`先看整个问题，随后`query_pairs`只从已经合并的全局dimensions寻找局部匹配；对象、主题与各自关联丢失后无法还原。最后修复应以请求pair作为内部真源，再派生全局维度集合，不能继续向全局合成维度追加例外。

1. 在请求原文上收集全部已识别对象跨度，保留来源类型及未知并列对象；对象位于第一个维度词之后也不能被丢弃。复合名称不盲目切开。不依赖当前alias排序作为请求顺序。
2. 先在对象跨度之间提取局部主题表达，再调用已有family/exact/generic规则。`A预算与B证章领取办法`和倒序得到 `(A,budget)`、`(B,term:证章领取)`；两个陌生主题也各自保留。带“的”、不带“的”、普通连接标点应一致。
3. `A与B的预算和排期`中前一个对象后面只有连接词，没有自己的主题，这才是共享后缀，得到两对象各预算/排期的四pair。`A的预算和B的排期`两个对象各有局部主题，只需两pair。局部信息不全而关系无法确定时明确不足，不能默认给全部对象套全局联合维度。
4. 同一对象请求两个独立主题（例如预算及签到办法）也保留两个独立pair。物品修饰主题（例如彩色牙刷储存规则）仍是一个复合主题，不得拆成“任意存储”而放宽；结合明确连接结构区别并列主题与修饰关系，复用已有归一化，不添加案例名称白名单。
5. `RetrievalPlan.required_pairs`由局部/共享解析直接得到，`dimensions`是这些pair的稳定去重并集。后续candidate/neighbor/引用passage/覆盖missing继续消费同一pairs，不重新把全局维度做笛卡尔积。泛方案、裸陌生主题、短alias、主题title、生成后的资格复核等上一轮通过能力不退化。

最小回归先在旧SHA RED后GREEN：family+exact、exact+exact、同对象两独立主题；对象/主题换序及带/不带“的”；完整资料正常引用、只有一方时partial准确、双方无资料时三mode零provider；同页不同句段不cross-pair；共享A/B预算排期四pair及原牙刷修饰主题负控。复跑原12+repair1新增8个独立harness副本，再全相关/README矩阵。Sol审查解析顺序和pair真源，不重复常规测试；固定新SHA后全新QA完成有限完整验收。若最后QA仍有必须解决的缺陷，按协议停止自动返工并交用户决定，不默默开始第三轮。

## Repair 2/2 Developer 固定候选（2026-10-12）

产品源码 `f79f613a902758da3173a5b27219fa568a912f5e` 已固定；局部pair→dimensions实现、支持/缺失观察、自测和语言边界见[repair 2 DEV 报告](../../quality/reports/2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-2-DEV.md)。对象跨度后逐个解析本地主题；仅在前面对象跨度都只有连接符、最后一个对象存在主题时共享后缀。无对象的明确并列主题同样拆成局部pairs；独立QA应覆盖非QA名称与题目变体。最终矩阵所有适用命令exit 0，guarded pytest 450 passed、Web56/12 files；旧12项本地QA副本12/12、新holdout副本9/9、qualified retrieval28/28。第一次格式检查的纯布局错误保留在 `.local/dev/c19-unified/r2-final/run1/`；修正后完整重跑日志在 `run2/`。

旧QA的 `test_fresh_same_page_multiple_objects_do_not_cross_pair_dimensions` 断言要求已有赤陶证章正文仍报告赤陶 missing，与“完整对象×主题 pair”验收含义矛盾。未改动旧 QA 报告、harness 或证据；仅在 Developer 本地副本纠正该项完整预期并增加 citation/provider passage 命中断言，再补缺少赤陶证章正文的partial反例，见repair2报告。fresh QA 应重新证明这两种情况，不继承本地副本的自测结论。

候选尚未经过 fresh QA。repair 1/2 C19 P1 FAIL仍有效；包 2及整体 M3未通过正式验收或合并。真实 provider/服务/材料/凭据、Keychain、native/DMG、五日/双机/发布仍NOT_RUN，runtime UNVERIFIED。

## 当前结论：最后自动返工结束

最终source `f79f613a902758da3173a5b27219fa568a912f5e` / QA `262f4eaa418d70f983f3b0b260d3635cd2e28c92` 仍有主题词剥除P1，原12+纠正9项通过，新15 PASS/7 FAIL同根因。自动repair2/2已结束，不因额度中断再开始第三轮。证据与具体待批提议见[Sol最终门](../../quality/reports/2026-10-12-M3-C19-UNIFIED-SOL-GATE.md)；源码冻结，正式M3未通过。
