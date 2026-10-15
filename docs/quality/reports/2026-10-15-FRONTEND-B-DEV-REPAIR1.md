# 前端 UX 里程碑 B Developer 报告 · 修复轮 1

日期：2026-10-15。固定产品 SHA：`a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`，父产品 SHA：`613d453ab1a47e2f0bfe78d685fb90817f70f4cc`。本报告只记录 Developer 实测；**fresh QA 尚未验收，Sol 尚未判门，不声称 B PASS**。该产品 SHA 固定后只做文档/evidence，不再改产品。

首次 QA 对父 SHA 判 **FAIL**：QA-001 是 `SourceOrganizer` 的 Real 来源整理预览未显示服务器冻结的 outgoing 原件正文与可读目标；QA-002 是 Import Drawer 隐藏的 1×1 文件选择控件获得焦点时，外观上看不到焦点。首次报告、命令结果、脱敏 harness 与截图见[初次 QA 归档](evidence/2026-10-15-frontend-b-initial-qa/README.md)。

## 修复行为

Real 来源整理预览现在先校验服务端返回的冻结 scope 与本次所选原件、operation、主线、项目及整理类型一致，再显示并确认该 scope。目标中文名在请求前捕获；随后修改选择器不会改变弹窗、acceptance confirmation 或 `/intake/jobs` 所用的目标。范围明细展示服务端 `outgoing_inputs` 中每个原件的完整原文及可读来源名，原文以纯文本节点呈现，不执行其中的 HTML 或指令；同时显示 plan 请求上限与 scope 输出上限。未知主线/项目、目标不匹配、缺字段或配置读取失败都会阻止打开确认流程。Fake 首次整理也展示捕获的主线、项目和来源归属。

Import Drawer 的两个文件选择入口在隐藏 input 获得键盘焦点时，通过 `:focus-within` 在可见 label 上显示高对比焦点环。原生 input 仍可 Tab 聚焦，并用 Enter/Space 打开原生多文件/文件夹选择。已有的焦点陷阱、Escape 关闭和关闭后焦点归还保持通过。

没有新增 API，也未触碰后端、内容信任门、检索或 prompt。Real scope UI harness 使用一次性 session token、隔离 Fake FastAPI profile/workspace 和全外网阻断；没有触发 provider。Fake 业务闭环来自独立 FastAPI + Fake 测试。

## Developer 自测

| 检查 | 结果 | 原始证据 |
|---|---|---|
| SourceOrganizer 回归 | **PASS**，4/4 | `evidence/2026-10-15-frontend-b-repair1/logs/source-unit-final.log` |
| Web 完整单测 | **PASS**，25 files、180 passed、6 todo | `.../logs/vitest-final.log` |
| TypeScript | **PASS**，exit 0 | `.../logs/typecheck-final.log` |
| Oxlint | **PASS**，exit 0；仍有 2 条既存 warning（App、ProjectsView effect 状态更新） | `.../logs/lint-final.log` |
| Vite build | **PASS**，exit 0；chunk 571.29 kB，保留 >500 kB 提示 | `.../logs/build-final.log` |
| Offline Playwright | **PASS**，2/2，串行执行 | `.../logs/web-e2e-serial-pass.log` |
| FastAPI + Fake 业务闭环 | **PASS**，1/1；收件、整理、冲突稿选择与确认、索引、正式页读回；无外部动作 | `.../logs/fake-fastapi-pass.log` |
| Real SourceOrganizer 冻结范围 / 取消 | **PASS**，同 QA 范围 harness 1/1；显示正文、目标和预算；取消后零 intake job、零 external attempt | `.../logs/scope-harness-pass.log`、`harness/source-scope.spec.ts` |
| 文件入口键盘焦点 | **PASS**，五个宽度 × light/dark；两个入口均检查可见焦点，并以 Enter/Space 激活原生选择器 | `.../logs/web-e2e-serial-pass.log`、`screenshots/import-focus/` |
| Python guarded pytest | **NOT_RUN（修复轮）**；后端本轮未改。初次 QA 在父 SHA 上的 661 passed / exit 0 可见初次归档 `logs/python-guarded.log`，不把它记作当前 SHA 本轮执行 |
| OpenAPI / Python static | **NOT_RUN（修复轮）**；没有 API 或 Python 变化 |

初次 QA 的 UI 截图与 `source-scope-final.log` 保留父 SHA 的失败观察。首次修复验证中有两个 harness 失败：Real scope fixture 起初填入了与合成来源不匹配的 source id；修正为从隔离 FastAPI 响应读取该合成来源 id 后，同一来源范围场景通过；全套 Playwright 曾与集成命令并发，共用 `test-results` 发生清理冲突，之后独立串行 2/2。未因这些 harness 问题降低产品断言。具体失败、修正与最终退出码见 `command-results.json` 及其日志映射。

`vitest` 第一次扫描也把 web 下的本地 QA Playwright harness 当成 Vitest suite，并因新增 scope 一致性字段计数触发守卫①。修复是将 `.local/qa/**` 从 Vitest 发现范围排除、明确更新 `operation_id` 的源码引用归属计数；全套仍为 180 passed / 6 todo，原有断言保留。变更与失败日志见 `vitest-discovery-fail.log`、最终 `vitest-final.log`。

## 截图与 Fresh QA 交接

Import Drawer 焦点截图对应 320/390/768/960/1280 × light/dark 共 10 张。Developer 实看全部宽度与主题的联系表，320 与 1280 的两主题原图复核焦点环清晰可见；键盘自动化在每个组合上均运行两个 input 的 Tab/Enter/Space 与 Escape/焦点归还断言。截图、SHA-256、测试命令及逐条日志由[repair1 evidence manifest](evidence/2026-10-15-frontend-b-repair1/evidence-manifest.json)索引。

fresh QA 请固定检查产品 SHA `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`，独立重验 QA-001/002：真实冻结 scope 的完整原文/目标/预算是否可读，选择器改变后确认是否仍只消费本次 scope；未知目标或 scope/settings 错误是否 fail closed；取消和刷新是否零 provider/job；Import Drawer 两入口在五宽度双主题有可见焦点并维持原生键盘选择、焦点陷阱/Escape/归还。可在独立隔离 profile/workspace 下复验 FastAPI/Fake 其余已实现闭环。初次 SHA 的 FAIL 需保留，不得合并为 PASS。

未测仍包括真实 provider/OAuth/飞书/Keychain、真实材料、付费预算、DMG/安装、公证、五日/双机；6 个 todo 仍归 C/D。**Developer 自测不替代独立 QA 或 Sol gate。**
