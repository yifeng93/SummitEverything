# 2026-10-13 清理与恢复记录

本记录说明在本次维护中已实际完成的本地归档、工作树和分支清理。清理对象均来自主 checkout 中的盘点清单；清单之外的项目、主 checkout、`_vault`、真实资料、凭据和已安装应用不在范围内。

## 被清理对象与保留点

- 删除了盘点中 12 个已结束且 clean 的本项目工作树，包括四个 DSH-C19 临时工作树。12 个 HEAD 均有本机 Git tag `archive/cleanup-2026-10-13/<slug>`，并包含在已验证的完整 Git bundle 中。清理前已有的 `archive/cleanup-2026-10-13/SummitEverything` 额外 ref 仍保留，指向 C03 pilot commit `2251ec8e32c1ada3d79cbe4f9feae5169b540bfd`；它不是额外工作树，也不计入本轮 12 个 snapshot。
- 其中 11 个工作树含有本地 `.local` 模拟验收状态，分别打包成独立的 `.tar.gz` 并读取校验；另一个 `m3-integrated-packages` 没有 `.local` 目录。另一个重复的 C03 pilot 本地状态压缩包经逐文件 SHA256 比较后移除；规范备份 `c03-delete-copy-pilot-local.tar.gz` 保留。
- 删除了五个已结束的本地分支：`codex/c03-delete-copy-pilot`、`codex/c03-delete-copy-qa`、`codex/dsh-c19-20261012`、`codex/m3-integrated-packages`、`codex/m3-postmerge-closeout`。删除前使用预期 OID 比对；原 OID 已由冻结 tag 与 bundle 保留。
- 远端 C03 pilot 分支由 Sol 独立删除，本记录不执行远端 refs 操作。Sol 保存了原始命令回执。
- 当前主 checkout 的 `.local/archives/2026-10-13-pre-next-stage-cleanup/` 私有恢复包目录权限为仅所有者访问。它包含 `inventory.json`、`cleanup-backups.json`、SHA256 清单、bundle、11 个 `.local` tar 和逐工作树删除回执。没有将这些本机模拟库、临时证据副本或私有 bundle 加入 Git。
- Native archive 请求曾返回 queued，但当时并未删除目录；后来通过核对路径、HEAD 与 clean 状态后执行的精确 `git worktree remove` 才完成实际删除。这里不声称 UI archive 状态。

## 恢复方法

在本项目 Git 仓库中，冻结 tag 已可直接作为恢复点：`git worktree add --detach <新路径> archive/cleanup-2026-10-13/<slug>`。需要完整对象包时可使用 `.local/archives/2026-10-13-pre-next-stage-cleanup/pre-next-stage-cleanup.bundle` 执行 `git bundle verify` 后再 fetch 对应 tag。压缩的 `.local` 仅是模拟验收过程数据；按 `cleanup-backups.json` 中路径与归属核验后，才可解包回相应恢复树的 `.local/`。不要把压缩包内容覆盖到主 checkout，也不要将其作为真实业务资料。

具体恢复路径、每个工作树 OID、tar SHA256 和执行退出码见同一私有目录的盘点及收据；该目录不进仓库。若私有备份目录不在原位置，应先从本机安全备份恢复它，不依赖已删除的 checkout 路径。

## 当前范围

本清理不启动 M4/M5、Stage C 真实连接、真实 provider / Feishu、OS Keychain、业务材料、native/DMG、发布、五日或双机验收。相关边界仍见[当前最新交接](LATEST-IMPLEMENTATION.md)与[验收矩阵](../quality/ACCEPTANCE.md)。

## 独立验收收口

产品源码固定 SHA `6a33259224097167cfdde689da93258fe925964e` 的独立离线 QA 判 PASS，QA-only 证据提交 `da76f56b765308a365eafd0927c84e88caec492e`，其 37 项 manifest SHA-256 `88a960e757ccd4de719a9574706b8964263f0ff705eaa377f2dd4f34d61ef6e3` 经 Sol 核验。QA 报告见[独立 QA 记录](../quality/reports/2026-10-13-PRE-NEXT-STAGE-CLEANUP-QA-6a33259.md)。QA 后状态文档收口没有修改产品源码；合入状态以 Sol 后续 Git/PR 核对为准。

随后在主 checkout 按白名单删除 19 个 ignored、未跟踪的可再生目录：`.pytest_cache`、`.mypy_cache`、`.ruff_cache`、根 `dist`、`web/dist`、已确认 ignored 的 `native/.build`，以及 `src/`、`tests/`、`scripts/` 下 13 个 `__pycache__`。逐路径检查确认目标不是 symlink 且没有 tracked 文件后才删除。完整路径清单和动作收据保存在主 checkout 私有 `.local/archives/2026-10-13-pre-next-stage-cleanup/primary-cache-cleanup-2026-10-13.json`（0600）；`.venv`、`web/node_modules`、全部 `.local` 数据、stash 与其他资料保留。
