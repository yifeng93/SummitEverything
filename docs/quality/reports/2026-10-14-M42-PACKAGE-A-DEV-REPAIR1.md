# M4.2 Package A 修复轮 1 Developer handoff

本轮固定产品源码 SHA 为 `419bb865b334389d1efd0f4a1a855cd0d5324d28`。此前实现提交 `4c6b0bdd453db63f7f59599592c6c725303a6e1e` 已修复 unknown 计划 GET 与完整问句 planner，并补齐规格既有的多文件/文件夹输入和 Real Journal Assist。旧候选 `bc5018ddc1c781bcb2b016a176d4d17623d7311b` 的真实 packaged UI 闭环证据保留原样。之后发现有效文件与零字节文件混选会被原生层严格整批拒绝，但 UI 将其表现为静默取消；本轮 Native 最小修复保持严格整批策略，并只在可信 NSOpenPanel 确认选择但校验失败时显示通用可操作提示，用户主动 Cancel 仍无提示。Native 策略新增回归测试。`419bb86` 相较 `4c6b0bd` 的 `src/`、`web/`、`uv.lock` 完全一致，产品 delta 仅 Native Swift 源码与测试。

这是 Developer 自测 handoff；fresh QA 正等待对固定源码 `419bb86` 独立验收。任何 Developer PASS 都不等于 M4.2 / C25 / 全产品验收通过。

## 固定 419bb86 候选和构建

新建的候选输出未覆盖此前候选，release 脚本强制重建前端。build-info 中 source SHA 为 `419bb865b334389d1efd0f4a1a855cd0d5324d28`、`dirty=false`，build ID `20261014T050331Z-788b29e2f3bb`。前端 SHA-256 `788b29e2f3bb8b95736179ed07af6fa0d02eea17b3e881f92a8d79f2e70cb2ec`；依赖 SHA-256 `2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`。

- App：`/Users/yifengstudio/.codex/worktrees/m42-readiness/SummitEverything/.local/dev/m42-package-a/repair1-empty-feedback/artifacts/SummitEverything Internal 419bb86.app`
- App：156 个文件；相对路径 + 内容 SHA-256 manifest 摘要 `9bb4d2c6e511e47812db8cca6e1af56d4dd248e1ca177a92525e1f7271c8c7f0`。逐项清单在 [candidate-419bb86-app-SHA256SUMS.txt](evidence/2026-10-14-m42-package-a-repair1/candidate-419bb86-app-SHA256SUMS.txt)。
- DMG：`/Users/yifengstudio/.codex/worktrees/m42-readiness/SummitEverything/.local/dev/m42-package-a/repair1-empty-feedback/artifacts/SummitEverything-Internal-419bb86.dmg`
- DMG SHA-256：`2e176a2d27f13821f2f82768966719408780c0ed963ee9d9e4413b75ff16f14a`
- 构建、codesign strict verify、`hdiutil verify` 分别 exit 0；逐项原始 log/exit 与 build identity 在 [证据包](evidence/2026-10-14-m42-package-a-repair1/README.md)。

## 自动检查

4c6b0bd 固定代码树的完整离线验证记录沿用并保留在证据包：guarded Python 513 passed；ruff check / format、mypy、`uv lock --check`、`uv build`、OpenAPI TS 生成及 diff check 均 exit 0；Web 实际 65 passed，typecheck、lint、production build exit 0。lint 保留了 2 条 React `set-state-in-effect` warnings。419bb86 只改 Swift，Python/Web/lock 树相等由固定 SHA diff 确认。Native 在新 SHA 上重新执行 `swift test --package-path native`：exit 0，5 passed。

## 419bb86 实际 packaged WKWebView 观察

将 App 复制到新的 `DARWIN_USER_TEMP_DIR` 临时子目录，再以 `open -n --env SUMMIT_OFFLINE_GUARD_ACTIVE=1 --env SUMMIT_INTERNAL_TEST_PROFILE_ROOT=<fresh child>/profile <candidate.app>` 通过 LaunchServices 启动。进程 checker exit 0：native/backend guard 均为 1，native profile 与 backend `SUMMIT_PROFILE_ROOT` 均 canonical-match。只记录必要布尔值，没有输出完整环境或 session token。

真实 WebKit file upload control 打开 macOS 原生 Open panel：选择 alpha.txt、beta.md 和 0-byte empty.txt 后，UI 显示“文件未导入”以及“所选文件未导入。请确认文件为非空 TXT / Markdown 且符合大小和数量限制后重新选择。”，没有把该失败伪装成 Cancel，且 inbox 保持 0。再次打开后主动按 Cancel，没有提示，inbox 仍为 0。只选择 alpha.txt + beta.md 时，UI 显示两个待导入条目；点击导入后两项均显示“已导入 · 已保存到待整理”，inbox 为 2。证据为保存的关键 AX 状态记录 [ui-419bb86-native-selection-feedback.txt](evidence/2026-10-14-m42-package-a-repair1/ui-419bb86-native-selection-feedback.txt) 和 guard/open 原始日志。CUA 本轮没有提供将新截图写入 evidence 目录的支持方法，因此没有声称保存新候选截图。

旧的 `bc5018d` 候选真实 UI 复演在相同 Python/frontend 产品树上验证过目录 FileList、Fake journal assist 取消/采用后独立保存与同 profile 重开，以及用初验批准正文、无自包含问句，在两条初验原问句下取得完整“访客离开时，前台补记离开时间。”引用。其原始记录与候选身份明确保留在证据包旧文件中；这部分不是 `419bb86` 的现场 UI 运行，必须由 fresh QA 在新固定候选上重新验证。

## 未测边界与 handoff

- UI 中通过 API / native 对“已部分成功后仅失败项用同一 operation ID 重试”的实际 fault retry 为 **NOT_RUN**。Real-mode Journal Assist preview/provider 网络路径为 **NOT_RUN**；Fake Runtime/Mock adapter 与 Web regression 覆盖按旧记录描述，不冒充实际 Real UI。
- 本地 Keychain 录入 / 轮换 / 删除，真实模型、Feishu/OAuth/task、真实业务材料、账单和质量，正式用户安装/覆盖或绕 Gatekeeper、Developer ID/公证、五日/双机/发布均 **NOT_RUN**。模型 runtime metadata **UNVERIFIED**。初次错误启动的 Keychain 查询次数和默认 profile 回退仍 **UNVERIFIED**。
- 不要把 4c6/bc5018 候选拿来替代 fixed `419bb86`；fresh QA 需固定 `419bb865b334389d1efd0f4a1a855cd0d5324d28` 全量复验 API P1/P2、Native 选择拒绝/取消和有效多选、目录安全、journal 生命周期及精确问答问题。qa 期间产品源码保持不动。

完整原始检查、初验 34 个 QA 原始文件的字节副本、旧候选 UI 和新候选 manifest/Build/UI 记录均在 [evidence README](evidence/2026-10-14-m42-package-a-repair1/README.md)，对应相对路径 SHA-256 manifest 在同目录 `SHA256SUMS.txt`。初验原报告不改写。
