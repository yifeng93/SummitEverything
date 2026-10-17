# 文档索引

新执行或验收任务从 [README](../README.md)、[进展账本](implementation/PROGRESS.md) 和[最新交接](handoff/LATEST-IMPLEMENTATION.md)确认当前状态。历史状态只适用于报告标明的固定 SHA，不作为当前任务入口。

## 当前交接与验收

- [实现者手册](handoff/IMPLEMENTER.md)与[实现者提示词](handoff/PROMPT-IMPLEMENTER.md)
- [独立验收手册](handoff/TESTER.md)与[验收提示词](handoff/PROMPT-TESTER.md)
- [验收矩阵](quality/ACCEPTANCE.md)、[报告索引](quality/reports/README.md)、[报告模板](quality/REPORT-TEMPLATE.md)
- [本次清理与恢复记录](handoff/2026-10-13-PRE-NEXT-STAGE-CLEANUP.md)

## 产品规格与工程契约

- [产品规格](product/PRODUCT-SPEC.md)：用户目标、完整 v1 和非目标。
- [前端指南](product/FRONTEND-GUIDE.md)、[逐页规格](product/FRONTEND-PAGE-SPECS.md)与[今日/审批改造计划](superpowers/plans/2026-10-16-frontend-usability.md)：三轮选择确认的新界面基线。
- [架构](architecture/ARCHITECTURE.md)、[工作库契约](contracts/WORKSPACE-v1.md)、[API 契约](contracts/API-v1.md)
- [全 v1 实施计划](superpowers/plans/2026-10-09-summit-everything-v1.md)：阶段任务、测试与退出门。
- [Provider 协议矩阵](architecture/PROVIDER-PROTOCOL-MATRIX.md)与[旧项目复用地图](architecture/REUSE-MAP.md)
- [架构与产品决策记录](decisions/)

## 历史记录

- [M3 离线验收收尾](handoff/history/2026-10-13-m3-offline-closeout.md)：固定 SHA、范围和仍未测门。
- [旧 DSH-C19 提示词](handoff/history/DSH-C19-2026-10-12.md)：仅供追溯；兼容入口见[归档说明](handoff/DSH-C19.md)。
- [进展账本历史副本](implementation/PROGRESS-HISTORY-2026-10-13.md)、[交接历史副本](handoff/LATEST-IMPLEMENTATION-HISTORY-2026-10-13.md)、[验收矩阵历史副本](quality/ACCEPTANCE-HISTORY-2026-10-13.md)、[报告索引历史副本](quality/reports/HISTORY-INDEX-2026-10-13.md)
- [其他阶段记录](implementation/)、[历史交接与补丁](handoff/history/)、[历史计划](superpowers/plans/)

## 规格与决策权威

用户最新明确指令 → 已确认的[产品规格](product/PRODUCT-SPEC.md) → ADR / 契约 → 实施计划。历史 DEV / QA 报告保留原样；其 PASS / FAIL 只适用于注明的固定 SHA。架构实现可在不改变产品语义和验收门时调整；批准指纹、语料资格、状态共享边界及动作确认含义不可静默改变。
