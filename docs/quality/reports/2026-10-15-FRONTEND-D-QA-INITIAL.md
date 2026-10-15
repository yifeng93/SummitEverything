# 前端 UX 里程碑 D 初次独立 QA（历史固定 SHA）

- 固定被测源码与候选 source SHA：`876008e1d33420f57fb31772c76e471379e6b98d`。
- 初次阶段 gate：**FAIL（P1）**。这是 876 的历史结果，不能迁移为 repair1 的结论。
- QA 独立验证完成配置后同 profile/workspace 重启：workspace gate 重现；打开已有 workspace 后再次进入向导模型与密钥 step 2，Today 不出现。Browser mock 用完成态 `{step:5,completed:true,open:false}` 独立复现。根因为 `App.tsx` `onOpened` 无条件设置 step 2，而进度只存在 localStorage、WKWebView 使用 nonPersistent storage，重启丢失。
- 其余初次 QA Web 204/204、typecheck/lint/build、Python 661、Swift 5 与已有 E2E 通过；这不抵消 P1，不表示 D gate 通过。

原始 QA 报告、candidate identity、完整日志、manifest、native 进程身份、截图及复现 harness 均保持不变，仍在 QA checkout 忽略目录：
`/Users/yifengstudio/.codex/worktrees/frontend-d-qa-initial/SummitEverything/.local/qa/frontend-d-initial/`

## 关键原件 SHA-256

| 原件 | SHA-256 |
|---|---|
| `QA-REPORT.md` | `792cc31a6e2123310e5f126292046102251d78879de537054259bf8131ccae05` |
| `evidence/workspace-gate/reproduction.json` | `5dcb5282f41bea6d198c637d37d1f43ec16a40f4245c5a8681c413cd0cf42225` |
| `evidence/native-restart-repro.json` | `dd242ee10fd3d56387faf3a42e2d35aa69b57567e1c05228f4be6ee3603365a2` |
| `evidence/native-preflight.json` | `c6bbaf8554c55baed76c73412dfe3a8774a025aa11aabaaac6874a4d1dfb28b3` |

上述 json 仅为无秘密安全摘要。此 tracked 摘要不复制 native screen captures、profile、trace、token、真实 workspace 或原始日志。完整范围、退出码和限制以 `.local/qa/frontend-d-initial/QA-REPORT.md` 为准。修复轮 1 的执行入口见[下一步 D repair1 交接](../handoff/NEXT-FRONTEND-D-REPAIR1.md)。
