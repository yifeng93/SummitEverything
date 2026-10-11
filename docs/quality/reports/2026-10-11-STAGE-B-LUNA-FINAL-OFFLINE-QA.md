# Stage B 最终固定源码离线后端 QA — 2026-10-11

**结论：PASS（仅限本报告的固定 SHA 离线后端 / 静态检查范围）。** 在独立 checkout 上复核了源码 `fd2042385c4916598337239f5259b3ef1889372a`。未发现未关闭的 P0/P1/P2 离线后端缺陷。UI 验收者另在该 SHA 报告原生冷启动 readiness alert，因此整体候选入口仍待修复后用新 SHA 复验；本报告不签发整体候选 PASS。浏览器 / 原生 UI、真实 provider、OS Keychain、真实模型质量及安装交付不属于本报告的 PASS 范围。

## 固定身份和隔离

- 源码 SHA：`fd2042385c4916598337239f5259b3ef1889372a`，detached `HEAD`，父提交 `386c8b2cb5dfd61b8e53bc3c10fe509f8f22cbb5`。
- 独立 checkout：`/Users/yifengstudio/.codex/worktrees/qa-stage-b-luna-final-backend/SummitEverything`。
- 独立环境：Python 3.12.13、uv 0.12.3、Node v24.15.0、npm 11.12.1；`.venv` 与 `web/node_modules` 均在该 checkout。
- 所有 Python 测试 / 运行命令均设置 `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src"`；负控制确认 guard 拒绝非 loopback socket、真实 DNS 和 OS Keychain。HTTP 只由 MockTransport 或有限数字 loopback 提供；凭据只用 MemorySecretBackend 与合成值。运行结束时 live transfer workers 为 0。
- Feishu exchange / refresh、DeepSeek chat、Model Studio embedding / rerank 实际请求均为 **0/1**；真实远端任务写为 **0**。未读取真实身份、资料、日历、任务或 Keychain。
- 产品 `src`、`tests`、`web`、`native`、`scripts`、`pyproject.toml`、`uv.lock` 和 `web/package-lock.json` 无 diff；两次 OpenAPI 类型生成一致，生成文件与提交版本相同。`uv lock --check` 通过。

身份、guard 负控制、源码树、lock 与 API 指纹见 [identity-audit.json](evidence/2026-10-11-stage-b-luna-final-offline-qa/identity-audit.json)。最新原生 readiness DEV 的 101 项源码哈希与本 SHA 全部匹配。13 个历史证据 manifest 及其可寻址报告均逐字节匹配；两个扁平 UI SHA map 已逐条验证 42 项与 29 项，均无 mismatch。第一次 audit parser 只识别 `files` envelope，曾把这两个 flat map 计为 0 项；[audit-correction.log](evidence/2026-10-11-stage-b-luna-final-offline-qa/audit-correction.log) 记录修正，[identity-audit-first-pass.json](evidence/2026-10-11-stage-b-luna-final-offline-qa/identity-audit-first-pass.json) 保留首次输出，最终的 [identity-audit.json](evidence/2026-10-11-stage-b-luna-final-offline-qa/identity-audit.json) 对两种格式均逐项重算。中间 strict-marker DEV 源码快照相对最终 SHA 只有后续原生 readiness 修改的 `native/Sources/SummitEverythingApp/App.swift` 不同，其 18 项历史证据 manifest 仍匹配。旧 SHA 上的 FAIL 报告未改写。

## 检查结果

完整 argv、退出码和日志见 [check-results.json](evidence/2026-10-11-stage-b-luna-final-offline-qa/check-results.json) 与相邻日志。

| 检查 | 结果 |
|---|---|
| `uv sync --locked --group dev`、`npm ci` | PASS，均 exit 0 |
| 全后端 `pytest -q -p no:cacheprovider` | **388 passed**，1 条既有 Starlette/httpx 弃用 warning |
| 独立边界与存储故障 harness | **25 passed**，1 条相同弃用 warning |
| Ruff check / format、`mypy src` | PASS，exit 0 |
| `uv lock --check` | PASS，exit 0；lock 未变 |
| `uv build --no-build-isolation` | PASS，exit 0；在独立 venv 安装 hatchling 后构建，guard 正常加载 |
| OpenAPI 类型生成连续两次 | PASS，均 exit 0；输出幂等且无生成文件 diff |
| Web | **45 passed**；typecheck、lint、production build 均 exit 0；保留 3 条既有 React effect lint warning |
| Swift build | PASS，exit 0 |
| `git diff --check` | PASS，exit 0 |

独立 harness 来自既有 7f / 8b QA oracle 与 storage-fault cases，存放在 [harness](evidence/2026-10-11-stage-b-luna-final-offline-qa/harness/)。只替换 HTTP 和 SecretBackend，route、service、coordinator、vault、lease、文件读写与应用实现保持真实。

## 刷新消费标记与故障复验

原 7f 候选 QA-B-01/P1 的 FAIL 仍保留在原报告；8b 中间提交的 QA-B-02/P2 也仍作为历史记录。最终 SHA 的当前行为由本轮新独立测试复核：

- 未知 refresh 响应后重启，不再次发送同一 refresh token；本地消费保留 set-then-raises 时零 HTTP，重启仍阻止重发。
- 消费保留写入失败（包括存储先写后抛错）不会派发 HTTP。轮换 token 的持久化失败后，重启不重发旧 token；若新 token 已写入，即使写确认丢失，重启只使用那个不同的新 token。
- 真正的 Boolean `false` 及旧凭据缺少新字段的兼容路径可以刷新；HTTP dispatch 前读取到已持久化 `true`，成功轮换写入的新 token 标记回到 `false`。
- `null`、数字、对象及字符串（包括 `"false"` / `"true"`）均返回 `credential_unreadable` 且新增 refresh HTTP 为 0；真正 Boolean `true` 返回 `token_expired` 且 HTTP 为 0。不存在字符串或数字到 Boolean 的宽松转换。

原 7f 的其他 8 项独立边界反例、8b 的轮换与凭据故障项都在本轮回归通过。完整 25 项通过日志见 [independent-boundaries.log](evidence/2026-10-11-stage-b-luna-final-offline-qa/independent-boundaries.log)。

## 离线范围判定

- SB-01/02、C04/C10/C11/C13：PASS（离线）。canonical qualification、stale cache、原件 / draft / helper 排除、邻页和最终 citation 复核由本轮 388 项后端回归覆盖。
- SB-03、C14：PASS（离线）。取消后不再触发后续 provider call，deadline 结束后无后台 HTTP；不代表实时外部费用或 M3 历史 UI。
- SB-04：PASS（离线）。本地合格候选数量、wire 上限和 rerank identity 由回归覆盖。
- SB-05/06/07：PASS（离线已测范围）。授权代次、logout/callback、配置切换与旧 provider 租约路径通过；不是跨设备验收。
- SB-08 / B02/B03 refresh 路径：PASS（本 SHA 离线）。重启、消费保留和合法轮换均经新 harness 覆盖。OS Keychain 仍 NOT_RUN。
- SB-09：PASS（API/组件自动检查范围）。未在本报告做真人浏览器操作。
- SB-10/11：PASS（离线）。业务模型门、一次性合成 smoke 账本、请求/响应边界、deadline、HTTP 200 业务错误拒绝及 client 释放由后端回归覆盖。
- SB-12/13、B01：离线契约与记录 PASS；真实账号权限、真实协议交换和 R03 质量评定 NOT_RUN。官方协议矩阵中明确禁用项仍受禁用门保护。
- B04：PASS（离线适配与门控范围）；真实模型结果、质量、用量和费用 NOT_RUN。
- B05/B06：本报告确认固定 SHA 的自动后端、Web 构建和 Swift 编译范围 PASS。实际浏览器、原生窗口和启动延迟 UI 未在本 checkout 执行，记为 **NOT_RUN（本报告）**；另一独立 UI 验收者在该 SHA 发现原生冷启动 readiness alert，整体候选门保持待修复和新 SHA 复验。

R2–R4、Sol closure、refresh restart、strict-marker 与 root DNS/TLS/HTTP transport 故障路径均由最终全后端 suite 执行通过，相关真实测试见 `tests/integration/test_stage_b_r2_regressions.py`、`test_stage_b_r3_regressions.py`、`test_stage_b_r4_*.py`、`test_stage_b_sol_closure.py`、`test_stage_b_refresh_restart.py`、`test_qualified_retrieval.py` 与 `test_feishu_real_gate.py`。这只证明合成边界下当前实现符合离线契约。

## 未测范围

真实 Feishu code exchange / refresh / scope / 身份 / 数据访问、真实 LLM / embedding / rerank 可用性与质量、费用、OS Keychain 拒绝 / 锁定 / 重启、DMG / 干净机器、M3–M5、五个实际工作日、双机往返及真实任务读写均 **NOT_RUN**。任务写仍因缺少独立结果证明而禁用；真实业务操作不属于本轮 QA。

QA checkout 只新增本报告、独立 harness 与 evidence，未修改产品实现 / lock，未 commit、push 或 merge。当前报告的 manifest 位于 [manifest.json](evidence/2026-10-11-stage-b-luna-final-offline-qa/manifest.json)。
