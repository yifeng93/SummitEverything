# C03 非空组织删除提示本地化 DEV（2026-10-11）

## 身份与范围

- 报告人 / 角色：Developer pilot，DEV 自测；运行时模型信息：UNVERIFIED。
- 起点提交：`b5aeb91f2e1cf6e07a92fad0392c25aab491f4a0`；固定源码 SHA：`9c953f095086a95e63edbce2169657dba9e71cd1`；测试执行时固定文档 checkpoint：`141bd96d15039f1cd29461785fdd91e2ef297476`。
- 分支：`codex/c03-delete-copy-pilot`；checkout：`/Users/yifengstudio/.codex/worktrees/c03-delete-copy-pilot/SummitEverything`。
- 范围：C03 P2 非空主线 / 项目删除的英文拒绝提示；Fake-only API 和隔离临时工作库。没有 UI、provider、真实业务材料、凭据或外部任务动作。
- 变更只将三个拒绝提示改为中文，并补 API 回归。409、`workspace_error`、标准错误 envelope、归档和删除逻辑不变。

## 结果

| 案例 | DEV 结果 | 观察 |
|---|---|---|
| 非空主线下有项目，且项目已归档 | PASS | 删除仍返回 409；中文提示要求移动项目，不暗示归档即可删除。失败前后 manifest 字节和项目原文件字节相同，项目仍保留。 |
| 主线目录直接含文件 | PASS | 删除返回 409 中文指引；manifest、主线 ID、原文件字节和目录保留。 |
| 非空项目（包括归档项目） | PASS | 删除返回 409 中文提示，指向归档作为收起方式；manifest 与原文件字节保持不变。 |
| 真正空项目 / 主线 | PASS | API 返回 204，目录和对应组织记录均删除。 |
| C03 定向自动回归 | PASS | contract + workspace mutation + qualified retrieval 共 37 项通过。 |
| 浏览器 / 真服务 / OS / 发布门 | NOT_RUN | 本切片仅 API 复制与文件检查；不构成 Stage B 或 v1 结论。 |

## RED → GREEN

先扩展 API 合同回归，要求中文拒绝信息、既有错误码和状态、拒绝操作不写库、归档项目仍阻止主线删除，以及空组织仍可删除。首次执行在两条英文拒绝消息断言处失败（2 failed，退出码 1）；失败原因与目标英文文案一致。改动仅替换 `manifest.py` 的三条字符串后，定向回归 2 passed，随后完整相关集合 37 passed。

## 命令

以下均在本报告所列 worktree 执行，使用离线依赖与 `scripts/offline_guard`。日志位于 ignored `.local/c03-delete-copy-pilot/evidence/`。

| 命令 | 结果 | 日志 |
|---|---|---|
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --offline --locked pytest -q tests/contract/test_workspace_api.py tests/integration/test_workspace_mutations.py tests/integration/test_qualified_retrieval.py` | PASS，37 passed，1 条既有 Starlette/httpx deprecation warning，exit 0 | `targeted-tests.log` |
| `uv run --offline ruff check src tests` | PASS，exit 0 | `ruff-check.log` |
| `uv run --offline ruff format --check src tests` | PASS，67 files already formatted，exit 0 | `ruff-format.log` |
| `uv run --offline mypy src` | PASS，36 source files，无问题，exit 0 | `mypy.log` |
| `uv lock --offline --check` | PASS，41 packages resolved，exit 0 | `uv-lock-check.log` |
| 首次红测：`PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --offline --locked pytest -q tests/contract/test_workspace_api.py -k 'nonempty_line_and_project_deletion_is_rejected or line_with_files_and_empty_organizations_can_be_deleted'` | 预期 FAIL：两项均在英文拒绝消息处失败，exit 1 | ignored `.local/c03-delete-copy-pilot/evidence/red-tests.log`（实际终端失败摘要） |

没有运行全量 backend、前端、浏览器、DMG 或外部服务验收；这些超出此窄范围或由 QA 后续处理。

## 门结论

- DEV C03 P2 文案修复：已实现并完成上述自动回归；不代表 M1 阶段重新验收。
- 独立模拟 QA：由 Sol 根据独立报告判定 C03 离线切片 PASS（首轮 PASS，repair 0/2）；详见 [独立 QA 报告](2026-10-11-C03-DELETE-COPY-QA-141bd96.md)。DEV 自测结论仍仅为 DEV；归档观察与运行日志见 [QA 证据目录](evidence/2026-10-11-c03-delete-copy-qa-141bd96/README.md)。
- 真实 provider、真实材料、OS Keychain、DMG、五日、双机及 M3–M5：本切片均 NOT_RUN，原状态不变。

## 给 QA 的交接

固定源码 `9c953f095086a95e63edbce2169657dba9e71cd1`。复核 C03 的三类拒绝文案、409 / `workspace_error` / envelope 保持、归档项目仍阻止主线删除、拒绝时 manifest / ID / 文件 / 目录不变，以及空项目和主线的 204 删除。建议复跑本报告的 pytest 命令及 ACCEPTANCE.md C03 对应行为。开发者没有在本文宣告 QA 通过。

后续交接说明：QA 测试执行时完整 HEAD 固定为文档提交 `141bd96d15039f1cd29461785fdd91e2ef297476`；QA 原报告以 `f381d28d077d3d668cc65ae5eb4fe13b4ad94761` 提交，并整合为本分支提交 `ebb99811d289ea821d5a1bfee9fad6a2a1ba04db`。QA 测试结束后的产品源码树与 `9c953f095086a95e63edbce2169657dba9e71cd1` 一致；后续仅提交文档和证据。Sol 依据独立 QA 结果判定本 C03 切片通过，分支候选仍未合并 main。
