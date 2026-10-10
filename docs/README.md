# 文档索引

这些文件足以让新的执行 / 验收聊天接手，不需要读取之前的聊天历史。

## 产品与决议

- [产品规格](product/PRODUCT-SPEC.md)：已确认的用户目标、完整 v1、非目标及决议来源。
- [产品与交付 ADR](decisions/0001-product-and-delivery.md)：为何统一产品、为何首版 DMG。
- [可信资产 ADR](decisions/0002-trust-and-portability.md)：为何采用版本批准、普通目录和本地 / 可迁移分界。
- [运行时与复用 ADR](decisions/0003-runtime-and-reuse.md)：技术栈、旧代码复用方式。
- [开发与验收顺序 ADR](decisions/0004-development-and-acceptance-sequence.md)：模拟开发先行，真实样板后续确认，两个 Luna 分工。

## 工程

- [架构](architecture/ARCHITECTURE.md)：模块责任、目录、数据流和外部服务配置。
- [旧项目复用地图](architecture/REUSE-MAP.md)：SWB / SK 的提交、模块和不继承的规则。
- [工作库契约 v1](contracts/WORKSPACE-v1.md)：元数据、批准、目录、写入、生命周期和辅助状态。
- [API 契约 v1](contracts/API-v1.md)：对象、错误、版本冲突、操作幂等和路由。
- [全 v1 实施计划](superpowers/plans/2026-10-09-summit-everything-v1.md)：各阶段的任务、测试和退出门。

## 两个 Luna 的操作入口

- [实现者手册](handoff/IMPLEMENTER.md)、[可复制执行提示词](handoff/PROMPT-IMPLEMENTER.md)。
- [独立验收手册](handoff/TESTER.md)、[可复制验收提示词](handoff/PROMPT-TESTER.md)。
- [Sol 6.1 进度综合评估提示词](handoff/PROMPT-M2-ASSESSMENT-SOL-6.1.md)：基于 M2 固定代码 SHA 评定现状和下一阶段；用户已准备真实测试资源。
- [验收矩阵](quality/ACCEPTANCE.md)、[报告模板](quality/REPORT-TEMPLATE.md)。
- [进展账本](implementation/PROGRESS.md)：执行者更新；不把开发自测写成独立验收通过。
- [本次框架核验](quality/FOUNDATION-VERIFICATION.md)：仅说明当前基础代码与文档检查。

## 权威与变更

用户最新明确指令 → 产品规格的已确认决议 → ADR / 工作库契约 → API 与实施计划。具体代码必须符合契约；发生不一致先确认原因，不能拿旧代码覆盖用户决议。

架构文档中的默认实现属于工程选择，可以在保持产品语义与验收门的前提下调整，并写清原因。修改批准指纹算法、语料资格、状态共享边界或动作确认含义属于契约变更，不能静默进行。
