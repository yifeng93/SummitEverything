# 已删路径 → 归档索引（2026-10-15 清理）

日期：2026-10-15。分片：C2 · 证据归档与索引。
作者：Luna（High）。

本文件是**索引**，不是重写。历史报告正文（含下列 `/Users/…/.codex/worktrees/…` 绝对路径快照）
按 AGENTS「历史报告、原始 DEV / QA 证据、manifest 与签名字节保留原样」的约束**逐字保留、未改写**。
本文件只做一件事：把这些已失效的快照路径映射到它们今天可追溯的归档去处。

## 0 · 实测扫描（不硬编码）

用以下脚本列出所有 tracked `*.md` 中指向上级目录 worktree 的**绝对路径链接**（`[…]` 形式）：

```sh
python3 - <<'PY'
import re, subprocess, os, urllib.parse
files=[f for f in subprocess.run(['git','ls-files','-z'],capture_output=True,text=True).stdout.split('\0') if f.endswith('.md')]
link=re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')
for f in files:
    txt=open(f,encoding='utf-8').read(); base=os.path.dirname(f)
    for m in link.finditer(txt):
        t=m.group(1)
        if not t.startswith('/Users/'): continue
        print(f"{f}\t{t}")
PY
```

实测输出**恰好 7 条**：`docs/quality/reports/2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md` 3 条
（均指向 `m3-package-1-qa`），`docs/quality/reports/2026-10-15-FRONTEND-A-INITIAL/QA-REPORT.md`
4 条（均指向 `frontend-a-qa-initial`）。这 7 条同时也是全仓相对链接检查中**仅有的 7 条失效项**
（其余相对链接失效为 0）。

## 1 · 对照表

| 来源报告 | 行内路径 | 指向的 worktree | 该 worktree 现状与去向 | 可追溯方式 |
|---|---|---|---|---|
| `docs/quality/reports/2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md`（第 9 行，`AskView.tsx:148`） | `/Users/yifengstudio/.codex/worktrees/m3-package-1-qa/SummitEverything/web/src/components/AskView.tsx:148` | `m3-package-1-qa` | 历史快照，2026-10-15 之前即已不存在，无原件可归档 | 源码行本身在仓库内以当时固定 SHA 可复现；历史正文逐字保留 |
| `docs/quality/reports/2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md`（第 9 行，`conversations.py:209`） | `/Users/yifengstudio/.codex/worktrees/m3-package-1-qa/SummitEverything/src/summit_everything/local/conversations.py:209` | `m3-package-1-qa` | 历史快照，2026-10-15 之前即已不存在，无原件可归档 | 同上 |
| `docs/quality/reports/2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md`（第 13 行，`AskView.tsx:243`） | `/Users/yifengstudio/.codex/worktrees/m3-package-1-qa/SummitEverything/web/src/components/AskView.tsx:243` | `m3-package-1-qa` | 历史快照，2026-10-15 之前即已不存在，无原件可归档 | 同上 |
| `docs/quality/reports/2026-10-15-FRONTEND-A-INITIAL/QA-REPORT.md`（第 60 行，`FirstUseWizard.tsx:301`） | `/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything/web/src/components/FirstUseWizard.tsx:301` | `frontend-a-qa-initial` | 属本轮 19 个删除集；checkout 于 C5 删除，`.local` 证据已归档 | [evidence/2026-10-15-worktree-archive/frontend-a-qa-initial/MANIFEST.sha256](evidence/2026-10-15-worktree-archive/frontend-a-qa-initial/MANIFEST.sha256) |
| `docs/quality/reports/2026-10-15-FRONTEND-A-INITIAL/QA-REPORT.md`（第 68 行，`SettingsView.tsx:46`） | `/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything/web/src/components/SettingsView.tsx:46` | `frontend-a-qa-initial` | 同上 | 同上 |
| `docs/quality/reports/2026-10-15-FRONTEND-A-INITIAL/QA-REPORT.md`（第 68 行，`settingsBadges.ts:195`） | `/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything/web/src/components/settingsBadges.ts:195` | `frontend-a-qa-initial` | 同上 | 同上 |
| `docs/quality/reports/2026-10-15-FRONTEND-A-INITIAL/QA-REPORT.md`（第 76 行，`SettingsView.tsx:80`） | `/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything/web/src/components/SettingsView.tsx:80` | `frontend-a-qa-initial` | 同上 | 同上 |

### `m3-package-1-qa`（3 条）

`m3-package-1-qa` **不在本轮 20 个 worktree 名单中**——它在 2026-10-15 之前就已移除，因此
**无原件可归档**，这 3 条路径只是当时执行位置的**历史快照**。它们指向的源码行（`AskView.tsx`
第 148 / 243 行、`conversations.py` 第 209 行）在仓库历史中有固定 SHA 可复现；历史报告正文一字未改，
失效快照仍在原处，仅由本索引说明其性质。

### `frontend-a-qa-initial`（4 条）

`frontend-a-qa-initial` 属本轮 C5 删除集，其 `.local` 证据已全量归档（47 文件 / 4042096 字节，
MANIFEST 47 行）。这 4 条路径指向的是**该 checkout 里的 `web/src/**` 源码行号**
（`FirstUseWizard.tsx:301`、`SettingsView.tsx:46`、`settingsBadges.ts:195`、`SettingsView.tsx:80`），
而这些源码在仓库内以**固定 SHA** 可复现：该 worktree 的 HEAD 为 `9ed544ab5cfcbf21b6e81290a4bf0c5a9825e9ad`，
即 `git show 9ed544a:web/src/components/SettingsView.tsx` 可取出与快照同一版本的源码。
因此这 4 条即便 checkout 目录消失，仍可从仓库内以 `9ed544a` 复现，不构成不可追溯的丢失。

## 2 · 补充：非链接形式的同类快照

除上述 7 条 Markdown **链接**外，`docs/quality/reports/2026-10-15-FRONTEND-A-INITIAL/QA-REPORT.md`
第 5 行还有一条以反引号包裹的同一 checkout 绝对路径
（`/Users/yifengstudio/.codex/worktrees/frontend-a-qa-initial/SummitEverything`）。
它不是链接、不计入相对链接检查的失效项，但其去向与本表一致：该 checkout 于 C5 删除，
证据归档于 [evidence/2026-10-15-worktree-archive/frontend-a-qa-initial/](evidence/2026-10-15-worktree-archive/frontend-a-qa-initial/)。

## 3 · 相关索引

- 全量归档说明与逐 worktree 表：`evidence/2026-10-15-worktree-archive/README.md`
- 候选构建身份：`evidence/2026-10-15-worktree-archive/CANDIDATE-IDENTITY.md`
- 删除可追溯主表：`evidence/2026-10-15-worktree-archive/DELETIONS.md`
- C3 孤儿原件归档：`evidence/2026-10-15-cleanup-orphans/`

## 4 · 归档副本内的既知失效链接（不改写）

清理后全仓 tracked `*.md` 的相对链接检查共 **23** 条失效，分两类，均**不属于本轮新增/修改的自撰文档**：

1. **7 条历史报告正文里的绝对路径快照**（本文 §1 已逐条解释）——按 AGENTS 约束逐字保留。
2. **16 条位于 `evidence/2026-10-15-worktree-archive/` 下的逐字归档副本内部**——这些副本是 C2 从即将删除的
   worktree `.local` 里原样复制过来的历史报告，其字节被同目录 `MANIFEST.sha256` 的 SHA-256 固定；
   **改写它们会立即破坏归档完整性校验**，因此一律不改。其中：
   - 4 条是归档副本 `frontend-a-qa-initial/qa/frontend-a-initial/QA-REPORT.md` 里的 `/Users/…/frontend-a-qa-initial/…` 绝对路径（与 §1 的 4 条同源，属同一 checkout 的历史快照）；
   - 14 条是各归档 `QA-REPORT.md` 指向**同 checkout 内兄弟证据文件**（如 `evidence/source-scope-request.json`、`candidate-identity.json`、`evidence/native-preflight.json`）或指向 `web/src/**` 源码行的相对链接；这些兄弟文件有的是二进制截图（`.png`）、有的不在 C2 的复制规则内，因此没有随报告一起复制。

**判定**：这两类失效都不影响「新增/修改的自撰文档相对链接全部可解析」这一验收要求——本轮 C1/C2/C3/C6/C7
自撰的文档（含本文件、`DELETIONS.md`、归档 `README.md`、`CANDIDATE-IDENTITY.md`、两份新报告）自身
**0 条**失效相对链接。
