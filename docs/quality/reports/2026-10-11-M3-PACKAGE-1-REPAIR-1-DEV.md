# M3 包 1 首轮整改：会话首问与历史引用提示 — Developer 报告

## 身份与固定版本

- 执行角色：Developer Luna；这是首轮 QA 缺陷整改与自测，不是独立 QA 结论。
- repair 轮次：1/2。
- 分支：`codex/m3-integrated-packages`。
- 首轮 QA 固定提交：`c90fe6e2bec5677deb7b069b86fa8971da1d8dcd`，结论 FAIL；原报告和 evidence 保持原样，见 [QA 报告](2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md)。
- 修复源码 commit：`a9078bd327f73f2cde3bab14a8665885d0f57c1c`。包含源码、测试，不含文档；本报告提交后完整 QA 目标为最新交接记录的分支 HEAD，其产品源码必须与此源码 SHA 一致。
- 自测材料：pytest 临时合成工作库，Web fetch stub 模拟严格服务端请求/响应契约；未使用真实业务材料、付费模型或凭据。

## 整改内容

**P1 首次提问 404：** 新会话的第一次 `POST /queries` 不再提交客户端随机生成的 `conversation_id`。服务端成功响应后，WebUI 读取 `X-Conversation-ID` 并保存实际 ID，用它重开历史和发送后续问题。首次响应未提供 ID 时 UI 明确提示从历史核实保存状态，不自动重发或尝试打开一个猜测 ID。已有会话仍提交其真实 ID；不存在或跨 profile 的显式 ID 继续由后端拒绝为 404。

**P2 更新引用提示消失：** 从历史打开 `updated` 引用时，将原引用 hash 传入 `onOpenPage`。App 的页面版本读取因此携带 `expected_content_sha256`；若当前页面已更新，API 返回 version conflict 后，App 读取当前版本并展示应用级提示，AskView 卸载后提示仍可见。

新增测试覆盖两个边界：AskView 测试 mock 会像实际服务端一样拒绝未知 conversation ID，首问省略 ID、响应头返回 ID、续问和 reopen 使用该服务端 ID；App 集成组件测试覆盖从历史打开旧 hash、页面返回 version conflict、读取新正文并验证全局提示仍存在。真实 FastAPI / SQLite 集成回归明确验证无 `conversation_id` 的首问成功、响应头给出真实 ID、可 reopen，且显式未知 ID 仍为 404。它与 UI 侧契约回归结合，防止只在组件 mock 中自洽。

## 实际检查结果

原始 stdout / stderr 和每条命令的退出码保存在开发 worktree ignored 目录 `.local/dev/m3-package-1-repair-1/logs/`。下表 PASS 表示命令实际退出码为 0。

| 命令 | 结果 | 日志 |
|---|---|---|
| `uv sync --locked --group dev` | PASS，exit 0 | `uv-sync.log` / `.exit` |
| `npm ci` | PASS，exit 0；lock 审计显示 0 vulnerabilities | `npm-ci.log` / `npm-ci.exit` |
| `uv run pytest -q tests/integration/test_conversations.py` | PASS，6 passed；1 条既有 Starlette/httpx deprecation；exit 0 | `conversations-focused.log` / `.exit` |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | PASS，395 passed；1 条既有 Starlette/httpx deprecation；exit 0 | `pytest.log` / `pytest.exit` |
| `npm --prefix web test` | PASS，49 tests / 12 files；exit 0 | `web-test.log` / `.exit` |
| `uv run ruff check src tests` | PASS，exit 0 | `ruff.log` / `ruff.exit` |
| `uv run ruff format --check src tests` | PASS，exit 0 | `format.log` / `format.exit` |
| `uv run mypy src` | PASS，38 source files；exit 0 | `mypy.log` / `mypy.exit` |
| `uv lock --check` | PASS，exit 0 | `lock.log` / `lock.exit` |
| `uv build` | PASS，sdist 与 wheel 构建成功；exit 0 | `uv-build.log` / `.exit` |
| `npm --prefix web run api:types` | PASS，OpenAPI 导出与 TypeScript 生成成功；exit 0 | `api-types.log` / `.exit` |
| `npm --prefix web run typecheck` | PASS，exit 0 | `web-typecheck.log` / `.exit` |
| `npm --prefix web run lint` | PASS，exit 0；保留 TodayView / ProjectsView 2 条既有 effect warnings | `web-lint.log` / `.exit` |
| `npm --prefix web run build` | PASS，Vite production build 成功；exit 0 | `web-build.log` / `.exit` |
| `git diff --check` | PASS，exit 0 | 命令终端输出；修复提交前执行 |

Web 包含 2 个新增/更新的闭环回归；前端依赖按仓库 `package-lock.json` 用 `npm ci` 安装。一次试探 `pnpm` 产生的未跟踪 `pnpm-lock.yaml` 已移除，没有更改项目锁文件或依赖。

## 独立 QA 复演要求

在本报告对应的交接文档提交后的固定分支 HEAD 独立 checkout，核实产品源码树 SHA `a9078bd327f73f2cde3bab14a8665885d0f57c1c`。至少复演：

1. 新工作库真实浏览器首问：网络请求体不含 `conversation_id`；SSE 响应含 `X-Conversation-ID`；历史出现新会话；重开后继续提问使用同一服务端 ID。
2. 直接 API 传入不存在及其他 profile 的 ID 均 404；正常无 ID 首问成功并可以按响应头 ID reopen。
3. 打开 history 中 `availability=updated` 的引用：读取 current page 请求包含历史原 hash；目标页面显示版本变化提示，且 AskView 已卸载后提示仍可见；正文不被当作原回答依据。
4. 重跑全包历史/权限/资格、SSE 状态与相关测试；复验取消、断流、重启 partial 和 profile/workspace 隔离不回归。

首轮 QA 未构造 `superseded` / archived 引用的 C13 场景；该覆盖缺口须在完整 M3 后续验收补上。Developer 未运行独立 QA、实际真实浏览器、原生壳或 runtime 元数据检查：分别记 QA 待运行、NOT_RUN、NOT_RUN、UNVERIFIED。未使用真实 provider / 凭据 / 业务资料，也未开始包 2 或合并。

## 状态

Repair 1 自测完成，待全新 QA 对固定源码验收；首轮 QA 的 FAIL 不因本报告改写。Sol 是最终 QA 判定者。包 1 未通过声明，M3 正式验收与重要里程碑合并仍待后续授权门。
