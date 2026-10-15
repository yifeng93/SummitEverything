# 前端 UX 里程碑 A repair1 fresh QA 归档

本目录归档 fresh QA 对固定产品 SHA `9c33a9dde3080fff3e3b3dd8a4193589ef52575f` 的报告、harness、命令日志、请求清单、截图和视口测量。原始 QA worktree `.local/qa/frontend-a-repair1/` 保持不变；归档文件清单、大小与 SHA-256 见 [evidence-manifest.json](evidence-manifest.json)。复制时排除了 `.venv`、生成的隔离 workspace/事务文件与浏览器临时结果包；报告和文本中的绝对 QA worktree 路径已替换为 `<QA_WORKTREE>`，合成密钥 canary 在 harness 副本中已替换为 `<SYNTHETIC_SECRET_CANARY>`。

QA 报告实际记录：Web 164 passed / 8 todo；typecheck、lint、build、Playwright（2）、隔离 FastAPI/Fake（1）和 F1–F3 复演（3）均 exit 0；lint 有 3 条 React effect warning。所有材料为合成值，本地服务 external attempts 为空。Sol 已核读报告、raw logs、受测 SHA 与 clean 状态，判定适用离线技术门 PASS。该结论不关闭 8 项全站 todo，也不代表真实 provider、OAuth、Feishu、OS Keychain、DMG、进程级重启、五日或双机通过。

原始 QA 报告的撰写时点写明等待 Sol gate；本轮 gate 结论单独记录于 [A Sol gate](../../2026-10-15-FRONTEND-A-SOL-GATE.md)。
