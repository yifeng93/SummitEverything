# MCP v1：本机 Agent 工具接口

状态：首版 MCP 合约。MCP 使用官方 Python SDK v1.x 的标准 stdio transport；不另启服务、不绕过唯一 FastAPI 后端。

## 连接

运行 `uv run --locked --project <项目目录> python -m summit_everything.mcp_server`。MCP 服务仅接受 `http://127.0.0.1[:port]` 或 IPv6 loopback URL；不支持 DNS、非 loopback、用户信息、路径前缀、查询参数或片段。HTTP 客户端禁用环境代理与重定向，固定 API 路由白名单，不将 token 放入工具参数、日志或返回值。错误返回安全状态码与 API 错误对象。

API token 可由 `SUMMIT_MCP_TOKEN` 提供，或使用 `SUMMIT_MCP_TOKEN_FILE` 指向权限为 0600 的本机文件。`SUMMIT_API_URL` 默认 `http://127.0.0.1:8793`。启动时读取 workspace 身份并将 `workspace_id` pin 到会话；可通过 `SUMMIT_WORKSPACE_ID` 预设预期身份。所有 agent 专用请求携带该身份，API 在同一次请求中核对活动工作库，切库后拒绝请求，不自动重绑定。

## 工具

| 工具 | 范围 | 副作用 |
|---|---|---|
| `workspace_status` | 当前工作库、索引状态 | 只读，不联网、不调用模型 |
| `list_lines` / `list_projects` | 目录 | 只读 |
| `list_confirmed_pages` | 已确认且资格有效页面元数据 | 只读 |
| `search_confirmed_knowledge` | LanceDB BM25 本机全文检索 | 只读；返回前重读页面并复验版本/资格 |
| `read_confirmed_page` | 指定页面版本正文 | 只读；SHA 不匹配或资格失效则拒绝 |
| `import_text` | UTF-8 文本进入收件箱 | 本机写入；要求 operation_id 幂等，不调用模型 |
| `list_intake` | 收件箱记录 | 只读 |
| `list_pending_drafts` / `get_draft` | 待审稿 | 只读 |
| `create_draft` / `edit_draft` | 完整待审稿提交/编辑 | 本机写入；版本冲突拒绝；不确认、不入库 |
| `read_source` | 显式选择的收件箱来源原件 | 只读；返回标记为未确认材料 |
| `list_calendar` | 显式区间的飞书日历 | 只消费 UI 已批准的一次性计划；MCP 无签发能力 |

此版本不提供 page/draft confirm、任务执行、凭据或任意 URL/路径工具。草稿创建只接受明确字段，拒绝 `approval`、`confirmation_id`、`user_confirmed` 等未知字段；稿件幂等键绑定完整请求内容并先写事务意图供中断恢复。正式页面须由应用用户在审核界面确认；Agent 创建或修改的内容一直只是建议稿。

搜索/读取资格以 `domain/content.py` 为准。当前页面内容必须重新读取并匹配索引 chunk 的 SHA；未确认、非正式区或发生外部语义修改的页面不得返回为知识。索引尚未建立时返回 `index_not_ready`，旧索引返回 `index_rebuild_required`；仅可用索引中没有命中时才返回空列表。不会生成向量或伪造搜索结果。

## 通用配置示例

由启动 SummitEverything API 的本机用户准备 token 文件；在开发启动器下将同一路径同时设为 `SUMMIT_SESSION_TOKEN_FILE` 与 MCP `SUMMIT_MCP_TOKEN_FILE`。示例创建随机 token 文件（token 不输出到终端）：`umask 077; python -c 'import secrets; print(secrets.token_urlsafe(32))' > /path/to/session-token; chmod 600 /path/to/session-token`。不要把 token 字面值写入 MCP JSON。通用 MCP stdio 配置：

```json
{
  "mcpServers": {
    "summit-everything": {
      "command": "uv",
      "args": ["run", "--locked", "--project", "/path/to/SummitEverything", "python", "-m", "summit_everything.mcp_server"],
      "env": {
        "SUMMIT_API_URL": "http://127.0.0.1:8793",
        "SUMMIT_MCP_TOKEN_FILE": "/path/to/owner-only/session-token"
      }
    }
  }
}
```

Codex CLI（命令语法已在本机核验）：

```sh
codex mcp add --env SUMMIT_API_URL=http://127.0.0.1:8793 --env SUMMIT_MCP_TOKEN_FILE=/path/to/owner-only/session-token summit-everything -- uv run --locked --project /path/to/SummitEverything python -m summit_everything.mcp_server
```

WorkBuddy 按其客户端的标准 stdio MCP 配置界面使用同一 command/args/env；此处不假定客户端配置文件位置。实际 token 如何安全取得取决于当前服务启动器，不能从状态端点读取。

WorkBuddy 的用户级配置位于 `~/.workbuddy/mcp.json`，项目级配置位于 `<项目>/.workbuddy/mcp.json`。配置形状见[官方 MCP 指南](https://www.workbuddy.ai/docs/zh/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/MCP-Guide)；连接器文档确认本地 stdio 支持并建议使用稳定协议：[MCP connector](https://open.workbuddy.cn/docs/connector)。示例片段：

```json
{
  "mcpServers": {
    "summit-everything": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "--locked", "--project", "/path/to/SummitEverything", "python", "-m", "summit_everything.mcp_server"],
      "env": {
        "SUMMIT_API_URL": "http://127.0.0.1:8793",
        "SUMMIT_MCP_TOKEN_FILE": "/path/to/owner-only/session-token"
      }
    }
  }
}
```
