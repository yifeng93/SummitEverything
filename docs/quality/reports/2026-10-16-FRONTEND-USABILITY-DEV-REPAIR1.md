# 今日与审批可用性 DEV 修复轮 1（2026-10-16）

状态：代码修复、自测与提交完成，等待全新独立 QA。Developer 不作验收签字。本轮是最多两次自动修复中的第 1 轮。

## 被测版本与初验

- 初验产品 SHA：`0957df2b871970d626fb2745048a6e79bad4defb`。
- 修复轮 1 产品 SHA：`d9f49c1fc1b2dc787b21e3f2bd47662de3d1e715`；文档只改动另成 docs-only commit，最终文档 tip 在本报告交接时单独列出，不作为受测产品 SHA。
- 分支：`codex/frontend-usability-20261016`；隔离 worktree：`/Users/yifengstudio/.codex/worktrees/frontend-usability-20261016/SummitEverything`。
- 初验 QA 的行为复演为 PASS；Sol 初验门判 FAIL，唯一质量门失败是 `ApprovalView.tsx` 两处本轮新增 `oxlint-disable-next-line react/set-state-in-effect` 违反已批准的质量门。未披露是额外的透明度问题，披露本身不会让 suppression 符合门限。原报告与 evidence 未修改：[Sol 初验报告](2026-10-16-FRONTEND-USABILITY-SOL-INITIAL.md)、[QA 初验报告](evidence/2026-10-16-frontend-usability-initial/REPORT.md)。

## 修复内容

移除了两处 lint suppression。刷新 effect 现在在异步边界开始工作，并对每个 refresh epoch 做取消保护；各资源仍各自完成并更新，不因一个慢请求而阻塞其他分组。目标路由在数据就绪后异步解析，使用 route identity 避免旧目标的延迟焦点回调。来源详情使用请求序号保护，旧详情不会覆盖新目标；仅新目标/详情请求作废旧详情，因此已处理目标后的隐藏页 refresh epoch 不会丢掉一个仍在加载的来源详情。

改动只涉及 `web/src/components/ApprovalView.tsx` 与 `web/src/components/ApprovalView.test.tsx`。新回归覆盖 refresh epoch 旧响应晚到、旧详情响应晚到以及目标已处理后 refresh epoch 期间详情继续完成；原有未就绪目标、精确 ID 定位、焦点/返回和 dirty guard 测试继续保留。没有 API、依赖或 lint 规则变更，也没有用 suppression 替换 suppression。

## 开发检查

日志根目录：`.local/dev/2026-10-16-frontend-usability/`。日志保留原始命令输出；实际退出码同时记录在 [repair-1-check-status.json](../../handoff/evidence/frontend-usability-dev-repair1-status-20261016.json)，不得从日志尾部推断退出码。

| 结果 | 命令 | 退出码 | 原始日志与观察 |
|---|---|---:|---|
| PASS | `cd web && npm test -- --run src/components/ApprovalView.test.tsx` | 0 | `.local/dev/2026-10-16-frontend-usability/repair-1-focused-final.log`，20/20。第一轮红测见 `repair-1-focused-red.log`，1 个旧 epoch 覆盖最新目标的失败。 |
| PASS | `cd web && npm test` | 0 | `.local/dev/2026-10-16-frontend-usability/repair-1-unit-final.log`，26 files、239/239。 |
| PASS | `cd web && npm run typecheck` | 0 | `.local/dev/2026-10-16-frontend-usability/repair-1-typecheck-final.log`。 |
| PASS with warnings | `cd web && npm run lint` | 0 | `.local/dev/2026-10-16-frontend-usability/repair-1-lint-final.log`。保留 `src/App.tsx:138` 与 `src/components/ProjectsView.tsx:62` 两条既有 `react(set-state-in-effect)` warning；ApprovalView 无 warning 或 suppression。 |
| PASS with warning | `cd web && npm run build` | 0 | `.local/dev/2026-10-16-frontend-usability/repair-1-build-final.log`。已有 Vite bundle 体积建议提示仍存在；本轮产物主 JS 为 603.32 kB，初验产物为 602.45 kB。 |
| PASS | `cd web && npm run test:e2e` | 0 | `.local/dev/2026-10-16-frontend-usability/repair-1-e2e-final.log`，2/2。Playwright 输出本机 `NO_COLOR`/`FORCE_COLOR` 提醒。 |
| PASS | `cd web && npm run test:e2e:integration` | 0 | `.local/dev/2026-10-16-frontend-usability/repair-1-e2e-integration-final.log`，1/1，本地 FastAPI Fake 集成。 |
| PASS | `git diff --check` | 0 | 产品代码提交前执行，命令状态见 status JSON。 |

本轮未运行 `npm run api:types`（没有 API schema 或后端变更）、Python 全套、真实服务、真实材料或安装包。此前的 1280×800 非空今日截图与 Fake API 流程截图可复用，它们对应未修改的 UI 行为；QA 应在新固定 SHA 复演新增异步行为。

## QA 交接

Fresh QA 必须固定复验修复轮 1 产品 SHA `d9f49c1fc1b2dc787b21e3f2bd47662de3d1e715`，不要用 docs-only tip 代替受测产品 SHA。复演 `cd web && npm test`、`npm run typecheck`、`npm run lint`、`npm run build`、`npm run test:e2e`、`npm run test:e2e:integration`；重点重放：refresh epoch A 延迟后 epoch B 与最新目标先完成、旧结果不能覆盖最新来源；旧来源详情响应不能覆盖当前目标；目标已处理后在隐藏页刷新时来源详情仍能完成；目标数据未就绪时不能提前清除目标；原来的精确 ID、dirty 保护、焦点/返回行为保持。Lint 不得重新引入 suppression 或减少守卫。

验收 verdict 与是否 PASS 由 Sol 根据 fresh QA 固定 SHA 的证据判定。本报告不是独立 QA 或 Sol gate 结论。
