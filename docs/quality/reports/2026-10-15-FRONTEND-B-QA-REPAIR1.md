# 前端 UX 里程碑 B repair1 独立 QA 与 Sol gate

日期：2026-10-15。固定受测产品 SHA：`a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`。QA worktree：`frontend-b-qa-repair1`，产品 checkout 结束时 clean，产品源码、tracked tests、配置与锁文件未修改。

## 结论与范围

Sol 核对独立 QA 报告、原始退出码、Fake/Real-scope 网络证据与 clean SHA 后，判定 **B 适用离线核心与 repair1 修复 PASS**。此结论只覆盖 B 的离线技术范围，不代表全站、Milestone C/D、Stage C 或产品整体 PASS。

- P1 Real 来源整理冻结范围：展示合成原件正文、目标、请求上限和输出预算；底层选择变化不改 captured scope；错目标或缺 scope fail closed；确认体与预览一致。取消只删除本机 plan，没有 confirm、intake job 或外网请求。
- P2 文件入口键盘可达：两个 file input 可由 Tab/Shift+Tab 到达，焦点可见；Enter 打开原生文件选择器；Escape 关闭并归还焦点。五档宽度 × 深浅主题共 20 张焦点截图通过断言，关键窄屏截图已人工查看。
- Fake 离线浏览器闭环：真实 FastAPI + Fake、全新 profile/workspace，完成随手记与文件导入、取消零 job、整理、冲突时阻止稿件确认、明确暂时未决、正式内容确认和 Fake 首次索引；未发现外网请求或外部动作写入。
- Web 单测 **180 passed / 6 todo**；typecheck、lint、build 均 exit 0，lint 有 App.tsx 与 ProjectsView.tsx 两条 `set-state-in-effect` warning，bundle 571.29 kB；离线 Playwright 2/2。
- Python 661 测试与 QA 独立守卫变异未运行；后端 `src/`、`tests/`、`pyproject.toml`、`uv.lock` 相对父 SHA 无差异。
- 真实 provider、飞书、OAuth、Keychain、用户材料、DMG/安装/公证、五日和双机均 **NOT_RUN**。

初始 B 产品 SHA `613d453ab1a47e2f0bfe78d685fb90817f70f4cc` 的首次 QA **FAIL**（QA-001 Real 来源预览正文/目标，QA-002 文件入口焦点）仍保留在[初始 QA 归档](evidence/2026-10-15-frontend-b-initial-qa/README.md)，本报告不改写其状态。修复轮使用 1/2。

## 命令索引

所有下列命令在固定产品 SHA 上由 QA 执行，退出码均为 0，除有数量说明外：

| 命令 | 结果 |
|---|---|
| `npm ci --prefix web` | 226 packages，0 vulnerabilities |
| `npm --prefix web test -- --run` | 25 files；180 passed、6 todo |
| `npm --prefix web run typecheck` | exit 0 |
| `npm --prefix web run lint` | exit 0；2 条既有 warning |
| `npm --prefix web run build` | exit 0；JS chunk 571.29 kB |
| `SUMMIT_E2E_EVIDENCE_DIR="$PWD/.local/qa/frontend-b-repair1/e2e" npm --prefix web run test:e2e -- --workers=1` | 离线 Playwright 2/2 |
| `cd web && npx playwright test --config ../.local/qa/frontend-b-repair1/playwright.config.ts --workers=1` | Fake Real-scope / focus 浏览器流程 1/1；外部请求拒绝 |
| `cd web && npx playwright test --config ../.local/qa/frontend-b-repair1/fake-integration.config.ts --workers=1` | FastAPI/Fake 闭环 1/1 |
| `git diff --check` | exit 0；受测 checkout clean |

逐条退出码、原始日志、scope network、Fake workflow 与截图仍在 QA 原件目录；索引及 SHA-256 摘要见[脱敏 evidence 索引](evidence/2026-10-15-frontend-b-repair1-qa/README.md)。原件不移动、不修改。

