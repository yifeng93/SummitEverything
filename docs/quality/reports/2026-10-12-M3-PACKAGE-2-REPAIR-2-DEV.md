# M3 包 2 repair 2 Developer 报告

日期：2026-10-12。此次为包 2 最后一轮自动修复（repair 2/2），不是 QA 报告或阶段结论。

## 固定代码与处理范围

- 修复前固定起点：`7de63ac28ddde6361230727045695ff0e96553bb`（包含 repair 1 QA 原报告与证据）。
- 固定源码提交：`51891ef5d6ed13461d1595fd99d448b6a159ee25`。
- 最终文档交接提交：见 `LATEST-IMPLEMENTATION.md` 顶部；该提交只更新交接文档，不变更受测产品源码。
- 保留原始首轮 QA FAIL 与 repair 1 QA FAIL 报告及证据；没有更改 QA 期望或移除测试。

## 修复行为

检索规划器每次查询临时读取当前 manifest 的线/项目名称，以及通过统一 HISTORY 资格门确认的正式页面标题、显式别名和页面正文中短而明确的“主体的……”称谓线索；不建立持久 alias/NLP 索引。识别主体时优先匹配这些语料线索，因此礼貌请求前缀不会变成检索过滤词。语料未识别时，只对可解析的明确主体保守过滤；不确定的完整请求不猜实体。

只有以指代词开头的短追问才从最多 8 条真实 user question 中倒序查找主题。中间的指代追问可跳过；最近的完整问题无论含已知主体、未知主体或没有主体，都会成为主题边界。未知或无法确定的边界不会借用更早主题，并对 fact 返回无引用的缺资料结果。assistant 历史答案不进入主题推断或检索依据。已有每轮当前/历史资格、hash 和引用有效性复核保持不变；comparison / plan 不套用 fact 主体过滤，仍可跨材料检索。

## 复验范围及开发者检查

新增回归覆盖不同自然请求前缀与非 QA 合成项目名、未知主体负控、青岚→指代→指代连续追问、切到已知/未知新主题、完整无主题问题边界、页面更新并重新确认后旧索引引用失效，以及比较和方案跨项目检索。聚焦命令：

```sh
uv run pytest tests/integration/test_qualified_retrieval.py tests/integration/test_answer_context.py -q
```

结果：16 passed。README 全量后端和 Web / 类型 / 静态 / 构建矩阵逐条记录于 `.local/dev/m3-package-2-repair-2/`，所有 `.exit` 为 0：

| 检查 | 结果 |
|---|---|
| `npm --prefix web ci` | PASS，126 packages，0 vulnerabilities |
| `uv sync --locked --group dev` | PASS |
| guarded `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | PASS，404 passed |
| `uv run ruff check src tests` / `uv run ruff format --check src tests` | PASS |
| `uv run mypy src` | PASS，40 source files |
| `uv lock --check` / `uv build` | PASS |
| `npm --prefix web run api:types` | PASS，生成 OpenAPI 类型；生成文件没有产品契约差异 |
| `npm --prefix web test` / `npm --prefix web run typecheck` | PASS，52 tests / 12 files；typecheck PASS |
| `npm --prefix web run lint` / `npm --prefix web run build` | PASS；lint 保留 TodayView / ProjectsView 两条既有 warning |

pytest 另有一条既有 Starlette/httpx deprecation warning。完整命令原文、日志与真实退出码见上述本地忽略目录。未运行真实服务、模型、材料、凭据、Keychain、DMG 或发布操作；runtime 元数据 UNVERIFIED。

## QA 交接

固定 `51891ef5d6ed13461d1595fd99d448b6a159ee25` 后由全新独立 QA checkout 复演 repair 1 QA 报告中的自然礼貌事实问句和多轮青岚→“它呢”→“它什么时候启动”缺陷，并覆盖上列新回归、每轮资格门及比较/方案负控。QA 应保留并引用此前两个 QA FAIL 及各自 SHA，不在本开发 checkout 改实现。此提交只表示 Developer 自测完成，Sol 尚未判包 2 状态；repair 2 是最后获准的自动修复轮次。
