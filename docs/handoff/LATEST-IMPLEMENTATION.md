# 最新实现交接

## 已合并（2026-10-17）

- PR [#26](https://github.com/yifeng93/SummitEverything/pull/26) 已按正常 merge commit
  合入 main：`f1b990a156e5757ac619f3202c4aefd82c8be2c3`；PR head
  `e76f2c0d42ef894323a94bbb760aa37b53d5be0c`，CI `offline-arm64` **PASS**（4m31s）。
- 产品修复提交：`fe78ba47099f61daf1f4e49f7191eddb9ad544b2`；基线 `e1cb028`。
  合并后 main 产品树与 `fe78ba4` 一致。
- 修复：设置页新增飞书日历身份（应用/用户）与日历 ID；真实模式隐藏不受支持的
  可见范围筛选，材料固定按妙记关键词搜索。
- 离线回归：Python 731 passed、Web 243 passed / 27 files；Ruff/format/mypy、
  typecheck/lint/build、内部 App/DMG 构建、codesign、hdiutil verify、packaged smoke
  通过。
- 真实 `Test2` 验证：飞书 OAuth 已授权；任务读取正常；`identity=user` 日历 3 条；
  妙记查询「会议」20 条（空查询 0 条）。未导入材料，未执行任务写回。
- DMG：`.local/internal-builds/fe78ba4-20261017/SummitEverything-Internal-fe78ba4.dmg`
  （source `fe78ba4`，`dirty=false`，SHA-256
  `3deb5ddc113518961e0b3cc2cf463ee29e976deb89a213340dfbcaba20d6c497`）；未公证。

## 此前已合并

- PR [#25](https://github.com/yifeng93/SummitEverything/pull/25)，merge
  `2e76f4c94d1f77e2b7285e93b7ef9ef7526a9bc2`，产品 `c82aecf`：API key 点分隔格式、
  整理 kind、失败取消和检索标题 scope 修复。

## 分支与清理

- 本地与远端分支现仅保留 `main`；已合并且确认是 main 祖先的
  `codex/credential-key-shape-20261017`、`codex/organize-kind-fix-20261017`、
  `codex/retrieval-title-scope-20261017`、`codex/feishu-settings-20261017`
  均已删除。
- 历史 QA worktree 与 `.local` DMG/证据保留，未删除。

## 后续门

- 飞书材料导入、任务写回、已安装 App/公证、五日、双机、发布、整站完整业务和
  WCAG AA 审计仍 **NOT_RUN**；Keychain 完整生命周期未单独验收；runtime model
  metadata **UNVERIFIED**。
- 新一轮任务从 main 新建 `codex/` 分支；不要重启旧 Stage B 或沿用旧 SHA 结论。

当前产品状态唯一来源为 [PROGRESS](../implementation/PROGRESS.md)，固定版本证据见
[报告索引](../quality/reports/README.md)。
