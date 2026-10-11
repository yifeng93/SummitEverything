# Stage B 固定源码后端离线复验 — 576895f（2026-10-11）

**结论：PASS（仅限后端离线回归、独立刷新 / 传输反例和 Swift 编译）。** 固定源码 `576895f6983ca41cacbbad45a9075b97b9986189` 与前次 `fd2042385c4916598337239f5259b3ef1889372a` 的 `src`、`tests`、`web`、`scripts`、依赖锁和其他检查目标完全相同。唯一产品差异是 `native/Sources/SummitEverythingApp/App.swift` 的 `webURL` 增加末尾 `/`。本报告不判断实际原生窗口启动结果；UI/native 验收仍由独立 UI 验收者执行，整体候选不得仅凭本报告判 PASS。

## 固定身份与源码差异

- 精确源码 SHA：`576895f6983ca41cacbbad45a9075b97b9986189`，detached `HEAD`；checkout `/Users/yifengstudio/.codex/worktrees/qa-stage-b-luna-backend-576895f/SummitEverything`。
- 前一固定源码 SHA：`fd2042385c4916598337239f5259b3ef1889372a`。
- Git 逐目录 tree ID 核对确认 `src`、`tests`、`web`、`scripts`、`pyproject.toml`、`uv.lock`、`web/package-lock.json` 全部与 fd204 相同。完整源差异只有 `App.swift` 一处：`http://127.0.0.1:\(webPort)` 改为 `http://127.0.0.1:\(webPort)/`。本轮没有重跑 Web 45 项或静态全矩阵；这些结果仅按 fd204 相同目录树引用。
- Python 3.12.13 / uv 0.12.3 / Node v24.15.0 / npm 11.12.1。使用本 checkout 的 `.venv` 与按 lock 安装的 `web/node_modules`。

差异、目录 tree ID、lock/API 指纹、环境、历史 manifest 与 guard 检查见 [identity-audit.json](evidence/2026-10-11-stage-b-luna-offline-retest-576895f/identity-audit.json)。

## 检查结果

| 检查 | 结果 |
|---|---|
| `uv sync --locked --group dev` | PASS，exit 0 |
| `npm ci` | PASS，exit 0；只为后端 run-dev 集成用例安装已锁定的 Web 依赖 |
| 完整后端 `pytest -q -p no:cacheprovider` | **388 passed**，1 条既有 Starlette/httpx deprecation warning |
| 独立传输 / 存储故障 harness | **25 passed**，相同既有 warning |
| `swift build` | PASS，exit 0 |

完整 argv、环境和日志见 [check-results.json](evidence/2026-10-11-stage-b-luna-offline-retest-576895f/check-results.json)。首次没有 `web/node_modules` 时，run-dev 集成用例按产品设计以 exit 2 报告“Web dependencies missing”；该次 387/388 失败日志和结果保存在 `pytest-full-before-npm-ci.log` 与 `check-results-before-npm-ci.json`。安装 lock 指定的依赖后，未更改产品代码，完整重跑 388/388 通过；根因说明见 [setup-failure.log](evidence/2026-10-11-stage-b-luna-offline-retest-576895f/setup-failure.log)。

## 独立反例和隔离

独立复验使用真实 API、route、service、coordinator、vault、provider、lease 和传输生命周期；只替换 HTTP 外部边界与 `MemorySecretBackend`。25 项全通过，包含：未知 refresh 响应后的跨重启不重发、dispatch 前消费标记写入、标记写失败零 HTTP、轮换写入失败后的旧 token 不重发、成功轮换后只接受不同的新 token、legacy 缺字段兼容，以及 refresh marker 的严格 JSON Boolean 解析。字符串、数字、对象、null 均按损坏凭据处理且零 refresh HTTP；真实 Boolean `true` 仍按已消费 token 拒绝。

全部 Python 测试 / 运行命令设置 `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src"`。负控制证明非 loopback socket、真实 DNS 与 OS Keychain 构造被拒绝；实际检查结束时 transfer worker 数为 0。真实 Feishu exchange / refresh、DeepSeek、embedding、rerank 都为 **0/1**，真实任务写入为 **0**，未访问真实身份、业务资料或凭据。

本轮逐项重算 13 个历史 manifest（共 336 个证据项；两个 flat UI map 分别 42 与 29 项），并从前一个独立 QA checkout 只读核验 fd204 最终报告 manifest 的 30 项证据与报告 SHA；全部无 mismatch。细节见身份审计 JSON。原 7f / 8b 历史 FAIL 与中间 P2 报告保持原样。

## 范围结论

此固定 SHA 的后端离线回归、刷新生命周期 / 故障安全路径与 Swift 编译通过。Web45、lint、typecheck、API types、mypy、Ruff、lock 和 package build 没有在该 SHA 重跑；相关源码目录和 lock 与 fd204 的逐树相同，故仅可引用 fd204 报告的结果。浏览器与原生实际窗口、readiness alert、真实 provider / 账号 / scope、OS Keychain、真实模型质量、DMG、五日试用、双机及 M3–M5 均不由本报告判定。整体 Stage B 候选仍等待独立 UI/native 验收结论。

本 QA checkout 仅新增本报告、独立 harness 和 evidence；没有改产品实现或 lock，没有 commit、push 或 merge。当前报告及 evidence 的 SHA-256 manifest 为 [manifest.json](evidence/2026-10-11-stage-b-luna-offline-retest-576895f/manifest.json)。
