# M3 包 1 独立 QA — bc3deab

## 身份与范围

- **受测集成 SHA：** `bc3deabcc4cb6c18a9e8b4809b0ac19e9f20dfb4`。测试前后 HEAD 均为此 SHA；产品目录 `src/ tests/ web/ native/` 与 repair 源码 SHA `a9078bd327f73f2cde3bab14a8665885d0f57c1c` 的 tree 完全一致。
- **范围：** M3 包 1 会话持久化、首问与服务端会话 ID、历史 list/reopen/续问/delete、SSE 完成/取消/断流/重启恢复、request ID 幂等、workspace/profile 隔离、历史引用资格和打开版本提示；对应 C14、C21 历史部分、C13 历史引用部分。
- **环境：** 独立 checkout；仅 loopback Uvicorn/Vite、Fake embedding/reranker、空白合成工作库和隔离 profile。真实 Feishu、模型、凭据、Keychain、业务材料、DMG 均未使用。
- **本轮 QA 产物：** 本报告与同名证据目录；完整 stdout/stderr 与退出码留在忽略目录 `.local/qa/m3-package-1-r1/logs/`，独立黑盒脚本和临时库在 `.local/qa/m3-package-1-r1/`。

## 案例结果

| 案例 | 结果 | 观察到的结果 |
|---|---|---|
| C14-QA-01 新库首问、历史、重开、同 ID 续问 | **PASS** | 真实浏览器新建空库后首问返回完成并立即出现在历史；重开该会话后续问，列表变为 2 个问题。真实 Uvicorn 的 reopen 路由对首问和续问均使用同一服务端 conversation UUID；SQLite 两条 query 均属于该 UUID。实际浏览器请求 JSON body 未通过 DevTools 面板捕获，见未测项。 |
| C14-QA-02 历史 API 读取与删除 | **PASS** | 独立 API harness 读取详情/reopen 成功；真实 WebUI 删除一条合成会话后，该行从历史列表消失。 |
| C14-QA-03 SSE 完成与稳定 request ID | **PASS** | 真实 Uvicorn SSE 序号连续 `1..6`，顺序为 `status, citation, citation, delta, delta, completed`，唯一终态为 completed。相同 request ID 与 payload 回放完全相同的 3,402-byte SSE；conversation ID 不变。相同 ID 换问题返回 `409 intent_conflict`。无 conversation ID 的首次 API 请求返回 `X-Conversation-ID`；显式不存在 ID 返回 404。 |
| C14-QA-04 浏览器取消 | **PASS** | Uvicorn 使用延迟 Fake embedding；收到 status 后对真实取消路由发 DELETE，返回 202。流事件为 `status, error(cancelled)`，序号 `1,2`，唯一终态；历史为 `cancelled`，答案空，没有 completed。 |
| C14-QA-05 非空 partial 断流与进程重启 | **PASS** | 在真实 Uvicorn SSE 收到 status、5 个 citation 和首个 delta（120 字符）后杀死服务进程；连接没有收到终态。重启同 profile 后历史为 `interrupted`，保留 120 字符和 7 个事件。相同 request ID 重放原有 7 个事件，没有 completed，也没有新 query；历史状态继续为 interrupted。 |
| C21-QA-01 workspace/profile 历史隔离 | **PASS** | 真实 UI 切到第二合成 workspace 时历史为空，切回首个 workspace 后历史恢复。第二 profile 打开同一工作库后起始历史为空；其查询 ID 在 profile A 显式使用返回 404，也不出现在 profile A 列表。profile A 创建的第二 workspace 同样没有首个库历史。 |
| C21-QA-02 本机状态不进入同步库语料 | **PASS** | 问题、回答与 SSE 历史 SQLite 位于 profile/workspace-ID 目录。合成工作库文件树没有 `conversations.sqlite3` 或其他历史数据库；页面索引由正式页面文件创建。 |
| C14/C13-QA-06 更新引用与打开边界 | **PASS** | 历史 SQLite 保留旧 hash `b42f…d71c62`、旧北馆 excerpt 和原 validity。重开后卡片显示“原引用版本已更新”。点击引用后，真实页面 GET 携带原 `expected_content_sha256` 并返回 409，随后 current GET 返回 200；目标页持续显示“当前显示的是新版本，不能替代原回答依据。”正文为新西馆版本。 |
| C14/C13-QA-07 unavailable 历史引用 | **PASS** | 将隔离合成页移出工作库后，页面 API 404；历史仍保留原 hash、excerpt、validity，availability 变为 unavailable。WebUI 显示“原引用已不可用”；点击没有导航。 |
| C13 历史效力部分 | **PASS（部分范围）** | 已归档项目内的当前页仍可由 current 问答引用；superseded 页不进入 current 查询，在 history 查询中被引用且返回/保存 `validity=superseded`。这只证明包 1 历史引用与资格切片，不代表 C13 全行通过。 |

本轮没有观察到 P0/P1/P2 产品缺陷。首轮 QA 报告中的 P1 首问 404 和 P2 updated 提示消失，在新 SHA 上分别通过真实浏览器复演；首轮 FAIL 报告保持原样。

## 自动门禁

所有命令均在固定 SHA 独立 checkout 执行；日志文件名对应 `.local/qa/m3-package-1-r1/logs/` 下同名 `.log` 与 `.exit`。

| 命令 | 结果 |
|---|---|
| `cd web && npm ci` | **PASS**, exit 0；126 packages，0 vulnerabilities |
| `uv sync --locked --group dev` | **PASS**, exit 0 |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | **PASS**, exit 0；395 passed，1 条既有 Starlette/httpx deprecation |
| `uv run ruff check src tests` | **PASS**, exit 0 |
| `uv run ruff format --check src tests` | **PASS**, exit 0；70 files 已格式化 |
| `uv run mypy src` | **PASS**, exit 0；38 source files |
| `uv lock --check` | **PASS**, exit 0 |
| `uv build` | **PASS**, exit 0；sdist 与 wheel 成功 |
| `npm --prefix web run api:types` | **PASS**, exit 0 |
| `npm --prefix web test` | **PASS**, exit 0；12 files / 49 tests |
| `npm --prefix web run typecheck` | **PASS**, exit 0 |
| `npm --prefix web run lint` | **PASS**, exit 0；保留 TodayView / ProjectsView 两条既有 effect warning |
| `npm --prefix web run build` | **PASS**, exit 0；Vite production build 成功 |

`uv.lock` SHA-256 为 `148ac7c5d1d795ec0ee17384bca7c2173dddb6ba8945b23445da71356c9bfbda`，`web/package-lock.json` 为 `d7b39319f006b0280857a02f3932f7e71e8d38cd0e63a0684f9b41f0d9c26ad3`。OpenAPI/TypeScript 生成前后没有 tracked diff；锁文件和生成文件均未改变。

## NOT_RUN / UNVERIFIED 与风险

- 实际浏览器没有可用 DevTools network/console 面板；首问 UI 闭环和服务端 UUID 已通过真实浏览器、Uvicorn access log、SQLite 复验，但首问 request body 的字段和该次浏览器响应头没有被网络面板直接导出。独立真实 API 黑盒确认无 ID 创建、响应头 ID、续开和未知 ID 404。console error/warn capture 为 **NOT_RUN**。
- Runtime 实际暴露的模型/profile 元数据为 **UNVERIFIED**；不能从配置推断。
- 原生 UI、DMG、真实 provider/资料/凭据/Keychain、五日和双机均 **NOT_RUN**。
- 完整多轮上下文是否送入模型属于包 2，**NOT_RUN**；本报告不声明整个 C13、C14、C21 或 M3 通过。

**QA 范围状态：** 本报告列出的包 1 离线黑盒及 README 适用自动门禁均 PASS；最终包级/阶段门由 Sol 决定。没有 P0/P1/P2 遗留缺陷建议转交修复。

## 工作树与服务

受测期间源码 SHA 保持 `bc3deabcc4cb6c18a9e8b4809b0ac19e9f20dfb4`；产品目录与 `a9078bd327f73f2cde3bab14a8665885d0f57c1c` 无差异。依赖锁、既有 tracked tests、源码和产品配置没有改动。QA 报告提交前工作树只包含本报告/evidence；所有隔离 Uvicorn/Vite 服务已停止，端口 18793、18794、18795、15173 均无监听。

可复演步骤、脱敏 UI/route 观察及证据 manifest 见[本轮证据目录](evidence/2026-10-11-m3-package-1-qa-bc3deab/README.md)。
