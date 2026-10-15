# B repair1 QA 脱敏证据索引

固定产品 SHA：`a0ccad8bcd46814a23c74d00bbba1d1d5f98699c`。Sol 核验 B 适用离线核心与两项修复 PASS；全站、C/D、真实服务和交付门不在结论内。QA 完整结论见[报告](../../2026-10-15-FRONTEND-B-QA-REPAIR1.md)。

QA 原件保留在独立 checkout 的 `.local/qa/frontend-b-repair1/`，未修改：原报告 SHA-256 `a3038530f85457459577ba0ea7b4c40a92c9f98150e12606de3698dd67a6118e`。原始 exit/log、网络证据和 screenshots 留在该 ignored `.local` 目录，不复制进 Git；其中临时 profile/runtime/token、完整浏览器 trace 也不纳入本归档。

| 脱敏原件 | SHA-256 |
|---|---|
| `scope-network-evidence.json` | `a772ad301f7e106df2ce8fcbd5870175082a30d8b5aa60c46eb6e82c2d7f2e77` |
| `valid-confirm-evidence.json` | `55c39ec5c01be58717e2fdad241190d6f72b1ccca86361e5d9e355bbb9bb39ef` |
| `real-scope-focus.log` | `a35a508fc5834f296def6dfa0eb168876de77c28aef591571213899573834833` |
| `fake-integration.log` | `a6420827996b408883a7da676574e2b9976867572d55c150d70890f86e37a47a` |
| `e2e/measurements.json` | `11ea93ebaac6a64c23941fc75de13caa20da19096e92dcea60a75d6614f6cfdf` |
| `fake-integration/workflow-manifest.json` | `48d151a60570d9bd87a9e84da1fe24d235bcb0f87f562e162f0535f6bc8113d7` |

`npm-ci`, `web-unit`, `typecheck`, `lint`, `build`、`offline-e2e`、`real-scope-focus`、`fake-integration` 对应 `.exit` 内容均为 `0`，统一文件内容 SHA-256：`9a271f2a916b0b6ee6cecb2426f0b3206ef074578be55d9bc94f6f3fe3ab86aa`。逐条命令见上方 QA 报告。该索引不替代 Sol 对证据的原件核验，也不升级为全站验收结论。
