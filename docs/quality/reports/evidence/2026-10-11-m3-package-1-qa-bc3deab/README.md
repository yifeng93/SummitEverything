# M3 包 1 QA 证据 — bc3deab

受测 SHA：`bc3deabcc4cb6c18a9e8b4809b0ac19e9f20dfb4`。以下证据仅含本机 loopback、Fake providers 与合成内容。

## 真实浏览器观察

浏览器为 Codex In-app Browser 标签 `http://127.0.0.1:15173/`，由 CUA 读取 accessibility tree 并实际点击。Chrome DevTools MCP/network 面板未配置。

1. 新建“QA 合成库”后，问答页显示“还没有问答历史”。提交“首问记录：本机合成问答是否能建立历史？”后，真实 UI 显示一条“已完成”历史；Uvicorn 记 `POST /api/v1/queries 200 OK`。
2. 点击历史重开，提交“续问记录：同一会话应保留服务端身份。”后 UI 的同一行显示“2 个问题 · 已完成”。SQLite 显示 conversation `33bcf763-0310-4d17-9799-92a31ff9adcc` 下有首问与续问两条 query；Uvicorn 两次 reopen 使用该同一 UUID。
3. 查看更新时间前创建的引用，浏览器历史卡为“原引用版本已更新”；点击后目标 PageReader 显示旧版本提示，并显示当前正文“西馆模拟仓库现在有 5 个测试箱”。Uvicorn 观察到：

   ```text
   GET /api/v1/pages/7106f1ac-c9eb-4fe6-ab16-ab293c183129?expected_content_sha256=b42fb761119bf3c7c3cd8bbd1012900aa921ca62908b9b93dcde2aca21d71c62 -> 409 Conflict
   GET /api/v1/pages/7106f1ac-c9eb-4fe6-ab16-ab293c183129 -> 200 OK
   ```

   页面持续显示：“引用保存的是回答当时的页面版本；该页面已更新。当前显示的是新版本，不能替代原回答依据。”
4. 将合成页移出工作库后重新打开对应历史，卡片显示“原引用已不可用”；点击后页面未导航。
5. 点击工作库选择器打开第二个空合成库，历史显示“还没有问答历史”；切回“QA 合成库”后原历史恢复。UI 删除测试会话后其历史行消失。

## 真实 API / SQLite 黑盒观察

无 `conversation_id` 首问返回 SSE 200 和 `X-Conversation-ID`。同一 request ID/payload 重放获得 byte-identical SSE；修改 question 返回 409 intent_conflict；显式未知 conversation ID 返回 404。事件 `seq` 连续、唯一终态。

Profile B 打开同一工作库后初始列表为空；在 B 创建的 ID `d7a5525f-b8be-45ef-9946-96d833303692` 被 profile A 显式使用时返回 404，且不在 A 列表。第二 workspace 历史为空；重开第一个 workspace 后历史恢复。

长合成回答在实际 Uvicorn SSE 中读到首个 120 字符 delta 后强制终止服务。响应端没有收到终态。重启后状态 `interrupted`，保存 7 个事件和 120 字符 partial；重放相同 request ID 只发出已保存的七个事件，仍无 completed。

C13 子场景：归档项目内 current 页面仍能被 current query 引用；superseded 页面从 current query 排除，在 purpose=history 的查询与持久引用中带 `validity=superseded`。

问答数据库位于 `.local/qa/m3-package-1-r1/profile-a/<workspace-id>/conversations.sqlite3`；工作库文件树没有问答数据库。完整 HTTP access logs、SQLite 检查与 API 响应分别见 `.local/qa/m3-package-1-r1/logs/dev-server*.log`、`profile-b-api.log`、`cancel-api.log`、`blackbox-contract.log`、`isolation.log`、`c13-history.log`、`kill-during-partial.log`、`restart-partial.log`、`real-cancel.log`、`unavailable-reference.log`。

## 复演命令

依赖与自动门禁按 [M3 包 1 QA 报告](../../2026-10-11-M3-PACKAGE-1-QA-bc3deab.md) 的命令表重跑。定制黑盒脚本保存在独立 checkout 忽略目录 `.local/qa/m3-package-1-r1/`：

- `uv run python .local/qa/m3-package-1-r1/blackbox_contract.py`
- `uv run python .local/qa/m3-package-1-r1/isolation.py`
- `uv run python .local/qa/m3-package-1-r1/c13_history.py`
- `uv run python .local/qa/m3-package-1-r1/unavailable_reference.py`
- `uv run python .local/qa/m3-package-1-r1/real_cancel.py`
- `uv run python .local/qa/m3-package-1-r1/kill_during_partial.py`（此脚本会故意 SIGKILL 当前隔离 QA Uvicorn PID；执行前应仅启动本轮专用服务，并按 `restart_partial.py` 重启后验状态。）
- `uv run python .local/qa/m3-package-1-r1/restart_partial.py`

所有输出均在 `.local/qa/m3-package-1-r1/logs/`，`.exit` 保存真实退出码。QA 报告 commit 只包含报告/evidence 文档，不包含临时工作库、profile、node_modules、build 输出或本地认证测试值。

忽略目录 `.local/qa/m3-package-1-r1/evidence-sha256.txt` 包含本轮 53 个关键 `.log`、`.exit` 与黑盒 Python harness 的 SHA-256，可用于校验原始命令输出和复演脚本。浏览器证据是本文件记录的 CUA accessibility tree 实际观察及相应 Uvicorn route/access log；本轮未保存屏幕截图，DevTools Network/Console 未配置，具体限制见 QA 报告。
