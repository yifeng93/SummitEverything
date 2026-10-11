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

旧 M1 QA 原生应用 local.qa.summiteverything.m1 在确认闲置和归档后由正常Quit退出；8793/5173已释放，未借用该窗口测试新候选。以下为第一批清理时点；随后固定SHA独立QA已完成，最终清理见追加记录。

恢复方式：在新的隔离目录解开对应tar.gz；从all-history.bundle读取原HEAD建checkout并恢复归档文件。原未提交R4起点另有deepseek-r4-dirty-source.tar.gz和deepseek-r4.diff。恢复后重建依赖；不能仅靠缓存重新认定历史PASS，也不要把已用的真实调用账本归零。

## 最终追加清理（2026-10-11，PR #10合并后）

最后9个试验/QA工作树均先保存原HEAD、原status、报告/源码/harness/log与非重建.local证据，再逐项校验tar内容并验证Git bundle。2个Codex托管工作树经archive_worktree归档；其余经Git移除。未提交报告先已导入main，并在tar中保留原件。运行时pyc缓存未归档；原manifest列入的4条pyc及发布纠正见[收口记录](2026-10-11-STAGE-B-POSTMERGE.md)。

| 工作树 | 原HEAD | 恢复归档 | SHA-256 |
|---|---|---|---|
| /Users/yifengstudio/.codex/worktrees/qa-stage-b-luna-backend-576895f/SummitEverything | `576895f6983ca41cacbbad45a9075b97b9986189` | final-qa-stage-b-luna-backend-576895f-recoverable.tar.gz | `1dc2dc6c51142c64710151947d2e608580a7f6bbe7079b5f8d96f997a34884c8` |
| /Users/yifengstudio/.codex/worktrees/qa-stage-b-luna-final-backend/SummitEverything | `fd2042385c4916598337239f5259b3ef1889372a` | final-qa-stage-b-luna-final-backend-recoverable.tar.gz | `536a2151d05eadda492ca1451cdcea01502f945b942f4444380ebad185876af3` |
| /Users/yifengstudio/.codex/worktrees/qa-stage-b-luna-final-ui/SummitEverything | `fd2042385c4916598337239f5259b3ef1889372a` | final-qa-stage-b-luna-final-ui-recoverable.tar.gz | `2764be49f93993671ecbbe1869811f8233983eb2f072ed13ea426775404eef57` |
| /Users/yifengstudio/.codex/worktrees/qa-stage-b-luna-ui-retest-576895f/SummitEverything | `576895f6983ca41cacbbad45a9075b97b9986189` | final-qa-stage-b-luna-ui-retest-576895f-recoverable.tar.gz | `057ac20d79c5d48eb70ad550bafab111778135d9433b16132260de1d6199d437` |
| /Users/yifengstudio/.codex/worktrees/qa-stage-b-refresh-final/SummitEverything | `8b6259a9aa6ff2e52b700134abadff24de46dc08` | final-qa-stage-b-refresh-final-recoverable.tar.gz | `aecd88e6dfd35dbcbc558473fc400b64f0f6ba2e33d9e4dad265b0f6bb48735a` |
| /Users/yifengstudio/.codex/worktrees/qa-stage-b-sol-backend/SummitEverything | `7f3119a511fda6f3d2771af4cf09fd9a9026edb7` | final-qa-stage-b-sol-backend-recoverable.tar.gz | `76396a908dbc3f93a7bd441b04fa0b58a54faf7d1e339afc4b882a3ba04f8b5c` |
| /Users/yifengstudio/.codex/worktrees/qa-stage-b-sol-ui/SummitEverything | `7f3119a511fda6f3d2771af4cf09fd9a9026edb7` | final-qa-stage-b-sol-ui-recoverable.tar.gz | `d343ef5f1b43398eb8040ea96bcd72b086204db2f5a61475607c9fbc1a36e425` |
| /Users/yifengstudio/.codex/worktrees/qa-stage-b-ui-retest/SummitEverything | `8b6259a9aa6ff2e52b700134abadff24de46dc08` | final-qa-stage-b-ui-retest-recoverable.tar.gz | `255df7744f1bdd0d987f9fd6597979fdf728fed70295feae9d218a60711cd6c6` |
| /Users/yifengstudio/Documents/GitHub/SummitEverything-deepseek-stage-b-trial | `5196c8f1c1b9da54aea5bbcb2149297594f60268` | final-SummitEverything-deepseek-stage-b-trial-recoverable.tar.gz | `c666cf909b8a89bf9acc23bb84798bc93b8840879440a7f000578ed73c6515b7` |

最终Git bundle：`stage-b-final-history.bundle`，SHA-256 `aa9db5a0b471fe8d89301eee976199731751f9dbab2e51fd687ae81e7e393213`；bundle verify与tar逐文件核对日志已归档。20个工作树已清理，只剩main；本地及远端的codex/deepseek-stage-b-trial、codex/stage-b-real-providers已删除。历史证据、Git归档标签和Codex恢复引用保留。归档只在本机，不包含真实业务材料/密钥；依赖与构建缓存需重建。

最终复核发现fd后端QA遗留两个服务进程组，确认PID/cwd/端口归属后终止，仅清理本轮相关服务。对应记录与最终端口扫描见postmerge evidence。不要将transfer worker为0等同于所有进程已退出。
