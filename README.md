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

## 文档导航

- 当前产品和验收状态：[PROGRESS](docs/implementation/PROGRESS.md)；本轮固定候选交接：[LATEST-IMPLEMENTATION](docs/handoff/LATEST-IMPLEMENTATION.md)。
- 实现/验收入口：[AGENTS.md](AGENTS.md)、[实现手册](docs/handoff/IMPLEMENTER.md)、[测试手册](docs/handoff/TESTER.md)、[验收矩阵](docs/quality/ACCEPTANCE.md)。
- 规格与实现边界：[产品规格](docs/product/PRODUCT-SPEC.md)、[前端指南](docs/product/FRONTEND-GUIDE.md)、[逐页规格](docs/product/FRONTEND-PAGE-SPECS.md)、[架构](docs/architecture/ARCHITECTURE.md)、[工作库契约](docs/contracts/WORKSPACE-v1.md)、[API 契约](docs/contracts/API-v1.md)。
- [全部文档索引](docs/README.md)、[开发与 QA 报告索引](docs/quality/reports/README.md)、[完整 v1 实施与验收计划](docs/superpowers/plans/2026-10-09-summit-everything-v1.md)。

SummitEverything 是独立实现；SummitWorkbench 与 SummitKnowledge 仅作只读参考，运行时不依赖旧应用。
