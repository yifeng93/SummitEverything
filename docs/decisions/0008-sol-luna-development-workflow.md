# ADR 0008：Sol / Luna 开发与验收工作流

日期：2026-10-11。状态：Accepted。范围：通用离线开发与独立验收；真实服务和业务数据门沿用现行产品规则。

## 背景

用户认可 C03 删除拒绝提示本地化试点，并正式确认长期多智能体协作方式。试点依据是源码 SHA `9c953f095086a95e63edbce2169657dba9e71cd1`、固定 QA 文档提交 `141bd96d15039f1cd29461785fdd91e2ef297476` 与独立报告；QA 记录 37 项定向自动回归和本地 Fake WebUI 浏览器复演通过，Sol 判定首轮通过、修复轮数 0/2。C03 与本协作规范已随 [PR #11](https://github.com/yifeng93/SummitEverything/pull/11) 合入 main（merge `2f08c764e740afa494a0445ec4d73382fdd55f3b`）；postmerge 独立核验见[报告](../quality/reports/2026-10-11-C03-POSTMERGE-2f08c76.md)。该事实不表示本 ADR 的实现已在所有 runtime 配置下验证。

## 决议

默认流程为 Sol 负责需求 / 架构 / 规划 / agent 调度 / 审查 / 最终门；custom Developer GPT-6 Luna（High）实现并自测，提交固定源码 SHA 和完整交接；全新 custom QA GPT-6 Luna（High）在独立 checkout 验收该 SHA 并形成证据。Sol 自动完成消息往返，用户不需手工复制提示词。修改按 serial mutation 执行：QA 不检查移动中的实现。

QA 不修改产品源码或已有 tracked tests。仅可在独立 checkout 的 `.local/qa` 或仓库许可的 evidence 位置写临时黑盒 harness、报告和脱敏证据。报告 / 证据可在固定验收结束后单独提交，并明确标记受测 SHA。

QA 首次失败后最多两轮自动修复，每轮都要求 Developer 新 SHA 和 fresh QA。两轮后仍未通过则停止并交用户决定；不删除测试、不降低验收门。Sol 根据实际退出码、日志、SHA、diff 与 QA 证据判定 PASS / FAIL / BLOCKED / NOT_RUN。未暴露的 runtime 配置记 UNVERIFIED，不能由 TOML 推断。过去用户观察到 Luna High smoke 只作为用户观察记录，不是本轮 runtime 证明。

低风险提交和合并仅在仓库规则、分支保护、实际测试和必要审批均允许时自动进行。重要里程碑合并、真实操作、不可逆操作及验收例外须先获用户明确批准。无授权不删除 branch / worktree。Stage C 真实服务、真实材料、凭据、OS Keychain，以及 DMG、五日、双机均继续作为独立门；有限 smoke 计数不因新 profile 或轮次重置。

当前产品状态只维护在真实 HEAD 的 PROGRESS。README 是项目首页；LATEST-IMPLEMENTATION 只记录当前任务的固定候选 SHA、执行交接和 PROGRESS 链接，不复制状态。历史 Stage B 提示词仅供追溯；不得据其重启已完成阶段。原始安装 overlay 保存在 [历史补丁](../handoff/history/2026-10-11-SOL-LUNA-INSTALL-OVERLAY.patch) 以保留来历，不作为当前执行入口。

## 后果

2026-10-11 用户更新：M3 按功能包连续实施及独立集成 QA（会话与历史、完整问答、连续工作与归档）。Developer 可在同一包内连续多个逻辑提交和自测，不逐小接口/提交启动 QA；包完成固定 SHA 后才启动全新 QA。Sol 自动协调最多两轮返工，包间可接续开发，不因普通进展等待人工回复；重要里程碑正式验收与合并仍需用户批准。完整执行与验收映射见 [M3 功能包计划](../superpowers/plans/2026-10-11-m3-integrated-packages.md)。产品和真实门不变。

2026-10-13 用户针对 M4.1 明确授权一个 Developer Luna 连续完成整个内部 macOS App/DMG 集成、自测、实际候选构建和 DEV 交接；同一开发包内不要求每个小提交单独 QA。Developer 固定最终 clean 源码 SHA 并交付场景 / 命令 / 退出码 / 产物摘要后，由全新 QA 在独立 checkout 集中验证固定 SHA。该节奏不授权 M4.2 真实资料或服务、真实凭据 / Keychain、正式安装、签名公证、M4/M5 结论或发布；QA 结论由 Sol 判定，未测项保持 NOT_RUN。

本轮 Developer 交接的产品源码 SHA 为 `b9321d64c5404feadffebc05964793e9402a07aa`；App 与 DMG 从该 clean SHA 构建，当前 DEV 报告和状态文档通过独立 doc-only 提交补齐，不移动 QA 目标。原生 UI 仅覆盖合成工作库保存、重开与退出清理；未测场景逐项留给 QA 或记为 NOT_RUN。详见[固定 SHA 的 M4.1 DEV 报告](../quality/reports/2026-10-13-M41-INTERNAL-APP-DEV.md)。

固定 SHA 和串行修改提供明确的 QA 目标；Sol 保留最终 gate 责任。任务交接可在 agent 间自动往返，避免用户承担提示复制。runtime 可见性不足时必须保留 UNVERIFIED。真实门和产品既有完整 v1 验收要求不因工作流调整而缩小。

## 试点依据与限制

C03 报告链及 QA 证据见 [最新交接](../handoff/LATEST-IMPLEMENTATION.md) 和 [报告索引](../quality/reports/README.md)。Smoke runtime 元数据在本次文档决议中没有独立观测，因此标记 UNVERIFIED。本文记录协作机制，并不宣称该机制已有重复运行统计或整个 v1 阶段通过。
