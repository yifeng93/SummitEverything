# Native Internal candidate UI observations (Developer)

Date: 2026-10-14. Fixed candidate source SHA: `fe473399bbc5dcd001a3bc2e5156fdbbb2f4148b`.

This is a Developer observation record from CUA AX state and screenshot of the actual WKWebView in the clean Internal App. It is not an independent QA result. Screenshot bytes were displayed in the CUA session but were not persisted in the repository.

The first attempt launched the executable inside the `.app` directly from a shell. Settings displayed “钥匙串可用.” Later process inspection showed the app may be reactivated by LaunchServices with a different environment. The first window’s effective profile root and whether any macOS Keychain read occurred remain **UNVERIFIED**. The default fallback path from the Swift source is `~/Library/Application Support/SummitEverything Internal`; only its directory modification time was read (`2026-10-13 14:56:23 +0800`). No file in that directory was read, written, removed or cleaned. The old attempt is not evidence of zero Keychain access.

The final attempt used `open -n` with `SUMMIT_OFFLINE_GUARD_ACTIVE=1` and a fresh profile directory under Darwin’s temporary directory. Log `36-native-offline-launch-verified.log` records the actual `open` exit and safe process checks: the native process flag is exactly `1`, the backend process flag is exactly `1`, and each process’s effective profile root resolves to the requested temporary directory. A synthetic workspace manifest in `.local/dev/m42-package-a/final-20261014/browser-workspace-verified/` confirms the UI selected the test workspace.

Observed in the candidate UI:

- Settings displayed “钥匙串不可用”; key save and delete buttons were disabled.
- Fake mode displayed an explicit synthetic Feishu label. Simulated authorization enabled Fake metadata and calendar actions; the sample calendar was empty.
- One synthetic “模拟会议” item was imported to a local inbox / review-needed state.
- The UI review stopped after import. Real organization, editorial approval, indexing and query UI flows were not exercised in this native run.
- No real plan was confirmed, no credential was entered, and no real provider/Feishu request was issued during the correctly guarded run.

DevTools browser network and console inspection was NOT_RUN. The command-line and automated evidence is in this directory; UI observations remain a manual Developer record for the fresh QA to independently reproduce.
