# Round 3 observation and cleanup record

- Candidate source: `32da67e9c0280e3dae18fd374e30c925565b0b82`.
- Browser: `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` with dedicated user-data directory `.local/qa/stage-a-final-round3/chrome-profile`, `--remote-debugging-port=19229`, and URL `http://127.0.0.1:15218/`. This is a direct Chrome/CDP session; it is not CUA IAB and not the native app WebView.
- Capture: CDP `Log`, `Runtime`, `Network` enabled before full reload; prior backlog discarded; reload plus 1.8 seconds; sanitized export has 82 request/response events (41 each), 0 warning/error/exception events, all destinations loopback `127.0.0.1:15218`, response status 200. This only describes the capture window.
- Process identity immediately before shutdown: Chrome PID 37419, parent 35223, full args include the unique QA profile and port 19229; API PID 37873 (`uvicorn summit_everything.api.app:app --host 127.0.0.1 --port 18818`); Vite PID 37888 (`.../web/node_modules/.bin/vite --host 127.0.0.1`, listening on 15218). The parent runner/session was 65855. These exact owned processes were stopped after capture.
- Post-shutdown audit: listeners on 18818, 15218, and 19229 were absent; the isolated Chrome PID/profile process was absent. No default Chrome or unrelated app process was targeted.
- UI evidence: PNGs in this directory correspond to the actual rendered page; API summaries were fetched read-only through same-origin routes; file hashes were checked against synthetic workspace manifests and bytes.
- Limitation: no OAuth cancel control was available. The dedicated CDP listener covered only the final reload window and cannot establish zero console events for the entire browser session.
- Privacy: only synthetic records. Callback state, auth tokens, and remote task client token were not copied to tracked evidence.
