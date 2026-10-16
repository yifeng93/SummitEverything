# Frontend C 独立 QA 报告

- 被测产品 SHA：`1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c`
- Checkout：`/Users/yifengstudio/.codex/worktrees/frontend-c-qa-initial/SummitEverything`
- 验收范围：C 项目列表/详情、问答流式与引用、Reader Markdown/引用闭环；全局 D 守卫与真实外部/安装门不在本轮 PASS 声明内。
- 固定性：验收开始与结束的 `git rev-parse HEAD` 均为上述 SHA；最终 `git status --short` 为空，`git diff --check` exit 0。仅有 Git 忽略的安装、构建、缓存和 `.local/qa/frontend-c-initial` 证据。

## 结果

| 场景 | 结果 | 证据 |
|---|---|---|
| `npm ci` | PASS，exit 0；锁文件未改 | `gates/npm-ci.log`, `gates/npm-ci.exit` |
| Web 单元测试 | PASS，25 files；190 passed、4 todo，exit 0 | `gates/web-test.log`, `gates/web-test.exit` |
| TypeScript | PASS，exit 0 | `gates/web-typecheck.log`, `gates/web-typecheck.exit` |
| Lint | PASS，exit 0；显示 App.tsx 与 ProjectsView.tsx 两条 React effect warning | `gates/web-lint.log`, `gates/web-lint.exit` |
| 生产构建 | PASS，exit 0；Vite 提示 JS chunk 584.80 KB | `gates/web-build.log`, `gates/web-build.exit` |
| FastAPI + Fake 引用闭环 | PASS，Playwright 1/1；创建合成内容、索引、检索、打开引用、更新正文后提示旧 hash 并显示当前内容；外部请求 0 | `gates/fastapi-flow.log`, `fastapi-integration/frontend-c-flow-manifest.json`, `fastapi-integration/citation-updated-page.png` |
| 项目/Reader/问答视口 | PASS，Playwright 1/1；320/390/768/960/1280 × light/dark × 4 页面共 40 图，测量横向溢出 0，基准正文字号 15px；目视复核 320px 项目详情浅色、320px Reader/Ask 深色及 1280px 项目详情深色 | `gates/view-matrix.log`, `view-matrix/measurements.json`, `view-matrix/*.png` |
| 项目返回状态 | PASS，独立 QA 浏览器复演 1/1；搜索/状态筛选保持，滚动位置恢复，返回后焦点回到原项目行，外部请求 0 | `gates/project-return-state-final.log`, `playwright.project-state.config.ts`, `e2e/project-state.spec.ts` |
| C 组件边界 | PASS，4 files / 31 tests；项目状态、详情摘要不读代码围栏、未猜日期、归档确认取消、Ask Real scope 取消零 query、SSE 错 request id/seq/双终态拒收且不重试、Markdown 相对/引用链接安全、Reader 版本边界 | `gates/focused-c-tests.log`, `gates/focused-c-tests.exit` |
| 项目关联日志 | PASS，隔离 FastAPI TestClient；写入合成项目日志后，页面关联正确且 `progress` / `progress_version` 不变 | `test_project_journal_progress.py`, `gates/project-journal-progress.log` |
| 网络隔离 | PASS；FastAPI 闭环、视口复演和项目返回浏览器复演的 `externalAttempts`/外部请求计数均为 0 | 对应 FastAPI manifest、视口测量结果及 Playwright 用例断言 |

首次项目状态浏览器试跑因 QA fixture 把审批动作响应伪造成数组而崩溃；补齐 `{items: [], next_cursor: null}` 后重跑通过。原始试跑保留于 `gates/project-return-state.log`，不计作产品缺陷。

## 未测与风险

- D 保留的四条全站守卫（①全站标识泄漏、④Today/Approval/Ask 未完成加载态、⑤全站危险动作单飞、⑥每个流式 chunk 的 Markdown 中间态）本轮明确 **NOT_RUN / 留 D**；C 页面局部证据不代表全站通过。
- Python 661、QA 变异矩阵未重跑；本切片未改后端或内容信任门。独立日志进度不变用例是聚焦场景，不代表全量 Python 回归。
- 本轮 Fake 服务、临时 profile/workspace、浏览器拦截全部为合成离线场景。真实 provider、OAuth、飞书、Keychain、真实业务资料、DMG/安装、公证、五日与双机均 **NOT_RUN**。
- 项目列表返回滚动/焦点用独立浏览器 mock API 复演；项目日志不改进度用隔离 FastAPI 复演。两者分别验证 UI 与后端边界，不声称同一 UI+真实路由端到端日志流程已跑。
- 无发现 C 范围产品缺陷。构建 chunk 与 lint warning 记录为风险提示，不阻断本轮通过。

## Gate 状态

- C 离线前端可复验场景：**PASS**（限本报告实际执行范围，Sol 保留最终 gate 判定）。
- 全产品/Stage C/发布验收：**NOT_RUN**。
- 真实外部服务与打包/长期/双机门：**NOT_RUN**。

下一步：Sol 核对本报告及 `.local/qa/frontend-c-initial/gates/` 原始退出码、manifest 和截图后决定是否接受 C 离线门；其余明确范围进入 D 或独立真实验收。
