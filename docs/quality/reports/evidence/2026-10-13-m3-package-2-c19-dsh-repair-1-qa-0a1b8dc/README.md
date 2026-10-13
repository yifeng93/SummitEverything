# C19 repair-1 QA evidence

受测产品源码 SHA: 0a1b8dc94a5d8f797161c38430dccfcb211a9e07
QA checkout: /Users/yifengstudio/.codex/worktrees/m3-c19-dsh-repair-1-qa/SummitEverything
最终结果: 本轮离线合成验收 PASS；正式包/M3 gate 由 Sol 判定。

目录:
- raw/: 原始命令输出、exit code、loopback HTTP/SSE、OpenAPI 隔离生成、服务停止状态。
- harness/: 独立 QA 黑盒 harness 和有限 D1/D3 探针。
- ui-observations.md / ui-steps.tsv / ui-ax-snapshot.txt: Chrome CUA 可见 UI 操作和具体页面文字。

SHA256SUMS 覆盖本目录下除清单本身之外的所有文件。命令原文及对应真实退出码索引见 commands.tsv。
