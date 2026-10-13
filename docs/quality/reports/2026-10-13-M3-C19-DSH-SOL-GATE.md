# C19 DSH 交接：Sol 审查与独立门

2026-10-13 当前：统一返工1/2的固定产品源码为 **`0a1b8dc94a5d8f797161c38430dccfcb211a9e07`**。Sol 已审查3文件实现/测试 diff、实际退出码和14项 DEV manifest（全部匹配，清单 SHA-256 `fbfd9fde042b7c85566395cf9a825b3e44cb1c77a62bc8debcd76d9976412f98`）；DEV 文档 HEAD `fdfa2533fdb998e39b6471bf59d431b0264833e0` 与受测产品树一致，checkout clean。DEV 后端491 / Web56、85个不同C19测试ID（107执行含副本）、API/SSE完整/部分/零证据与历史重开自测通过。**全新独立 QA 正在独立工作树 `m3-c19-dsh-repair-1-qa/SummitEverything` 验收该固定 SHA；QA / Sol 本轮结论待定，不能把DEV通过替代QA。** 下列 be4 初验 FAIL 与契约记录保留，包2 / M3 正式门未通过，main未合并。

2026-10-13 初验历史。**DSH 候选独立 QA / Sol FAIL：主题剥词 P1、上限原因 P2。** 原设备用例已关闭，但复合主题中的“信息”仍被全局删除；本轮新的默认上限对照也失败。DSH 自测和三轮子代理预验不替代此次全新 QA。原 f79 / 262 的 P1 FAIL 保留。进入本次固定候选初验后的自动统一返工 1/2，不重置或改写旧周期历史。

## 固定版本及 Sol 已核对事项

- 起点冻结标签 `handoff/c19-dsh-2026-10-12` 仍指向 `b3d0dff587c94ee295dfe5379bd67916c98184ec`；main 仍为 `5fd91c78930c80b2365957197b8a605757694a91`。
- DSH 固定产品源码 `be4e72f80127b9c14e0e69a21fdd6f2dabb1ddac`；最终交接 HEAD `04a504f7e2716366fa9335da099b967554db256c` 相对 be 的产品 / tests / scripts / 依赖与配置树 diff 为 0。
- DSH checkout clean。相对 b3，产品只改 planner.py / query.py 并新增19项测试：共456增 / 28删。Sol 未重复执行开发方完整自测，由全新 QA 负责固定候选的实际验收。
- [DSH 开发报告](2026-10-12-M3-PACKAGE-2-C19-UNIFIED-REPAIR-3-DEV.md)及 [64项证据](evidence/2026-10-12-m3-package-2-c19-unified-repair-3-dsh-be4e72f/SHA256SUMS)已实际读取及核对；64项全部匹配，清单 SHA-256 为 `535c55f68bd8388b6fcde651b69db7667b26935731a5b57890f53f110984d0b0`。b3 已有的1403个 evidence 文件逐字节保持。
- 新独立 QA 工作树 `/Users/yifengstudio/.codex/worktrees/m3-c19-dsh-independent-qa/SummitEverything` 固定 be。Sol 审查记录位于另一工作树 `/Users/yifengstudio/.codex/worktrees/m3-c19-dsh-sol-gate/SummitEverything`、分支 `codex/c19-dsh-sol-gate`，起点04。不在 main、冻结 M3 或 DSH 基线工作树写源码。

## D1：按已存在的证据契约判断

产品规格规定页面单一主项目；该规则限制知识组织和主归属，不能自行扩展成“页内只允许出现该项目事实”。产品支持对象档案及跨项目引用，专项计划第25 / 29行允许项目 / 页名 / aliases提供主体线索与元数据归属，但维度必须由支持正文验证。

DSH 的 D1 fixture 是主项目玄石展览、页名及 alias 为“枫湾活动预算”、正式正文“预算上限为九万元”。仅因目录项目不同，不能直接推定该已确认页必不属于枫湾事实；也不能仅因标题出现对象名就豁免局部正文范围。需要独立分开验证匿名正文元数据绑定、明确另一对象正文、主题-only标题、同名实体歧义及完整 / 部分 / 零证据。

DSH 关于既有“青榆”测试的论据须更正：`tests/integration/test_qualified_retrieval.py` 的 fixture 正文实际为“青榆的访客登记须由前台核验姓名并记录来访时间。”，同时有 alias 青榆。它不是“正文与项目名都不含青榆”的 alias-only 用例，不能用其现状证明任何新绑定政策；不修改该历史测试或降低期望。本次先按契约核证，无证据不提请改变规格；真正需要新增元数据优先级等产品规则时才交用户决定。

## S12 / D3：范围不足的原因必须真实

专项计划 S12允许公平保留覆盖或准确报告截断造成不足，不要求实现新的排序策略。但 be 的 `truncated_by_limit and missing_pairs` 分支对所有未覆盖 pair 统一换成“引用条数上限”，没有区分库内本来无依据和已有依据被截断。

Sol 已将以下有界对照交全新 QA，并等待黑盒证据，不把静态怀疑冒充已验 FAIL：A 有多段相关正文触发 limit，B 所问范围完全无正文；A/B 本来完备但只实际传一部分；高limit无截断；资格失效的尾候选；dense前20丢覆盖。逐项核对真实来源 / actual provider passages与missing原因；provider empty missing 不可抹掉真实缺失。

## 固定候选实际门判断

Sol 已读取 [独立 QA 报告](2026-10-13-M3-PACKAGE-2-C19-DSH-QA-be4e72f.md)、原始 commands / exit / failure日志和 final-state，并核对 [71项manifest](evidence/2026-10-13-m3-package-2-c19-dsh-qa-be4e72f/SHA256SUMS)全数匹配：清单 SHA-256 `930fcecee7e4a003d272965eeab1ac7f6a62f26bc997a568864a411889d52607`。QA-only初始提交 `4c3464b834c53c0982a75348469d7a8680c18716`，原作者报告措辞更正提交 `b365e79cde324332d87f1997be6169934d261574`；未改产品或evidence，测试期间源be不变，产品diff0、checkout clean、端口18873 / 15179无监听。

| 门 | Sol 判断 |
|---|---|
| C19 主题范围 | FAIL P1：白萤会展“年度访客信息登记”完整正文三模式均漏引用；缺“信息”的近似正文在事实/比较被误引。6项5 FAIL / 1 PASS，不能逐词追加例外 |
| 引用上限与资料存在性 | FAIL P2：默认limit5，云岬6份预算 / 汀屿无排期，三模式把真缺失替换成cap；limit20对照正确 |
| D1 元数据 / 明确正文边界 | 本次有限对照PASS，未证实需改变契约；青榆论据按上文更正，不修改旧测试 |
| 历史与tracked回归 | PASS，53不同用例；实际执行75含22重复，未双计 |
| 完整检查 | PASS，guarded469 / Web56及静态、类型、lock、build；隔离OpenAPI生成与tracked无diff。首次api:types同字节写回方式已在QA报告如实说明，不将它冒充隔离验证 |
| 实际合成UI / history / restart / stale引用 | PASS，仅报告实际观察流程 |
| 专门HTTP/API/UI complete / partial / zero组合及两项新缺陷端到端 | NOT_RUN，本轮新反例为服务harness；新候选复验必须补齐 |
| C19 / 包2及正式M3 | 未通过，无合并或发布 |

非回归只能说明没有新引入，不能自动豁免C19原要求。真实门和工具未测项仍按下文保留。

## 统一返工 1/2 的具体实现契约

Developer Luna 在 `codex/c19-dsh-sol-gate` 连续负责 planner.py / query.py、相关新回归及DEV交接。QA已停止，不同时运行实现修改和新QA。main、M3冻结标签/目录、DSH交接目录不写；不改旧QA报告、evidence、资格基准或规格。

1. 先复制本轮两份failed harness到自己的 `.local/dev` 复跑RED，保留实际退出码；把行为正反控提升为tracked回归，不删或弱化现有19 / 34项。
2. 根因是全局删除集合仍作用于主体候选、family qualifier、topic phrase及alias tail。审计`_TOPIC_FILLER` 的4次调用及其定义（共5处引用）和全局“的”替换，统一改成位置明确的请求外壳剥离；主题内部的“信息 / 资料 / 工作”等内容词以及对象名不得因命中常用词就消失。不得以删“信息”一个备选项收口。计划句末的“工作方案”必须在明确计划外壳位置处理，而内部“访客工作证”保持；同一主题在fact / comparison / plan正反控一致。保持陌生主题、registered/unregistered名字、礼貌 / 泛化方案、局部pairs与共享维度原正控。
3. 对未覆盖pairs区分：当前资格与范围内确无支持、已有支持被dense候选预算截断、已有支持被引用limit截断。覆盖来自真实支持正文及统一资格检查，不靠页面数量 / 分数 / 单一break标志。真缺资料独立列明，截断只解释被实际排除的支持范围；混合原因可并列，纯截断不得称已知材料缺失。保持资格 / hash复核及provider实收范围，不新增排序系统、不暗增公共limit或90KB预算。
4. 对信息 / 资料词的完整与近似正文、计划请求尾壳、相似名字正反控，对limit1 / 默认5 / 高limit、同时真缺失、纯截断、candidate前20造成不足做有限结构矩阵。不要无限扩展语言词汇；所有原有数据/权限及M3包1/3边界保持。
5. 在自己工作树安装依赖并跑适用完整guarded / Web / 静态 / lock / build和生成稳定性，实际API/SSE完整 / partial / zero / 混合原因及history流程，写DEV报告与raw exit/hash。固定新源码SHA后停止写入，交全新QA集中复验；Sol判门，最多两轮自动返工。此次为1/2；若失败按新发现统一修复2/2而非逐小提交QA。

此文尚不签发 C19 / 包2 / M3 PASS。正式 M3验收与合并仍需用户批准；真实 provider / 飞书 / 凭据 / Keychain / 材料、native / DMG、五日 / 双机 / 发布均 NOT_RUN，runtime UNVERIFIED、smoke未消费。产品修复只在 QA结束固定提交后串行交 Developer，最多两轮自动返工并各由全新 QA 复验；旧报告与被测源码不移动、不改写。
