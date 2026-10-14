# M4.2 Package A repair round 1 evidence map

This directory holds the unchanged developer raw evidence from the earlier `bc5018d` candidate and the additional Native repair evidence for fixed product source SHA `419bb865b334389d1efd0f4a1a855cd0d5324d28`. Read the report `../../2026-10-14-M42-PACKAGE-A-DEV-REPAIR1.md` before interpreting this mixed-candidate archive.

## Candidate identity

- Final QA target source SHA: `419bb865b334389d1efd0f4a1a855cd0d5324d28`.
- Final App: `/Users/yifengstudio/.codex/worktrees/m42-readiness/SummitEverything/.local/dev/m42-package-a/repair1-empty-feedback/artifacts/SummitEverything Internal 419bb86.app`.
- Final DMG: `/Users/yifengstudio/.codex/worktrees/m42-readiness/SummitEverything/.local/dev/m42-package-a/repair1-empty-feedback/artifacts/SummitEverything-Internal-419bb86.dmg`; SHA-256 `2e176a2d27f13821f2f82768966719408780c0ed963ee9d9e4413b75ff16f14a`.
- App relative-path/content manifest SHA-256 `9bb4d2c6e511e47812db8cca6e1af56d4dd248e1ca177a92525e1f7271c8c7f0` (156 files), full manifest `candidate-419bb86-app-SHA256SUMS.txt`; build identity and all final candidate exits are in `candidate-419bb86-*` files and `candidate-419bb86-commands.json`.
- `src/`, `web/`, and `uv.lock` match implementation source `4c6b0bd`; only the subsequent Native source/tests change is under review. This comparison does not say documentation is unchanged.

## Raw evidence map

- `candidate-419bb86-*`: new App/DMG build, integrity, signature and DMG verification, copied-candidate operation, per-file App hashes.
- `ui-419bb86-*`: LaunchServices guarded launch and process identity; both native and backend recorded guard `1` and fresh profile canonical match. `ui-419bb86-native-selection-feedback.txt` records actual WKWebView native file dialog selection, generic rejection prompt for a valid+empty mix, cancel without prompt, and successful subsequent valid multi-file import. The current session exposed the screenshot visually but did not provide a supported save-to-file method; this is explicitly recorded, and no new-candidate screenshot is claimed.
- `swift-tests-419bb86.*`: full Native suite on the final product SHA (5 passed).
- `source-tree-comparison-419bb86.txt`: exact command and exit confirming Python/frontend/lock tree equality with `4c6b0bd`.
- Existing non-suffixed files: previous `bc5018d` candidate full automated checks and actual UI records. In particular, `ui-exact-qa-*` demonstrates the original exact question/body flow on `bc5018d` only, not on the final `419bb86` candidate. The fresh QA must repeat these checks on `419bb86`.
- `SHA256SUMS-bc5018d-pre-native-fix.txt`: preserved earlier manifest bytes. `SHA256SUMS.txt`: current complete relative-path manifest for all files in this directory except itself.
- `prior-evidence-prebuild-sha256sums.txt`: pre-build tracked evidence SHA list used while temporarily staging those same bytes under ignored `.local`; restored copies were checked against this list successfully. It proves the old evidence files were restored without edits before appending 419bb86 records.

## Limits

Developer evidence is not a QA verdict. Partial-failure/failed-only retry on an actual UI batch, Real JournalAssist provider/network, real material/services/Keychain, production install/signing/notarization, five-day/two-device use, and release remain NOT_RUN; runtime model metadata remains UNVERIFIED. See the handoff report for full scope and limitations. The initial QA report and its original 34-file evidence bytes are separate and unchanged.
