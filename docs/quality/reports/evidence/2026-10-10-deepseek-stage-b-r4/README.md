# DeepSeek Stage B R4 evidence (2026-10-10)

Evidence for the uncommitted `codex/deepseek-stage-b-trial` tree that remediates the three findings
from Sol's R3 final read-only review. **DEV evidence, not independent QA.** HEAD is still the fixed
documentation commit `0a1db5d72e6ac11184d28e65dea3ba008762ba43`; nothing was committed.

## Contents

- `r3-start-snapshot/` + `r3-start-snapshot-hashes.txt` — the exact R3 sources for every file this
  round touched, archived **before** any edit. All before-replays are verified byte-for-byte against
  these hashes (5/5).
- `before/` — the R3-baseline failures: `r4_01.log`, `r4_02.log`, `r4_03.log`, `r4_combo.log`, plus
  `OVERLAY-README.md` documenting how the baseline was replayed (and the single documented shim).
- `after/` — the same selections passing on the current tree.
- `r4_02-timings-and-tests.log` — the R4-02 suite including the 10-run timings for each deadline case.
- `checks/01..14-*.log` — the full offline check battery, each ending with `EXIT=<code>`;
  `14-pytest-guarded.log` is the whole suite under the archived guard.
- `final-source-hashes.txt`, `git-state.txt`, `replay-commands.txt` — final source hashes, the exact
  git state (no commit) and every command executed.
- `manifest.json` — SHA-256 of every file here except itself.

## Boundaries

- Synthetic data, in-memory secret backends, MockTransport and a local `127.0.0.1` server only.
  Real calls after this round: Feishu code exchange 0/1, refresh 0/1, DeepSeek chat 0/1,
  Model Studio embedding 0/1, rerank 0/1.
- No user Keychain item was read, listed or migrated; no credential was entered.
- No browser or native session was started for this tree; browser/native/OS-Keychain evidence stays
  NOT_RUN. Nothing was borrowed from another worktree.
- All R4 loopback servers are started and stopped inside their fixtures; no listener is left behind.
- A high-confidence credential-pattern scan over the changed files found 0 non-synthetic hits.
- R1/R2/R3 evidence directories are untouched; their manifests still verify.
