# M3 包 3 repair 1/2 独立复验

**包 3 离线复验：PASS。** 本轮固定产品源码 `ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`，独立 QA HEAD `7fd8a538cf99fd3b8b23bf30a7032cb9b42cdea2`。此前 C22 lease 异常缺陷的两条修复路径均由独立故障 harness 复验通过，包 3 相关自动矩阵、归档 / bulk 与本机浏览器短复演也通过。没有观察到包 3 新缺陷。

**整体 M3 仍不能通过：已知 C19 P1 保持 FAIL。** 包 2 固定报告 `2026-10-12-M3-PACKAGE-3-QA-22e5ad9.md` 中的 C19 反例显示，缺少相关资料时仍会引用无关预算页。本次包 3 修复没有改 retrieval / planner / query；该既有失败及 Sol 对包 2 的 FAIL 决定继续有效，本报告不将其豁免。由 Sol 按原矩阵作最终 gate 判断。

## 固定目标与隔离

- QA checkout：`/Users/yifengstudio/.codex/worktrees/m3-package-3-qa-r1/SummitEverything`
- 被测 HEAD：`7fd8a538cf99fd3b8b23bf30a7032cb9b42cdea2`
- 产品源码：`ea11fc5a06bed61c18c1527c0c0db6f4dad36c5f`
- 固定目标在开始和结束时均为同一 SHA。`git diff --quiet <产品源码> <被测HEAD> -- src web native config tests` exit 0；工作树结束时 clean。源码相对初验 QA SHA `22e5ad945353929ebd781e1397f641c9d5fcf963` 的差异限于 `intake/actions.py`、`intake/review.py` 与两条新增集成回归；`web`、API schema/types、`native`、配置及其他 tracked tests 无差异。
- 按 README 使用 `scripts/offline_guard`。运行仅使用 FakeFeishu、FakeLLM、隔离 workspace/profile、合成凭据；没有调用真实 provider、真实 Feishu、Keychain、真实材料或账户。
- 所有新增文件只在 QA evidence 目录和 `.local/qa/m3-package-3-repair-1/`；没有更改产品实现或已有 tracked tests。

## 复验结果

| 范围 | 结果 | 独立观察 |
|---|---|---|
| C22 action：首次 `running` receipt 原子保存失败 | **PASS** | 新 harness 向真实 FastAPI route 注入 OSError，响应 HTTP 500。保留异常对象和 traceback 时 lease 文件已删除、`attempt_is_live=false`；receipt 保持 `confirmed`，FakeFeishu 任务数为 0。同 operation 恢复保存后重试 `succeeded`，远端任务总数恰为 1。未调用 `gc.collect()`。 |
| C22 intake job：acquire 后 jobs 目录 mkdir 失败 | **PASS** | 保留异常和 traceback；无 lease、无 job record，item 仍 `pending`，FakeLLM 调用为 0。失败后 jobs 目录与 job 文件均未创建；同 operation 重试完成且只调用 FakeLLM 一次。 |
| C22 live owner、死 owner 无 checkpoint、checkpoint 仅恢复本地稿、取消后迟到 CAS、同 operation 并发/202+Location/不同 hash 冲突 | **PASS** | 当前 440 全套及 99 项核心回归均通过；具体相关回归见 `tests/integration/test_intake_review.py`、`test_actions.py`。初验固定源码的独立复演也已通过这些场景；本次源码改动限于取得 lease 后的失败清理。 |
| C21 profile/workspace 边界与待审稿接续 | **PASS（受测范围）** | 初验固定 SHA 已独立验证 profile 本地状态隔离；本轮两个独立 profile 实际打开同一隔离工作库，均看见同一份待审稿和 unknown 来源。角色 / 历史 / memory / index 的跨设备行为不由此浏览器观察扩展推断。 |
| Unknown 显式重处理 UI | **PASS** | 两个真实本机 WebUI 均显示 unknown；选中后提示“不会自动重发”，显式重新整理会创建新操作、可能再次调用模型，且保留原件和稿件。未触发重新整理按钮。 |
| C23 月归档、原件/草稿保留与四类 transaction 记录 | **PASS（离线范围）** | 120 个 Fake 整理流程分布在 2026-06 至 2026-09；item/job 各归档 120 条、transaction 共 366 条，捕获/变更/write-intent/合成 Feishu 四类记录均有计数。回放后 provider 仍为 120 次；120 份原件和完整草稿保留；完成流程没有 active item/job、lease 或 checkpoint。unknown item/job 与 1 条 legacy-undated item 留在 active。 |
| C23 归档失败 / 相同副本 / 非法或意外副本 | **PASS（已执行矩阵）** | 注入 summary 原子写失败后 active 不丢；完全相同的 active/archive 副本可读；非法月份及意外副本拒绝且保留 active。冲突、损坏、running/unknown 条目和 active+summary 读取另由当前核心回归及初验固定 SHA 的故障矩阵覆盖。 |
| 归档 progress proof reconcile | **PASS** | receipt 先设为 unknown，proof 已在月摘要；reconcile 返回 succeeded，progress version 保持 1，没有重复应用。 |
| Fake Feishu 实际导入—归档/重启同意图重放 | **PASS** | `test_selected_body_calls_and_restart_replay` 通过；重放使用本地结果，不再次读取原件正文。未计为 bulk 中真实 provider 调用。 |
| C13/C14/C20 相关回归 | **PASS（离线关联范围）** | 当前全套、99 项核心及 37 项 qualification/mutation 回归通过；初验报告覆盖归档知识检索、刷新/重启引用状态和用户记忆候选边界。包 3 repair 不涉及检索、session 或记忆实现。 |
| C19 缺资料比较误引用无关预算 | **FAIL（包 2 已知 P1）** | 固定初验报告 `22e5ad9` 的 `known-c19.log` 已实际复现并由 Sol 判包 2 FAIL。本轮不重复大型基线样例；本次源码差异未触及 retrieval/planner/query，不能关闭该缺陷。 |
| Web/API console、network、PNG | **NOT_RUN** | 本机浏览器通过 accessibility tree 实际复演 UI；当前 CUA surface 未提供 DevTools console/network 导出或 PNG 文件落盘。 |
| 跨机 OneDrive 并发写、真实模型/Feishu、OS Keychain、真实材料、Native/DMG、五日、双机、发布 | **NOT_RUN** | 本轮只验证合成离线范围。跨机 `flock` 不是分布式锁。配置没有证明真实 runtime 暴露值，runtime 继续 **UNVERIFIED**；合成 smoke 计数维持 **0/1**。 |

## 自动检查命令与结果

原始日志及每项实际 exit code 见 `evidence/2026-10-12-m3-package-3-repair-1-qa-7fd8a53/raw-logs/`；`COMMANDS.md` 列出可复跑命令。首轮 full pytest 在 fresh checkout 未安装 Web 包时，`test_runner_uses_its_ports_and_stops_only_its_owned_services` 失败（439 passed / 1 failed，runner exit 2）。该日志未删除；按 README 运行 `npm --prefix web ci` 后重跑，完整 guarded 后端为 **440 passed / exit 0**。两轮仅有既有 Starlette/httpx deprecation warning。

- `uv sync --locked --group dev`、`npm --prefix web ci`：exit 0。
- `PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q`：安装 Web 包前首轮失败记录保留；安装后 440 passed，exit 0。
- 修复期望独立 harness `repro_repaired_lease_failures.py`：action 与 job 两异常通过，exit 0。
- 包 3 核心回归：99 passed，exit 0；qualification / workspace mutations：37 passed，exit 0。
- archive failure matrix、archived progress proof reconcile、FakeFeishu import/restart replay：各 exit 0。
- bulk sample：120 完成、4 业务月份、provider replay 总数不变，exit 0。
- Ruff check、format check、mypy（43 files）、`uv lock --check`、`uv build`、OpenAPI types 生成：均 exit 0。
- Web：56 tests、typecheck、build 均 exit 0；lint exit 0，保留既有 TodayView / ProjectsView 两条 effect warning。

## 浏览器、清理与下一步

本轮浏览器记录见 `evidence/.../browser-observations.md`。profile A reload 后看见待审稿和 unknown；profile B 用独立 profile 打开相同隔离库后观察到同样结果。选中 unknown 时两边均显示显式重处理提醒。未把历史初验的 WebUI 证据冒充为本轮复演；本轮观察是在代码未变的 UI 树上补做。

两个 `scripts/run_dev.py` 实例已 Ctrl-C 停止；检查 16173、16174、17993、17994 端口均无 LISTEN，见 `services-stopped.txt`。SHA 在验收期间未变化，最终产品 diff 为 0，QA checkout clean。QA-only report/evidence commit 只保存本轮报告与脱敏证据，由 Sol 检查并决定是否接收；Sol 的最终 gate 仍须保留包 2 C19 P1 FAIL。
