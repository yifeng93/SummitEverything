"""Shared test isolation.

The suite must give the same result regardless of the developer's shell
environment. ``SUMMIT_FIRST_USE_DEFAULTS`` is the one variable that changes how
the API resolves the non-secret first-use defaults (ADR 0010), and 23 test
modules build the app without pinning a source, so an exported value used to
change the outcome of unrelated tests: independent QA measured 33 failures with
the variable pointing at the repository-local file and 591 passes without it.

Any inherited value is removed here. A test that wants injected defaults sets
the variable itself through ``monkeypatch``, which runs after this fixture.
"""

from __future__ import annotations

import pytest

from summit_everything.integrations.first_use_defaults import DEFAULTS_ENV_VAR


@pytest.fixture(autouse=True)
def isolate_first_use_defaults_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Never inherit an injection source from the outer environment."""
    monkeypatch.delenv(DEFAULTS_ENV_VAR, raising=False)
