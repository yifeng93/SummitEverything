# F2 修复报告：origin guard 对损坏 profile 的失败形态

分支 `codex/origin-guard-error-20261014`（自 `main` `bb80b40` 单独开出，与设置 UX 分支无关）。**固定产品 SHA `c9b3f7cc9af75d1bc46b9ab32e0950ba32995db9`**。本报告由 Sol 编写；独立验收由全新 QA 完成，报告见下文与[证据目录](evidence/2026-10-14-origin-guard-settings-error/README.md)。

## 缺陷

`origin_guard` 是 HTTP 中间件，每次请求都要读取当前 profile 的设置以解析允许的 callback origin，但读取未捕获 `SettingsError`。中间件位于应用的异常处理器**之外**，因此未捕获的异常逃逸为**裸 500**：`Internal Server Error`、`text/plain`、没有 `code`、`message` 或 `request_id`，而注册好的处理器（本应返回 JSON 503 `settings_unavailable`）根本没有机会运行。

后果不止是错误格式：损坏 profile 之后**每个请求都 500**，其中也包括**用来修复它的 `PATCH /api/v1/settings`**，用户只能手改文件。该形态在功能前提交 `a6faf7e` 上同样存在，由设置 UX 分支的第二轮独立 QA 作为既有问题记录（当时编号 F2，未修）。

## 修复

- 抽出模块级 helper `settings_error_response(request, exc)`，**中间件与 `@app.exception_handler(SettingsError)` 共用同一信封**，形状不会再漂移。
- `origin_guard` 捕获 `SettingsError` 并返回该信封（`settings_unavailable` → 503 JSON）。
- 该中间件在中间件栈中位于分配 `request_id` 的 `LoopbackOnly` **之外**（`add_middleware` 前插，后注册者更靠外），因此 helper 在 `request_id` 缺失时自行分配一个并写回 `request.state`，保证信封始终带相关 ID。

## Sol 本机证据

| 检查 | 结果 |
|---|---|
| 新增契约测试 `tests/contract/test_origin_guard_settings_error.py` | 3 passed |
| 修复前对照（临时 stash 掉中间件改动，同 harness） | **2 of 3 failed**（旧行为确为裸 500） |
| guarded 全量 | **516 passed**, exit 0（`main` 基线 513 + 新增 3） |
| `ruff check` / `ruff format --check` / `mypy src` / `uv lock --check` | 全部 exit 0 |
| OpenAPI 与前端类型 | 运行 `scripts/export_openapi.py` 后 `web/` 无 git 改动 → 契约未变 |

## 独立 QA 判定（固定 SHA `c9b3f7c`）

7 项必做验证全部 **PASS**，修复本身未发现新缺陷：

1. **身份与范围** PASS：`git diff --name-status main..c9b3f7c` 仅 `src/summit_everything/api/app.py` 与新增测试文件；OpenAPI 与 `generated.ts` 导出前后哈希一致。
2. **修复前/后对照** PASS：同一 harness、同一解释器，仅切换 `PYTHONPATH` —— `main` 只读导出树为 **500 `text/plain` "Internal Server Error"**（`raise_server_exceptions=True` 下确实抛出未捕获的 `SettingsError`），本树为 **503 `application/json`** 三键信封；section 级与字段级两种损坏均一致。
3. **信封一致性** PASS：路由级 503（`credential_store_unavailable`）、路由级 422（`validation_error`）、中间件级 503 三者 `error` 键集合相同、`request_id` 均为 16 位；并用 monkeypatch spy 证明两条路径**命中同一 helper 符号**。
4. **未放松 fail closed** PASS：45 个探针（15 路径 × 3 种 Origin）全部 503，无任何 2xx、无非信封响应；响应正文不含损坏内容或 profile 路径（无回显）。
5. **既有 origin 语义未破坏** PASS：健康 profile 下存储的 callback origin 被允许（200）、外来 origin 仍 403 `forbidden_origin`、设置读写正常。
6. **全量测试** PASS：516 passed，exit 0（fresh worktree 缺 `web/node_modules` 时 `test_dev_runner.py` 的 3 项失败已单独复现并与本次修复无关）。
7. **静态检查** PASS：ruff check / format / mypy / `uv lock --check` 全部 exit 0。

## 既有观察（本轮不修，如实记录）

- **O1**：`forbidden_origin` 的 403 信封只有 `{code, message}`，**没有 `request_id`**，与异常处理器/helper 的三键形状不一致；`main` 上同形，属未修复的历史不一致。因此「guard 与异常处理器同形」应限定为 **SettingsError 路径**。
- **O2**：因 guard 位于认证、路由与 `LoopbackOnly` 之外，损坏 profile 会让**所有**请求 503 —— 包括 `GET /`（WebUI 完全不可用）、`/callback`（OAuth 回调）、未知路径（503 而非 404），以及**未认证请求（503 而非 401）**。这是有意的 fail closed，但可用性副作用值得在设计上再决定：另一种做法是读取失败时退回 `config.allowed_origins`（不扩展未经验证的 origin），让应用仍可进入设置界面。**本分支未改该行为**。
- **O3**：修复后损坏 profile 仍**无法经 API 自修**（`PATCH /settings` 同为 503），需手改或删除 `provider-settings.json`。加「重置本机设置」入口属后续独立范围。

## 未验证

真实 HTTP 服务器/浏览器（本轮为进程内 `TestClient` 黑盒）、真实 macOS 钥匙串（使用 `MemorySecretBackend` / `UnavailableSecretBackend`）、付费模型与真实飞书、DMG/安装包级验收、双机与五日门、非 macOS 平台、以及并发竞态（guard 读取与 `PATCH` 写入同时发生）。

## 候选与后续提交

本修复只改后端与测试，**未重建安装候选**：它不改变设置 UX 分支的候选包所对应的产品树用途；如需把 F2 一并放进安装包，应在合入后统一重建。后续 docs-only 提交不改变受测产品 SHA `c9b3f7c`。
