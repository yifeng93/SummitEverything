# M3 Package 2 Extra 1 QA — 2026-10-12

## Verdict

**FAIL (package gate).** The two extra1 fixes pass independent end-to-end checks. One separate C19 defect remains: when a fresh, ready index has no eligible answer evidence, the API reports a stale-cache/qualification failure as the missing information. This is a P2 user-facing diagnostic error; the response contains no citations, source statements, inferred facts, advice, or fabricated numbers, and does not call the provider.

- Fixed tested checkout HEAD: `507cc1f197ce3af3b22aa53c98148e4ca45ff935`
- Product source SHA: `bb997a42ed1d218e10527e3e07e6c587fc9929f6`
- Tested product tree: `2289109bfbb2230c55d16cb2491f402c515dec46`
- Checkout tree at test start: `e0db3844c58b4a985a247063d8525e6005aa2306`; only handoff/report documentation differs from source SHA. The product source, tests, generated API files and lockfiles were unchanged by QA.
- Evidence directory: [`evidence/2026-10-12-m3-package-2-qa-extra-1-507cc1f`](evidence/2026-10-12-m3-package-2-qa-extra-1-507cc1f)

## Results by acceptance area

- **PASS — C13 history citation state and page eligibility.** In the real browser UI over synthetic workspace pages, an approved superseded citation opened as “已确认 · 已被替代” with historical-only guidance. After a synthetic external hash change, the page became “待确认 · 已被替代”; reconfirming the new hash returned it to “已确认 · 已被替代” and did not promote it to CURRENT. Approved invalid history opened as “已确认 · 已失效” with historical-only guidance. CURRENT retrieval excluded invalid/superseded content; HISTORY returned it with its validity. The old citation became unavailable after its hash changed; the endpoint returned HTTP 409 for the old expected hash.
- **PASS — PageWriter invalid-page reconfirmation.** Explicitly confirming an invalid page updated its approval proof to the matching content hash while keeping validity `invalid`; it remained excluded from CURRENT and available only in HISTORY.
- **PASS — C20 memory provenance and promotion.** In the browser, the user-authored preference was explicitly attested, created as pending, edited, and separately confirmed. A following provider request contained the confirmed memory. API negative controls rejected bare quotes, Markdown blockquotes, material quote substrings, assistant text, forged message IDs and false user attestation (HTTP 422). Positive controls accepted source-attribution wording, an internally quoted term, and a personal preference after a material-attribution paragraph. Pending candidate text did not enter the active provider prompt.
- **PASS — C14 request replay, cancellation and restart recovery.** Stable request-ID replay after role/memory edits returned the same event semantics without another provider call; a different payload under the same ID returned HTTP 409. Cancel returned HTTP 202 and terminal `canceled` with zero answer chars. A synthetic partial stream was killed and restarted; history restored `interrupted` with the exact partial text/event counts and replay did not automatically resend it.
- **PASS — C21 profile/workspace isolation.** Two profile roots sharing a workspace UUID remained isolated for conversation history, roles, memories and index state. Switching between workspaces in one profile restored only the selected workspace's state. This used isolated synthetic profile/workspace directories.
- **PASS — C19 comparison and missing-data safety.** A cross-page comparison over synthetic current pages returned evidence from both requested subjects with the response sections separated. The no-evidence probe produced no citations or unsupported values and did not invoke the provider.
- **FAIL — C19 no-evidence diagnostic.** The same no-evidence probe mislabeled the missing basis as stale cache or failed qualification even though index status was ready and had zero stale pages. Details below.
- **PASS — automated README matrix.** `uv run pytest -q` (407 passed); `uv run ruff check src tests`; `uv run ruff format --check src tests`; `uv run mypy src`; `uv lock --check`; `uv build`; `npm --prefix web run api:types`; `npm --prefix web test` (55 passed); `npm --prefix web run typecheck`; `npm --prefix web run lint` (exit 0, two warnings); `npm --prefix web run build`. Full outputs and exit records are in `raw-logs/`.
- **NOT_RUN — DevTools console/network inspection.** The available browser automation exposed page accessibility state but not DevTools instrumentation.
- **NOT_RUN — live external integrations, real materials/credentials/Keychain, native or DMG install, five-day use, and two-machine gate.** These were outside the authorized offline synthetic scope.
- **UNVERIFIED — runtime/model metadata exposure.** No runtime metadata was actually exposed during this run.

## C19 defect reproduction

Harness: `evidence/.../harness/no-data-diagnostic-extra1.py`; captured response: `evidence/.../harness/no-data-diagnostic-extra1-results.json`.

1. Read `GET /api/v1/index/status`: HTTP 200, state `ready`, `pages=7`, `chunks=7`, `current_pages=7`, `stale_pages=0`, fingerprint `summit-fake-embedding-v1`.
2. Submit `POST /api/v1/queries` with synthetic question `为风铃工程的彩色牙刷储存规则提出方案，并列出缺失信息。` and `answer_mode=plan`, `purpose=current`.
3. Actual result: HTTP 200, SSE `status`, `delta`, `completed`; completed `index_status=ready`, text says there is no confirmed basis and a supported plan cannot yet be proposed, but `missing_information` is `已缓存的资料版本与当前工作库不一致，或当前资格检查未通过。` Citations, `source_statements`, `inferences` and `advice` are all empty. Provider call counter remained 19 before and after.
4. Expected: indicate that the requested fact/rule is absent from eligible confirmed material (or otherwise describe the actual missing information); do not report an index/cache mismatch when status is fresh and ready.

This is a misleading diagnosis, not evidence leakage: the response cites no content and invents no numeric fact. In the tested source, the no-citations branch in `src/summit_everything/retrieval/query.py` (around lines 352–382) hardcodes the cache/qualification text. No code was changed by QA.

## Reproducibility and cleanup

The evidence uses only generated synthetic fixtures, a fake embedding implementation and an in-process mock provider. The exact probe scripts, distilled payload results, UI observations, full command logs and exit codes are retained in the evidence directory. No real user material or credentials were used.

All QA services were stopped; listeners on ports 5173, 18793 and 18795 were absent at cleanup. QA left no tracked product, test, API generation or dependency-lock changes. The only repository changes are this report and its evidence, committed separately from the tested product SHA.
