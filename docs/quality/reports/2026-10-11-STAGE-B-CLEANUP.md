# Stage B 工作区收口与恢复记录

用户选择：先制作可恢复归档，再清理完成/闲置的本地与远端分支及工作树；不触及其他项目或活跃QA。

旧工作树11个均在删除前核对HEAD、Git status为空和归档SHA-256。原始tracked/untracked及非重建文件（含.local测试证据）已存档；.venv/node_modules/.build/dist/缓存排除。完整Git历史另存all-history.bundle并git bundle verify成功。归档根目录：`/Users/yifengstudio/.codex/archives/summit-stage-b-20261011`。删除使用git worktree remove，无reset/clean/强制覆盖。

| 旧工作树 | HEAD | 恢复tar.gz | SHA-256 |
|---|---|---|---|
| /Users/yifengstudio/.codex/worktrees/8c6c/SummitEverything | `51b3654ba068c11da377359ad23ac3ec7684dd81` | 8c6c-recoverable.tar.gz | `d17bc64fd9edbde60f7f7c119385bd873c9c263d2ade34776cfdaab9d1b89907` |
| /Users/yifengstudio/.codex/worktrees/qa-c18-reconcile-ui-309 | `2d6254c4c2717857fda8ccaa97c210b41e0c695e` | qa-c18-reconcile-ui-309-recoverable.tar.gz | `5f5bc4994aa3e27048cb3a44bf94612a21f37be787a33e1e6ed227e6d90a99b6` |
| /Users/yifengstudio/.codex/worktrees/qa-m1-close-daf726e | `23579b65b50b80fadffcd815ea96b8aee1fc5400` | qa-m1-close-daf726e-recoverable.tar.gz | `930b1857e72b7fc0bce35fd114b1cfd8cfaf4d9db927ca60347ad429cbb83635` |
| /Users/yifengstudio/.codex/worktrees/qa-m1-close-r2 | `34522507f2c5c9856ed859f0593e1967190cae41` | qa-m1-close-r2-recoverable.tar.gz | `31e169f705f5105ef7906e22e3d3aabc8caad6c5436f0b98579c03863e02f9c6` |
| /Users/yifengstudio/.codex/worktrees/qa-m1-close-r3 | `b407e3807f9a36ffdfce758e10f4c9d04e29d47e` | qa-m1-close-r3-recoverable.tar.gz | `7b577b58dddeefc2a62afb582acbd4c232040f2ed151bed003ba3adb398509d1` |
| /Users/yifengstudio/.codex/worktrees/qa-m1-f364c01/SummitEverything | `c4f755f648324bf714000e2765fa99917909692b` | qa-m1-f364c01-recoverable.tar.gz | `a4d33ceca5018c1cad15c417be2b89a708c6f7c972c68576e94a4db3c2cf35da` |
| /Users/yifengstudio/.codex/worktrees/qa-stage-a-evidence/SummitEverything | `c51272fc046a0cff1b0f30f99730f138573b2f11` | qa-stage-a-evidence-recoverable.tar.gz | `57d5e81e4bb68508d98024433b57129b63b20b09b73cd28cba58357f66e4266e` |
| /Users/yifengstudio/.codex/worktrees/qa-stage-a-final/SummitEverything | `0531e0d1b95eb8dbb56af9237e39e21fcdf1d6f8` | qa-stage-a-final-recoverable.tar.gz | `77aceb7f56d23607d956234ceb1d2c02f2f46de2cdd2c5a313e00162f0662fe3` |
| /Users/yifengstudio/.codex/worktrees/qa-stage-a-recovery-ui-supplement | `998b4d2fa1165cecb71c9baf8ff6610a516d3df0` | qa-stage-a-recovery-ui-supplement-recoverable.tar.gz | `053a68e146ef9ec1f4ab97321675869424ba2c58b45638a3dd116b9af414d780` |
| /Users/yifengstudio/.codex/worktrees/stage-b-real-providers/SummitEverything | `0a1db5d72e6ac11184d28e65dea3ba008762ba43` | stage-b-real-providers-recoverable.tar.gz | `fe24eb92c68ca2a10318a930023efe77c961a0b72dc329790783b47d3c2b4d24` |
| /Users/yifengstudio/.codex/worktrees/summit-m2/SummitEverything | `53ad04829bbf71bf010eb9aa2a652c3f0845c1eb` | summit-m2-recoverable.tar.gz | `25e5ed9967fd0e1028653d7fa792940e79c61a2ff327ab9bcf235ea51ee829ac` |

旧 M1 QA 原生应用 local.qa.summiteverything.m1 在确认闲置和归档后由正常Quit退出；8793/5173已释放，未借用该窗口测试新候选。当前固定SHA独立QA工作树仍保留，待证据导入和归档后清理。main/远端分支清理与合并核验待QA结果。

恢复方式：在新的隔离目录解开对应tar.gz；从all-history.bundle读取原HEAD建checkout并恢复归档文件。原未提交R4起点另有deepseek-r4-dirty-source.tar.gz和deepseek-r4.diff。恢复后重建依赖；不能仅靠缓存重新认定历史PASS，也不要把已用的真实调用账本归零。
