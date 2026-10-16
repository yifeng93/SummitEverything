# 证据包：App 图标 + DMG 卷图标 独立 QA（固定 SHA `deed704`）

对应报告：[`../../2026-10-16-APP-ICON-QA.md`](../../2026-10-16-APP-ICON-QA.md)

受测 SHA：`deed704b16f2e7adee56e18136b4290d713912fa`
QA checkout：`/Users/yifengstudio/.codex/worktrees/qa-appicon`（detached，已清理）

原始未脱敏日志（含完整构建输出）保留在 QA checkout 的 `.local/qa/appicon/`；本目录只放**小型脱敏摘录**与 QA 自写 harness。

| 文件 | 内容 |
| :-- | :-- |
| `A-no-regression.txt` | A 组：改动面、指纹、pytest/ruff/mypy/vitest/typecheck/lint/build/e2e 的真实退出码与计数 |
| `C-icns-fidelity.txt` | C 组：`.icns` 身份、逐档墨色像素实测、≥64px 逐像素比对、参数标定、iconutil 无损往返、四角/底板色 |
| `D-fail-closed.txt` | D 组：QA 独立对抗 harness 18 项结果 + 篡改实验（真实构建路径 fail closed） |
| `E-artifacts.txt` | E 组：真实构建退出码、CFBundleIconFile、签名、UDZO、卷图标、`C` 位、smoke、DMG SHA 不可复现证据 |
| `ci-run-38838074701.json` | CI run 的独立确认（`gh run view`：conclusion=headSha=workflowName） |
| `harness/qa_inkcount.py` | QA 自写墨色像素计数器（Pillow），不复用实现者脚本 |
| `harness/qa_compose.py` | QA 自写最小合成器（只读 `assets/branding/logo-mark.svg`） |
| `harness/qa_adversarial.py` | QA 自写 fail-closed 对抗 harness（`importlib` 载入构建脚本） |
| `harness/qa_tamper.sh` | D4 篡改实验脚本（含 `git checkout --` 还原与 trap） |

本目录不含任何凭据、token、真实业务数据或用户材料；`.icns` 为二进制专利产物，未随证据入库。
