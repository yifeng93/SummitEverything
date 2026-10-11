"""Independent offline QA: SecretBackend fault only; production vault/store retained."""
import pytest
from pydantic import SecretStr
from summit_everything.integrations.settings import CredentialVault, MemorySecretBackend, SettingsError
from summit_everything.integrations.feishu.provider import VaultCredentialStore, AppCredentials, UserCredentials

class FaultBackend(MemorySecretBackend):
    def __init__(self, code):
        super().__init__(); self.code = code
    def get(self, namespace, key):
        if self.code: raise SettingsError(self.code)
        return super().get(namespace, key)
    def set(self, namespace, key, value):
        if self.code: raise SettingsError(self.code)
        return super().set(namespace, key, value)
    def delete(self, namespace, key):
        if self.code: raise SettingsError(self.code)
        return super().delete(namespace, key)

@pytest.mark.parametrize('code', ['credential_access_denied', 'credential_store_locked'])
def test_denied_and_locked_fail_without_fallback(code):
    backend = FaultBackend(code)
    vault = CredentialVault('independent-qa', backend)
    for action in [lambda: vault.put('feishu_app', 'synthetic-secret', account_id='cli_qa'),
                   lambda: vault.get_secret('feishu_app', account_id='cli_qa'),
                   lambda: vault.delete('feishu_app', account_id='cli_qa')]:
        with pytest.raises(SettingsError) as error: action()
        assert error.value.code == code
        assert 'synthetic-secret' not in str(error.value)
    assert backend._values == {}

def test_store_restart_shares_only_same_namespace_and_app():
    backend = MemorySecretBackend()
    first = VaultCredentialStore(CredentialVault('profile-a', backend), 'cli_qa')
    expected = UserCredentials(access_token='synthetic-access', refresh_token='synthetic-refresh', expires_at=2000000000, scopes=['offline_access'])
    first.put(expected)
    first.put_app(AppCredentials(app_id='cli_qa',app_secret=SecretStr('synthetic-secret')))
    restarted = VaultCredentialStore(CredentialVault('profile-a', backend), 'cli_qa')
    assert restarted.get() == expected and restarted.get_app() == first.get_app()
    assert VaultCredentialStore(CredentialVault('profile-b', backend),'cli_qa').get() is None
    assert VaultCredentialStore(CredentialVault('profile-a', backend),'cli_other').get() is None
    restarted.delete(); assert first.get() is None
