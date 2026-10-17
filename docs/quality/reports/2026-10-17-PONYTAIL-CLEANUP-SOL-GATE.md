# Ponytail 精简 — Sol 最终门判断

日期：2026-10-17。初始基线：`6f8fe80558d6e51481f6a3dd203c7e53e6faad89`。

## 固定对象与判断

| 对象 | 固定受测 SHA | Sol 判定 |
|---|---|---|
| 文档批次一 | `f57c7ed3a6d2e6763e1624aa3fd08187f5c4d796` | PASS，仅文档专项 |
| 代码批次二及内部包技术检查 | `5835faa72b513202e92694f4fa14790afefe1e70` | PASS，仅实际执行的离线技术门 |

实际代码提交为 `2d90a7e9efc9ed67f6a0260323f9b071d586f7a1`。后续 DEV/QA/状态交接均为文档；Sol 实际运行产品树等同性比较，exit 0。两批各一次 fresh Luna QA，产品自动修复 0 轮；QA 报告标题、日志归档和范围说明的交付收口没有重跑产品测试，不构成额外验收轮次。

## 已核验的证据

- [文档 QA](2026-10-17-PONYTAIL-CLEANUP-DOCS-QA.md)及原始 checker 输出：271 个当前入口链接/锚点无错误，31 个 C 行及 5 个 R 行与基线原文相同，3,348 个既有报告/evidence Git blob 不变；产品、测试、依赖及三份产品/前端规格零差异。Sol 独立比较 blob、验收行与保护树，exit 0。
- [代码 QA](2026-10-17-PONYTAIL-CLEANUP-CODE-QA.md)的[24 条命令/实际退出码](evidence/2026-10-17-ponytail-code-qa/commands.tsv)与原始 stdout/stderr：Python 712、Web 239、Playwright 2+1、Swift 5；Ruff、format、mypy、lock、Python/Web build、生成类型一致性、App/DMG 构建、strict codesign、hdiutil verify 和 packaged smoke 均 exit 0。基线→候选的 scope diff exit 1 是预期的四行删除；代码提交→完整候选的产品树 diff exit 0。
- 20 份原始日志只归档一份，Sol 实际运行 `shasum -a 256 -c logs-sha256.txt`，20/20 OK、exit 0。包内 `source_sha=5835faa72b513202e92694f4fa14790afefe1e70`、`dirty=false`；Sol 重算 DMG SHA-256 为 `b97594003fc753be16ca455f0681f9e51a8055e4962916f3c06a612d232bee47`，与 QA manifest 相同。
- Sol 以 AST 定位原函数，验证实际源码差异只有 `job_attempt_hash` 四行定义的删除；归档摘要与版本链代码保持原文，测试、断言、前端、native、脚本和依赖零差异。未找到证据的精简候选保留，理由见[DEV 记录](2026-10-17-PONYTAIL-CLEANUP-DEV.md)。
- 文档 QA 日志的 `initial status entries=1` 发生在 checker 自身 evidence 目录已创建之后；QA 补充说明创建前实际 `git status --short` 为空。此条不是已有产品改动或产品失败。

## 文档整合与例行维护

Sol 在验收后将 PROGRESS 改为当前结论、LATEST 改为后续动作，并将报告索引的旧“当前已验收”叙述改为固定版本导航，避免继续复制过时 main 状态。此收口只改状态/索引和本判断，另做链接、保护原件与产品树检查，不宣称它又经过一次 fresh QA。

本次仅删除未调用 helper，不改变产品行为、API、工作库格式或验收门，按已授权例行维护规则整合。已查询 main 无保护规则；合并仍以准确 PR tip 的 CI 成功、无冲突及产品树等同为条件，保留分支/worktree。远端 CI 和合并事实以该 PR 对应 SHA 的实际记录为准，本文不提前宣称它们通过。

## 风险与未测

既有两条 Oxlint warning、Starlette/httpx 弃用提示与 603.32 kB 主包提示保留；前轮 e2e artifact ENOENT 根因仍未确认，本轮未再现。真实 provider/飞书、业务材料、凭据/OS Keychain、用户安装/公证、五日/双机/发布、完整全站业务和 WCAG AA 审计均 NOT_RUN；runtime model metadata UNVERIFIED。包 smoke 不替代原生 UI、用户安装或发布验收。

本机空间清理只完成恢复包准备与校验，源目录未删；主 checkout 私有清单 `.local/archives/2026-10-17-ponytail-cleanup/CLEANUP-REQUEST.md` 列出三个历史 worktree 与五个缓存/输出目录，执行前须用户另行批准。无权限/范围例外，无测试或验收标准降低。
