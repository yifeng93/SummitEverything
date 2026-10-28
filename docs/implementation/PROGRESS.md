# 实施进展账本

本页维护当前产品与验收状态。此前索引集成状态见[本轮前快照](PROGRESS-HISTORY-2026-10-29-PRE-MCP.md)；更早阶段的边界沿历史快照与[报告索引](../quality/reports/README.md)追溯。当前执行入口见[最新交接](../handoff/LATEST-IMPLEMENTATION.md)。

## 当前 MCP 接入（2026-10-29）

- 当前开发目录为 `/Users/hanwenbo/ai/SummitEverything`，分支 `codex/mcp-workbench-prototype-20261023`。本轮源码提交 `b8699a35d3323942bef2d4355d6eb7d818bd3ddd` 的 Git tree 与独立 QA 候选 `33e73f96a4271be7b2a2260439799f004acfd65a` 完全一致；未推送、未执行里程碑合并。
- 标准 MCP stdio 接口已实现 14 个工具：工作库状态、主线/项目目录、当前已确认页列表、BM25 检索与版本读取、文本导入/原件读取/收件箱、待审稿创建/编辑/列表/详情，以及受既有授权门保护的日历读取。连接复用唯一 FastAPI，不启动第二套业务服务；接入步骤见 [MCP-v1](../contracts/MCP-v1.md)。
- MCP 会话固定工作库身份，切库后拒绝读写；参数拒绝未知审批字段。文本和草稿均不自动成为正式知识，正式内容仍由应用用户确认。搜索与读取复用共享资格门，旧版本、未确认材料和待审稿不得成为当前知识；搜索不调用模型。
- **源码与合成本机协议门 PASS**：首轮固定候选全量 Python 757 项通过；发现的 CLI 配置提示 P2 已修复。最终候选独立复验：MCP 专项 18 项、CLI 配置黑盒 18/18、补充鉴权 4/4、Ruff/mypy/lock 均通过。最终候选未直接重跑独立全量，不将首轮结果迁移到新 SHA。
- **当前工作区组合回归 PASS**：保留原有未提交修改后，全量离线 Python 769 项通过，Ruff、格式、mypy 与锁检查通过；实际开发启动器已验证读取 owner-only token 文件、正确 token 通过认证、错误 token 返回 401、退出关闭本次服务。组合输入 patch/哈希与原始日志见 [Sol 收口报告](../quality/reports/2026-10-29-MCP-SOL.md)。
- 原有 UI、原生壳、检索性能与热更新改动继续保留；另一任务的界面修改不纳入 MCP 源码提交或界面验收结论。源码 commit 不包含这些既有 dirty 改动；本轮完整组合回归不等于 UI/安装包全产品验收。

## 未测与后续门

实际 Codex/WorkBuddy 客户端配置与用户实连 **NOT_RUN**；已提供配置示例但未修改客户端配置。真实材料、模型/embedding/rerank、飞书真实读取和任务写回、Keychain 生命周期、已安装 App、DMG/公证、五日、双机、发布和 WCAG AA 仍按独立门执行。本轮不使用现有开发库数据、不重建现有索引、不修改或重启已安装应用。运行时模型元数据 **UNVERIFIED**。
