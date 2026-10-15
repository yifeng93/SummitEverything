# Frontend D Developer evidence index

Product SHA: `876008e1d33420f57fb31772c76e471379e6b98d` (clean, fixed). This index points to ignored local evidence; it intentionally excludes profiles, raw defaults, credentials, traces, and native screen captures that could expose setup values. It records Developer evidence only; independent QA and Sol gate remain outstanding.

## Exit summary

| Check | Recorded result | Raw evidence location |
|---|---|---|
| Web tests | `npm --prefix web run test`: 204/204, exit 0 (rerun for this report) | command output in task record |
| TypeScript, lint, production build | each exit 0; lint has 2 existing React effect warnings; build retains bundle-size warning | Developer run logs in `.local/dev/frontend-d/` |
| Focused confirmation / streaming / metadata and runtime canary tests | exit 0 | `.local/dev/frontend-d/` |
| Shell E2E and C browser flow | 2/2 and 1/1 | `.local/dev/frontend-d/` |
| 10 controlled mutations | all red sidecars exit 1; all restored green sidecars exit 0 | `.local/dev/frontend-d/mutation/` |
| Guarded Python | 661 passed | Developer run log in `.local/dev/frontend-d/` |
| Ruff check / format check / mypy; uv lock/schema gate | exit 0 | Developer run logs in `.local/dev/frontend-d/` |
| Swift tests | 5/5 | Developer run log in `.local/dev/frontend-d/` |
| Release candidate build | exit 0, forced frontend rebuild | build worktree `.local/dev/frontend-d-final/release-build.{log,exit}` |
| Initial and restart native runtime preflight | exit 0; allowlisted PID/profile/offline guard/port/health identity/static-root fields only | build worktree `.local/dev/frontend-d-final/{native-preflight,restart-preflight}.{json,log,exit}` |
| Independent CSS zoom simulation | exit 0; 2× text/button rect height, focus reachable, no root horizontal overflow | build worktree `.local/dev/frontend-d-final/zoom-proof.{mjs,log,exit}` |

## Viewport and package evidence

- Browser shell matrix: 78 PNGs in `.local/dev/frontend-d/browser-shell-final/`, with 320/390/768/960/1280 CSS viewport checks in light/dark mode, reduced-motion screenshots, measurements, and focus/disabled/dialog assertions. SHA-256 of `measurements.json`: `11ea93ebaac6a64c23941fc75de13caa20da19096e92dcea60a75d6614f6cfdf`.
- Projects/Reader/Ask matrix: 48 PNGs in `.local/dev/frontend-d/browser-projects/`. SHA-256 of `measurements.json`: `d062dfe309779e8719c5e4bdaf2b094d44fe0207c89e8a049adeae0f40160089`.
- Earlier 200% labels in matrix artifacts correspond to 640 CSS-pixel effective-width reflow, not true page zoom. The separate proof uses an offline representative page and CSS root zoom; it is not a native WKWebView pageZoom result. The old ineffective body-zoom diagnostic is retained: SHA-256 `05cefb654d89938c88bdbd1cefe713f8ff7a572bb6794fbb220355c4d4c2c5e1`.
- Managed build tree is `frontend-d-final`; exact candidate manifest: `.local/dev/frontend-d-final/candidate-manifest.json` (SHA-256 `13e0bc63c466fcd9f31929f2e4d7e0d74768581a96e97edd44c6c6af31934d0c`). Build log SHA-256: `2cee76ddc767aea146e2d777cc7918c29532a2863d8c06127220914ada3a2f30`. Restart preflight SHA-256: `c28e8e9814ef8c152c718f87e8d44df68d53b047f345a5a7c35a4b3e7038528d`.
- CSS zoom proof screenshot SHA-256: `0c08f6575e1d6fad75d31658c9abed8a55f1543361333a168e59c0700e59946e`.

## Native GUI handoff

The fixed candidate was used with an isolated temporary Fake profile for quick-note/file import, source organize cancel then confirm, draft review and formal confirmation, Fake index, query citation and Reader. Same-candidate restart retained workspace data and allowed opening the isolated workspace again. Restart displayed onboarding step 2 again; that completion/persistence issue is **UNVERIFIED** and under independent QA review. Native `pageZoom=2` is **NOT_RUN**. The app was quit; this run's native/backend PIDs stopped and port 18793 was released. The CUA interaction transcript is in the current task history; no native screenshot was copied into tracked evidence.

Do not reuse the Developer temporary profile for QA. QA must use a fresh `NSTemporaryDirectory()` child and the exact candidate path from the manifest. The package is ad-hoc and not notarized, so it is only an internal candidate.
