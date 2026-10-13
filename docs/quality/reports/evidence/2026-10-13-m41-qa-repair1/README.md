# M4.1 repair1 QA evidence

This evidence belongs to the independent QA run for source SHA `3f6eaa408a8860ff5a438be8a874a2c3904733e4`. See the adjacent report `docs/quality/reports/2026-10-13-M41-INTERNAL-APP-QA-REPAIR1.md` for verdict and acceptance mapping.

## Candidate identity

- Candidate app: `/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/repair-1/artifacts/SummitEverything Internal fix1 3f6eaa4.app`
- Source SHA in `Contents/Resources/build-info.json`: `3f6eaa408a8860ff5a438be8a874a2c3904733e4`; dirty `false`; build `20261013T060945Z-577f0cc805f2`; frontend `577f0cc805f2f7727add28c1e0d4714c0c15040fa7c094fce7e6234c65239fc6`; dependencies `2aa53e0cf1698d768c2f3f06995a9fd9dcd680003f598a94ca7bc1e7a057fe5f`.
- Tree digest method in `harness/verify_tree_digest.py`: sorted relative path bytes, NUL, then raw SHA-256 digest bytes for each file. App and read-only mounted DMG each had 156 files and digest `1e58574ea68174ffa20f77b7838796d1c180c35cab7e43b66c274a3587b2f4eb`.
- Main executable SHA-256: `b23fa16046cfe39c1aa8885f08b6bbbfe1b90e0d9744919f91f950e42f60cc64`.
- DMG: `/Users/yifengstudio/.codex/worktrees/m41-internal-app/SummitEverything/.local/dev/m41/repair-1/artifacts/SummitEverything-Internal-fix1-3f6eaa4.dmg`; SHA-256 `554b7ab3d2bc22728ec6484d1109d9bee8b149814aac556571e45a1d1d7f59d8`. Signature is ad hoc; `spctl` returned rejected. Developer ID/notarization/Gatekeeper acceptance were not tested.

## UI and process record

Controlled app copies and test profile roots were beneath `/var/folders/yp/7n9pls2j2rl0sz9vmfdf4z6r0000gn/T/`, obtained from `getconf DARWIN_USER_TEMP_DIR`. Every controlled valid App launch used an empty `PATH` and `SUMMIT_INTERNAL_TEST_PROFILE_ROOT` pointing inside that temporary root. One invalid earlier CUA auto-launch had no test-profile environment; its circumstances are retained under `logs/attempts-and-tool-errors.log`, and its synthetic default profile was not inspected or modified. The first full UI run used PID `89086`; the same copied bundle/profile restart used PID `89313`; the menu-Quit run used PID `89393`; missing-backend UI used PID `89589`. Shell `lsof` confirmed the isolated profile `instance.lock`; after expected quits the exact App/backend PIDs and 18793 listener were absent.

For the full flow, the real native workspace picker selected `/var/folders/yp/7n9pls2j2rl0sz9vmfdf4z6r0000gn/T/m41-qa-repair1.1intRJ/workspace`. The upload button opened the actual macOS Open panel. Cancel left inbox count at 0. Selecting `fixtures/qa-upload.txt` and `fixtures/qa-upload.md` produced two pending items. Both were organized with explicit Fake actions, reviewed and approved separately, indexed after an explicit index action, then queried. On restart, sources, index (2 pages / 2 chunks), and two history messages remained.

Wrong-identity rerun: persistent synthetic listener PID `89802` owned `127.0.0.1:18793`; test App PID `89940` held `/var/folders/yp/7n9pls2j2rl0sz9vmfdf4z6r0000gn/T/m41-qa-repair1.1intRJ/wrong-identity/profile-root/instance.lock`. The native alert displayed the expected local-service-not-ready / candidate-or-port-mismatch text. CUA acknowledgement returned `procNotFound`, and a later key action reported the app inactive; I terminated only PID `89940`. The listener remained bound/alive after that termination. I then stopped only listener PID `89802`; no process remained on port 18793. Raw request logs are retained, including an invalid earlier attempt whose listener died with its shell and whose requests must not be attributed as a valid run.

Missing-backend test moved only the backend directory from a copied app to a sibling temporary location. The real native alert was observed; after acknowledging it, the test app exited and its port was clear. The developer worktree artifact and installed applications were not modified.

## Logs and harnesses

- `commands-results.json` is the structured command/exit/status ledger; if a complete shell wrapper was not retained, it explicitly marks that command as non-exact instead of inferring arguments.

- `logs/pytest.log`, `logs/m4-api-release-sse-tests.log`, lint/typecheck/build logs and package checks preserve actual output for source and web checks.
- `harness/test_delayed_native_readiness_qa.py` records health-before-root with a 4-second synthetic backend delay; `logs/delayed-readiness.log` has app PID `90112`, temp root `summit-m41-delayready-b5f0a939`, observed path order, exit `-15` (intentional harness stop), and harness exit 0.
- `harness/test_sigkill_cleanup_qa.py` records a fresh copied app with backend PID `90391`, app PID `90389`, exact profile under temp root `summit-m41-sigkill-9b624bf2`, and successful EOF cleanup after parent SIGKILL; see `logs/sigkill-cleanup.log`.
- `harness/verify_bundle_tamper.py` and `logs/bundle-tamper.log` preserve the copied static-resource tamper reproduction; embedded backend exit was 1 and no readiness listener appeared.
- `logs/dmg-*.log`, `logs/app-tree.log`, and `logs/app-executable-sha256.log` preserve hash, read-only mount, signature verification, tree comparison, `spctl` assessment, detach and executable checks. `spctl` exit 3 is recorded without bypassing Gatekeeper.
- `logs/native-app-*.log`, `logs/missing-backend-native-app.log`, and `logs/wrong-identity-*` preserve startup warnings and the wrong-identity request traces. The `sandbox_extension_issue_file_to_process` line is a system/tool warning; it did not prevent the separately verified process/readiness/UI behavior.
- `harness/qa_listener.py` is a QA-only loopback listener; it binds only `127.0.0.1:18793` and returns synthetic mismatched identity data in the wrong-identity mode.

`logs/final-cleanup.log` records the last PID, port, and mounted-volume check. `SHA256SUMS` covers every file in this evidence directory except itself. No real credential, random app session token, user business file, Keychain data, or external service response is present.
