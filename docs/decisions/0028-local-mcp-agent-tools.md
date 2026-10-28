# ADR 0028：本机标准 MCP 工具桥

日期：2026-10-29。状态：Accepted。

## 决定

提供官方 Python MCP SDK 稳定 v1.x 的 stdio server，供 Codex、WorkBuddy 等 MCP host 发现工具。进程只作为受限 client 访问已运行的唯一 FastAPI，服务仍监听 loopback；不创建第二个业务后端、写库、索引或 Flask 服务。bridge 仅允许代码内固定路由，禁用代理和重定向，拒绝非 loopback URL，并以 session bearer 认证。

Agent 每次会话绑定一个 `workspace_id`。Agent API 在处理同一请求时核对绑定与活动工作库；用户切库后请求失败，必须重新启动会话并显式绑定。凭据只从环境或权限 0600 的外部 token 文件读，不进入 MCP 参数、项目文件或日志。

只开放读取目录、符合共享 `domain/content.py` 资格的版本化知识检索/读取、文本入收件箱和草稿提交/编辑、来源原件读取及持有现有用户审批计划时的日历读取。草稿是待审建议，确认只能由应用用户完成。工具不暴露确认凭据、正式页面确认、任务执行或凭据接口。日历工具不创建、扩展或签发审批计划，只能消费已由应用用户审批的计划。

## 后果

- MCP 工具说明、schema、注解与结构化结果为对外合约，见 [MCP-v1](../contracts/MCP-v1.md)。
- 搜索只用本机 LanceDB BM25；索引尚未建立时返回 `index_not_ready`，识别到旧索引时返回 `index_rebuild_required`。只有在可用索引中查询无命中时才返回空列表；绝不创建 Fake embedding 结果或触发付费模型。
- 接入配置放在客户端配置中，token 文件路径可见但 token 内容不可见。用户级/项目级 WorkBuddy 配置和 Codex CLI 命令见合约；本 ADR 不代用户写全局配置。
- WorkBuddy / Codex 客户端实际连接验收仍需独立运行；SDK 子进程互操作测试只证明协议实现，不等于产品安装包或真实用户连接已通过。
