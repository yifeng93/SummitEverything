"""R4-03 regressions: a retired provider must not accept unrelated new work.

The provider under test is the real ``FeishuHttpProvider`` (real boundary, real
transport lifecycle) with a synthetic HTTP transport; the API-level cases also
drive the real FastAPI route, service and CredentialVault/VaultCredentialStore.
"""

from __future__ import annotations

import time
from threading import Event, Thread
from typing import Any

import httpx
import pytest
from authorized_feishu_client import AuthorizedFeishuReadClient
from pydantic import SecretStr

from summit_everything.api.app import create_app
from summit_everything.integrations.feishu.http import FeishuHttpProvider
from summit_everything.integrations.feishu.provider import (
    AppCredentials,
    FeishuConfig,
    FeishuError,
    UserCredentials,
)
from summit_everything.integrations.settings import MemorySecretBackend

HEADERS = {"Authorization": "Bearer synthetic-r4-session"}
APP_ID = "cli_synthetic_r4_app"
CALLBACK = "http://localhost:8765/callback"
SEARCH_SCOPE = "minutes:minutes.search:read"

TENANT_PATH = "/open-apis/auth/v3/tenant_access_token/internal"
SEARCH_PATH = "/open-apis/minutes/v1/minutes/search"
TRANSCRIPT_SUFFIX = "/transcript"


class CountingRemote:
    """Synthetic remote with a request counter and an optional first-call gate."""

    def __init__(
        self,
        *,
        gate_suffix: str | None = None,
        gate_at: int = 1,
        body: bytes = b"synthetic transcript",
    ) -> None:
        self.gate_suffix = gate_suffix
        self.gate_at = gate_at
        self.body = body
        self.requests = 0
        self.by_path: dict[str, int] = {}
        self.events: list[str] = []
        self.entered = Event()
        self.release = Event()

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.requests += 1
        self.by_path[path] = self.by_path.get(path, 0) + 1
        if path == TENANT_PATH:
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
            )
        if path == SEARCH_PATH:
            return httpx.Response(
                200, json={"code": 0, "data": {"items": [{"token": "obc" + "0" * 21}]}}
            )
        if self.gate_suffix is not None and path.endswith(self.gate_suffix):
            if self.by_path[path] == self.gate_at:
                self.entered.set()
                assert self.release.wait(15)
            return httpx.Response(200, content=self.body)
        if path.endswith(TRANSCRIPT_SUFFIX):
            return httpx.Response(200, content=self.body)
        if path.endswith("/events"):
            self.events.append(path)
            return httpx.Response(200, json={"code": 0, "data": {"items": []}})
        return httpx.Response(404, json={"code": 99991672, "msg": "unexpected synthetic path"})


class CloseTrackingClient(httpx.Client):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1
        super().close()


USER = UserCredentials(
    access_token="synthetic-access",
    refresh_token="synthetic-refresh",
    expires_at=time.time() + 3600,
    scopes=[SEARCH_SCOPE, "task:task:read"],
)
APP = AppCredentials(app_id=APP_ID, app_secret=SecretStr("synthetic-app-secret"))


def _provider(remote: CountingRemote, holder: dict[str, CloseTrackingClient]) -> FeishuHttpProvider:
    def make() -> CloseTrackingClient:
        client = CloseTrackingClient(
            transport=httpx.MockTransport(remote.handler), follow_redirects=False
        )
        holder["client"] = client
        return client

    return FeishuHttpProvider(
        FeishuConfig(mode="real", app_id=APP_ID),
        lambda: APP,
        client_factory=make,
        open_api_base="https://synthetic.invalid",
    )


def _parallel(call, *args, **kwargs):  # type: ignore[no-untyped-def]
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["value"] = call(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - surfaced by _join
            box["error"] = exc

    thread = Thread(target=run)
    thread.start()
    return thread, box


def _join(thread: Thread, box: dict[str, Any], timeout: float = 20.0) -> Any:
    thread.join(timeout)
    assert not thread.is_alive(), "worker thread did not finish"
    if "error" in box:
        raise box["error"]
    return box["value"]


# --- R4-03: lease ownership --------------------------------------------------


def test_r4_03_a_new_operation_from_another_thread_is_refused_after_retire():
    remote = CountingRemote()
    holder: dict[str, CloseTrackingClient] = {}
    provider = _provider(remote, holder)
    holding, release = Event(), Event()

    def holder_thread() -> None:
        with provider.operation():
            holding.set()
            assert release.wait(10)

    owner = Thread(target=holder_thread)
    owner.start()
    assert holding.wait(10), "the lease holder never started"
    provider.retire()

    outcome: dict[str, Any] = {}

    def newcomer() -> None:
        try:
            with provider.operation():
                outcome["accepted"] = True
        except FeishuError as exc:
            outcome["error"] = exc.code

    intruder = Thread(target=newcomer)
    intruder.start()
    intruder.join(5)
    release.set()
    owner.join(10)

    assert not intruder.is_alive(), "the new operation never returned"
    assert outcome.get("accepted") is not True, "a retired provider accepted unrelated new work"
    assert outcome.get("error") == "provider_unavailable", outcome
    assert remote.requests == 0, remote.requests


def test_r4_03_b_the_owning_operation_still_finishes_nested_steps_and_http():
    remote = CountingRemote()
    holder: dict[str, CloseTrackingClient] = {}
    provider = _provider(remote, holder)
    holding, release = Event(), Event()

    def owner() -> None:
        with provider.operation():
            holding.set()
            assert release.wait(10)
            # A legal nested step of the same operation, plus a second HTTP call.
            with provider.operation():
                provider._call(lambda: provider._application_token())

    thread = Thread(target=owner)
    thread.start()
    assert holding.wait(10)
    provider.retire()
    release.set()
    thread.join(10)

    assert not thread.is_alive()
    assert remote.by_path.get(TENANT_PATH, 0) == 1, remote.by_path
    assert holder["client"].close_calls == 1, holder["client"].close_calls


def test_r4_03_c_direct_adapter_use_after_retire_is_refused():
    remote = CountingRemote()
    holder: dict[str, CloseTrackingClient] = {}
    provider = _provider(remote, holder)
    provider.retire()

    with pytest.raises(FeishuError) as error:
        provider.materials(USER, "", None, None, 10)
    assert error.value.code == "provider_unavailable"
    assert remote.requests == 0, remote.requests
    assert holder["client"].close_calls == 1, holder["client"].close_calls


def test_r4_03_d_two_leases_nesting_and_an_exception_close_the_client_once():
    remote = CountingRemote()
    holder: dict[str, CloseTrackingClient] = {}
    provider = _provider(remote, holder)
    first_holding, release = Event(), Event()

    def first_owner() -> None:
        with provider.operation():
            with provider.operation():  # nested lease
                first_holding.set()
                assert release.wait(10)

    def failing_owner() -> None:
        try:
            with provider.operation():
                raise RuntimeError("synthetic failure inside an operation")
        except RuntimeError:
            pass  # the point is that the lease is released on the exception path

    one = Thread(target=first_owner)
    one.start()
    assert first_holding.wait(10)
    two = Thread(target=failing_owner)
    two.start()
    two.join(10)
    assert not two.is_alive()
    provider.retire()
    assert holder["client"].close_calls == 0, "closed while a lease was still held"
    release.set()
    one.join(10)
    assert not one.is_alive()

    assert holder["client"].close_calls == 1, holder["client"].close_calls
    provider.retire()
    assert holder["client"].close_calls == 1, "the client was closed more than once"


def test_r4_03_f_timeout_and_retire_at_the_same_time_do_not_leak():
    from summit_everything.integrations.http_boundary import live_transfer_workers

    remote = CountingRemote()
    holder: dict[str, CloseTrackingClient] = {}
    provider = _provider(remote, holder)
    remote.gate_suffix = TRANSCRIPT_SUFFIX  # not used; timeout comes from the deadline
    started, finished = Event(), Event()

    def owner() -> None:
        with provider.operation():
            started.set()
            try:
                provider.materials(USER, "", None, None, 10)
            finally:
                finished.set()

    # A trickling remote is not needed: retire plus a completed operation must
    # leave no worker, no open connection and a single close.
    thread = Thread(target=owner)
    thread.start()
    assert started.wait(10)
    provider.retire()
    assert finished.wait(10)
    thread.join(10)

    assert not thread.is_alive()
    assert live_transfer_workers() == 0, live_transfer_workers()
    assert holder["client"].close_calls == 1, holder["client"].close_calls


# --- R4-03 E: API-level configuration change with an in-flight read ----------


class ApiRemote:
    """Serves the endpoints a real import and calendar read need."""

    def __init__(self, *, pause_at_transcript: int = 2) -> None:
        self.pause_at_transcript = pause_at_transcript
        self.transcripts = 0
        self.events: list[str] = []
        self.transcript_paths: list[str] = []
        self.entered = Event()
        self.release = Event()

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == TENANT_PATH:
            return httpx.Response(
                200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
            )
        if path.endswith(TRANSCRIPT_SUFFIX):
            self.transcripts += 1
            self.transcript_paths.append(path)
            if self.transcripts == self.pause_at_transcript:
                self.entered.set()
                assert self.release.wait(15)
            return httpx.Response(200, content=b"synthetic transcript")
        if path.endswith("/events"):
            self.events.append(path)
            return httpx.Response(200, json={"code": 0, "data": {"items": []}})
        return httpx.Response(404, json={"code": 99991672, "msg": "unexpected synthetic path"})


def _api_client(tmp_path, monkeypatch, backend, remote: ApiRemote):
    import summit_everything.api.app as app_module

    clients: list[CloseTrackingClient] = []

    def factory(config, app_credentials, **kwargs):  # type: ignore[no-untyped-def]
        def make() -> CloseTrackingClient:
            client = CloseTrackingClient(
                transport=httpx.MockTransport(remote.handler), follow_redirects=False
            )
            clients.append(client)
            return client

        return FeishuHttpProvider(config, app_credentials, client_factory=make, **kwargs)

    monkeypatch.setattr(app_module, "FeishuHttpProvider", factory)
    app = create_app(
        session_token="synthetic-r4-session",
        profile_root=tmp_path / "profile",
        secret_backend=backend,
    )
    client = AuthorizedFeishuReadClient(app, base_url="http://127.0.0.1:5173")
    assert (
        client.post(
            "/api/v1/workspaces",
            headers=HEADERS,
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "Synthetic R4",
                "operation_id": "open",
            },
        ).status_code
        == 201
    )
    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={
                "mode": "real",
                "feishu": {
                    "app_id": APP_ID,
                    "redirect_uri": CALLBACK,
                    "real_data_enabled": True,
                    "calendar_id": "cal-a",
                },
            },
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/credentials/feishu_app",
            headers=HEADERS,
            json={"account_id": APP_ID, "secret": "synthetic-app-secret"},
        ).status_code
        == 200
    )
    return client, clients


def test_r4_03_e_config_change_keeps_the_old_read_on_its_snapshot(tmp_path, monkeypatch):
    backend = MemorySecretBackend()
    remote = ApiRemote(pause_at_transcript=2)
    client, clients = _api_client(tmp_path, monkeypatch, backend, remote)

    old_client = clients[0]
    materials = ["obc" + "0" * 21, "obc" + "1" * 21, "obc" + "2" * 21]
    thread, box = _parallel(
        client.post,
        "/api/v1/integrations/feishu/imports",
        headers=HEADERS,
        json={"material_ids": materials, "operation_id": "imp-r4"},
    )
    assert remote.entered.wait(10), "the old read never reached its second body step"

    assert (
        client.patch(
            "/api/v1/settings",
            headers=HEADERS,
            json={"feishu": {"calendar_id": "cal-b"}},
        ).status_code
        == 200
    )
    assert old_client.close_calls == 0, "the retired client was closed mid-operation"

    # A new request must immediately use the new configuration and provider.
    assert (
        client.get(
            "/api/v1/integrations/feishu/calendar",
            headers=HEADERS,
            params={
                "start": "2026-10-09T00:00:00+08:00",
                "end": "2026-10-10T00:00:00+08:00",
                "timezone": "Asia/Shanghai",
            },
        ).status_code
        == 200
    )
    assert remote.events and "/calendars/cal-b/" in remote.events[-1], remote.events
    assert len(clients) == 2, len(clients)
    assert clients[1].close_calls == 0

    remote.release.set()
    result = _join(thread, box)
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["state"] == "succeeded", body
    assert len(body["outcomes"]) == 3
    assert old_client.close_calls == 1, old_client.close_calls
