# DeepSeek Stage B R3 evidence (2026-10-10)

Evidence for the uncommitted `codex/deepseek-stage-b-trial` tree that remediates the five P1
findings from Sol's review of R2. **DEV evidence, not independent QA.** HEAD is still the fixed
documentation commit `0a1db5d72e6ac11184d28e65dea3ba008762ba43`; nothing was committed.

## Contents

- `before/` — the regressions failing against the R2-equivalent code, one log per finding, plus
  `OVERLAY-README.md` documenting exactly which functions were reverted and how to replay it.
- `after/` — the same selections passing on the current tree (`r3_01`..`r3_05`).
- `checks/01..14-*.log` — the full offline check battery, each ending with `EXIT=<code>`.
  `14-pytest-guarded.log` reruns the whole suite under the archived guard.
- `loopback-timings.txt` — measured real-loopback elapsed times for the R3-05 deadline.
- `sol-harness-regressions.log`, `sol-harness-additional.log`,
  `sol-harness-regressions-corrected.log` — the archived Sol harness re-run unchanged, plus the
  corrected concurrency harness (8/8).
- `replay-commands.txt` — exact commands, guard hash and how the before-replay was produced.
- `git-state.txt` — branch, HEAD, dirty count, `git status --short`, `git diff --stat`, and the
  base-vs-last-candidate documentation-only diff.
- `product-source-hashes.txt` — SHA-256 of every changed/new source and test file.
- `manifest.json` — SHA-256 of every file here except itself.

## Boundaries

- Synthetic data, in-memory secret backends, stub providers, MockTransport and a local
  `127.0.0.1` HTTP server only. Real calls after this round: Feishu code exchange 0/1, refresh 0/1,
  DeepSeek chat 0/1, Model Studio embedding 0/1, rerank 0/1.
- No user Keychain item was read, listed or migrated; no credential was entered.
- No browser or native session was started for this tree; browser/native/OS-Keychain evidence
  remains NOT_RUN. Nothing was borrowed from another worktree.
- The loopback servers are started and stopped inside their test fixture; no background service is
  left listening.
- A high-confidence credential-pattern scan over the changed files found 0 non-synthetic hits.
- R1 and R2 evidence directories are untouched; both manifests still verify 22/22.
