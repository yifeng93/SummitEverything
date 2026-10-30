# Sol repair-1 source review

Fixed SHA 4358c7b2b410d8c5bcc6ab4dd7d219ce9d349a25, parent initial candidate 5d76fe20b0300fb846b6af01475f55f4e75859ab. Developer worktree clean. Six-file repair: ProjectsView request lifetime and bounded retries, App monitor warning, tests, exact internal-use allowlist, ADR035 retry wording. No backend change in repair. Base-to-candidate scope 20 files.

Reviewed source behavior: same-page overview PageReader retained while loading/error and synchronizing disables unsafe confirmation; detail retries get fresh controller/deadline, target/hash budget avoids repeated 409 resetting itself; monitoring errors visible independent of reader unavailable branch; allowlist updates enumerate internal API references, render guard unchanged. Product specification now explicitly readonly overview and external-save lifecycle. Initial source path scanning follows existing registered directories and rejects outside/symlink pages.

Developer proof: stdout transcripts and reported exits archived, 313 frontend tests before final retry-bound adjustment; final 47 targeted tests plus typecheck afterward, build/lint exit0, lint warnings retained. These are Developer self-checks, not independent final acceptance. Fresh QA pending.

Main preflight: branch hanwenbo-dev-202610, HEAD fad0de06cc5333ac457e88b9df73498ca5189d0b at check. BASE->candidate patch applies cleanly. Existing other task changes in app.py, API/frontend docs, generated schemas must be retained. No actual patch applied yet.
