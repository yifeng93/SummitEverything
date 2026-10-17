# 最新实现交接

## 当前候选：飞书身份/日历与材料筛选（QA PASS，待推送/CI）

- 分支：`codex/feishu-settings-20261017`；产品提交
  `fe78ba47099f61daf1f4e49f7191eddb9ad544b2`；基线 `e1cb028`。
- 修复：设置页新增飞书日历身份（app/user）与日历 ID；真实模式隐藏不受支持的
  可见范围筛选，材料只按妙记关键词搜索。
- 验证：Python 731、Web 243、typecheck/lint/build、DMG 构建与 packaged smoke 通过；
  真实日历（identity=user）3 条，真实妙记查询「会议」20 条。
- DMG：`.local/internal-builds/fe78ba4-20261017/SummitEverything-Internal-fe78ba4.dmg`
  （source `fe78ba4`，SHA-256 `3deb5ddc…c497`，未公证）。
- 详见 [DEV 记录](../quality/reports/2026-10-17-FEISHU-SETTINGS-DEV.md)。

## 已合并（2026-10-17）

- PR [#25](https://github.com/yifeng93/SummitEverything/pull/25) 已按正常 merge commit
  合入 main：`2e76f4c94d1f77e2b7285e93b7ef9ef7526a9bc2`；PR head
  `e6e9ffcf6d0259c6db46cb68e7f8a3a51f842fec`，CI `offline-arm64` **PASS**（4m36s）。
- 产品修复提交：`c82aecf09b195ddcbae40e3b5c5db31d959aea6e`；基线 `e1bbcee`。
  合并后 main 产品树与 `c82aecf` 完全一致；后续提交仅文档。
- 修复：百炼点分隔 API key 被旧白名单误拒；整理提示词与 `kind` schema 冲突；已提交计划
  不可取消时的英文提示与残留对话框；页面标题未参与检索 scope 导致已确认页面 0 引用。
- 离线回归：Python 731 passed、Web 241 passed / 26 files；Ruff/format/mypy、
  typecheck/lint/build、内部 App/DMG 构建、codesign、hdiutil verify、packaged smoke
  通过。
- 真实 `Test2` 验证：整理 job completed（12 稿，DeepSeek 3137/1408 tokens）；索引
  4 chunk（embedding 299 tokens）；问答“学员28号晚住宿需求自动勾选流程是什么？”
  得到 1 条引用，真实调用 embedding 28 / rerank 85 / DeepSeek 390+588 tokens。
- DMG：`.local/internal-builds/c82aecf-20261017/SummitEverything-Internal-c82aecf.dmg`
  （source `c82aecf`，`dirty=false`，SHA-256
  `775d147bab3f4c6ce9c669b95e1a97464f15b9691952885550da29aa9de6f6c5`）；未公证。

## 后续门

- 真实飞书 OAuth/读取、已安装 App/公证、五日、双机、发布、整站完整业务和 WCAG AA
  审计仍 **NOT_RUN**；Keychain 生命周期未单独验收；runtime model metadata
  **UNVERIFIED**。
- 分支 `codex/retrieval-title-scope-20261017` 保留，未删除；QA worktree 与本地 DMG 保留。
- 新一轮任务从当前 main 新建 `codex/` 分支；不要重启旧 Stage B 或沿用旧 SHA 结论。

当前产品状态唯一来源为 [PROGRESS](../implementation/PROGRESS.md)，固定版本证据见
[报告索引](../quality/reports/README.md)。
