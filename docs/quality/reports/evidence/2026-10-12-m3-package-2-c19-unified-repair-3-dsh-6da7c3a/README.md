# C19 repair 3（DSH 试修）DEV evidence

- 受测固定源码 SHA：`6da7c3a8303ec310d6e87f0981f1abf3b9204f7d`（修复 `18fe80a36d5ac0d592a7fbcf7404a7324d639c15` + tracked 回归 `6da7c3a`）。
- 起点：`b3d0dff587c94ee295dfe5379bd67916c98184ec`（`handoff/c19-dsh-2026-10-12`），起点产品源码 `f79f613a902758da3173a5b27219fa568a912f5e`。
- 分支 `codex/dsh-c19-20261012`；工作树 `/Users/yifengstudio/Documents/GitHub/SummitEverything-DSH-C19-20261012`。
- **结论：DEV PASS（仅执行者自测）。独立 QA NOT_RUN**，由 Sol 调度另一个 checkout 的全新 QA。历史 FAIL 不改写。
- 只用 Fake/offline provider、loopback 与隔离合成工作库；未使用真实模型/飞书/凭据/Keychain/真实材料，未消费 smoke，未构建 DMG。

## 目录

- `harness/test_c19_previous_holdout.py` — 冻结的旧 12 项 holdout tracked 副本（未改动）。
- `harness/test_c19_r2_expanded_matrix.py` — 冻结的最后 22 项 expanded 矩阵 tracked 副本（与 corrected 文件逐字节相同，未改动；不双计）。
- `harness/reproduce_device_topic.py` — 最小黑盒复现（tracked 副本）。
- `harness/reproduce_scope_normalization.py` — 本轮新增边界观测脚本（设备/年度/专项/工作正反控、对象跨度分离、generic plan）。
- `harness/api_c19_replay.py` — 本轮新增实际 API/SSE + history reopen 复演（真实 uvicorn、隔离 profile、loopback）。
- `harness/test_c19_topic_scope_normalization.py` — 本轮新增 tracked 回归副本（仓库内路径 `tests/integration/test_c19_topic_scope_normalization.py`）。
- `raw-logs/` — 逐命令 `.log` 与 `.exit`，以及 RED/GREEN 的 JSONL 观测。
- `commands.tsv` — 命令、exit 与结果。
- `final-state.txt` — 复演后工作树、SHA、监听端口与外部边界。
- `SHA256SUMS` — 本目录文件哈希清单。

## RED → GREEN 关键原始日志

| 文件 | 含义 |
|---|---|
| `raw-logs/baseline-holdout-34.log` / `.exit` | 修复前 12+22 = **7 failed / 27 passed**，exit 1 |
| `raw-logs/baseline-device-topic.log` | 修复前最小复现：`term:访客领用`、只引预算、单问 provider 0 次 |
| `raw-logs/fix-holdout-34.log` / `.exit` | 修复后 12+22 = 34 passed，exit 0 |
| `raw-logs/fix-tracked-regressions.log` / `.exit` | 新增 tracked 回归 15 passed，exit 0 |
| `raw-logs/fix-device-topic.jsonl` | 修复后最小复现：两段支持进入引用与 provider passages、missing 空 |
| `raw-logs/fix-scope-normalization.jsonl` | 修复后边界观测（含 `年度`/`专项`/`工作` 正反控） |
| `raw-logs/fix-api-replay.log` | 实际 API/SSE 13 项观测全部 PASS + history reopen 正确 |
| `raw-logs/fix-pytest-full.log` / `guarded-pytest.log` | 全量后端 465 passed（基线 450 passed） |

所有 harness 与原始日志均为本轮 DSH 自测产物；本目录不构成独立 QA 结论。
