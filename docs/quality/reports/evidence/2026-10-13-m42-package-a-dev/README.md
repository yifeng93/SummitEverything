# M4.2 Package A supplemental Developer evidence

This directory preserves the incremental raw logs and preliminary exit ledger from development. Earlier failures remain intact and are not the final result. The original `exit-ledger.tsv` is preserved byte-for-byte; its later rows did not include full command/log mappings. The final full checks and exact command map are in [`final-20261014/`](final-20261014/) (`command-manifest.tsv`, `results.tsv`, `SHA256SUMS`).

`SHA256SUMS` in this directory covers the supplemental original logs and original ledger. `SHA256SUMS` inside `final-20261014/` independently covers that final run's raw logs, command manifest and results.

Some tracked test output includes explicit synthetic bearer placeholders used by the mock adapter tests (for example, values named `synthetic-*`); these are not real credentials. No production secrets or user materials are included.
