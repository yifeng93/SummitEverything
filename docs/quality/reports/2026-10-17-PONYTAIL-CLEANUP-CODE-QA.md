# Ponytail code cleanup QA — draft

## 身份与范围

- 固定待测完整 SHA：`5835faa72b513202e92694f4fa14790afefe1e70`
- 产品源码提交：`2d90a7e9efc9ed67f6a0260323f9b071d586f7a1`
- 独立 checkout：`/Users/yifengstudio/.codex/worktrees/ponytail-code-qa-20261017/SummitEverything`
- 初始 HEAD 精确匹配目标，detached HEAD，初始 git status clean。
- 系统：arm64 macOS 27.0.1，Python 3.12.13，uv 0.12.3，Node 24.15.0，npm 11.12.1，Swift 6.4。
- 对照基线 `5ef96375634a963d5961c8636ffec210aae6c9a9`：产品树只有 `src/summit_everything/workspace/state.py` 删除 4 行 `job_attempt_hash`。目标产品树与源码提交 `2d90a7e9efc9ed67f6a0260323f9b071d586f7a1` 一致，diff exit 0。
- docs-only 后续变更中，原有 `docs/quality/reports/evidence` 没有 diff；目标 HEAD 的 DOC/PROGRESS/LATEST 入口链接检查 10 个本地链接均存在。PROGRESS 为唯一产品状态来源，LATEST 指向 DEV、方案和 PROGRESS；基线及真实门限制一致。
- 范围：独立离线全量回归、源码/依赖/测试树边界核验、内部候选 App/DMG 技术构建与包 smoke。Fake/Mock 与临时数据；未调用真实 provider、Feishu、Keychain、真实材料或服务。

## 结果

| 案例 | 结果 | 观察 |
|---|---|---|
| 产品 diff / 精简边界 | PASS | 仅删除 4 行 helper；`hashlib`、`_canonical`、档案链仍在。API、生成类型、工作库格式、前端、native、脚本、依赖和测试均未改。源码 diff exit 0。 |
| Python 全量离线回归 | PASS | 712 passed；1 条 Starlette/httpx 弃用 warning。 |
| Python 静态与包构建 | PASS | Ruff、format、mypy、uv lock check、uv build 均 exit 0。 |
| Web 单元、类型、lint、build、API types | PASS | Vitest 239/239；其余均 exit 0。保留两条既有 Oxlint warning、603.32 kB chunk advisory。API 生成后 `generated.ts` 与锁文件 diff 为空。 |
| Chromium 离线 UI | PASS | Playwright 2/2：首配恢复、主题/视口。 |
| FastAPI + Fake 集成 | PASS | Playwright 1/1，真实本机后端配一次性 token 与合成 Fake 库。 |
| Swift | PASS | 5/5。 |
| 内部 App/DMG 构建 | PASS | release 脚本 exit 0；codesign strict、hdiutil verify、packaged smoke 均 exit 0。 |
| App/DMG 身份 | PASS | build-info `source_sha=5835faa72b513202e92694f4fa14790afefe1e70`、`dirty=false`；DMG SHA-256 `b97594003fc753be16ca455f0681f9e51a8055e4962916f3c06a612d232bee47`。 |
| 真实外部、Keychain、用户安装/公证、五日/双机/发布 | NOT_RUN | 本轮只覆盖离线技术门。runtime model metadata 未暴露，UNVERIFIED。 |

## 场景映射（来自本轮全量通过的既有测试）

- 收件整理、幂等重试与失败后显式重试：`tests/integration/test_intake_review.py::test_identical_intake_retry_reuses_item_and_source`、`test_failed_source_is_visible_and_retry_requires_explicit_reprocess`。
- 部分确认：同文件 `test_explicit_job_creates_reviewable_draft_and_partial_confirmation`。
- 过期内容排除及引用：`tests/integration/test_qualified_retrieval.py::test_external_edit_and_reapproval_reject_old_cached_chunk`。
- 异步取消：`tests/integration/test_intake_review.py::test_cancelled_job_rejects_late_provider_result` 和 `tests/integration/test_http_sse_lifecycle.py::test_live_http_sse_cancel_disconnect_and_reopen`。
- 首次配置恢复：`web/e2e/first-use.spec.ts` 的“first use stays in one app-owned flow and resumes to a requested step”实浏览器用 Fake endpoint 通过；`tests/unit/test_first_use_progress_store.py` 覆盖配置记录恢复、损坏 fail-closed、原子写和并发。

这些映射只说明本轮执行并通过的离线测试场景；不代表 C01–C31 或完整产品验收通过。测试与断言没有变更，base→target 对照证明测试树零差异。

## 缺陷

未发现本次精简相关缺陷。历史 lint/deprecation/build advisory 如上保留。

## 注意事项 / 未测

`test:e2e` 自带截图写入默认目录 `.local/dev/frontend-a/current`。本轮运行后发现 8 张首配截图，已复制到 `.local/qa/ponytail-code/browser-artifacts`；默认目录保留，没有删除未知 ignored 文件。Git tracked 状态保持 clean。后续执行结果与 evidence manifest 记录该目录情况。

包装 smoke 只验证移位包 backend、空 PATH、静态 UI、认证边界、端口冲突和父管道退出清理；不代表真实用户安装、原生 UI 交互或公证。

## 证据

- 命令与实际退出码：[commands.tsv](evidence/2026-10-17-ponytail-code-qa/commands.tsv)
- 环境、构建身份、产物 SHA-256、限制：[manifest.json](evidence/2026-10-17-ponytail-code-qa/manifest.json)
- 完整合并 stdout/stderr 日志留在本独立 checkout 的忽略目录 `.local/qa/ponytail-code/logs/`；内部候选 App/DMG 留在 `.local/qa/ponytail-code/artifacts/`，未提交大产物。
