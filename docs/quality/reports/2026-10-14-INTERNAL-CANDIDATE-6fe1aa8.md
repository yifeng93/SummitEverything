# 内测候选记录：`6fe1aa8`（设置 UX + F2 整合）

分支 `codex/internal-candidate-20261014`（自 `codex/settings-ux-20261014` 开出并合入 `codex/origin-guard-error-20261014`）。**固定产品 SHA `6fe1aa8f7d3957232b8a34baf17bb70dfe966f5d`**，`dirty=false`。本记录由 Sol 编写，用于交付一个可供用户配置试用的内部候选；**不代表**阶段通过或真实外部能力验收。

## 包含内容

- 设置页卡片化（工作库 / AI 模型 / 飞书三卡 + 状态徽章 + 高级折叠区）与 5 步首次配置向导；密钥只进内存、提交后清空、不落任何持久化；连接检查必须显式确认本次范围。
- 非秘密接入值（Feishu App ID、原生 callback、两个百炼 Base URL）由本机 Git 忽略文件在构建时注入包内 `Resources/first-use-defaults.json`；运行时只认显式环境变量与包内资源；secret 形态键名或未知键 fail closed。
- profile 只保存用户显式覆盖；提交值等于注入默认值时不落盘，未覆盖过的 profile 跟随构建更新；注入永不「修复」损坏的 section 或字段。
- F2 修复：`origin_guard` 读取损坏 profile 时返回设计好的 503 JSON 信封，而不是裸 500（此前连修复用的 `PATCH` 也 500）。
- 合并冲突仅出现在 guard 的设置读取处：一侧加注入默认值、一侧加 `SettingsError` 处理，合并后**两者都保留**。

## 验证（Sol 本机执行）

| 检查 | 结果 |
|---|---|
| guarded 全量 pytest（合并树） | **594 passed**, exit 0（设置分支 591 + F2 的 3 项契约测试） |
| `ruff check` / `ruff format --check` / `mypy src` / `uv lock --check` | 全部 exit 0 |
| web `npm test` | **90 passed**, exit 0 |
| 完整打包 `scripts/release-macos.sh` | exit 0，DMG `hdiutil verify` CRC VALID |
| `scripts/smoke_packaged_app.py` | PASS（身份、静态 UI、未授权读写、端口冲突、父进程清理） |
| 包内端到端验证（自写脚本） | **29/29**：注入生效、保存不固化、换默认值跟随、secret 形态键启动失败、section 级与字段级损坏都不被静默接受**且都返回设计好的 503 信封** |
| DMG 挂载复核 | 包内 `first-use-defaults.json` 四个键与来源一致；`build-info.json` 的 `source_sha=6fe1aa8…`、`dirty=false` |

## 候选身份

- App：`.local/internal-builds/internal-6fe1aa8/SummitEverything Internal.app`（157 个文件）
- DMG：`.local/internal-builds/internal-6fe1aa8/SummitEverything-Internal-6fe1aa8.dmg`
- DMG SHA-256：`644affebbe88c501d893615f6be45bbe2bbed0e616baccd36279de7d7381a8be`
- `build-info.json`：`source_sha=6fe1aa8f7d3957232b8a34baf17bb70dfe966f5d`、`dirty=false`、`build_id=20261014T142210Z-0d21a90f194c`、`app_version=0.1.0`、`frontend_sha256=0d21a90f194cbe035f29b9545125101289a8e4a82de23bb0f0139fc9afdc21f0`、`dependencies_sha256=2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`
- ad-hoc 本地签名、**未公证**；`spctl` 结论沿用历史（exit 3 / rejected，未绕过系统安全设置）。

## 独立 QA 覆盖情况（如实说明）

- `codex/settings-ux-20261014` 侧：四轮独立 QA（D1/F1/F3 已修复并复核），证据归档在 [设置 UX QA 证据](evidence/2026-10-14-settings-ux-qa/README.md)。
- `codex/origin-guard-error-20261014` 侧：一轮独立 QA，7 项全 PASS，证据归档在 [F2 QA 证据](evidence/2026-10-14-origin-guard-settings-error/README.md)。
- **合并后的 SHA `6fe1aa8` 本身尚未经过独立 QA**：它由上述两个已验收分支合并而成，冲突解决只涉及一处（两者都保留），并由 Sol 跑了全量 594、静态检查、web 90、完整打包与包内 29/29。若需要，可对合并 SHA 再开一轮独立 QA。

## 用户试用边界

- 安装是本地、可回退动作：复制到新文件夹、不覆盖已有应用。
- 真实密钥录入会**首次真实使用 macOS 钥匙串**（此前验证均在 guard 下禁用钥匙串，故该生命周期仍为 NOT_RUN）。密钥只应在应用设置里输入，不经聊天或终端传递。
- 连接检查（每项一次、跨运行累计、约 ¥0.01 级）与任何真实业务调用仍需用户当场确认；飞书任务写继续禁用。
- 真实 provider/飞书账户/OAuth/scope/材料/账单与答案质量、正式安装与公证、五日、双机、发布仍 **NOT_RUN**；新界面未做浏览器或真机视觉复核。
