# M3 包 3 Developer 报告：连续状态与归档压缩

日期：2026-10-12。用户明确要求直接开始包 3；这改变实施顺序，不改变产品规格、包 2 QA FAIL 或 Sol 的验收门。

## 固定源码与结果边界

- 分支：`codex/m3-integrated-packages`。
- 源码 SHA：`d03c548b69a4ec48a947486df191bd4af009b6e2`（含实现、回归和批量计数器）。
- 起点：`e4b491504c5c867b978f1bacff4d79326313533a`。
- 本报告是 Developer 自测。包 3 独立 QA 尚未开始，Sol 未判包 3；**不能据此标记 C22/C23 或 M3 PASS**。
- 包 2 extra 2 的 C19 P1 仍为 FAIL：无资料的跨材料比较仍引用无关预算，报告和证据保留；本工作未更改 retrieval/planner/query，也未声称修复。

## 行为与实现

完成的 intake item/job 与 capture、mutation、SHA write-intent、Feishu import 回执可以从 active 文件或按完成时间建立的月摘要查找和重放。没有额外持久索引或 tombstone；摘要读取核实 namespace、文件夹月份、合法月份与每条 receipt 的 `finished_at`，枚举意外/冲突副本，并在任何归档写入前校验该 namespace 的全部现存摘要。月摘要先原子写入再删除 active，崩溃后的相同副本可恢复，内容冲突或损坏会 fail closed。旧的无时间戳记录保持可读；需要显式重新整理时，旧 item 业务版本先保存到 `undated`，不伪造业务完成日期，也不丢失 attempt parent hash。原件字节、完整 draft 正文及确认历史都不删除。

每个整理 attempt 使用本机 advisory lease 和 UUID attempt 标识；读取可识别同机另一 profile 的活跃 owner，不能仅因 session/profile 不同将其标成 unknown。持锁 attempt 经 durable `calling`、provider 返回、checkpoint / 本地落稿和终态 CAS，lease 持续到终态保存完成。死 owner 无 checkpoint 时保持 unknown 且不自动重发；成功结构化 checkpoint 只用于恢复本机稿件/候选，不批准知识。取消与迟到返回以 expected state、attempt 和 revision CAS 防覆盖。明确重新处理产生新 operation 并在 UI 提示可能再次调用模型。跨机器仅支持用户同步后轮流写，不提供分布式锁或远端自动重试。

provider job 的 `completed` 只表示整理调用和稿件落地完成；各 draft 仍独立待审/确认。未完成、unknown、running 和待审业务状态继续留在 active 记录，完成回执按月汇总。已有 action receipt 月汇总及 unknown/no-POST 行为继续复用。事务及 item 的读取、list、refresh、source identity、Feishu replay 和 project-progress proof reconcile 均查 active+摘要。跨 profile list/refresh 在主锁内重新读当前版本再做派生状态写入，避免旧快照覆盖另一 profile 的 reprocess。API 为运行中的同意图返回明确 202 + Location；TodayView 显示未知状态、手动刷新和重新处理的副作用提示。

诊断事件用 allowlist 的安全代码、ID 与计数，仅写本机 profile 的轮转日志（256 KiB，3 个备份）；不传入任意消息，不写工作库，也不写 prompt、正文、token、凭据或本机绝对路径。

## 可复验批量样本

`PYTHONPATH="$PWD/src" uv run python scripts/m3_package3_bulk_sample.py` 退出码 **0**；完整输出和 `.exit` 在 `.local/dev/m3-package-3/bulk-sample.log` 与 `.local/dev/m3-package-3/bulk-sample.exit`。样本包含 120 个 FakeLLM 整理与确认流程，完成时间落在四个月（2026-06 至 2026-09），然后抽样重放来源和 job。

| 计数 | 实测 | 说明 |
|---|---:|---|
| 已完成合成流程 | 120 | FakeLLM 本地调用 120 次；来源与 job 重放后仍各为 completed，调用数仍为 120 |
| Intake item 月摘要记录 | 120 | 4 个 finish 月，每月一个摘要 |
| Intake job 月摘要记录 | 120 | 同上 |
| Transaction 月摘要记录 | 366 | capture 120、mutation 120、SHA write-intent 122（样本 120 + setup 2）、合成 Feishu 回执 4 |
| 月摘要文件 | 13 | intake item 4、job 4、transaction 5；transaction 的 2026-10 有 2 条 setup SHA 回执，不算入 4 个流程月 |
| Active item / job 总数 | 2 / 1 | item 含新流程 unknown 1 与 legacy undated 1；job 为 unknown 1 |
| 新流程 item/job active（含 unknown） | 1 / 1 | 未完成的 unknown 是此处新流程子集 |
| 完成样本遗留 active item/job | 0 / 0 | 120 个完成样本全部已压缩 |
| Legacy undated active item | 1 | 单独例外，保留旧记录，不伪造月份；类别与 total 交叉说明 |
| Unknown active item/job | 1 / 1 | 仍在 active，不自动归档或重发 |
| 原件 / 完整 draft | 120 / 120 | 正文文件保留 |
| 完成后 checkpoint / lease 文件 | 0 / 0 | 所有完成样本清理；unknown 不依赖 checkpoint 自动重发 |
| Active transaction 文件 | 0 | capture、mutation、SHA write-intent、Feishu import 四类均为 0 |

样本中的 4 条 Feishu 记录是合成 transaction 收据，只计压缩/读取；不声称实际 Feishu provider 调用。实际 Fake Feishu 导入保存、重启后从摘要重放及不再取正文由 `tests/integration/test_feishu.py::test_selected_body_calls_and_restart_replay` 单独覆盖。120 条样本没有计算 filesystem 性能基准，也未测试跨机器并发写。

## 检查结果

README 适用矩阵及扩展批量计数检查均已实际运行，日志和每条 `.exit` 位于 `.local/dev/m3-package-3/raw-logs/`；全项 exit 0。

| 命令/检查 | 结果 |
|---|---|
| `uv sync --locked --group dev` | PASS，exit 0 |
| `npm --prefix web ci` | PASS，exit 0；126 packages，0 vulnerabilities |
| `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q` | PASS，438 passed；1 条既有 Starlette/httpx deprecation，exit 0 |
| `uv run ruff check src tests`、`ruff format --check src tests` | PASS，exit 0 |
| 批量脚本 `ruff check`、`ruff format --check` | PASS，exit 0 |
| `uv run mypy src` | PASS，43 source files，exit 0 |
| `uv lock --check`、`uv build` | PASS，exit 0 |
| `npm --prefix web run api:types` | PASS，exit 0；随后 OpenAPI JSON / generated TS SHA 稳定性检查 exit 0 |
| `npm --prefix web test -- --run` | PASS，56 tests / 12 files，exit 0 |
| `npm --prefix web run typecheck` | PASS，exit 0 |
| `npm --prefix web run lint` | PASS，exit 0；保留 TodayView / ProjectsView 两条既有 set-state-in-effect warnings |
| `npm --prefix web run build`、`git diff --check` | PASS，exit 0 |
| 定向 intake/archive/action/Feishu/workspace/log 回归 | PASS，105 passed；1 条相同 Starlette/httpx deprecation，exit 0 |

最终源码只在全量矩阵后更改了批量脚本的 active receipt 计数输出。该更新后重新执行 bulk sample（exit 0）、脚本 Ruff check / format（exit 0）；产品源码未变，因此未重跑 438 项全套。OpenAPI/types 随源码生成后稳定，无额外依赖/lock 修改。

## QA 交接与限制

请全新独立 checkout 固定源码 `d03c548b69a4ec48a947486df191bd4af009b6e2`。按 C22/C23/C21 完整复演另一 profile 的待审稿/部分确认、同机活跃 owner、进程失效 unknown/no-resend、checkpoint 崩溃恢复、取消后迟到响应、explicit reprocess、旧 undated item 链；检查五类 receipt 的月归档/active union replay、同/冲突摘要副本、损坏/非法月份和写中断，并核对原件、完整稿、确认记录、workspace/profile 存储隔离与本机日志位置。bulk harness 可从上述脚本复跑；Fake Feishu 的真实 import/replay API harness 是单独集成测试。还应回归 C13/C14/C19/C20，并记录包 2 C19 P1 的失败，不得因包 3 结果推断其已修复。

Developer 未运行真实 provider / Feishu 账户或数据、真实材料、OS Keychain、原生窗口/DMG、五日/双机或发布场景；这些是 **NOT_RUN**。runtime 元数据为 **UNVERIFIED**；未执行浏览器独立 QA。legacy 无时间戳终态记录可保持 active（bulk 保留了一个作为明确例外），并不会被统计成已完成月归档。Sol 负责最终独立验收判定；本报告不是 gate approval。
