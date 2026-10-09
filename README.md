# SummitEverything

个人工作知识应用：把工作材料整理成经本人确认、可复用、可迁移的 Markdown 资产，并在同一应用中完成检索问答与日常工作。

首版交付 macOS DMG，内部使用 WebUI；每台电脑独立运行，本地目录或 OneDrive 保存工作库。核心栈为 Python / FastAPI、React / TypeScript、SQLite 和薄 macOS 壳。

## 当前状态

2026-10-09：M1 本地知识闭环已在模拟材料与 Fake providers 范围内通过独立验收，并合入 `main`。受测代码为 `f349fe6cb5da86c3fdafff11738e2a55335d8874`；详见 [独立复验报告](docs/quality/reports/2026-10-09-M1-close-retest-f349fe6.md)、[进展账本](docs/implementation/PROGRESS.md) 和 [最新交接](docs/handoff/LATEST-IMPLEMENTATION.md)。M2.1 已实现飞书授权、材料与日历的 Fake 流程，DEV 自测完成后待独立验收；真实飞书读取 / 写入、真实模型质量验收和可安装 DMG 仍未完成，并受各自确认门约束。

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

上面的自动检查是开发者命令；M1 模拟范围另有独立 QA 证据，二者范围和结果见进展账本。它们不代表真实飞书、真实模型质量、DMG、五日试用或双机验收通过。

### 本地 WebUI 开发预览（M1 / M2.1）

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

WebUI 支持主线 / 项目 / 页面浏览与管理、页面移动和链接确认、随手记、文字导入、显式 FakeLLM 整理、多稿审核、单页确认与更新、增量索引及本地 SSE 问答。查询仅使用经确认且仍为当前版本的页面。TXT / Markdown 导入要求 UTF-8，最大 20 MB。首次索引与变更计划均需用户在界面确认。

开发壳在 readiness 后显示同一 WebUI，工作库可通过原生目录选择器指定。此壳依赖本机 `uv`、Node.js 和已安装的前端依赖；它不是可安装 DMG。真实模型、飞书和真实业务材料仍未接入。M2.1 默认仅启用无网络的 FakeFeishu 与进程内凭据存储，不能通过环境配置切换真实 provider。

## 与原项目的关系

SummitWorkbench（SWB）提供写入、审批、飞书和 macOS 生命周期的参考；SummitKnowledge（SK）提供分块、检索、重排、引用和会话的参考。SummitEverything 是独立的新实现，运行时不依赖两套旧应用。

详见 [复用地图与源码基线](docs/architecture/REUSE-MAP.md)。旧源码、旧应用和真实 _vault 保留；新项目采用自己的契约和验收规则。

### M2.1 飞书模拟复演

沿用上述 `uv run python scripts/run_dev.py`，新建空的隔离工作库，在“今日 / 飞书日常”点击“模拟授权飞书”。搜索 / 可见范围筛选只读 metadata；选择材料后“导入所选”保存原件与待整理项，必须另行选择整理。日历须指定开始、结束（不含）和时区；模拟日程位于 2026-10-09。分页、导入部分失败与授权失败不会显示虚假成功。

开发默认 callback 为 `http://127.0.0.1:5173/api/v1/integrations/feishu/callback`。隔离端口从 `SUMMIT_WEB_PORT` 构成 Fake 默认地址；显式 `SUMMIT_FEISHU_REDIRECT_URI` 始终原样使用，不重写配置。仅允许 http loopback callback 与配置的本机 Origin；所有业务路由要求 Bearer，callback 只接受本次运行发起、300 秒有效且一次性的 state。模拟登录仅在本进程有效，重启需重新模拟授权；已完成导入凭据重启后仍能重放本地结果。

~~~sh
uv run pytest -q tests/integration/test_feishu.py
uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
cd web && npm run api:types && npm test && npm run typecheck && npm run lint && npm run build
~~~

这些检查只覆盖合成材料、Fake Feishu 与内存凭据。真实 user access token 的 scope、真实材料读取与长期钥匙串配置尚未验收；M2.2 正式任务写入不在本切片内。
