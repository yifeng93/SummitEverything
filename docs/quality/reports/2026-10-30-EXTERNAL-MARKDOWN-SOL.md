# 外部 Markdown 自动发现、只读阅读与确认

用户要求在外部保存后自动发现变化、变成待确认并更新页面，应用正文保持只读。当前开发源码已应用：工作库登记的正式目录中，新增、修改、删除会更新目录、阅读内容和审批数量；文件损坏时明确不可用，修复后自动恢复。项目概览也复用只读阅读器，移除原来的内嵌正文编辑/创建入口。

## 版本与应用范围

- 基线 `417117401a0a165b14a67abd1e8b27d1ea76d4ca`；首版 `5d76fe20b0300fb846b6af01475f55f4e75859ab`；修复后固定源码 `4358c7b2b410d8c5bcc6ab4dd7d219ce9d349a25`，分支 `codex/external-watch-20261030`。实现目录 `/Users/hanwenbo/.codex/worktrees/external-watch-20261030/SummitEverything`。
- 独立 QA 在 detached `/Users/hanwenbo/.codex/worktrees/qa-external-watch-repair1-20261030/SummitEverything` 验固定 SHA，未改产品源码或 tracked tests。Developer/QA 请求配置为 Luna High；运行时实际模型元数据未暴露，记 UNVERIFIED。
- 20 文件定向补丁应用至主目录 `/Users/hanwenbo/ai/SummitEverything`，当前分支 `hanwenbo-dev-202610`。应用时 HEAD 为 `fad0de06cc5333ac457e88b9df73498ca5189d0b`。API/规格/生成类型中并行模型状态及日历改动逐项保留，补丁应用时没有切换主分支或覆盖整文件。见[应用清单](evidence/2026-10-30-external-markdown/applied.json)、[并行改动核对](evidence/2026-10-30-external-markdown/parallel-edits-preserved.json)。
- 同步 PRODUCT-SPEC、FRONTEND-PAGE-SPECS、API-v1、ACCEPTANCE 与 [ADR 0035](../../decisions/0035-external-markdown-auto-discovery.md)。正文确认、首次建立索引和后续增量索引仍是原有规则；自动发现本身不批准、不建索引、不调用模型或飞书。范围是工作库登记目录，不是持续同步导入前的外部原件。

## 验收结论

| 门 | 结论与证据 |
|---|---|
| 独立固定源码自动检查 | PASS：组件与 UI 守卫 100 项，日志/稿件输入保护组件 7 项，后端 74 项，typecheck/build exit 0。[独立报告](evidence/2026-10-30-external-markdown/qa-final/REPORT.md)、[命令及退出码](evidence/2026-10-30-external-markdown/qa-final/COMMANDS.md)。 |
| 真实文件与浏览器主流程 | PASS：合成工作库 + 真实 FastAPI/SQLite/本地 BGE，首次索引经 UI 确认；外部原子保存西门→东门，自动待确认；确认前 current_pages=0/stale_pages=1，确认后 index_update=updated、索引 ready；旧引用标记 updated，新问答命中东门。DeepSeek 边界使用 MockTransport，无真实模型请求。 |
| 文件生命周期 | PASS：新 Markdown 自动列出并待确认；同一选中文件无效 UTF-8 后不可用，原地修复自动恢复，删除后自动不可用；没有用手动刷新或重新导航代替恢复。[结果](evidence/2026-10-30-external-markdown/qa-final/logs/external-file-lifecycle.json)。 |
| 修复后 Sol 浏览器复核 | PASS：固定新 SHA 的项目内联正文单次 503 后读取次数 1→3、自动显示东门；监控 503 警示可见且恢复后清除；概览滚动 2000→2019，确认回执保留。[正文探针](evidence/2026-10-30-external-markdown/sol-repair1/sol-ui-probe.json)、[概览探针](evidence/2026-10-30-external-markdown/sol-repair1/sol-overview-probe.json)。这些是全 API 合成响应的界面复核，与独立真实文件流程分别记录。 |
| 当前 5173 服务 | PASS：health/current workspace/revision 均 HTTP 200；revision no-store、绑定当前工作库、不透明摘要；当前 App/ProjectsView/PageReader 模块包含本轮实现。[只读核对](evidence/2026-10-30-external-markdown/main-live-readonly.json)。没有在真实工作库写入验收文件。 |
| 主目录组合检查 | 后端 76 passed、Ruff/typecheck/build exit 0，OpenAPI 与后端一致且保留日历字段。前端初跑 99/100，既有断连测试 5 秒超时；单独模块复跑 14/15，原超时项通过但另一今日缓存项超过元素等待时间；该项原断言定向复跑通过（1 passed / 14 skipped）。未改源码、断言或超时阈值，保留两次失败日志；不称本机组合一次全绿。 |

浏览器为 Playwright Chromium，桌面 1440×960；Browser plugin not available，使用仓库 Playwright。页面身份、非空渲染、无框架错误覆盖层与交互截图已核对。真实文件测试捕获的外部来源请求和 pageerror 均为空；有意注入的 503 与无效文件读取错误属于故障场景。未做移动端验收。

轻量扫描补证：首版固定 SHA 的后端在修复轮没有变化；180 个合成 Markdown，30 次 revision 扫描 median 7.69ms、max 9.71ms，未解析正文；同大小/同 mtime 的原子替换可发现，来源目录与 .tmp 不影响 revision，外部 symlink 被拒绝。该耗时仅代表本机这次样本，不是性能承诺。[原始结果](evidence/2026-10-30-external-markdown/sol-initial/sol-revision-probe.json)。

主目录日志：[前端初跑](evidence/2026-10-30-external-markdown/main-web-tests.log)、[App 模块复跑](evidence/2026-10-30-external-markdown/main-app-shell-isolated.log)、[今日单项复跑](evidence/2026-10-30-external-markdown/main-today-test-isolated.log)、[后端](evidence/2026-10-30-external-markdown/main-backend-tests.log)、[类型](evidence/2026-10-30-external-markdown/main-typecheck.log)、[构建](evidence/2026-10-30-external-markdown/main-build.log)、[接口一致性](evidence/2026-10-30-external-markdown/main-schema-check.json)。按用户后续指令，本轮实现与验收记录纳入 `hanwenbo-dev-202610` 分支提交；上述功能分支继续保留原始固定验收提交。安装包未更新。

## 首轮缺陷与边界

首轮 QA 的内部标识 allowlist 守卫失败；Sol 另发现项目内正文一次读取失败后不恢复、监控失败无提示、概览更新跳回顶部并丢回执。修复轮 1 已全部关闭，没有删测试或放宽守卫。[首轮报告](evidence/2026-10-30-external-markdown/qa-initial/REPORT.md)、[修复交接](evidence/2026-10-30-external-markdown/dev/DEV-REPAIR1.md)。独立新 QA 两次夹具失败（包解析路径、错误期待树按钮含状态）单独留证，不算产品缺陷；构建已有体积提示、lint 既有 warning 保留。

精确的「切换工作库后旧 revision HTTP 响应迟到」竞态尚未实测；普通输入保护组件通过不等于外部 revision 浏览器中所有未保存输入场景均已覆盖。真实 DeepSeek 质量、飞书、Keychain、用户材料、安装包/DMG、五日与双机未测。本轮只通过授权的隔离文件流程，不替代完整产品或发布验收；未更新安装包。当前产品状态只维护在 [PROGRESS](../../implementation/PROGRESS.md)。
