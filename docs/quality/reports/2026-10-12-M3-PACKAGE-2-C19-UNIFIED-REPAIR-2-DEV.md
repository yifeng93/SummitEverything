# M3 包 2 C19 统一范围 repair 2 Developer 报告

日期：2026-10-12。产品源码固定提交 `f79f613a902758da3173a5b27219fa568a912f5e`，基于 repair 1 QA 报告整合后的 `d3c9de9` 与 Sol 最终指令文档提交 `14af72bb2bd292d254625ee7c781958b6a95207f`。这是 C19 统一候选周期最后自动修复轮 repair 2/2；不重置此前的 repair、extra 或 QA 结论。包 3源码与 QA 报告未改动。

## 行为变化

`RetrievalPlan.required_pairs` 现在由原问题中的对象跨度和它们各自的局部主题直接生成，之后才从 pairs 汇总 `dimensions`。这样“比较白鹭工程预算与赤陶项目的活动证章领取办法”及倒序问法分别形成白鹭预算、赤陶证章领取两项；“比较白鹭工程与赤陶项目的预算和排期”在前面的对象只有连接词时共享最后主题，形成四项；“白鹭的预算和赤陶的排期”则只形成两个明确指定的 pair。同一对象多个主题保留为独立 pair。没有显式对象的问句也先拆开以连接词明确并列的主题；不能拆出的复合短语继续作为单一主题，例如彩色牙刷储存规则不会因“储存”一词退化为所有存储资料。通用、信息不足或不可解析的问句仍走各自原有路径。

检索候选、邻页筛选、citation passage 和产品层 missing 均继续消费相同的 `required_pairs`。每个 pair 仍需由当前合格内容的相应句段支持；不改变 content/hash/approval 资格门，不把页面数量当覆盖，也不调用模型补造缺失主题。无依据时保持零引用和零 provider 调用，partial 只报告没有依据的 pair。API schema、OpenAPI 和 TypeScript 生成物没有变化。

## 验证

旧 repair 1/2 QA 报告与证据均保持原样。依 Sol 指令从 QA harness 建立的本地副本 `.local/dev/c19-unified/r2-holdout/test_c19_fresh_holdout.py` 中，`test_fresh_same_page_multiple_objects_do_not_cross_pair_dimensions` 的历史断言错误要求赤陶显示 missing，然而该 fixture 已含该问题所需的正式证章领取正文，与完整 pair 的验收目的相冲突。本地副本将该断言改为无 missing，并新增正文出现在 citation excerpt / provider passage 的断言；另加移除赤陶证章正文的 partial 对照，继续要求只报告该缺失 pair。版本控制中的旧 QA harness、报告、哈希及 evidence 未改；全新 QA 必须独立复验正确的完整与 partial 语义，不能继承旧错误断言。

最终 README 适用矩阵脚本 `.local/dev/c19-unified/r2-final/run2/run_matrix.py` 各步骤退出码均为 0：`uv sync --locked --group dev`、`npm --prefix web ci`、OpenAPI/TS 生成、旧 QA 的 12 项本地 holdout 副本、修正后的 9 项 repair 1 holdout 副本、qualified retrieval 28 项、guarded pytest **450 passed**、Ruff check/format、mypy 43 个源文件、lock check、`uv build`、Web **56 项 / 12 files**、Web typecheck/lint/build。保留 1 条既有 Starlette/httpx deprecation；lint 保留仓库既有 React effect warnings。第一次矩阵中的 format check 曾 exit 1，原因是三处纯布局未格式化；修正后最终矩阵重新执行并全项 exit 0，初次失败输出保存在 `.local/dev/c19-unified/r2-final/run1/ruff-format.log`，最终日志在 `run2/`。API types 生成无 diff。独立测试 stdout 与退出码逐文件记录在上述日志目录。

## C19 语言边界与交接

解析仅识别已有主题 family、请求句包装和明确并列连接符，不是通用自然语言解析器。主题关系能够从对象间原文片段中辨认时按该 pair 检索；仅连接词之后的主题在前面对象跨度均无局部主题时作为共享后缀。遇到不能可靠解析的关联，不通过全局 dimensions 反推对象笛卡尔积；保留信息性 exact term 或明确不足。独立 QA 应变化实体、主题词、顺序、标点及“的”结构，重点检查句段支持、partial missing、零调用和三个 answer mode，不只复演实现中的同名样例。

此报告是 Developer 自测，不是独立 QA PASS。repair 1/2 QA 的 C19 P1 FAIL 保持有效，最终 automatic repair 尚未由全新 QA 验收；Sol 决定新 SHA 的门状态。M3 正式验收和合并未通过。真实 provider、真实服务/材料/凭据、Keychain、native/DMG、五日、双机及发布门 NOT_RUN；runtime UNVERIFIED；有限 smoke 未消费。
