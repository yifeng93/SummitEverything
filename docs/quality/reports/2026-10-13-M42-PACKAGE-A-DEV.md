# M4.2 工作包 A Developer 交接

日期：2026-10-14。受测产品源码固定为 `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b`（`codex/m42-readiness-20261013`）；本报告与后续文档证据提交不改变该产品 SHA。独立 QA 尚未开始，Developer 自测不是验收结论。

## 交付范围

真实模型整理、索引、问答与 Feishu 只读/导入现在都经过单次服务端 approval plan：预览绑定 workspace/profile、配置、具体上下文或来源版本，显式用户确认后由原业务路由执行；范围或配置变化、取消、过期、异库、未确认均拒绝。账本使用有限请求上限、原子锁写、unknown/no-resend 与 provider 用量记录。用量缺失保持未知，账本不推算真实账单。模型使用显式受限的 thinking 与输出预算；真实 Feishu task 写仍保持禁用。

计划、记录和界面采用业务标题与范围。Ask/Today 标明的是 HTTP 请求上限，不表示费用金额；Details 可查技术 ID/hash。设置能力状态写作“已配置，待本次确认”。Feishu、query 与索引计划取消会撤销服务端计划。Native App 只转发值为 `1` 的 `SUMMIT_OFFLINE_GUARD_ACTIVE`；受保护运行会使用 `UnavailableSecretBackend`，真实 Keychain 保存入口失败关闭。

产品与手册已同步：[README](../../../README.md)、[API-v1](../../contracts/API-v1.md)、[验收矩阵](../ACCEPTANCE.md)、[准备卡](../../handoff/M42-PACKAGE-A-READINESS.md)。旧 README 的“普通整理/索引问答仍拒绝”和旧 AC B03/B04 全局门控仅描述其标明的旧固定 SHA。M4.2 新行为需要 fresh QA。

## Developer 检查结果

以下结果来自 worktree 的实际命令。完整逐命令原始日志、退出码、命令映射与 SHA-256 清单位于 [最终检查证据](evidence/2026-10-13-m42-package-a-dev/final-20261014/)。历史上修复前失败的日志原样保留；以对应的 GREEN / FINAL 行为准。

| 检查 | 结果 |
|---|---|
| `env PYTHONPATH=scripts/offline_guard:src uv run pytest -q` | PASS，508 passed，1 warning，exit 0 |
| failure-boundary 与真实 adapter loopback 正/负路径 | PASS，Mock HTTP + 合成凭据；未替换整体 query/review 服务，exit 0 |
| Ruff check / format check、mypy、lock check | PASS，exit 0 |
| Web tests / typecheck / lint / production build | PASS；最终 Web 61 tests，exit 0 |
| Swift tests | PASS，3 tests，exit 0 |
| `uv build` | PASS，wheel 与 sdist，exit 0 |
| 固定源码 Internal `.app` / DMG clean rebuild | PASS，release 脚本 exit 0，clean manifest，DMG 创建及只读挂载检查完成 |

全量结果末段为 pytest 508、Web 61、Swift 3。初始 Ruff 和 AskView 失败项及其修复前原始日志继续留存，不从 evidence 删除。早期 baseline/RED 原始执行日志没有保存；这里没有伪造或重建。

## Clean 候选

- 源码 SHA：`fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b`，build manifest `dirty=false`。
- 候选目录：`/Users/yifengstudio/.codex/worktrees/m42-readiness/SummitEverything/.local/dev/m42-package-a/final-20261014/artifacts/SummitEverything Internal fe47339.app`。
- DMG：`/Users/yifengstudio/.codex/worktrees/m42-readiness/SummitEverything/.local/dev/m42-package-a/final-20261014/artifacts/SummitEverything-Internal-fe47339.dmg`，SHA-256 `0b1404971711b0823c2a236882bb619fe891612704bf9d02de32050c03c16f5f`。
- App manifest：版本 `0.1.0`；build ID `20261013T233919Z-2aab5e81a62d`；frontend SHA-256 `2aab5e81a62dbabd517c132014df2cf86f7e157718ed1f2c8f8981ba41f66627`；dependencies SHA-256 `2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`。
- App 为本机 ad-hoc internal 候选；没有安装、覆盖应用或绕过 Gatekeeper。SDK 对话框/UI 使用候选真实 WKWebView。完整 release 输出见 35 号日志。

## 隔离 UI 复演与边界

使用 macOS `open -n` 启动 clean candidate，同时只传入 `SUMMIT_OFFLINE_GUARD_ACTIVE=1` 和位于 `DARWIN_USER_TEMP_DIR` 下的 `SUMMIT_INTERNAL_TEST_PROFILE_ROOT`。逐进程检查只提取 guard 是否等于 `1` 及 profile-root 路径是否匹配，native 与 backend 均为 true；profile 的实例锁在该临时根目录，workbook manifest 也证明 UI 使用所建的合成 workspace。正确启动下，设置页显示“钥匙串不可用”，保存/删除密钥按钮禁用；Fake 今日页模拟授权、展示 Fake 材料与空日历，并把一份“模拟会议”合成材料导入到隔离 workspace 的待整理项。真实整理、用户审核、索引、问答的原生 UI 闭环未复演。没有确认任何真实计划，没有录入密钥，也没有调用真实 provider、Feishu 或读取真实材料。最终临时 profile 位于 `/private/var/folders/yp/7n9pls2j2rl0sz9vmfdf4z6r0000gn/T/summit-m42-package-a-final.30cK8y`；隔离 workspace 在仓库 `.local/dev/m42-package-a/final-20261014/browser-workspace-verified/`。

第一次 UI 尝试使用 shell 直接执行 `.app/Contents/MacOS/SummitEverything`。设置页错误显示“钥匙串可用”；随后核查发现实际 LaunchServices 窗口/backend 进程可以脱离 shell 启动，丢失禁用标志。该次 profile override 是否同样丢失、是否落在默认 `~/Library/Application Support/SummitEverything Internal`，以及该次是否发生 Keychain 查询均 **UNVERIFIED**。仅读取该默认目录的目录 mtime（`2026-10-13 14:56:23 +0800`），没有读写、删除、清理其中任何内容；目录时间不能证明本轮未触碰。第一次候选状态不作离线安全 PASS。之后使用 fresh `open -n` temp profile 启动方式，native 与 backend guard 和 profile-root 匹配均确认 true，设置 UI 显示钥匙串不可用。两次启动的差异与限制须由独立 QA 保留复验。

本次 UI 观察由 CUA 对真实原生候选的 AX 树及屏幕完成；目前没有另存 UI screenshot 文件。浏览器 DevTools 控制台/网络面板没有接入，未声称其已通过。

## 尚未完成或未测

- 本报告不提供独立 QA verdict；需 fresh QA 在独立 checkout 固定相同产品 SHA。
- 真实 provider/Feishu/OAuth/业务材料、用户显式选择的业务范围、实际 token/账单、真实系统 Keychain 生命周期、真实用户安装、C28 五个实际工作日、双机、Developer ID/公证/发布均 NOT_RUN。首轮错误候选过程的 Keychain 查询次数 UNVERIFIED。
- Runtime 模型元数据 UNVERIFIED。Fake / Mock / loopback 成功不代表真实网络或内容质量。
- Today 的原生选择器仍一次单文件；已确认的批量文件/文件夹导入未补。真实 journal assist 未接入一次性计划，因此未声称受控真实整理。
- 真实 Feishu task create/patch/write 仍禁用，因为缺乏可独立证明最终结果的 provider 协议端点。

## Fresh QA handoff

固定产品 SHA 是上述 `fe473399...`。QA 应按[已提交的权威执行计划](../../superpowers/plans/2026-10-13-m42-integrated-packages.md)和[独立验收手册](../../handoff/TESTER.md)做完整包验证，先确认 clean manifest，再对计划无确认/取消/超期/越界、provider Mock 正向闭环、用量计账/资源关闭、stable replay、Feishu身份/授权代次和真实 native offline guard 做反例与路径验证。Native QA 必须使用新的临时 profile，采用 `open -n --env SUMMIT_OFFLINE_GUARD_ACTIVE=1 --env SUMMIT_INTERNAL_TEST_PROFILE_ROOT=<DARWIN_USER_TEMP_DIR 下新目录> <candidate.app>`；只看设置页确认为“钥匙串不可用”后才可继续 Fake UI。对首次错误直接启动的结果保持 UNVERIFIED，绝不能表述为“0 次 Keychain 查询”。禁止真实服务、用户资料、密钥和实际费用。
