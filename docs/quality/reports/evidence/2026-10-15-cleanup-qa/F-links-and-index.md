# F · 链接与索引自洽（QA 独立实现的口径）

QA **未使用**实现者的 `/tmp/linkcheck.py`（该脚本已随 `/tmp` 清理不可得），而是自写
[linkcheck.py](linkcheck.py) 并公开口径：

- 扫描面：`git ls-files '*.md'`（`7a448c3` 原样实测 **340** 个 tracked Markdown 文件；
  把本次 QA 新增的 5 个 `.md` 一并纳入后为 **345** 个，见下方「双口径」）；
- 链接形态：行内链接（方括号文本 + 圆括号目标，含图片）与引用式定义（方括号标识 + 冒号 + 目标）；
- 跳过：空目标、纯锚点 `#…`、scheme `http://` / `https://` / `mailto:` / `tel:` / `data:` / `ftp://`；
- 其余目标：去掉 `#anchor` 与 `?query`、URL 解码后，作为文件系统路径相对该 md 所在目录解析
  （以 `/` 开头者按绝对路径解析）；**目标不存在即计 broken**。

**双口径（都对 `7a448c3` 有效）**

| 扫描面 | tracked md | TOTAL broken | 其中 QA 新增文档贡献 |
|---|---|---|---|
| `7a448c3` 原样（不含 QA 新增 5 个 `.md`） | 340 | **23** | — |
| 含 QA 新增的 5 个 `.md`（用 `git add -N` 纳入 `git ls-files`） | 345 | **23** | **0** |

即 QA 自撰/修改的文档**新增 0 条**失效相对链接，不改变 23 这个总数。

```sh
uv run python .local/qa/cleanup-verify/linkcheck.py .
# tracked md files scanned: 340   relative-ish link targets: 1049
# TOTAL broken = 23
```

## 分解（期望 7 + 16 + 0）

| 类别 | 期望 | QA 实测 | 命中的文件 |
|---|---|---|---|
| 历史报告正文里的 `/Users/…` 绝对路径快照 | 7 | **7** | `docs/quality/reports/2026-10-11-M3-PACKAGE-1-QA-c90fe6e.md` ×3、`docs/quality/reports/2026-10-15-FRONTEND-A-INITIAL/QA-REPORT.md` ×4 |
| `evidence/2026-10-15-worktree-archive/` 下被 MANIFEST 哈希固定的逐字归档副本内部 | 16 | **16** | `frontend-a-qa-initial/qa/frontend-a-initial/QA-REPORT.md` ×4、`frontend-b-qa-initial/qa/frontend-b-initial/QA-REPORT.md` ×7、`frontend-d-qa-initial/qa/frontend-d-initial/QA-REPORT.md` ×5 |
| 其它（本轮自撰/修改文档自身） | **0** | **0** | — |

实测命令：

```sh
awk -F'\t' '/^BROKEN/{print $2}' F-linkcheck.txt > /tmp/qa-broken-files.txt
grep -c  '2026-10-15-worktree-archive/' /tmp/qa-broken-files.txt   # 16
grep -vc '2026-10-15-worktree-archive/' /tmp/qa-broken-files.txt   # 7
grep '^BROKEN' F-linkcheck.txt | grep -v '/Users/' | grep -vc '2026-10-15-worktree-archive/'   # 0
```

16 条的具体形态分两类，均属**归档副本在仓库内的相对位置已改变**所致，是「逐字归档」的必然代价：

1. 7 条 `/Users/…/.codex/worktrees/<wt>/SummitEverything/web/src/...` 绝对路径快照
   （原件在源 worktree 内也无法解析，与归档位置无关；全仓 `/Users/` 命中合计 14 = 归档区 7 + 报告正文 7）；
2. 9 条原本相对 `.local/<rel>` 解析的兄弟路径（如 `evidence/source-scope-request.json`、
   `candidate-identity.json`、`evidence/native-preflight.json`），复制进仓库后其兄弟文件落在复制规则之外
   （PNG / 超限 JSON 不进复制集）。

**其它 0 → 本轮自撰/修改的全部文档自身 0 条失效相对链接 → PASS。**
（说明：`docs/quality/reports/2026-10-15-PRE-PR21-CLEANUP-DEV.md`、`DELETIONS.md`、
`DELETED-PATHS-INDEX.md`、`2026-10-15-worktree-archive/README.md` 等均在「其它」中贡献 0 条。）

## 报告索引自洽

```sh
cd docs/quality/reports
ls *.md | grep -v '^README.md$' | wc -l     # 120（直接层报告数，不含 README.md 自身）
# 逐个反查 README.md 是否出现该文件名
# not indexed in README.md = 0
```

直接层 `.md`（不含 `README.md`）**120** 个，其中**未出现在 `README.md` 里的 = 0** → PASS。

计数演进与 DEV 报告一致：C1 时点 118/缺口 0 → C6 后 119/缺口 1（新增的 `DELETED-PATHS-INDEX.md`
是索引不是报告）→ `7a448c3` 时点 120/缺口 **0**（DEV 报告本身 +1，且
`412e0fd`/`7a448c3` 已把索引补全）。本次 QA 追加的 `2026-10-15-PRE-PR21-CLEANUP-QA.md`
由 QA 自己补进 `README.md` 的「历史报告完整索引」（标签 = 该报告 H1 原文），
补后复测：直接层 `.md` = **121**，**未出现在 `README.md` 里的 = 0** → 缺口仍为 0。
