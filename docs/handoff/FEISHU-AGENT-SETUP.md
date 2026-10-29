# 飞书 Agent 接入执行手册

本手册供 Codex、WorkBuddy 或后续本机 Agent 执行「连接飞书」提示词时使用。配置客户端成功与 SummitEverything 实际能读取飞书是两件独立的事，报告必须分别给证据。

## 先发现，再复用

1. 从用户给出的网页 origin 定位运行中的 SummitEverything；不要将 origin 的 query、fragment 或凭据加入命令或报告。确认当前 profile 与工作库身份。MCP 会话的 workspace 身份会固定，切库后需按契约重新连接。
2. 读取 `docs/contracts/MCP-v1.md`、`docs/contracts/API-v1.md`、README Agent 接入段和 Feishu 协议矩阵。检查当前助手已连接的 Summit MCP、Feishu 工具/插件、CLI 与相关本机技能；优先沿用有效配置与既存授权。
3. Summit MCP 当前为 14 个受限工具，不暴露设置/凭据，也没有 Feishu CLI bridge。它的 `list_calendar` 只可消费 UI 已批准的一次性计划，不签发计划；不能从 MCP 工具缺失推断其他官方本机 API 不可用。

## 配置安全边界

- 非秘密设置由本机 FastAPI `GET/PATCH /settings` 读取与更新；请求只使用 allowlisted local origin 和本机现有会话认证。变更前读取当前值，只提交必要字段，保留其它设置。
- 凭据走 `PUT /credentials/{provider}` 的正式接口与 macOS Keychain adapter。接口只返回 `configured` 状态；可从已存在的钥匙串或宿主秘密管理中通过受支持的本机安全通道读取并提交到该接口，以完成复用/配置。不得将密钥读出到对话、终端输出、日志或普通文件；不得要求用户把密钥发到聊天。不得臆造或新建 token 文件，不得把凭据写进 MCP JSON、项目普通配置、终端日志或工作库。
- 先看项目当前的 Feishu identity 配置与 endpoint 所需 scope。应用身份优先；只有功能要求 user token 时才走用户授权。权限不足不得自动扩大 scope 或切换身份。
- 如果缺少安全凭据来源，或宿主没有获支持的本机秘密输入/钥匙串交互方式，完成其他安全且有依据的工作后再报告这个具体阻塞和最小用户动作。不要要求用户把密钥发到聊天。

## 分层验证与授权

1. 验证助手/MCP 连到预期 Summit 服务、workspace identity 正确、契约工具可调用；这只证明本机 Agent 接入。
2. 读取非秘密设置和凭据 `configured` 状态，不触发连接检查。配置保存本身不联网。
3. 验证飞书外部连接时，遵循 UI 的既有授权门和一次性 acceptance plan。有效计划仅在其绑定的配置、工作库与确切范围仍匹配时复用；不得绕开计划或重复要求确认。没有适用计划时遵循 API/UI 要求，先给用户必要范围说明并由应用用户确认。
4. 飞书外部授权成功不等于 SummitEverything 已读到数据。应用读取要通过当前 API/集成路径完成，并分别记录 endpoint、身份、scope、范围、实际结果和计划证据。仅使用已授权的无敏感测试范围；不创建任务、不导入材料、不确认知识。
5. OAuth 若需浏览器扫码/用户同意，只要求用户完成这个最小动作。严禁自动抓取浏览器令牌或把授权码发回聊天。

## 收尾报告

列出复用/修改的非秘密配置、验证过的 gate 与证据、未验证门、所需的最小用户动作。区分客户端 MCP 连通、外部飞书授权、应用实际数据读取。不得宣称未执行的 gate 已通过，也不得包含密钥、token、授权码或敏感 URL。
