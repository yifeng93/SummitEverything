# 独立 QA 报告：整合本机 LanceDB 索引

- 固定候选：`193aa35a33c667a41a9fe125db4f0caf50d62545`
- 基线：`/var/folders/sc/gywzky152m1_46r5hlv4y3bw0000gn/T/summit-lancedb-integration-qa-0f_mmoxy/checkout`
- 环境：macOS arm64；Python 3.13.2；lancedb 0.40.0；pyarrow 26.0.0；依赖由目标 `.venv` 提供。
- 导入核对：`summit_everything.__file__` 指向固定 QA checkout，组合回归时指向组合副本；没有从 editable 主目录导入。
- 数据边界：测试使用合成临时库与 offline guard；没有访问真实 provider、真实工作库/材料、Keychain、seed 或安装 App。

## 固定 SHA 回归

命令：

```sh
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" /Users/hanwenbo/ai/SummitEverything/.venv/bin/python -m pytest -q \
  tests/integration/test_lancedb_index.py \
  tests/integration/test_legacy_index_rebuild.py \
  tests/integration/test_qualified_retrieval.py \
  tests/integration/test_workspace_mutations.py \
  tests/integration/test_c19_topic_scope_normalization.py \
  tests/unit/test_inspect_index.py \
  tests/integration/test_app_lifecycle.py
```

- 结果：PASS，退出码 0；109 passed，1 Starlette/httpx 弃用告警；用时 16.08s。
- 日志：[fixed-targeted.log](fixed-targeted.log)

## 组合快照回归

先从固定 SHA `git archive` 构造 QA 私有副本，再替换三个经 `qa-input.json` 清单验证的快照文件。哈希均匹配：

- `src/summit_everything/retrieval/query.py`: `b13a81b3546047709b29702728d0ad01bd4dbcdcf045c5793188c79136921940`
- `tests/integration/test_qualified_retrieval.py`: `b4fe89e2ed7c1a312ea4e379763dd47354ee063cfb117536c97a0f951312aefb`
- `src/summit_everything/api/app.py`: `1253e6ee235939024148c94cc91b76dd3dbea776d25a221496044e6767f091cb`

执行相同 pytest 命令，`PYTHONPATH="$PWD/scripts/offline_guard:$PWD/.local/qa/integrated-lancedb/combined/src"`，工作目录为组合副本。

- 结果：PASS，退出码 0；110 passed，1 Starlette/httpx 弃用告警；用时 14.79s。
- 日志：[combined-targeted.log](combined-targeted.log)
- 导入路径核对为 `.local/qa/integrated-lancedb/combined/src/summit_everything/__init__.py`。

## 重点审查结果

- PASS：旧 SQLite-only `vector_json` 行在查询/状态/预览路径不被解码或使用；显式重建失败时旧 schema、pointer 与 chunk 保留；显式成功重建发布 LanceDB 代但保留旧行（由 `test_lancedb_index.py` 与 `test_legacy_index_rebuild.py` 覆盖）。
- PASS：已有 LanceDB 代读取、增量复用、发布失败回滚/并发 CAS，以及查询期间固定代行为通过定向用例。
- PASS：生成后引用资格从当前页面状态重新核验，组合快照相关 qualified retrieval 用例通过。
- PASS：index inspector 空代与 legacy 库只读/哈希不变检查通过。
- PASS：README、PROGRESS、LATEST-IMPLEMENTATION、ADR 0019/0020 中发现的相对 Markdown 链接均指向存在目标。
- 缺陷：`docs/handoff/LATEST-IMPLEMENTATION.md` 当前任务仍写“固定候选 SHA：待提交后填入”，且候选行称“具体 full SHA 由 Git commit 回执给 QA”；但交接及本轮实际固定 SHA 是 `193aa35a33c667a41a9fe125db4f0caf50d62545`。这是可复验入口的元数据不一致，应在交接中补齐完整 SHA。未发现其他直接断链。

## 本轮未运行 / 状态

- NOT_RUN：全量 Python 套件、Ruff/mypy、UI/浏览器、打包/App、真实索引重建、真实 provider/材料、Keychain、runtime model metadata（UNVERIFIED）、真实外部能力与发布门。
- DEV 报告全量回归为 748 passed / 1 failed；失败是已有 `test_stage_b_r4_loopback.py::test_r4_02_deadline_cases_hold_over_ten_consecutive_runs[0.15-cfg1-False]` 首轮冷连接 0.404s 超过 0.25s，原参数重跑 1 passed。该事实来自 DEV 日志，不是本 QA 本轮全量复测；不能称 full clean。

## 结论

针对本轮 LanceDB 集成的固定 SHA 和三文件组合快照，定向离线回归均 PASS。交接 SHA 字段存在一项文档缺陷，建议修复；本报告不构成完整产品或阶段验收通过。
