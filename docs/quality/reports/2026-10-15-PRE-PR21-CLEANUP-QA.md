# PR #21 合并前仓库清理 · 独立 QA 报告（Luna · High，2026-10-15）

- **QA 身份**：全新独立 QA **Luna（High）**，**未参与**本轮清理的任何实现。
- **受测固定源码 SHA**：`7a448c39092b81d0afcb15ce4dc57d91faaa7e5e`（`git rev-parse 7a448c3`；分支
  `codex/frontend-ux-20261015`；commit 标题 `docs(cleanup): fix the deleted-path index links and complete the report index`）。
- **产品受测基线 SHA**：`e8e1dba0c1fed9a5f02babcc29d5f67dc1d374`（前端 D 最终固定产品 SHA）。
- **QA 独立 checkout**：`/Users/yifengstudio/.codex/worktrees/qa-cleanup-verify`，
  由 `git worktree add --detach … 7a448c3` 建立，`git rev-parse HEAD` = 上述完整 SHA；
  验收完成后已按交付要求 `git worktree remove --force` + `git worktree prune` 删除。
- **依赖安装**：`uv sync --locked --group dev` exit 0；`npm --prefix web ci` exit 0（226 packages，0 vulnerabilities）。
- **日期**：2026-10-15（本地时间 2026-10-16 上午实测）。
- **证据**：[evidence/2026-10-15-cleanup-qa/](evidence/2026-10-15-cleanup-qa/README.md)（脱敏摘要）+ QA checkout 的
  `.local/qa/cleanup-verify/`（大日志，Git 忽略，随 QA worktree 删除）。
- **QA 边界**：未改产品源码、未改任何已有 tracked 测试、未 push / merge / rebase、未删任何分支，
  未删任何他人 worktree（只删了我自己的 QA checkout）。唯一写入主工作目录的内容是本报告、其证据目录
  与 `docs/quality/reports/README.md` 的一行索引。

---

## 判定总表

| 项 | 内容 | 判定 |
|---|---|---|
| A | 产品面冻结 + 判别力对照 | **PASS**（A1 空 / A2 非空 175 行 / A3 = 2） |
| B | 测试与自动检查计数不降（13 项） | **PASS**（13/13 退出码 0，计数全部达标） |
| C | 前端指纹 | **PASS**（`784ae1ee…28dbf0` 逐字符一致） |
| D | 删除可追溯性与「没有偷偷删测试」 | **PASS**（D1–D6 全部满足） |
| E | 归档完整性与凭据 | **PASS**（ok=395 / mismatch=0 / 1679；严格凭据命中 0） |
| F | 链接与索引自洽 | **PASS**（broken = 7 + 16 + 0 = 23；索引缺口 0） |
| G | 真实 CI | **PASS**（run 38831085564 = `af65f04` success，四步骤 success） |
| H | 对抗性检查（3 项） | **PASS**（门非空洞；归档循环性已声明且有独立信任锚；无删测试换绿） |
| — | 计数下降 / 门变软 / 不可追溯删除 | **未发现**（0 项） |

**未发现任何与实现者声明不符之处；未发现需要判 FAIL 的缺陷。** 发现的 4 条 Nit 与 1 条覆盖缺口见 §9、§10。

---

## A · 产品面冻结（含判别力对照）

`e8e1dba..7a448c3` 在排除测试文件后的产品路径（`src`、`web/src`（排除 `*.test.ts(x)`）、
`web/package.json`、`web/package-lock.json`、`pyproject.toml`、`uv.lock`、`native`）上：

| 检查 | 命令 | 实测 | 退出码 | 判定 |
|---|---|---|---|---|
| A1 | `git diff e8e1dba 7a448c3 -- <产品 pathspec>` | **无输出**（空 diff） | 0 | PASS |
| A2 | `git diff faa1edd e8e1dba -- <同一 pathspec> --stat` | **非空**：4 files changed, 55 insertions(+), 21 deletions(-)；diff 正文 **175** 行 | 0 | PASS |
| A3 | `git diff faa1edd e8e1ba --name-only -- web/src \| grep -c 'test\.tsx$'` | **2** | 0 | PASS |

A2 命中的 4 个文件（证明该门能看见真实产品改动，不是空洞的）：
`src/summit_everything/local/first_use_progress.py`、`web/src/App.tsx`、`web/src/api/generated.ts`、
`web/src/components/WorkspaceGate.tsx`。

A3 = 2 证明 `:(exclude)` 确实在做功 —— 若 exclude 写错，A1 会因测试文件差异而变非空。

**结论：产品受测基线 `e8e1dba` 在受测区间内零改动，A1 的空是真空 → PASS。**

---

## B · 测试与自动检查计数（13 项，全部真实退出码）

在 QA checkout 实测；逐项详情见 [B-and-C-checks.txt](evidence/2026-10-15-cleanup-qa/B-and-C-checks.txt)。

| # | 命令 | 期望 | 实测 | 退出码 | 判定 |
|---|---|---|---|---|---|
| B1 | `PYTHONPATH=$PWD/scripts/offline_guard:$PWD/src uv run pytest -q` | 692 passed | `692 passed, 1 warning in 81.26s` | 0 | PASS |
| B2 | `npm --prefix web test -- --run` | 222 / 26 files / 0 todo | `Test Files 26 passed (26)`、`Tests 222 passed (222)`，无 todo/skip 行 | 0 | PASS |
| B3 | `npm --prefix web run test:e2e` | 2 passed | `2 passed (12.6s)` | 0 | PASS |
| B4 | `npm --prefix web run test:e2e:integration` | 1 passed | `1 passed (3.5s)` | 0 | PASS |
| B5 | `npm --prefix web run typecheck` | 0 | 无输出 | 0 | PASS |
| B6 | `npm --prefix web run lint` | 0，恰好 2 warning | `Found 2 warnings and 0 errors.` / `Finished in 40ms on 73 files` | 0 | PASS |
| B7 | `npm --prefix web run build` | 0 | `✓ built in 241ms` | 0 | PASS |
| B8 | `uv run ruff check src tests` | 0 | `All checks passed!` | 0 | PASS |
| B9 | `uv run ruff format --check src tests` | 0 | `100 files already formatted` | 0 | PASS |
| B10 | `uv run mypy src` | 0 | `Success: no issues found in 47 source files` | 0 | PASS |
| B11 | `uv lock --check` | 0 | `Resolved 48 packages in 3ms` | 0 | PASS |
| B12 | `uv build` | 0 | sdist + wheel 均 built | 0 | PASS |
| B13 | `npm --prefix web run api:types && git diff --exit-code -- web/src/api/generated.ts` | 0 | 再生成 exit 0；`git diff` 无输出 | 0 | PASS |

**附带核查**：`web/openapi.json` 亦为 tracked 文件；再生成后 `git diff` 同样无输出，
命令结束后 `git status --porcelain` 为空。**B 全项 PASS，无任何计数低于基线。**

---

## C · 前端指纹

```sh
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python -c \
  "from summit_everything.release import fingerprint_web_dist as f; print(f('web/dist'))"
```

在 B7 的 `npm run build` 产物上实测输出（exit 0）：

```
784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0
```

与期望值**逐字符一致 → PASS**。

---

## D · 删除的可追溯性与「没有偷偷删测试」

详情见 [D-E-F-H-details.md](evidence/2026-10-15-cleanup-qa/D-E-F-H-details.md) §D。

| # | 检查 | 实测 | 判定 |
|---|---|---|---|
| D1 | `web/e2e/first-use-real.spec.ts`、`scripts/build_macos_app.sh` 已不存在 | `git ls-files` 两者**无输出**；`ls` 两者均 `No such file or directory` | PASS |
| D2 | 删除理由 + 归档件 SHA-256 一致 | `DELETIONS.md` §3 两行（含判定理由 / 无引用证据 / 归档索引）；QA 重算 `first-use-real.spec.ts` = `0592629563…a656fc3`、`build_macos_app.sh` = `1983dbf083…312c2a`，与记录一致；`shasum -a 256 -c MANIFEST.sha256` = 3×OK / exit 0 | PASS |
| D3 | 删除该 spec 不降低覆盖 | 4 个 `playwright*.config.ts` 的 `testMatch` 命中 5 个 spec，**无一条命中 `first-use-real.spec.ts`**；`--list` 实测 e2e = 2 tests/2 files、integration = 1 test/1 file，两份清单中该文件名命中 **0 / 0** | PASS |
| D4 | 随机抽查 5 项 | 种子 20261016 从 19 个池中抽得 `frontend-a-qa-initial`、`frontend-d-qa-repair3`、`m41-qa-b9321d6`、`m41-internal-app`、`frontend-b-qa-repair1`；**5/5** 均具备「判定理由 + 归档索引 + 验证方式」，归档目录均实际存在且 `MANIFEST` 非空；另抽查 2 个被删分支，其 commit 对象仍在且 `--is-ancestor origin/main` = 0 | PASS |
| D5 | 分支收敛 | 本地 `git branch` = `main` + `codex/frontend-ux-20261015`（QA checkout 为 detached）；`git ls-remote --heads origin` = 仅 `refs/heads/main` + `refs/heads/codex/frontend-ux-20261015` | PASS |
| D6 | worktree 收敛 | `git worktree list` = **3** 条：主仓库(main)、`frontend-ux-20261015`、QA checkout 自身 | PASS |

---

## E · 归档完整性与凭据

详情见 [D-E-F-H-details.md](evidence/2026-10-15-cleanup-qa/D-E-F-H-details.md) §E 与
[E-manifest-selfcheck.txt](evidence/2026-10-15-cleanup-qa/E-manifest-selfcheck.txt)。

1. **无二进制**：`git ls-files 'docs/quality/reports/evidence/2026-10-15-worktree-archive/**'` 共 **418** 个
   tracked 文件，其中 `.app` / `.dmg` = **0**；区间内新增路径与 `7a448c3` 全树扫描 `.(app|dmg)$` 亦为 0 → **PASS**。
2. **MANIFEST 自校验**：QA 自写脚本对 19 个目录逐条重算
   **`file_lines=1671，ok=395，mismatch=0，absent=1276，TREE=8`**，
   总条目 **1679 = 1671 + 8**，与期望完全一致 → **PASS**。
   `absent=1276` 属设计内（复制规则只收 `*.md`/`*.sha256`/名称含 `manifest|command-results|evidence` 的
   `*.json`/`*.log`/`*.txt` 且各有体积上限；`.dmg`、`.app`、超限日志、全部截图 PNG 只进 MANIFEST）。
   **限制**：源 worktree 已在 C5 删除，本节**只能自校验**（归档字节 == 同目录 MANIFEST 记录），
   不能由自身证明等于当时源目录的字节。
3. **凭据扫描**：扫描面 = `e8e1dba..7a448c3` 全部新增/修改 tracked 文件 = **440** 个。
   **严格形态扫描命中 0**（`Bearer\s+\S{20,}`、`sk-\w{20,}`、`gho_\w{20,}`、`ghp_\w{20,}`、
   `SUMMIT_SESSION_TOKEN` / `app_secret` / `api_key` 的赋值形态、`BEGIN … PRIVATE KEY`）→ **PASS**。
   宽口径子串扫描命中 64 行，**逐条均为误报**：`Bearer ${token}` 源码/日志片段 ×12、
   `gho_`/`ghp_` 的**正则定义本身**（`generate-manifest.py`、归档 `README.md`）与类别说明、
   `tasks/`、`ask-320-dark.png` 之类**路径子串**、以及合成测试标记 `sk-QA-LEAK` / `sk-QA-R2-LEAK`
   与其注入断言输出。**无真实凭据。**

---

## F · 链接与索引自洽

QA **未复用**实现者的 `/tmp/linkcheck.py`（已随 `/tmp` 清理不可得），而是自写
[linkcheck.py](evidence/2026-10-15-cleanup-qa/linkcheck.py)（口径写在脚本内：340 个 tracked `*.md`；
行内链接 + 引用式定义；跳过 `http(s)/mailto/tel/data/ftp` 与纯锚点；其余按相对路径解析，不存在即 broken）。

**TOTAL broken = 23**，分解与期望**完全一致**：

| 类别 | 期望 | 实测 |
|---|---|---|
| 历史报告正文里的 `/Users/…` 绝对路径快照 | 7 | **7**（`2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md` ×3、`2026-10-15-FRONTEND-A-INITIAL/QA-REPORT.md` ×4） |
| `evidence/2026-10-15-worktree-archive/` 下被 MANIFEST 哈希固定的逐字归档副本内部 | 16 | **16**（`frontend-a-qa-initial/…/QA-REPORT.md` ×4、`frontend-b-qa-initial/…/QA-REPORT.md` ×7、`frontend-d-qa-initial/…/QA-REPORT.md` ×5） |
| 其它（本轮自撰/修改文档自身） | **0** | **0** |

「其它 0」的独立复核命令：`grep '^BROKEN' … | grep -v '/Users/' | grep -vc '2026-10-15-worktree-archive/'` = **0**。

**报告索引**：`docs/quality/reports/` 直接层 `.md`（不含 `README.md` 自身）= **120**；
逐个反查「未出现在 `README.md` 里」= **0** → **PASS**。
（演进与 DEV 报告一致：C1 118/缺口 0 → C6 后 119/缺口 1 → `7a448c3` 120/缺口 **0**。
本次 QA 新增的报告由 QA 自己补进索引，补后复测 **121**/缺口 **0**；同理，把 QA 新增的 5 个 `.md`
用 `git add -N` 纳入扫描面后，链接检查仍为 **broken = 23**，其中 QA 自撰文档贡献 **0** 条。）

---

## G · 真实 CI

详情见 [G-ci.md](evidence/2026-10-15-cleanup-qa/G-ci.md)。

- `gh run list --branch codex/frontend-ux-20261015 --limit 8`（7 条）实测：
  **run `38831085564` 的 `headSha` = `af65f049a12caebbcb932a86e610282702e1ffc3`（= `af65f04`，清理后 tip），
  `conclusion = success`**。
- `gh run view 38831085564 --json headSha,status,conclusion,jobs`：单一 job `offline-arm64` = success，
  其中四个步骤 **`Guarded Python checks` / `Web checks and API types` / `Native upload policy tests` /
  `Build and verify internal App and DMG` 全部 success**。（口径确认：这四项在工作流里是 **steps**，
  不是四个 job；job 只有 `offline-arm64` 一个。）
- 该 PR 上后续 run 一并列出：`38831643643` @ `68c3639` = success；`38832106964` @ `ebb6b6f` = success。
  另见更早的 `38756944004` @ `e8e1dba` = **failure**（仅 DMG 步骤，`hdiutil: create failed - Resource busy`，
  DEV 报告与 PROGRESS 已如实记录，非本轮隐藏）。
- `gh pr checks 21` 当前输出 1 条：`offline-arm64  pass  3m42s`，指向 run `38832106964`（即最新已 push 的
  `ebb6b6f`），**不是** `af65f04` 那次 run —— 与「PR 上任何 push 都会再次触发」一致。

**判定：PASS。**（注意边界：CI **从未在 `7a448c3` 上运行**，见 §10。）

---

## H · 对抗性检查

### H1 · 门是否空洞 —— 非空洞

- A2 判别力对照在同一 pathspec 上产出 **4 文件 / 175 行**真实产品 diff → 门确实能看见产品改动。
- A3 反例对照 = **2**（不排除测试文件时可见 `web/src` 下 2 个 `*.test.tsx`）→ `exclude` 确实在做功。
- **结论：A1 的空是真空。**

### H2 · 归档是否自证循环 —— 部分是，已定位并补强信任锚

- **局限成立且必须声明**：19 个 worktree 的源目录已在 C5 删除，`git worktree list` 只剩 3 条（含 QA 自己），
  故 E2 的 395 条**只能自校验**。
- **「删除前」源比对记录确实存在**：`DELETIONS.md` §6「归档副本与源文件逐字节抽样复核（16/16 一致）」
  与 `2026-10-15-worktree-archive/README.md` §6（第 112–115 行），逐条给出复核文件、字节、
  SHA-256、结论与源绝对路径。
- **信任锚（QA 独立补强）**：C3 的两个被删文件在 Git 对象库中仍有原件 blob，QA 实测
  `git rev-parse e8e1dba:web/e2e/first-use-real.spec.ts` == `git rev-parse 7a448c3:<归档路径>` ==
  `9e41cd80b467147a37f69baca72db0166757fb50`（`git diff` 同时报 **R100**），
  `git cat-file blob` 的 SHA-256 = `0592629563…a656fc3`；`scripts/build_macos_app.sh` 同理
  （blob `26e6a8bb…`，R100，SHA-256 `1983dbf0…`）。被删分支的 6 个 SHA 亦仍是对象库内 commit 且
  `--is-ancestor origin/main` = 0。**即这两项「删除前 == 归档后」今天仍可被 Git 独立复证。**
- **剩余风险（如实）**：19 个 worktree 的 1671 个文件条目中，仅 16 条有可读的源件比对记录
  （抽样率 ≈ 16/395 ≈ 4.1%，非全量）；其余依赖 `DELETIONS.md`/`README.md` 写入者诚实性 +
  MANIFEST 与仓库一同被 Git 提交固化。**这是有限但可接受的信任锚。**

### H3 · 计数是否靠删测试换绿 —— 否

| 计数 | `e8e1dba` | `7a448c3` | 差 |
|---|---|---|---|
| `web/**/*.test.ts(x)` | 26 | 26 | 0 |
| `web/e2e/*.spec.ts` | 6 | 5 | −1（**仅** `first-use-real.spec.ts`） |
| `tests/**/*.py` | 53 | 53 | 0 |

`git diff --no-renames --diff-filter=D e8e1dba 7a448c3` 的全部删除只有 5 条：
`docs/handoff/NEXT-FRONTEND-D-REPAIR1.md`、`scripts/build_macos_app.sh`、`tasks/plan.md`、
`tasks/todo.md`、`web/e2e/first-use-real.spec.ts` —— 其中 4 条在默认 rename 检测下是
**R085/R087/R089/R100 的移动**（`tasks/*` 与 `NEXT-*` 移入 `docs/handoff/history/`，
两个孤儿件 **R100 逐字节**移入归档）。**除该 spec 外没有任何测试文件被删**；
该 spec 又**未被任何 `testMatch` 命中**，且三项计数（vitest 222 / e2e 2 / integration 1）
与 pytest 692 **全部不降**。**不存在靠删测试换绿。**

---

## 与实现者声明不符之处 / 新缺陷

**与声明不符：0 项。** 逐条 Nit 如下（均不影响判定）：

1. **Nit · `gh pr checks 21` 的归属易误读**：其输出只有 1 条 `offline-arm64`，属于 run `38832106964`
   （`ebb6b6f`），**不是** `af65f04` 的 `38831085564`。若只跑这一步而不看 run list，会得到
   「PR checks 对应 af65f04」的错误印象。建议在 DEV 报告中显式写 run id。
2. **Nit · `DELETIONS.md` §C4.4 的远端快照已过期**：该节记 `codex/frontend-ux-20261015` 远端为
   `e76244e`，QA 实测现为 `ebb6b6f`。这是后续 push 的正常结果，不是错误，但读者需知道该行是时点快照。
3. **Nit · 归档引入 16 条新增 broken 链接**：`evidence/2026-10-15-worktree-archive/` 内逐字归档副本
   使全仓 broken 从 7 升到 23。这是「逐字归档」的必然代价且已被 DELETIONS/README 说明，
   但报告口径应写明「相对链接失效 7」这一旧数字**已不再等于全仓总数**，否则易被误引。
4. **Nit · 区间 diff 的删除集在默认 rename 检测下不可见**：`git diff --diff-filter=D e8e1dba 7a448c3`
   （不带 `--no-renames`）输出为**空**，会让人误以为「本轮没有任何删除」。实际需加 `--no-renames`
   才看到 5 条删除，或在默认口径下看 4 条 R 行 + 1 条 D。审计者若用错口径会得出相反结论。

## 覆盖缺口（已声明但本机不可再验证）

5. **`frontend-d-build` 的 `MANIFEST.sha256` 为 0 字节**：该 worktree（HEAD `944634c`）的 `.local`
   按 `DELETIONS.md` §1 / 归档 `README.md` §2 记载「本机已无 `.local` 证据」，故**无任何归档副本**。
   这是**已登记的已知例外**，但删除后**无法再由本机独立验证**该声明为真 —— 若当时源目录其实存在
   而被跳过，今天不会有任何证据暴露。QA 将其列为**覆盖缺口**（不是 FAIL：口径公开、可追溯、
   且该 worktree 只是中间构建）。

---

## 本 PASS 明确不覆盖

1. **只对 `7a448c3` 有效**：不覆盖 `412e0fd`、`ebb6b6f`、`68c3639`、`af65f04`、`e8e1dba` 等其它 SHA。
2. **CI 未在 `7a448c3` 上运行**：该提交未 push（远端 tip = `ebb6b6f`），`gh run` 里**没有** `7a448c3` 的 run；
   G 的 success 全部来自 `af65f04` 及更早/平行 SHA。**「清理后 tip 的 CI 绿」不等于「7a448c3 的 CI 绿」。**
3. **归档 MANIFEST 只能自校验**：19 个源 worktree 已删，395 条 ok 只证明「归档字节 == 同目录 MANIFEST」，
   不证明「== 当时源目录字节」；仅 §6 的 16 条抽样 + C3 两件的 Git blob（R100）可证。
   `frontend-d-build` 无归档副本、无可验证内容。
4. **凭据扫描只覆盖形态与已知类别**：8 类正则 + 440 个新增/修改 tracked 文件；
   不覆盖未入库文件、Git 历史深处的旧 blob、二进制内部的非 UTF-8 载荷，也不等于密钥泄露审计。
5. **未做任何真实外部动作**：未 push / merge / rebase / 建 tag；未跑真实飞书、真实模型、Keychain、
   真实 DMG 安装、五日或双机场景；未改任何产品源码或已有 tracked 测试。
6. **未验证归档副本的"业务正确性"**：只验证了字节与索引自洽，未逐份复核 395 个归档件的语义内容。
7. **未验证 `/tmp` 侧记录的长期存续**：`DELETIONS.md` §5/§C5.5.6 引用的
   `/tmp/sol-worktrees-dir-before.txt` 等主机级快照不入库、可能已被 periodic cleaner 清理，
   QA 未（也无法）据其复证 55 条删除清单。
8. **未复核删除者本人的操作时序**：`git worktree remove` / `git branch -d` / `git push --delete`
   的实测输出来自 `DELETIONS.md` 的自述，QA 只复核了**结果状态**（分支/worktree/对象可达性）与
   可独立复算的部分，未重放其删除过程。
9. **未评估 PR #21 的产品功能正确性**：本报告只验收「清理」，不构成对前端 D 产品面的验收
   （那属于 `e8e1dba` 的既有 QA 报告）。

---

## 复现方式

```sh
cd /Users/yifengstudio/Documents/GitHub/SummitEverything
git worktree add --detach /Users/yifengstudio/.codex/worktrees/qa-cleanup-verify 7a448c3
cd /Users/yifengstudio/.codex/worktrees/qa-cleanup-verify
git rev-parse HEAD                      # 7a448c39092b81d0afcb15ce4dc57d91faaa7e5e
uv sync --locked --group dev && npm --prefix web ci
# A/B/C：见 docs/quality/reports/evidence/2026-10-15-cleanup-qa/A-product-freeze.txt 与 B-and-C-checks.txt
uv run python docs/quality/reports/evidence/2026-10-15-cleanup-qa/verify_manifests.py \
  docs/quality/reports/evidence/2026-10-15-worktree-archive      # E2
uv run python docs/quality/reports/evidence/2026-10-15-cleanup-qa/linkcheck.py .   # F
gh run list --branch codex/frontend-ux-20261015 --limit 8 --json databaseId,headSha,status,conclusion,event
gh run view 38831085564 --json headSha,status,conclusion,jobs
gh pr checks 21
```
