# 下一步：前端 D repair1 验收与候选

## 当前固定状态

- 产品工作树：`/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything`，分支 `codex/frontend-ux-20261015`。
- **repair1 产品源码固定 SHA：`faa1edd611a74dcdc26bff234de810bdf47761cb`**（父产品 SHA `876008e1d33420f57fb31772c76e471379e6b98d`），提交后产品 tree clean。该 SHA 之后的 docs/evidence 提交都不是受测产品 SHA。
- 里程碑 A `9c33a9d`、B repair1 `a0ccad8`、C `1b1efda` 均仅适用各自离线范围 PASS。
- D 初次 SHA `876008e` 经 fresh QA 判 **FAIL / P1**，脱敏报告见[初次 QA 归档](../quality/reports/2026-10-15-FRONTEND-D-QA-INITIAL.md)，原始证据仍在 `/Users/yifengstudio/.codex/worktrees/frontend-d-qa-initial/SummitEverything/.local/qa/frontend-d-initial/`（不得复制 trace、profile、token 或真实数据到 tracked 文档）。
- repair1 已实现并自测：见 [D repair1 DEV 报告](../quality/reports/2026-10-15-FRONTEND-D-DEV-REPAIR1.md)。**fresh QA 尚未完成；不声称 D PASS 或 P1 已关闭。**

Sol 负责计划、调度、gate 判断；实现交给 Developer，修复/实现固定 SHA 后再交**全新** QA 独立验收。串行修改，fresh QA 不修改实现和 tracked tests。最多两轮自动修复；重要里程碑 merge 仍需用户批准。

## repair1 做了什么

把首次配置进度从浏览器 `localStorage` 移到本机 backend：新增 profile + workspace 隔离的非秘密进度存储（原子写入、严格白名单 `step/completed/open`、非法与密钥形状字段拒绝），通过 typed API `GET/PUT /api/v1/first-use/progress` 读写（无记录 404 `first_use_progress_absent`，读写失败 503 `progress_unavailable`），OpenAPI 与浏览器类型同步。前端以后端为唯一真源，旧 localStorage 仅一次性迁移且迁移后不再双写。`App` 按本机记录决定落点：completed→今日；未完成且 open→原 step；明确关闭→不自动弹但设置可手动续接；无记录→新工作库从第 2 步开始；**不按「有凭据」猜测首配完成**，也不新增自动打开上次工作库。步骤变化、关闭与完成都必须等 durable write 成功，失败停在原步骤并可重试。

## 仍然缺的两件事

1. **fresh QA**：对固定产品 SHA `faa1edd611a74dcdc26bff234de810bdf47761cb` 在独立 worktree 黑盒复验，重点重演初次 P1 路径（完成首配 → 同 profile/workspace 重启 → 手动打开已有库 → 直接 Today），并独立核对 store 隔离/原子性/白名单、迁移仅一次、失败可见与重试、鉴权与错误码、OpenAPI 逐字节一致，以及真实退出码与计数。
2. **native 候选与同 profile 重启**：本轮按用户决定**没有**建包，所以原始 P1 被观察到的 native WKWebView 路径 **NOT_RUN**。D 门要覆盖这一条，需要用户另行授权建新候选。

## Native 候选流程（获授权后执行）

- 源码与文档分开提交；产品 tree clean 后记录新产品 SHA。用 Codex native `create_worktree` 创建 exact SHA 的新 managed build worktree，不能 shell git 绕注册；只将主 repo `.local/first-use/defaults.json` 的 LOCAL COPY 到隔离 worktree 对应 ignored 路径，不 cat/print/提交/外传内容。QA 用空/合成 defaults。
- 构建唯一新的 app/DMG 输出目录，强制 frontend rebuild；记录 source SHA、dirty=false、build ID、frontend/dependencies hash、DMG SHA。保留旧物件，不覆盖不删除：
  - D 初次候选 App：`/Users/yifengstudio/.codex/worktrees/frontend-d-final/SummitEverything/.local/dev/frontend-d-final/SummitEverything-D-876008e.app`
  - D 初次候选 DMG：`/Users/yifengstudio/.codex/worktrees/frontend-d-final/SummitEverything/.local/dev/frontend-d-final/SummitEverything-D-876008e.dmg`
  - build ID `20261015T132109Z-8a0917f72e08`；frontend `8a0917f72e0833727fa90a4f827e70be8835db6711eb9e24b167df16087fab62`；dependencies `cab274716d93a5485155114bd25f3a65722eede97c4487d11262d8b73728c7d7`；DMG `8bd387bac1c942da3640952da2b334ed53776f12dd04adf2f1eed343989d8fa9`。
  - 更早的 `.local/internal-builds/main-bce8843` 及所有 876 candidates/tree/raw artifacts 均保留原样。
- 新候选启动前重新 `lsof` 检查固定端口 18793；若被占用，识别占用者、不连接、不 kill，记录 BLOCKED。native/backend 必须在严格 canonical `NSTemporaryDirectory()` child profile 中启动，`SUMMIT_INTERNAL_TEST_PROFILE_ROOT` / `SUMMIT_PROFILE_ROOT` 与 `SUMMIT_OFFLINE_GUARD_ACTIVE=1` 均由真实进程 allowlist 检查；实际 PID、候选路径、manifest health identity、static root 200 核验通过后才能用 CUA 选 exact app。ps env 原文/token 不得打印或保存。通过 LaunchServices `open -n --env ...` 启动，不能直接执行二进制。完成 GUI 后只退出本轮启动 PID 并确认端口释放。
- Native same-profile 生命周期（完成 → quit → 同 profile 重启 → 手动 open existing → 直接 Today；未完成 step 3/4 → 重启 → open existing → 原 step；明确 close → 重启 → 不弹、设置可手动续接）以及 Fake 导入→审批→索引→问答→引用→Reader/目录闭环必须在新候选上真实执行；backend smoke 不能代替 WKWebView。
- 200% 浏览器 menu zoom 与 WKWebView 原生 `pageZoom` 仍为 **NOT_RUN**；640 CSS viewport 仅 reflow，独立 CSS zoom 2× harness 仅 simulation。截图只存 build `.local`。

## 边界（对所有角色）

- 不触碰真实 provider / OAuth / Feishu / Keychain、用户真实资料、真实 App Support、Desktop/test、已安装 App、付费、production、push、merge、删 branch/worktree。
- QA 在独立 worktree/checkout 中工作，可在 `.local/qa` 建立黑盒 harness 与验收记录；不改产品源码、不改已有 tracked tests、不移动被测 SHA。
- 自动检查通过不等于阶段通过；阶段证据、未测项与人工门分别记录。失败不得靠删测试或降低验收门收口。
- `src/summit_everything/domain/content.py` 仍是内容指纹与检索资格的唯一基准；repair1 未改内容信任门。
