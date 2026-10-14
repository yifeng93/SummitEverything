# M4.2 PR #18 CI 原始日志归档

- Workflow run: [38550700081](https://github.com/yifeng93/SummitEverything/actions/runs/38550700081)
- PR: [#18](https://github.com/yifeng93/SummitEverything/pull/18)，merge 时间 2026-10-14T10:42:19Z
- 源码 head：`0e8fc4633d4b1409fb7da0354d4474a4faeef430`
- workflow 的显示名沿用 M4.1；此 run 实际针对 M4.2 PR #18。offline-arm64 / macOS 14 所有步骤 success，覆盖 pytest、静态与锁依赖检查、Web、schema、Swift、build、codesign、DMG 与 packaged backend smoke。
- 源日志：`.local/sol/m42-merge/ci-run-38550700081.log`（只读；未修改）。归档为逐字节 gzip。
- 原日志 SHA-256：`f854fb90a08dde5ef67682718465dc1480af1dde8630e9621674ca40c3113973`；gzip SHA-256：`14b65ebe341c172561e59ae045c9b2e331a9816dde3c23fd9d5ede8009906cfa`。解压复验：`gzip -dc ci-run-38550700081.log.gz | shasum -a 256` 应为 `f854fb90a08dde5ef67682718465dc1480af1dde8630e9621674ca40c3113973`；已本地逐字节比较通过。
- `SHA256SUMS.txt` 校验本目录 README 与压缩 payload。
