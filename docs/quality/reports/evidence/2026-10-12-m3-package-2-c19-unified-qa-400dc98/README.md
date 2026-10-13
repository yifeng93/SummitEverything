# C19 QA 证据

本目录记录固定候选 `247f6708c68812e8b217b1079a2fe953ebb06960` 在完整交接 HEAD `400dc98c4b0a555561bb98f6633cf1d22ece8550` 上的独立验收。复现代码只在 `.local/qa` 环境运行；本目录提交仅包含 QA harness、脱敏输出、检查日志与观察记录，没有产品代码或 tracked tests。

- `raw-logs/guarded-pytest-final.log`：全量 guarded pytest，exit 0。
- `raw-logs/c19-holdout-final-matrix.log`：独立 holdout，7 passed / 5 failed，exit 1（12 项）。
- `reproductions/`：unknown-dimension、对象名/主题维度交叉污染和 S11 标题别名 JSON actuals，包括 provider passages、citation excerpt、missing、body。
- `ui-observations.md`：真实 Chrome UI 的黑盒可访问性树观察摘要。
- `harness/`：独立的 holdout pytest 及最小复现脚本。
- 其余 `raw-logs/*` 保存 npm/Web、Ruff、mypy、lock、build 与监听端口实测日志及退出码。

哈希见 `SHA256SUMS`。
