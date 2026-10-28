# MCP DEV 原始命令证据

适用源码 SHA：`222b46062fa9fff0cee52deb202c71698e1365ba`。

| 文件 | 命令 / 结果 |
|---|---|
| `targeted-pytest.log` | `uv run --locked python -m pytest -q tests/integration/test_mcp_stdio.py tests/integration/test_mcp_search.py tests/unit/test_agent_drafts.py` — exit 0，7 passed。 |
| `ruff-check.log` | `uv run --locked ruff check src tests scripts/run_dev.py` — exit 0。 |
| `ruff-format.log` | `uv run --locked ruff format --check src tests scripts/run_dev.py` — exit 0，109 files formatted。 |
| `mypy.log` | `uv run --locked python -m mypy src/summit_everything` — exit 0，48 files。 |
| `lock-check.log` | `uv lock --check` — exit 0，72 packages。 |
| `pytest-full-prior.log` | 全量回归历史原始输出，exit 1，756 passed / 1 failed；唯一失败是旧错误文案断言，修正后该坏 token 用例在上述 targeted pytest 中通过。SHA-256 `39cade1591a07bbc8ae6bc30a112af845669b97f3e4c9346118050be5f18cb49`。 |

全量套件未在当前固定 SHA 重跑，因此全量结论仍为 NOT_PASS，不能引用 targeted 结果推断全量通过。原始完整输出来自执行 worktree 的 `.local/mcp-20261029/pytest-full.log`。
