# Ponytail 全面精简批次一、二 — Developer 记录

日期：2026-10-17
基线：`6f8fe80558d6e51481f6a3dd203c7e53e6faad89`
分支：`codex/ponytail-cleanup-20261017`
范围：批次一整理当前文档入口；批次二审计 `src`、`web/src`、`native`、`scripts`、`tests` 和依赖，删除一处有充分证据的死代码。未处理本机磁盘清理。

## 交付

- README 改为项目首页，保留能力、隔离开发启动、常用检查和文档入口；历史 DEV/QA 过程与 SHA 不再放在首页。
- PROGRESS 是唯一产品状态来源；LATEST 只记录当前文档任务、产品代码基线、QA 指令及状态链接。
- 同步 AGENTS、ADR 0008、实现/测试手册、对应提示词、文档与报告索引，以及完整 v1 计划入口说明。
- 修正架构中“不存在真实 Feishu HTTP adapter”的旧描述；API 文档不再把候选实现与旧阶段状态作为当前说明；ACCEPTANCE 不再声明当前 main 等同 M4.2 的旧 SHA。C01–C31、UI 十条守卫、产品范围、真实验收门均保留。
- 新增本批次唯一计划 `docs/superpowers/plans/2026-10-17-ponytail-cleanup.md`。既有报告/evidence 原件不修改、不删除。

## 文档处置理由

README 原有大量历史里程碑细节、旧固定 SHA、逐轮 QA 和面向已完成阶段的操作提示，混淆了首页与状态账本的职责；重写为精简项目入口。PROGRESS 保留产品基线与未测范围，并仅增补文档批次状态。LATEST 原来复制多轮报告内容，改为可执行交接。手册与 prompt 移除旧阶段开场、候选与历史操作指令，统一链接权威状态和验收标准。ARCHITECTURE/API/ACCEPTANCE 的实现性旁注改为当前契约或明确历史注记，不改产品规格迁就源码。

## 检查

实现前 HEAD/分支/工作区检查：`pwd && git status --short --branch && git rev-parse HEAD && git branch --show-current` — **PASS / exit 0**；初始工作区 clean，HEAD 与分支符合任务指定值。

以下检查在修改后执行并填入实际退出码：

| 检查 | 结果 |
|---|---|
| 本地 Markdown 链接与锚点（20 份当前文档） | PASS / exit 0；检查 265 个本地链接、0 个错误。BASE 有 1 个原有失效锚点，已修正为实际标题 `#1-库与身份` |
| 当前入口失效指令/旧状态扫描 | PASS / exit 0；无旧阶段提示作为当前入口，无旧三处状态维护口径 |
| 受保护历史报告/evidence base→worktree | PASS / exit 0；`git diff --name-status BASE -- docs/quality/reports` 仅显示允许更新的索引 README；新增本 DEV 报告为本轮文件，其他历史报告与 evidence 未变 |
| `src tests web native scripts` 与依赖树未变 | PASS / exit 0；`git diff --quiet BASE -- src tests web native scripts pyproject.toml uv.lock web/package.json web/package-lock.json` |
| `git diff --check` | PASS / exit 0 |

未运行产品全量测试、浏览器、DMG 构建或真实服务：本批仅改文档，任务要求使用文档专项 QA。真实 provider/Feishu、业务材料、OS Keychain、用户安装/公证、五日/双机/发布等仍按 PROGRESS 标为未测；本轮没有采集 runtime 模型元数据。

一次正则化链接扫描器将 FRONTEND-GUIDE 的正文误读为路径并报错；该次未形成文档检查结果。随后使用过滤空格目标、校验文件与锚点的检查器重跑，结果见表格。

对整个 `docs/**/*.md` 的探索性扫描检查了 382 份文档和 1,153 个链接，发现 28 个历史报告/evidence 内的旧绝对路径、归档 harness 参考或报告行号锚点。该扫描不是验收门；涉及的历史原件均未改动，当前入口与本轮相关文档的 265 个链接已单独通过检查。

Developer 自测不代表 fresh QA 或 Sol gate 通过。QA 应按 [LATEST-IMPLEMENTATION](../../handoff/LATEST-IMPLEMENTATION.md) 在独立 checkout 验收其指定的完整固定 SHA。

## 批次一结论与代码批次二交接

文档批次一候选 `f57c7ed3a6d2e6763e1624aa3fd08187f5c4d796` 已由 fresh QA 检查；Sol 核读其原始日志和证据后判文档专项 PASS。原始 QA 证据位于 [`evidence/2026-10-17-ponytail-docs-qa`](evidence/2026-10-17-ponytail-docs-qa/README.md)。该结论仅覆盖文档批次一。

代码批次二的产品源码基线为 `5ef96375634a963d5961c8636ffec210aae6c9a9`。产品源码提交 `2d90a7e9efc9ed67f6a0260323f9b071d586f7a1`（`refactor: remove unused job hash helper`）只从 `src/summit_everything/workspace/state.py` 删除 4 行 `job_attempt_hash` 定义。它输入任意 job attempt JSON 值，按 `_canonical` 算 SHA-256；在该 helper 后没有任何用途或调用者。

### 候选、入口、契约与依赖审计

| 候选 | 引用/入口/构建/动态证据 | 决策 |
|---|---|---|
| `job_attempt_hash` (`workspace/state.py`) | 全仓（含隐藏文件，排除 `.git`、`node_modules`、`.venv`）源码搜索仅在定义处命中；Python 源码/脚本 AST 与文本搜索没有调用/import，Web/native 无入口；提交历史显示它由 `fd12177c04dd6dd9a5d85078a5f1f7bb4c2b8c26` 首次新增且后续没有使用；WORKSPACE/API 契约、Stage M3.2 计划均没有此 API 或此名称的持久格式要求。`state.py` 的 `AttemptLease`、`attempt_is_live`、`archive_intake`、`list_items`、`get_job` 仍由 intake 路径调用。 | 删除定义。无反射、插件或导出表引用证据。其输入本身为泛型 dict，删除不改任务存档格式或 API。 |
| `state._canonical` 与 `archives._canonical` | 两者实现相近，但前者用于 `list_items` 的历史 attempt 版本链校验，后者用于摘要条目 SHA 和摘要写入；持久化 JSON 摘要必须保持字节行为。 | 保留，合并收益低、涉及持久化摘要风险高。`hashlib` 仍服务于有效版本链校验。 |
| 直接 Python / 前端依赖 | `httpcore` 在 `integrations/transport.py` 直接构造 network backend、pool、request/response 并处理错误；`python-multipart` 被 FastAPI 上传路由 `UploadFile`/`File()` 使用；PyYAML 用于工作库 frontmatter 读取/写入；FastAPI、Pydantic、HTTPX、uvicorn、keyring、aiodns、pyinstaller 及 Web React/Vite/TypeScript/Vitest/Playwright 等依赖均有源码、脚本、测试或构建入口引用。`native/Package.swift` 仅声明本仓库 targets，无外部 Swift package。 | 未移除依赖；`pyproject.toml`、`uv.lock`、`web/package.json`、`web/package-lock.json` 与 `native/Package.swift` 未改。其它未证实无调用者的模块和构建入口均保留。 |
| 测试合并候选 | 已检查归档及整理审阅测试；阶段 B 的并发、取消、DNS/TLS、流式传输和刷新场景分散覆盖不同边界。没有证明可无损合并的重复测试。 | 无测试修改或合并；原场景与断言全部保留，场景映射表不适用。 |

归档链仍在 `state.py` 中以 `_canonical` 与 `hashlib.sha256` 校验前后版本摘要；`archives.py` 仍校验月摘要中的每个条目 SHA。新增文档状态不会改变这些代码路径、持久格式或 API。批次二 diff 只有此函数的删除，无 UI、OpenAPI/生成类型或依赖变化。

### 批次二自测与退出码

在独立工作树执行自己的锁定依赖安装：`uv sync --locked --group dev --group build` — exit 0；`npm ci` — exit 0。前后两个离线守卫回归命令完全一致：

- 删除前：`PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/unit/test_workspace_archives.py tests/integration/test_intake_review.py` — exit 0，36 passed，1 项既有 Starlette/httpx deprecation warning。
- 删除后：同一命令 — exit 0，36 passed，1 项相同 deprecation warning。
- `uv run ruff check src tests` — exit 0；`uv run ruff format --check src tests` — exit 0，101 files formatted。
- `uv run mypy src` — exit 0，47 source files 无问题。
- `uv lock --check` — exit 0；`git diff --check` — exit 0。
- `git diff --quiet -- uv.lock pyproject.toml web/package.json web/package-lock.json web/src native scripts tests` — exit 0，确认未改动以上树（此项在源码提交前检查）。
- 全仓复搜删除后没有 `job_attempt_hash` 命中；产品源码基线至源码提交的 diff 只显示 `state.py` 删除 4 行。

命令日志保存在忽略目录 `.local/dev/ponytail-cleanup/`。本轮没有运行全量 Python、Web/Vitest、Playwright、Swift、打包 App/DMG；遵照交接由独立 QA 对固定产品源码 SHA 集中执行。真实 provider/飞书、业务材料、凭据/Keychain、实际安装/公证、五日/双机/发布和 runtime metadata 仍 NOT_RUN / UNVERIFIED，不属于本轮验收。

源码候选固定 SHA：`2d90a7e9efc9ed67f6a0260323f9b071d586f7a1`。后续文档交接提交只改本 DEV 报告、PROGRESS 和 LATEST；QA 对照源码树应与该固定源码 SHA 完全一致。Developer 自测不代表代码批次 fresh QA 或 Sol 阶段门通过。
