# PR #21 合并前仓库清理 · Sol 最终门判断（2026-10-16）

- **判定对象**：分支 `codex/frontend-ux-20261015` 上的 2026-10-15/16 仓库清理（C0→C7c）。
- **受测产品 SHA**：`e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374`（前端 D 最终固定产品 SHA）。
- **独立 QA 受测 SHA**：`7a448c39092b81d0afcb15ce4dc57d91faaa7e5e`；QA 报告
  [2026-10-15-PRE-PR21-CLEANUP-QA.md](2026-10-15-PRE-PR21-CLEANUP-QA.md)（QA checkout 独立建立后已删除）。
- **Developer 报告**：[2026-10-15-PRE-PR21-CLEANUP-DEV.md](2026-10-15-PRE-PR21-CLEANUP-DEV.md)；计划
  [2026-10-15-PRE-PR21-CLEANUP-PLAN.md](../../handoff/2026-10-15-PRE-PR21-CLEANUP-PLAN.md)。
- **本提交即清理后的最终 tip**。其 push 触发的真实 CI run 由 Sol 在交付回报中给出；为避免
  「改文档 → 又触发 run」的循环，**运行结论不回写本文件**（该决定沿用 C6 证据页的既有做法）。
- 本判断基于：逐片提交的真实 diff、Sol **自己执行**的退出码与计数、Sol 在删除**之前**完成的归档
  全量源比对、QA 独立 checkout 的复验报告、以及真实远端 CI run 的逐步结论。

## 判定

| 范围 | 判定 |
|---|---|
| C0 计划落盘 | **PASS**（`8973b5a`，只新增计划文件） |
| C1 文档事实收敛 | **PASS**（`9a9aba8`；索引缺口 0/119，自撰文档失效链接 8→7） |
| C2 证据归档与索引 | **PASS**（`207b8f9`；19 目录 / 1679 条目 / 395 原件 / 凭据命中 0） |
| C3 孤儿与冗余 | **PASS**（`9d6e097`；两件先归档后删，`tasks/*` 迁历史，`/tmp` 白名单） |
| C4 分支清退 | **PASS**（`32aa10c`；本地 4 + 远端 2，全部 `--is-ancestor origin/main` = 0） |
| C5 worktree 清退 | **PASS**（`32aa10c`；19 个先归档后删，`worktree list` = 2） |
| C5.5 范围外残留清理（用户另授权） | **PASS**（55 条，`56 → 1`，`1.1 G → 804 M`） |
| C6 CI 显示名 + 真实 CI | **PASS**（`af65f04` 恰好 1 行；run `38831085564` success） |
| C7 交接与清理报告 | **PASS**（`412e0fd`；NEXT-STAGE + DEV 报告） |
| C7b/C7c 收口修正 | **PASS**（`7a448c3`、`ad35839`；索引 0/121，全仓 broken 23 = 7+16+0） |
| 独立 QA（固定 `7a448c3`） | **PASS**（A–H 全项；与实现者声明不符 **0 项**） |
| **本轮清理 —— 限「仓库整理」范围** | **PASS，可随 PR #21 一起合入（待用户批准）** |
| 真实服务 / 凭据 / 安装 / 公证 / 五日 / 双机 / 发布 / `pageZoom` / native GUI 独立复现 | **NOT_RUN**（各自独立门，未包含在本 PASS 内） |

## 硬验收不变量（逐条证据）

| # | 不变量 | 实测 | 判定 |
|---|---|---|---|
| 1 | 产品面逐字节冻结 | `git diff e8e1dba <tip> -- src 'web/src' ':(exclude)web/src/*.test.ts' ':(exclude)web/src/*.test.tsx' ':(exclude)web/src/**/*.test.ts' ':(exclude)web/src/**/*.test.tsx' web/package.json web/package-lock.json pyproject.toml uv.lock native` → **无输出，exit 0**（Sol 与 QA 各自独立复现） | PASS |
| 2 | 前端指纹不变 | `fingerprint_web_dist('web/dist')` = `784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0`（Sol 与 QA 各一次） | PASS |
| 3 | 自动检查不低于基线 | pytest **692**；vitest **222 / 26 files / 0 todo**；`test:e2e` **2**；`test:e2e:integration` **1**；typecheck / lint（**2** warning / 0 error）/ build；ruff check / ruff format / mypy（47 files）/ `uv lock --check` / `uv build`；`api:types` 后 `git diff --exit-code -- web/src/api/generated.ts` → 全 **exit 0** | PASS |
| 4 | 链接与索引自洽 | 自撰/修改文档失效链接 **0**；全仓 broken **23 = 7（历史正文绝对路径快照）+ 16（逐字归档副本内部，哈希固定不可改）+ 0**；`docs/quality/reports/` 直接层索引缺口 **0/121** | PASS |
| 5 | 删除可追溯 | 每个被删文件 / 分支 / worktree 在 [DELETIONS.md](evidence/2026-10-15-worktree-archive/DELETIONS.md) 有「判定理由 + 归档索引 + 验证方式」；QA 随机抽查 5/5 齐备 | PASS |
| 6 | CI 绿 | run [`38831085564`](https://github.com/yifeng93/SummitEverything/actions/runs/38831085564)（`headSha=af65f04`）completed / success，四步骤全 success；**最终 tip 的 run 见交付回报** | PASS |

## Sol 的核对动作

| 核对项 | 结果 |
|---|---|
| 受测 SHA 可解析、产品树自 `e8e1dba` 未变 | ✅ 冻结面 pathspec 在每一片后各跑一次，均空 / exit 0 |
| 归档完整性（**删除前**） | ✅ 1671 条 MANIFEST 逐条重算对源文件：**0 缺失 / 0 不符**；395 个复制件对源：**0 不一致**（Sol 在 C5 之前执行） |
| 归档完整性（**删除后**） | ✅ 只能自校验：395 ok / 0 mismatch / 1276 absent（未复制条目）；源已删，此限制已在归档 README 与 QA 报告双处声明 |
| 归档候选凭据扫描 | ✅ 395 个候选 + 440 个新增/修改 tracked 文件：严格形态命中 **0**；唯一宽口径命中是 Swift XCTest 用例名与正则定义本身 |
| 三件候选 DMG | ✅ `e8e1dba` = `5f9805eb…bb2b`（与 D 文档记载一致）、`876008e` = `8bd387ba…8fa9`、`96fdf4d` = `bdbed422…3765`；`3f6eaa4` = `554b7ab3…59d8` |
| `.app` 目录树摘要口径 | ✅ 先对文档已记载的 `3f6eaa4` 复算，得 `1e58574e…f4eb` **与文档逐字一致**，才采用同一算法处理其余 7 个 |
| worktree 删除前状态 | ✅ 19/19 `git status --porcelain` 为空（无未提交/未跟踪） |
| 分支删除 | ✅ 6/6 `git merge-base --is-ancestor <b> origin/main` = 0；`git branch -d`（非 `-D`）失败即会中止 |
| 主仓库未被波及 | ✅ `main` 仍 `e84e9e5`、clean；`.local/internal-builds/{3f6eaa4,internal-f40bc39,m42-419bb86,main-bce8843}` 完好 |
| QA 是否独立 | ✅ QA 自建 `qa-cleanup-verify` 独立 checkout、自装依赖、**自写** linkcheck 与 manifest 校验脚本；未复用实现者脚本 |
| QA 是否有判别力 | ✅ A2 判别力对照非空（4 文件 / 175 行）；A3 反例 = 2；H3 计数对照 26→26 / 53→53 |
| 是否 push / merge / 删 branch 或 worktree（超出授权） | ✅ 远端删除与 worktree 删除均为**用户明确授权**；**未 merge**、未 push 到 main |
| 证据是否含 token / 真实数据 | ✅ 严格凭据形态命中 0；归档不含 `.app`/`.dmg` 二进制 |

## 缺陷与 Nit 台账

| 编号 | 级别 | 内容 | 处置 |
|---|---|---|---|
| N-1 | Nit | `gh pr checks 21` 只显示最新 check，易被误读为 `af65f04` 那次 run | DEV 报告与 QA 报告均已写明 run id 与归属 |
| N-2 | Nit | `DELETIONS.md` §C4.4 远端快照 `e76244e` 是时点值 | `ad35839` 已在同节追加「后续变化」补记，原快照保留不改 |
| N-3 | Nit | 旧口径「相对链接失效 7」不再等于全仓总数 | `ad35839` 在 DEV 报告 §9 写明全仓 23 与两类构成，并声明两种口径不可混用 |
| N-4 | Nit | 默认 rename 检测下 `--diff-filter=D` 为空，删除审计会误判 | `ad35839` 在 DELETIONS.md §6 追加 `--no-renames` 审计提示 |
| N-5 | Nit | QA 报告 §A 的 A3 命令把 `e8e1dba` 误写成 `e8e1ba` | **不改写 QA 报告原文**（QA 记录保持原样）；Sol 用正确 SHA 独立复跑得 `2`，与报告一致，结论不受影响 |
| G-1 | 覆盖缺口 | `frontend-d-build/MANIFEST.sha256` 为 0 字节（该 worktree 的 `.local` 本就不存在） | 已知例外且已登记；删除后本机无法再独立证实，QA 已列为覆盖缺口而非 FAIL |
| C-1 | 过程偏差 | 首轮 Luna 停滞无产出；C6/C7 两个 Luna 曾并发写同一分支 | 已中断停滞者与并发者；未污染工作树（每步 `git status` 为空）；C7b/C7c 已把所有过期表述收口 |
| C-2 | 口径更正 | 「docs-only 提交不触发 CI」的假设**被实测推翻**：`pull_request` 的 `paths` 按 PR 相对 base 的整体 diff 判定 | 已由 C6 证据页 §5 记录，并据此让最终 tip 的 push 直接产出真实 run |

## 本 PASS 明确不覆盖

真实 provider / 飞书 OAuth / Keychain 生命周期 / 真实业务材料 / 已安装 App / Developer ID 与公证 /
五日 / 双机 / 生产与发布；200% 浏览器菜单缩放与原生 `pageZoom`；native GUI 的**独立**复现
（D 门三条 native 路径仍是 Sol 实机 + 本机 Vision OCR 判读，QA 未独立复现）；产品功能面本身
（属 `e8e1dba` 的既有 QA 与 Sol 门，不由本轮清理重新判定）；归档副本的**语义内容**
（只验证字节与索引自洽，未逐份复核 395 个归档件的业务正确性）。

## 合入判断

- 本轮清理**不新增产品能力、不改产品面、不降低任何验收门、不删测试换绿**；
  硬不变量 1–6 全部有可复现证据。
- **Sol 判定：本轮清理可以随 PR #21 一起合入 main。**
- **合并动作本身仍需用户明确批准。Sol 未 merge，也不会 merge；也未 push 到 main。**

## 仍需用户决定的事项

1. **是否合并 PR #21**（AGENTS：重要里程碑合并需用户批准）。
2. **合并后的收尾顺序**（见 [NEXT-STAGE-2026-10-16.md](../../handoff/NEXT-STAGE-2026-10-16.md) §2）：
   核对 main 产品树、记录 merge commit 与 CI run、并把 `NEXT-AFTER-FRONTEND-D.md` 移入 history。
3. **D 候选二进制已按用户决定删除**：`e8e1dba`/`876008e`/`96fdf4d` 的 `.app`/`.dmg` 本机不再保留，
   仅存 SHA-256 与 `build-info.json`；日后如需复验必须重建。
4. **下一个阶段的方向选择**：D-3 契约补全 / 前端剩余守卫与页面切片 / 工作包 B-C 真实授权准备 /
   native GUI 独立复现授权（见 NEXT-STAGE §3）。
