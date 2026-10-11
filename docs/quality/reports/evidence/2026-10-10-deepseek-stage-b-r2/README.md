# DeepSeek Stage B R2 evidence (2026-10-10)

Evidence for the uncommitted `codex/deepseek-stage-b-trial` tree that remediates the five P1 and
one P2 findings from Sol's independent DEV review of round 1. This is **DEV evidence, not
independent QA**. HEAD is still the fixed documentation commit
`0a1db5d72e6ac11184d28e65dea3ba008762ba43`; nothing was committed.

## Contents

- `checks/01..14-*.log` — raw stdout of the full offline check battery, each ending with
  `EXIT=<code>`. `14-pytest-guarded.log` reruns the whole suite under the archived guard.
- `sol-harness-regressions.log` / `sol-harness-additional.log` — the **archived** Sol harness
  re-run unchanged. The two non-pass items are the known archived-harness issues, explained in the
  R2 report §5; they are retained, not rewritten.
- `sol-harness-regressions-corrected.log` + `test_review_regressions_corrected.py` — a copy of the
  archived regression harness whose *only* change is the concurrent-refresh test: it releases the
  blocked refresh from an independent thread instead of after a synchronous call that a correct
  single-flight lock must block. Result: **8 passed**, showing the archived error was the harness's
  own deadlock.
- `replay-commands.txt` — exact commands, including the guard path and how the corrected harness
  was produced and run.
- `git-state.txt` — branch, HEAD, dirty count, `git status --short`, `git diff --stat`, and the
  base-vs-last-candidate documentation-only diff.
- `product-source-hashes.txt` — SHA-256 of every changed/new source and test file.
- `manifest.json` — SHA-256 of every file here except itself.

## Boundaries

- Synthetic data, in-memory secret backends, stub providers and `httpx.MockTransport` only.
  Real calls after this round: Feishu code exchange 0/1, refresh 0/1, DeepSeek chat 0/1,
  Model Studio embedding 0/1, rerank 0/1.
- No user Keychain item was read, listed or migrated; no credential was entered.
- No browser or native session was started for this tree, so no candidate run identity exists
  here. Nothing was borrowed from the `qa-m1-close-daf726e` worktree or any other window.
- A high-confidence credential-pattern scan over the changed files found 0 non-synthetic hits.
  This is a sanity check, not a security certification.
- Round-1 evidence (`../2026-10-10-deepseek-stage-b/`) is untouched; its 22-file manifest still
  verifies.
