# M2 Stage A 合并后核验记录（2026-10-10）

## 固定版本与提交关系

- PR #4：[Close M2 Stage A Fake-only QA and remediation](https://github.com/yifeng93/SummitEverything/pull/4)，以 merge commit `0789f9ebfee4a0352e2818510055a252ba374daf` 合入 `main`。
- 本次独立合并后 checkout 固定在该 merge SHA：`/Users/yifengstudio/.codex/worktrees/m2-stage-a-postmerge/SummitEverything`。
- 独立 QA 最终受测源码为 `32da67e9c0280e3dae18fd374e30c925565b0b82`；该源码是 merge commit 的祖先。QA 最终报告原提交为 `0531e0d1b95eb8dbb56af9237e39e21fcdf1d6f8`，被 PR #4 中的报告导入提交 `ecfc87b304c177a302420cf6c38ff54e5d119c18` 收录。`src/`、`tests/`、`web/`、`native/` 在受测源码和合并树之间无差异。
- QA 初验和各轮补充报告、回归测试、脱敏证据与复演 harness 均在合并树中；可从 [最终第四轮 QA 报告](2026-10-10-M2-stage-a-final-fourth-followup-qa.md)及其 evidence 目录进入。代码修复前的原候选 `09398fcae597b2478001d40aedf580ea91322c11` 与报告链按 [验收矩阵](../ACCEPTANCE.md)追溯。

## 合并后自动检查

在上述隔离 checkout 执行，工作库和依赖环境均位于独立 worktree：

| 命令 | 结果 |
|---|---|
| `uv sync --frozen --group dev` | PASS，退出 0 |
| `uv run --frozen pytest -q` | PASS，142 passed；保留 1 条既有 Starlette/httpx TestClient deprecation warning |
| `uv run --frozen ruff check src tests scripts` | PASS，退出 0 |
| `uv run --frozen ruff format --check src tests scripts` | PASS，43 files already formatted |
| `uv run --frozen mypy src` | PASS，30 source files 无问题 |
| `uv lock --check` | PASS，退出 0 |
| `uv build` | PASS，sdist 与 wheel 成功 |
| `cd web && npm ci` | PASS，安装完成，npm audit 0 vulnerabilities |
| `cd web && npm run api:types` | PASS，OpenAPI 导出和 TypeScript 类型生成成功；生成结果与提交内容一致 |
| `cd web && npm test` | PASS，8 个测试文件 / 32 项通过 |
| `cd web && npm run typecheck` | PASS，退出 0 |
| `cd web && npm run lint` | PASS，退出 0；保留 3 条既有 React effect warning |
| `cd web && npm run build` | PASS，Vite production build 成功 |
| `cd native && swift build` | PASS，开发壳编译成功 |
| `git diff --check` | PASS，退出 0 |

## 关键行为冒烟

命令：

```sh
uv run --frozen pytest -q \
  tests/integration/test_stage_a_original_qa.py \
  tests/integration/test_journal_overviews.py::test_journal_supports_no_association_line_only_and_line_with_project \
  tests/integration/test_actions.py::test_unknown_timeout_lookup_and_no_evidence_never_reposts \
  tests/integration/test_actions.py::test_task_results_validate_requested_fields_and_explicit_clears \
  tests/integration/test_actions.py::test_project_progress_separate_from_knowledge_and_version_conflict
```

结果：**8 passed**，保留同一条 Starlette/httpx deprecation warning。覆盖概览 metadata 与知识资格、已批准日志自动增量索引、任务完成响应字段校验、无关 Fake task 不核实 unknown、unknown 不重发，以及知识批准和项目进度独立确认 / 版本冲突。

合并后的浏览器 Fake 流程与原生壳不重新启动：合并树 `src/tests/web/native` 与最终受测 SHA 的目录树相同，PR #4 使用 merge commit 且没有冲突解决或后续实现提交。浏览器 console 与原生壳窗口 / 生命周期的实际候选证据仍见固定 SHA 的独立 QA 报告。此核验不扩大为真实 provider 或发布验收。

## 最终边界

- 合并树模拟范围 P0/P1/P2 未关闭项：0。
- 真实 Feishu 账号 / 权限 / 任务、真实模型 / embedding / rerank、真实业务材料、OS Keychain、DMG、五日试用、双机：**NOT_RUN**。用户已准备资源未消费。
- 未启动 M3–M5 或阶段 B/C。
- 报告只记录合并后核验，不更改任何产品实现或独立 QA 结论。
