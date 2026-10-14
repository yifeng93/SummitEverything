# M4.2 Package A 离线收口记录

## 合入与验证

用户于 2026-10-14 批准 Package A 离线正式收口及合入 main。PR [#18](https://github.com/yifeng93/SummitEverything/pull/18) 于 2026-10-14T10:42:19Z 合并，PR head 为 `0e8fc4633d4b1409fb7da0354d4474a4faeef430`。GitHub Actions [run 38550700081](https://github.com/yifeng93/SummitEverything/actions/runs/38550700081) 对该 source head 执行的 offline-arm64 / macOS 14 workflow 所有步骤成功，包括 pytest、静态/锁依赖、Web、schema、Swift、build、codesign、DMG 与 packaged backend smoke。工作流显示名称沿用 M4.1，但该运行适用于 PR #18。原始日志无损压缩与 hash 见 [CI evidence](evidence/2026-10-14-m42-ci/README.md)。

PR head 的产品/tests/lock 树与 fixed fresh-QA 产品 SHA `419bb865b334389d1efd0f4a1a855cd0d5324d28` 一致；当前 main 产品树比较 exit 0。QA 对 fixed SHA 的结论与 Sol gate 为 **适用工作包 A 离线技术场景 PASS**，不是整个 M4.2、C25、Stage C 或整款产品 PASS。后续本 docs-only commit 不改变受测产品 SHA。具体 QA 场景和证据限制见 [QA 报告](2026-10-14-M42-PACKAGE-A-QA-REPAIR1.md)及 [Sol gate](2026-10-14-M42-PACKAGE-A-SOL-GATE.md)。

## 最终候选交付

最终固定候选已复制并逐 156 项 manifest 与 DMG SHA 核验，位于主仓库本机忽略目录：

- App：`/Users/yifengstudio/Documents/GitHub/SummitEverything/.local/internal-builds/m42-419bb86/SummitEverything Internal 419bb86.app`
- DMG：`/Users/yifengstudio/Documents/GitHub/SummitEverything/.local/internal-builds/m42-419bb86/SummitEverything-Internal-419bb86.dmg`
- DMG SHA-256：`2e176a2d27f13821f2f82768966719408780c0ed963ee9d9e4413b75ff16f14a`
- 156-file App manifest SHA-256：`9bb4d2c6e511e47812db8cca6e1af56d4dd248e1ca177a92525e1f7271c8c7f0`

这是内部候选；`spctl` 对 ad-hoc 包 exit 3 / rejected。未完成 Developer ID、公证或正式用户安装验收。

## 保留与清理记录

三个 M42 managed worktree 已由原生工具归档并保留可恢复 Git snapshot；ignored `.local/.superpowers` 的独立 tar 备份位于主仓库 `.local/acceptance-archives/2026-10-14-m42/`：`m42-readiness.tar.gz`、`m42-package-a-qa.tar.gz`、`m42-package-a-qa-repair1.tar.gz`，逐文件核验通过。M42 与 M41 已合入的本地/远端 codex 分支已删除。M41 旧 workspace clean detached 保留，两个历史 QA worktree 也保留。三个本轮合成且无使用进程的 DARWIN 临时目录已删除。此记录限于上述对象，不表示全机所有临时目录都已清理；用户数据、工作库、运行中的旧 App 和旧应用均保留。

## 未测与授权边界

以下仍为 NOT_RUN：部分成功后失败项同 operation ID 的真实 UI retry、Real JournalAssist packaged UI、真实 provider/Feishu/OAuth/tasks、四份真实业务材料、真实 Keychain 生命周期、真实账单与答案质量、正式用户安装/覆盖、公证与发布、五日/双机和 M5。Runtime model metadata 与误启动期间 profile/Keychain 是否访问及影响仍为 UNVERIFIED。未读取四份真实 Markdown。用户同意 Package A 合入不授权真实材料、付费 provider 调用、Feishu scope/连接或任务操作。

下一步仅可在用户给出四份 Markdown 的完整路径并单独授权只读事实核对/grillme 后开始；读取不等于批准/入库/外发。首次配置的用户目标、当前必要非秘密字段及实现审计见 [readiness](../../handoff/M42-PACKAGE-A-READINESS.md) 与 [ADR 0009](../../decisions/0009-first-use-provider-configuration.md)。秘密只能由用户在本机安全入口录入，不能通过聊天或写入包。非秘密 WorkspaceId 或完整 endpoints、Feishu AppID 尚待用户提供；提供非秘密配置值本身不授权真实服务连接。真实 OAuth、scope、Keychain 与账户可用性不因合并或 CI 成功而变为 PASS。
