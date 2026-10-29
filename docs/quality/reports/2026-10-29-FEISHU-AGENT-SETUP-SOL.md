# 飞书连接提示词入口：Sol 复核

日期：2026-10-29。源码分支 `codex/mcp-workbench-prototype-20261023`，产品实现提交 `7d9dcc4b73663ca2d414b286f22d1dbd4b2bf288`，最终固定候选 `666621d5315b2194e79bd274935dba81dc29c0fd` 补齐旧测试的新交互断言，未推送。QA 专用组合界面快照 `33337999f43f579cdd4528484ac32400e2e238ce` 包含产品提交及当时主目录完整 web 树，不包含其它后端 dirty 修改，也不进入产品分支。

## 行为

今日及设置主区的「连接飞书」直接复制相同的助手接入提示词。复制本身不发 OAuth、外部读取或配置写请求；失败就地展示只读可选文本及重试。提示词携带当前网页 origin，不带查询串、fragment 或秘密；引导 Codex / WorkBuddy 发现本机工具、读取 MCP/API 契约及执行手册、复用授权、通过受支持的安全路径配置，并分别验证外部连接和应用实际读取。MCP 没有凭据设置工具及飞书 CLI bridge 的限制明确保留；高级手动配置仍可用。

## 证据与门

- DEV 组合界面定向回归：25 passed，typecheck 与 lint exit 0。
- 固定源码归档 typecheck exit 0。首次定向回归 23 passed、2 个默认 5 秒超时；命令经 tee 未保留 Vitest 原始退出码，不视为通过。失败两例单 worker 原样重跑 2 passed，23 skipped，exit 0；未放宽 timeout 或断言。
- Sol 实际浏览器：在合成试用工作库 `http://127.0.0.1:5187/` 点击今日按钮，显示已复制及粘贴提示，无配置对话框，会议/任务状态未伪装成已连接。截图已查看。浏览器剪贴板读取因权限等待未得到内容证据，该调用已终止；不能声称浏览器剪贴板内容独立验收通过。
- 后续相关五文件回归：57 passed、2 个默认 5 秒 timeout，exit 1；typecheck/lint exit 0。此运行输入为当时主目录组合树，不能迁移为最终固定源码独立通过。
- 完整首配 E2E：当前 dirty UI 在既有首步文案断言失败；隔离 7d9dcc4 + 新测试在既有 reload 等待处超过未修改的 30 秒上限。整段测试未通过，本次 clipboard 目标段 NOT_RUN。保留前置断言，没有删测试或放宽 timeout。
- Sol 追加当前页面观察：临时模拟 clipboard 拒绝后显示只读提示词（含正确 origin），无弹窗和横向溢出；恢复原生 clipboard 后重试成功。此时并行任务已修改成功按钮样式，属于当时工作区观察，不属于旧组合快照或最终固定源码证据；并行改动原样保留。
- **最终固定源码独立目标 QA PASS**：源码审查、组件/设置定向 3 passed（6 skipped）、今日入口 1 passed（15 skipped）、typecheck 均 exit 0；依赖只读复用主目录 node_modules，不声称独立依赖安装门通过。
- **独立浏览器目标门 PASS**：5297 隔离 Vite + 合成 API，真实 clipboard 读回 origin 与 MCP 文档；拒绝后全文回退与重试通过，dialogCount=0，无应用写/OAuth 请求与外部请求，390px scrollWidth=clientWidth，consoleErrors=[]，exit 0。首次 browser fixture 缺项导致未到目标段；只修 QA harness 后补跑，产品与 tracked tests 未变，首轮证据保留。Sol 已查看截图及两份 QA 报告。
- 首次 QA agent 环境启动遇 `workspace routing discovery timed out`，重试未取得结果后中断；当时本机负载 838.83 / 544.96 / 370.40。最终新 QA 成功完成上述有界门，不能将最终目标 PASS 外推为扩大回归或完整首次配置 E2E clean。
- 真实飞书授权/权限、应用实际飞书读取、Codex/WorkBuddy 执行提示词后的完整自动接入、Keychain、原生壳剪贴板、DMG 与发布均 NOT_RUN。runtime model metadata UNVERIFIED。

## 范围与交接

提交只含本任务源码、行为测试及规格/ADR/执行手册。启动时 staged index 为空，提交后恢复为空；已有 UI/API/热更新等 dirty 修改保留。未修改真实凭据或材料，未创建飞书任务或确认知识，未调用模型。

本次目标实现与固定源码独立 QA 已完成。完整首次配置 E2E 和扩大回归的失败/超时仍保留；之后若要对并行 UI 新版本作全产品验收，需另固定组合 SHA。不得用当前工作区未固定的后续修改冒充本候选证据。

[独立 QA 最终报告](evidence/2026-10-29-feishu-agent-setup/qa/FINAL-QA-rerun.md)；[原始证据目录](evidence/2026-10-29-feishu-agent-setup/)；[执行手册](../../handoff/FEISHU-AGENT-SETUP.md)；[当前状态](../../implementation/PROGRESS.md)。
