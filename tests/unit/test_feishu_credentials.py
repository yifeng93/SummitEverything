import json

import pytest
from pydantic import SecretStr

from summit_everything.integrations.feishu.provider import (
    AppCredentials,
    KeychainCredentialStore,
    UserCredentials,
    VaultCredentialStore,
)
from summit_everything.integrations.settings import CredentialVault, MemorySecretBackend


def _credentials(refresh_token: str = "refresh-v1") -> UserCredentials:
    return UserCredentials(
        access_token="access-v1",
        refresh_token=refresh_token,
        expires_at=2_000_000_000,
        scopes=["offline_access", "minutes:minutes:readonly"],
    )


def test_keychain_store_round_trips_rotated_user_tokens_and_logout():
    backend = MemorySecretBackend()
    first = KeychainCredentialStore("profile-a", "cli_app_a", backend)
    first.put(_credentials())

    restarted = KeychainCredentialStore("profile-a", "cli_app_a", backend)
    assert restarted.get() == _credentials()

    rotated = _credentials("refresh-v2")
    restarted.put(rotated)
    assert first.get() == rotated
    first.delete()
    assert restarted.get() is None


def test_keychain_store_scopes_tokens_by_profile_and_app_id():
    backend = MemorySecretBackend()
    KeychainCredentialStore("profile-a", "cli_app_a", backend).put(_credentials())

    assert KeychainCredentialStore("profile-b", "cli_app_a", backend).get() is None
    assert KeychainCredentialStore("profile-a", "cli_app_b", backend).get() is None


def test_keychain_store_keeps_app_secret_separate_from_user_tokens():
    backend = MemorySecretBackend()
    store = KeychainCredentialStore("profile-a", "cli_app_a", backend)
    app_credentials = AppCredentials(app_id="cli_app_a", app_secret=SecretStr("synthetic-secret"))

    store.put_app(app_credentials)
    store.put(_credentials())

    assert store.get_app() == app_credentials
    assert store.get() == _credentials()
    assert len(backend._values) == 2


def test_keychain_store_rejects_app_identity_mismatch():
    store = KeychainCredentialStore("profile-a", "cli_app_a", MemorySecretBackend())

    with pytest.raises(ValueError):
        store.put_app(AppCredentials(app_id="cli_app_b", app_secret=SecretStr("secret")))


def test_keychain_store_rejects_corrupt_persisted_token_without_leaking_secret():
    backend = MemorySecretBackend()
    store = KeychainCredentialStore("profile-a", "cli_app_a", backend)
    backend.set(store.namespace, store.user_item_key, json.dumps({"access_token": "secret"}))

    with pytest.raises(ValueError, match="stored Feishu credentials are invalid") as error:
        store.get()

    assert "secret" not in str(error.value)


def _vault(
    backend: MemorySecretBackend, namespace: str = "com.summiteverything.test"
) -> CredentialVault:
    return CredentialVault(namespace, backend)


def test_vault_store_shares_the_settings_app_secret_slot():
    backend = MemorySecretBackend()
    vault = _vault(backend)
    # The settings UI path writes feishu_app under the configured app id.
    vault.put("feishu_app", "synthetic-app-secret", account_id="cli_app_a")
    store = VaultCredentialStore(vault, "cli_app_a")

    assert store.get_app() == AppCredentials(
        app_id="cli_app_a", app_secret=SecretStr("synthetic-app-secret")
    )
    # Only one slot is used for the app secret; no second disconnected store.
    assert list(backend._values) == [
        ("com.summiteverything.test", CredentialVault._item_key("feishu_app", "cli_app_a"))
    ]


def test_vault_store_round_trips_user_tokens_next_to_the_app_secret():
    backend = MemorySecretBackend()
    vault = _vault(backend)
    store = VaultCredentialStore(vault, "cli_app_a")
    store.put_app(AppCredentials(app_id="cli_app_a", app_secret=SecretStr("synthetic-secret")))
    store.put(_credentials())

    assert store.get() == _credentials()
    assert store.get_app() is not None
    assert len(backend._values) == 2
    store.delete()
    assert store.get() is None
    assert VaultCredentialStore(vault, "cli_app_b").get() is None


def test_vault_store_is_isolated_per_profile_namespace():
    backend = MemorySecretBackend()
    VaultCredentialStore(_vault(backend, "namespace-a"), "cli_app_a").put(_credentials())

    assert VaultCredentialStore(_vault(backend, "namespace-b"), "cli_app_a").get() is None


def test_vault_store_rejects_corrupt_data_without_leaking_the_secret():
    backend = MemorySecretBackend()
    vault = _vault(backend)
    store = VaultCredentialStore(vault, "cli_app_a")
    vault.put(
        "feishu_user", json.dumps({"access_token": "synthetic-secret"}), account_id="cli_app_a"
    )

    with pytest.raises(ValueError, match="stored Feishu credentials are invalid") as error:
        store.get()

    assert "synthetic-secret" not in str(error.value)


def test_vault_store_uses_a_single_shared_namespace_for_both_items():
    backend = MemorySecretBackend()
    vault = _vault(backend)
    store = VaultCredentialStore(vault, "cli_app_a")
    store.put_app(AppCredentials(app_id="cli_app_a", app_secret=SecretStr("synthetic-secret")))
    store.put(_credentials())

    namespaces = {namespace for namespace, _key in backend._values}
    assert namespaces == {"com.summiteverything.test"}
