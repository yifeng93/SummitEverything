# SummitEverything

SummitEverything 是个人工作知识整理与检索应用。首版目标是每台 Mac 独立运行的 DMG，使用 FastAPI、React/TypeScript 与薄 macOS 壳；工作知识由用户确认后保存为可迁移的 Markdown 页面。

## 当前状态

M3 与清理维护维持原固定 SHA 的历史结论。M4.1 修复轮 1 的固定源码 `3f6eaa408a8860ff5a438be8a874a2c3904733e4` 已经全新独立 QA 与 Sol 证据核验，适用离线技术门 PASS；文件导入缺陷 M41-QA-001 已在实际候选复验关闭，自动修复使用 1/2 轮。正式里程碑收口和合并 main 待用户批准，整个 M4 未通过。见[独立 QA](docs/quality/reports/2026-10-13-M41-INTERNAL-APP-QA-REPAIR1.md)、[Sol 门判断](docs/quality/reports/2026-10-13-M41-SOL-GATE.md)、[内部候选测试说明](docs/handoff/M41-INTERNAL-INSTALL.md)与[最新交接](docs/handoff/LATEST-IMPLEMENTATION.md)。原候选 `b9321d6` 的初验 FAIL 与完整 DEV / QA 证据均保留。

本轮实现了内置 Python onedir 后端、强制重建静态前端、独立 Internal bundle/profile、每次运行新 token、健康身份与资源指纹校验、loopback Bearer API 和原生生命周期。构建目标为 arm64、最低系统版本声明 macOS 13；本机实测环境为 arm64 macOS 27.0.1，其他架构与系统版本未测。内部候选未公证，实际用户安装、签名证书/公证、真实模型与飞书、真实材料、OS Keychain、M4.2、五日试用、双机和发布仍为 NOT_RUN；runtime 模型元数据 UNVERIFIED。

## 文档入口

- 执行者：[AGENTS.md](AGENTS.md) → [最新交接](docs/handoff/LATEST-IMPLEMENTATION.md) → [执行手册](docs/handoff/IMPLEMENTER.md) → [全 v1 计划](docs/superpowers/plans/2026-10-09-summit-everything-v1.md)。
- 验收者：[AGENTS.md](AGENTS.md) → [独立验收手册](docs/handoff/TESTER.md) → [验收矩阵](docs/quality/ACCEPTANCE.md)。
- 当前进展：[进展账本](docs/implementation/PROGRESS.md)；[报告索引](docs/quality/reports/README.md)；[全部文档](docs/README.md)。
- 新聊天提示词：[实现者](docs/handoff/PROMPT-IMPLEMENTER.md)、[验收者](docs/handoff/PROMPT-TESTER.md)。

## 产品范围

知识目录由主线、项目和页面组成；已确认且仍为当前版本的页面进入问答语料。原件、待审稿、收件箱状态和辅助状态不作为依据。模型输出只是建议；正式内容以及任务/项目进度动作分别由用户确认。聊天历史、角色、记忆、索引、凭据和诊断日志留在本机。完整已确认范围见[产品规格](docs/product/PRODUCT-SPEC.md)。

## 当前可执行的命令

在本仓库执行；只安装本项目的工具，不同步或改动 SWB / SK 的环境。

Fresh checkout 运行全量 `pytest` 前，先按下方 WebUI 预览步骤安装前端依赖；dev runner 集成测试需要已安装的 Web 依赖。

~~~sh
uv sync --locked --group dev
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy src
uv lock --check
uv build
swift test --package-path native
~~~

guard 阻断非 loopback socket、真实 DNS 和 macOS Keychain，允许合成 HTTP 与数字 loopback。生产 HTTP 必须使用请求独立的 DeadlineTransport；完整 JSON wire ≤1MB、identity 响应有界读取、禁止环境代理/重试/重定向。

这些是检查命令，不单独构成阶段通过。M1 / M2 的历史报告见报告索引；当前 M4.1 修复轮 1 Developer 自测与 QA handoff 见最新交接。

### 构建 M4.1 Internal 候选

只在 arm64 macOS 构建机器上运行。输出路径必须是全新路径；脚本先强制构建 WebUI、检查锁定依赖、构建内置 Python onedir 与 Swift 壳、校验 bundle，再创建并验证只读可挂载的未公证 DMG。它不会安装或覆盖应用：

~~~sh
uv sync --locked --group dev --group build
npm --prefix web ci
scripts/release-macos.sh "$PWD/.local/dev/m41/artifacts/SummitEverything Internal.app" "$PWD/.local/dev/m41/artifacts/SummitEverything-Internal.dmg"
~~~

该候选供隔离 QA 使用，不表示用户正式安装、Gatekeeper/公证或 M4 阶段验收已通过。

### 本地 WebUI 开发预览（M1 / M2）

先安装前端依赖，然后在仓库根目录启动 FastAPI 与 Vite。脚本自动生成仅供本次进程使用的本机会话 token 和运行身份，并在退出时只关闭自己启动的服务：

~~~sh
cd web && npm ci
cd ..
uv run python scripts/run_dev.py
~~~

打开 `http://127.0.0.1:5173`，新建工作库时选一个空的隔离目录。隔离并发复演可通过 `SUMMIT_API_PORT`、`SUMMIT_WEB_PORT` 和 `SUMMIT_PROFILE_ROOT` 指定独立端口与 profile。原生内部候选通过 `scripts/release-macos.sh` 构建；该 `.app` 从自身 bundle Resources 启动后端，不使用 `swift run` 的开发启动方式。实际开发预览继续使用上方的 Web runner。

WebUI 支持主线 / 项目 / 页面浏览与管理、页面移动和链接确认、随手记、文字导入、显式模型整理、多稿审核、单页确认与更新、增量索引及本地 SSE 问答。查询仅使用经确认且仍为当前版本的页面。TXT / Markdown 导入要求 UTF-8，最大 20 MB。首次索引仍需用户在界面确认；Fake 模式已有索引时，批准的新内容和重新确认内容会自动执行同模型 fingerprint 的增量更新。真实 embedding 下审批只提示用户另行查看并确认索引计划。更新失败或中断时，页面版本复核会阻止旧片段作为当前依据。

内部 `.app` readiness 校验通过后显示同一 WebUI，工作库可通过原生目录选择器指定。打包后的 App 内置后端与静态前端；开发预览仍依赖本机 Python / Node 工具。默认仍为 Fake/offline；设置读取和保存不会联网。普通整理、索引和问答的真实模型请求仍由服务端拒绝；仅三条独立 smoke 路由接受固定合成输入，每种 provider 每个 app profile 最多尝试一次，尚未调用。Feishu OAuth / 数据 adapter 已有离线实现；真实业务材料与真实账户验收仍未完成。Feishu Fake 仍使用进程内凭据存储。

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

这些检查只覆盖合成材料、Fake Feishu 与内存凭据。真实 scope、材料和 OS 钥匙串验收仍 NOT_RUN；设置入口与 adapter 已实现，真实任务写入保持禁用。

M2.1 审查修正：模拟授权严格保留已配置 callback 的 scheme / host / port / path；可跨 Web / API 端口完成本机 callback，浏览器请求不携带 Bearer 或 cookie，不跟随重定向。callback 仅向 allowlist Origin 开放读取并禁止缓存。界面收到 expired / not_authorized 时立即停用读取，missing_scope 单独显示“权限不足”。应用 app_id 属于非秘密配置，app_secret 由独立 AppCredentials / CredentialStore 接口隔离；已有真实 adapter、凭据设置 UI 与 fail-closed Keychain 接口；此段 Fake 复演不能证明真实账户或 OS Keychain 通过。


### M2.2 任务与独立动作模拟复演

只用空的隔离工作库与上述 Fake 模拟授权。“今日 / 飞书任务与独立动作”可读取任务、填写创建表单、只选所改字段编辑、拟定完成或项目进度变化。必须先审阅最终值，再点击“独立确认此动作”，随后明确执行；知识确认、列表刷新和建议都不执行动作。任务标题和日期方式由用户填写；没有默认截止日期。日期保留用户原文、全天标志和 IANA 时区；具体时间要求显式时区偏移一致。

结果未知时只读核实或记录用户独立提供的明确结果；不重发未知动作、不按标题猜成功。任务创建 / 编辑 / 完成的回执会核对目标与请求字段，完成必须有非零完成时间。Fake 核实证据绑定当前 client token、动作类型、目标和实际返回字段；普通任务对象不能核实动作。动作记录可分页读取及重启恢复。模拟远端任务文件 `simulated_remote_tasks.json` 位于系统临时目录下明确命名的 `summit-simulated-feishu-remote-*`，不在工作库 / profile 的任务账本；正式任务事实由 provider 返回，本地仅保存提议和执行证据。重启后须重新模拟授权；模拟远端和本地回执仍可读取。

~~~sh
uv run pytest -q tests/integration/test_actions.py
uv run pytest -q tests/integration/test_intake_review.py tests/integration/test_feishu.py
npm --prefix web test -- TasksPanel.test.tsx
~~~

Task v2 的毫秒 timestamp 与全天日期含义见协议矩阵；账号侧规范化仍需真实证据，Fake 约定不能替代它。Fake `task_result` 是合成动作证据查询，未声称飞书存在按 client_token 查结果的真实端点。没有可验证查询证据时动作保持 unknown。真实任务、账号、凭据 / 钥匙串与协议验收未测。DEV 证据见 [M2.2 任务报告](.superpowers/sdd/2026-10-09-summit-everything-v1/task-M2.2-report.md)。

### M2.3 日志、思考与项目概览

侧栏“日志与思考”提供独立日志 / 思考入口；可不关联、仅关联主线或关联主线与项目。保存按钮明确确认并仅写入本机正式页。浏览列表不会调用模型；“AI 辅助建议”只请求 FakeLLM，将可编辑建议留在编辑区，用户可取消或采用，仍需另行点击保存。页面以稳定操作标识防止重试重复写入。

项目详情可显式创建项目概览并从目录重开；修改要求当前页面版本，冲突保留现有正文。概览保存、日志 / 思考保存与项目进度动作分别处理；保存知识不更改进度。验证命令：

~~~sh
uv run pytest -q tests/integration/test_journal_overviews.py
npm --prefix web test -- JournalView.test.tsx ProjectsView.test.tsx
~~~

此切片只用模拟工作库与 FakeLLM；没有执行真实模型、真实材料、真实飞书或任务写入。M2.3 DEV 报告和 [汇总 M2 DEV 报告](docs/quality/reports/2026-10-10-M2-DEV.md)保留开发时的 UI 复演与未测项；阶段 A 当前独立验收结果见上方状态与[验收矩阵](docs/quality/ACCEPTANCE.md)。
