# Frontend B Developer raw evidence index

固定产品 SHA：`613d453ab1a47e2f0bfe78d685fb90817f70f4cc`。此为历史父 SHA 的索引；该 SHA 后经首次独立 QA 判 **FAIL**，QA 报告及脱敏归档见 [initial QA archive](../2026-10-15-frontend-b-initial-qa/README.md)。产品修复轮 1 与当前验收入口为 [repair1 DEV/evidence](../../2026-10-15-FRONTEND-B-DEV-REPAIR1.md) 和 [repair1 raw evidence](../2026-10-15-frontend-b-repair1/README.md)。本目录只索引父 SHA 的原始开发日志，不能代替 repair1 测试或 QA 结论。原始开发日志、截图与 workflow manifest 在开发 worktree 的 `.local/dev/frontend-b/`，路径均相对仓库根。Developer 自测不是 QA 结论。

## 最终命令结果

| 命令 / 范围 | 退出码 | 原始文件 | 结果摘要 |
|---|---:|---|---|
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q`（backend 自 `1cb3d8a` 后未变） | 0 | `.local/dev/frontend-b/pytest-guarded.log`, `pytest-guarded.exit` | 661 passed；复用已有本轮原始日志 |
| `npm --prefix web run api:types` | 0 | `api-types.log`, `api-types.exit` | OpenAPI 生成完成，tracked 输出无变化 |
| `npm --prefix web test -- --run` | 0 | `full-unit.log`, `full-unit.exit` | 24 test files；176 passed、6 todo |
| `npm --prefix web run typecheck` | 0 | `post-review-typecheck.log`, `.exit` | TypeScript 项目引用检查 |
| `npm --prefix web run lint` | 0 | `post-review-lint.log`, `.exit` | 2 条 warning：App 与既有 ProjectsView 的 React effect setState |
| `npm --prefix web run build` | 0 | `post-review-build.log`, `.exit` | 构建成功；568.73 kB JS chunk warning |
| `npm --prefix web run test:e2e` | 0 | `final-e2e-complete.log`, `.exit` | 2/2：first-use 与浏览器矩阵 |
| `npm --prefix web run test:e2e -- --grep 'offline viewport'`（最终含弹窗边界断言） | 0 | `dialog-matrix-bounds.log`, `.exit` | 1/1；五宽度×双主题；三种弹窗焦点/边界/Escape/归还 |
| `npm --prefix web run test:e2e:integration` | 0 | `fastapi-integration-conflict.log`, `fastapi-integration-conflict.exit` | 1/1；Fake 冲突 fixture、独立 profile / workspace、无外部尝试 |
| `uv run ruff check web/e2e/fixtures/fastapi_conflict_app.py && uv run ruff format --check web/e2e/fixtures/fastapi_conflict_app.py && git diff --check` | 0 | `python-fixture-static.log`, `.exit` | Python fixture lint/format 与差异空白检查 |

集成流程的 `workflow-manifest.json` 记录所有写入端点与 `externalAttempts: []`。页面检查到 intake 恰有 2 条，origin kind 为 `file` / `quick_note`，文件与 quick note 在隔离 workspace 的原始字节逐字节匹配；冲突暂未决时 formal confirm disabled，用户选择暂时未决后写入正式页并读回；取消整理没有 intake job 写入，动作组无 confirmation/execution 写入。

## 守卫变异红绿证据

历史变异命令退出码由当时的测试执行记录确认；旧文件未统一生成 `.exit` sidecar，禁止将后续总测试日志误写成单条变异日志的退出码。全部日志保留原样。

| 守卫 | 破坏/恢复证据 | 实际测试观察 |
|---|---|---|
| ① | `guard-1-mutated.log` / `guard-1-restored.log` | mutated 1 failed，restored 1 passed；内部来源标识被渲染时断言报红 |
| ② | `guard-2-mutated-final.log` + `.exit` / `guard-2-restored-final.log` + `.exit` | mutated exit 1（中文选项变为英文内部 ID，1 failed）；恢复 exit 0（9 passed） |
| ④ | `guard-4-mutated.log` / `guard-4-restored.log` | mutated 1 failed，restored 1 passed；加载态被画成空态时断言报红 |
| ⑤ | `guard-5-mutated.log` / `guard-5-restored.log` | mutated 1 failed，restored 1 passed；取消触发整理写请求时 FastAPI E2E 报红 |
| ⑧ | `guard-8-mutated.log` / `guard-8-restored.log` | mutated 1 failed，restored 1 passed；导航顺序变更被断言捕获 |
| ⑨ | `guard-9-mutated.log` / `guard-9-restored.log` | mutated 1 failed / 1 test error，restored 1 passed；今日启动额外请求 index plan 时断言报红 |
| ⑩ | `guard-10-mutated.log` + `.exit` / `final-e2e-complete.log` + `.exit` | mutated exit 1（固定 400px 最小宽度导致 viewport test fail）；恢复后最终全套 E2E 2/2 pass |

守卫①②④⑤⑧⑨变异相关的原始结果文本有些旧日志不保存进程 exit sidecar；此表按日志失败/通过结果描述，不补造 sidecar。②与⑩本轮收尾额外红绿使用的完整退出码见相邻 `.exit` 文件。

## 失败历史与对应修复

| 旧失败证据 | 退出码 | 说明及最终对应证据 |
|---|---:|---|
| `.local/dev/frontend-b/quick-note-red.log`, `quick-note-red.exit` | 1 | 初始真实 FastAPI POST 缺 operation id 导致 422；修复为稳定意图 ID 并加入原始空格/换行原件断言。当前 `TodayView.test.tsx` included in `full-unit.log`，FastAPI 字节验证见最终 integration manifest。 |
| `.local/dev/frontend-b/fastapi-integration.log`, `fastapi-integration.exit` | 1 | 早期 FastAPI 集成 harness 失败，配置/首次授权与 profile 状态未隔离稳定；保留为失败原件。 |
| `.local/dev/frontend-b/fastapi-integration-final.log` | 此次无独立 sidecar | 早期闭环通过但冲突数为零，不作为部分冲突验收证据。 |
| `.local/dev/frontend-b/fastapi-integration-conflict.log`, `fastapi-integration-conflict.exit` | 0 | 最终独立配置、独立 profile、FakeLLM 冲突 fixture；1/1 pass，是当前冲突覆盖证据。 |
| `.local/dev/frontend-b/guard-2-mutated-final.log`, `guard-2-mutated-final.exit` | 1 | 明确故意把主线选项业务文案替换为内部英文 ID；对应恢复日志 exit 0。 |

## 浏览器截图索引

`.local/dev/frontend-b/viewport/screenshot-manifest.json` 列出每个文件名：

- Today：320/390/768/960/1280 × light/dark；
- Approval：同 5×2；
- Import Drawer：同 5×2；
- Journal Dialog：同 5×2；
- Approval selection summary：同 5×2。

共 50 张 Playwright 截图，人工通过按场景 contact sheet 检查；原始 `.png`、`measurements.json`、五个 `contact-*.jpg` 在上述目录。Import/Journal/汇总弹窗在每一尺寸和主题下执行 focus containment、Escape 与焦点归还；三者均检查 fixed backdrop 和视口内边界。Today/Approval 检查横向 document/body 溢出为零。首次 full-page mobile capture 中固定底导航会出现在长截图中段，这是整页捕获视口固定元素的表现；按 viewport 截屏仍是固定底栏。
