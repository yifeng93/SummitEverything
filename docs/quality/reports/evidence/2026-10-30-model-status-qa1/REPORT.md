# 独立 QA 报告：本机模型调用状态

## 固定目标

- 产品 SHA：`24305e89fa41db41267fcf7a6363c5578b9a2272`
- 基线 SHA：`f63d0debc7c7f4c5839c575dd6dcee657225495a`
- 独立 checkout：`/Users/hanwenbo/.codex/worktrees/model-status-evidence-qa/SummitEverything`
- QA 日期：2026-10-30
- 结论：**FAIL**。候选新增一项 Keychain 失败路径回归；具体修复交 Developer。浏览器验收 BLOCKED，需后续固定新 SHA 的 QA 重跑。

## 执行环境

- Python：共享 `/Users/hanwenbo/ai/SummitEverything/.venv/bin/python`，所有测试用 `PYTHONPATH=<QA checkout>/src`，未安装或改依赖。
- 前端：复用主仓库 `web/node_modules`，TypeScript typecheck 使用 QA checkout 源码。
- 浏览器：QA checkout Vite 在 `127.0.0.1:5194` 返回 HTTP 200；Playwright 通过合成 API 路由运行。未调用真实 API、模型、Keychain 或主工作库。
- 源码 diff 已相对基线审查：本轮增加 acceptance ledger 的只读快照、DeepSeek 凭据代次和 smoke 结果持久化、Settings 状态摘要与卡片状态映射。本轮未改源码或 tracked tests。

## 定向检查

| 检查 | 结果 | 证据 |
|---|---|---|
| `tests/integration/test_model_call_status.py` | PASS，6 passed，exit 0 | `model_call_status.log` / `.exit` |
| `tests/unit/test_acceptance_plan_ledger.py` | PASS，6 passed，exit 0 | `acceptance_plan_ledger.log` / `.exit` |
| `tests/unit/test_provider_smoke.py` | PASS，3 passed，exit 0 | `provider_smoke_unit.log` / `.exit` |
| `tests/unit/test_local_retrieval_model.py` | PASS，5 passed，exit 0 | `local_retrieval_model.log` / `.exit` |
| 合成 DeepSeek smoke API：`test_limited_deepseek_smoke_is_synthetic_and_one_shot`、`test_failed_smoke_attempt_consumes_its_authorized_slot` | PASS，2 passed，exit 0 | `provider_smoke_api.log` / `.exit` |
| SettingsView cards/test/regressions 三文件 | PASS，25 passed，exit 0 | `frontend.log` / `.exit` |
| `npm run typecheck` | PASS，exit 0 | `typecheck.log` / `.exit` |

所有测试实际命令均为 `PYTHONPATH="<QA checkout>/src" /Users/hanwenbo/ai/SummitEverything/.venv/bin/python -m pytest -q <case>`，前端为 `web/node_modules/.bin/vitest run src/components/SettingsView.cards.test.tsx src/components/SettingsView.test.tsx src/components/SettingsView.regressions.test.tsx`。TypeScript 使用 `cd web && npm run typecheck`。

## FAIL：不可用 Keychain 失败关闭回归

执行 `tests/integration/test_provider_settings_api.py::test_unavailable_keychain_fails_closed_without_file_fallback`：

- 候选 SHA：exit 1。`PUT /api/v1/credentials/deepseek` 返回预期 503，但目录扫描断言对 profile 下的目录调用 `Path.read_text()`，抛出 `IsADirectoryError`。候选新建的 credential generation 状态路径触发此扫描路径。
- 基线 SHA：exit 0，同一测试 1 passed。
- 因此该用例不是基线已有失败；这是候选回归。没有删除或修改用例。
- 证据：`keychain-regression-candidate.log` / `.exit`、`keychain-regression-baseline.log` / `.exit`。基线 detached checkout 位于 `.local/qa/model-status/baseline-worktree`。

## 浏览器黑盒：BLOCKED

已启动 QA Vite（`127.0.0.1:5194`，HTTP 200），Playwright 拦截 `/api/v1/**` 并提供合成设置、最近调用成功及本地状态。壳页启动时，未覆盖的审批 API 被通用 fixture 错误地回为数组，React 在 `ApprovalView` 读取 `intents.data.items` 时异常，页面未形成可操作界面，设置导航定位超时。没有成功验证成功状态刷新/重开、本地模型未准备或 disabled 状态，也没有生成截图。浏览器脚本退出 1，日志见 `browser.log` / `.exit`，脚本为 `browser-status.mjs`。这是本轮 harness fixture 不完整导致的 BLOCKED，不能据此判定 UI 产品行为 PASS 或 FAIL。

## 交接文档不一致

候选内 `docs/handoff/LATEST-IMPLEMENTATION.md` 仍标注固定源码短 SHA `a46e1b2b`，与本轮指定并实际检出的完整 SHA `24305e89fa41db41267fcf7a6363c5578b9a2272` 不同。本轮按委托的完整 SHA 验收；文档一致性待 Developer 更新。

## 未覆盖边界

真实 DeepSeek 请求、真实 Keychain、真实工作库、真实 API 和 SSE 生命周期均未执行。SSE 边界不在本次审查范围；调用成功只代表 provider 返回完整响应，不表示浏览器收齐所有流帧。未跑全量测试、未构建或验收安装包。
