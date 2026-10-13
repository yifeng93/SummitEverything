# M3 包 1 独立验收 — c90fe6e

受测代码固定为 `c90fe6e2bec5677deb7b069b86fa8971da1d8dcd`（产品源码等同 `faf1563d406cf0cf092550f9845626efb9b09c72`，base `5fd91c78930c80b2365957197b8a605757694a91`）。工作位于独立 checkout；测试起止 HEAD 均为受测 SHA。包 1 **FAIL**：发现 1 个 P1 和 1 个 P2，均为实际浏览器复演。没有修改产品源码、tracked tests、依赖或 lock。

## 缺陷

**P1 — UI 新建对话首问必定 404，历史不会创建。** 在干净合成 profile / 工作库打开“知识问答”，输入任意问题并点“开始检索”，浏览器实际发出 `POST /api/v1/queries` 后收到 404；UI 显示连接中断 / 问答不可用，历史列表为空。其后自动 `POST /api/v1/conversations/{随机ID}/reopen` 也返回 404。直接 API 请求省略 `conversation_id` 能正常创建会话，因此后端提供的创建行为与 UI 首问契约不一致。最小复现：启动全新 profile，创建/选择工作库，问答页新建对话后提交任意非空问题。

源定位：[AskView.tsx](/Users/yifengstudio/.codex/worktrees/m3-package-1-qa/SummitEverything/web/src/components/AskView.tsx:148) 在首问时用 `crypto.randomUUID()` 预填 conversation id 并总是提交；[conversations.py](/Users/yifengstudio/.codex/worktrees/m3-package-1-qa/SummitEverything/src/summit_everything/local/conversations.py:209) 将提供但尚不存在的 id 当作已存在会话校验并抛出 `ConversationNotFound`。复演摘要和已有 route/store 对照证据见 `evidence/2026-10-11-M3-PACKAGE-1-QA-c90fe6e/browser-and-blackbox.md`。该失败由真实 WebUI、真实 FastAPI route 和 SQLite store 观察，不是组件 mock。

**P2 — 打开已更新引用没有展示版本变化提示。** 历史答案上引用卡正确显示“原引用版本已更新”；点击会打开该页面当前版本（合成页面从“北馆”更新为“西馆”），但页面切换后没有显示规格要求的提示“当前页面不能替代原回答依据”。实现先在 AskView 内 `setNotice(...)`，再立即 `onOpenPage(...)`；导航卸载 AskView 后提示无处呈现。最小复现：用真实页面/API 建索引并问答，更新页面后从历史打开旧引用，观察被打开页。

源定位：[AskView.tsx](/Users/yifengstudio/.codex/worktrees/m3-package-1-qa/SummitEverything/web/src/components/AskView.tsx:243) 的 `openCitation` 和第 248–250 行。历史卡片与已打开页面均由真实 WebUI 呈现，版本资格由真实 route / `QueryService` / reader 门重验，只有 embedding 与 answer provider 替换为离线 fake。脱敏 DOM 观察、历史引用 hash/excerpt 及 API 请求日志见同一 browser evidence 文件和 `harness-*` 原始日志哈希。

## 案例结果

| 案例 | 结果 | 观察范围与边界 |
|---|---|---|
| 新对话首问 / 创建历史 | **FAIL (P1)** | 实际浏览器 + 真实 route/store；首问 404，历史为空。 |
| API 不带 conversation_id 新建、SSE 完成 | PASS | 本机实际 Uvicorn；事件 seq 单调，唯一 `completed` 终态；具体请求/响应在原始证据。 |
| 列表、重开历史、同会话续提问、删除 | PASS | 实际浏览器；API 创建的会话可读，续问后历史问题数递增，删除后列表为空。只证明续问持久化。 |
| 跨进程重启读取完整及 interrupted 历史 | PASS | 浏览器 / Uvicorn 重启后重新载入历史；中断记录没有被标为完成、没有自动重发。 |
| 对话隔离 | PASS | 实际 UI：同一 profile 切两个合成 workspace 后历史分别为空/恢复；第二 profile 打开同一库不见第一 profile 历史。profile 会话 SQLite 位于 profile 目录，不写入工作库目录。 |
| 稳定 `request_id` 同 payload 回放 | PASS | 真实 API；normalized SSE 完全一致，无额外调用；相同 id 不同 payload 返回 409 `intent_conflict`；同 request id 在不同 workspace 独立。 |
| 活跃查询跨 workspace 误取消 / 误中断 | PASS（自动集成） | 全量集成测试含同 workspace 存储作用域、跨库取消隔离和 live owner 恢复；未额外做真实两个 Uvicorn 同时运行的跨库取消。 |
| 浏览器取消 | PASS | 实际浏览器 + 真 route、store、`QueryService`；只把 `FakeEmbedding` 换为可延迟 8 秒 fake。点击“停止回答”后 UI 和 SQLite 均为 `cancelled`，空答案，仅 seq 1 `status` / seq 2 `error(cancelled)`，没有 `completed` 或自动重发。 |
| 传输断开与恢复 | PASS（断流边界） | 本机真实 Uvicorn + curl 在收到 status 后断开；curl exit 28，历史为 `interrupted`，仅 status、空答案且没有假完成。实时断流没有制造非空 partial；partial 保留由全量集成测试覆盖，未冒充为真实 transport partial 复演。 |
| 当前引用 / 更新 / 缺失 | **P2 FAIL**（更新提示）；其他 PASS | 真页面/API 写入确认合成页、建 fake 索引和真实查询；旧 hash `fb36347059da01dcf9aa54698fe68bf694b7befee7689594077a17a74504cb89` 与“北馆”excerpt 不变；current 页面变“西馆”后标 `updated`；移走页面后标 `unavailable`，UI 明示“原引用已不可用”且点击不导航。打开 `updated` 页面时必要提示缺失。 |
| 历史进入工作库/检索语料 | PASS（本地隔离） | 合成 workspace 仅包含页面及 workspace 元数据；`conversations.sqlite3` 位于 profile/workspace-id 子目录。未发现历史数据库/回答文本写入 workspace 文件树；索引由页面真实 API 单独构建。 |
| 多轮上下文进入模型请求 | NOT_RUN / 范围边界 | 当前实现重开保留 `conversation_id`，但之前消息没有拼入下一次模型请求；完整上下文多轮问答属于 M3 总要求，Developer 计划放包 2，不能将本项记为通过。 |
| C13 历史引用部分 | PARTIAL | 已观察旧引用 current→updated→unavailable 与不可用标记；未构造 superseded/归档业务场景。不能据此宣布 C13 全行通过。 |
| C14 历史/流部分 | **FAIL** | SSE 序号/终态、取消、传输断开通过；引用更新提示失败，另有首问 P1。 |
| C21 历史隔离部分 | PASS | workspace 和双 profile 历史隔离 / 库切换完成；角色、记忆和全索引同步仍不属于包 1 本轮范围。 |

真实 Feishu / 模型 / embedding / rerank、Keychain、DMG、发布门、五日和双机均 **NOT_RUN**。合成 answer provider 输出固定文本，不能据此判断检索问答质量、真实模型行为或价格。仅 `FakeEmbedding` 的延迟被用于真实取消路由测试；引用路径案例使用 fake embedding 和 fake answer，但保留真实页面 writer/reader、SQLite 索引和资格门、查询服务、HTTP route 及 WebUI。

## 自动门禁

| 命令 | 退出 | 结果 / 原始日志 |
|---|---:|---|
| `uv sync --locked --group dev` | 0 | `.local/qa/m3-package-1/uv-sync.log` |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q`（初次） | 1 | 394 passed / 1 failed；隔离 checkout 缺少 `web/node_modules`，runner 子进程以 2 退出，属环境准备问题；`pytest.log`。 |
| `npm --prefix web ci` | 0 | 126 packages，audit 0；`npm-ci.log` |
| 同上全量 pytest（安装 Web 依赖后） | 0 | 395 passed，1 条现有 Starlette/httpx TestClient deprecation；`pytest-after-npm-ci.log` |
| `uv run ruff check src tests` | 0 | `ruff-check.log` |
| `uv run ruff format --check src tests` | 0 | 70 files formatted；`ruff-format.log` |
| `uv run mypy src` | 0 | 38 source files；`mypy.log` |
| `uv lock --check` | 0 | `lock-check.log` |
| `uv build` | 0 | sdist + wheel；`uv-build.log` |
| `npm --prefix web run api:types` | 0 | OpenAPI / TS types generated；`api-types.log` |
| `npm --prefix web test` | 0 | 11 files / 47 tests；`web-test.log` |
| `npm --prefix web run typecheck` | 0 | `web-typecheck.log` |
| `npm --prefix web run lint` | 0 | 保留 TodayView、ProjectsView 两条已有 warning；`web-lint.log` |
| `npm --prefix web run build` | 0 | `web-build.log` |
| `cd native && swift build` | 0 | README 开发壳源码构建成功；原生 UI 因系统锁屏未启动；`native-build.log` |

OpenAPI 及 TS generated 文件生成前后无 diff；`uv.lock` 与 `web/package-lock.json` 未改，哈希分别为 `148ac7c5d1d795ec0ee17384bca7c2173dddb6ba8945b23445da71356c9bfbda`、`d7b39319f006b0280857a02f3932f7e71e8d38cd0e63a0684f9b41f0d9c26ad3`。Developer 原始日志只作旁证，本轮通过独立 checkout 自己运行，结果不以 Developer 报告替代。

## 证据与状态

可复演命令、UI/网络/console 观察、真实与替代层说明见 [`evidence/2026-10-11-M3-PACKAGE-1-QA-c90fe6e/browser-and-blackbox.md`](evidence/2026-10-11-M3-PACKAGE-1-QA-c90fe6e/browser-and-blackbox.md)；原始日志均留在隔离 checkout `.local/qa/m3-package-1/`，摘要文件 SHA-256 清单随报告提交。初次依赖准备失败也予保留。运行时浏览器 console error/warn capture 为空；DevTools network 面板 API 不可用，HTTP 观察来自真实浏览器触发与真实 Uvicorn access log，不包含请求头 / token。原生 Mac 应用不可用（系统报告已锁屏）；此门不适用包 1 且未测。

测试期间无 tracked source/test/lock 变化。实测使用的服务器和 Vite 会话均已停止。QA commit 只包含此报告和脱敏证据文件，父提交是受测 SHA；因此受测产品树保持原样。
