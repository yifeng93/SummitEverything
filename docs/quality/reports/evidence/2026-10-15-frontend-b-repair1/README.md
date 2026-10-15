# Frontend B repair1 Developer evidence

This evidence belongs to product SHA `a0ccad8bcd46814a23c74d00bbba1d1d5f98699c` only. The command list records failures and final reruns separately; `evidence-manifest.json` checksums every tracked file. Developer results are not an independent QA verdict.

`logs/` contains raw command transcripts for the final focused tests, typecheck, lint, build, serial browser suite, Fake FastAPI flow, and the same bounded Real SourceOrganizer preview/cancel case used in initial QA. It also retains two harness/test-discovery failures and their resolution. The concurrent Playwright failure is documented separately from the serial 2/2 pass. Python 661 passed is only a prior result for unchanged backend code at the parent SHA; repair1 Python tests were not run.

`harness/` contains the synthetic source-scope Playwright case and its isolated FastAPI/Vite configuration. It creates a one-time test session value at runtime and contains no saved credential. The stub uses a synthetic source returned by the isolated Fake service, displays its exact text in the UI, cancels the plan, and asserts zero intake-job writes and zero external attempts.

`screenshots/import-focus/` contains the 10 keyboard-focus captures at 320, 390, 768, 960, and 1280 pixels in light and dark themes. `screenshot-manifest.json` maps each image to its viewport, theme, byte size, and SHA-256. These are synthetic browser UI. Developer visually inspected the full contact sheet plus 320/1280 source screenshots. Each viewport/theme also ran keyboard assertions for both file controls, native Enter/Space activation, dialog containment, Escape, and focus return.

The first independent QA remains **FAIL** on parent SHA `613d453ab1a47e2f0bfe78d685fb90817f70f4cc`; its raw report and red evidence remain in [initial QA archive](../2026-10-15-frontend-b-initial-qa/README.md). Fresh QA should now inspect this repair1 SHA independently.
