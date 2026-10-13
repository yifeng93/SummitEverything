# 浏览器与黑盒证据 — c90fe6e

受测 SHA：`c90fe6e2bec5677deb7b069b86fa8971da1d8dcd`。观察来自 Codex in-app browser 对 `127.0.0.1` 隔离服务的实际操作。profile/workspace 全为 `.local/qa/m3-package-1/` 下的合成数据，未填入真实材料或凭据。浏览器 console capture 用 `tab.dev.logs({levels:["error","warn"],limit:50})` 读取，结果 `[]`。没有可用 DevTools network 面板；网络证据是服务自身 Uvicorn access log 和 curl 对 loopback 的观察，不含 headers/token。

## 首问失败 (P1)

干净 profile 和刚建的合成 workspace 下，在问答页输入普通非空合成问题并提交。观察到 UI 显示“本次回答 · 连接中断 / 知识问答暂不可用”，列表没有新历史。服务 access log 显示：

```text
POST /api/v1/queries 404 Not Found
POST /api/v1/conversations/fd075a48-e281-46d3-9264-7b1cc41737c5/reopen 404 Not Found
```

`fd075a48-e281-46d3-9264-7b1cc41737c5` 是当次 UI 自动生成并请求 reopen 的临时会话 ID，不是用户数据。随后用同一真实 API route 在已选 workspace 请求时省略 `conversation_id`，返回 SSE status(seq 1)、delta(seq 2)、completed(seq 3) 并持久化会话。源码读查确认 AskView 为新对话随机生成 id 后提交；store 对未创建 id 返回 not found。由此限定故障在 WebUI 首问与后端创建契约衔接，不是工作库未建、索引未就绪或 Fake answer 的结果。

## 历史 / workspace UI 复演

第一次 API 创建对话后，WebUI 历史展示首问；再次打开同一会话能恢复回答；在该会话内续问后历史计数从 1 变 2；“删除”按钮后显示空历史。将同一个 UI 连接至第二个 workspace，历史为空；切回第一个 workspace，原历史复现。第二个 profile 打开同一个 workspace 时历史为空。服务进程重启后，已完成和 interrupted 会话仍可列出并打开。服务器请求状态保存在 profile 下按 workspace id 分开的 `conversations.sqlite3`；合成 workspace 文件树不含该数据库。

## 引用与真实 reader 门

使用本机真实 WebUI、FastAPI route、workspace writer / confirmation、SQLite `IndexStore`、`QueryService`、页面资格 reader 和历史 route。替代范围仅 `FakeEmbedding` 与 `FakeLLM`：fake embedding 用来建索引；fake answer provider 返回可辨识的“合成回答”。合成页面 API 建立并确认，索引返回 1 page / 1 chunk，随后真实 query 生成 citation / delta / completed 事件。

初始页面正文“本次合成会议的地点是北馆。”，citation 保存 `content_sha256=fb36347059da01dcf9aa54698fe68bf694b7befee7689594077a17a74504cb89` 和该 excerpt。浏览器引用卡显示“引用版本仍可用”，点击后打开正确的稳定页面并看到北馆。通过真实 API 确认更新页面为“西馆”后，历史 detail 仍保留原 hash 和北馆 excerpt、可用性改为 `updated`。浏览器卡显示“原引用版本已更新”；点击后正确打开当前西馆页面，但没有显示“现在打开的是当前页面，不能替代原回答依据”提示。AskView 设置 notice 后马上调用 `onOpenPage`，离开问答组件即看不到 notice。

移出隔离 workspace 的合成页面文件后，真实历史 detail 仍保留原 hash/excerpt 并将 availability 更新为 `unavailable`；UI 卡显示“原引用已不可用”。点击该卡没有导航，也没有额外 AX tree 变化。页面文件之后恢复到原合成路径，便于后续查询/清理。

## 实际浏览器取消

同一真实 `QueryService`、route、store、WebUI 运行；仅 embedding fake 对前缀 `QA-CANCEL-PROBE:` 延迟 8 秒。快速提交后 UI 显示“停止回答”，点击后历史状态为“已取消”，当前 turn 文本为“尚无回答内容 / 查询已取消”。SQLite 验证 request `d6aa5d94-aa98-43b9-98cf-78ac011d0eac` state=`cancelled`、answer 空，事件严格为 seq 1 `status(retrieving)`、seq 2 `error(code=cancelled)`，没有 completed。服务 log 同时有 `POST /api/v1/queries` 200 与 `DELETE /api/v1/queries/{id}` 202。无自动重发。

## 真 transport 断开

对真实 Uvicorn `8873` 发送 curl 请求并将 client deadline 设为 0.01s；收到 seq 1 status 后 curl 以 28 退出。再次通过 API detail/list 观察到该对话与查询已存储，state=`interrupted`，answer 空，仅一个 status 事件，无 completed。UI 重启后显示“连接中断”并可重新打开该历史。原始文件：`api-transport-disconnect.txt`、`.stderr`、`-detail.json`、`-history.json`。该复演没有产生非空 partial；部分文本保留只由全量 integration suite 覆盖。

## 不作为产品失败的准备观察

- 第一轮全量 pytest 在 `npm ci` 前失败，因为干净 checkout 缺 `web/node_modules`，runner 测试中的 runner process exit 2。执行 README 所需 `npm --prefix web ci` 后完整复跑 395 passed，原失败和成功日志都保留。
- harness 第一次从 Vite `5275` 访问 API 时被 harness 的本机 origin allowlist 403 拒绝。仅在 `.local` harness 增加该临时 Vite origin 后重测；产品 CORS 未改。
- 曾尝试通过 API 将已确认页面直接标为 invalid，writer 按 qualification 规则以 422 拒绝该非法转换。后续用移出合成文件的方式测试引用 unavailable，不把 422 记为产品缺陷。

复演原始 stdout/stderr、API payload 与历史 detail、Uvicorn/Vite logs 在 `.local/qa/m3-package-1/`（只包含 QA 合成数据）。`sha256.txt` 将每项哈希绑定到独立 QA checkout 路径。
