# 2026-10-16 保留开发 worktree 的 `.local` 证据归档

日期：2026-10-16。执行：Sol。
归档对象：`/Users/yifengstudio/.codex/worktrees/frontend-ux-20261015/SummitEverything/.local`

## 0 · 为什么会有这份归档

该 worktree 是前端 UX 线 A→D 的开发 checkout（分支 `codex/frontend-ux-20261015`）。
PR #21 合入 main（merge commit `12280ec1893f8f526b9b73a84b98416545254f42`）后分支退役，
用户于 2026-10-16 同意删除该 worktree。

但它的 `.local/`（Git 忽略）里仍放着**被 tracked 文档直接引用的原始证据**——A/B/C/D 各轮的
harness、变异日志、视口矩阵截图、native OCR 工具与命令退出码。按用户 2026-10-15 定的规则
**「删 worktree 之前必须先归档证据；被 tracked 文档引用的原件不得静默消失」**，
先归档、后删除。

归档时的 worktree 身份：**detached HEAD `8ded0d9d276ce6170ce97f090ad1eff7d2679156`**
（= PR #21 被合并的 tip，其内容已全部进入 main 历史）。

## 1 · 口径

与 19 个历史 worktree 的归档（[../2026-10-15-worktree-archive/](../2026-10-15-worktree-archive/README.md)）
使用**同一套规则**，另加一项扩展：

| 项 | 规则 |
|---|---|
| `.venv/` | **排除**。本 worktree 的 `.local/dev/frontend-a/repair1/.venv` 约 135 MB，是虚拟环境，不承载证据 |
| 全量清单 | 其余**每个文件**都记 `sha256 + size + 相对路径` 进 `MANIFEST.sha256` |
| 复制入库（小原件） | `*.md` ≤512 KiB、`*.sha256` ≤512 KiB、名称含 `manifest`/`command-results`/`evidence` 的 `*.json` ≤512 KiB、`*.log` ≤256 KiB、`*.txt` ≤256 KiB |
| **复制入库（本目录扩展）** | 追加 `*.ts`/`*.tsx`/`*.js`/`*.mjs`/`*.cjs`/`*.py`/`*.swift`/`*.sh`/`*.css`/`*.html`/`*.patch`/`*.sql` ≤256 KiB ——因为 tracked 文档引用的 harness 与工具是这些小脚本，若只留哈希则原件仍会消失 |
| 二进制 / 大文件 | 只进 `MANIFEST.sha256`，**不复制**：774 张 `.png`（86.28 MB）、2 个 `.zip`、36 个 `.sqlite3`、6 个 `.jpg`、超限日志等 |

## 2 · 实测数字

| 项 | 值 |
|---|---|
| MANIFEST 条目 | **1347** |
| 清单覆盖字节 | **91.3 MB** |
| 复制入库原件 | **324 个 / 1.12 MB** |
| 凭据形态扫描（8 类正则） | **命中 0** |
| 排除内容 | `.local/dev/frontend-a/repair1/.venv`（虚拟环境） |

按类型（全部 1347 条）：

| 类型 | 个数 | 字节 |
|---|---|---|
| `.png` | 774 | 86.28 MB |
| `.zip` | 2 | 1.28 MB |
| `.log` | 261 | 0.91 MB |
| `.json` | 78 | 0.89 MB |
| `.sqlite3` | 36 | 0.86 MB |
| `.jpg` | 6 | 0.73 MB |
| `.sqlite3-wal` / `-shm` | 6 | 0.20 MB |
| `.md` | 19 | 0.06 MB |
| `.ts` / `.tsx` / `.cjs` | 10 | 0.08 MB |
| `.txt` | 12 | 0.03 MB |
| `.py` / `.swift` / `.patch` | 8 | 0.02 MB |
| `.exit` | 120 | 0.00 MB |
| `.lock` 等 | 23 | 0.00 MB |

按二级目录：`dev/frontend-d` 415 个 / 38.01 MB、`dev/frontend-a` 291 / 24.75 MB、
`dev/frontend-b` 184 / 11.09 MB、`dev/frontend-b-repair1` 91 / 7.77 MB、
`dev/frontend-c` 232 / 7.56 MB，其余零散。

## 3 · 被哪些 tracked 文档引用（引用映射）

| `.local` 子路径 | 引用它的 tracked 文档 |
|---|---|
| `dev/frontend-a/**` | [FRONTEND-A-DEV](../../2026-10-15-FRONTEND-A-DEV.md)、[FRONTEND-A-DEV-REPAIR1](../../2026-10-15-FRONTEND-A-DEV-REPAIR1.md)、[A-INITIAL/EVIDENCE-INDEX](../../2026-10-15-FRONTEND-A-INITIAL/EVIDENCE-INDEX.md)、`evidence/2026-10-15-frontend-a-dev/command-results.json`、`evidence/2026-10-15-frontend-a-repair1/{README,command-results,evidence-manifest}.json` |
| `dev/frontend-b/**`、`dev/frontend-b-repair1/**` | [FRONTEND-B-DEV](../../2026-10-15-FRONTEND-B-DEV.md)、`evidence/2026-10-15-frontend-b-dev/README.md` |
| `qa/frontend-b-repair1/**` | [FRONTEND-B-QA-REPAIR1](../../2026-10-15-FRONTEND-B-QA-REPAIR1.md)、`evidence/2026-10-15-frontend-b-repair1-qa/README.md`、`evidence/2026-10-15-frontend-b-repair1/{command-results.json,harness/*,logs/*}`、`evidence/2026-10-15-worktree-archive/frontend-b-qa-repair1/**` |
| `dev/frontend-c/**`（含 92 张视口矩阵截图） | [FRONTEND-C-DEV](../../2026-10-15-FRONTEND-C-DEV.md)、[FRONTEND-D-SOL-GATE-FINAL](../../2026-10-15-FRONTEND-D-SOL-GATE-FINAL.md) |
| `dev/frontend-d/mutation/**` | [FRONTEND-D-DEV](../../2026-10-15-FRONTEND-D-DEV.md)、`evidence/2026-10-15-frontend-d-dev/README.md` |
| `dev/frontend-d-repair1/**`、`dev/frontend-d-repair2/**`、`dev/frontend-d-repair3/**` | [FRONTEND-D-DEV-REPAIR1](../../2026-10-15-FRONTEND-D-DEV-REPAIR1.md)、[FRONTEND-D-DEV-REPAIR2](../../2026-10-15-FRONTEND-D-DEV-REPAIR2.md)、[FRONTEND-D-SOL-GATE-FINAL](../../2026-10-15-FRONTEND-D-SOL-GATE-FINAL.md)、`evidence/2026-10-15-worktree-archive/CANDIDATE-IDENTITY.md` |

（唯一以**绝对路径**形式指向本 worktree 的 tracked 文本是
`evidence/2026-10-15-frontend-b-repair1/logs/scope-harness-fixture-fail.log` 的两行堆栈。）

## 4 · 明确声明：哪些内容**没有**按字节保留

按用户 2026-10-15 批准的归档粒度，下列内容**只保留 SHA-256**，原件随 worktree 删除而消失：

- **774 张 PNG（86.28 MB）**，包括 C 轮 92 张全站视口矩阵截图、D 轮的 native 截图与 prod/dev 截图；
- 2 个 `.zip`、36 个 `.sqlite3`（及其 `-wal`/`-shm`）、6 个 `.jpg`；
- 超过体积上限的日志与文本。

这**不是**静默丢失：每个文件的路径、大小与 SHA-256 都在 `MANIFEST.sha256` 里，
「曾经存在且内容为某哈希」可被独立复核；只是内容本身不可再取。需要内容时只能按对应 SHA
重建或重跑。若要改为保留原图，需用户另行决定（本目录 2.0 MB ↔ 原图 86 MB）。

## 5 · 复核方式

```sh
cd <repo>
# 1) 清单自校验（对归档内已复制的文件）
python3 - <<'PY'
import hashlib
from pathlib import Path
A=Path('docs/quality/reports/evidence/2026-10-16-frontend-ux-local-archive')
ok=absent=bad=0
for line in (A/'MANIFEST.sha256').read_text().splitlines():
    h,s,rel=line.split(' ',2); p=A/rel
    if not p.exists(): absent+=1; continue
    d=hashlib.sha256(p.read_bytes()).hexdigest()
    ok+= d==h; bad+= d!=h
print(f"ok={ok} mismatch={bad} absent={absent}")
PY
# 2) 凭据形态再扫（期望 0）
# 3) 与 tracked 文档的引用对照见 §3
```

## 6 · 相关索引

- 19 个历史 worktree 的归档：[../2026-10-15-worktree-archive/README.md](../2026-10-15-worktree-archive/README.md)
- 删除可追溯主表：[../2026-10-15-worktree-archive/DELETIONS.md](../2026-10-15-worktree-archive/DELETIONS.md)
- 清理 Sol 门判断：[../../2026-10-16-PRE-PR21-CLEANUP-SOL-GATE.md](../../2026-10-16-PRE-PR21-CLEANUP-SOL-GATE.md)
