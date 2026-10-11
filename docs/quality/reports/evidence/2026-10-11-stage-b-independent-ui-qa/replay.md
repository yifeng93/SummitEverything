# Fixed 7f3119a independent offline UI replay

Checkout `/Users/yifengstudio/.codex/worktrees/qa-stage-b-sol-ui/SummitEverything`, detached `7f3119a511fda6f3d2771af4cf09fd9a9026edb7`.

Commands (all exit 0 except deliberate runtime stop):

```sh
uv sync --locked --group dev
(cd web && npm ci)
(cd native && swift build)
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" SUMMIT_API_PORT=18895 SUMMIT_WEB_PORT=15175 SUMMIT_PROFILE_ROOT="$PWD/.local/qa-ui/profile" uv run python scripts/run_dev.py
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/unit/test_provider_settings.py tests/integration/test_provider_settings_api.py
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run pytest -q tests/unit/test_feishu_credentials.py docs/quality/reports/evidence/2026-10-11-stage-b-independent-ui-qa/test_vault_faults.py
(cd web && npm test)
PYTHONPATH="$PWD/scripts/offline_guard:$PWD/src" uv run python .local/qa-ui/disk-assert.py
```

CUA IAB tab at `http://127.0.0.1:15175`, hidden because subagent cannot enable visibility. It is an actual browser, not component simulation. Created library `.local/qa-ui/workspace` → Projects: new synthetic line/project → Today: text `合成资料：会议室可容纳 24 人，预约时段为周五下午。仅用于离线 QA。` → save intake → select source → Fake organize → open draft → change title/save → explicit approval → Knowledge: index plan/confirm → query `合成会议室可容纳多少人？` → cited synthetic paragraph.

Today Fake authorize → create synthetic task, explicitly choose no date → review → confirm (no execution) → execute → refresh → complete → review → confirm → execute → refresh completed. Settings save Real and nonsecret `cli_synthetic_independent_ui`; no secret entered; smoke remains 1 each. Today Real new task disabled, local progress enabled. Local progress chosen synthetic project → review → confirm (manifest byte-for-byte unchanged) → execute (progress_version 0→1).

Network mechanism: uvicorn's actual access log and parsed `loopback-api-requests.json`, 132 inbound API requests. 2 initial GET workspace 409 are expected no-library responses; all other recorded requests are <400. This is not HAR, does not capture bodies, does not claim full browser egress capture. Browser resource enumeration attempt was unavailable in read-only CUA evaluate scope (`performance` undefined); no resource-list claim. No business/provider HTTP was substituted in this GUI flow; Fake providers used the normal runtime. Python offline guard was active, blocks external DNS/socket and OS Keychain. Setup package installs are not runtime-provider calls. Console collection via `tab.dev.logs(warn/error)` was `[]`.

Stopped browser runner with Ctrl+C (exit241); verified ports absent, then built ignored test-only `.app` wrapper. Normal bundle `local.summit.stageb.independent.ui.qa`, wrapper PATH includes `/Users/yifengstudio/.local/bin`, `/usr/local/bin`, `/opt/homebrew/bin`, system dirs; PYTHONPATH guard+src, ports18895/15175, same isolated profile. Binary is exact checkout `native/.build/debug/SummitEverything`, not installed app. CUA launched app, native Go To Folder selected only `.local/qa-ui/workspace`, open existing, Today Real disabled writes, settings persisted. Native inherited UUID equals health run_id; selected process environment only (session token deliberately omitted) in native-identity.json. Last-window close via CUA → no exact-checkout process nor port listener. Test-only failure bundle `local.summit.stageb.independent.failure.qa`, ports18896/15176, missing uv PATH → readiness error captured then OK → no remnants. Browser test tab closed.

Native runner intentionally discards server output, so native network logs NOT_CAPTURED. Native identity, UI and disk evidence remain separate from browser's access log. No OS Keychain, real OAuth link click, account, material, calendar/task read/write, real model, DMG or installation acceptance. B03 app-only configured-calendar actual GUI NOT_RUN (no fixture credential inserted); official OAuth link actual external-browser routing NOT_RUN, existing component tests verify safe URL path. Synthetic credential denial/locked/corrupt/restart covered by real vault/store with MemorySecretBackend/fault backend only.
