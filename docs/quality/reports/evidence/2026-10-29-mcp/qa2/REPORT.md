# MCP CLI 窄修复独立验收

## 身份与范围

- 验收者：独立 QA（固定提交复验）
- 完整待测 SHA：`33e73f96a4271be7b2a2260439799f004acfd65a`
- checkout：`/Users/hanwenbo/.codex/worktrees/summit-mcp-qa/SummitEverything`，detached HEAD；执行前确认工作区干净，验收期间未切换 SHA。
- 系统：macOS 25.5 arm64；Python 3.13.2；uv 0.6.5；项目依赖按锁定文件准备。
- 对照基线：`25ff3933ca87bb2a805607b0ccf5f8434d907af3..33e73f96a4271be7b2a2260439799f004acfd65a`，变更范围为 MCP 启动代码、专项测试和相关文档。
- 仅使用临时合成工作库、Fake 本机 FastAPI；没有使用真实 provider、飞书、Keychain、业务材料、用户配置、App 或 DMG。

## 结果

| 案例 | 结果 | 实际步骤与观察 | 证据 |
|---|---|---|---|
| MCP-CLI-01 非法 URL 配置错误 | PASS | 以 `python -m summit_everything.mcp_server` 和实际 `.venv/bin/summit-everything-mcp` 两入口分别运行 DNS 主机、非 loopback IP、URL 路径和 HTTPS，共 8 个进程。全部 exit 2、stdout 空、stderr 有可理解原因、无 traceback、无秘密回显。 | `config-probe.log` |
| MCP-CLI-02 token 配置错误 | PASS | 两入口分别覆盖缺少 token、带空格的非法 token、缺失 token 文件、格式错误 token 文件和权限过宽的 token 文件，共 10 个进程。全部 exit 2、stdout 空、stderr 有可理解原因、无 traceback、无秘密回显。 | `config-probe.log` |
| MCP-STDIO-01 官方 SDK 会话与工具 | PASS | 官方 MCP Python SDK stdio client 对真实 CLI 子进程执行 initialize、list_tools（14 个工具且 schema 禁止额外字段）及工具调用；覆盖导入/重放、来源读取、待审稿创建/编辑/重放/冲突、未批准日历请求拒绝。 | `pytest.log`；独立黑盒配置与会话测试 `tests/integration/test_mcp_stdio.py` |
| MCP-STDIO-02 合成工作库绑定 | PASS | 对同一 session 打开第二工作库后，`list_lines` 和 `workspace_status` 请求均失败，未静默切换绑定。测试服务和 profile/workspace 均由 pytest 临时目录创建。 | `pytest.log` |
| MCP-SEARCH-01 检索和资格 | PASS | MCP 搜索与页面读取专项通过；详情见本轮 pytest 记录。 | `pytest.log` |
| MCP-DRAFT-01 草稿生命周期 | PASS | agent 草稿专项通过。 | `pytest.log` |
| 静态质量与依赖锁 | PASS | Ruff、mypy、uv lock 检查均通过。 | `ruff.log`、`mypy.log`、`lock.log` |
| 真实 Codex/WorkBuddy 配置、真实模型运行时、外部业务门 | NOT_RUN / UNVERIFIED | 未配置真实客户端或连接真实服务；runtime model metadata 未实际暴露。 | 本轮未执行 |

## 实际命令与退出码

- `uv run --locked python .local/qa/mcp-33e73f9/config_probe.py`：exit 0，18/18 子进程断言通过（每个子进程期望 exit 2）。
- `uv run --locked python -m pytest -q tests/integration/test_mcp_stdio.py tests/integration/test_mcp_search.py tests/unit/test_agent_drafts.py`：exit 0，18 passed，1 条 Starlette/httpx 弃用提示。
- `uv run --locked ruff check src tests scripts/run_dev.py`：exit 0。
- `uv run --locked python -m mypy src`：exit 0，48 source files。
- `uv lock --check`：exit 0。
- `git diff --check 25ff3933ca87bb2a805607b0ccf5f8434d907af3..HEAD`：exit 0。
- 固定版本核验 `git rev-parse HEAD`：`33e73f96a4271be7b2a2260439799f004acfd65a`。

详细 stdout/stderr、命令结果及退出码见同目录 `config-probe.log`、`pytest.log`、`ruff.log`、`mypy.log`、`lock.log`。

## 补充鉴权探针（QA2）

在本机随机空闲 loopback 端口临时启动 `create_app(session_token="synthetic-correct-token", profile_root=<临时目录>, secret_backend=UnavailableSecretBackend())`，未连接或探测其他服务。官方 CLI 两种入口分别执行以下两种认证状态：

- 语法合法但错误的合成 token：API 返回 401 后 CLI exit 2，stdout 空，stderr 为“API token 无效或已过期”的友好提示，无 traceback 或 token 回显。
- 正确合成 token，但没有打开/选择工作库：API 返回未打开工作库状态后 CLI exit 2，stdout 空，stderr 提示先在 SummitEverything 应用中打开工作库，无 traceback 或 token 回显。

四个组合全部 PASS。命令 `PYTHONPATH=src uv run --locked python .local/qa/mcp-33e73f9/auth_probe.py` exit 0；每个子进程预期 exit 2。探针源码 `auth_probe.py`，原始结果 `auth-probe.log`。此补充只扩充鉴权证据，不重跑前述测试，也不覆盖或改写其来源。

## 缺陷

本次范围内未发现缺陷。语法合法但错误 token 的 API 401 错误处理路径由本节随机 loopback Fake FastAPI 探针覆盖；未连接真实运行服务。

## 门结论

- CLI 启动错误处理：PASS。
- MCP stdio SDK 与本机合成 API/工作库：PASS。
- 搜索、草稿和指定静态检查：PASS。
- 真实 provider、真实客户端配置、真实业务材料、Keychain、DMG/安装、五日、双机和发布门：NOT_RUN。
- runtime model metadata：UNVERIFIED。

以上是本 SHA 的独立窄范围验收，不将此前 `222b460` 的全量 757 项通过记录迁移为本 SHA 证据，也不替代 Sol 的最终阶段判门。
