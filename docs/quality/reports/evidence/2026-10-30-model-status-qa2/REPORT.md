# 独立 QA 报告：模型调用状态修复第 1 轮

## 固定目标与结论

- 产品 SHA：`1e0347401de170919a526b6027f73e35430396be`
- 基线 SHA：`f63d0debc7c7f4c5839c575dd6dcee657225495a`
- 独立 checkout：`/Users/hanwenbo/.codex/worktrees/model-status-evidence-qa2/SummitEverything`（detached HEAD；源码和 tracked tests 未修改）
- 结论：**PASS（本轮指定门）**

## 检查结果

| 检查 | 结果 | 退出码与证据 |
|---|---|---|
| `tests/integration/test_model_call_status.py` | 6 passed | 0；`logs/test_model_call_status.log`、`.exit` |
| 全部 `tests/integration/test_provider_settings_api.py` | 15 passed | 0；`logs/test_provider_settings_api.log`、`.exit`。其中 unavailable Keychain 用例通过，返回 503 且没有回退写入或凭据泄露。 |
| `tests/unit/test_local_retrieval_model.py` | 5 passed | 0；`logs/test_local_retrieval_model.log`、`.exit` |
| SettingsView cards/test/regressions 三文件 | 25 passed | 0；`logs/settingsview-vitest.log`、`.exit` |
| `npm run typecheck` | PASS | 0；`logs/typecheck.log`、`.exit` |
| Vite + Playwright 合成 API 浏览器检查 | PASS | 0；`logs/browser-status.log`、`.exit` |

环境复用了 `/Users/hanwenbo/ai/SummitEverything/.venv` 与 `web/node_modules`（QA `web/node_modules` 为指向共享依赖的 symlink）；Python 测试设置 `PYTHONPATH` 指向本 QA checkout 的 `src`。没有安装依赖，没有调用真实 API、Keychain、付费模型或主工作库。浏览器插件不可用，使用仓库 Playwright 和独立 Vite `127.0.0.1:5194`，所有 `/api/v1/**` 均由脚本合成。

### 浏览器证据

- 成功状态：打开设置后显示「已就绪」「最近调用成功」「本机可用」；刷新并重新打开设置后仍显示已就绪。截图：[browser-success-ready.png](browser-success-ready.png)
- 本机模型未准备：保留 DeepSeek 最近成功状态，但 embedding/rerank 显示「本机模型未准备」，没有绿色就绪/可用状态。截图：[browser-unprepared.png](browser-unprepared.png)
- 本机能力 disabled：显示「已配置，未启用」，没有「本机可用」。截图：[browser-disabled.png](browser-disabled.png)

首轮 harness 故障原因已记录在首轮报告。本轮仅修正 QA fixture：`/action-intents` 返回真实分页结构 `{items: [], next_cursor: null}`，之后三种状态及刷新/重开检查通过；没有改产品代码或 tracked tests。

## key replacement 语义复核

`test_credential_replacement_hides_old_success_and_unknown_without_usage_is_not_success` 通过：换 DeepSeek 凭据前的成功记录在替换后变为 `state=none`、`has_success=false`。实现仍在真实凭据写入前递增 generation，使旧成功绑定失效；增加的 `vault.has()` 预检查只让不可用 Keychain 在创建 generation 文件前失败，不改变凭据替换后的失效语义。对应不可用 Keychain API 用例也通过。

详细退出码及日志位于本目录 `logs/`。本次未跑全量测试、未调用真实服务/模型，也未做安装包验收。
