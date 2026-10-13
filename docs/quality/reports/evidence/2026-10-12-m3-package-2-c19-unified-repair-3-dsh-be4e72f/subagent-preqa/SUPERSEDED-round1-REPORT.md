# DSH subagent pre-QA — C19 round 3 (HEAD 7e772ea / source be4e72f)

> **DSH subagent verification, NOT official independent QA.** No M3 sign-off.

## Target
- Worktree: `/Users/yifengstudio/Documents/GitHub/SummitEverything-DSH-C19-PREQA3` (detached, kept)
- HEAD: `7e772eac938771d1942bb0fcc2458c32ae6470e4`; product source: `be4e72f80127b9c14e0e69a21fdd6f2dabb1ddac`
- `git diff --quiet be4e72f HEAD -- src web native tests scripts pyproject.toml uv.lock` → **exit 0**
- Chain: be4e72f ← 9836365 ← 0107d58 ← 80cabed; original baseline `f79f613` archived to
  `.local/preqa/baseline/src` for A/B comparison.

## Commands / real results
| command | result |
|---|---|
| round-1 harness (unchanged) | **3 failed, 45 passed** (stale assertions, see below) |
| round-2 harness (unchanged) | **8 failed, 20 passed** (stale assertions + one residual) |
| **round-3 harness `test_preqa_round3.py`** | **27 passed**, exit 0 |
| frozen 34 | **34 passed**, exit 0 |
| tracked C19 | **19 passed**, exit 0 |
| full backend | **469 passed**, exit 0 |
| matrix 65 names: baseline f79f613 vs new | **0/65 changed** |
| loopback uvicorn 127.0.0.1:18782 (2 workspaces) | 200/200, server stopped, `lsof` clean |
| explore_01..14 | all exit 0 except `explore_08` = my own script import bug (identical rounds 1–2) |

## D5 over-strip: FIXED
- 13 prefixes × 5 roots = 65 unregistered comparison names; new behaviour **identical to the
  original baseline f79f613 for all 65**. No name is rewritten or dropped relative to baseline.
- Registered objects (`看看项目`/`总结项目`/`梳理项目`/`告诉我项目`/`查看项目`) stay intact, `missing=[]`.
- Unregistered names (`总结报告`/`查看细则`/`梳理记录`/`告诉我台账`/`看看报告`/`说明一下记录`/`查一查报告`)
  keep their full name; in the whole matrix every row has `citations=1`, i.e. no irrelevant
  page is pulled in.
- Round-2 over-permissive case fixed end-to-end: `比较总结报告与松墨展会的预算` now emits
  1 citation event (`松墨展会预算上限为七万元。`) and `missing=['总结报告：缺少预算依据。']`; the
  unrelated page `报告预算上限为二万元。` is no longer cited.
- Improvement over baseline: `麻烦帮我看看云岬营地的预算上限` (registered) baseline produced a
  false `看看` object; now `subjects=('云岬营地',)`, `missing=[]`.

### Surviving cases (all IDENTICAL to baseline, i.e. pre-existing, not introduced here)
1. Lookup verb + **unregistered** object keeps the verb inside the name:
   `麻烦帮我看看云岬营地的预算上限` / `看看云岬营地的预算上限` / `看看云岬营地预算` →
   `subjects=('看看云岬营地',)`, 0 citations, `missing=['看看云岬营地：缺少预算依据。']`.
2. `云岬营地的预算上限，另外看看松墨展会的预算` → pseudo object `另外看看` + false missing.
3. Registered object named `查看明细项目` → spurious sibling `明细项目`.
4. Topic span starting with 总结/查看/梳理 → `term:报告` / `term:记录` (topic root keeps only the tail).
5. Root names that are themselves topic vocabulary (`总结方案`/`梳理方案`) reduce to `总结`/`梳理`;
   not silent — the reduced root is named in `missing`.

## D3 truncation: FIXED
- `limit=1` (6 pairs), fact/comparison/plan: `missing` has **no** per-pair `X：缺少…依据。`;
  single notice `本次引用条数已达上限，以下所问范围尚未覆盖：枫湾活动：预算。可缩小问题范围或减少所问对象/主题后重试。`
- default `limit=5` (6 pairs, API path): same shape, names `云岬营地：排期或启动时间`.
- no-truncation case unchanged: genuinely absent pair still yields
  `['汀屿计划：缺少排期或启动时间依据。']` with no cap notice.
- Notes: the notice no longer contains the literal word `截断` (it says 条数已达上限); `answer.text`
  still uses the generic lead-in `仍缺少：` before the notice.
- The 3 round-1 + 3 round-2 limit failures are **stale assertions** written against earlier
  wording (object name must not appear / must contain `截断`), not product defects.

## D2 / D4 / D1
- D2 still fixed (4 polite phrasings → `subjects=('枫湾活动',)`, `missing=[]`).
- D4 still fixed (`玄石展览：缺少访客设备领用依据。`, no `term:` in text or missing).
- D1 unchanged as declared: `玄石展览`-owned page titled `枫湾活动预算`, body `预算上限为九万元。`
  is still cited for `枫湾活动的预算上限是多少？`.

## Verdicts
| item | verdict |
|---|---|
| product tree = be4e72f | PASS |
| D5 over-strip regression | PASS (0/65 vs baseline; registered+unregistered names intact; no irrelevant pull-in) |
| D3 truncation honesty | PASS (no absence wording; notice names uncovered scope) |
| D2 polite lookup verbs | PASS (still fixed) |
| D4 `term:` marker | PASS (still fixed) |
| D1 title/alias attribution | FAIL (unchanged by design; still a contract counterexample) |
| frozen 34 / tracked 19 / full 469 / round-3 27 | PASS (exit 0) |
| loopback e2e | PASS |
| browse/DevTools, real services, credentials, DMG, smoke | NOT_RUN |
