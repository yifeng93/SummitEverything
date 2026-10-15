# Frontend C QA evidence index

Fixed product SHA: `1b1efda0e2cbfe9df49c1541101d89dc2fd3b60c`

QA source: `/Users/yifengstudio/.codex/worktrees/frontend-c-qa-initial/SummitEverything/.local/qa/frontend-c-initial/`

The original report, raw gate logs, exit sidecars, Playwright harness, screenshots, and manifests remain in the ignored `.local/qa` directory above. This tracked index contains only classifications and hashes; it does not copy profile state, tokens, traces, screenshots, or raw logs.

## Gate classification

| Gate | Final result | Evidence |
|---|---|---|
| `npm ci` | PASS, exit 0 | `gates/npm-ci.exit` |
| Web tests | PASS, 190 passed / 4 todo, exit 0 | `gates/web-test.exit`, `gates/web-test.log` |
| Typecheck / lint / build | PASS, each exit 0; 2 lint warnings and one large-chunk notice recorded | `gates/web-typecheck.exit`, `gates/web-lint.exit`, `gates/web-build.exit` |
| Focused C components | PASS, 31 tests, exit 0 | `gates/focused-c-tests.exit` |
| Project / Reader / Ask matrix | PASS, 40 screenshots, overflow 0 | `gates/view-matrix.exit`, `view-matrix/measurements.json` |
| FastAPI + Fake citation update | PASS, 1/1; external requests 0 | `gates/fastapi-flow.exit`, `fastapi-integration/frontend-c-flow-manifest.json` |
| Project return state | Initial attempt FAIL (fixture shape), retry FAIL, final fixed harness PASS, exit 0 | `gates/project-return-state.exit`, `gates/project-return-state-retry.exit`, `gates/project-return-state-final.exit` |
| Project journal progress invariant | PASS; `progress` and `progress_version` unchanged | `gates/project-journal-progress.exit`, `test_project_journal_progress.py` |

The two nonzero project-return attempts are preserved and classified as QA harness failures. Only the final rerun is the passing evidence. UI return-state and backend journal/progress checks are separate tests, not one end-to-end claim.

## SHA-256

| Original artifact | SHA-256 |
|---|---|
| `QA-REPORT.md` | `263dd8e1e4bfe99235ffdd130bb958db96ca8710d0581020dec7e131b3986a72` |
| `gates/web-test.log` | `9a50572aa7a6dbaacfa02fbd6c49e2a3e1d60b3ee7f9f88b7df897b1647dc9a1` |
| `gates/view-matrix.log` | `67a7ab02aa5cae9f73956a56fca2917511791dffc498eaeb9b1ecbbd7ccfebc6` |
| `gates/fastapi-flow.log` | `8405409fb673cb9e3a937337be96736df83ccb69b659e5ebacb8e5f372037eb1` |
| `fastapi-integration/frontend-c-flow-manifest.json` | `0a9ced7e8f7649a433f0477ea3dc23e5da55e6aee9adadfa1f7ba36e8416cb7b` |
| `gates/project-return-state.log` (initial harness failure) | `930edde9d9ce2ce4238ef3901bd997e3a097a66f604ec857ebd0a3b9381dfbfb` |
| `gates/project-return-state-retry.log` (retry harness failure) | `0356ae325d7ea6285ac3c697f416758d9135913a362ee1383ab41c34f2fe921c` |
| `gates/project-return-state-final.log` | `e685ad2f55486c443aa45b125538332c113c7ecce85e9ab525aad12f4ee7d470` |
| `gates/project-journal-progress.log` | `695009df3efb8a1da179c02377c5cec83b90b5069eda65de8f1a745292b8f2e5` |

The original QA report SHA-256 is recorded in its entirety. Exit sidecars and selected safe summary logs remain available at the QA path; the original QA report is the authority for full scope and limitations.
