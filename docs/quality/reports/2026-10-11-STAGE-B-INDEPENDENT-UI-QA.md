# Stage B 固定 7f3119a 独立 UI / 原生壳 QA

本报告是固定候选的 UI 子范围记录，**不是整体 Stage B 通过**。同期后端独立验收发现 refresh 消耗标记只在内存、重启可重发旧 refresh token 的 P1；交执行者修复，新 SHA 必须另行复验，本报告不回写为新 SHA 证据。

## 身份与范围

- 角色：独立离线 UI / 原生验收子 agent；产品完整 SHA `7f3119a511fda6f3d2771af4cf09fd9a9026edb7`。
- 独立 detached checkout `/Users/yifengstudio/.codex/worktrees/qa-stage-b-sol-ui/SummitEverything`；本 checkout 自建 `.venv`、`web/node_modules`、Swift build、profile 与合成工作库。没有产品修改、commit 或 push。
- Python3.12.13；实际 CUA IAB（子 agent 限制隐藏）；actual native development binary，独立 bundle ID。API18895 / Web15175；失败反馈18896 / 15176。
- 先读 AGENTS/README/PROGRESS/PRODUCT-SPEC/ARCHITECTURE/API/WORKSPACE/TESTER/ACCEPTANCE/最新交接/Sol DEV 与 UI replay。受测契约均来自本 SHA。
- 全 runtime 使用 `scripts/offline_guard:src`；无真实秘密/账户/材料/模型/日历/task 操作，既有真实 smoke 全部仍0/1。

## 场景结果

| 场景 | 结果 | 实际证据与限度 |
|---|---|---|
| C01/C04/C05/C10/C12 新库→来源→稿件→批准→索引→问答 | PASS（本复演） | 实际浏览器完成，24人合成文字原件保留；批准页同一内容门eligible/approved；SQLite仅1 chunk；问答引用该段。不是整个 C01–C14 重验。 |
| C16/C17 Fake 创建/完成 | PASS（本复演） | 明确无日期，proposed→confirmed→另执行；列表刷新创建/已完成；正常真实业务route/store，不 mock业务。编辑异常及恢复变体不在此 GUI 复演。 |
| B02 设置与凭据失败关闭 | PASS（离线范围） | Real/AppID保存，settings真实磁盘一致；IAB与native均Keychain不可用、保存/删除/smoke禁用；设置/API24 passed，vault/fault13 passed。Memory/fault拒绝、locked、损坏及实例重建/隔离，不等于OS测试。 |
| Real任务写 UI / C18本地独立进度 | PASS（本复演+组件） | 创建按钮disabled、文字说明真实禁写；本地进度enabled，提议/确认不改manifest，执行后version0→1。Real edit/complete控制由45项Web测试覆盖，本次真实账户任务对象NOT_RUN。 |
| B05 原生开发壳 | PASS（本开发壳） | exact checkout binary，run_id与native派生进程一致、guard active1与profile绝对路径匹配；原生目录选择器打开合成库，设置持久；最后窗口关闭children与ports无残留；缺uv隔离场景显示readiness错误并清理。 |
| Console / inbound API log | PASS（捕获窗） | IABwarn/error=[]；实际uvicorn132条loopback API记录，2条初始空库409，其余<400；没有smoke POST。不作HAR/完整egress结论。 |
| 配置完整的app-only日历 GUI / Real OAuth官方链接外部浏览器 | NOT_RUN（GUI） | 本正常guard无app secret，日历按预期禁用；组件回归覆盖app_configured/auth=false可用和官方链接，不点击真实OAuth链接。 |
| DMG、安装、OS Keychain、真实provider、真实质量、样板、五日、双机、M3–M5 | NOT_RUN | 无相应材料/动作；不能由开发壳及模拟结果推出通过。 |

## 命令和证据

[复演记录](evidence/2026-10-11-stage-b-independent-ui-qa/replay.md)记录完整命令、隔离路径、操作及网络机制；所有证据同目录，manifest逐项SHA-256。

- `uv sync --locked --group dev`、`npm ci`、`swift build`：exit0，lock无变化。
- guard `test_provider_settings.py` + `test_provider_settings_api.py`：24 passed，1既有Starlette warning；guard凭据及独立fault：13 passed。
- `npm test`：10文件45 passed。这个子验收没有重跑全后端/静态矩阵，由后端验收单独报告。
- 磁盘断言：审批资格、原件/待审保留、1 chunk、progress确认未执行不变/执行变1、Real数据门false、smoke POST0均通过。第一次网络断言误将预期空库409当失败，修正只允许具体初始GET workspace409后通过；非产品缺陷。
- 网络来源是实际服务访问日志；native父实现丢弃stdout/stderr，native网络未捕获。浏览器performance资源列表接口在CUA只读域不可用，不声称资源或HAR完整性。

## 缺陷与下一步

本UI子范围未发现产品新缺陷。整体候选被独立后端refresh重启P1阻断，详见该报告；本报告的局部PASS不得用于整体整合授权。修复固定新SHA后，须重建并复演native/设置/禁写与对应后端反例，保存新证据，保留本旧SHA记录。
