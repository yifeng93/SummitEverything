"""Unit tests for embedding local non-secret defaults into the app bundle."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from summit_everything.integrations.first_use_defaults import (
    BUNDLE_RESOURCE_NAME,
    REPO_DEFAULTS_RELATIVE_PATH,
    FirstUseDefaultsError,
)

BUILD_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "build_macos_app.py"
EMBEDDING_BASE_URL = (
    "https://ws-synthetic0000000000.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
)


def load_build_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_build_macos_app_under_test", BUILD_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_source(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_a_missing_local_file_is_not_a_build_requirement(tmp_path):
    module = load_build_module()
    resources = tmp_path / "Resources"
    resources.mkdir()

    assert module.embed_first_use_defaults(resources, source=tmp_path / "absent.json") is None
    assert list(resources.iterdir()) == []


def test_the_repository_local_file_is_validated_and_copied(tmp_path, monkeypatch):
    module = load_build_module()
    fake_repo = tmp_path / "repo"
    source = write_source(
        fake_repo / REPO_DEFAULTS_RELATIVE_PATH, {"embedding_base_url": EMBEDDING_BASE_URL}
    )
    monkeypatch.setattr(module, "ROOT", fake_repo)
    assert module.REPO_DEFAULTS_RELATIVE_PATH == REPO_DEFAULTS_RELATIVE_PATH

    resources = tmp_path / "Resources"
    resources.mkdir()
    embedded = module.embed_first_use_defaults(resources)

    assert embedded is not None
    assert embedded.source == source
    assert embedded.values == {"embedding_base_url": EMBEDDING_BASE_URL}
    copied = resources / BUNDLE_RESOURCE_NAME
    assert copied.read_bytes() == source.read_bytes()


def test_secret_shaped_keys_stop_the_build_without_copying(tmp_path):
    module = load_build_module()
    leaked = "synthetic-value-that-must-not-leak"
    source = write_source(tmp_path / "defaults.json", {"deepseek_api_key": leaked})
    resources = tmp_path / "Resources"
    resources.mkdir()

    with pytest.raises(FirstUseDefaultsError) as error:
        module.embed_first_use_defaults(resources, source=source)
    assert error.value.code == "first_use_defaults_secret_key"
    assert leaked not in str(error.value)
    assert list(resources.iterdir()) == []


def test_invalid_injected_url_stops_the_build_without_copying(tmp_path):
    module = load_build_module()
    source = write_source(
        tmp_path / "defaults.json", {"rerank_base_url": "http://example.invalid/api/v1"}
    )
    resources = tmp_path / "Resources"
    resources.mkdir()

    with pytest.raises(FirstUseDefaultsError) as error:
        module.embed_first_use_defaults(resources, source=source)
    assert error.value.code == "first_use_defaults_value_invalid"
    assert "example.invalid" not in str(error.value)
    assert list(resources.iterdir()) == []
