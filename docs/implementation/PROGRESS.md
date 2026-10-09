# 实施进展账本

初始记录：2026-10-09。实现者维护，验收者另写报告；状态不从测试数量推断。

## 更新记录

- 2026-10-09：整理并纳入两份针对旧实现 SHA `f364c0122a1a74580009bf9342e6e864df6d975d` 的独立验收原报告；同步记录报告结论差异、模拟材料边界和新实现 SHA `7b41ca272b14c38a7b6ebf0e9766766749ccf001` 待独立复验状态。没有据开发自测宣告 M1 通过。
- 2026-10-09：本轮修复 C05 来源 / 整理作业 / 稿件状态与重复生成门禁、补充 C07 最终正文结果、修复本地开发服务身份及退出清理，更新 API / 工作库契约、执行 / 测试交接和当前阶段计划。候选代码固定在 `73ec81a06f2557c006f98ff88fa81b08d14ef315`；DEV 命令与浏览器 / 原生复演证据见 [自测记录](../quality/reports/2026-10-09-M1-close-DEV.md)。独立 QA 尚未完成，M1 未宣告收口。

| 阶段 | 实施状态 | 独立验收 | 备注 |
|---|---|---|---|
| Foundation | 本轮完成文档与核心门禁骨架，自检证据见报告 | 尚未独立验收 | 没有应用服务 / UI / DMG |
| M1 本地闭环 | DEV完成待验收 | 当前候选 `73ec81a06f2557c006f98ff88fa81b08d14ef315` 尚未独立验收 | 两份旧 SHA 报告仍保留；C05 / C07 和 runner 生命周期有新补修，M1 收口须等独立 QA、缺陷复验及合并后验证 |
| M2 飞书 / 日常 | 未开始 | 未开始 | 真实权限与写动作门独立记录 |
| M3 完整问答 / 连续状态 | 未开始 | 未开始 | 角色 / 记忆 / 历史各机本地 |
| M4 单机交付 / 五日试用 | 未开始 | 未开始 | 真实业务与模型质量不能由 mock 代替 |
| M5 双机 | 未开始 | 未开始 | 先通过单机门 |

## 当前下一步

下一步由独立 QA agent 在仓库外 checkout `73ec81a06f2557c006f98ff88fa81b08d14ef315`，对照 [执行交接](../handoff/LATEST-IMPLEMENTATION.md) 与验收手册复核 Foundation 和 M1.1–M1.5 Must 场景。当前记录不标记独立验收通过；旧 SHA 的两份报告均保留，新 SHA 不继承旧报告结论。

## 独立验收报告（旧 SHA）

以下两份报告均固定在 `f364c0122a1a74580009bf9342e6e864df6d975d`，报告范围和观察不同，结论存在差异。它们是各自验收者的原始记录，不互相覆盖，也不能作为 `7b41ca272b14c38a7b6ebf0e9766766749ccf001` 的验收结果：

- [2026-10-09-M1-f364c01.md](../quality/reports/2026-10-09-M1-f364c01.md)：C08/C10 FAIL（P1）；C03/C06/C13/C14 未整体验证；自动测试 67 passed。
- [2026-10-09-M1.1-M1.5-f364c01.md](../quality/reports/2026-10-09-M1.1-M1.5-f364c01.md)：C05/C06/C13 FAIL（P1）；C03/C07/C11/C12/C14 未整体验证；C08/C10 PASS；自动测试 67 passed。

两份报告均只用合成材料和 Fake providers，未运行真实模型、飞书写入、真实样板、五日试用或双机验收。修复代码加入了对应整改和自测证据；仍须对新固定 SHA 独立复验，不能据此标记 QA 通过。

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
| M1.5 WebUI 与本地运行壳 | DEV完成待验收 | `f364c0122a1a74580009bf9342e6e864df6d975d` | `uv run pytest -q`：67 passed；ruff / format、mypy、`uv lock --check`、`uv build`、OpenAPI 类型生成、`npm test`（2 passed）、`npm run typecheck`、`npm run build`、Oxlint、`swift build` 均退出 0。浏览器复演覆盖新建工作库至外部编辑后旧索引无引用。解锁后临时 debug `.app` 渲染 WebUI，系统目录选择器选中既有合成 replay 库并把路径回填；未创建工作库。`cd native && swift run` 启动 API / Vite，health 返回 ready。 | 临时合成工作库；FakeLLM / Fake embedding / rerank / answer；无真实材料、模型或飞书调用 | 原生交互测试时 QA worktree 占用端口，目录选择 UI 使用了已有服务。`swift run` 的 Ctrl+C 留下 API / Vite 子进程，手动 SIGTERM 本轮 `run_dev.py` 后确认监听端口关闭；原生窗口正常 Quit / 关闭时的进程清理仍待验证。Oxlint 有 3 条 effect 提示；pytest 有 Starlette/httpx 弃用提示；DMG 未做。 |
| M1 QA 修复与补充证据 | DEV完成待验收 | `7b41ca272b14c38a7b6ebf0e9766766749ccf001` | `uv run pytest -q`：72 passed；ruff check / format、mypy、`uv lock --check`、`uv build`、`npm test`（4 passed）、typecheck、build、lint、`swift build` 通过。浏览器复演 C06/C08/C10；自动测试补充 C03 归档 / 非空删除、C13 当前与历史效力、C14 顺序 / 唯一终态 / 取消。Documents 访问通过后，临时 debug `.app` 启动 API / Vite，通过原生 UI `⌘Q` 退出；随后确认端口 8793 / 5173 无监听且本轮服务子进程退出。 | 只用 `/tmp/summit-m1-fix-replay-nwyhoS` 隔离合成内容及 Fake providers；没有读取、导入、审批或提交真实业务材料；没有真实模型或飞书调用 | 新 SHA 独立复验未开始。C06 按用户选择修订为“用户先选定一个项目，一份多主题来源在该项目下生成多稿”，不做自动跨项目分流。开发 `⌘Q` 清理已验证；`swift run` 终端 Ctrl+C 留存子进程的问题仍存在。M3 历史会话 / 旧引用 UI、M4 打包 / DMG 及真实门仍未测。保留一个 Starlette/httpx 弃用提示和三个既有 Oxlint effect 提示。 |

### 本轮 M1 收口候选（固定代码 SHA `73ec81a06f2557c006f98ff88fa81b08d14ef315`）

| 任务 | 实施状态 | 实现代码 SHA | 检查 / 覆盖 | 材料边界 | 备注 |
|---|---|---|---|---|---|
| C05 来源状态与重复整理修复 | DEV完成待验收 | `4939abc`，包含于候选 `73ec81a06f2557c006f98ff88fa81b08d14ef315` | `uv run pytest -q`：77 passed；来源状态覆盖 pending / processing / reviewing / completed / failed / cancelled、部分确认、全部确认、失败显式重试与完成后显式重新处理；真实 UI 显示多稿审核中与完成状态。 | FakeLLM 与隔离工作库 / profile | 新操作 ID 不能绕过在途或待审状态；失败或完成后重处理需要明确选项。待独立 QA。 |
| C07 冲突最终正文 | DEV完成待验收 | `4939abc`，包含于候选 `73ec81a06f2557c006f98ff88fa81b08d14ef315` | 测试覆盖选择 / 明确未决写入正式正文；未决明确为非确定事实；前端显示预期最终处理结果。 | FakeLLM 与隔离工作库 | 需 QA 独立复核案例期望。 |
| 本地运行壳身份 / 清理 | DEV完成待验收 | `73ec81a` | runner 测试 2 passed：独立端口与 profile、API 端口冲突不误杀其他服务、SIGTERM 后监听关闭；本机 UI 真实复演最后窗口关闭、正常 Quit 与 swift run Ctrl+C 后均无本轮服务残留。 | 单独端口 8823/5183、8825/5185；.local 临时 profile / 工作库 | 不代表 DMG、干净机器安装或发布验收。 |
| 全量 M1 DEV 检查 | DEV完成待验收 | `73ec81a06f2557c006f98ff88fa81b08d14ef315` | 后端 77 项、前端 6 项、ruff / format、mypy、lock、uv build、OpenAPI 类型生成、typecheck、lint、前端 build、swift build 全部退出 0；浏览器覆盖 C06/C08/C10 端到端流程。细节见 [最新交接](../handoff/LATEST-IMPLEMENTATION.md)。 | 全部模拟与 Fake | 保留 1 条 Starlette/httpx 弃用提示和 3 条既有 frontend effect lint 警告。 |

真实业务样板、真实模型、飞书、五日实际工作及双机仍由各自授权门控制；执行者不填写 QA 通过。

## 更新格式

每个任务记录：任务 ID、实施状态、代码 SHA、检查命令与结果、相关验收案例 ID、真实 / 模拟范围、已知缺陷、下一步。

allowed 状态为 未开始 / 进行中 / DEV完成待验收 / 验收未通过 / QA通过 / 真实门待完成 / 完成。不能将“已交接”“mock 全绿”填写为 QA通过或实际交付完成。
