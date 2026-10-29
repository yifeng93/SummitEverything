# QA: 飞书 portable prompt final candidate

- 固定 SHA：`d864b137bdca3e7b9320e9526e7f12a3444f0c01`
- 父 SHA：`71c670e48e6556c2c276e057b85c234c337be945`
- Checkout：`/Users/hanwenbo/.codex/worktrees/summit-feishu-portable-prompt-qa-final/SummitEverything`
- 范围：父差异与规范对齐核对；一次隔离真实浏览器剪贴板读回。无飞书服务、凭据、真实动作。

## 差异核对

- `git diff --name-status HEAD^ HEAD`：只改 `docs/decisions/0029-feishu-agent-setup-entry.md`（M）。`git diff --check HEAD^ HEAD` 通过。
- 唯一文本调整将“网页 origin 不是 API origin”改为“不能默认网页 origin 等同 API origin，也不得猜替端口；已证实的同源 API 或受支持本机代理可以使用”。与 `web/src/components/feishuAgentSetupPrompt.ts`、`docs/product/PRODUCT-SPEC.md`、`docs/handoff/FEISHU-AGENT-SETUP.md` 的口径一致。
- `git diff --quiet HEAD^ HEAD -- web src tests` exit 0：产品源码与 tracked tests 相对上一轮 SHA byte unchanged；继承上一轮记录的 4/4 目标测试与 typecheck exit 0，本轮未重跑。

## 浏览器门

- Harness 位于本目录；Vite web root、`@vitejs/plugin-react`，显式 `optimizeDeps.include: ['react','react-dom/client','react/jsx-runtime']`；只挂载原 `FeishuAgentSetup`，使用主目录 `web/node_modules` 只读复用。浏览器请求拦截为仅允许 `127.0.0.1:5191`，其余请求 abort；断言了真实 `navigator.clipboard.readText()` 内容及精确禁止动作文本。
- 首次启动失败：`vite` 缺失（新 checkout 无 `web/node_modules`），浏览器报 `ERR_CONNECTION_REFUSED`；未读回剪贴板。
- 一次修复后重跑：Vite 已启动，但 console/server 报 harness import 错误：`../../src/components/FeishuAgentSetup` 路径解析失败；因此目标按钮未渲染，Playwright `getByRole(button, name=连接飞书)` 30 秒超时，未发生剪贴板读回。该 harness 执行到超时后 Node 子进程未自然退出，已清理相关进程；外层 shell 的最终退出码未能采集。此失败属于 harness，浏览器门 **BLOCKED**，不判产品缺陷。
- Harness 尚需将相对导入修正为从 `web/.local/qa/<case>` 到 `web/src` 的 `../../../src/...` 后重新运行；本轮在一次修复重跑额度内停止。

原始日志：`vite.log`、`clipboard.log`。浏览器真实 clipboard readback 未取得，精确禁止动作断言未执行。
