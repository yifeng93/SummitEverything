# 实施进展账本

初始记录：2026-10-09。实现者维护，验收者另写报告；状态不从测试数量推断。

| 阶段 | 实施状态 | 独立验收 | 备注 |
|---|---|---|---|
| Foundation | 本轮完成文档与核心门禁骨架，自检证据见报告 | 尚未独立验收 | 没有应用服务 / UI / DMG |
| M1 本地闭环 | 进行中 | 未开始 | M1.1–M1.4 DEV 切片已提交，继续推进 M1.5 |
| M2 飞书 / 日常 | 未开始 | 未开始 | 真实权限与写动作门独立记录 |
| M3 完整问答 / 连续状态 | 未开始 | 未开始 | 角色 / 记忆 / 历史各机本地 |
| M4 单机交付 / 五日试用 | 未开始 | 未开始 | 真实业务与模型质量不能由 mock 代替 |
| M5 双机 | 未开始 | 未开始 | 先通过单机门 |

## 当前下一步

执行 Luna 从 M1.1 开始直接实现通用代码，用隔离模拟库。按完整 v1 计划推进到 M1 可复验交接点，更新 [执行交接](../handoff/LATEST-IMPLEMENTATION.md)，给独立测试 Luna 验收。

## 独立数据 / 外部门

- G-SAMPLE：场地与酒店真实内容未整组确认；允许通用编码，初始化真实样板前需专门 grillme。
- G-MODELS：未调用真实模型；需用户明确选择材料、调用范围和凭据配置。
- G-FEISHU：未核实真实新权限，未创建真实测试任务；外部写须指定测试动作。
- G-SINGLE：单机全流程与五个实际工作日尚未开始。
- G-DUAL：双机正常往返与接续尚未开始。

## M1 切片记录

| 任务 | 实施状态 | 实现代码 SHA | 检查 / 覆盖 | 材料边界 | 备注 |
|---|---|---|---|---|---|
| M1.1 DTO、库打开、组织管理 | DEV完成待验收 | `005e7a4`（本地提交） | `uv run pytest -q`：32 passed；ruff、mypy、`uv lock --check`、`uv build` 均退出 0。契约测试覆盖 C02 的临时库创建 / legacy 拒绝 / 初始化重试 / 组织改名 / 页面归属校验部分。 | 合成线、项目和页面；没有真实业务内容或外部调用 | 仅 M1.1；不代表 M1 DEV 门或 C02 全场景通过。TestClient 有 Starlette 关于 httpx 的弃用提示，待依赖更新评估。 |
| M1.2 可靠本地写入与用户确认 | DEV完成待验收 | `ce650ba0516b36753aeb94b246cdc1714a8901e8` | 当前完整自动套件 `uv run pytest -q`：50 passed；ruff、mypy、`uv lock --check`、`uv build` 均退出 0。集成覆盖批准写入、过期基准拒绝、幂等、原子多文件恢复、移动与相对链接维护。 | 全部为临时隔离库与合成事实；无真实 provider / 飞书动作 | 未填写独立验收结果。模拟检查不等于 M1 DEV 门完成。 |
| M1.3 来源、随手记录和多稿整理 | DEV完成待验收 | `4a1fc293bbc6520cb6819cbc1902f53841cc6fea` | `uv run pytest -q`：59 passed；ruff、mypy、`uv lock --check`、`uv build` 均退出 0。覆盖原字节保存、TXT/MD 与 UTF-8 限制、零模型读取、显式 FakeLLM 多稿、malformed/timeout 边界、冲突分项处理、逐稿确认、仅候选 action、本机 API 流程。 | 临时隔离库、合成文本与 FakeLLM；无真实模型或飞书调用 | 作业运行中断后保留 running 状态；同步 Fake provider 调用不能运行时取消。Starlette TestClient/httpx 弃用提示仍存在。没有 UI。 |
| M1.4 增量索引、问答与引用门禁 | DEV完成待验收 | `0aae5a2718a792b7e9b35afaf401987ed1d9ccaa` | `uv run pytest -q`：64 passed；ruff、mypy、`uv lock --check`、`uv build` 均退出 0。覆盖 source/draft 排除、中文多候选检索、外部编辑及重新批准的旧 chunk 拒绝、邻页复验、分块嵌入复用、过期计划拒绝、model-change 失败保留旧索引。 | SQLite 位于隔离 profile；Fake embedding / rerank / answer，无网络模型或费用 | M1.4 service 尚未接到 WebUI/API；历史 purpose 沿共享门禁实现但需进一步外部复验。Starlette 弃用提示仍存在。 |

下一步：M1.5 将检索、知识浏览、随手记、待整理和稿件审核接入 WebUI，形成 M1 本地闭环。M1.1–M1.4 等待独立 QA，M1 独立 QA 尚未运行。

## 更新格式

每个任务记录：任务 ID、实施状态、代码 SHA、检查命令与结果、相关验收案例 ID、真实 / 模拟范围、已知缺陷、下一步。

allowed 状态为 未开始 / 进行中 / DEV完成待验收 / 验收未通过 / QA通过 / 真实门待完成 / 完成。不能将“已交接”“mock 全绿”填写为 QA通过或实际交付完成。
