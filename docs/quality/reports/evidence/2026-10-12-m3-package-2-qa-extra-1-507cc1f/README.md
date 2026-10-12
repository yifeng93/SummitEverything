# Evidence bundle

All fixtures are synthetic and contain no real user material or credentials.

- `harness/`: independent QA scripts plus minimized JSON results for extra1 history, provenance, retrieval, profile/workspace and stream-recovery checks.
- `raw-logs/`: complete automated matrix stdout and exit codes; matrix summary is retained alongside the logs.
- `browser-ax-observations.md`: visible PageReader and memory-confirmation states from the actual browser UI.

The HTTP no-evidence diagnostic reproduction is in `harness/no-data-diagnostic-extra1.py` and its result JSON. Re-run it only with the local mock API factory configured by the script; it does not contact external services.
