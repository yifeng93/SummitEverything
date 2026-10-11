# M3 包 2 Developer 报告：完整问答、角色与记忆

日期：2026-10-11  
状态：Developer 实现与自动自测完成；等待 Sol 调度全新独立 QA。Developer 报告不构成包级验收或 PASS。  
分支：`codex/m3-integrated-packages`  
源码 SHA：待提交后填写

## 交付范围

- 新增 fact / comparison / plan 三种问答模式。当前资格门和 QueryService 仍是唯一来源检索路径；服务端从受检索的引用生成来源陈述，答案将推断、建议和缺失资料独立保存和显示。Fake comparison 逐页对照并明确缺少共同指标时不判断优劣或因果；Fake plan 输出可复验的审核步骤，不编造业务数字。
- profile 本地 SQLite 按 workspace 二次隔离的角色和记忆 CRUD。角色说明按实际 UTF-8 字节预算校验；已确认记忆总预算超限时返回清楚错误，不静默丢弃上下文。
- 仅从 ConversationStore 中的真实用户问题创建 memory candidate；客户端需提交 `user_expression=true` 的明确表达声明，服务端要求文本属于该问题并拒绝常见引用、来源、转述和粘贴标志以及不符合第一人称表达的内容。候选保持 pending，用户可编辑并确认后才 active；来源 request/message id 与确认意图保留。相同 pending 来源/文本重试复用候选。
- 多轮上下文只带最近 8 条先前用户问题作为指代参考，不带 assistant 旧答案。每个新查询重新过当前资格门检索；稳定 request ID 重放已保存的 SSE 事件，不能因角色、记忆或会话后续变化产生新 provider 调用。不同模式等请求意图仍按原逻辑拒绝冲突。
- 问答历史保存并返回 mode、来源陈述、推断、建议和缺失资料；删除角色后原答案与角色 ID 仍可读取。页面添加模式选择、角色管理、候选声明/确认、记忆编辑删除及结构化答案区域。
- DeepSeek adapter 保持 stub-tested；真实业务 Real model gate 未打开，provider payload 增加模式、角色风格、已确认记忆、先前用户问题（reference-only）和合格 passages，不包含先前 assistant 答案。

## 实际检查结果

所有以下记录的退出码与原始输出保存在 ignored `.local/dev/m3-package-2/`：

| 命令 | 结果 | 原始日志 |
|---|---:|---|
| `uv sync --locked --group dev` | PASS，exit 0 | `uv-sync.log` / `uv-sync.exit` |
| `uv run pytest -q tests/integration/test_feishu.py` | PASS，35 passed；1 条 Starlette/httpx deprecation，exit 0 | `pytest-feishu.log` / `pytest-feishu.exit` |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | PASS，399 passed；1 条 Starlette/httpx deprecation，exit 0 | `pytest-full.log` / `pytest-full.exit` |
| `uv run ruff check src tests` | PASS，exit 0 | `ruff-check.log` / `ruff-check.exit` |
| `uv run ruff format --check src tests` | PASS，exit 0 | `ruff-format.log` / `ruff-format.exit` |
| `uv run mypy src` | PASS，39 source files，exit 0 | `mypy.log` / `mypy.exit` |
| `uv lock --check` | PASS，exit 0 | `uv-lock-check.log` / `uv-lock-check.exit` |
| `uv build` | PASS，exit 0 | `uv-build.log` / `uv-build.exit` |
| `cd web && npm ci` | PASS，exit 0 | `npm-ci.log` / `npm-ci.exit` |
| `cd web && npm run api:types` | PASS，exit 0 | `api-types.log` / `api-types.exit` |
| 第二次 `npm run api:types` | PASS，exit 0；generated TypeScript SHA-256 前后不变 | `api-types-idempotence.log` / `.exit` |
| `cd web && npm test -- --run` | PASS，50 passed / 12 files，exit 0 | `web-tests.log` / `web-tests.exit` |
| `cd web && npm run typecheck` | PASS，exit 0 | `web-typecheck.log` / `.exit` |
| `cd web && npm run lint` | exit 0；保留 TodayView / ProjectsView 两条既有 effect warnings | `web-lint.log` / `.exit` |
| `cd web && npm run build` | PASS，exit 0 | `web-build.log` / `.exit` |

本轮额外聚焦检查：后端角色/记忆/多轮、会话 intent、资格门、应用生命周期、Stage B query regressions、provider settings 与 adapter 共 59 passed；AskView 4 passed、typecheck exit 0。最终全量命令覆盖了这些检查。

## QA 复演重点

在隔离 profile / 合成 workspace 上构建两页已确认材料（不同主题，例如预算与排期），并用 Fake provider：

1. 分别提交 fact、comparison、plan，确认三种正文与结构化 fields 不同；comparison 只对照当下合格页面，缺少共同指标时显示缺失项，不编造数值；plan 输出待用户决定的步骤。
2. 创建本地角色，设置说明预算，问答时检查真实 provider context 收到 mode、role name/instructions；越过预算应以可读错误停止，不截断当前问题或策略。
3. 从真实 user question 选择“这是我本人表达”的声明；未确认候选不进入后续上下文。验证 assistant 文本、伪造 request id、带引用/原文/粘贴标记的 source canary 和缺少声明均被拒绝。确认并编辑后检查 provenance request id 和 active 记忆 provider context；再测编辑、删除与 profile/workspace 隔离。
4. 多轮追问 provider payload 只含先前 user questions，绝不含 assistant answer；每个新 query 使用当前资格门重新取证。修改 role/memory 或增加后续轮次后重放相同 request id，检查 SSE 完全相同且 provider 调用计数不变；不同 mode 同 request id 应 409。
5. 删除 role 后重开历史，检查旧结构化答案仍完整可读；确认 answer 不创建知识页或执行动作。

自动化核心命令：`uv run pytest -q tests/integration/test_answer_context.py tests/integration/test_conversations.py tests/integration/test_qualified_retrieval.py tests/integration/test_app_lifecycle.py tests/integration/test_stage_b_regressions.py tests/integration/test_provider_settings_api.py tests/unit/test_real_model_adapters.py`；`cd web && npm test -- --run src/components/AskView.test.tsx && npm run typecheck`。

## 尚未观察的门与限制

- 全新固定 SHA QA 尚未运行；Sol 尚未判包级状态。
- Developer 本轮未运行真实浏览器；实际 DOM / 网络请求与 console 为 QA 待验证项。runtime 元数据 UNVERIFIED。
- 真实 DeepSeek credential/API、模型输出质量、Keychain、真实资料、Real 业务调用、DMG、五日/双机与发布门均 NOT_RUN；Real model gate 保持关闭。
- memory candidate 的第一人称与来源标记检查是保守的文本规则，配合用户明确声明和真实历史消息来源；它不是语义鉴定器。QA 应验证 source canary 负例，并检查普通可用偏好/事实表达不会被过度拒绝。
- Web lint 两条 effect warnings 和 FastAPI TestClient 的 Starlette/httpx deprecation 均记录保留，没有因本包引入新依赖或锁文件。
