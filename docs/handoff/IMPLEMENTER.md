# 实现者手册

你的职责：按已确认规格实现完整 v1 的当前阶段，自测并提交可复验版本。用户已授权通用编码，不需要再问是否开始。

## 开始

读根 AGENTS、README、PROGRESS、产品规格、架构 / 复用地图、两个契约和全 v1 计划。当前 M1 与 M2 阶段 A Fake-only 已收口；Stage B真实adapter已实现，当前固定源码及独立离线QA状态见LATEST-IMPLEMENTATION，不能回退到骨架或重复执行历史提示词。真实账号、OS与发布门仍单独待验。样板未批准不阻塞模拟开发。

先检查工作区和已有进度，保存他人修改，不 reset / checkout 覆盖。使用 codex/ 分支小步提交；从整理后的 main 创建短期功能分支，旧 Foundation / QA 归档引用只作历史参考。当前执行状态以 `docs/implementation/PROGRESS.md` 和 `docs/handoff/LATEST-IMPLEMENTATION.md` 为准。已有候选闭环进入修复或独立验收时，先继续该固定候选，不得因文档旧模板回退到 M1.1 或启动未来阶段。

本项目不是 SWB / SK 补丁，不能去旧目录改代码。需要复用时在固定来源版本查证并移植到新 package，记录依据。

## 实现

- 按任务测试真实行为；业务、文件和索引逻辑不整体 mock，外部网络可 Fake。
- 统一调用 content.py；完整 schema、StorageArea 路径判定、缓存 version 参数是接入者责任。
- provider / file / configuration 边界严格解析；AI 只提出稿件和 action，用户确认才写。
- API 类型生成前端类型；UI 表达业务，不把内部 operation / hash 当审核正文。
- 使用临时模拟库；初始化旧真实库、全量嵌入和真实 task 不是开发自测。
- 缺凭据继续 Fake 实现，列未测外部门。遇到真实产品语义歧义再给用户选项，普通库选择 / 分文件 / 测试修复自行完成。

## 阶段完成

1. 对照任务和 ACCEPTANCE 列覆盖项，不用单元数量宣称完整完成。
2. 跑适当检查及真实 UI / 打包验证，保存退出码与复演材料。
3. 提交实现、测试、规格同步，取得完整代码 SHA。
4. 更新 PROGRESS 与 LATEST-IMPLEMENTATION，列真实 / 模拟、未测、缺陷和启动命令，再提交交接文档。
5. 将固定 SHA、复演范围、自测退出码、真实 / 模拟边界和未测项交给 Sol。默认由 Sol 自动创建全新的独立 QA handoff；用户无需复制提示词。QA 在隔离 checkout 验收，不得修改源码或已有 tracked tests。

进入后续阶段按计划验收门推进。等待独立 QA 时可以做不跨门的准备，不写“已验收”；收到缺陷按最小复现修复，给新 SHA。最多两轮自动修复，每轮须有新 SHA 和全新 QA；仍未通过时交 Sol 停止并请用户决定。

## 必须持续维护

真实启动命令、新增依赖 lock、API / 工作库语义变更、移植记录、进展、构建身份和具体已知问题。不能保留一个已过时框架文件让下一 agent 猜当前行为。
