"""Unit tests: the dev preview passes the local defaults file explicitly.

The runtime never reads the repository file implicitly, so the development
preview runner has to opt in. These tests pin that wiring.
"""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from summit_everything.integrations.first_use_defaults import (
    DEFAULTS_ENV_VAR,
    REPO_DEFAULTS_RELATIVE_PATH,
)

RUN_DEV = Path(__file__).resolve().parents[2] / "scripts" / "run_dev.py"


def load_run_dev() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_run_dev_under_test", RUN_DEV)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_local_defaults(repo: Path) -> Path:
    source = repo / REPO_DEFAULTS_RELATIVE_PATH
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(json.dumps({"feishu_app_id": "cli_synthetic_app_0001"}), encoding="utf-8")
    return source


def test_an_existing_local_file_is_passed_through_the_environment(tmp_path, monkeypatch):
    module = load_run_dev()
    repo = tmp_path / "repo"
    source = write_local_defaults(repo)
    monkeypatch.setattr(module, "ROOT", repo)
    base = {"PATH": "/usr/bin"}

    env = module.first_use_defaults_environment(base)

    assert env[DEFAULTS_ENV_VAR] == str(source)
    assert env["PATH"] == "/usr/bin"
    assert DEFAULTS_ENV_VAR not in base


def test_a_missing_local_file_leaves_the_environment_unchanged(tmp_path, monkeypatch):
    module = load_run_dev()
    monkeypatch.setattr(module, "ROOT", tmp_path / "repo-without-defaults")

    env = module.first_use_defaults_environment({"PATH": "/usr/bin"})

    assert env == {"PATH": "/usr/bin"}


def test_an_explicit_environment_value_wins(tmp_path, monkeypatch):
    module = load_run_dev()
    repo = tmp_path / "repo"
    write_local_defaults(repo)
    monkeypatch.setattr(module, "ROOT", repo)

    env = module.first_use_defaults_environment({DEFAULTS_ENV_VAR: "/explicit/defaults.json"})

    assert env[DEFAULTS_ENV_VAR] == "/explicit/defaults.json"
