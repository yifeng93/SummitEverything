# Frontend B initial QA archive

This archive preserves the independent QA result for product SHA `613d453ab1a47e2f0bfe78d685fb90817f70f4cc`. The verdict is **FAIL**: QA-001 found the Real SourceOrganizer preview omitted the frozen outgoing original text and its readable destination; QA-002 found the keyboard focus on the clipped file input was not visible. Do not reinterpret this archive as evidence for the repaired SHA.

`QA-REPORT.md`, `command-results.json`, the source manifest, red/green logs, synthetic screenshots, and sanitized harness are checksummed in `archive-manifest.json`. The original QA worktree retains its raw `.local` artifacts. Its Playwright trace and error-context copies are intentionally excluded here because the trace contained an ephemeral session Authorization value; the synthetic workspace snapshot is also not needed for this failure record. The archived harness contains only the generated-token construction, not a token value.

The repair1 Developer report links the fixed SHA and separate results. A fresh QA must inspect that SHA independently.
