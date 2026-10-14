# QA harness — settings-ux-qa-ea90828 (untracked, never committed)

Target: detached HEAD `ea90828c4eae50873faf3a8f2f7007e6a31d4a1f`, pre-fix parent
`8c4f81c51aac4fe2030b33fb354a5f4f19dfaf1b`.
No product or tracked test file was modified (`git status --porcelain` empty).

## Files

| file | purpose |
| --- | --- |
| `run_ab.sh` | first A/B run (before `web/node_modules` was provisioned) |
| `run_full_matrix.sh` | post-fix A/B **and** pre-fix baseline A/B control |
| `test_env_isolation_probe.py` | item-4 probe: asserts the injected variable is absent in the test body |
| `baseline/` | `git archive 8c4f81c` extraction (whole pre-fix tree, no `tests/conftest.py`) |
| `logs/A.log B.log` | raw A/B, missing `web/node_modules` → 3 env-caused dev-runner failures, identical in A and B |
| `logs/A2.log B2.log` | post-fix A/B with web deps → 591 passed each, exit 0 |
| `logs/P_A.log` | pre-fix + injected → 33 failed, 558 passed, exit 1 |
| `logs/P_B.log` | pre-fix + unset → 591 passed, exit 0 |

## Environment notes

* `web/node_modules` is a **symlink** to the main repository's copy. `web/package.json`
  and `web/package-lock.json` are byte-identical to the main repo, so reuse is safe.
  Without it `scripts/run_dev.py` exits 2 ("Web dependencies missing") and the three
  `tests/integration/test_dev_runner.py` tests fail — in A **and** B equally, i.e.
  unrelated to the change under test.
* Pre-fix control runs `baseline/` with
  `PYTHONPATH=<baseline>/scripts/offline_guard:<baseline>/src`, verified to shadow the
  editable install (`summit_everything.__file__` resolves inside `baseline/`).

## Item-4 caveat (measured)

`tests/conftest.py` is only loaded for tests **below `tests/`**. A probe placed in
`.local/qa/` therefore does *not* get the autouse fixture:

* `.local/qa/test_env_isolation_probe.py` under A → **1 failed** (variable leaks).
* Same file, same A shell, with the repository conftest registered explicitly
  (`PYTHONPATH=...:$PWD/tests uv run pytest -p conftest .local/qa/test_env_isolation_probe.py`)
  → **1 passed**.

So the fixture is effective inside `tests/**` (which is `testpaths`), but its
protection is directory-scoped, not global.
