"""Independent QA harness isolation (mirrors tests/conftest.py, not tracked).

The QA harness lives outside ``tests/`` so it never runs as part of the product
suite and never modifies tracked tests. It still needs the same environment
isolation the product suite relies on: an inherited ``SUMMIT_FIRST_USE_DEFAULTS``
must never change a result.
"""

from __future__ import annotations

import pytest

DEFAULTS_ENV_VAR = "SUMMIT_FIRST_USE_DEFAULTS"


@pytest.fixture(autouse=True)
def isolate_first_use_defaults_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEFAULTS_ENV_VAR, raising=False)
