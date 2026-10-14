# M4.2 A candidate UI observations (manual CUA transcript)

Tested source SHA: `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b`.
Candidate was copied to `/var/folders/yp/7n9pls2j2rl0sz9vmfdf4z6r0000gn/T/se-m42-package-a-qa.20261014080102/candidate.app`; UI data lives only in `/var/folders/yp/7n9pls2j2rl0sz9vmfdf4z6r0000gn/T/se-m42-package-a-qa.20261014080102/profile-ui-20261014-080704` and the isolated `ui-workspace`.

The copied app was launched with `open -n --env SUMMIT_OFFLINE_GUARD_ACTIVE=1 --env SUMMIT_INTERNAL_TEST_PROFILE_ROOT=<fresh profile root> <candidate.app>`. QA-only process verification found native PID 30964 and backend PID 30970; both had guard value `1` and canonical profile root matching the isolated root. On relaunch native PID 31230 and backend PID 31232 had the same guard/profile match. The checker prints only safe guard booleans, PIDs, and profile-match booleans; it does not print full process environment. The initially wrong checker run is retained in `native-guard-process-check.log`; checker source/field correction is documented in REPORT.md. Both corrected outputs are retained.

Settings before and after restart displayed `运行模式: Fake · 离线`, `钥匙串不可用`, `当前运行环境无法访问 macOS 钥匙串`, and `当前不可对外请求`; `保存到钥匙串` and `删除本机密钥` were disabled. No credential was entered and no external service was intentionally invoked.

In the actual native app and WebView, QA created `M42 QA 合成库`, mainline `QA 合成访客流程`, and project `访客登记规则`. Using the native file picker, QA selected only `.local/qa/m42-a/fixtures/synthetic-visitor.md` (SHA-256 `a92f8ddbc3f6278d2e71fd84ba6f5a3dd11afe184fa3f45fefb23638b89e4e72`). The source appeared as pending review. QA explicitly clicked organize, edited the complete title to `访客登记与离场记录流程` and complete body to:

> # 访客登记与离场记录
>
> 前台接待访客时，应先核验姓名，再记录来访时间。访客离开时，前台补记离开时间。
>
> 以上规则用于合成 QA 流程验证。

QA saved edits and explicitly confirmed writing. Source moved to `已完成`; UI stated first indexing still required confirmation. QA prepared and confirmed the Fake local index plan; UI reported 1 eligible page, about 17 text tokens, ¥0 Fake embedding cost, then `本机索引已就绪 1 个页面 · 1 个分块 · summit-fake-embedding-v1`.

First exact question: `访客离开时，前台应记录什么？` UI returned a completed answer: `当前资料只覆盖了部分所问范围：访客登记与离场记录：访客离开时，` and said `未限定对象：缺少前台应记录什么依据。` The citation button identified page `访客登记与离场记录`, snippet `访客离开时，`, and `引用版本仍可用`. This is visibly incomplete and the missing-evidence statement conflicts with the complete confirmed sentence above.

After app quit and relaunch with the same guard and profile, QA explicitly reopened the same workspace through the onboarding UI. Source `synthetic-visitor.md` remained `已完成`; the same mainline/project selection remained. The question appeared in local history, with 1-page/1-chunk Fake index ready. Opening history reproduced the incomplete answer and citation version was still available.

A second, separate conversation asked `访客离场后要补充记录哪些信息？`. The Fake answer said no supporting evidence for the topic and returned no citation, again despite the confirmed body containing a directly relevant statement. This is observed Fake-mode answer/retrieval quality only; it does not establish the quality of answers generated with a real provider, nor does this UI observation isolate whether the underlying cause is the Fake answer adapter, shared query planning/evidence assessment, or both.

CUA accessibility-tree results are present in the QA task transcript. No screenshot, browser DevTools console, or browser network-panel capture was obtained. Thus UI behavior above is observed through native accessibility state, not claimed as DevTools/network-panel verification.

The app was quit through its own UI; a final process-table check found no process for the isolated candidate executable. No existing app or service was terminated.
