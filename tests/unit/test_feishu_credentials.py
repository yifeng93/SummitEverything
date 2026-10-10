import json

import pytest
from pydantic import SecretStr

from summit_everything.integrations.feishu.provider import (
    AppCredentials,
    KeychainCredentialStore,
    UserCredentials,
)
from summit_everything.integrations.settings import MemorySecretBackend


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
