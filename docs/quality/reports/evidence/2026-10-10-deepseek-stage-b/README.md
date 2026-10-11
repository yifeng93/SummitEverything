# DeepSeek Stage B trial — evidence set (2026-10-10)

This directory holds the DEV evidence for the uncommitted
`codex/deepseek-stage-b-trial` tree. It is **not** independent QA. The trial base is the fixed
documentation commit `0a1db5d72e6ac11184d28e65dea3ba008762ba43`; the last committed source
candidate is `7dc7114595704f34ba386c96324dffa77d529ba4` and the base differs from it only in
documentation.

## Contents

- `checks/01..13-*.log` — raw stdout of the full offline check battery, each ending with
  `EXIT=<code>`. Captured in the trial tree on 2026-10-10.
- `sol-harness-regressions.log`, `sol-harness-additional.log`, `sol-harness-frontend.log` —
  re-run of Sol's archived SB-01–13 counterexamples against this candidate, from a replay
  directory outside the repository, with the archived `sitecustomize.py` guard active
  (non-loopback sockets and macOS Keychain blocked). Two non-pass items are explained in the DEV
  report §4.
- `replay-commands.txt` — the exact commands used, including how the temporary frontend harness
  was copied in and removed.
- `git-status.txt` — branch, HEAD, `git status --short`, and the base-vs-candidate documentation
  only diff.
- `diff-stat.txt` — working-tree diff stat and untracked file list.
- `product-source-hashes.txt` — SHA-256 of every changed/new source and test file, for
  independent tree verification.
- `manifest.json` — SHA-256 of each file in this directory except the manifest itself.

## Boundaries

- Synthetic data, in-memory secret backends and `httpx.MockTransport` only. No real Feishu or
  model request was made: code exchange 0/1, refresh 0/1, DeepSeek chat 0/1, Model Studio
  embedding 0/1, rerank 0/1.
- No user Keychain item was read, listed or migrated; no credential was entered.
- No browser or native session was started for this tree, so there is no candidate run identity
  in this evidence set. Do not borrow a window or profile from another worktree.
- A high-confidence credential-pattern scan over the changed files found 0 non-synthetic hits.
  This is a sanity check, not a security certification.
- Evidence files were scrubbed of temporary absolute paths where they appeared; the guard
  Python file is not duplicated here (it is referenced by path and archived with Sol's own
  evidence set).
