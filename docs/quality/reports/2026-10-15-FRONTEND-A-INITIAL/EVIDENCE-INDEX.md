# 前端 A 初次 QA 证据索引

初次被测产品提交为 `9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad`，基线为 `e84e9e5a56475a19f68ca1a684366fba7f9fee83`。独立 QA 判定 **FAIL**，缺陷为 F1 必填密钥按钮仍可提交、F2 单项检查成功使 AI 总卡误报通过、F3 飞书状态刷新失败丢失最近成功授权状态。

本目录中的 [`QA-REPORT.md`](QA-REPORT.md) 是 QA 原报告逐字复制，复制时用 `cmp` 验证一致。`harness/` 中两份规格文件也是 QA 初始版的未修改副本，仅包含合成设置、Fake/本机 API 路由和模拟凭据状态。它们用于追溯初次红证据，不代表当前修复版的验收；修复版的红绿 harness 保存在开发 worktree 的 `.local/dev/frontend-a/repair1/red-harness/`。

原始 QA 报告、测试输出、截图和 FastAPI 证据保留在原 QA worktree，没有覆盖或移动：

`/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything/.local/qa/frontend-a-initial/`

[`INITIAL-EVIDENCE-MANIFEST.json`](INITIAL-EVIDENCE-MANIFEST.json) 给出 47 个原始报告、harness、Playwright 输出、截图、测量数据及 FastAPI 证据文件的 SHA-256 与大小。manifest 明确排除 QA 专用 `.venv` 和运行时 profile/workspace；这些不是产品材料。

初次原始证据主要包括：

- `mock-evidence/`：今日与设置页五档 × 两主题截图、向导步骤/错误态截图和布局测量。
- `fastapi-evidence/`：真实 FastAPI + Fake 首配截图及本机 API 请求 manifest。
- `playwright-review-results/` 与 `playwright-wizard-results/`：设置交互、密钥边界和向导错误行为结果。
- `playwright-mock-results/` 与 `playwright-results/`：离线 UI 与隔离 Fake 集成测试结果。

初次报告保留其原始结论、命令结果与限制。修复轮 1 的测试与证据另见 [`../2026-10-15-FRONTEND-A-DEV-REPAIR1.md`](../2026-10-15-FRONTEND-A-DEV-REPAIR1.md)；该报告不代替 fresh QA。
