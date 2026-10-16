# 今日与审批可用性：Sol 最终门判断

日期：2026-10-16。固定受测产品 SHA：`d9f49c1fc1b2dc787b21e3f2bd47662de3d1e715`。初验后自动修复使用 **1/2 轮**。

## 结论：PASS（本轮核心离线源码与浏览器范围）

Sol 核对 fresh Luna QA 的实际退出码、原始日志、独立 harness、反例、网络 manifest、截图、SHA 与干净工作树后，判定本轮核心离线范围 PASS。今日并列安排与记录、真实 ID 接续、单项审批阅读、未保存保护、多稿部分确认和失败/未知导入行为已交付。整站业务、完整 WCAG AA、真实服务与用户安装不包含在此结论中。

初验 `0957df2` 的 FAIL 保留：两处新增 lint suppression 本身违反批准质量门；未披露是额外透明度问题。修复版移除了两处禁用，未新增替代 suppression、跳过测试、降低规则或修改 API/依赖。独立异步测试在修复版 5/5 PASS，在初验源码副本出现两项预期失败，证实旧响应覆盖问题已修复。未用旧 SHA 的行为 PASS 直接继承新结论。

## 证据与结果

| 状态 | 实际检查与范围 |
|---|---|
| PASS | QA 开始/结束 SHA 均为 `d9f49c1fc1b2dc787b21e3f2bd47662de3d1e715`，工作树干净，`git diff --check` exit 0；Sol 再次读取 SHA/status/diff 复核。 |
| PASS | 独立 `npm ci`、Web 239/239、typecheck、lint、build、API 类型生成，退出码均 0；生成类型后无 tracked diff。 |
| PASS | 默认 Playwright 最终 2/2；真实 FastAPI/Fake integration 1/1。首次默认 Playwright exit 1 的 trace/zip `ENOENT` 及成功重跑日志均保留，根因 UNVERIFIED，未误报为端口占用或产品通过。 |
| PASS | 独立延迟响应 harness 5/5：旧 refresh epoch、旧详情响应、已处理目标后详情继续、数据未到不提前消费、卸载后迟到响应无残留可见 UI。旧 `0957df2` 为 2 failed / 3 passed 的有效反例。 |
| PASS | 320/390/768/960/1024/1280/1440、深浅主题无页面横溢；1280×800 非空今日首屏可操作会议/任务首行与记录/导入入口，默认 3/5 可展开。文件入口/对话框关闭焦点、dirty 取消保留与返回焦点按实际脚本路径通过。 |
| PASS | 同名来源按返回 ID 定位、Markdown 阅读、冲突选择只在最终确认请求生效、首次索引状态在已有 confirmed page 而 store.pages=0 时仍提示。 |
| PASS | 混合文件批次 201/400/503 只选择成功 ID；失败项仅显式重试；未知项只发送一次。真实 FastAPI/Fake 一来源拆两稿、只确认一稿，另一稿 pending，正式页一份，任务写入为空、项目 progress_version=0。 |
| PASS | [CI 38919089638](https://github.com/yifeng93/SummitEverything/actions/runs/38919089638) 对 docs-only tip `c0f0692a9ff1e2bcb2659be910e7580fccaabd5d` 全 13 步 success；相对受测 SHA 产品/tests/依赖树零差异。包含 Python 712 passed / 1 warning、Web 239、native 5 tests、内部 App/DMG 技术构建与校验。不是用户安装验收。 |
| PASS（抽样） | 今日/审批稳定态代表性文字浅色最低 4.72:1、深色最低 6.97:1；只代表记录的采样。 |
| NOT_RUN | 项目、知识问答等完整业务复演、整站完整键盘/屏幕阅读器/所有状态 WCAG AA 审计。 |
| NOT_RUN | 真实 provider/飞书/凭据/用户材料/Keychain、用户安装、公证、五日、双机与发布。runtime model metadata 未暴露，UNVERIFIED。 |

浏览器独立视口及 focused 场景 console/pageerror/外联尝试为空。文件批次四条 HTTP 400/503 resource error 为注入且已处理；FastAPI 首次空库两次 workspace 409 与一次 first-use 404 为初始化探测，后续恢复成功。没有把这些预期响应混称为未处理 JS 错误。

## 保留观察与限制

两条既有 lint warning（App/Projects）与 Vite 603.32 kB 主包 advisory 保留，未改阈值；初验主包为 602.45 kB。QA 外部 harness 配置有未来 Vite loader 提示，不是产品 lint 禁用。首次 Playwright artifact 缺失原因未确定，后续相同命令及独立视口复演通过；如后续复发，应继续检查测试产物生命周期。未发现本轮阻塞合并的产品缺陷。

Chrome DevTools MCP 未配置，使用项目 Playwright/真实 Chromium。初验早期无 raw 的 `items.filter` 旧观测继续 UNVERIFIED，不补造证据。没有重跑真实服务或安装应用。

## 持久证据与交付

- [fresh QA 原报告](evidence/2026-10-16-frontend-usability-qa-repair1/REPORT.md)、[实际退出码](evidence/2026-10-16-frontend-usability-qa-repair1/check-status.json)、[45 份原始文件 SHA-256 清单](evidence/2026-10-16-frontend-usability-qa-repair1/manifest.json)。包含报告、harness、日志、manifest、代表截图及 CI 元数据，逐字节复制；完整视口 PNG 留在原 QA `.local`。不提交测试 workspace/profile/db。
- [DEV 修复报告](2026-10-16-FRONTEND-USABILITY-DEV-REPAIR1.md)、[8 份原始开发日志清单](evidence/2026-10-16-frontend-usability-dev-repair1/manifest.json)。原始报告保持其提交时 pending 状态，不回写历史结论。
- [初验 FAIL 与证据](2026-10-16-FRONTEND-USABILITY-SOL-INITIAL.md)保留。产品、规格、ADR 0012、DEV/QA 和当前入口在 [PR #23](https://github.com/yifeng93/SummitEverything/pull/23) 可审查。

当前尚未合入 main。按 AGENTS.md 的重要里程碑规则，合并需要用户明确批准；不删除分支/worktree，不把本结论扩大为正式发布。
