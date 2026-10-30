# Independent QA report: external Markdown discovery repair

- Candidate: `4358c7b2b410d8c5bcc6ab4dd7d219ce9d349a25`
- Required base: `417117401a0a165b14a67abd1e8b27d1ea76d4ca`
- Checkout: detached worktree, clean tracked tree at completion
- Scope: ADR 0035 external Markdown revision discovery, normal shell recovery, project inline reader, overview read-only state, approval/index/retrieval path
- Environment: isolated synthetic workspace and profile under this worktree's `.local/qa`; real FastAPI, filesystem reader/writer, SQLite, local cached BGE model; DeepSeek boundary mocked; no actual user library, Keychain, Feishu, or paid model call

## Results

| Scenario | Result | Evidence |
|---|---|---|
| App / Projects / PageReader / Approval component coverage and two UI contract guard suites | PASS | `logs/ui-components.log`: 6 files, 100 tests |
| Work log and draft input persistence component checks | PASS | `logs/journal-draft-preservation.log`: JournalDialog and DraftReview, 7 tests. `App.shell.test.tsx` also covers a draft edit across refresh and confirmation before workspace switch. These are component/shell checks, not an external-revision browser scenario. |
| Web typecheck and production build | PASS | `logs/typecheck.log`, `logs/build.log`; build retains existing >500 kB chunk advisory |
| Revision API, workspace mutations, qualified retrieval backend checks | PASS | `logs/backend-revision-reader-retrieval.log`: 74 passed |
| Actual browser: first-use synthetic library, confirmed/indexed page, prior west-gate answer, external atomic replace with east-gate text, automatic pending state, stale-index exclusion, UI confirmation, incremental index update, old citation marked updated, new east-gate answer | PASS | `logs/external-watch-flow.json`, `logs/provider-requests.json`, `logs/index-status-responses.json`, `screenshots/05-confirmed-indexed-reader.png`, `07-external-change-pending.png`, `08-confirmed-current-version.png` |
| Actual browser project inline: external new Markdown appears without manual refresh/navigation, body is pending and read-only; invalid UTF-8 becomes unavailable; same file repaired and automatically recovers; selected file deleted and automatically becomes unavailable | PASS | `logs/external-file-lifecycle.json`, `screenshots/09-external-file-lifecycle.png`; the same page remained selected through invalid-file recovery and deletion |
| Actual browser project overview | PASS, limited | Same project view's overview empty state was checked for absence of textarea/input/contenteditable. This did not test a populated overview's scroll/receipt preservation; that behavior remains outside this independent browser run. |
| External revision request from old workspace arriving after a workspace switch | NOT_RUN | No matching precise race test was found in this scoped suite. Do not infer this from general refresh or unrelated Feishu workspace tests. |
| Real model quality, Feishu, Keychain, real user data/profile, installed DMG, dual-device / five-day acceptance | NOT_RUN | Out of this authorized synthetic QA scope |

## Observations

The primary browser workflow ran with a 1440×960 viewport, one Playwright worker, local API on 6185 and Vite on 8895. Browser requests to external origins were blocked; `logs/browser-network.json` records no external attempts or page errors. The automatic pending page had `approval_state: invalid`, and the existing index reported `stale_pages: 1`, `current_pages: 0` until explicit confirmation. Confirmation returned `index_update: updated`; the index returned to `ready`, and the prior citation availability became `updated`.

There were two harness-only failures before successful runs. The first wrapper invocation could not resolve `@playwright/test` from the `.local/qa` config; rerunning with `NODE_PATH=web/node_modules` succeeded. The first lifecycle assertion expected the tree button's accessible label to contain “待确认”; the UI intentionally labels that button with the title only. The assertion was corrected to verify pending status in the reader and non-confirmed API state. The failed run and trace remain in `logs/playwright-wrapper.stdout.log` and `logs/playwright-lifecycle.log`, plus Playwright output. Neither was a product defect.

No product failure was observed in the executed scope. This is a bounded synthetic-flow PASS, not a full acceptance or release PASS.

