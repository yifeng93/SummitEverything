# C19 DSH 交接：Sol 审查与独立门

2026-10-13。**独立 QA 进行中，C19 新候选尚未通过门。** DSH 自测和三轮子代理预验仅为开发证据，不替代此次全新 QA。原 f79 / 262 的 P1 FAIL 保留。

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

## 待独立 QA 后更新

原34项、tracked19项、新结构 holdout、完整 guarded / Web / 静态 / 构建与隔离 OpenAPI、实际 API/SSE / UI / history及信任变化，均由新 QA 在 be 固定目标复验。结束后 Sol读取原始退出码 / SHA / diff / manifest / 服务状态，逐项作 PASS / FAIL / BLOCKED / NOT_RUN判断；非回归只能说明没有新引入，不能自动豁免C19原要求。

此文尚不签发 C19 / 包2 / M3 PASS。正式 M3验收与合并仍需用户批准；真实 provider / 飞书 / 凭据 / Keychain / 材料、native / DMG、五日 / 双机 / 发布均 NOT_RUN，runtime UNVERIFIED、smoke未消费。产品修复只在 QA结束固定提交后串行交 Developer，最多两轮自动返工并各由全新 QA 复验；旧报告与被测源码不移动、不改写。
