# M3 包 3 repair 1 Developer 报告：lease 发布前异常清理

日期：2026-10-12。此轮是包 3 首次独立 QA 的自动修复第 1/2 轮；未改变验收期望，也未修包 2 的 C19 P1。

## 固定源码与缺陷

- 分支：`codex/m3-integrated-packages`。
- 起点：`fd2cc552e83669ec7e7cda9754cd74e1bcd0a367`（QA 报告已由 Sol cherry-pick）。
- 修复源码：`ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`。
- 初验 QA 报告：[M3 包 3 QA](2026-10-12-M3-PACKAGE-3-QA-22e5ad9.md)；QA 复现脚本位于对应 evidence/harness 的 `repro_running_receipt_failure.py`，原报告与证据保持未改。
- 初验根因：`ActionService.execute` 在取得 action attempt lease 后，把首次 `running` receipt 保存放在其外层 `try/finally` 之前。写回抛 `OSError` 时，状态仍为 `confirmed`、Fake provider 调用为 0，但 lease 只等对象回收 / GC 才解锁及删除。

## 修复与回归

action 首次发布 `running` 状态失败时立即释放并删除 lease，然后原样抛出异常；确认回执保持 `confirmed`，外部任务未发出，同意图重试可成功且只创建一项 Fake 任务。新集成回归保留异常 traceback，验证清理不依赖 GC。`IntakeReviewService.create_job` 的同类 acquire 后、try 外 `jobs_root.mkdir` 窗口也纳入 lease 清理 try/finally 保护；目录创建失败不遗留 lease、不改变 pending item、不调用 FakeLLM。

已先验证两条新回归在起点 SHA `fd2cc55` 上均按预期失败，再应用修复并通过：

| 命令 | 结果 |
|---|---|
| 两条 targeted regression | PASS：2 passed；起点 SHA 预期 FAIL，修复 SHA 通过 |
| actions / intake review / workspace archives / workspace mutations / Feishu 集成 | PASS：105 passed，1 条既有 Starlette/httpx deprecation |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | PASS：440 passed，1 条既有 Starlette/httpx deprecation |
| `uv run ruff check src tests` | PASS，exit 0 |
| `uv run ruff format --check src tests` | PASS，exit 0；78 files 已格式化 |
| `uv run mypy src` | PASS，43 source files，exit 0 |
| `uv lock --check` | PASS，exit 0 |
| `uv build` | PASS，sdist 与 wheel 均构建，exit 0 |
| `PYTHONPATH="$PWD/src" uv run python scripts/m3_package3_bulk_sample.py` | PASS，exit 0；120 流程、4 业务月，重放 provider 调用仍 120，active lease 0 |

实际日志及各命令 `.exit` 位于 `.local/dev/m3-package-3-repair-1/`。Web、OpenAPI 类型生成和浏览器未因这次仅 Python lease 生命周期改动重复；本轮无前端/API 契约变化。新增两条测试与修复代码见固定源码 SHA。

## 当前门与限制

这是 Developer 修复和自测，不是 QA PASS。请由全新 QA 在独立 checkout 固定 `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f` 复验初始 package 3 C22/C23/C21 范围，重点重放 action 首次 running receipt 写入失败：异常对象保持存活时 lease 文件必须已经移除、receipt 仍 confirmed、provider 调用 0；恢复保存后同意图重试仅一次副作用。另验证 job startup 的 jobs 目录 mkdir 异常路径，确认无遗留 lease、item 仍 pending、provider 0，并回归活 owner、同意图并发、取消后迟到结果 CAS、checkpoint 恢复和 120 流程计数。

QA 初验报告中包 2 C19 P1 仍 FAIL 且未在本轮修改；M3 正式门未通过。真实服务、材料、凭据 / Keychain、native / DMG、五日、双机与发布门 NOT_RUN，runtime UNVERIFIED。未运行独立 QA、merge 或真实外部操作。
