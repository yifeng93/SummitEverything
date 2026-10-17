# Ponytail docs batch 1 QA evidence

Tested commit: `f57c7ed3a6d2e6763e1624aa3fd08187f5c4d796`
Comparison base: `6f8fe80558d6e51481f6a3dd203c7e53e6faad89`

- `check_docs.py`: read-only checker for pinned HEAD, changed path scope, protected specs, report/evidence Git blob IDs, acceptance rows, current-entry Markdown file links/anchors, README headings, and referenced command inputs. Run with `python3 docs/quality/reports/evidence/2026-10-17-ponytail-docs-qa/check_docs.py`.
- `check_docs.log` / `check_docs.exit`: successful run output and actual exit code.
- `diff-check.log` / `diff-check.exit`: `git diff --check BASE..TARGET`, exit 0.
- `protected-tree-diff.exit`: `git diff --quiet BASE TARGET -- src tests web native scripts .github/workflows pyproject.toml uv.lock package.json package-lock.json`, exit 0 (no differences).

Initial independent checkout status was clean before QA evidence creation. Final working-tree status is recorded in the QA report. The check did not run product tests, builds, browser UI, real services, package gates, or runtime metadata inspection.
