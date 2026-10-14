"""Unit tests for injected non-secret first-use defaults (all values synthetic)."""

import inspect
import json
import sys
from pathlib import Path

import pytest

from summit_everything.integrations import first_use_defaults as first_use_defaults_module
from summit_everything.integrations.first_use_defaults import (
    ALLOWED_DEFAULT_KEYS,
    BUNDLE_RESOURCE_NAME,
    DEFAULTS_ENV_VAR,
    REPO_DEFAULTS_RELATIVE_PATH,
    FirstUseDefaults,
    FirstUseDefaultsError,
    is_secret_shaped_key,
    load_first_use_defaults,
    read_first_use_defaults_file,
)
from summit_everything.integrations.settings import ProviderSettings, SettingsError, SettingsStore

EMBEDDING_BASE_URL = (
    "https://ws-synthetic0000000000.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
)
RERANK_BASE_URL = "https://ws-synthetic0000000000.cn-beijing.maas.aliyuncs.com/api/v1"
CALLBACK_URI = "http://127.0.0.1:18793/api/v1/integrations/feishu/callback"
APP_ID = "cli_synthetic_app_0001"


def write_defaults(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# --- lookup order and no-source behaviour ---------------------------------


def test_without_any_source_the_behaviour_is_unchanged(tmp_path):
    defaults = load_first_use_defaults(environ={}, bundle_path=tmp_path / "no-bundle")
    assert defaults.values == {}
    assert defaults.source is None

    store = SettingsStore(tmp_path / "settings.json")
    assert store.read() == ProviderSettings()
    assert store.read().embedding.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"


def test_source_priority_env_then_bundle(tmp_path):
    env_file = write_defaults(
        tmp_path / "env.json",
        {
            "embedding_base_url": "https://env-priority.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
        },
    )
    bundle_dir = tmp_path / "bundle"
    write_defaults(
        bundle_dir / BUNDLE_RESOURCE_NAME,
        {
            "embedding_base_url": (
                "https://bundle-priority.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
            )
        },
    )

    from_env = load_first_use_defaults(
        environ={DEFAULTS_ENV_VAR: str(env_file)}, bundle_path=bundle_dir
    )
    assert from_env.source == env_file
    assert from_env.values["embedding_base_url"].startswith("https://env-priority.")

    from_bundle = load_first_use_defaults(environ={}, bundle_path=bundle_dir)
    assert from_bundle.source == bundle_dir / BUNDLE_RESOURCE_NAME
    assert from_bundle.values["embedding_base_url"].startswith("https://bundle-priority.")


def test_the_repository_local_file_is_never_a_runtime_source(tmp_path, monkeypatch):
    # The lookup has exactly two sources: an explicit environment path and the
    # packaged bundle resource. There is no repository-relative fallback, so a
    # developer machine that has .local/first-use/defaults.json behaves exactly
    # like CI or a colleague's machine.
    assert "repo_root" not in inspect.signature(load_first_use_defaults).parameters

    source = write_defaults(
        tmp_path / "repo" / REPO_DEFAULTS_RELATIVE_PATH, {"feishu_app_id": APP_ID}
    )
    monkeypatch.setattr(first_use_defaults_module, "REPO_DEFAULTS_RELATIVE_PATH", source)

    defaults = load_first_use_defaults(environ={}, bundle_path=tmp_path / "no-bundle")

    assert defaults.values == {}
    assert defaults.source is None


def test_explicit_env_path_must_exist(tmp_path):
    missing = tmp_path / "missing.json"
    with pytest.raises(FirstUseDefaultsError) as error:
        load_first_use_defaults(
            environ={DEFAULTS_ENV_VAR: str(missing)},
            bundle_path=tmp_path / "no-bundle",
        )
    assert error.value.code == "first_use_defaults_unavailable"
    assert error.value.source == missing


def test_bundle_resource_is_resolved_from_the_frozen_layout(tmp_path, monkeypatch):
    resources = tmp_path / "SummitEverything Internal.app" / "Contents" / "Resources"
    backend = resources / "backend" / "summit-backend"
    backend.mkdir(parents=True)
    executable = backend / "summit-backend"
    executable.write_bytes(b"")
    bundle_file = write_defaults(resources / BUNDLE_RESOURCE_NAME, {"feishu_app_id": APP_ID})

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    defaults = load_first_use_defaults(environ={})
    assert defaults.source == bundle_file
    assert defaults.values == {"feishu_app_id": APP_ID}


# --- defaults only: stored profile values win ------------------------------


def test_valid_file_injects_defaults_and_keeps_explicit_profile_values(tmp_path):
    source = write_defaults(
        tmp_path / "defaults.json",
        {
            "feishu_app_id": APP_ID,
            "feishu_redirect_uri": CALLBACK_URI,
            "embedding_base_url": EMBEDDING_BASE_URL,
            "rerank_base_url": RERANK_BASE_URL,
        },
    )
    defaults = read_first_use_defaults_file(source)
    assert set(defaults.values) == set(ALLOWED_DEFAULT_KEYS)

    settings_path = tmp_path / "settings.json"
    settings_path.write_text(
        json.dumps(
            {
                "feishu": {"app_id": "cli_user_chosen"},
                "embedding": {
                    "base_url": "https://user-chosen.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
                },
            }
        ),
        encoding="utf-8",
    )
    settings = SettingsStore(settings_path, defaults=defaults).read()
    assert settings.feishu.app_id == "cli_user_chosen"
    assert settings.embedding.base_url.endswith(
        "user-chosen.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    )
    assert settings.feishu.redirect_uri == CALLBACK_URI
    assert settings.rerank.base_url == RERANK_BASE_URL


def test_saving_the_injected_default_does_not_persist_it(tmp_path):
    # Build "A": the injected default.
    defaults_a = FirstUseDefaults(
        values={"embedding_base_url": EMBEDDING_BASE_URL}, source=tmp_path / "defaults-a.json"
    )
    settings_path = tmp_path / "settings.json"
    store = SettingsStore(settings_path, defaults=defaults_a)

    assert store.read().embedding.base_url == EMBEDDING_BASE_URL

    updated = store.update({"embedding": {"base_url": EMBEDDING_BASE_URL}})

    assert updated.embedding.base_url == EMBEDDING_BASE_URL
    persisted = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "base_url" not in persisted["embedding"]
    assert persisted["embedding"]["provider"] == "fake"


def test_a_profile_without_overrides_follows_a_new_injected_default(tmp_path):
    build_a = FirstUseDefaults(
        values={"embedding_base_url": EMBEDDING_BASE_URL}, source=tmp_path / "defaults-a.json"
    )
    build_b_url = "https://ws-rebuilt0000000000.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    build_b = FirstUseDefaults(
        values={"embedding_base_url": build_b_url}, source=tmp_path / "defaults-b.json"
    )
    settings_path = tmp_path / "settings.json"

    SettingsStore(settings_path, defaults=build_a).update(
        {"embedding": {"base_url": EMBEDDING_BASE_URL}}
    )

    assert SettingsStore(settings_path, defaults=build_b).read().embedding.base_url == build_b_url
    assert build_b_url != EMBEDDING_BASE_URL


def test_an_explicit_override_is_persisted_and_stays_fixed(tmp_path):
    build_a = FirstUseDefaults(values={"embedding_base_url": EMBEDDING_BASE_URL})
    build_b_url = "https://ws-rebuilt0000000000.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    build_b = FirstUseDefaults(values={"embedding_base_url": build_b_url})
    explicit_c = "https://ws-explicit000000000.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    settings_path = tmp_path / "settings.json"

    updated = SettingsStore(settings_path, defaults=build_a).update(
        {"embedding": {"base_url": explicit_c}}
    )

    assert updated.embedding.base_url == explicit_c
    persisted = json.loads(settings_path.read_text(encoding="utf-8"))
    assert persisted["embedding"]["base_url"] == explicit_c
    assert SettingsStore(settings_path, defaults=build_b).read().embedding.base_url == explicit_c


def test_clearing_a_field_follows_the_current_injected_default_again(tmp_path):
    build_a = FirstUseDefaults(values={"embedding_base_url": EMBEDDING_BASE_URL})
    build_b_url = "https://ws-rebuilt0000000000.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    build_b = FirstUseDefaults(values={"embedding_base_url": build_b_url})
    explicit_c = "https://ws-explicit000000000.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    settings_path = tmp_path / "settings.json"

    SettingsStore(settings_path, defaults=build_a).update({"embedding": {"base_url": explicit_c}})
    cleared = SettingsStore(settings_path, defaults=build_a).update({"embedding": {"base_url": ""}})

    assert cleared.embedding.base_url == EMBEDDING_BASE_URL
    persisted = json.loads(settings_path.read_text(encoding="utf-8"))
    assert "base_url" not in persisted["embedding"]
    assert SettingsStore(settings_path, defaults=build_b).read().embedding.base_url == build_b_url


def test_without_injected_defaults_the_stored_document_is_unchanged(tmp_path):
    settings_path = tmp_path / "settings.json"
    store = SettingsStore(settings_path)

    updated = store.update({"llm": {"provider": "deepseek", "model": "deepseek-flash"}})

    assert store.read() == updated
    persisted = json.loads(settings_path.read_text(encoding="utf-8"))
    assert persisted["mode"] == "fake"
    assert persisted["llm"]["provider"] == "deepseek"
    # Untouched non-injectable defaults are still materialised exactly as before.
    assert persisted["embedding"]["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert persisted["rerank"]["base_url"] == "https://dashscope.aliyuncs.com/api/v1"
    assert updated.embedding.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"


def test_injected_values_still_fail_stored_settings_validation(tmp_path):
    defaults = FirstUseDefaults(values={"feishu_app_id": APP_ID}, source=tmp_path / "d.json")
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"mode": "not-a-mode"}), encoding="utf-8")
    with pytest.raises(SettingsError):
        SettingsStore(settings_path, defaults=defaults).read()


def test_a_corrupted_section_survives_injection_unchanged(tmp_path):
    """Injection must never repair a corrupted section into something valid."""
    defaults = FirstUseDefaults(
        values={"embedding_base_url": EMBEDDING_BASE_URL, "feishu_app_id": APP_ID},
        source=tmp_path / "defaults.json",
    )
    applied = defaults.apply({"embedding": "not-an-object", "feishu": None})
    assert applied["embedding"] == "not-an-object"
    assert applied["feishu"] is None


@pytest.mark.parametrize("with_defaults", [False, True])
def test_a_corrupted_section_still_fails_closed(tmp_path, with_defaults):
    """A corrupt profile section must raise with and without injection present."""
    settings_path = tmp_path / "settings.json"
    settings_path.write_text(json.dumps({"embedding": "not-an-object"}), encoding="utf-8")
    defaults = (
        FirstUseDefaults(
            values={"embedding_base_url": EMBEDDING_BASE_URL}, source=tmp_path / "d.json"
        )
        if with_defaults
        else None
    )
    with pytest.raises(SettingsError):
        SettingsStore(settings_path, defaults=defaults).read()


# --- fail closed on key policy --------------------------------------------


@pytest.mark.parametrize(
    "key",
    ["deepseek_api_key", "dashscope_secret", "feishu_app_token", "app_password", "credential_blob"],
)
def test_secret_shaped_keys_fail_closed_without_echoing_values(tmp_path, key):
    synthetic_value = "synthetic-value-that-must-not-leak"
    source = write_defaults(tmp_path / "defaults.json", {key: synthetic_value})
    with pytest.raises(FirstUseDefaultsError) as error:
        read_first_use_defaults_file(source)
    assert error.value.code == "first_use_defaults_secret_key"
    assert error.value.fields == (key,)
    assert synthetic_value not in str(error.value)
    assert key in str(error.value)
    assert error.value.__cause__ is None


def test_secret_keys_fail_closed_even_when_empty(tmp_path):
    source = write_defaults(tmp_path / "defaults.json", {"deepseek_api_key": ""})
    with pytest.raises(FirstUseDefaultsError) as error:
        read_first_use_defaults_file(source)
    assert error.value.code == "first_use_defaults_secret_key"


def test_unknown_non_secret_keys_fail_closed(tmp_path):
    source = write_defaults(tmp_path / "defaults.json", {"calendar_id": "synthetic-calendar"})
    with pytest.raises(FirstUseDefaultsError) as error:
        read_first_use_defaults_file(source)
    assert error.value.code == "first_use_defaults_unknown_key"
    assert error.value.fields == ("calendar_id",)


def test_allowed_keys_never_match_the_secret_pattern():
    for key in ALLOWED_DEFAULT_KEYS:
        assert is_secret_shaped_key(key) is False, key
    for key in ("deepseek_api_key", "dashscope_secret", "feishu_app_token", "app_password"):
        assert is_secret_shaped_key(key) is True, key


# --- fail closed on invalid content and values ----------------------------


def test_invalid_json_and_shapes_fail_closed(tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(FirstUseDefaultsError) as error:
        read_first_use_defaults_file(broken)
    assert error.value.code == "first_use_defaults_invalid"
    assert "not json" not in str(error.value)

    with pytest.raises(FirstUseDefaultsError):
        read_first_use_defaults_file(write_defaults(tmp_path / "list.json", [1, 2]))

    non_string = write_defaults(tmp_path / "non-string.json", {"feishu_app_id": 7})
    with pytest.raises(FirstUseDefaultsError) as error:
        read_first_use_defaults_file(non_string)
    assert error.value.code == "first_use_defaults_invalid"
    assert error.value.fields == ("feishu_app_id",)


def test_blank_values_are_ignored(tmp_path):
    source = write_defaults(tmp_path / "defaults.json", {"feishu_app_id": "   "})
    defaults = read_first_use_defaults_file(source)
    assert defaults.values == {}
    assert defaults.source == source


@pytest.mark.parametrize(
    ("key", "value"),
    [
        (
            "embedding_base_url",
            "http://ws-synthetic.cn-beijing.maas.aliyuncs.com/compatible-mode/v1",
        ),
        ("embedding_base_url", "https://example.invalid/compatible-mode/v1"),
        ("embedding_base_url", "https://ws-synthetic.cn-beijing.maas.aliyuncs.com/api/v1"),
        ("rerank_base_url", "https://ws-synthetic.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"),
        ("rerank_base_url", "https://ws-synthetic.cn-beijing.maas.aliyuncs.com/api/v1?token=1"),
        ("feishu_redirect_uri", "https://example.invalid/api/v1/integrations/feishu/callback"),
        ("feishu_redirect_uri", "http://127.0.0.1:18793/not-the-callback"),
    ],
)
def test_invalid_injected_values_are_rejected_by_the_existing_validators(tmp_path, key, value):
    source = write_defaults(tmp_path / "defaults.json", {key: value})
    with pytest.raises(FirstUseDefaultsError) as error:
        read_first_use_defaults_file(source)
    assert error.value.code == "first_use_defaults_value_invalid"
    assert error.value.fields
    assert any(key.split("_")[0] in field for field in error.value.fields)
    assert value not in str(error.value)
    assert value not in repr(error.value)
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__ is True


def test_load_failure_reports_the_source_path_only(tmp_path):
    source = write_defaults(
        tmp_path / "defaults.json", {"embedding_base_url": "http://nope.invalid"}
    )
    with pytest.raises(FirstUseDefaultsError) as error:
        load_first_use_defaults(environ={DEFAULTS_ENV_VAR: str(source)})
    assert error.value.source == source
    assert str(source) in str(error.value)


# --- merge semantics -------------------------------------------------------


def test_apply_leaves_non_mapping_settings_payloads_untouched():
    defaults = FirstUseDefaults(values={"feishu_app_id": APP_ID})
    assert defaults.apply(["not", "a", "mapping"]) == ["not", "a", "mapping"]


def test_apply_does_not_mutate_the_input_mapping():
    raw = {"feishu": {"app_id": ""}}
    defaults = FirstUseDefaults(values={"feishu_app_id": APP_ID})
    merged = defaults.apply(raw)
    assert raw == {"feishu": {"app_id": ""}}
    assert merged == {"feishu": {"app_id": APP_ID}}
