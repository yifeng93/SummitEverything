# 前端 UX 里程碑 B Developer 报告

日期：2026-10-15。固定产品提交：`613d453ab1a47e2f0bfe78d685fb90817f70f4cc`（分支 `codex/frontend-ux-20261015`）。本报告只记录 Developer 自测；**fresh QA pending，Sol 尚未判门，不声称里程碑 PASS**。后续报告、路线图和进度账本提交均为 docs-only，不改变此产品 SHA。

## 交付范围

审批页按来源、稿件、正式内容、索引、外部动作分成五组，各自表达加载、空、错误、最近成功与重试。检查并应用只汇总已选事项，确认仍逐类独立；Real 索引只有 plan 与 acceptance 请求完整成功才开放确认。来源整理保留原件，历史未知来源按 `unknown` 展示；稿件冲突要求选择明确结果，正式正文仍走 expected-hash 原子确认 API。外部动作先独立确认，结果未知只对账或记录用户提供的结果；Real 任务写禁用。

今日页按会议、待办任务、有内容时才显示的行动建议、工具、收件箱呈现；会议只读，行动建议不等于批准。记一句具稳定意图幂等键并保留输入原始字节；Enter 遵守中文输入法 composing 状态。workspace / auth 身份决定缓存边界，导航切页不触发重读，身份变化才失效并阻止旧异步回流。导入支持多文件、目录、拖放逐文件失败反馈及飞书分页选择；日志思考弹窗复用 JournalView。导入、日志、确认与选择汇总弹窗有固定边界、焦点陷阱、Escape 关闭和焦点归还，导入忙时不丢弃状态。

修改逐页规格，并补充隔离 FastAPI + Fake 浏览器流程、中文/内部ID业务文案断言、Today cache 与 quick-note 断言。没有改动 `content.py`、检索或 prompt。全部运行只使用合成 Fake、一次性 session token、隔离 profile/workspace；不接触真实 OAuth、Keychain、飞书、用户桌面库、付费模型或安装应用。

## 自测结果

| 检查 | 结果 | 原始证据 |
|---|---|---|
| guarded Python | **PASS**，661 passed，exit 0。后端自 `1cb3d8a` 后未改，复用本轮原始结果 | `.local/dev/frontend-b/pytest-guarded.log`、`pytest-guarded.exit` |
| OpenAPI / TS 生成 | **PASS**，`npm --prefix web run api:types` exit 0，tracked 生成物未变 | `api-types.log`、`api-types.exit` |
| Web 单元 / 组件 | **PASS**，24 files、176 passed、6 todo，exit 0 | `full-unit.log`、`full-unit.exit` |
| TypeScript | **PASS**，`npm --prefix web run typecheck` exit 0 | `post-review-typecheck.log`、`post-review-typecheck.exit` |
| Oxlint | **PASS**，exit 0；保留 2 条既存 `set-state-in-effect` warning（`App.tsx`、`ProjectsView.tsx`） | `post-review-lint.log`、`post-review-lint.exit` |
| Vite build | **PASS**，exit 0；提示 JS chunk 568.73 kB 超过 500 kB 建议值 | `post-review-build.log`、`post-review-build.exit` |
| 离线 Playwright | **PASS**，2/2，exit 0；首配流程 + 五宽度/双主题浏览矩阵 | `final-e2e-complete.log`、`final-e2e-complete.exit` |
| 固定边界/焦点矩阵 | **PASS**，五宽度×双主题；三类弹窗均验证 fixed 边界、焦点陷阱、Escape 与归还；1/1，exit 0 | `dialog-matrix-bounds.log`、`dialog-matrix-bounds.exit`；截图索引见下节 |
| FastAPI + Fake B 闭环 | **PASS**，1/1，exit 0；来源两条（file / quick_note）、字节相等、origin_kind、取消零写、organize → 冲突待决阻止确认 → 选择「暂时未决」→ 正式正文读回 → index；外部请求 0、外部动作执行/确认写 0 | `fastapi-integration-conflict.log`、`fastapi-integration-conflict.exit`、`fastapi-integration/workflow-manifest.json` |
| Python fixture 与 diff | **PASS**，ruff check、format check、`git diff --check` exit 0 | `python-fixture-static.log`、`python-fixture-static.exit` |
| 守卫变异 | **PASS**，①②④⑤⑧⑨⑩均有故意破坏的红证据并恢复为绿；exit 索引见 raw README | `guard-*.log`、`guard-2-*-final.log`、`dialog-matrix-bounds.log`、`final-e2e-complete.log` |

当前保留 **6 个 todo**：渲染守卫 ②/④/⑤/⑥/⑨ 是项目/问答/阅读或全站范围，分别归入后续 C/D；剩余一个源码扫描型守卫①的跨所有页面完整位置断言归 D。B 已有的审批/今日和导入业务用例覆盖，不代表上述全站 todo 关闭。QA 应核对固定 SHA 和产品范围，不将 todo 或两条 lint warning 解释为通过。

## 截图矩阵

Playwright 产物在 `.local/dev/frontend-b/viewport/`，`screenshot-manifest.json` 列出所有文件。人工查看了联系表：Today、Approval、Import Drawer、Journal Dialog、Approval selection summary；每类均为 320/390/768/960/1280 × light/dark，共 50 张。测试实际断言 Today/Approval 横向溢出为零，并断言三类弹窗在视口内、焦点进入、焦点循环、Esc 关闭与归还。联系表 `contact-{today,approval,import,journal,selection}.jpg` 与原始 PNG 均留在 `.local`。截图是浏览器合成 UI，不代表真实安装应用验收。

## Fresh QA 交接

QA 固定检查 `613d453ab1a47e2f0bfe78d685fb90817f70f4cc`，不得在受测目标上并行写产品。请独立验证五组审批确认隔离、按 workspace/auth 的缓存失效与竞态、quick-note 原件字节/稳定幂等、中文输入法确认、冲突正文资格、Real index preview fail-closed、Import/Journal 多文件失败与弹窗语义，以及独立可重复的真实 FastAPI + Fake 闭环。**已知需判定的范围呈现疑点：Real 索引范围确认弹窗当前只显示计划标题、类型与一句占位范围提示，没有展开 `pending.scope` 明细；本报告不把“范围确认足够清楚”列为 PASS，请 QA 以实际 UI 与 API 返回范围对照判断。**重点审阅 raw index 中的历史失败与最终成功对应关系。QA 需自行决定未测/失败项；Developer 自测不能代替 QA verdict。

明确未测：真实 provider、Feishu OAuth/资料/任务写、真实 Keychain、真实用户材料、付费预算、打包 App、安装/公证、五日与双机。产品主 SHA 后没有代码变更；如果发现缺陷，修复须产生新产品 SHA 并由全新 QA 复验。

详细命令、退出码、旧失败与最终通过证据路径见[raw evidence 索引](evidence/2026-10-15-frontend-b-dev/README.md)。
