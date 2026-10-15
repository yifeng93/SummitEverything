# Milestone A 独立 QA 修复轮 1 报告

## 身份与固定版本

- QA：fresh 独立验收实例；日期：2026-10-15。
- 被测产品 SHA：`9c33a9dde3080fff3e3b3dd8a4193589ef52575f`。
- 初次失败产品 SHA：`9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad`；共同基线：`e84e9e5a56475a19f68ca1a684366fba7f9fee83`。
- 独立 checkout：`<QA_WORKTREE>`。
- 测试期间及结束时 `git rev-parse HEAD` 均为受测 SHA；`git status --short --untracked-files=all`、cached/working diff 均为空。tracked lock 未变化。
- 系统：macOS 27.0.1；Node v24.15.0；npm 11.12.1；Playwright 1.64.1；FastAPI harness 使用 Python 3.12.13。
- 本报告、独立 harness、临时 profile、浏览器结果、截图与命令日志均位于 `.local/qa/frontend-a-repair1/`。QA checkout 的 `node_modules`、构建输出与本地 `.venv` 为忽略文件。

## 范围及隔离

验收 A：共享基础、切片 3 首配合并、切片 9 设置对齐。按固定验收决议覆盖 Fake 默认、共享向导、工作库前置、profile/workspace 进度隔离、密钥处理、三张设置卡、危险确认、Markdown 共享组件和五档两主题页面矩阵。今日旧授权迁移属于 B，审批/今日全面整理属于 B，项目问答与阅读消费者接入属于 C，完整守卫和安装包属于 D。

所有材料为合成值。独立 FastAPI 测试运行离线 guard、使用新 profile、空 first-use defaults 和新临时工作库；浏览器路由只允许本机测试 origin。FastAPI manifest 中 `externalAttempts: []`，没有 provider smoke POST。未读取桌面材料、真实 Application Support、旧 App、Keychain 或任何真实秘密；没有真实 provider、OAuth、飞书或外网业务请求。

## 命令结果

| 项目 | 完整命令 | 结果与证据 |
|---|---|---|
| 安装依赖 | `npm ci`（`web/`） | PASS，exit 0；226 packages，0 vulnerabilities。日志 `logs/npm-ci.log`。 |
| 前端测试 | `npm --prefix web test -- --run` | PASS，exit 0；24 files，164 passed、8 todo。日志 `logs/npm-test.log`。 |
| 类型检查 | `npm --prefix web run typecheck` | PASS，exit 0。日志 `logs/typecheck.log`。 |
| lint | `npm --prefix web run lint` | PASS，exit 0；3 条 `react(set-state-in-effect)` warning，位置为 `src/App.tsx`、`src/components/ProjectsView.tsx`、`src/components/TodayView.tsx`。日志 `logs/lint.log`。 |
| 构建 | `npm --prefix web run build` | PASS，exit 0；Vite 生产构建完成。日志 `logs/build.log`。 |
| 离线浏览器 | `SUMMIT_E2E_EVIDENCE_DIR="$PWD/.local/qa/frontend-a-repair1/mock-evidence" npm --prefix web run test:e2e` | PASS，exit 0；Playwright 2/2。首配失败提示、步骤恢复/手动续接/完成、今日与设置 320/390/768/960/1280 × light/dark 无整页横溢。日志 `logs/e2e.log`，截图和测量 `mock-evidence/`。 |
| FastAPI + Fake | `cd web && env PYTHONPATH="$PWD/../scripts/offline_guard:$PWD/../src" UV_PROJECT_ENVIRONMENT="$PWD/../.local/qa/frontend-a-repair1/.venv" UV_OFFLINE=1 npx playwright test --config ../.local/qa/frontend-a-repair1/playwright.integration.config.ts` | PASS，exit 0；真实本机 FastAPI、Fake、一次性 session token、合成 workspace 的首配链 1/1。日志 `logs/fastapi-fake.log`；`fastapi-integration/fastapi-request-manifest.json` 记录本地 workspace/settings 请求、无外发尝试、无 provider smoke。 |
| F1–F3 独立浏览器复演 | `cd web && npx playwright test --config ../.local/qa/frontend-a-repair1/playwright.review.config.ts` | PASS，exit 0；3/3。独立正确预期断言、模拟 API 失败，不替代 FastAPI 集成。日志 `logs/f1-f3.log`；源码仅为 QA harness `harness/frontend-a-regressions.spec.ts`。 |

## 修复轮缺陷复测

| 项目 | 状态 | 复演与观察 |
|---|---|---|
| F1 缺少所选能力密钥 | PASS | 新 profile 无密钥且 Keychain 不可用时选择整理与问答：保存按钮 disabled，`title` 指出 DeepSeek API Key，输入框有 `aria-invalid` 和字段级提示；改填合成值后按钮仍 disabled，提示钥匙串不可用；没有 settings PATCH 或 credential PUT，canary 不进入浏览器存储或请求体。另以服务端已配置 DeepSeek 凭据的 profile 验证空密码不要求重填，且只提交配置、不 PUT 密钥即可进入下一步。 |
| F2 AI 单能力结果被总卡泛化 | PASS | Rerank 返回合成 502 后，逐项结果显示失败；随后 DeepSeek 成功，AI 总卡仍显示“有检查失败”，未检查的能力没有被宣称通过。仅 Rerank API Base URL 改变并保存后，Rerank 旧失败结果失效、DeepSeek 成功结果保留；卡片显示“部分已检查”。界面 DOM 未出现 `configStamp` 或合成 sentinel。两项 POST 各 1 次。 |
| F3 飞书状态读取失败覆盖最后成功值 | PASS | 本机只读状态先返回已授权，再于用户点击重新读取后模拟 503；卡片保留“已授权”和成功读取时间，明确提示本次读取失败、可能过时并提供重试。随后通过危险确认删除合成飞书应用密钥，唯一 DELETE 完成后卡片变为未配置、不再显示已授权。 |

初次 QA 报告中的 F1、F2、F3 均在固定新 SHA 上按正确预期复测通过。另检验已确认删除凭据清除旧缓存状态，结果符合预期。

## 交互与隔离边界

危险删除弹窗使用 `role=dialog`、`aria-modal=true`，默认焦点在取消按钮；Tab / Shift+Tab 在对话框内环绕，Esc 关闭并归还焦点。Esc 和取消均为 0 DELETE；双击确认仅 1 DELETE。Rerank 合成检查弹窗取消为 0 POST，双击确认仅 1 POST。各页面测试的外部 origin 记录为空。

初始自建 harness 曾有仅测试配置问题：外置 QA 配置的 Playwright 模块解析路径和 `webServer` 工作目录需要显式设为 `web/`；F1 saved-credential fixture 初次还启用了未测试的 Dashscope 能力；F2/F3 有过 status locator 严格匹配和 Feishu 初始读次数假设错误。以上均在固定 SHA 不变时修正 harness，最终复跑完整通过；不构成产品缺陷。集成测试配置和浏览器证据现均指向本 QA 目录。

## 五轴代码质量判断

- **正确性与规格一致性：PASS（A 离线范围）**。F1–F3、共享向导续接、FastAPI + Fake 首配和页面矩阵符合本轮 A 期望。产品中仍登记 8 个 todo，属于后续守卫/切片，未把它们计为已通过。
- **安全性：PASS（已测离线边界）**。密钥输入与失败关闭、无存储/请求泄漏、确认门和请求计数符合预期；本机测试 manifest 没有外发。真实 Keychain、provider、OAuth、飞书授权及账户权限均 NOT_RUN。
- **可读性与维护性：PASS（有 warning）**。逐能力结果在界面上分开呈现，F2 配置失配只淘汰相应检查结果。lint 有三条 effect 更新 warning，记录为维护风险，不阻断 A 验收。
- **架构：PASS（A 范围）**。实际 FastAPI + Fake 路径可完成首配；工作库/设置/飞书读取使用本机服务，UI/API 隔离 profile 与 workspace。Ask/PageReader 接入属于 C，未在 A 中判定。
- **性能与响应式：PASS（有限）**。Today 与 Settings 的五种宽度、两主题浏览器测量无 document/body 横向溢出。没有做慢网、压力、大数据或安装包性能测试，均 NOT_RUN。

## 门状态与风险

- **Milestone A 离线技术 QA：PASS**，等待 Sol 按协作约定核对固定 SHA、报告和适用门并作最终 gate 判断。
- **真实 provider / 真实 Feishu / OAuth / OS Keychain：NOT_RUN**。本轮未授权或要求真实连接，也没有对应真实凭据。
- **DMG / 正式安装与公证 / 五日试用 / 双机：NOT_RUN**，不是自动测试可覆盖的范围。
- **B、C、D：NOT_RUN / 尚未进入本轮**。完整 10 条全站守卫并未因此全部通过；8 个 todo 保留待后续切片。
- **风险**：lint 的三条 effect warning；真实外部服务与系统钥匙串生命周期没有由 Fake 证据验证。

## 下一步

由 Sol 审核本报告和固定 SHA，并判定 A 的离线技术 gate。F1–F3 本轮没有发现仍待修复的缺陷；真实连接、Keychain、安装交付和后续 B/C/D 仍按各自独立验收门处理。
