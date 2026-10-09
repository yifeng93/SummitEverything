# SummitEverything

个人工作知识应用：把工作材料整理成经本人确认、可复用、可迁移的 Markdown 资产，并在同一应用中完成检索问答与日常工作。

首版交付 macOS DMG，内部使用 WebUI；每台电脑独立运行，本地目录或 OneDrive 保存工作库。核心栈为 Python / FastAPI、React / TypeScript、SQLite 和薄 macOS 壳。

## 当前状态

2026-10-09：产品决议、架构契约、全 v1 实施计划、独立验收手册和交接提示词已建立。代码只有无 I/O 的内容指纹及检索资格骨架；没有应用服务、界面、飞书连接或可安装 DMG。

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

当前测试只证明基础信任契约，不代表产品验收通过。应用启动、前端和打包命令由 M1 / M4 实现后补到这里，不能用不存在的命令伪装可运行产品。

## 与原项目的关系

SummitWorkbench（SWB）提供写入、审批、飞书和 macOS 生命周期的参考；SummitKnowledge（SK）提供分块、检索、重排、引用和会话的参考。SummitEverything 是独立的新实现，运行时不依赖两套旧应用。

详见 [复用地图与源码基线](docs/architecture/REUSE-MAP.md)。旧源码、旧应用和真实 _vault 保留；新项目采用自己的契约和验收规则。
