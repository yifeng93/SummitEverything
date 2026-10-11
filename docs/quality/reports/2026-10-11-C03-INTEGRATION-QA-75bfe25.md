# C03 文档整合候选独立 QA（2026-10-11）

## 固定版本与范围

- **待测 SHA：** `75bfe2548e947432e72767b0b7822d34685a8b61`；执行前后 HEAD 相同，detached QA worktree 起始及测试前为 clean。
- **QA checkout：** `/Users/yifengstudio/.codex/worktrees/c03-integration-qa/SummitEverything`。
- **本轮 runtime 模型 / effort：UNVERIFIED。** 没有可观察的运行时元数据，未从配置文件推断。
- **范围：** 核对 C03 先前 QA 归档与 Sol/Luna 长期工作流文档整合；在固定候选上按 handoff 执行离线 Python / Web 检查。源码、tracked tests、产品配置及依赖锁均未改。
- **证据：** 原始文本日志及校验清单见 [`evidence/c03-integration-75bfe25`](evidence/c03-integration-75bfe25/)；QA 临时环境日志另留在 checkout 忽略目录 `.local/qa/c03-integration-75bfe25/logs/`。

## 文档与提交范围复核

**PASS — 提交范围与代码树。** `141bd96..6eb33d0` 的变更全部位于 `docs/`，包含 C03 开发 / 独立 QA 报告及 QA 日志、浏览器观察、快照归档；没有产品代码路径。`6eb33d0..75bfe25` 仅包含 `AGENTS.md`、`README.md` 和 `docs/`。直接比较 `src tests web native` 与 `141bd96` 无差异（exit 0），候选没有移动产品实现或前端树。

**PASS — 先前 C03 证据可保留。** 先前报告覆盖 37 项定向回归和真实本地 Fake 浏览器步骤；归档 `SHA256SUMS` 中的 15 个条目全部校验通过。报告明确没有导出截图，也没有声明专用 DevTools 网络 / console 检查。先前浏览器范围可以按其原始报告保留；本轮没有重跑浏览器，故本轮浏览器状态为 **NOT_RUN**。

**PASS — 安装 overlay 来源。** `docs/handoff/history/2026-10-11-SOL-LUNA-INSTALL-OVERLAY.patch` 与 `/tmp/summit-existing-agents-2026-10-11.patch` 逐字相同，双方 SHA-256 均为 `d9c3122955848afab852c81a2b24e8d9e62d9eb0eb59ace61d1b8cd21d111f32`。

**PASS — 长期流程规则与原项目门保留。** 新增 AGENTS / ADR 和同步后的交接文档写明 Sol 默认协调、custom Developer GPT-6 Luna High、全新独立 QA GPT-6 Luna High、串行代码变更、固定 SHA handoff、最多两轮新 SHA 修复、Sol 判最终 gate；测试者不得改源码或 tracked tests，自动 agent handoff 不要求用户手工转发。元数据不可见时记录 UNVERIFIED。真实 Stage C、材料 / 凭据 / Keychain、DMG、五日和双机仍为独立未测门。历史安装 overlay 和 Stage B 提示被明确限定为追溯资料，不能用来重启已完成阶段。

**PASS — 路线图状态及范围。** 当前文档仍将 M3 标为未开始，M3.1 仅为建议；引用 PRODUCT-SPEC、API-v1、ACCEPTANCE C14 / C21 的历史 / 引用要求，并说明建议不缩减角色、记忆、三类问答或完整 v1 范围。C03 仍标记为分支候选、未合入 main；报告没有预写合并状态。改动没有修改产品规格、API 契约或验收矩阵。对 9 个受影响 Markdown 文件的 117 个相对链接检查通过。

## 自动检查

所有原始命令、输出及退出码在证据目录对应日志中。首次 guarded pytest 先于 `npm ci` 执行，暴露 fresh worktree 尚无 `web/node_modules` 的环境前置条件：runner 测试进程 exit 2。该首次结果完整保留在 `pytest.log`。`scripts/run_dev.py:20-23` 对该条件明确返回 exit 2 并提示安装 Web dependencies。随后按 README / handoff 安装离线前端依赖，再对同一 SHA、同一 guard 命令做一次复验，通过；没有改源码、测试或依赖锁。

| 检查 | 结果 | 证据 |
|---|---|---|
| `uv sync --offline --locked --group dev` | PASS，exit 0 | `evidence/c03-integration-75bfe25/logs/uv-sync.log` |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run --offline --locked pytest -q` 首次 | 首次 FAIL（环境前置未满足）：1 failed / 388 passed，exit 1；失败测试见下文 | `evidence/c03-integration-75bfe25/logs/pytest.log` |
| `npm --prefix web ci --offline` | PASS，exit 0；安装 126 packages | `evidence/c03-integration-75bfe25/logs/npm-ci.log` |
| 同一 guarded pytest 命令，安装依赖后一次复验 | PASS，389 passed，exit 0；保留 1 条 Starlette/httpx 弃用 warning | `evidence/c03-integration-75bfe25/logs/pytest-after-npm-ci.log` |
| `uv run --offline --locked ruff check src tests` | PASS，exit 0 | `evidence/c03-integration-75bfe25/logs/ruff-check.log` |
| `uv run --offline --locked ruff format --check src tests` | PASS，67 files already formatted，exit 0 | `evidence/c03-integration-75bfe25/logs/ruff-format.log` |
| `uv run --offline --locked mypy src` | PASS，36 source files，exit 0 | `evidence/c03-integration-75bfe25/logs/mypy.log` |
| `uv lock --check --offline` | PASS，exit 0 | `evidence/c03-integration-75bfe25/logs/lock-check.log` |
| `uv build --offline` | PASS，source distribution 与 wheel 构建成功，exit 0 | `evidence/c03-integration-75bfe25/logs/uv-build.log` |
| `npm --prefix web test` | PASS，10 files / 45 tests，exit 0 | `evidence/c03-integration-75bfe25/logs/npm-test.log` |
| `npm --prefix web run typecheck` | PASS，exit 0 | `evidence/c03-integration-75bfe25/logs/npm-typecheck.log` |
| `npm --prefix web run lint` | PASS，exit 0；保留 3 条既有 `react(set-state-in-effect)` warning | `evidence/c03-integration-75bfe25/logs/npm-lint.log` |
| `npm --prefix web run build` | PASS，exit 0 | `evidence/c03-integration-75bfe25/logs/npm-build.log` |

首次全量测试的唯一失败是 `tests/integration/test_dev_runner.py::test_runner_uses_its_ports_and_stops_only_its_owned_services`，观察到 runner `returncode: 2`。失败发生在本 worktree 的 `npm ci` 之前；runner 对不存在的 `web/node_modules` 明确返回该状态。离线安装依赖后同一 suite 全部通过，因此当前固定候选没有复现代码失败。两次运行的原始结果都保留，Sol 可据此判最终门。

## 未执行门与风险

- **浏览器：本轮 NOT_RUN。** 产品 UI 树与先前 C03 浏览器 QA 的固定源码相同；先前真实浏览器观察与限制在原 QA 报告 / 归档中，本报告不把它表述成本轮复验。
- **真实服务 / 账户 / 模型 / 材料 / 凭据 / OS Keychain：NOT_RUN。** 所有测试使用离线依赖、guarded Python suite 与 Fake / 合成范围；未调用真实服务或读取真实业务材料。
- **DMG、五日连续工作日、双机、M3–M5：NOT_RUN。** 自动检查不构成这些门的证据。
- Python 测试保留 1 条 Starlette/httpx 弃用 warning；前端 lint 保留 3 条既有 warning。

## Git 与结论

- 测试后 HEAD 仍为 `75bfe2548e947432e72767b0b7822d34685a8b61`。
- `uv.lock` SHA-256 前后均为 `148ac7c5d1d795ec0ee17384bca7c2173dddb6ba8945b23445da71356c9bfbda`；`web/package-lock.json` 为 `d7b39319f006b0280857a02f3932f7e71e8d38cd0e63a0684f9b41f0d9c26ad3`。无意外 tracked working-tree 变化。隔离 `.venv`、`web/node_modules`、`dist` / Web build 产物与 QA logs 位于忽略 / evidence 目录。
- **QA verdict：PASS（仅文档整合与离线回归范围；首次依赖前置失败已记录，并在离线 npm 安装后一次复验通过）。**
- **Gate 状态：** 本轮提交范围、C03 先前证据归档、文档链接和离线源码检查 PASS；本轮浏览器 NOT_RUN；真实 / 发布 / 多机门 NOT_RUN。Sol 负责最终 gate 判定。
