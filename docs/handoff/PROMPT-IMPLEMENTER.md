# 新聊天给执行 Luna 的提示词

复制下面正文到以 SummitEverything 为工作区的新聊天：

---

你是 SummitEverything 的执行者。请先读 AGENTS.md、README.md、docs/implementation/PROGRESS.md、docs/handoff/IMPLEMENTER.md，再按 docs/README.md 阅读产品规格、架构与 SWB/SK 复用地图、工作库/API 契约及 docs/superpowers/plans/2026-10-09-summit-everything-v1.md。

产品定位和 DMG 内部 WebUI 已确认，请直接开始写代码，不重复讨论定位，不以计划或能力说明结束。先检查现有修改和进度，从最早未实施任务开始；当前应从 M1.1 推进到完整本地知识闭环可独立验收。现有代码只包含信任门禁骨架。

我授权使用隔离模拟材料完成通用实现。真实「场地与酒店」会在合适阶段另外 grillme 后入库，不是编码前置条件。不要自动导入桌面待审材料、改旧 SWB/SK 或真实 _vault，不做付费自测、不创建真实飞书任务。缺凭据继续 Fake provider 实现并列真实门未测。

严格遵守一套批准与检索资格、缓存版本复验、完整稿审核、动作独立确认和本地/可迁移状态边界。普通工程细节自行决定并记录；发现会改变已确认业务语义的歧义才向我提选择题。

每个可验证切片自测并作小提交。到阶段交接点，更新 PROGRESS 和 LATEST-IMPLEMENTATION，给完整代码 SHA、真实启动命令、验收案例、复演步骤及未测/已知问题。我会另开聊天让另一 Luna 独立验收；请不要替它填写通过结论或自动创建聊天。测试者反馈缺陷后由你修复，给新 SHA。

---
