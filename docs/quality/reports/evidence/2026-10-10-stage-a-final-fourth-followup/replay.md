# Round four replay assets

All provider behavior is synthetic. The harness is `harness/round4-sitecustomize.py` and patches only `FakeFeishu`, `workspace.transactions.atomic_write`, and `workspace.action_receipts` inside the running QA Python process. It does not modify tracked product source. A throwaway workspace and QA profile are required for every replay.

## Runner

From the fixed QA checkout, launch the normal dev runner with:

```sh
PYTHONPATH="$PWD/docs/quality/reports/evidence/2026-10-10-stage-a-final-fourth-followup/harness" \
SUMMIT_API_PORT=18828 SUMMIT_WEB_PORT=15228 \
SUMMIT_PROFILE_ROOT="$PWD/.local/qa/stage-a-final-round4/profile" \
SUMMIT_QA_REMOTE_ROOT="$PWD/.local/qa/stage-a-final-round4/remote" \
SUMMIT_QA_TRACE_PATH="$PWD/.local/qa/stage-a-final-round4/provider-trace.jsonl" \
SUMMIT_QA_CONTROL_PATH="$PWD/.local/qa/stage-a-final-round4/fault-control.json" \
uv run python scripts/run_dev.py
```

The browser was a directly launched Chrome with an isolated user-data directory and CDP port 19239, opened only to `http://127.0.0.1:15228/`. Do not attach to the default browser profile. The actual fourth-round `.local` workspace/profile/remote state was ignored and is not committed.

## Deterministic scenarios

- Create a task titled exactly `QA R4 concurrent double` and send two execute requests for the same confirmed action with 250 ms separation; provider count should advance once.
- Create `QA R4 process exit`; `task_create` persists via the original Fake method, then calls `os._exit(72)` to simulate an abrupt API-process exit.
- Create `QA R4 mismatch result`; the original Fake persists the requested task, then the harness returns a mismatched summary. Expected UI/API state is `unknown`, followed by read-only reconciliation from the exact Fake result; a replay must not add a task.
- For local receipt loss, prepare and separately confirm a `project_progress` action in a synthetic workspace, then set control to `{"mode":"receipt_success_write_failure","fired":false}` immediately before Execute. The manifest write succeeds; the success receipt write raises. Restart the runner and reopen the same workspace; running becomes unknown. Read-only reconcile uses the local writer journal. Replaying the same action must not increment progress version.
- For interrupted manifest commit, use a distinct synthetic workspace and set `{"mode":"atomic_manifest_before_replace","fired":false}` before Execute. The harness writes and fsyncs the transaction temp file and raises before `os.replace`. The old manifest remains byte-identical; restart leaves the action unknown and subsequent execute/reconcile cannot claim success without proof.
- For monthly archive, use a third isolated workspace containing a succeeded action, preserve its original receipt, and set its `finished_at` to a prior month as synthetic fixture setup. Set `{"mode":"archive_after_summary_before_delete","fired":false}` before GET `/api/v1/action-intents`; the summary is atomically replaced and then the harness raises. The active and summary records must be identical and unique. After clearing the control, GET recovers and deletes only the active duplicate. To exercise delete failure separately, restore an identical active copy, set `{"mode":"archive_delete_interruption","fired":false}`, GET once, verify both equal copies remain, clear the control, then GET to recover.
- To verify corrupt/duplicate safety on the same isolated archive fixture, make a conflicting active copy by changing only its synthetic `evidence` array; listing returns 409. Restore equality and list successfully. Separately preserve the summary bytes, temporarily truncate the summary JSON (409 expected), then restore the original bytes and verify listing succeeds.

The control file is one-shot per mode (`fired` flips true) and should be reset to `{"mode":null,"fired":true}` between scenarios. `provider-trace.jsonl` contains only synthetic titles/counts, harness PID, fault mode, and task GUID/field names; remote task JSON containing Fake client tokens is not included.
