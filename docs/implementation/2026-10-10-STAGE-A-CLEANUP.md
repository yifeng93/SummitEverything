# Stage A 文档与工作环境整理（2026-10-10）

## 范围与基线

用户要求补齐当前文档并整理各类分支，为下一 LUNA 留出清晰环境。本轮只修改当前入口 / 状态文档、追加报告索引与 B/C 执行提示词、整理 Git 引用和可再生缓存；不修改产品代码、测试期望、历史报告 / 证据或产品 MUST，不启动 B/C。

Stage A 收口 main 为 `117086eb2075726730cd7aa62ea0b61498e96f0c`；受测修复代码 `30903c4cdf73855af71a201e3edea6c535ee8199`。整理工作在独立 `codex/stage-b-c-handoff-cleanup` worktree 完成，源码入口最终回到干净 main。整理后的实际完整 main SHA 应从 Git 读取，不能把这个文档所处的后续文档提交冒称为重新受测代码。

## 文档处置

- README、PROGRESS、LATEST-IMPLEMENTATION、架构、API、执行 / 验收入口和全 v1 计划纠正过期的“只有骨架 / 当前仍做 M2.1 / 没有独立 QA”等当前时态。
- 报告索引串联原始缺陷、修复、各轮 QA、重复截图 / 指纹纠正、409b C18 FAIL 与 309 修复 PASS，保留原报告事实。
- 验收矩阵追加 B/C 门，均为 NOT_RUN，原 C01–C31 和 MUST 不变。
- 新增 [B/C 完整提示词](../handoff/PROMPT-STAGE-B-C-LUNA.md)，包含接口依赖、离线独立 QA、逐项真实授权、费用和敏感数据边界、整合及结束语。
- 不删历史报告或归档证据。已不存在的旧 worktree 路径属于当时执行位置，报告保留；当前可复查副本统一用仓库内相对链接打开。

## Git 与 worktree 处置

处理前检查所有源码 worktree 的 tracked / untracked 状态、分支关系、当前相关聊天状态和运行进程。未发现工作中的执行任务；待清理目录均无待提交源码或未跟踪文件。忽略目录另查，不把 `.local` 当成可删缓存。

| 对象 | 处置 |
|---|---|
| 主 checkout | 原 `codex/project-foundation` 已是 main 祖先；切回 main 并 fast-forward 至收口基线，后续再同步本轮文档合并 |
| 18 个旧本地分支 | 建立同 SHA 的本地 `archive/stage-a-2026-10-10/<原分支去掉 codex/>` tag，Git bundle 校验成功后删除旧分支名；没有把独立 QA 的未整合旧树再合入 main |
| 8 个旧远端 codex 分支 | 各头已确认是收口 main 的祖先，归档后按固定 SHA 检查删除；fetch --prune 后远端旧分支消失 |
| 12 个旧 worktree | 固定原 HEAD 后移除，仅含可再生依赖 / 构建 / 缓存或没有忽略文件；未删除业务材料 |
| 10 个带本地 QA 状态的旧 worktree | 原路径保留、detached 在原完整 SHA；`.local` 与私有 QA 状态保留，不查看其中秘密，不上传 |
| 本轮文档工作分支 / worktree | 经检查、PR 与 main 整合后清理，只清理本轮对象 |

删除的远端分支：`codex/m1-docs-current-status`、`codex/m2-feishu-actions-journal`、`codex/m2-stage-a-closeout`、`codex/m2-stage-a-postmerge-report`、`codex/m2-stage-a-recovery-ui-closeout-ledger`、`codex/m2-stage-a-recovery-ui-ledger`、`codex/project-foundation`、`codex/qa-stage-a-evidence-supplement`。

保留的 10 个证据目录位于 `/Users/yifengstudio/.codex/worktrees/`：`8c6c/SummitEverything`、`qa-c18-reconcile-ui-309`、`qa-m1-close-daf726e`、`qa-m1-close-r2`、`qa-m1-close-r3`、`qa-m1-f364c01/SummitEverything`、`qa-stage-a-evidence/SummitEverything`、`qa-stage-a-final/SummitEverything`、`qa-stage-a-recovery-ui-supplement`、`summit-m2/SummitEverything`。不再用于下一阶段运行。

## 归档与恢复

本地私有归档：`/Users/yifengstudio/.codex/archives/SummitEverything/stage-a-20261010-164619/`。

- `source-refs.bundle`：整理前全部 Git refs / 可达对象，已用 `git bundle verify` 验证；不是 `.local` 或 Keychain 的备份。
- `inventory-before.json`：整理前完整分支 SHA、远端 heads、worktree。
- `cleanup-local.json`：逐目录原 SHA 与保留 / 移除决定。
- `cleanup-remote.json`：删除后远端 heads 核对。

目录权限 0700，归档文件 0600；归档 tag 不推送到远端，避免再次发布历史候选。它们是可恢复记录，不是新的验收通过证明。

复查历史源码，先选归档 tag，再在新目录建立只读检查用 worktree，例如：

~~~sh
git tag --list 'archive/stage-a-2026-10-10/*'
git worktree add --detach /独立的新检查目录 archive/stage-a-2026-10-10/m2-feishu-actions-journal
~~~

如需灾难恢复，可从本地 bundle 创建独立 clone；不要覆盖现有 checkout。已保留 `.local` 的目录留在原位置，Git bundle 不含其证据或秘密。

## 可复查的完成门

1. 本轮改动仅文档；`src/tests/web/native` 与 `30903c4` 无差异，旧报告 / manifest / harness 无改动。
2. 相对 Markdown 文件链接无断链，`git diff --check` 通过；历史证据 manifest 按实际条目重算匹配。
3. 文档 PR 合并后源码入口本地与远端 main 一致、tracked / untracked 无改动；只留下 main 活动分支，归档 tag 和 10 个 detached 证据 worktree 保留。
4. 没有调用真实 provider、收费模型、真实凭据或业务材料。本轮 GitHub push / PR / merge 是源码整合网络操作，不能写成所有网络通信为 0。

本轮文档整理不重跑产品自动矩阵，不把文档校验当作新增产品 QA。B/C 仍 NOT_RUN；下一执行者从干净 main 新建实现 worktree，并按提示词依次交付。

整合前实际校验：127 个相对 Markdown 文件链接无断链；五份历史 evidence manifest 共 227 项逐项匹配（43 / 82 / 29 / 26 / 47）；18 个 archive tag 已与原分支 SHA 逐项核对，bundle verify 通过；产品目录与受测修复 SHA 无差异，git diff --check 通过。本轮做文档一致性、权限边界与恢复路径审阅，不将其称为独立产品 QA。
