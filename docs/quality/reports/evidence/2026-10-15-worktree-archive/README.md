# 2026-10-15 worktree 证据归档（删除前全量 SHA-256 清单）

日期：2026-10-15。分片：C2 · 证据归档与索引。
生成器：[generate-manifest.py](generate-manifest.py)（本目录内，方法记录随提交入库）。
生成命令（2026-10-15 在本 worktree `codex/frontend-ux-20261015` 实测，退出码 0）：

```sh
python3 docs/quality/reports/evidence/2026-10-15-worktree-archive/generate-manifest.py \
  --out docs/quality/reports/evidence/2026-10-15-worktree-archive \
  --repo "$PWD"
```

## 1 · 目的与口径

### 为什么要归档

用户 2026-10-15 决定：只保留 `main` + `codex/frontend-ux-20261015`，其余 **19 个 worktree 将在 C5 删除**。
这 19 个 checkout 的 `.local/` 里放着 A→D 前端线与 M4.1 的原始 QA 报告、命令输出、manifest 与构建日志；
它们**不在 Git 里**（`.local/` 被忽略），删除 worktree 即永久消失。因此必须在删除前把原件字节复制进
仓库、并把**全量**文件按 SHA-256 记账，使「原件不得静默消失」可校验。

### 记录口径

- **`.venv` 跳过**：虚拟环境不承载证据，逐文件入清单无意义，且体量与噪声极大。
- **`*.app` 用目录树摘要**：`.app` 是 bundle 目录，逐文件记账会淹没清单。按同目录生成器与
  [verify_tree_digest.py](../2026-10-15-cleanup-orphans/verify_tree_digest.py) 确立的仓库既有约定，
  记为一条 `TREE <tree_sha256> <file_count> <relpath>`，算法为
  `sha256(concat(relative_posix_path + b"\0" + sha256(file_bytes)))`，文件序按路径排序，见
  [generate-manifest.py](generate-manifest.py) 的 `tree_digest()`。
- **`*.dmg` 记整文件 SHA-256**：作为单个二进制记 `<sha256> <size> <relpath>`。
- **清单格式**：`MANIFEST.sha256` 每行 `<sha256> <size> <relpath>`，或 `.app` 的 `TREE` 行；
  路径相对该 worktree 的 `.local/`。
- **复制规则**（只复制被引用 / 人类可读的小原件，二进制不入 Git）：

  | 形态 | 上限 |
  |---|---|
  | `*.md` | 512 KiB |
  | `*.sha256` | 512 KiB |
  | 名称含 `manifest` / `command-results` / `evidence` 的 `*.json` | 512 KiB |
  | `*.log` | 256 KiB |
  | `*.txt` | 256 KiB |

  未被该规则命中的文件（含 `.dmg`、`.app`、超限日志）**只进 MANIFEST**，不进复制集。

## 2 · 逐 worktree 归档表

每行由 `generate-manifest.py` 实测写出（`/tmp/c2-report-rows.txt` 的内容），「用途」为本轮补注。
`归档字节` 为该 worktree `.local` 内**除** `.venv` 与 `.app` 外的文件字节合计；`MANIFEST 行数` 含 `.app` 的 `TREE` 行。

| worktree | git HEAD | 归档文件数 | 归档字节 | MANIFEST 行数 | MANIFEST | 用途 |
|---|---|---|---|---|---|---|
| `frontend-a-qa-initial` | `9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad` | 47 | 4042096 | 47 | [frontend-a-qa-initial/MANIFEST.sha256](frontend-a-qa-initial/MANIFEST.sha256) | 前端 A 初次独立 QA checkout |
| `frontend-a-qa-repair1` | `9c33a9dde3080fff3e3b3dd8a4193589ef52575f` | 72 | 7408051 | 72 | [frontend-a-qa-repair1/MANIFEST.sha256](frontend-a-qa-repair1/MANIFEST.sha256) | 前端 A 修复轮 1 QA checkout |
| `frontend-b-qa-initial` | `613d453ab1a47e2f0bfe78d685fb90817f70f4cc` | 125 | 8881225 | 125 | [frontend-b-qa-initial/MANIFEST.sha256](frontend-b-qa-initial/MANIFEST.sha256) | 前端 B 初次独立 QA checkout |
| `frontend-b-qa-repair1` | `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c` | 211 | 10577552 | 211 | [frontend-b-qa-repair1/MANIFEST.sha256](frontend-b-qa-repair1/MANIFEST.sha256) | 前端 B 修复轮 1 QA checkout |
| `frontend-c-qa-initial` | `1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c` | 87 | 2472667 | 87 | [frontend-c-qa-initial/MANIFEST.sha256](frontend-c-qa-initial/MANIFEST.sha256) | 前端 C 独立 QA checkout |
| `frontend-d-build` | `944634c0795930426b41110052e3ba1eaeebaf52` | 0 | 0 | 0 | [frontend-d-build/MANIFEST.sha256](frontend-d-build/MANIFEST.sha256) | 前端 D 初次候选构建 worktree；本机已无 `.local` 证据 |
| `frontend-d-build-repair2` | `96fdf4d7cccfd71bd1719d4318e0e399309e8281` | 2 | 22145475 | 3 | [frontend-d-build-repair2/MANIFEST.sha256](frontend-d-build-repair2/MANIFEST.sha256) | 前端 D 修复轮 2 候选构建 worktree（产出 `96fdf4d` DMG/App） |
| `frontend-d-build-repair3` | `e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374` | 2 | 22145235 | 3 | [frontend-d-build-repair3/MANIFEST.sha256](frontend-d-build-repair3/MANIFEST.sha256) | 前端 D **最终**候选构建 worktree（产出 `e8e1dba` DMG/App） |
| `frontend-d-final` | `876008e1d33420f57fb31772c76e471379e6b98d` | 20 | 22226878 | 21 | [frontend-d-final/MANIFEST.sha256](frontend-d-final/MANIFEST.sha256) | 前端 D 初次候选收尾 / 发布构建 worktree（产出 `876008e` DMG/App） |
| `frontend-d-qa-initial` | `876008e1d33420f57fb31772c76e471379e6b98d` | 178 | 12922381 | 178 | [frontend-d-qa-initial/MANIFEST.sha256](frontend-d-qa-initial/MANIFEST.sha256) | 前端 D 初次独立 QA checkout（对 `876008e`） |
| `frontend-d-qa-repair1` | `faa1edd611a74dcdc26bff234de810bdf47761cb` | 240 | 15752645 | 240 | [frontend-d-qa-repair1/MANIFEST.sha256](frontend-d-qa-repair1/MANIFEST.sha256) | 前端 D 修复轮 1 QA checkout（对 `faa1edd`） |
| `frontend-d-qa-repair1-parent` | `876008e1d33420f57fb31772c76e471379e6b98d` | 24 | 819369 | 24 | [frontend-d-qa-repair1-parent/MANIFEST.sha256](frontend-d-qa-repair1-parent/MANIFEST.sha256) | 前端 D 修复轮 1 QA 的父端 harness checkout（构建与后端侧日志） |
| `frontend-d-qa-repair2` | `96fdf4d7cccfd71bd1719d4318e0e399309e8281` | 268 | 15848221 | 268 | [frontend-d-qa-repair2/MANIFEST.sha256](frontend-d-qa-repair2/MANIFEST.sha256) | 前端 D 修复轮 2 QA checkout（对 `96fdf4d`） |
| `frontend-d-qa-repair2-parent` | `faa1edd611a74dcdc26bff234de810bdf47761cb` | 33 | 714237 | 33 | [frontend-d-qa-repair2-parent/MANIFEST.sha256](frontend-d-qa-repair2-parent/MANIFEST.sha256) | 前端 D 修复轮 2 QA 的父端 harness checkout |
| `frontend-d-qa-repair3` | `e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374` | 208 | 12981047 | 208 | [frontend-d-qa-repair3/MANIFEST.sha256](frontend-d-qa-repair3/MANIFEST.sha256) | 前端 D **最终** QA checkout（对 `e8e1dba`） |
| `frontend-d-qa-repair3-parent` | `96fdf4d7cccfd71bd1719d4318e0e399309e8281` | 6 | 5761 | 6 | [frontend-d-qa-repair3-parent/MANIFEST.sha256](frontend-d-qa-repair3-parent/MANIFEST.sha256) | 前端 D 最终 QA 的父端 gate harness checkout |
| `m41-internal-app` | `52d0f3419bf10ad9cb719efed0580256bd059022` | 91 | 109999472 | 96 | [m41-internal-app/MANIFEST.sha256](m41-internal-app/MANIFEST.sha256) | M4.1 构建 worktree（含 5 个 `.app` bundle） |
| `m41-qa-b9321d6` | `acd3ef95e199f6af2714df10f548779b6db3aed8` | 22 | 18179 | 22 | [m41-qa-b9321d6/MANIFEST.sha256](m41-qa-b9321d6/MANIFEST.sha256) | M4.1 QA checkout（对 `b9321d6`） |
| `m41-qa-repair1-3f6eaa4` | `2437f9c771ff7da3aaf2b39a387903654fde5b9d` | 35 | 369027 | 35 | [m41-qa-repair1-3f6eaa4/MANIFEST.sha256](m41-qa-repair1-3f6eaa4/MANIFEST.sha256) | M4.1 修复轮 1 QA checkout（对 `3f6eaa4`） |

## 3 · 合计

| 项 | 实测 |
|---|---|
| 归档 worktree 数 | **19** |
| MANIFEST 总行数 | **1679** |
| 复制原件数 | **395** |
| 复制原件字节 | **888861** |
| `.app` 目录树摘要数 | **8** |
| 凭据命中 | **0** |

19 个 worktree 的 `git status --porcelain` 删除前实测**全部为空**（`frontend-d-build` 的 `.local` 不存在，
其 MANIFEST 为空属正常，非异常）。

## 4 · 凭据扫描声明

对被复制进本目录的 **395** 个候选，生成器逐字节跑了 7 类凭据形态正则：

| 类别 | 形态 |
|---|---|
| `bearer_token` | `Bearer\s+[A-Za-z0-9\-_\.]{20,}` |
| `sk_key` | `sk-[A-Za-z0-9]{16,}` |
| `gho_token` | `gho_[A-Za-z0-9]{20,}` |
| `ghp_token` | `ghp_[A-Za-z0-9]{20,}` |
| `session_token_assign` | `SUMMIT_SESSION_TOKEN\s*[=:]\s*['"]?…` |
| `app_secret` | `app_secret\s*[=:]\s*['"]?…` |
| `api_key` | `api[_-]?key\s*[=:]\s*['"]?…` |

**命中 0**（实测输出 `CREDENTIAL hits=0`）。说明：清单与日志里会成片出现 40 位十六进制串
（`long_hex40` 形态），它们全部是文件 SHA-256 或 git commit SHA，**不是凭据**；因此未把
40 位十六进制列为凭据类别，否则会把正常哈希记账判成泄漏。

## 5 · 原件不可逆声明

`.app` 与 `.dmg` 二进制按 **2026-10-15 用户决定「候选二进制随 worktree 一起删，只留 SHA-256 +
`build-info.json`」**，**不复制入 Git、不另存他处**。它们随 C5 的 worktree 删除一并消失；
其身份此后**只由本目录的 SHA-256 记录保留**（`.app` 见各 `MANIFEST.sha256` 的 `TREE` 行与
`/tmp/c2-app-digests.txt` 同源输出，`.dmg` 见整文件 SHA-256）。
四个关键候选的构建身份另见 [CANDIDATE-IDENTITY.md](CANDIDATE-IDENTITY.md)。

## 6 · 复制件与源文件逐字节复核（抽样）

复制后对**每个有复制件的 worktree 各抽 1 个文件**（取该 worktree 复制集中字节最大者）重新
`shasum -a 256` 比对归档副本与 `.local` 源文件：**16/16 逐字节一致，0 mismatch**。
`frontend-d-build`、`frontend-d-build-repair2`、`frontend-d-build-repair3` 这三个构建 worktree 的
`.local` 内只有 `.app`/`.dmg` 二进制（不满足复制规则），**无复制件可复核**，其身份由 MANIFEST 的
`TREE` / 整文件 SHA-256 覆盖。完整抽样记录见 [DELETIONS.md](DELETIONS.md) §6。
