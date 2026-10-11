"""New independent storage-fault probes over the real API/provider/vault chain."""

import json

import httpx
import pytest
from test_independent_boundaries import HEADERS, SCOPE, Backend, Remote, api, login

from summit_everything.integrations.settings import SettingsError


def user_value(backend):
    return next(
        json.loads(value)
        for (_namespace, key), value in backend._values.items()
        if key.startswith("feishu_user:")
    )


def rewrite_user(backend, update):
    for (namespace, key), raw in list(backend._values.items()):
        if key.startswith("feishu_user:"):
            value = json.loads(raw)
            update(value)
            backend.set(namespace, key, json.dumps(value))


class FaultBackend(Backend):
    phase = None

    def set(self, namespace, key, value):
        if key.startswith("feishu_user:") and self.phase is not None:
            wire = json.loads(value)
            if self.phase == "reservation-after-set" and wire.get("refresh_consumed") is True:
                super().set(namespace, key, value)
                raise SettingsError("credential_access_denied")
            if self.phase == "rotation-before-set" and wire["refresh_token"].startswith("rotated-"):
                raise SettingsError("credential_access_denied")
            if self.phase == "rotation-after-set" and wire["refresh_token"].startswith("rotated-"):
                super().set(namespace, key, value)
                raise SettingsError("credential_access_denied")
        return super().set(namespace, key, value)


class RotationRemote(Remote):
    def __init__(self):
        super().__init__(short_token=True)
        self.spent = []

    def handler(self, request):
        if request.url.path.endswith("/oauth/token"):
            payload = json.loads(request.content)
            if payload["grant_type"] == "refresh_token":
                self.calls.append((request.method, request.url.path))
                self.refresh_calls += 1
                self.spent.append(payload["refresh_token"])
                return httpx.Response(
                    200,
                    json={
                        "code": 0,
                        "access_token": "synthetic-new-access",
                        "refresh_token": f"rotated-{self.refresh_calls}",
                        "expires_in": 1 if self.refresh_calls == 1 else 7200,
                        "scope": SCOPE,
                        "token_type": "Bearer",
                    },
                )
        return super().handler(request)


def test_reservation_set_then_raises_blocks_http_and_restart_retry(tmp_path, monkeypatch):
    backend, remote = FaultBackend(), Remote(short_token=True)
    with api(tmp_path, monkeypatch, backend, remote) as first:
        login(first)
        backend.phase = "reservation-after-set"
        failed = first.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert failed.status_code == 503, failed.text
        assert remote.refresh_calls == 0
        assert user_value(backend)["refresh_consumed"] is True
        assert "synthetic-user-access" not in failed.text
    backend.phase = None
    with api(tmp_path, monkeypatch, backend, remote, create=False) as restarted:
        blocked = restarted.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert blocked.status_code == 401, blocked.text
        assert remote.refresh_calls == 0


@pytest.mark.parametrize("phase", ["rotation-before-set", "rotation-after-set"])
def test_rotation_storage_failure_never_resends_old_refresh(tmp_path, monkeypatch, phase):
    backend, remote = FaultBackend(), RotationRemote()
    with api(tmp_path, monkeypatch, backend, remote) as first:
        login(first)
        backend.phase = phase
        failed = first.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert failed.status_code == 503, failed.text
        assert remote.spent == ["synthetic-single-use-refresh"]
        saved = user_value(backend)
        if phase == "rotation-before-set":
            assert saved["refresh_token"] == "synthetic-single-use-refresh"
            assert saved["refresh_consumed"] is True
        else:
            assert saved["refresh_token"] == "rotated-1"
            assert saved["refresh_consumed"] is False
    backend.phase = None
    with api(tmp_path, monkeypatch, backend, remote, create=False) as restarted:
        result = restarted.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        if phase == "rotation-before-set":
            assert result.status_code == 401, result.text
            assert remote.refresh_calls == 1
        else:
            # Persisted new token is a distinct usable value despite lost acknowledgement.
            assert result.status_code == 200, result.text
            assert remote.spent == ["synthetic-single-use-refresh", "rotated-1"]
        assert remote.spent.count("synthetic-single-use-refresh") == 1


def test_legacy_json_without_marker_refreshes_once_and_reserves_before_http(tmp_path, monkeypatch):
    backend, remote = Backend(), RotationRemote()
    with api(tmp_path, monkeypatch, backend, remote) as first:
        login(first)
    rewrite_user(backend, lambda value: value.pop("refresh_consumed"))
    assert "refresh_consumed" not in user_value(backend)
    observed = []
    original_handler = remote.handler

    def observe(request):
        if request.url.path.endswith("/oauth/token"):
            observed.append(user_value(backend)["refresh_consumed"])
        return original_handler(request)

    remote.handler = observe
    with api(tmp_path, monkeypatch, backend, remote, create=False) as restarted:
        result = restarted.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert result.status_code == 200, result.text
        assert remote.spent == ["synthetic-single-use-refresh"]
        assert observed == [True]
        assert user_value(backend)["refresh_token"] == "rotated-1"
        assert user_value(backend)["refresh_consumed"] is False


@pytest.mark.parametrize("marker", [None, 2, {}, "not-a-boolean"])
def test_invalid_consumption_marker_fails_closed_without_http(tmp_path, monkeypatch, marker):
    backend, remote = Backend(), Remote(short_token=True)
    with api(tmp_path, monkeypatch, backend, remote) as first:
        login(first)
    rewrite_user(backend, lambda value: value.update(refresh_consumed=marker))
    with api(tmp_path, monkeypatch, backend, remote, create=False) as restarted:
        failed = restarted.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert failed.status_code == 401, failed.text
        assert failed.json()["error"]["code"] == "credential_unreadable"
        assert remote.refresh_calls == 0


@pytest.mark.parametrize("marker", [True, "true", 1, "1"])
def test_true_consumption_representations_never_dispatch(tmp_path, monkeypatch, marker):
    backend, remote = Backend(), Remote(short_token=True)
    with api(tmp_path, monkeypatch, backend, remote) as first:
        login(first)
    rewrite_user(backend, lambda value: value.update(refresh_consumed=marker))
    with api(tmp_path, monkeypatch, backend, remote, create=False) as restarted:
        blocked = restarted.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert blocked.status_code == 401, blocked.text
        assert blocked.json()["error"]["code"] == "token_expired"
        assert remote.refresh_calls == 0


@pytest.mark.parametrize("marker", ["false", 0])
def test_nonboolean_false_marker_is_invalid_stored_state(tmp_path, monkeypatch, marker):
    """The implementation generates JSON booleans; other stored types are corrupt."""
    backend, remote = Backend(), Remote(short_token=True)
    with api(tmp_path, monkeypatch, backend, remote) as first:
        login(first)
    rewrite_user(backend, lambda value: value.update(refresh_consumed=marker))
    with api(tmp_path, monkeypatch, backend, remote, create=False) as restarted:
        rejected = restarted.get("/api/v1/integrations/feishu/materials", headers=HEADERS)
        assert rejected.status_code == 401, rejected.text
        assert rejected.json()["error"]["code"] == "credential_unreadable"
        assert remote.refresh_calls == 0
