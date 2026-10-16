# Frontend B repair1 独立 QA

日期：2026-10-15。受测产品 SHA：`a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`。Checkout：`/Users/yifengstudio/.codex/worktrees/frontend-b-qa-repair1/SummitEverything`。最终 `git status --short --branch` 仅显示 `## HEAD (no branch)`；产品 checkout 固定，未改源码、tracked tests、配置或锁文件。证据均位于 `.local/qa/frontend-b-repair1/`。

## 结论

- **PASS — P1 Real scope 可核验。** 通过真实 FastAPI、隔离 workspace 和真实 intake 返回的合成 `item_id/source_id`，Real 预览展开后逐字显示服务器冻结的原件正文，并显示目标主线/项目、1 次请求上限及 2048 token 输出预算。改变底层主线选择后预览仍显示已捕获目标；实际发送的唯一 plan confirm body 与本轮 preview scope 完全相等。
- **PASS — scope fail-closed 与取消。** 将真实 preview 响应的 project_id 改为错误值时 UI 不开放确认；去掉 scope 时也不开放确认。取消真实预览只删除本机 plan；以上路径没有 plan confirm、没有 intake job、没有外网尝试。
- **PASS — P2 文件入口键盘可达。** Tab / Shift+Tab 实际到达两个隐藏 file input，父级按钮出现可见 3px 焦点框；Enter 为“选择多个文件”和“选择文件夹”各触发真实浏览器 filechooser。Escape 关闭导入抽屉并归还焦点。320/390/768/960/1280 × light/dark 的 20 张独立焦点截图均通过焦点与无水平溢出断言；关键窄屏截图已人工查看。
- **PASS — Fake 浏览器业务闭环。** 独立新 profile/workspace 上通过真实 FastAPI + Fake 完成记一句和文件导入、取消零 job、整理、冲突未决时阻止稿件确认、显式选择“暂时未决”、稿件/正式内容读取与确认、Fake 首次索引；没有外网请求，没有 Action confirm/execute 写入。明细见 `fake-integration/workflow-manifest.json`。
- **PASS — 基础 Web 检查。** npm ci、Vitest、typecheck、lint、build 退出码均为 0；离线 Playwright 2/2。
- **NOT_RUN — Python 661 测试与变异矩阵。** 本轮未重跑 Python：`613d453..a0ccad8` 后端 `src/tests/pyproject.toml/uv.lock` 无 diff。守卫①②④⑤⑧⑨⑩未在独立 QA 中重复做 mutation run；开发报告中的历史结果不当作本轮证据。
- **NOT_RUN — 真实 provider/飞书/OAuth/Keychain、用户材料、DMG/安装/公证、五日和双机。** 本轮全部使用离线 Fake、合成数据和 loopback；没有使用真实服务或秘密。

Sol 保留 B 最终 gate 决定。以上支持 P1/P2 与 B 核心离线闭环通过；未覆盖的广门与 C/D 事项保持 NOT_RUN，不据此宣称 Stage C 或产品整体通过。

## 命令与原始结果

| 命令 / 结果 | 退出码证据 |
|---|---|
| `npm ci --prefix web` — 226 packages，0 vulnerabilities | `npm-ci.log`, `npm-ci.exit` |
| `npm --prefix web test -- --run` — 25 files passed；180 passed、6 todo | `web-unit.log`, `web-unit.exit` |
| `npm --prefix web run typecheck` | `typecheck.log`, `typecheck.exit` |
| `npm --prefix web run lint` — exit 0；2 条 `set-state-in-effect` warning（App.tsx、ProjectsView.tsx） | `lint.log`, `lint.exit` |
| `npm --prefix web run build` — exit 0；JS chunk 571.29 kB，Vite 建议值为 500 kB | `build.log`, `build.exit` |
| `SUMMIT_E2E_EVIDENCE_DIR="$PWD/.local/qa/frontend-b-repair1/e2e" npm --prefix web run test:e2e -- --workers=1` — 首配 + viewport/theme 2/2 | `offline-e2e.log`, `offline-e2e.exit`；截图在 `e2e/` |
| `cd web && npx playwright test --config ../.local/qa/frontend-b-repair1/playwright.config.ts --workers=1` — 自建真实 FastAPI/Real scope + focus browser flow 1/1 | `real-scope-focus.log`, `real-scope-focus.exit`；harness、scope 和网络证据在本目录 |
| `cd web && npx playwright test --config ../.local/qa/frontend-b-repair1/fake-integration.config.ts --workers=1` — FastAPI/Fake 闭环 1/1 | `fake-integration.log`, `fake-integration.exit`；`fake-integration/workflow-manifest.json` |
| `git diff --check` — 无输出、exit 0；复核 `git diff 613d453..HEAD -- src tests pyproject.toml uv.lock web/package-lock.json` 无差异 | checkout 核验，无产品 diff |

两条前端自建 Playwright 配置和测试只在本 `.local/qa` 目录。Real scope harness 在 profile 中仅选择 Real mode 与启用 LLM，以允许离线范围预览；`SUMMIT_OFFLINE_GUARD_ACTIVE=1`，浏览器拒绝所有非 loopback 请求。有效 scope 确认请求到达本机一次性 plan ledger；测试在 `/api/v1/intake/jobs` 浏览器路由处截断后续提交，确认 body 与预览 scope 相同且只出现一次，故没有 provider 调用或真实 job。`valid-confirm-evidence.json` 保存脱敏合成 scope、confirm body 与截断的 job body；scope / target / request 记录见 `scope-network-evidence.json`。

## 风险与状态

- Web 测试仍有 6 个 todo，归属全站后续 C/D 范围；其存在不作为 B 功能通过证据。
- 本轮未执行守卫变异。现有 tracked SourceOrganizer tests 会覆盖范围/目标不匹配及 confirm payload 冻结，但不足以替代本轮完整变异矩阵。
- `web-unit`、`typecheck`、`lint`、`build`、`offline-e2e`、`real-scope-focus`、`fake-integration`：**PASS**。
- P1、P2：**PASS**。B 离线核心流程：**PASS**。Python/变异及真实集成、打包、长期/多机门：**NOT_RUN**。
- 缺陷：在本轮固定 SHA 上未复现已报 P1/P2；没有发现新的 P1/P2。

受测 SHA 结束复核仍为 `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`。tracked working tree clean；唯一新写内容为许可的 `.local/qa/frontend-b-repair1/` QA harness、日志和证据。
