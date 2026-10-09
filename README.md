# SummitEverything

个人工作知识应用：把工作材料整理成经本人确认、可复用、可迁移的 Markdown 资产，并在同一应用中完成检索问答与日常工作。

首版交付 macOS DMG，内部使用 WebUI；每台电脑独立运行，本地目录或 OneDrive 保存工作库。核心栈为 Python / FastAPI、React / TypeScript、SQLite 和薄 macOS 壳。

## 当前状态

2026-10-09：M1.1–M1.5 的本地知识闭环已完成 DEV 实现，并补修来源处理状态、重复整理、冲突结果表达与本地服务生命周期。当前候选版本正在独立验收；验收通过前不宣告 M1 收口。飞书、真实模型质量验收与可安装 DMG 尚未实现。详见 [进展账本](docs/implementation/PROGRESS.md) 和 [最新交接](docs/handoff/LATEST-IMPLEMENTATION.md)。

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

### 本地 WebUI 开发预览（M1）

先安装前端依赖，然后在仓库根目录启动 FastAPI 与 Vite。脚本自动生成仅供本次进程使用的本机会话 token 和运行身份，并在退出时只关闭自己启动的服务：

~~~sh
cd web && npm ci
cd ..
uv run python scripts/run_dev.py
~~~

打开 `http://127.0.0.1:5173`，新建工作库时选一个空的隔离目录。隔离并发复演可通过 `SUMMIT_API_PORT`、`SUMMIT_WEB_PORT` 和 `SUMMIT_PROFILE_ROOT` 指定独立端口与 profile。也可运行薄 macOS 壳：

~~~sh
cd native && swift run
~~~

WebUI 支持主线 / 项目 / 页面浏览、随手记、文字导入、显式 FakeLLM 整理、多稿审核、单页确认与更新、增量索引及本地 SSE 问答。查询仅使用经确认且仍为当前版本的页面。TXT / Markdown 导入要求 UTF-8，最大 20 MB。首次索引与变更计划均需用户在界面确认。

开发壳在 readiness 后显示同一 WebUI，工作库可通过原生目录选择器指定。此壳依赖本机 `uv`、Node.js 和已安装的前端依赖；它不是可安装 DMG。真实模型、飞书和真实业务材料仍未接入。

## 与原项目的关系

SummitWorkbench（SWB）提供写入、审批、飞书和 macOS 生命周期的参考；SummitKnowledge（SK）提供分块、检索、重排、引用和会话的参考。SummitEverything 是独立的新实现，运行时不依赖两套旧应用。

详见 [复用地图与源码基线](docs/architecture/REUSE-MAP.md)。旧源码、旧应用和真实 _vault 保留；新项目采用自己的契约和验收规则。
