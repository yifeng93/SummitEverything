# SummitEverything

个人工作知识应用：把工作材料整理成经本人确认、可复用、可迁移的 Markdown 资产，并在同一应用中完成检索问答与日常工作。

首版交付 macOS DMG，内部使用 WebUI；每台电脑独立运行，本地目录或 OneDrive 保存工作库。核心栈为 Python / FastAPI、React / TypeScript、SQLite 和薄 macOS 壳。

## 当前状态

2026-10-09：产品决议、架构契约、全 v1 实施计划、独立验收手册和交接提示词已建立。M1.1 已提供本地 FastAPI 工作库 API；WebUI、飞书连接和可安装 DMG 尚未实现。

通用代码开发可以立即使用隔离模拟材料开始。「场地与酒店」真实样板尚未整组批准，后续在合适阶段专门 grillme 并初始化；它不是编码的前置阻塞。

## 先读哪些文件

- 执行者：[AGENTS.md](AGENTS.md) → [执行手册](docs/handoff/IMPLEMENTER.md) → [全 v1 计划](docs/superpowers/plans/2026-10-09-summit-everything-v1.md)。
- 验收者：[AGENTS.md](AGENTS.md) → [独立验收手册](docs/handoff/TESTER.md) → [验收矩阵](docs/quality/ACCEPTANCE.md)。
- 全部资料：[文档索引](docs/README.md)；当前工作：[进展账本](docs/implementation/PROGRESS.md)。
- 两个新聊天可直接使用：[执行提示词](docs/handoff/PROMPT-IMPLEMENTER.md)、[验收提示词](docs/handoff/PROMPT-TESTER.md)。

## 当前可执行的命令

在本仓库执行；只安装本项目的工具，不同步或改动 SWB / SK 的环境。

~~~sh
uv sync --group dev
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv lock --check
uv build
~~~

当前测试只覆盖已实现的契约切片，不代表 M1 或产品验收通过。DMG / WebUI 构建命令将在相应阶段实现后补充。

### 本地 API 开发预览（M1.1）

设置一个随机的本机会话 token 后启动 FastAPI：

~~~sh
export SUMMIT_SESSION_TOKEN='replace-with-a-random-local-token'
uv run uvicorn summit_everything.api.app:app --host 127.0.0.1 --port 8793
~~~

`GET http://127.0.0.1:8793/api/v1/health` 可检查 readiness；业务 API 需要 `Authorization: Bearer $SUMMIT_SESSION_TOKEN`。当前命令只启动本地后端，还没有 WebUI、启动器或安装包。

## 与原项目的关系

SummitWorkbench（SWB）提供写入、审批、飞书和 macOS 生命周期的参考；SummitKnowledge（SK）提供分块、检索、重排、引用和会话的参考。SummitEverything 是独立的新实现，运行时不依赖两套旧应用。

详见 [复用地图与源码基线](docs/architecture/REUSE-MAP.md)。旧源码、旧应用和真实 _vault 保留；新项目采用自己的契约和验收规则。
