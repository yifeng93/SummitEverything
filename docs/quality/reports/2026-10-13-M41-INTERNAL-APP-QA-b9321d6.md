# M4.1 Internal App 独立离线 QA（初验）

## 身份与范围

- 验收者：全新独立 QA Luna。
- 固定受测产品 SHA：`b9321d64c5404feadffebc05964793e9402a07aa`。checkout：`/Users/yifengstudio/.codex/worktrees/m41-qa-b9321d6/SummitEverything`，detached HEAD；开始、结束均为该 SHA。源码、tracked tests、依赖及产品配置没有修改。
- 环境：macOS 27.0.1 arm64，系统 Python 3.9.6。UI 使用 QA 临时目录内复制的 App、合成 workspace/profile；通过受限 PATH (`/usr/bin:/bin:/usr/sbin:/sbin`) 启动，避免依赖系统 Python、Node 或 Docker。候选 DMG SHA256：`1822e655836d591dcc612f6de4dfeda095dc16bd8e194e87e33cf5b5894c72fd`。
- 候选包身份：source `b9321d6`、dirty `false`、build `20261013T052105Z-577f0cc805f2`；内置前端 SHA256 `577f0cc805f2f7727add28c1e0d4714c0c15040fa7c094fce7e6234c65239fc6`、依赖 SHA256 `2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`。Runtime 元数据未在运行时实际暴露：`UNVERIFIED`。
- 本轮范围是 M4.1 离线源码、候选包和合成数据验证；没有访问真实凭据、Keychain、账户、业务材料、付费模型、飞书或 Stage C。

## 结果

| 案例 | 结果 | 实际步骤与观察 | 证据 |
|---|---|---|---|
| C24：本机 API 与无凭据请求 | 部分 PASS；整项 NOT_RUN | 对隔离 App 发无授权 workspace 写请求得 401；使用外部 Origin 得 403；合成 credential sentinel 的有效 PUT 路径在无授权时得 401，响应与隔离 profile diagnostics 中均未发现 sentinel。未执行持有有效合成 bearer 的授权写入及完整 API / 日志矩阵，不能据此判定整项通过。 | `evidence/2026-10-13-m41-qa-b9321d6/ui-observations.txt`；命令结果 JSON |
| C24：Markdown / 命令文本 | PASS（有限 UI 观察） | 通过真实 UI 输入合成 Markdown，其中含 `<script>` 和命令样式文本；页面将 script 显示为文本，合成命令标记文件未生成。没有覆盖所有 Markdown / WebView 导航注入变体。 | `ui-observations.txt` |
| C25：冷启动、工作库闭环与恢复 | PASS（合成范围） | 限制 PATH 下运行隔离 App，完成新建工作库、项目和页面、粘贴、生成模拟草稿、明确确认内容与索引计划、建立索引及问答引用；退出后以同 profile 重开工作库，页面、索引和聊天引用历史恢复。工作库检查未见 SQLite、凭据或诊断日志；这些 profile 本地状态按产品设计存在。 | `ui-observations.txt`；`packaged-backend-smoke-after-exit.log` |
| C25：原生目录选择 | PASS | 点击“选择文件夹…”出现 macOS Open panel；通过 Cmd+Shift+G 输入本轮自行创建的合成 workspace 路径，选择后打开该库成功。 | `ui-observations.txt` |
| C25：HTML 文件导入选择 | **FAIL，P1** | 对文件上传入口进行 AX 点击、鼠标点击、Space 和 Return；入口仅获得焦点，没有出现原生 Open panel 或选择文件后的状态。`native/Sources/SummitEverythingApp/App.swift` 声明 `WKUIDelegate`，但没有 `runOpenPanelWith` 实现。Apple 的 WKUIDelegate 文档说明 macOS 默认禁用文件上传，除非实现该方法。该缺陷阻断已承诺的文件导入路径。 | `ui-observations.txt`；[Apple WKUIDelegate 文档](https://developer.apple.com/documentation/webkit/wkuidelegate/webview(_:runopenpanelwith:initiatedbyframe:completionhandler:)) |
| C25：Cmd+Q 与关闭最后窗口 | PASS | Cmd+Q 后 shell 核对 App、后端和 18793 监听均退出。另一隔离 profile 下关闭最后一个原生窗口后，UI 句柄报告 `procNotFound`，shell 再核对无 QA App/后端和监听；未再用 CUA 查找或重绑 App。 | `ui-observations.txt` |
| C25：被强制中断的父进程清理 | PASS | 对精确 QA App 父 PID 发 SIGKILL 后，后端通过管道 EOF 退出且 18793 释放。 | `ui-observations.txt`；打包 smoke 日志 |
| C25：端口冲突 / 错误 readiness 服务 | PASS（单一路径） | 合成独立服务先占用 18793。App 显示“本地应用服务未就绪”，只对 health endpoint 做 readiness 探测；合成服务保持存活，App 未接管或杀死该服务。 | `occupied-port-server.log`；`ui-observations.txt` |
| C25：DMG 与候选身份 | PASS（本机离线检查） | DEV 候选 DMG SHA 与交接值一致；只读挂载、包内 App `codesign --verify --deep --strict` 和卸载成功；DEV manifest SHA256SUMS 16 项在其所属 checkout 中核对全部匹配。此处不代表 Developer ID 签名、公证或安装门通过。 | `dmg-mount.log`、`dmg-app-codesign.log`、`dmg-detach.log`；DEV manifest 由交接提供，本轮独立复核 |
| C25：完整文件导入 / 资料隐私闭环 | NOT_RUN（导入入口已 FAIL） | 因文件上传面板缺陷，未能通过文件选择导入 TXT/MD 并继续端到端流程。 | 上述 C25 文件导入 FAIL |
| 未覆盖的离线故障场景 | NOT_RUN | 本轮没有完整执行 missing-backend、延迟 readiness、身份错误 fail-closed、SSE 主动取消/断流及历史恢复后的重试语义等所有组合。 | — |
| 范围外门 | NOT_RUN | 真实模型 / 飞书 / Keychain、真实用户安装、Developer ID / 公证、旧安装覆盖、Intel 与低版本 macOS、五日、双机、M4.2 与正式发布。 | — |

### 缺陷

**M41-QA-001 — C25 文件导入面板缺失，P1。** 固定 SHA `b9321d64c5404feadffebc05964793e9402a07aa`。最小复现：运行复制的候选 App → 打开隔离工作库 → 点击 HTML 文件导入入口（AX、鼠标、Space、Return 均复现）。预期：macOS 文件面板出现并可选择合成 TXT/MD；实际：没有文件面板或选择结果。产品代码未提供 WKUIDelegate 文件面板回调，而 WKWebView 在 macOS 默认禁用上传。影响：用户无法使用承诺的文件选择导入能力。证据及官方文档见上表。请 Developer 修复并提交新 SHA，再由全新 QA 复验文件选择与后续处理闭环。

## 命令与环境准备

完整命令、逐条退出码和摘要见 [`commands-results.json`](evidence/2026-10-13-m41-qa-b9321d6/commands-results.json)，原始 stdout / stderr 见同目录日志。新 checkout 首次全量 pytest 因未先安装 web 依赖，499 项中 3 个 dev-runner 集成测试失败；按 README 执行 `npm --prefix web ci` 后，重复同一 pytest 命令为 499 passed。该次失败属于 QA 准备顺序，不登记为产品缺陷。

首次 `uv build` 与 Web build 并发执行时 sdist 以 `unexpected end of data` 失败；并发结束后顺序重跑成功。当前证据没有证明该失败由产品代码导致，也没有进一步推断其机制。打包 backend smoke 的首次尝试因 UI 测试正占用端口 18793 而退出；App 退出后按相同 smoke 流程成功。

## 门结论

- 独立离线 QA：**FAIL**。P1 `M41-QA-001` 未关闭，M4.1 不可标记整体通过。
- 源码自动检查、前端 56 项、499 项 pytest、Swift release build、顺序 `uv build`、隔离 backend smoke：本轮实际运行并通过（命令详见 JSON）。
- DEV 自测摘要不是本报告结论；候选包只完成列出的离线核验。
- 真实 provider、真实样板 / 凭据、安装与公证、五日、双机和发布门均 `NOT_RUN`。Runtime 元数据为 `UNVERIFIED`。
- 最终清理核对：无 QA SummitEverything 进程、无 QA 后端监听 TCP 18793、无存留只读 DMG 挂载。CUI readiness 阶段曾有一次工具确认动作可能触发无显式 profile 环境的自动启动；精确进程已停止，未读取、检查或删除任何默认 profile。其余受控 UI 测试均先显式设置隔离 profile 再绑定运行中的 App。

## 给执行者的下一步

修复 WKWebView 文件选择器委托和允许的 TXT/MD 导入流程，提交新的固定产品 SHA。新一轮由全新 QA checkout 复验实际原生面板、选择合成文件和完整导入闭环，并补测本轮标为 NOT_RUN 的适用离线故障案例。保留本报告及证据，不覆盖初验记录。
