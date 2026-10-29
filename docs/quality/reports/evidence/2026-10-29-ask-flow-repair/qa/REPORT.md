# 独立离线 QA 报告：offline ask schema / index readiness

- 固定源码 SHA：`b737a4c1a2c14c6641347353414f1a0cf7631e6f`
- 分支：独立 worktree detached HEAD（基于 Developer 固定提交）
- checkout：`/Users/hanwenbo/.codex/worktrees/qa-offline-ask/SummitEverything`
- QA 时间：2026-10-29（Asia/Shanghai）
- 测试边界：仅合成输入；无 DeepSeek/Model Studio 请求，无真实材料、真实凭据或 Keychain 写入，无飞书请求。

## 结论

| 检查项 | 结果 | 证据 |
|---|---|---|
| Organizer 严格 schema、18 个成功响应回放、恶意/未知字段诊断脱敏及原件保留 | PASS | `backend-focused.log`；`tests/unit/test_organize_schema_replay.py`、`tests/unit/test_llm_schema_tolerance.py`、`tests/integration/test_intake_review.py` |
| Fake 索引切换 Real 后，未准备匹配 fingerprint 时在 query plan 和 query dispatch 阻断 | PASS | `backend-focused.log`；`tests/integration/test_provider_settings_api.py`、`tests/integration/test_real_model_approval_flow.py` |
| 同 fingerprint 的部分页面 stale 不阻断有效索引查询；逐页资格仍控制召回 | PASS | `test_real_model_approval_flow.py::test_organize_index_and_query_use_confirmed_plans_and_real_adapters` 包含新增页后的 query。provider transport 是 test 内 MockTransport。 |
| 错误保留 Ask 问题、显示审批 CTA 并打开审批入口 | PASS | 本地真实 React + FastAPI 浏览器运行；问句“合成资料里的答案是什么？”保留，显示 `index_not_ready` 提示和“前往审批建立或更新索引”，点击后到审批页并看到“搜索与问答准备”。结构证据见 `browser-ui.txt`；截图在 QA 对话工具输出中。 |
| 开始后续新请求时清除旧审批 CTA | PASS | AskView 专项测试验证 index-not-ready 之后启动新请求时旧 CTA 消失，出现新的计划确认入口；见 `frontend-focused.log` 的 53/53。浏览器本轮未建立可成功执行的索引，因此未对完整成功回答后的 UI 状态另做浏览器复演。 |
| AskView / AskPreferences / SourceOrganizer / UI contract guards | PASS | `frontend-focused.log`：5 files, 53 tests passed。 |
| TypeScript typecheck / production web build | PASS | `typecheck.log`、`build.log`。build 有 Vite 既有 JS chunk >500 kB 提示。 |
| 本轮 DeepSeek/embedding/rerank 真实质量、真实向量模型、实际模型 metadata | NOT_RUN | 未发任何外部模型请求；runtime model metadata 未作为本轮模型调用证据暴露，记 UNVERIFIED。 |
| Full UI 整理→审核→正式化→显式索引→SSE 引用成功全流程 | NOT_RUN | 当前浏览器实际复演覆盖 Real 模式未就绪拦截和审批 CTA；后续可用本地 MockTransport 继续完整合成链路。 |

## 实际运行命令与结果

在该 worktree 首次按锁文件执行 `npm ci`，退出码 0。node 为 `v24.12.0`，npm 报告部分依赖声明要求 `^24.15.0` 或其它版本；实际下列前端检查仍通过。

1. `uv run pytest -q tests/integration/test_intake_review.py tests/integration/test_provider_settings_api.py tests/integration/test_real_model_approval_flow.py tests/integration/test_feishu_real_gate.py tests/unit/test_organize_schema_replay.py tests/unit/test_llm_schema_tolerance.py tests/unit/test_real_model_adapters.py`
   - 退出码 0；`116 passed, 1 warning`（Starlette/httpx deprecation）。原始输出：`backend-focused.log`。
2. `npm --prefix web test -- --run src/components/AskView.test.tsx src/components/AskPreferences.test.tsx src/components/SourceOrganizer.test.tsx src/ui-contract.test.ts src/ui-contract.render.test.tsx`
   - 退出码 0；`5 files, 53 tests passed`。原始输出：`frontend-focused.log`。
3. `npm --prefix web run typecheck`
   - 退出码 0；原始输出：`typecheck.log`。
4. `npm --prefix web run build`
   - 退出码 0；原始输出：`build.log`。
5. `git diff --check`
   - 退出码 0；固定源码目录没有 tracked changes。构建产物、npm 依赖与 `.local/qa` 均为本地 ignored 数据，不进入 Git。

## 浏览器与本机 API harness

- 本机 WebUI 由 Vite 提供；API 是候选源码的真实 FastAPI `create_app`、真实路由、真实 workspace、SQLite 与 query/index 代码。
- Harness：`serve_memory.py`，profile 和工作库分别位于 `.local/qa/profile` 与 `.local/qa/workspace`。
- 外部边界：`MemorySecretBackend` 使用合成凭据；Embedding/LLM/Rerank client 全部替换为 `httpx.MockTransport`，返回离线 503 响应，不可能访问提供商。实际 UI query 在 provider transport 前由 `index_not_ready` 返回。
- 模型请求计数没有从 provider transport 发生；无真实 key/Keychain，no external network.
- 浏览器观察：Real query UI 保留输入，错误说明本次没有预留/发送模型请求，提供审批 CTA；点击 CTA 后到审批页，索引准备区说明须先添加并确认正式内容。
- 首次尝试的隔离 UI 连接未带可用本机 secret backend，因而只观察到 provider_disabled；随后切至上述 MemorySecretBackend + MockTransport harness 后通过 index_not_ready 浏览器场景。前者不作为 PASS 证据。

## 受测 SHA 清洁性

- `git rev-parse HEAD`：`b737a4c1a2c14c6641347353414f1a0cf7631e6f`
- `git status --short --branch`：`## HEAD (no branch)`，无 tracked/untracked changes。`.local/qa` 按仓库规则忽略。
- 被测实现模块通过该 checkout 的 `uv` 项目环境运行；无源码 patch、无已有 tracked tests 修改。

## 与历史实测边界

所回放的 fixture 是 18 个既有成功整理响应。原来两次 schema 失败的响应并未保存，因此这里不声称重放或复现了那两条原始响应；负例使用合成未知字段/类型错误。没有重试逻辑检查到的真实 provider 质量保证。
