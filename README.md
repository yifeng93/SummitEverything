# SummitEverything

个人工作知识应用：把工作材料整理成经本人确认、可复用、可迁移的 Markdown 资产，并在同一应用中完成检索问答与日常工作。

首版交付 macOS DMG，内部使用 WebUI；每台电脑独立运行，本地目录或 OneDrive 保存工作库。核心栈为 Python / FastAPI、React / TypeScript、SQLite 和薄 macOS 壳。

## 当前状态

2026-10-12 最新结果：用户授权的 extra 1 已完成；历史确认/效力及本人偏好两修均通过，包 2 仍因 C19 无依据回答误报缓存/资格异常而 FAIL（P2 提示误导，无数字编造或证据泄漏）。固定源码 `bb997a42ed1d218e10527e3e07e6c587fc9929f6`，QA 固定 `507cc1f197ce3af3b22aa53c98148e4ca45ff935`。停止产品修改，等待用户是否授权下一轮；包 1 保留 PASS，包 3 尚未实施。 [Sol 核证与接续](docs/quality/reports/2026-10-12-M3-SOL-EXTRA-1-GATE.md)。下方 QA pending/授权状态是对应交接发布时历史，由本条取代。

2026-10-12 最新状态：包 1 离线集成由 Sol 判 PASS。包 2 的 repair 2/2 QA 曾判 FAIL，见[Sol 门判断](docs/quality/reports/2026-10-12-M3-SOL-GATE.md)；用户随后明确批准仅一轮额外修复。Developer 已在源码 `bb997a42ed1d218e10527e3e07e6c587fc9929f6` 完成 extra 1 自测，现待全新独立 QA；这不是 QA PASS 或 Sol 门结论。此前首轮及 repair 1/2、repair 2/2 的 QA FAIL 原报告继续保留。若 extra 1 QA 仍 FAIL，需再次由用户决定，不能自动继续。包 3 只完成只读准备，待包 2 QA 通过后接续；M3 正式验收和合并尚未执行。最新实现、受测 SHA 与自测结果见[最新交接](docs/handoff/LATEST-IMPLEMENTATION.md)和[extra 1 DEV 报告](docs/quality/reports/2026-10-12-M3-PACKAGE-2-EXTRA-1-DEV.md)。

2026-10-11：Stage B 离线源码收口候选 `576895f6983ca41cacbbad45a9075b97b9986189` 已由 Luna High 在独立 checkout 复验：后端388项与25项独立失败路径通过，Web45项及类型/构建检查通过；实际浏览器、原生冷启动、重启、5秒Web启动延迟与退出清理已复验。已合入main（PR #10，merge `41207e5bfb81b535c0254fd4ac242df11da40d67`），合并后核验、证据发布更正及归档清理见[收口记录](docs/quality/reports/2026-10-11-STAGE-B-POSTMERGE.md)。已采纳 DeepSeek R1–R4 中经复核的实现，并修复传输取消/资源所有权/大小边界、未知refresh跨重启重发、严格凭据解析和原生就绪问题。历史FAIL与原始证据保留。此结论仅覆盖离线源码和开发壳；真实账户/协议运行、OS Keychain、模型R03质量、DMG、M4/M5、五日/双机仍NOT_RUN，不能称完整Stage B或v1验收通过。保留当时的Starlette弃用及3条React lint warning。

已有有限 smoke 授权保持：code exchange ≤1、必要 refresh ≤1、DeepSeek chat / embedding / rerank 各 ≤1；实际次数全部 **0/1**。不索取或使用密钥，不读取真实身份/材料/日历/task，不执行真实任务写入，也不因新 profile 重置次数。真实材料另有内容确认门。CNY 5 为旧提示词建议操作上限，不是用户指定预算；真正使用既有授权前须核对官方当前价格。

权威入口：[最新交接](docs/handoff/LATEST-IMPLEMENTATION.md)、[进展账本](docs/implementation/PROGRESS.md)、[验收矩阵](docs/quality/ACCEPTANCE.md)、[报告索引](docs/quality/reports/README.md)。DeepSeek 历史各轮报告与失败证据保留。

C03 删除拒绝提示切片已随 [PR #11](https://github.com/yifeng93/SummitEverything/pull/11) 合入 main（merge `2f08c764e740afa494a0445ec4d73382fdd55f3b`）；源码受测 SHA 为 `9c953f095086a95e63edbce2169657dba9e71cd1`，合并后核验见[交接](docs/handoff/LATEST-IMPLEMENTATION.md)。M3 按三个集成开发包推进；包 1“会话与历史”由 Sol 判定离线集成 PASS：修复源码 `a9078bd327f73f2cde3bab14a8665885d0f57c1c`，QA 固定提交 `bc3deabcc4cb6c18a9e8b4809b0ac19e9f20dfb4`。包 2 首轮、repair 1/2 和 repair 2/2 独立 QA 均为 FAIL，原报告及证据保留；用户明确批准额外一轮，Developer extra 1 源码 `bb997a42ed1d218e10527e3e07e6c587fc9929f6` 已固定，待全新独立 QA。该版本把历史页批准状态和知识效力分开，并依据真实 user 原文中的来源归属语境判断候选；自测不代表 QA 或包级 PASS。完整状态见[最新实现](docs/handoff/LATEST-IMPLEMENTATION.md)、[进展账本](docs/implementation/PROGRESS.md)、[报告索引](docs/quality/reports/README.md)与[extra 1 DEV 报告](docs/quality/reports/2026-10-12-M3-PACKAGE-2-EXTRA-1-DEV.md)。包 3（连续工作与归档压缩）尚未开始，等待包 2 QA gate。M3 完整验收及真实/发布门仍未完成。

开发协作按 [Sol / Luna 工作流 ADR](docs/decisions/0008-sol-luna-development-workflow.md)：Sol 规划和审查，Developer Luna 完成整个功能包并固定 SHA，再由独立 QA Luna 验收，Sol 判定最终门。包 1 离线集成已通过；包 2 repair 2 独立 QA 曾由 Sol 判 FAIL，用户后来明确批准仅一轮额外修复。extra 1 已完成 Developer 自测，待新 SHA 独立 QA；若仍失败则停止并请用户决定。Stage C 与发布 / 实际试用门仍独立未测。

## 先读哪些文件

- 执行者：[AGENTS.md](AGENTS.md) → [最新交接](docs/handoff/LATEST-IMPLEMENTATION.md) → [执行手册](docs/handoff/IMPLEMENTER.md) → [全 v1 计划](docs/superpowers/plans/2026-10-09-summit-everything-v1.md)。
- 验收者：[AGENTS.md](AGENTS.md) → [独立验收手册](docs/handoff/TESTER.md) → [验收矩阵](docs/quality/ACCEPTANCE.md)。
- 全部资料：[文档索引](docs/README.md)；当前工作：[进展账本](docs/implementation/PROGRESS.md)。
- 两个新聊天可直接使用：[执行提示词](docs/handoff/PROMPT-IMPLEMENTER.md)、[验收提示词](docs/handoff/PROMPT-TESTER.md)。

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
~~~

guard 阻断非 loopback socket、真实 DNS 和 macOS Keychain，允许合成 HTTP 与数字 loopback。生产 HTTP 必须使用请求独立的 DeadlineTransport；完整 JSON wire ≤1MB、identity 响应有界读取、禁止环境代理/重试/重定向。

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

WebUI 支持主线 / 项目 / 页面浏览与管理、页面移动和链接确认、随手记、文字导入、显式模型整理、多稿审核、单页确认与更新、增量索引及本地 SSE 问答。查询仅使用经确认且仍为当前版本的页面。TXT / Markdown 导入要求 UTF-8，最大 20 MB。首次索引仍需用户在界面确认；Fake 模式已有索引时，批准的新内容和重新确认内容会自动执行同模型 fingerprint 的增量更新。真实 embedding 下审批只提示用户另行查看并确认索引计划。更新失败或中断时，页面版本复核会阻止旧片段作为当前依据。

开发壳在 readiness 后显示同一 WebUI，工作库可通过原生目录选择器指定。此壳依赖本机 `uv`、Node.js 和已安装的前端依赖；它不是可安装 DMG。默认仍为 Fake/offline；设置读取和保存不会联网。当前 Stage B 候选即使启用 Real provider，普通整理、索引和问答的真实模型请求也会被服务端拒绝；仅三条独立 smoke 路由接受固定合成输入，每种 provider 每个 app profile 最多尝试一次，尚未调用。Feishu OAuth / 数据 adapter 已有离线实现；真实业务材料与真实账户验收仍未完成。Feishu Fake 仍使用进程内凭据存储。

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
