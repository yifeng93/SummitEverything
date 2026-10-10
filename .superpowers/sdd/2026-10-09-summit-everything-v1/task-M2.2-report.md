# M2.2 DEV report — 2026-10-10

## Status and fixed commits

**DEV完成待验收，Fake only。** Scope is the exact M2.2 brief; M2.3 and M3–M5 are not implemented here. No push / PR / merge, real account / task / credential or paid provider calls. Independent QA is outstanding. The documentation commit containing this report is identified by the final handoff; no self-referential commit SHA is embedded.

Checkout `/Users/yifengstudio/.codex/worktrees/summit-m2/SummitEverything`, branch `codex/m2-feishu-actions-journal`, baseline `83c5eb6a1ca0a121d39a2b663c9f172339b36f9b` (M2.1 provider/session/credential interfaces).

| Logical increment | Exact SHA |
|---|---|
| Durable independent actions, Fake task state, local progress, routes / tests | `ffe9456513071115aa012b623d28a4ced67b333d` |
| REST strings / canonical hash / write-scope reads / independent evidence / local recovery | `9d3057333e5468ac8bc389af0e955fb90aaa4d9c` |
| Strict date bool / nonblank confirmation | `0c8aaa00c36e7ba38a8e108edc000dae4f130dc1` |
| Explicit task / progress forms, review / confirmation / unknown UI | `a73cf4d93c8901c1d6c503b5d374318bb3dde139` |
| Exact task targets / selected project version / late terminal outcome protection | `a22bfeeb56bf837a9b86e4aaa15e0c1e9a426ea1` |
| Existing running replay returns contractual 202 + Location (final code) | `a7f76e4d188dad607ac069047e76ffaa3135707d` |

## Implementation and failure semantics

- Preserve exact payload and canonical UTF-8 JSON SHA-256; action identity, kind and candidate association are compared independently. Same UUID / same hash returns existing result or running state; changed values409. Different valid UUIDs may create identical titles.
- Knowledge / draft approval and candidate prose never approve actions. User sees final values, confirms independently, then explicitly executes. Payload edit invalidates the confirmation and records the old ID/hash; the old confirmation cannot be reused. Candidate conversion preserves candidate/draft/source IDs while old candidate records and array API remain unchanged.
- Workspace identity lock covers validation, confirmation/hash comparison and atomic durable running claim **before** provider boundary. Other callers receive running202 + Location without a write. Stable UUID client token derives from workspace UUID + action UUID; unknown never retries or invents another UUID. Memory session ID distinguishes persisted running after restart → unknown.
- Timeout / malformed response / unavailable response → unknown. Missing authorization / expiry / scope preflight prevents a write; definite not_found / scope failure during boundary → failed. Project version conflict → failed without overwriting progress. Raw exception text / credentials are not returned. Receipt write interruption can propagate an error, leaving durable running; later restart / read yields unknown, with no second execution.
- Reconciliation only reads exact Fake execution evidence, or verified local writer journal. No evidence stays unknown; titles / ordinary task lists do not prove execution. Unknown can be explicitly resolved by independently confirmed user outcome and nonempty evidence; same outcome ID/value replays, changed evidence409. Latest evidence is retained when an original response arrives late; an already resolved terminal outcome is not overwritten.
- Local ProjectProgressWriter reuses workspace manifest write_intent / atomic replacement, expected progress_version and explicit confirmation. It modifies progress fields only; knowledge confirmation does not call it. Lost receipt can recover from local writer operation_id / request_hash and target manifest without applying progress twice.
- Active receipts are portable workspace evidence, not a task database. Older succeeded/failed finished months move to schema `action-receipt-month-v1` summary; atomic summary precedes deletion. Equal interrupted duplicates are safe; hash corruption/conflicting duplicates block409. running/unknown are never compressed away or removed by TTL. Lookup scans all receipts; no additional speculative cache.
- Fake owns a named `simulated_remote_tasks.json` outside product workspace/profile, under `summit-simulated-feishu-remote-*` in temporary storage by default (tests inject their own remote root). Actual file locks / atomic writes persist synthetic facts and token results across processes. Credentials are still M2.1 process-memory synthetic credentials, never a new auth stack.

## Provider request mapping and documentation limits

Only public first-party documentation / official SDK code were read; no Feishu API calls were made.

| Behavior | Verified shape / Fake boundary |
|---|---|
| Read | GET `/open-apis/task/v2/tasks`; GET `/:task_guid`; user `task:task:read` **or** `task:task:write` |
| Pagination | page_size/page_token; provider items/has_more/page_token; local cursor/limit, items/next_cursor |
| Create | POST tasks: summary, description, optional due, stable UUID client_token; user write scope |
| Edit | PATCH `/:task_guid`: task plus update_fields, only explicitly selected summary/description/due; selected null due clears date |
| Complete | GET current first; already completed succeeds without PATCH; otherwise PATCH task.completed_at millisecond **string**, update_fields=[completed_at] |
| Timed due | due.timestamp millisecond **string** + is_all_day=false; explicit aware ISO time and IANA timezone validated in local intent; timezone not an invented REST field |
| All-day due | Original ISO date + IANA + strict all-day bool retained. Local-zone midnight timestamp is **Fake-only convention**, actual Feishu extraction rule remains unverified. |
| Result lookup | `task_result(token)` is a **synthetic evidence operation**. It is not claimed to be a real Feishu client_token lookup endpoint; real implementation with no concrete lookup must retain unknown. |

Sources: [official Task v2 overview](https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/task-v2/overview), [first-party English indexed overview](https://open.larkenterprise.com/document/task-v2/overview), [official Python SDK request models](https://github.com/larksuite/oapi-sdk-python/tree/v2_main/lark_oapi/api/task/v2/model), [official Go SDK Due / InputTask comments](https://pkg.go.dev/github.com/larksuite/oapi-sdk-go/v3/service/task/v2).

The overview specifies millisecond REST strings and that write scope permits reads; SDK model numeric typing alone does not establish REST encoding. Its client_token support applies to create / subtask / add-members, with five-minute successful-response window; Summit durable safety is independent and has no arbitrary TTL. PATCH token is Fake evidence only, not an invented wire field. The overview warns all-day differs from normal timezone rules and points to a detailed section that could not be retrieved here. A real adapter must verify that rule first; this DEV result makes no assertion of real all-day equivalence or real precision normalization.

## Test-first evidence

New tests were written against actual routes / receipt files / workspace lock / manifest writer / child process, with only the provider boundary replaced by Fake. Initial action/route behavior was red before core implementation; later mapping/recovery/confirmation and UI tests were added before their production changes. Regression checks for already implemented safe behavior were kept; no tests were removed or expected safety lowered.

Reproducible observed red→green examples from this run (all use repository root above):

| Command / stage | Red exit / reason | Green |
|---|---|---|
| `uv run pytest -q tests/integration/test_actions.py` during slices | exit1, missing routes / task behavior, then focused REST/time/hash/recovery/confirmation mismatches before fixes | exit0, final19 passed |
| `npm --prefix web test -- TasksPanel.test.tsx` before UI | exit1, missing task UI / behavior | exit0, final10 passed |
| same component command: unchanged task target review | exit1, 1failed/8passed, selected due review lacked target task | exit0,9passed after target rendering |
| same component command: changed progress project | exit1,1failed/9passed, expected version7 but old project version2 | exit0,10passed after selected-project version fix |
| `uv run pytest -q tests/integration/test_actions.py -k late_response` | exit1,1failed/1passed, late success overwrote independently resolved failed outcome | exit0 in final19 suite after terminal preservation |
| `uv run pytest -q tests/integration/test_actions.py -k concurrent_running` | exit1,1failed, running replay returned200 instead of202 | exit0,1passed, Location asserted |

Backend19 cover: unconfirmed zero writes / same intent replay / same title separate tasks; stale hashes / edited confirmation; explicit due / selected fields / already complete; invalid date/zone/bool; write-then-timeout and no-evidence unknown; concurrent durable running; **real subprocess os._exit(23)** after Fake remote write, restart unknown and month lookup; knowledge vs progress and version conflict; legacy candidate/source migration; corrupt receipt/summary; scopes / paging / errors / request mapping; wrong-GUID malformed PATCH unknown; canonical hash / string times / write-only reads; local progress lost receipt fault injection; summary deletion interruption; fresh confirmation / explicit outcome replay; late-response evidence and explicit terminal protection.

Frontend10 render actual TodayView / TasksPanel and Fake fetch boundary: explicit title/date/no invented date; final review→confirm→execute; refresh / completion only proposal; edit clears approval; unknown read-only evidence/no retry; independent progress; separate completion intent while editing; selected due-only PATCH; lost response uses same intent GET; target review; changed project version.

## Final verification commands at final code SHA

All commands below exited **0** (not merely launched). No dependency/version change; uv.lock is unchanged.

| Exact command | Result / warnings |
|---|---|
| `uv run pytest -q tests/integration/test_actions.py` | 19 passed;1 existing Starlette/httpx deprecation |
| `uv run pytest -q tests/integration/test_intake_review.py tests/integration/test_feishu.py` | 45 passed;1 same existing deprecation (M1 candidate / M2.1 regression) |
| `uv run pytest -q` | 126 passed;1 same existing deprecation |
| `uv run ruff check src tests` | pass |
| `uv run ruff format --check src tests` | 39 files formatted |
| `uv run mypy src` | 30 source files pass |
| `uv lock --check` | 32 packages resolved, lock valid |
| `uv build` | source distribution and wheel built successfully; ignored build output |
| `npm --prefix web run api:types` | OpenAPI / generated TypeScript regenerated, no residual generated diff |
| `npm --prefix web test` | 28 passed,7 files |
| `npm --prefix web run typecheck` | pass |
| `npm --prefix web run lint` | 3 existing effect warnings (ProjectsView/TodayView/AskView); no added warning |
| `npm --prefix web run build` | production build pass,26 modules |

## Real-browser DEV replay

IAB local browser, synthetic-only, code `a22bfeeb56bf837a9b86e4aaa15e0c1e9a426ea1` (its UI and normal execution implementation unchanged in final `a7f76e4`, which adds running202 header behavior independently tested). Runner command:

`SUMMIT_API_PORT=18793 SUMMIT_WEB_PORT=15173 SUMMIT_PROFILE_ROOT=/tmp/summit-m22-final-ui-profile uv run python scripts/run_dev.py`

Opened `http://127.0.0.1:15173/`; created `/tmp/summit-m22-final-ui-workspace`, name `M2.2 最终代码模拟`, clicked Fake authorization. New task title `最终代码模拟任务`; date choice explicitly `不设截止日期`. Final exact values visible; independent confirm visibly `已确认，尚未执行`; execute visibly `动作已成功`; refresh yielded one Fake provider task. Completion card showed exact target title; independent confirm/execute; refresh visibly `飞书已完成`. Browser warn/error logs `[]`. Screenshot emitted in tool conversation for created task / exact final values; no saved repository screenshot. This is developer replay, not independent QA.

Earlier evolving-tree replay also created a timed synthetic task, and the Fake remote file survived runner restart. The earlier receipt used a pre-final experimental fingerprint and was correctly blocked409 by final hash validation; final successful replay used a clean dedicated workspace/profile. No released receipt migration is claimed. Attempting all-day native date input through this IAB controller updated the date field but did not enable the React submit control; browser all-day flow therefore **NOT_RUN**. Service and component date tests are passing, but do not replace actual provider semantics or native date interaction acceptance. Timeout/concurrency/child-exit/monthly failure scenarios were verified by real service/file tests, not all replayed in browser.

## Files and handoff

Implementation: `api/app.py`, new `api/routes/actions.py`; `domain/models.py`; new `intake/actions.py`; `integrations/feishu/provider.py`, `fake.py`, new `tasks.py`; new `workspace/action_receipts.py`, `workspace/writer.py`; new `tests/integration/test_actions.py`; new `TasksPanel.tsx` / `TasksPanel.test.tsx`, `TodayView.tsx`, `App.css`, OpenAPI JSON and generated TS.

Documentation: README, API-v1 / WORKSPACE-v1, ACCEPTANCE C16–C18 replay, plan M2.2 checks, PROGRESS, LATEST-IMPLEMENTATION, this exact task report. Historical QA evidence is preserved; no DEV count changes independent QA status.

**Concerns / untested:** real account/scope, real GET/POST/PATCH, exact all-day timestamp rule and normalization, actual client_token evidence lookup, OS Keychain/configuration, real material/model quality, native/DMG/installation, five-day work and two-machine gates; IAB native all-day control needs independent browser QA. Existing1 backend+3 frontend warnings retained. Fake-only requested implementation is complete; independent review/QA and real gates remain. Temporary own runner is stopped before final handoff; no user services killed, no external push/PR.
