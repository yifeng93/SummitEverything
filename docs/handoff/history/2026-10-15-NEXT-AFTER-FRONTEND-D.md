> 历史归档（2026-10-16）：PR #21 已合入 main（merge commit `12280ec1893f8f526b9b73a84b98416545254f42`），本文件的「下一步 1/2/3」已全部落地；当前起点页是 [NEXT-STAGE-2026-10-16.md](../NEXT-STAGE-2026-10-16.md)。

# 下一步：前端 D 收口之后

## 当前固定状态

- **前端 UX 线 A→D 已全部通过各自的离线范围**；**D 最终固定产品源码 `e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374`**（链 `876008e` → repair1 `faa1edd` → repair2 `96fdf4d` → repair3 `e8e1dba`），分支 `codex/frontend-ux-20261015`，产品 tree clean。
- Sol 判定：**P1 CLOSED；D 门限「离线 + 内部候选」范围 PASS**。依据见 [D 最终 QA](../../quality/reports/2026-10-15-FRONTEND-D-QA-FINAL.md)与 [Sol 最终门判断](../../quality/reports/2026-10-15-FRONTEND-D-SOL-GATE-FINAL.md)。
- 最终 native 候选：`SummitEverything-D-e8e1dba.app` / `.dmg`（DMG SHA-256 `5f9805eb8ced1ccacbdd32f2e63a70d74ee94b67f9dd18375a893ba3e779bb2b`，build ID `20261015T144744Z-784ae1ee176a`，`source_sha=e8e1dba`、`dirty=false`）。包内 runtime 自建 harness 15/15；实机 WKWebView 三条路径以本机 Vision OCR 机器判读通过。
- **PR [#21](https://github.com/yifeng93/SummitEverything/pull/21) 已开（含整条前端 UX 线 A→D，217 文件 / +15341 −1755）。合并仍需用户明确批准。**

## 下一步（按顺序）

1. **PR #21 的真实 CI 已通过**：`pull_request` 事件触发 `.github/workflows/m41-internal-app.yml`（`offline-arm64`），run [`38757225760`](https://github.com/yifeng93/SummitEverything/actions/runs/38757225760) **completed / success，4m42s**，全部步骤 success——含 `Guarded Python checks`、`Web checks and API types`（**D-6 那条门**）、`Native upload policy tests`（`swift test --package-path native`）、`Build and verify internal App and DMG`。此前所有 CI 门都只是本地精确复现；这是第一次真实远端运行，并顺带覆盖了 `swift test` 与 App/DMG 构建校验。若后续再改动产品，需重跑该 CI。
2. **用户批准后合并**（AGENTS：重要里程碑合并需用户批准）。合并后应做一次 merge 后核对：main 的产品/tests/lock 树与 `e8e1dba` 一致，并在文档中记录 merge commit、CI run 与「PR head ≠ 受测产品 SHA」的区分。
3. **合并后收尾**：更新 README / PROGRESS / LATEST-IMPLEMENTATION 的合入事实；把 repair1 的历史交接（[history/2026-10-15-NEXT-FRONTEND-D-REPAIR1.md](2026-10-15-NEXT-FRONTEND-D-REPAIR1.md)）保持原样仅作追溯。

## 仍未关闭的项（按性质分开）

- **D-3（INFO）**：`GET/PUT /api/v1/first-use/progress` 的 OpenAPI 只声明 200/422，未声明实际存在的 401/404/503。前端依赖 404 `first_use_progress_absent` 做控制流，建议后续补契约描述。属小切片。
- **D-5（P3，用户已决议接受）**：新建工作库后若一步都没走就 reload/重启，会落到今日并给非阻塞提示（`create` 意图只在内存）。已在文档中把「新建仍走向简」限定为「点击创建那一刻」。
- **D-2（P3，dev 专属）**：React StrictMode 下旧 localStorage 迁移会发两次载荷相同的 PUT；生产构建恰好一次。已按生产构建语义表述。
- **`swift test`**：本地未重跑（`native/` 在 `876008e..e8e1dba` 未改），但**真实 CI 已运行 `swift test --package-path native` 并通过**。
- **200% 浏览器菜单缩放与原生 `pageZoom`**：**NOT_RUN**；640 CSS px 只是 reflow，root CSS zoom harness 只是 simulation。
- **native GUI 的独立复现**：native 三条路径由 Sol 实机以本机 Vision OCR 判读通过，但 QA 无 GUI 能力、未独立复现；如需第三方独立验证 native 交互，必须另行授权（且需要 macOS 辅助功能权限或人工点击配合）。
- **真实门**：真实 provider / 飞书 OAuth / Keychain 生命周期 / 真实业务材料 / 已安装 App / Developer ID 与公证 / 五日 / 双机 / 生产与发布，全部仍是各自独立的未测门，需要用户按准备卡单独授权。**D 门的 PASS 不含这些。**

## 保留的产物与工作树（未经授权不删）

- 候选：`876008e`（初次，`frontend-d-final`）、`96fdf4d`（`frontend-d-build-repair2`）、**`e8e1dba`（最终，`frontend-d-build-repair3`）**；主仓库 `.local/internal-builds/main-bce8843` 亦保留。
- QA checkout：`frontend-d-qa-initial`、`frontend-d-qa-repair1`、`frontend-d-qa-repair1-parent`、`frontend-d-qa-repair2`、`frontend-d-qa-repair2-parent`、`frontend-d-qa-repair3`（+parent）。
- 构建 worktree：`frontend-d-build-repair2`、`frontend-d-build-repair3`。
- 所有原始证据留在各自 checkout 的 ignored `.local/qa|dev/` 下；tracked 文档只放脱敏摘要与 SHA-256 索引。

## 边界（对所有后续角色）

- 不触碰真实 provider / OAuth / Feishu / Keychain、用户真实资料、真实 App Support、已安装 App、付费、production、push 到 main、删 branch/worktree。合并 main 需用户批准。
- QA 在独立 worktree 取证，不改产品源码与 tracked tests。
- 失败不得靠删测试或降低验收门收口；自动检查通过不等于阶段通过。
- 候选构建流程与安全约束（LaunchServices `open -n --env`、canonical TMPDIR child profile、`SUMMIT_OFFLINE_GUARD_ACTIVE=1`、端口 18793 预检、token 不落盘、不覆盖旧候选）见历史交接 [history/2026-10-15-NEXT-FRONTEND-D-REPAIR1.md](2026-10-15-NEXT-FRONTEND-D-REPAIR1.md)。
- `src/summit_everything/domain/content.py` 仍是内容指纹与检索资格的唯一基准；本轮未改内容信任门。
