# 最新实现交接

## 当前候选：API key 形状修复（未合并、未独立 QA）

- 分支：`codex/credential-key-shape-20261017`；基线 `e1bbcee0f9e3e71e077e813db360cb3b802b57c3`；产品修复 SHA：`f1f0982be75aadd9a74021a7ee5641317ddc2113`。
- 现象：真实阿里云百炼 key 为 `sk-` 开头的点分隔 JWT 风格字符串，被旧的 `[A-Za-z0-9_-]` 白名单误拒；DeepSeek key 正常。不是用户输入错误。
- 修复：key 校验接受单行可见 ASCII（仍禁空白/控制/非 ASCII/引号），并同步两处日志与 provider 文案脱敏；新增点分隔 key 的接受与整体遮蔽回归。见 [DEV 记录](../quality/reports/2026-10-17-API-KEY-SHAPE-FIX-DEV.md)。
- 自测：定向 54 passed、全量 719 passed、Ruff/format/mypy exit 0；内部 App/DMG 构建、strict codesign、hdiutil verify、packaged smoke 均通过。DMG 路径与 SHA-256 见 DEV 记录。
- 边界：未执行独立 QA，未合并、未推送；真实 provider / 飞书 / Keychain / 安装与公证 / 五日 / 双机 / 发布仍为 NOT_RUN。
- 后续：用户在应用内用真实 key 复验连接检查；通过后再安排独立 QA、CI 与合并。

## 已合入基线

Ponytail 精简已合入 `main`（`e1bbcee`）；当前产品状态唯一来源为 [PROGRESS](../implementation/PROGRESS.md)，其历史证据和 Sol 门见 [报告索引](../quality/reports/README.md)。
