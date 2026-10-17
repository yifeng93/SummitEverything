# 初验报告 — Frontend usability

- 被测源码 SHA：`0957df2b871970d626fb2745048a6e79bad4defb`（测试前、测试后 `git rev-parse HEAD` 相同）
- QA checkout：`/Users/yifengstudio/.codex/worktrees/frontend-usability-qa-initial/SummitEverything`
- QA 起始/结束 tracked 工作树：`git status --short` 均为空。临时浏览器、Playwright profile、FastAPI workspace、harness、截图和日志均在 `.local/qa/frontend-usability-0957/`（ignored）。运行集成测试时短暂创建的 `.local/dev` symlink 已清除。
- 核心范围：前端及交互可用性、真实 FastAPI/Fake 单稿确认、合成 Mock 高风险边界。未调用真实模型、飞书服务、外部网络、用户材料或凭据。

## 结果

### PASS

- `cd web && npm ci`：exit 0；安装使用本 QA checkout 的 `web/node_modules`。
- `cd web && npm test -- --run`：exit 0，26 个文件、235 项测试通过。
- `cd web && npm run typecheck`：exit 0。
- `cd web && npm run lint`：exit 0；保留两条已知 warning（`src/App.tsx`、`src/components/ProjectsView.tsx` 的 `react/set-state-in-effect`）。
- `cd web && npm run build`：exit 0；有 Vite 主 chunk 约 602 KB 提示。
- `cd web && npm run api:types`：exit 0；重新生成的 `src/api/generated.ts` 未造成 tracked diff。
- `cd web && npm run test:e2e`：exit 0，first-use 与 viewport 共 2/2 通过。最终干净复跑日志无 Vite Unhandled；覆盖 320/390/768/960/1024/1280/1440 宽度、浅/深主题、4 会议/6 任务默认 3/5、1280×800 首屏、空组展开/返回恢复及横向溢出检查。Chromium 使用本地 Playwright 安装。
- `cd web && npm run test:e2e:integration`：exit 0，1/1 通过，真实本机 FastAPI + Fake。日志 `logs/web-e2e-integration.log`。
- 独立黑盒 `node .local/qa/frontend-usability-0957/focused-browser.cjs`：exit 0。1280×800 下验证快速记录成功回执的返回 `item_id` 与 `source_id` 精确导航；同名旧材料未选中；已确认正式页存在而 `/index/status.pages=0` 时首次索引计数为 1；Markdown 渲染；取消离开确认后 dirty 内容保留；正文 PATCH 不含 `conflict_resolutions`，最终确认 POST 才带所选冲突结果；无模型/索引 job/外部请求，console errors 0。修正了 harness 的回执夹具，使 `index_update` 使用契约枚举字符串 `"not_enabled"`，并断言界面回执文案。日志 `logs/focused-browser-final.log`，manifest `focused-browser-manifest.json`，截图 `focused-exact-id-initial-index.png`。
- 独立真实 FastAPI/Fake 多稿 harness `node .local/qa/frontend-usability-0957/multidraft-fastapi.cjs`：exit 0。POST `/intake/jobs` 实际返回两个 `draft_ids`；仅确认一个后，另一稿仍 pending，只有确认稿对应正式页；动作候选 0、任务写入 0、项目 `progress_version=0` 且进度为空。没有任务/进度越权写。manifest 中记录完整 ID、请求和错误响应来源。启动首次配置前的探测响应单列如下。
- 独立本机文件批次 Mock `node .local/qa/frontend-usability-0957/file-batch-mock.cjs`：exit 0。第一批 `good.md`=201、`failed.md`=400、`unknown.md`=503 各 POST 一次；“继续整理”只读取 `good-source-qa-1`。第二批 `retryable.md` 首次 400，用户点击“重试失败项”后第二次 POST=201；`unknown-2.md`=503 仍只有一次 POST；回执只读取 `retry-source-qa-1`。无外部请求/pageerror。4 条 Chromium console resource errors 分别对应夹具明确返回的 400/503，页面显示失败/未知状态，属于已处理的 API 错误响应。
- 反例检查：将相同的独立浏览器行为检查指向旧基线 `6ecfc75f18f3c61154648093830901cd7b8c73d7`，在缺少“保存原文/返回 ID 继续”行为处按预期失败（exit 1）。日志 `logs/baseline-counterexample.log`。此证据说明新增检查能识别旧行为缺口。
- `git diff --check 6ecfc75..0957df2`：exit 0。抽查差异为前端页面布局/焦点流、导入/保存目标、稿件确认和相关测试；未见 API schema、后端业务或依赖变更。UI-contract allowlist：`TodayView:.slice(0,8)` 删除；`App.tsx:page_id` 3→2；`ApprovalView:content_sha256` 1→2；`ApprovalView:page_id` 4→17。增加的 page_id 命中与正式页打开/保存回执等详情可达路径对应；运行时 `ui-contract.render.test.tsx` 保留内部 ID/hash/path/JSON 防泄漏约束，单测通过。未发现删减这类防泄漏检查。

### FAIL（质量门）

- `web/src/components/ApprovalView.tsx:151` 与 `:214` 新增两处 `// oxlint-disable-next-line react/set-state-in-effect`。前者包围按外部 `refreshEpoch` 同步审批数据的 effect；后者包围目标 ID 数据就绪后的提示状态更新。局部用途可解释，但两处均抑制本次代码的静态质量信号、且开发交接未列明这些豁免。按已批准质量门要求，本轮初验将其记为 FAIL，要求修复轮移除禁用并保持行为、不得用另一条 suppression 代替；本 QA 未修改产品代码。源码 diff 中可核对。

### 运行时错误观察（不作为产品缺陷；证据状态 UNVERIFIED）

- 早期工具输出曾出现三条 Vite `[Unhandled error] TypeError: Cannot read properties of undefined (reading 'filter')`，定位到 `ApprovalView.tsx:157` 的 `intents.data?.items.filter(...)`。该内容没有保存进 QA raw log，故不能把历史工具输出当成可独立复核证据。
- 归因发现：早期文件批次 harness 漏配 `/action-intents?limit=20`，fallback 返回裸数组 `[]`，违反 `ActionPage` `{items,next_cursor}` 响应契约；之后已修 harness。修正后的 B 场景 pageerror=0；修正后完整 `npm run test:e2e` 2/2 干净复跑，日志没有 Unhandled。更准确说这是受测夹具错误的高度可能解释，但由于早期三条消息未留 raw，旧观测本身标为 UNVERIFIED；不列产品 FAIL。

## 探测响应、失败与处理归类

- 真实 FastAPI/Fake 多稿流在空工作库首次进入时：`GET /api/v1/workspaces/current` 两次 HTTP 409；`GET /api/v1/first-use/progress` 一次 HTTP 404。均为初始化前的只读探测，页面随后进入五步首次配置并成功创建本机测试工作库；之后的未处理 JS/pageerror=0，其他非预期失败响应=0。响应 URL、方法、状态、后续写请求与结果见 `logs/multidraft-fastapi-final.log`。
- B 文件导入夹具的 400/503 是故意注入：界面捕获为“导入失败”/“结果未知”，unknown 不重发；resource error console 行是这些 HTTP 失败的 Chromium 表示，不是未处理 JS。
- `pageerror`：A、B 均 0。A 初始化探测 409/404 独立列出，不混入业务失败。B 4 条 HTTP 错误已由 UI 状态处理，不混称未处理错误。

## NOT_RUN / UNVERIFIED

- 真实飞书授权/导入、真实模型运行时及其 runtime metadata（UNVERIFIED）、真实外部服务/凭据/用户材料：NOT_RUN。
- macOS 原生应用完整人工检查、DMG 安装/升级/隔离环境验收、五日稳定性、双机状态隔离：NOT_RUN。本轮不重跑这些独立真实门。
- Chrome DevTools MCP 未配置；DOM、console、网络请求和截图使用项目 Playwright/本地 Chromium 观察。
- 后端 Python 独立回归未运行；本次变更面向前端，且真实 FastAPI/Fake browser integration 1/1 已跑。

## 原始证据路径

QA 根目录：`/Users/yifengstudio/.codex/worktrees/frontend-usability-qa-initial/SummitEverything/.local/qa/frontend-usability-0957/`

- 日志：`logs/web-unit.log`、`web-typecheck.log`、`web-lint.log`、`web-build.log`、`web-api-types.log`、`web-e2e-viewport.log`、`web-e2e-integration.log`、`focused-browser-final.log`、`multidraft-fastapi-final.log`、`file-batch-mock.log`、`baseline-counterexample.log`
- Harness：`focused-browser.cjs`、`multidraft-fastapi.cjs`、`file-batch-mock.cjs`
- Manifest/截图：`focused-browser-manifest.json`、`focused-exact-id-initial-index.png`、`multidraft-97316/manifest.json`、`multidraft-97316/one-confirmed-one-pending.png`、`file-batch-mock-manifest.json`、`file-batch-mock-final.png`
