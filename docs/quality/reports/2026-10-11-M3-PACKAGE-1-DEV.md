# M3 功能包 1：会话与历史 — Developer 报告

## 身份与范围

> 本报告记录首轮源码交付 `faf1563d406cf0cf092550f9845626efb9b09c72`，不覆盖其后的修复。独立 QA 对后续固定提交 `c90fe6e2bec5677deb7b069b86fa8971da1d8dcd` 判 FAIL；原报告保留，repair 1/2 的缺陷整改和新自测见[追加报告](2026-10-11-M3-PACKAGE-1-REPAIR-1-DEV.md)。

- 执行角色：Developer Luna；本报告是实现者自测，不是独立 QA 结论。
- 基线：clean main `5fd91c78930c80b2365957197b8a605757694a91`。
- 分支：`codex/m3-integrated-packages`。
- 固定源码 SHA：`faf1563d406cf0cf092550f9845626efb9b09c72`。最终文档整合提交会在最新交接记录中列出；QA 应固定交接文档后的分支 HEAD，源码与本 SHA 相同。
- 覆盖：本机 profile / workspace 隔离的问答历史与查询事件、稳定 request ID、SSE partial 和终态恢复、历史引用版本提示、API 与 WebUI；相关验收范围 C14、C21 历史部分、C13 历史引用部分。
- 测试材料：pytest `tmp_path` 下隔离合成工作库、Fake / stub QueryService；没有访问真实业务材料、用户凭据或付费模型。
- 外部门授权及真实外部请求：无；本轮未调用真实飞书 / LLM、未读写 Keychain。

## 交付行为

- 在本机 profile SQLite 中保存会话、问题、回答 partial、按 request_id 单调递增的 SSE 事件及原引用快照；数据以 workspace_id 再隔离，绝不写入可同步工作库或知识语料。
- 提供历史分页、详情 / 重开、删除 API。稳定 request_id + 同请求体只重放已保存事件；不同输入冲突，已在途请求不会再次触发 QueryService。跨 profile / workspace 使用相同 request_id 不串联，也不能越库取消。
- 问答 UI 可列出和恢复历史、在恢复会话中追加提问、取消查询、显示已收到 partial 与异常断流状态；断流后不自动重新发送。
- 持久化 completed / error / cancelled / interrupted 的真实状态。终态事件与状态原子提交；无法向已断开的 SSE 客户端发送终态时不会伪造 completed。进程恢复保留已收到的部分回答。
- 引用保留原 content hash、excerpt 与效力；历史读取时通过 `retrieval_eligibility` 重新检查并标记 available / updated / unavailable。打开 updated 引用明确提示当前页面版本不能替代原回答依据；unavailable 引用不可作为当前依据打开。

产品与类型契约同步：[API-v1](../../contracts/API-v1.md)、[WORKSPACE-v1](../../contracts/WORKSPACE-v1.md)、生成的 OpenAPI JSON 与 TypeScript 类型。

## 自测结果

以下为固定源码 SHA 上实际运行的 README 全量适用门禁。真实 stdout / stderr 在实现 worktree ignored `.local/dev/m3-package-1/logs/`；`final-exit-codes.txt` 记录每个命令的真实退出码。

| 命令 | 结果 | 证据摘要 |
|---|---|---|
| `uv sync --locked --group dev` | PASS，exit 0 | `logs/uv-sync.log` |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | PASS，exit 0 | **395 passed**，1 条既有 Starlette/httpx deprecation；`logs/pytest.log` |
| `uv run ruff check src tests` | PASS，exit 0 | `logs/ruff-check.log` |
| `uv run ruff format --check src tests` | PASS，exit 0 | `logs/ruff-format.log` |
| `uv run mypy src` | PASS，exit 0 | `logs/mypy.log` |
| `uv lock --check` | PASS，exit 0 | `logs/lock-check.log` |
| `uv build` | PASS，exit 0 | `logs/uv-build.log` |
| `npm --prefix web run api:types` | PASS，exit 0 | 生成的 OpenAPI / TypeScript 已纳入提交；`logs/api-types.log` |
| `npm --prefix web test` | PASS，exit 0 | **47 tests / 11 files passed**；`logs/web-tests.log` |
| `npm --prefix web run typecheck` | PASS，exit 0 | `logs/web-typecheck.log` |
| `npm --prefix web run lint` | PASS，exit 0 | exit 0；保留既有 TodayView / ProjectsView 两条 React effect warning；`logs/web-lint.log` |
| `npm --prefix web run build` | PASS，exit 0 | `logs/web-build.log` |
| `git diff --check` | PASS，exit 0 | 在固定源码和文档整合前执行 |

定向闭环：

- `uv run pytest -q tests/integration/test_conversations.py tests/integration/test_app_lifecycle.py tests/integration/test_qualified_retrieval.py` — **18 passed**，包含两 profile 隔离、跨库请求标识、跨 workspace 取消、历史重开 / 重放、分页、真实 partial 中断恢复、引用版本更新及删除后的 unavailable 状态。
- `npm --prefix web test -- AskView.test.tsx` — AskView 历史重开续问 / updated 引用提示和缺少 SSE 终态时保留 partial、不自动重发通过；全量 Web 47 项复跑也通过。

上述为观察到的命令结果；独立 QA、实际浏览器 / 原生壳复演均尚未运行。运行时模型和环境身份元数据未从实际 app runtime 检查，记 `UNVERIFIED`。

## 独立 QA 复演建议

在独立 checkout 固定最新交接文档记录的 QA SHA，使用临时 profile 与合成工作库：

1. 查询后刷新并重启 app，分页列出历史、打开会话，核对 question / answer / state / citation hash / excerpt 与 SSE seq。
2. 两个 workspace 使用相同 request_id，分别请求与取消，确认历史、SSE 和取消不跨 workspace；同一 workspace 下两 profile 打开同库，确认历史互相不可见。
3. 用相同 request_id / 同请求体重试，验证事件只重放且 QueryService 调用计数不增加；改问题或 conversation_id 应收到 409。另测不存在 / 其他 profile 的 conversation_id 为 404。
4. 在 query 仍 active 时读取历史，确认不误标 interrupted；取消和硬断流 / 重启后重开历史，确认唯一状态、真实 partial、无假 completed、无自动重发。
5. 创建只含合成内容的已确认页面并形成 citation，随后确认更新原页，再删除或改为 pending。逐次读历史核对原 hash / excerpt 不变，availability 分别 updated / unavailable；通过真实 WebUI 打开旧引用，确认提示出现且不会静默替换原依据。
6. 运行 README 的全后端/Web/静态/类型/构建门禁，保存真实日志退出码和独立 UI / network / console 观察；不要使用真实材料、模型、凭据、Keychain 或 DMG。

## 状态与边界

- DEV 实现和自测已完成，源码固定；Sol 需要派发全新 QA Luna 复验整包并作最终判断。不得依据本报告标记 M3 包 1 已通过。
- M3 包 2（完整问答、角色、记忆）和包 3（状态恢复、跨 profile 接续、归档压缩）尚未由本轮实现；真实 / 发布门未运行。
- 当前产品树外的 `.local/dev/m3-package-1/logs/` 属忽略文件，交付前需通过本机该 worktree 读取；不得把日志路径误当仓库内已提交 artifact。
