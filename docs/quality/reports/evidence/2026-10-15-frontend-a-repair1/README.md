# Frontend A repair1 evidence index

This archive describes the development evidence for fixed product SHA `9c33a9dde3080fff3e3b3dd8a4193589ef52575f`, based on baseline `e84e9e5a56475a19f68ca1a684366fba7f9fee83`. It is not an independent QA verdict. Fresh QA is running in a separate worktree; the gate remains PENDING until Sol records a decision.

`command-results.json` records the exact command strings, observed exit codes, test counts, and raw log locations. `evidence-manifest.json` lists SHA-256 and byte size for 93 raw log, exit-code, harness, request-manifest, measurement, and screenshot files under the developer worktree's `.local/dev/frontend-a/repair1/`. Generated virtualenvs, runtime profiles/workspaces, browser caches, and build output are excluded. The raw developer evidence remains in that local worktree and is not duplicated into Git.

The three repair screenshots are `mock-evidence/onboarding-missing-key-guidance.png`, `mock-evidence/settings-ai-per-capability.png`, and `mock-evidence/settings-feishu-stale-read.png`. The mock viewport matrix covers widths 320, 390, 768, 960, and 1280 in light and dark themes. FastAPI/Fake request evidence is `fastapi-evidence/fastapi-request-manifest.json`; it records an isolated synthetic workspace and no external attempts.

Three isolated mutations were detected (their targeted tests exited 1) and each changed source file was restored byte-for-byte. The complete run and post-restoration checks are indexed in `command-results.json`. Earlier harness setup mistakes and retries are disclosed there rather than counted as passing evidence.
