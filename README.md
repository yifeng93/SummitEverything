# SummitEverything

SummitEverything 是个人工作知识整理与检索应用。它把工作记录整理成经用户确认的 Markdown 页面，并在本机提供检索、问答与引用。首版以独立运行的 macOS 应用交付：薄 Swift 壳、React/TypeScript WebUI 与 FastAPI 服务。

## 能力

- 按主线、项目和页面管理知识；导入、随手记、整理草稿、逐项审批和版本更新。
- 对已确认的当前页面建立本地索引，支持带引用的问答。
- 提供本地历史、角色和记忆，并集成飞书材料读取入口；任务操作与知识审批分开确认。
- 将工作库 Markdown 与业务状态保存在用户选择的位置；历史、索引、凭据和诊断数据保留在本机。

模型输出只是建议。正式页面由用户确认；任务和项目进度也须各自确认。完整范围与非目标见[产品规格](docs/product/PRODUCT-SPEC.md)。

## 本地开发

需要 Python 3.12+、uv、Node.js/npm，以及运行 macOS 壳测试时的 Swift 工具链。默认开发与测试使用合成数据和 Fake provider；真实服务调用需按各自授权门单独确认。

```sh
uv sync --locked --group dev
cd web && npm ci
cd ..
uv run python scripts/run_dev.py
```

打开 <http://127.0.0.1:5173>，并为工作库选择新的隔离目录。脚本启动本机 FastAPI 和 Vite 服务；退出时只关闭本次启动的服务。详细隔离选项、Internal App/DMG 构建和验收边界见[实现手册](docs/handoff/IMPLEMENTER.md)与[测试手册](docs/handoff/TESTER.md)。

提供标准 MCP stdio 入口供 Codex / WorkBuddy 连接已运行的本机 API：`uv run --locked --project "$PWD" python -m summit_everything.mcp_server`。先准备当前服务会话的 token 文件（权限 0600），再按[本机 MCP 契约](docs/contracts/MCP-v1.md)配置 `SUMMIT_MCP_TOKEN_FILE`；MCP 不会启动第二个后端。

## 常用检查

```sh
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv lock --check
uv build
swift test --package-path native
npm --prefix web test -- --run
npm --prefix web run typecheck
npm --prefix web run lint
npm --prefix web run build
```

首次运行后端集成测试前安装 Web 依赖。Playwright、Fake API 集成与内部应用构建命令和安全边界见实现/测试手册。自动检查通过不等于阶段验收通过。

本地索引由 SQLite 指针与 profile 内嵌入式 LanceDB 组成，`index.sqlite3` 对应独立的 `index.lancedb` 数据目录。查询和索引构建通过 profile 文件锁保留代；旧代会在应用退出后通过下面的维护命令清理。旧 SQLite `vector_json` 索引不会自动迁移或用于查询，状态会要求重建；需从已确认 Markdown 预览并显式建立新索引。旧 SQLite 行会原样保留，新 profile 不再创建 `chunks/vector_json` 表。查询在重建前不会因此触发 embedding。

清理 LanceDB 旧代时先退出应用，再将 `<profile>/index.sqlite3` 替换为对应本机 profile 中的真实文件路径。此命令不会清理旧 SQLite `chunks/vector_json` 残留：

```sh
uv run python scripts/prune_local_index.py --index-db "/actual/profile/path/index.sqlite3" --app-stopped
```

## 文档导航

- 当前产品和验收状态：[PROGRESS](docs/implementation/PROGRESS.md)；本轮固定候选交接：[LATEST-IMPLEMENTATION](docs/handoff/LATEST-IMPLEMENTATION.md)。
- 实现/验收入口：[AGENTS.md](AGENTS.md)、[实现手册](docs/handoff/IMPLEMENTER.md)、[测试手册](docs/handoff/TESTER.md)、[验收矩阵](docs/quality/ACCEPTANCE.md)。
- 规格与实现边界：[产品规格](docs/product/PRODUCT-SPEC.md)、[前端指南](docs/product/FRONTEND-GUIDE.md)、[逐页规格](docs/product/FRONTEND-PAGE-SPECS.md)、[架构](docs/architecture/ARCHITECTURE.md)、[工作库契约](docs/contracts/WORKSPACE-v1.md)、[API 契约](docs/contracts/API-v1.md)。
- Agent 接入：[MCP v1 契约](docs/contracts/MCP-v1.md)、[ADR 0028](docs/decisions/0028-local-mcp-agent-tools.md)。
- [全部文档索引](docs/README.md)、[开发与 QA 报告索引](docs/quality/reports/README.md)、[完整 v1 实施与验收计划](docs/superpowers/plans/2026-10-09-summit-everything-v1.md)。

SummitEverything 是独立实现；SummitWorkbench 与 SummitKnowledge 仅作只读参考，运行时不依赖旧应用。
