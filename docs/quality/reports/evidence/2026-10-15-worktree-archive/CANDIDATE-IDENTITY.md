# 2026-10-15 候选构建身份（build-info 全文 + 二进制 SHA-256）

日期：2026-10-15。分片：C2 · 证据归档与索引。
本文件逐个记录四个候选 `.app` / `.dmg` 的**身份**。`build-info.json` 为 `.app` 内
`Contents/Resources/build-info.json` 的**全文原文**（2026-10-15 在本 worktree 实测 `cat`，未改写）；
`.app` 树摘要按 [generate-manifest.py](generate-manifest.py) 的 `tree_digest()` 算法实测；
`.dmg` 为整文件 SHA-256。

## 0 · 身份总表

| 候选 | worktree | DMG 整文件 SHA-256 | `.app` 树摘要 | `.app` 文件数 |
|---|---|---|---|---|
| `e8e1dba`（D 最终） | `frontend-d-build-repair3` | `5f9805eb8ced1ccacbdd32f2e63a70d74ee94b67f9dd18375a893ba3e779bb2b` | `f634fc05101a21ead924ea80cb755c40a5a02145b507f23dedd3dfbb791e635f` | 157 |
| `876008e`（D 初次） | `frontend-d-final` | `8bd387bac1c942da3640952da2b334ed53776f12dd04adf2f1eed343989d8fa9` | `01fb7046ce4c291a0525d2b085370ad94196bb23beac0e904e2b3f8ea1b5a9f8` | 157 |
| `96fdf4d`（D 修复轮 2） | `frontend-d-build-repair2` | `bdbed4228b2b93ee830786e5732fe851dca3bce9a563d02d51b1851c11783765` | `6944d670f936a746d860315bd15a6f91977f45919c2193b8e402619744288cc9` | 157 |
| `3f6eaa4`（M4.1 修复轮 1） | `m41-internal-app` | `554b7ab3d2bc22728ec6484d1109d9bee8b149814aac556571e45a1d1d7f59d8` | `1e58574ea68174ffa20f77b7838796d1c180c35cab7e43b66c274a3587b2f4eb` | 156 |

三个 D 候选的 DMG SHA-256 由 C2 独立 `shasum -a 256` 复算，与
[frontend-d-build-repair3/MANIFEST.sha256](frontend-d-build-repair3/MANIFEST.sha256) 等清单内记录一致；
`3f6eaa4` 的 DMG SHA-256 与 [m41-internal-app/MANIFEST.sha256](m41-internal-app/MANIFEST.sha256) 内
`dev/m41/repair-1/artifacts/SummitEverything-Internal-fix1-3f6eaa4.dmg` 行一致，且与
`docs/handoff` 中该轮的文档记载一致。

---

## 1 · `e8e1dba`（前端 D 最终候选）

- worktree：`/Users/yifengstudio/.codex/worktrees/frontend-d-build-repair3/SummitEverything`
- 产物：`.local/dev/frontend-d-repair3/SummitEverything-D-e8e1dba.app`、
  `.local/dev/frontend-d-repair3/SummitEverything-D-e8e1dba.dmg`
- DMG 整文件 SHA-256：`5f9805eb8ced1ccacbdd32f2e63a70d74ee94b67f9dd18375a893ba3e779bb2b`（22144911 字节）
- `.app` 树摘要：`f634fc05101a21ead924ea80cb755c40a5a02145b507f23dedd3dfbb791e635f`（157 文件）

`Contents/Resources/build-info.json` 全文：

```json
{"app_version": "0.1.0", "build_id": "20261015T144744Z-784ae1ee176a", "dependencies_sha256": "cab274716d93a5485155114bd25f3a65722eede97c4487d11262d8b73728c7d7", "dirty": false, "frontend_sha256": "784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0", "source_sha": "e8e1dba0c1fed9a5f02babcc29e5d5f67dc1d374"}
```

关键值：`build_id` = `20261015T144744Z-784ae1ee176a`、`frontend_sha256` = `784ae1ee…`、
`dependencies_sha256` = `cab27471…`、`dirty` = `false`、`source_sha` = `e8e1dba…`。

---

## 2 · `876008e`（前端 D 初次候选）

- worktree：`/Users/yifengstudio/.codex/worktrees/frontend-d-final/SummitEverything`
- 产物：`.local/dev/frontend-d-final/SummitEverything-D-876008e.app`、
  `.local/dev/frontend-d-final/SummitEverything-D-876008e.dmg`
- DMG 整文件 SHA-256：`8bd387bac1c942da3640952da2b334ed53776f12dd04adf2f1eed343989d8fa9`（22140209 字节）
- `.app` 树摘要：`01fb7046ce4c291a0525d2b085370ad94196bb23beac0e904e2b3f8ea1b5a9f8`（157 文件）

`Contents/Resources/build-info.json` 全文：

```json
{"app_version": "0.1.0", "build_id": "20261015T132109Z-8a0917f72e08", "dependencies_sha256": "cab274716d93a5485155114bd25f3a65722eede97c4487d11262d8b73728c7d7", "dirty": false, "frontend_sha256": "8a0917f72e0833727fa90a4f827e70be8835db6711eb9e24b167df16087fab62", "source_sha": "876008e1d33420f57fb31772c76e471379e6b98d"}
```

关键值：`build_id` = `20261015T132109Z-8a0917f72e08`、`frontend_sha256` = `8a0917f7…`、
`dependencies_sha256` = `cab27471…`、`dirty` = `false`、`source_sha` = `876008e…`。

---

## 3 · `96fdf4d`（前端 D 修复轮 2 候选）

- worktree：`/Users/yifengstudio/.codex/worktrees/frontend-d-build-repair2/SummitEverything`
- 产物：`.local/dev/frontend-d-repair2/SummitEverything-D-96fdf4d.app`、
  `.local/dev/frontend-d-repair2/SummitEverything-D-96fdf4d.dmg`
- DMG 整文件 SHA-256：`bdbed4228b2b93ee830786e5732fe851dca3bce9a563d02d51b1851c11783765`（22145151 字节）
- `.app` 树摘要：`6944d670f936a746d860315bd15a6f91977f45919c2193b8e402619744288cc9`（157 文件）

`Contents/Resources/build-info.json` 全文：

```json
{"app_version": "0.1.0", "build_id": "20261015T142919Z-784ae1ee176a", "dependencies_sha256": "cab274716d93a5485155114bd25f3a65722eede97c4487d11262d8b73728c7d7", "dirty": false, "frontend_sha256": "784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0", "source_sha": "96fdf4d7cccfd71bd1719d4318e0e399309e8281"}
```

关键值：`build_id` = `20261015T142919Z-784ae1ee176a`、`frontend_sha256` = `784ae1ee…`、
`dependencies_sha256` = `cab27471…`、`dirty` = `false`、`source_sha` = `96fdf4d…`。
注意其 `frontend_sha256` 与最终候选 `e8e1dba` 相同（均为 `784ae1ee…`），差异只在 `source_sha`
与 `build_id`（`96fdf4d` → `e8e1dba` 为同一前端指纹下的源码提交推进）。

---

## 4 · `3f6eaa4`（M4.1 修复轮 1 候选）

- worktree：`/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything`
- 产物：`.local/dev/m41/repair-1/artifacts/SummitEverything Internal fix1 3f6eaa4.app`、
  `.local/dev/m41/repair-1/artifacts/SummitEverything-Internal-fix1-3f6eaa4.dmg`
- 文档记载 DMG SHA-256：`554b7ab3d2bc22728ec6484d1109d9bee8b149814aac556571e45a1d1d7f59d8`
  （本轮独立 `shasum -a 256` 实测同值，21934165 字节）
- `.app` 树摘要：`1e58574ea68174ffa20f77b7838796d1c180c35cab7e43b66c274a3587b2f4eb`（156 文件）

`Contents/Resources/build-info.json` 全文：

```json
{"app_version": "0.1.0", "build_id": "20261013T060945Z-577f0cc805f2", "dependencies_sha256": "2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f", "dirty": false, "frontend_sha256": "577f0cc805f2f7727add28c1e0d4714c0c15040fa7c094fce7e6234c65239fc6", "source_sha": "3f6eaa408a8860ff5a438be8a874a2c3904733e4"}
```

`m41-internal-app` 的 `.local` 内共 **5 个 `.app`** 与对应 DMG，全部身份记录在
[m41-internal-app/MANIFEST.sha256](m41-internal-app/MANIFEST.sha256)：

| `.app` 相对 `.local` 路径 | 文件数 | 树摘要 |
|---|---|---|
| `dev/m41/artifacts/SummitEverything Internal 2.app` | 156 | `942fcfa9a60b74d522ab66e5e2f48408918d8da0ee96b7815aacdb052fc87a02` |
| `dev/m41/artifacts/SummitEverything Internal M4.1 b9321d6.app` | 156 | `96face5e21c4d237018bc86e8ab89d74651ac4bad5caaea653580a93475def73` |
| `dev/m41/artifacts/SummitEverything Internal M4.1-DV3.app` | 156 | `b583b068c0148574aec25f1712f2b15a2bb0d090aa685d0d05e573cee99b57de` |
| `dev/m41/artifacts/SummitEverything Internal.app` | 156 | `533583d11cb1430f719ba17a8e72abaf57f94c8325c35acbe204a3f6ac628c99` |
| `dev/m41/repair-1/artifacts/SummitEverything Internal fix1 3f6eaa4.app` | 156 | `1e58574ea68174ffa20f77b7838796d1c180c35cab7e43b66c274a3587b2f4eb` |

---

## 5 · 二进制不可逆声明

**上述 `.app` 与 `.dmg` 二进制已按 2026-10-15 用户决定随 worktree 删除，本机不再保留；
本文件与各 `MANIFEST.sha256` 中的 SHA-256 及 `build-info.json` 副本是唯一可追溯来源，
日后复验需按对应 `source_sha` 重建。**

以上四个候选的 DMG 实测 SHA-256（删除前）：

| 候选 | DMG 整文件 SHA-256 |
|---|---|
| `e8e1dba` | `5f9805eb8ced1ccacbdd32f2e63a70d74ee94b67f9dd18375a893ba3e779bb2b` |
| `876008e` | `8bd387bac1c942da3640952da2b334ed53776f12dd04adf2f1eed343989d8fa9` |
| `96fdf4d` | `bdbed4228b2b93ee830786e5732fe851dca3bce9a563d02d51b1851c11783765` |
| `3f6eaa4` | `554b7ab3d2bc22728ec6484d1109d9bee8b149814aac556571e45a1d1d7f59d8` |
