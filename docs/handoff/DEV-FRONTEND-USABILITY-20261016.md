# DEV 交接：今日与审批可用性（2026-10-16）

状态：实现和开发者自测完成，独立 QA 尚未开始。此报告不作验收签字。

## 被测版本与提交

- 固定受测产品源码 SHA：`0957df2b871970d626fb2745048a6e79bad4defb`。
- 提交链（从旧到新）：产品基线 `6ecfc75f18f3c61154648093830901cd7b8c73d7` → 已批准计划 `42f8872` → 第一段产品 checkpoint `431fc95f696e660befef7b129c97900edbec185d` → 固定产品提交 `0957df2b871970d626fb2745048a6e79bad4defb`。
- 分支：`codex/frontend-usability-20261016`；实现只发生在隔离 worktree `~/.codex/worktrees/frontend-usability-20261016/SummitEverything`。
- 本报告、规格和状态入口是在产品 SHA 固定后追加的文档更新。它们的 docs-only commit 是本报告提交之后的 repo HEAD；不得将该文档 tip 误报成已测产品源码 SHA。最终 HEAD 由本报告所附 task handoff 一并报告。

## 行为变化

- 今日宽屏并列显示左侧会议/任务与右侧记事/材料导入；窄屏按日程再记录纵向排列。会议默认 3 条，任务默认 5 条；展开全部和旧分页仍可用。首屏非空 fixture 同时展示会议首条、任务首条、记事输入与导入入口。
- 随手保存和批量导入按服务返回的准确 `item_id` 接续。已 processing/reviewing 的来源继续已有整理任务或稿件，不重复创建 job。来源详情展示原文、归属、整理状态和本次实际稿件。
- 审批五组保持固定顺序；有待处理事项的组默认展开，空组默认收起但可展开，状态在专注页打开与返回间保留。已有 confirmed 正式页面且索引为 `not_ready` 时，首次索引计入一项并展开；此判断使用服务端正式页状态，不读索引页数推断未索引页面，也不复制信任/资格算法。真空库仍折叠。
- 稿件以 Markdown 阅读；编辑、来源和改动差异按需打开。冲突选择未由 PATCH 持久化时明确提示“未提交”，只在最终确认时生效。版本冲突按 API 状态/code 识别并在载入新版本前保护本地编辑。确认保留真实 `index_update` 与 page ID，并可打开准确正式页或继续下一份。
- 离开审批、打开正式页、切换工作库和浏览器关闭会保护未保存正文；审批数据刷新不覆盖编辑内容。无需后端 API 或新依赖。

## 开发者检查

所有日志位于隔离 worktree 的 `.local/dev/2026-10-16-frontend-usability/final/`；截图和合成 Fake 流程证据位于相邻 `browser/viewport-final/` 与 `integration/`。退出码写入各日志末尾。

逐项命令、状态、退出码、日志、红绿与截图路径索引见 [DEV manifest](evidence/frontend-usability-dev-manifest-20261016.json)。

| 结果 | 命令 | 真实结果 | 日志 |
|---|---|---|---|
| PASS | `cd web && npm test` | 235 passed，26 files，exit 0 | `unit-final-3.log` |
| PASS | `cd web && npm run typecheck` | exit 0 | `typecheck-final-2.log` |
| PASS | `cd web && npm run lint` | exit 0；2 条 React warning（`App.tsx` 首配同步、`ProjectsView.tsx` 状态同步），与本轮修改前的基线数量相同；Approval 新增 warning 已消除 | `lint-final-2.log` |
| PASS with warning | `cd web && npm run build` | exit 0；Vite 提示主 JS bundle 约 602.45 KB，高于 500 KB 建议线 | `build-final-2.log` |
| PASS | `cd web && npm run api:types` | OpenAPI 导出与 TS 生成 exit 0，生成文件无 diff；本轮未改后端契约 | `api-types-final.log` |
| PASS | `cd web && SUMMIT_E2E_EVIDENCE_DIR=../.local/dev/2026-10-16-frontend-usability/browser/viewport-final npm run test:e2e` | 2/2 passed，exit 0；包括首配与 viewport/theme/折叠/首屏可见性检查 | `e2e-final-2.log` |
| PASS | `cd web && SUMMIT_E2E_EVIDENCE_DIR=../.local/dev/2026-10-16-frontend-usability/browser/integration-final npm run test:e2e:integration` | 1/1 passed，exit 0；本地 FastAPI + Fake + 独立合成工作库验证记录、导入、来源整理、稿件确认、精确正式页、首次索引与动作隔离 | `integration-rerun-8.log` |
| PASS | `git diff --check`、`python3 -m json.tool web/src/ui-contract.allowlist.json`、确认 `web/e2e/fixtures/empty-first-use-defaults.json` 保持 `{}` | 全部成功 | exit 0；日志 `repo-check-final-3.log`；fixture 变更为无 diff |

Playwright Node 在本机输出 `NO_COLOR` 与 `FORCE_COLOR` 环境变量提醒；未影响退出码。产品基线由 Sol 检查过的原始日志为 vitest 222/222 和 typecheck exit 0；不将基线数据计入当前 SHA 的测试结果。

## 保留的失败与 red/green 证据

未删除或覆盖早期失败日志。最终规格明确后，以下失败分别对应待修代码或旧测试对折叠交互/视口的陈旧预期，后续修正均使用新日志：

- `unit-final.log` exit 1：3 个定向断言失败；最终全套 `unit-final-3.log` 235/235 exit 0。
- `viewport-final-2.log`、`viewport-final-3.log` exit 1：初始脚本要求整块日程全部塞进 800px，后来按用户明确口径改为检验会议首条、任务首条、记事输入和导入入口都在首屏；`viewport-final-4.log` exit 1：紧凑布局前任务首条仍在首屏下方。最终矩阵 `viewport-final-5.log` exit 0 且本轮再跑 `e2e-final-2.log` exit 0。
- `integration-final.log` exit 1：旧断言假设已完成正式组永远展开；`integration-rerun-6.log` exit 1：空动作组应默认折叠；`integration-rerun-7.log` exit 1：索引预览按钮需要显式点击。最终复演已改为按真实折叠状态主动展开空组、验证首次索引组计数/展开，再点击预览，`integration-rerun-8.log` exit 0。
- TDD 红/绿证据保留：`.local/dev/2026-10-16-frontend-usability/phase-1-focused.log` exit 1，随后 `phase-1-green.log` exit 0；`phase-2-followup-focused.log` exit 1，随后 `phase-2-followup-focused-green-2.log` exit 0。未删除请求、确认、外部写入隔离或内部 ID 可见性断言。

## 视觉和行为证据

- 非空 1280×800 今日首屏：`.local/dev/2026-10-16-frontend-usability/browser/viewport-final/today-1280-800-nonempty.png`。图中会议标题和首条、任务标题和首条、记事输入及“导入材料”按钮同时可见。**不要用** `.local/dev/2026-10-16-frontend-usability/browser/viewport/today-1280-800-nonempty.png`：那是旧截图。
- Approval 320/390/768/960/1024/1280/1440 × light/dark：`.local/dev/2026-10-16-frontend-usability/browser/viewport-final/`。
- Fake API 完整审批复演图：`.local/dev/2026-10-16-frontend-usability/integration/approval-after-fake-flow.png`；非空今日保存与导入图：`.../integration/today-nonempty-capture.png`；外部写入/域名核对 manifest：`.../integration/workflow-manifest.json`（实际外部写入为空，外部 origin 尝试为空）。

## 限制与 QA 交接

- 未运行独立 QA、变异验收、Python 全套、真实飞书/模型/Keychain、真实材料、安装包、双机或生产连接；均为 NOT_RUN。本轮不声称独立验收通过。
- Lint 两条既有 warning 和 Vite bundle 大小 warning 需 QA 复核；Playwright 脚本使用的是本地合成内容与 Fake API。
- 建议 fresh QA 在固定 SHA `0957df2b871970d626fb2745048a6e79bad4defb` 复演：`cd web && npm test`、`npm run typecheck`、`npm run lint`、`npm run build`、`npm run api:types`、`npm run test:e2e`、`npm run test:e2e:integration`；重点抽查 1280×800 非空首屏，4/6 条默认 3/5 展示与展开/分页，空组折叠/持久展开，首次确认页触发的索引待处理数量，切库/页面导航/beforeunload dirty guard，冲突选择时效，同名精确 ID，多稿单选确认，真实 `index_update`/page ID 回执，外部写 0 与 UI 内部 ID 不外泄。
- QA 必须固定并报告所测产品源码 SHA；不要把后续 docs-only HEAD 当受测源码 SHA。Sol 负责最终 PASS/FAIL/BLOCKED/NOT_RUN 判定。
