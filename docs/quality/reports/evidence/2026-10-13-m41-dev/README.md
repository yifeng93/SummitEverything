# M4.1 Developer evidence bundle

Evidence is for product source SHA `b9321d64c5404feadffebc05964793e9402a07aa`. This bundle contains logs and text manifests only; the `.app` and `.dmg` binaries remain under the ignored `.local/dev/m41/artifacts/` path recorded in the DEV report. `manifests/evidence-manifest.json` records source and tracked SHA-256 values, command outcomes, and the artifact identities.

The tracked SSE red log is a sanitized copy: its one synthetic session token literal is replaced with `<SYNTHETIC_SESSION_TOKEN_REDACTED>`. Its original remains untouched in `.local/dev/m41/raw-logs/`; the evidence manifest records both hashes. Other log bytes are copied as captured. No real credential or runtime token is present. Native PID, port, and isolated temporary paths are retained because they identify the owned process cleanup and test boundary.

| Evidence | Recorded result |
|---|---|
| `logs/guarded-pytest-final.log` | guarded pytest: 499 passed, 1 warning, exit 0 |
| `logs/final-static.log` | ruff, format, mypy, uv lock check, diff check: exit 0 |
| `logs/gates-full.log` | preserves first 5-test red run and following green gates with per-command exit codes |
| `logs/sse-real-query-exception-red.log` / `green.log` | real HTTP SSE test before/after task-exception-consumption fix; exit 1 / 0 |
| `logs/dev-runner-ctrl-c-baseline.log` / `green.log` | baseline startup interrupt exit 241; corrected tracked regression 4 passed, exit 0 |
| `logs/build-final-b9321d6.log` | clean fixed-SHA App/DMG build, exit 0 |
| `logs/packaged-backend-smoke-final.log` | moved bundle backend smoke with empty PATH, exit 0 |
| `logs/final-artifact-verification.log` | codesign, DMG verify, architecture, plist and DMG SHA checks |
| `logs/native-ui-final-observations.txt` | actual copied native App UI, isolated profile/workspace, persistence, exit and PID/listener observations |
| `logs/swift-build-final.log` | Swift release build, exit 0 |
| `manifests/build-info.json` / `dependencies.json` | exact package build identity and dependency inventory |

`SHA256SUMS` covers all files in this directory except itself. To verify from the repository root, run `shasum -a 256 -c docs/quality/reports/evidence/2026-10-13-m41-dev/SHA256SUMS`.
