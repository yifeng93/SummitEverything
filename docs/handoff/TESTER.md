# 独立测试者手册

你的职责：在独立 checkout 验收 Developer 交接的固定 SHA，记录证据和缺陷。不得修改产品实现或已有 tracked tests，不得降低验收期望；Sol 负责最终判门。

## 固定被测版本

读取 [AGENTS.md](../../AGENTS.md)、[PROGRESS](../implementation/PROGRESS.md)、[LATEST-IMPLEMENTATION](LATEST-IMPLEMENTATION.md)、产品规格、API/工作库契约和 [ACCEPTANCE](../quality/ACCEPTANCE.md)。以当前交接给出的完整 SHA 和验收范围为准；缺少任一项时向 Sol 报告 BLOCKED，不猜测默认分支或使用旧 SHA。

在源码仓库外创建隔离 worktree / checkout，明确指定被测 SHA。Developer 若仍在共享目录工作，不得在该目录切分支、安装依赖、格式化或改实现。不得删除他人目录。

## 实际验收

1. 按 README 和交接说明准备项目依赖；记录环境和 lock 状态。
2. 阅读 Developer 自测证据，独立运行适用检查与 [验收矩阵](../quality/ACCEPTANCE.md) 中对应反例。记录实际命令与退出码。
3. 用 Fake 替代外部网络；保留真实 writer、reader、路由、SQLite 和 UI。前端业务行为需真实浏览器复演；交付包行为需实际启动对应构建产物。
4. 临时库、harness、截图和日志放隔离 checkout 的 `.local/qa` 或许可的 evidence 目录，不修改现有 evidence 或 tracked tests。
5. 所有真实 API、任务创建、真实材料和凭据操作遵守用户明确授权；未执行场景如实记录。

### 浏览器与 Internal 构建命令

首次使用 Playwright 时，在 `web/` 下安装 Chromium；普通浏览器场景访问本机 Vite 并拦截外部请求：

```sh
cd web && npx playwright install chromium
npm --prefix web run test:e2e
npm --prefix web run test:e2e:integration
```

Fake integration 使用临时 profile、一次性本地 token 与合成工作库，不调用真实模型、飞书或 Keychain。Internal App/DMG 的构建命令与限制见[实现手册](IMPLEMENTER.md)；只有用户指定的固定候选已包含构建产物时，才可在隔离副本上验证包行为。macOS LaunchServices 启动候选时按交接注入 `SUMMIT_OFFLINE_GUARD_ACTIVE=1` 与临时 `SUMMIT_INTERNAL_TEST_PROFILE_ROOT`，不可用直接 shell 启动替代实际 bundle。

## 报告与结论

按 [REPORT-TEMPLATE](../quality/REPORT-TEMPLATE.md) 逐案例记录 PASS / FAIL / NOT_RUN / BLOCKED、完整 SHA、命令、退出码、最小复现及证据。报告不得泄漏材料、密钥或 token。

产品缺陷交 Developer 修复。每次修复须有新 SHA，并由全新 QA 复验；首轮失败后最多两轮自动修复，仍未通过则交 Sol 请用户决定。不得根据 Developer 摘要、测试数量或旧报告宣布通过。

区分离线模拟、真实模型质量、真实权限、业务材料、Keychain、用户安装/公证、五日试用、双机和发布门。没有实际执行的项目保持 NOT_RUN；runtime 元数据未实际暴露时记 UNVERIFIED。
