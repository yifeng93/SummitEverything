# 2026-10-13 清理维护独立 QA — 6a33259

## 身份与范围

- 报告人 / 角色：全新独立 QA，验收者（Luna）
- 完整待测代码 SHA：`6a33259224097167cfdde689da93258fe925964e`；清理前基线 `879c82464903a7aed91b30955d7355064fa85088`
- 独立 checkout：`/Users/yifengstudio/.codex/worktrees/maintenance-cleanup-qa-20261013/SummitEverything`，detached；测试全程 HEAD 未变。系统 macOS 27.0.1 / Darwin 27.0.0 arm64；Python 3.12.13、Node 24.15.0、npm 11.12.1、uv 0.12.3。浏览器本轮未启动。
- 范围：清理维护批准的私有 `_load_items` / import 删除、当前文档入口与历史保留、旧工作树 / 分支 / 本机恢复包清理事实，以及 README 指定的离线自动整包命令。
- 材料：仅源码仓库、测试夹具和合成 / 离线 guard；未读取真实业务材料、凭据或旧应用。
- 服务 / App / frontend / build：没有启动服务或 App；前端以 `npm ci` 后的本地依赖执行测试、类型检查、lint 与 Vite build。`uv build` 产出仅在被测 checkout 的 ignored `dist/`。
- Fake / 真实外部服务、用户授权范围：不调用真实 provider、付费模型、Feishu、Keychain 或真实任务；仅按交接运行 guarded 自动测试与只读 Git remote metadata 查询。

## 结果

| 案例 | 结果 | 实际步骤与观察 | 证据 |
|---|---|---|---|
| CLEAN-01 固定目标与源码边界 | PASS | HEAD 在开始、命令组前后均为完整 SHA `6a33259224097167cfdde689da93258fe925964e`。相对 `879c824` 的唯一产品文件差异是 `src/summit_everything/intake/review.py` 删除 `IntakeReviewService._load_items` 三行方法及唯一随之未用的 `IntakeItem` import；无测试、schema、依赖锁或产品规格改动。基线 `git grep` 仅找到该 helper 的定义。调用 / 反射搜索未发现动态引用；保留 `IntakeReviewService` 的实际使用、`_ResponseStream.__aiter__`、API 注册调用、归档模块和 `scripts/m3_package3_bulk_sample.py`。`domain/models.py` 与 DTO 仍存在。 | `evidence/2026-10-13-cleanup-qa/independent-audit.json`、`docs-scope-final.json` |
| CLEAN-02 文档入口与验收门 | PASS | README、PROGRESS、LATEST、契约、架构、完整 v1 与 M3 计划将 M3 离线正式验收记为已批准并合入 `47a3971`；C19 固定源码 `0a1b8dc` 的 QA PASS 作为历史固定 SHA 结论。当前真实 / DMG / 五日 / 双机仍 NOT_RUN，runtime 仍 UNVERIFIED；已知 run_dev Ctrl+C 清理 PermissionError / exit 1 继续保留。历史失败仍限定于当时 SHA。基线 ACCEPTANCE 全文 39,122 bytes 在 `ACCEPTANCE-HISTORY-2026-10-13.md` 中逐字节保留；C01–C31、B01–B06、R01–R05、PASS/FAIL/BLOCKED/NOT_RUN、MUST 与“实现者自测不等于独立 QA”规则均保留。DSH-C19 是明确指向历史副本的 redirect；新增包1兼容报告明确标为修复链接的历史入口，不签发新 QA 结论。 | `evidence/2026-10-13-cleanup-qa/docs-scope-final.json`、`historic-links-review.json` |
| CLEAN-03 相对链接与历史证据不变 | PASS | 全仓 Markdown 相对链接独立扫描缺失 0；baseline `docs/quality/reports/` 的 1,762 个 tracked 文件中，允许报告索引 README 变更后其余 1,761 个与基线逐字节比较，0 mismatch。三条不可用的旧绝对 checkout 路径都在不可变的 2026-10-11 历史 QA 报告，并由带历史来源说明的 DEV 链接审计记录；QA 未改原件。 | `evidence/2026-10-13-cleanup-qa/independent-audit.json`、`historic-links-review.json` |
| CLEAN-04 本地清理与恢复点 | PASS | 独立检查清理前 main 为 clean `main` / `879c824`。盘点中的 12 个旧 worktree 路径和四个 Documents/GitHub `SummitEverything-DSH-*` 目录实际不存在；五个过期本地分支均不存在。当前本机 worktree 只有 main、Developer 和本 QA 三棵；本地 refs 只有 main 与维护分支。主机 stash 仍在。12 个 snapshot tag OID 均与清单相同；C19 handoff tag `b3d0dff` 存在；额外恢复 tag 指向 `2251ec8`，不是新快照。恢复 bundle SHA-256 为 `8efc21cfb4065766a91ec34791ecf9a18c3a36359b3841c03b8dcececf3bf6e3` 且 `git bundle verify` exit 0；11 个 `.local` tar 均实际可读且 SHA 与清单一致，重复 tar 不存在。归档目录为 0700，文件为 0600。只读 `git ls-remote --heads origin` 观察到 main 与维护分支；C03 remote ref 无输出。 | `evidence/2026-10-13-cleanup-qa/environment-and-docs-summary.json`、`archive-mode-final.json` |
| CLEAN-05 后端与 Web 自动测试 | PASS | 依赖全新安装后 guarded pytest 为 491 passed、1 条既有 Starlette/httpx 弃用 warning；Web 为 12 files / 56 tests passed。 | `pytest-guarded.log/.exit`、`web-test.log/.exit` |
| CLEAN-06 静态检查、锁与构建 | PASS | Ruff check、Ruff format check、mypy、uv lock check、uv build、Web typecheck / lint / build、`git diff --check` 均 exit 0。Oxlint 保留两条既有 `react(set-state-in-effect)` warning（TodayView、ProjectsView）。`uv.lock` 与 `web/package-lock.json` 未变化。 | 对应 `ruff-check`、`ruff-format`、`mypy`、`lock-check`、`uv-build`、`web-typecheck`、`web-lint`、`web-build`、`diff-check` 日志及 `.exit` |
| CLEAN-07 隔离 OpenAPI / TypeScript 生成 | PASS | 将 exporter 与 `src/summit_everything` 复制到 `TemporaryDirectory`，以隔离 `PYTHONPATH` 导出 OpenAPI，再用已安装 `openapi-typescript` 生成临时 TS。两步 exit 0；OpenAPI 与 `web/openapi.json`、TS 与 `web/src/api/generated.ts` SHA-256 均逐字节一致；没有执行会写 tracked 文件的 `npm run api:types`。 | `openapi-export.log/.exit`、`openapi-types.log/.exit`、`openapi-isolated-result.json` |
| CLEAN-08 浏览器 / 服务人工复演 | NOT_RUN | 本轮 UI 与 API 实现没有变化，遵照交接不重跑浏览器或完整服务流程；本结果不表示本轮做过 UI 测试。 | 本报告范围说明 |

## 命令

依赖准备：`uv sync --locked --group dev`（exit 0），`npm --prefix web ci`（exit 0）。全量检查只运行一轮：

| 命令 | Exit | 结果摘要 / 原始日志 |
|---|---:|---|
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | 0 | 491 passed，1 warning；`evidence/2026-10-13-cleanup-qa/pytest-guarded.log` |
| `npm --prefix web test` | 0 | 56 passed / 12 files；`web-test.log` |
| `uv run ruff check src tests` | 0 | All checks passed；`ruff-check.log` |
| `uv run ruff format --check src tests` | 0 | 79 files already formatted；`ruff-format.log` |
| `uv run mypy src` | 0 | 43 source files，无问题；`mypy.log` |
| `uv lock --check` | 0 | lock 已解析，无变化；`lock-check.log` |
| `uv build` | 0 | sdist 与 wheel 成功；`uv-build.log` |
| `npm --prefix web run typecheck` | 0 | 通过；`web-typecheck.log` |
| `npm --prefix web run lint` | 0 | 通过，含两条上述既有 warning；`web-lint.log` |
| `npm --prefix web run build` | 0 | Vite build 成功；`web-build.log` |
| `git diff --check 879c82464903a7aed91b30955d7355064fa85088 6a33259224097167cfdde689da93258fe925964e` | 0 | 无 whitespace error；`diff-check.log` |

隔离生成步骤、输入副本、SHA 和命令输出见 `openapi-isolated-result.json` 与相邻日志。旧恢复 bundle / tar / refs / branch / worktree 的实测与环境输出见 `environment-and-docs-summary.json` 及 `independent-audit.json`。所有 QA 原始日志、exit 文件、终检 JSON 与本报告均列入同目录 `evidence-manifest.sha256`；其 manifest SHA-256 在此记录：88a960e757ccd4de719a9574706b8964263f0ff705eaa377f2dd4f34d61ef6e3。

## 缺陷

未发现本轮验收范围内的产品缺陷。QA 未修改产品实现、tracked tests 或已有 DEV / QA 证据。

## 门结论

- DEV 自测复核：PASS（QA 独立运行了本报告命令，不依赖 DEV 全绿摘要）。
- 本轮清理范围的独立离线 QA 观察：PASS；最终阶段门由 Sol 判断。
- 本轮 UI / API 浏览器人工复演：NOT_RUN，符合此次维护 handoff 对未变 UI 的范围说明。
- 真实 provider / Feishu / 业务材料 / 付费模型 / OS Keychain / 真实样板：NOT_RUN。
- Native / DMG / 安装包 / 发布、五日试用、双机：NOT_RUN。
- Runtime 配置元数据：UNVERIFIED。
- 已知 `scripts/run_dev.py` Ctrl+C 清理可能报 `PermissionError` 且 exit 1；本轮未启动该服务、未复测此风险，也未将其记为通过。

自动检查结果只覆盖本报告明示范围，不替代上述未运行的人工 / 真实门。

## 给执行者的下一步

请 Sol 复核固定 SHA、原始日志、恢复包 / 历史证据核验与证据 manifest 后独立判定门。此 QA 提交只包含本报告与新增 QA evidence；不得把 QA-only 提交误记为产品源码变更。
