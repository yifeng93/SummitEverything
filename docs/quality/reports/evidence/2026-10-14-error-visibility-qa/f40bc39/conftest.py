"""QA-local isolation: mirror tests/conftest.py for the untracked harness dir."""

from __future__ import annotations

import pytest

from summit_everything.integrations.first_use_defaults import DEFAULTS_ENV_VAR


@pytest.fixture(autouse=True)
def isolate_first_use_defaults_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DEFAULTS_ENV_VAR, raising=False)
