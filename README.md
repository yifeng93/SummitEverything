# SummitEverything

个人工作知识应用：把工作材料整理成经本人确认、可复用、可迁移的 Markdown 资产，并在同一应用中完成检索问答与日常工作。

首版交付 macOS DMG，内部使用 WebUI；每台电脑独立运行，本地目录或 OneDrive 保存工作库。核心栈为 Python / FastAPI、React / TypeScript、SQLite 和薄 macOS 壳。

## 当前状态

2026-10-10：M1 与 M2.1–M2.3 阶段 A 已在 Fake-only 范围完成独立验收并合入 main。最终受测修复代码为 `30903c4cdf73855af71a201e3edea6c535ee8199`，收口 main 为 `117086eb2075726730cd7aa62ea0b61498e96f0c`。C18 恢复 UI 的旧 FAIL 和修复后 PASS 分别保留；截图撤回、故障恢复和并发证据见[报告索引](docs/quality/reports/README.md)。当前仅有 Fake providers 和内存凭据；真实资源虽已准备，真实 adapter、配置和 Keychain 尚未实现，真实环境门仍 NOT_RUN。

下一步按[B/C 执行提示词](docs/handoff/PROMPT-STAGE-B-C-LUNA.md)先完成 B 的适配与离线独立 QA，再经逐项授权做 C 的受控真实验收。B/C 与 M3–M5 尚未开始，DMG、五日和双机仍有独立门。[最新交接](docs/handoff/LATEST-IMPLEMENTATION.md)、[进展账本](docs/implementation/PROGRESS.md)、[验收矩阵](docs/quality/ACCEPTANCE.md)记录固定 SHA 和证据边界；[工作环境整理](docs/implementation/2026-10-10-STAGE-A-CLEANUP.md)记录旧分支 / worktree 归档。

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

这些是检查命令，不单独构成阶段通过。M1 / M2 阶段 A 的独立报告、原生开发壳 UI 和后续修复范围见报告索引；真实飞书、真实模型质量、Keychain、DMG、五日及双机仍未通过相应门。

### 本地 WebUI 开发预览（M1 / M2）

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

WebUI 支持主线 / 项目 / 页面浏览与管理、页面移动和链接确认、随手记、文字导入、显式 FakeLLM 整理、多稿审核、单页确认与更新、增量索引及本地 SSE 问答。查询仅使用经确认且仍为当前版本的页面。TXT / Markdown 导入要求 UTF-8，最大 20 MB。首次索引仍需用户在界面确认；已有索引后，批准的新内容和重新确认内容会自动执行同模型 fingerprint 的增量更新，并显示实际更新状态。更新失败或中断时，页面版本复核会阻止旧片段作为当前依据。

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

这些检查只覆盖合成材料、Fake Feishu 与内存凭据。真实 user access token 的 scope、真实材料读取与 OS 钥匙串配置入口尚未实现 / 验收；M2.2 正式任务写入不在本切片内。

M2.1 审查修正：模拟授权严格保留已配置 callback 的 scheme / host / port / path；可跨 Web / API 端口完成本机 callback，浏览器请求不携带 Bearer 或 cookie，不跟随重定向。callback 仅向 allowlist Origin 开放读取并禁止缓存。界面收到 expired / not_authorized 时立即停用读取，missing_scope 单独显示“权限不足”。应用 app_id 属于非秘密配置，app_secret 由独立 AppCredentials / CredentialStore 接口隔离；仅测试合成秘密，不存在真实账号适配器、凭据设置 UI 或 OS Keychain 权限路径。


### M2.2 任务与独立动作模拟复演

只用空的隔离工作库与上述 Fake 模拟授权。“今日 / 飞书任务与独立动作”可读取任务、填写创建表单、只选所改字段编辑、拟定完成或项目进度变化。必须先审阅最终值，再点击“独立确认此动作”，随后明确执行；知识确认、列表刷新和建议都不执行动作。任务标题和日期方式由用户填写；没有默认截止日期。日期保留用户原文、全天标志和 IANA 时区；具体时间要求显式时区偏移一致。

结果未知时只读核实或记录用户独立提供的明确结果；不重发未知动作、不按标题猜成功。任务创建 / 编辑 / 完成的回执会核对目标与请求字段，完成必须有非零完成时间。Fake 核实证据绑定当前 client token、动作类型、目标和实际返回字段；普通任务对象不能核实动作。动作记录可分页读取及重启恢复。模拟远端任务文件 `simulated_remote_tasks.json` 位于系统临时目录下明确命名的 `summit-simulated-feishu-remote-*`，不在工作库 / profile 的任务账本；正式任务事实由 provider 返回，本地仅保存提议和执行证据。重启后须重新模拟授权；模拟远端和本地回执仍可读取。

~~~sh
uv run pytest -q tests/integration/test_actions.py
uv run pytest -q tests/integration/test_intake_review.py tests/integration/test_feishu.py
npm --prefix web test -- TasksPanel.test.tsx
~~~

全天日期的真实 Task v2 timestamp 提取规则未从可访问的一手文档确证；当前午夜转换仅为 Fake 约定，不可直接用于真实 adapter。Fake `task_result` 是合成动作证据查询，未声称飞书存在按 client_token 查结果的真实端点。没有可验证查询证据时动作保持 unknown。真实任务、账号、凭据 / 钥匙串与协议验收未测。DEV 证据见 [M2.2 任务报告](.superpowers/sdd/2026-10-09-summit-everything-v1/task-M2.2-report.md)。

### M2.3 日志、思考与项目概览

侧栏“日志与思考”提供独立日志 / 思考入口；可不关联、仅关联主线或关联主线与项目。保存按钮明确确认并仅写入本机正式页。浏览列表不会调用模型；“AI 辅助建议”只请求 FakeLLM，将可编辑建议留在编辑区，用户可取消或采用，仍需另行点击保存。页面以稳定操作标识防止重试重复写入。

项目详情可显式创建项目概览并从目录重开；修改要求当前页面版本，冲突保留现有正文。概览保存、日志 / 思考保存与项目进度动作分别处理；保存知识不更改进度。验证命令：

~~~sh
uv run pytest -q tests/integration/test_journal_overviews.py
npm --prefix web test -- JournalView.test.tsx ProjectsView.test.tsx
~~~

此切片只用模拟工作库与 FakeLLM；没有执行真实模型、真实材料、真实飞书或任务写入。M2.3 DEV 报告和 [汇总 M2 DEV 报告](docs/quality/reports/2026-10-10-M2-DEV.md)保留开发时的 UI 复演与未测项；阶段 A 当前独立验收结果见上方状态与[验收矩阵](docs/quality/ACCEPTANCE.md)。
