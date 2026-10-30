"""Explicit Fake settings-store factory for isolated legacy offline integration tests.

Production ``create_app`` never selects this factory. New delivery-contract tests
should omit the dependency and verify the real runtime defaults.
"""

from __future__ import annotations

import json
from pathlib import Path

from summit_everything.integrations.first_use_defaults import FirstUseDefaults
from summit_everything.integrations.settings import SettingsStore


def fake_settings_store_factory(path: Path, defaults: FirstUseDefaults | None) -> SettingsStore:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "mode": "fake",
                    "feishu": {"identity": "user"},
                    "llm": {"provider": "fake", "model": None, "enabled": False},
                    "embedding": {"provider": "fake", "model": None, "enabled": False},
                    "rerank": {"provider": "fake", "model": None, "enabled": False},
                }
            ),
            encoding="utf-8",
        )
    return SettingsStore(path, defaults=defaults, allow_test_fake=True)


def create_fake_test_app(*args, **kwargs):
    """Build the app with an explicit synthetic Fake settings profile."""
    from pathlib import Path
    from tempfile import mkdtemp

    from summit_everything.api.app import create_app
    from summit_everything.intake.review import IntakeReviewService
    from summit_everything.integrations.feishu.fake import FakeFeishu
    from summit_everything.integrations.llm import FakeLLM

    kwargs.setdefault("settings_store_factory", fake_settings_store_factory)
    profile_root = kwargs.get("profile_root")
    remote_root = (
        Path(profile_root) / "synthetic-feishu-remote"
        if profile_root
        else Path(mkdtemp(prefix="summit-test-feishu-"))
    )
    if kwargs.get("feishu_provider") is None:
        kwargs["feishu_provider"] = FakeFeishu(remote_root)
    if kwargs.get("review_service") is None:
        kwargs["review_service"] = IntakeReviewService(FakeLLM())
    return create_app(*args, **kwargs)
