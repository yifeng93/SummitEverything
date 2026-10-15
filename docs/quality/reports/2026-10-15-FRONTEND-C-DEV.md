# 前端 UX 里程碑 C DEV handoff

日期：2026-10-15。产品代码固定 SHA：`1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c`（分支 `codex/frontend-ux-20261015`）。本报告是开发者自测记录，不是独立 QA 或 Sol gate；fresh QA 待开始。

## 交付范围

C 完成 Projects 列表与独立完整详情，详情返回保留搜索、筛选、排序、滚动和焦点。状态只由归档标记、明确进度或已确认 overview 决定；详情五区不从未确认内容猜摘要，时间线只列真实关联页面并使用可信业务日期。项目 CRUD、归档/恢复、overview 自由 Markdown 与版本冲突、推进日志和导入入口继续可用。

Ask 以提问为首屏主区，历史、索引和个性化内容折叠；范围预览、历史引用 hash、流式请求状态、取消、回答模式、角色/记忆确认与删除确认沿用既有边界。索引操作转到审批页，不重复创建写入器。

Reader 与 Ask/Projects 共用安全 Markdown 渲染；内部 wiki/相对链接解析到唯一真实页面，链接目标需有 id/hash 映射，歧义或缺失目标不可点击且可读。拒绝绝对路径、越界和危险 scheme；外部链接加安全 rel；代码区域、raw HTML 禁用、引用式链接与版本确认有测试。Reader 返回保留来源页/问答上下文，过期引用仍要求用户确认。

## 实际验证

以下命令均在 `web/` 执行；完整原始日志及退出码 sidecar 存于未跟踪的 `.local/dev/frontend-c/`：

| 检查 | 结果 | 证据 |
|---|---|---|
| `npm test` | PASS：25 files，190 passed，4 todo，exit 0 | `gates/web-test-freeze.log` / `.exit` |
| `npm run typecheck` | PASS，exit 0 | `gates/web-typecheck-final.log` / `.exit` |
| `npm run lint` | PASS，exit 0；保留既有 App.tsx 与 ProjectsView.tsx 两条 React warnings | `gates/web-lint-final2.log` / `.exit` |
| `npm run build` | PASS，exit 0；Vite 提示单一 chunk 584.80 KB | `gates/web-build-final.log` / `.exit` |
| focused contract + C component tests | PASS：6 files / 50 tests | `gates/guard-restored-green.log` / `.exit` |
| Fake FastAPI + isolated synthetic workspace E2E | PASS：1/1，exit 0；确认合成页、索引、问答、引用打开、CAS 更新后旧引用提示；外部尝试 0 | `gates/fastapi-flow-restored.log` / `.exit`；`fastapi-integration/frontend-c-flow-manifest.json` 与截图 |
| responsive/theme Playwright | PASS：5 widths × 2 themes × 4 views = 40 screenshots；横向溢出为 0，正文最低字体 15px；exit 0 | `gates/view-matrix-final.log` / `.exit`；`view-final/measurements.json` 与 PNG |
| UI guard mutation representatives | PASS：7 个预期变异均使测试以 exit 1 失败；恢复实现后 focused test exit 0 | `mutations/guard-*.log` / `.exit` 与上述 restored green |
| `git diff --check` | PASS | 执行后工作树检查结果；产品提交前干净 |

7 条变异具体覆盖：①标识泄漏、②业务中文、④Projects 加载/空态、⑤跨项目移动确认、⑥ Markdown 链接安全、⑧ Ask 提问优先顺序、⑨ Reader 导航不发 provider/索引计划。它们是 C 相关代表用例，不等于全站守卫已收口。

项目/UI 具体测试包括：独立详情返回列表筛选状态、加载与空态区分、确认 overview/显式进度状态、无猜日期、项目增改与归档、overview 确认和页面移动确认；Ask 首问顺序、索引路由、提交错误/断流不自动重试、引用版本更新提示及删除确认；Markdown code/inline code、相对路径、引用式链接、歧义与危险链接；Reader 正文、版本警告、移动/关联与来源返回。

## 保留给 D 的全站守卫

本产品 SHA 仍有 4 条 todo，未通过重命名或删测试规避：

- ① 全站普通正文、details、title 与 aria-label 的 ID/hash/path/raw JSON 泄漏扫描（诊断导出除外）。C 的跨页集成检查只覆盖项目/阅读/问答范围。
- ④ Today、Approval、Ask 在请求未完成时不得显示空态；C 仅覆盖 Projects 的 loading 与 confirmed-empty。
- ⑤ 全站删除、断开、覆盖、移动等危险动作的逐类取消零写入/确认一次写入。C 覆盖项目归档/恢复和 Reader 跨项目移动的部分场景。
- ⑥ SSE 每个 chunk 的未闭合 Markdown 标记中间态都不显示为源码，并验证终态 DOM 与静态 Markdown 一致。C 已测代码保真和最终渲染一致，但未证明每种中间态。

② 中文用户业务名称在 `web/src/ui-contract.render.test.tsx` 的“项目、阅读和问答的普通文案使用中文名称且不泄漏内部标识”用例中覆盖；⑨同文件用例断言项目/阅读/问答导航期间无 provider 或索引计划写请求。二者只说明上述 C 用例，不代表全站其它视图。D 必须继续做全局验证。

## 未运行 / 限制

- Python 661 未重跑；本切片未修改后端、检索、prompt 或 `domain/content.py`。
- 真实 provider、OAuth、飞书、Keychain、用户真实材料、DMG/安装、公证、长期五日、双机、发布：NOT_RUN。
- 全站守卫余项按上节明确归 D。DEV 自测不代替 fresh QA；QA 应在独立 checkout 对固定产品 SHA `1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c` 验收，文档后续提交不属于该产品 SHA。
