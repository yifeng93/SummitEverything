# MCP 独立 QA 报告

- 被测 SHA：`222b46062fa9fff0cee52deb202c71698e1365ba`
- 基线比较：`d7af7d5..222b46062fa9fff0cee52deb202c71698e1365ba`
- checkout：独立 detached worktree；HEAD 验证固定，未切换或更新
- 数据：FastAPI loopback + 临时合成工作库；未访问真实 provider、Keychain、业务材料、飞书或 DMG
- 日志与黑盒探针：本目录

## 结论摘要

当前固定 SHA 存在 1 项 CLI 配置错误（P2）：配置非法 `SUMMIT_API_URL` 时异常发生在入口异常处理器外，程序返回 exit 1 并输出 traceback，未给出契约承诺的友好配置提示。无 token 回显，且不会连接非 loopback API。

其余本轮执行项目通过。此报告不代替 Sol 的最终阶段判门。

## 结果

| 场景 | 状态 | 证据 |
|---|---|---|
| 全量离线 pytest | PASS | `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --locked python -m pytest -q`，exit 0，757 passed；`pytest.log` |
| MCP 端到端专项 | PASS | `uv run --locked python -m pytest -q tests/integration/test_mcp_stdio.py tests/integration/test_mcp_search.py tests/unit/test_agent_drafts.py`，exit 0，7 passed；真实 SDK stdio 子进程 ↔ loopback FastAPI ↔ 临时工作库；`blackbox-tests.log` |
| Ruff | PASS | `uv run --locked ruff check src tests scripts/run_dev.py`，exit 0；`ruff.log` |
| Mypy | PASS | `uv run --locked python -m mypy src`，exit 0，48 files；`mypy.log` |
| Lock | PASS | `uv lock --check`，exit 0；`lock.log` |
| initialize/list_tools/schema/tool calls | PASS | 14 工具；每个 schema `additionalProperties=false`；读取目录、来源、稿件、索引状态；stdout 为 stdio 协议，由 SDK 客户端解析 |
| 未知审批字段/操作面 | PASS | `approval` 未知字段调用被拒绝；没有 confirm、任务执行、凭据或任意 URL/路径工具；日历随机未批准 plan 被拒绝 |
| 认证与配置 | FAIL（P2，仅非法 URL 文案/退出路径） | `config_probe.py`：无凭据、格式错误 token、symlink token 文件均 exit 2 且无 stdout/秘密回显；非 loopback URL 与路径 URL exit 1 并输出 traceback，详见下方缺陷 |
| 工作库 pin | PASS | 同一 MCP session 切换活动工作库后读取/status 请求失败；不会重绑；专项测试覆盖读取状态与目录拒绝 |
| BM25/资格/版本 | PASS | 临时 LanceDB 命中当前已确认页；未确认与历史页不返回；外部改写后搜索不返回旧 chunk、按旧 SHA 读取返回 409；空/旧索引明确返回 `index_not_ready` / `index_rebuild_required`，不调用 embedding |
| 来源/草稿生命周期 | PASS | 同 operation 导入与草稿重放稳定；改 payload 冲突；稿件编辑版本递增/版本冲突拒绝；应用 API 显式确认后稿件为 confirmed、来源 completed；MCP 无批准能力 |
| 草稿部分写入恢复 | PASS（已覆盖故障点） | `recovery_probe.py` 在 draft 写后、job 写前注入中断；重放能补完，编辑/确认后的重放保留正文/确认状态，来源最终 completed；日志 `recovery-confirm-probe.log` |
| 目标页范围/版本 | PASS | 自动化用例拒绝另一项目目标页及未配对 base；对应 `blackbox-tests.log` |
| CLI 无遗留进程 | NOT_RUN | CLI 服务进程在 API 启动失败时结束；没有另外做操作系统级进程清点 |
| runtime model metadata | UNVERIFIED | 配置值不构成实际运行时证明 |
| 实际 Codex/WorkBuddy 配置、真实外部门、Keychain、DMG、双机 | NOT_RUN | 本轮未授权真实连接或真实材料验收 |

## 缺陷：非法 API URL 绕过 CLI 友好错误处理

严重度：P2（可用性/诊断，不是凭据泄漏）。

最小复现：

```sh
SUMMIT_API_URL=http://example.com:8793 SUMMIT_MCP_TOKEN=synthetic-token \
  uv run --locked python -m summit_everything.mcp_server
```

实际：exit 1；`ValueError` 的 traceback 指向 `ipaddress.ip_address()`。把 URL 改为 `http://127.0.0.1:8793/prefix` 也在 `Bridge()` 构造时失败并返回 traceback。预期：CLI 捕获 `MCPConfigurationError`，stderr 显示可理解的本机配置错误，exit 2。两种情况下均未建立外部连接，未回显 token。

复验：`uv run --locked python .local/qa/mcp-222b460/config_probe.py`，exit 1 是探针发现两项预期不符；missing token、bad token、symlink token 三项 PASS。原始输出 `config-probe.log`。

## 其他记录

- 第一次普通 `uv run --locked ruff/mypy` 因此 QA checkout 的 `.venv` 未装 dev 命令 shim 而报 `Failed to spawn`。按 lock 执行 `uv sync --locked --group dev`；ruff 又用 `uv sync --locked --group dev --reinstall-package ruff` 修复缺失 binary。最终 Ruff/Mypy 检查均 PASS，未更改项目源文件或依赖锁。
- `git diff --check d7af7d5..222b46062fa9fff0cee52deb202c71698e1365ba` exit 0。
- 单元/集成测试有一条 Starlette `TestClient` 与 httpx 的 deprecation warning，不影响通过结果。
