"""Offline protocol tests for the real Feishu HTTP adapter.

Only ``httpx.MockTransport`` and synthetic payloads are used. No real Feishu
request, credential or Keychain item is touched.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest
from pydantic import SecretStr

from summit_everything.integrations.feishu.http import (
    CALENDAR_EVENTS_PATH,
    CALENDAR_PRIMARY_PATH,
    MINUTES_ARTIFACTS_PATH,
    MINUTES_SEARCH_PATH,
    MINUTES_TRANSCRIPT_PATH,
    TASK_PATH,
    TASKS_PATH,
    TENANT_TOKEN_PATH,
    TOKEN_PATH,
    FeishuHttpProvider,
)
from summit_everything.integrations.feishu.provider import (
    AppCredentials,
    FeishuConfig,
    FeishuError,
    UserCredentials,
)
from summit_everything.integrations.feishu.tasks import ProviderDue

APP_ID = "cli_synthetic_app"
APP_SECRET = "synthetic-app-secret"
USER = UserCredentials(
    access_token="u-synthetic-user-token",
    refresh_token="r-synthetic-refresh",
    expires_at=2_000_000_000,
    scopes=["minutes:minutes.search:read", "task:task:read"],
)


class Recorder:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []


def _config(**overrides: Any) -> FeishuConfig:
    values: dict[str, Any] = {
        "mode": "real",
        "app_id": APP_ID,
        "identity": "app",
        "calendar_id": "feishu.cn_synthetic@group.calendar.feishu.cn",
    }
    values.update(overrides)
    return FeishuConfig(**values)


def _provider(
    handler: Any,
    recorder: Recorder | None = None,
    *,
    config: FeishuConfig | None = None,
    app_secret: str | None = APP_SECRET,
    clock: Any = None,
) -> FeishuHttpProvider:
    def wrapped(request: httpx.Request) -> httpx.Response:
        if recorder is not None:
            recorder.requests.append(request)
        return handler(request)

    kwargs: dict[str, Any] = {}
    if clock is not None:
        kwargs["clock"] = clock
    return FeishuHttpProvider(
        config or _config(),
        lambda: (
            None
            if app_secret is None
            else AppCredentials(app_id=APP_ID, app_secret=SecretStr(app_secret))
        ),
        client=httpx.Client(transport=httpx.MockTransport(wrapped), follow_redirects=False),
        **kwargs,
    )


def _tenant(request: httpx.Request) -> httpx.Response:
    assert request.url.path == TENANT_TOKEN_PATH
    return httpx.Response(
        200, json={"code": 0, "tenant_access_token": "t-synthetic", "expire": 7200}
    )


def test_authorization_url_uses_documented_accounts_endpoint():
    provider = _provider(lambda request: httpx.Response(500))
    url = provider.authorization_url("http://localhost:8765/callback", "synthetic-state")
    assert url.startswith("https://accounts.feishu.cn/open-apis/authen/v1/authorize?")
    assert f"client_id={APP_ID}" in url
    assert "response_type=code" in url
    assert "state=synthetic-state" in url
    assert "scope=" in url and "offline_access" in url


def test_code_exchange_posts_documented_json_and_parses_tokens():
    recorder = Recorder()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == TOKEN_PATH
        body = request.read().decode()
        assert "authorization_code" in body and "synthetic-code" in body
        assert APP_ID in body and APP_SECRET in body
        return httpx.Response(
            200,
            json={
                "code": 0,
                "access_token": "u-new",
                "refresh_token": "r-new",
                "expires_in": 7200,
                "scope": "offline_access task:task:read",
                "token_type": "Bearer",
            },
        )

    credentials = _provider(handler, recorder).exchange(
        "synthetic-code", "http://localhost:8765/callback"
    )
    assert credentials.access_token == "u-new"
    assert credentials.refresh_token == "r-new"
    assert credentials.scopes == ["offline_access", "task:task:read"]
    assert len(recorder.requests) == 1


def test_exchange_requires_app_secret_fail_closed():
    provider = _provider(lambda request: httpx.Response(500), app_secret=None)
    with pytest.raises(FeishuError) as error:
        provider.exchange("synthetic-code", "http://localhost:8765/callback")
    assert error.value.code == "credential_missing"


def test_refresh_rotates_token_and_reports_invalid_grant_as_expired():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": 0,
                "access_token": "u-rotated",
                "refresh_token": "r-rotated",
                "expires_in": 3600,
                "scope": "task:task:read",
                "token_type": "Bearer",
            },
        )

    rotated = _provider(handler).refresh(USER)
    assert rotated.refresh_token == "r-rotated"
    assert rotated.scopes == ["task:task:read"]

    invalid = _provider(
        lambda request: httpx.Response(
            400, json={"error": "invalid_grant", "error_description": "expired"}
        )
    )
    with pytest.raises(FeishuError) as error:
        invalid.refresh(USER)
    assert error.value.code == "token_expired"


def test_minutes_search_requires_user_token_and_paginates():
    recorder = Recorder()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TENANT_TOKEN_PATH:
            return _tenant(request)
        assert request.url.path == MINUTES_SEARCH_PATH
        # Minutes search documents user_access_token only.
        assert request.headers["authorization"] == f"Bearer {USER.access_token}"
        assert request.url.params["page_size"] == "2"
        assert request.url.params.get("page_token") == "cursor-1"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "items": [
                        {"token": "obc" + "0" * 21, "display_info": "产品<h>周会</h>纪要"},
                        {"token": "obd" + "0" * 21, "display_info": "设计评审"},
                    ],
                    "has_more": True,
                    "page_token": "cursor-2",
                },
            },
        )

    page = _provider(handler, recorder).materials(USER, "", None, "cursor-1", 2)
    assert [item.title for item in page.items] == ["产品周会纪要", "设计评审"]
    assert page.next_cursor == "cursor-2"
    assert page.items[0].updated_at is None


def test_minutes_search_refuses_undocumented_visibility_filter():
    provider = _provider(lambda request: httpx.Response(500))
    with pytest.raises(FeishuError) as error:
        provider.materials(USER, "", "owner", None, 10)
    assert error.value.code == "unsupported_capability"


def test_minutes_error_codes_map_to_readable_failures():
    def denied(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 2094011, "msg": "identity not found"})

    with pytest.raises(FeishuError) as error:
        _provider(denied).materials(USER, "", None, None, 10)
    assert error.value.code == "token_expired"

    def no_scope(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 2091005, "msg": "permission deny"})

    with pytest.raises(FeishuError) as scope_error:
        _provider(no_scope).body(USER, "obc" + "0" * 21)
    assert scope_error.value.code == "missing_scope"


def test_transcript_download_uses_tenant_identity_and_bounded_bytes():
    recorder = Recorder()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TENANT_TOKEN_PATH:
            return _tenant(request)
        assert request.url.path == MINUTES_TRANSCRIPT_PATH.format(token="obc" + "0" * 21)
        assert request.url.params["file_format"] == "txt"
        assert request.headers["authorization"] == "Bearer t-synthetic"
        return httpx.Response(200, content=b"synthetic transcript text")

    body = _provider(handler, recorder).body(USER, "obc" + "0" * 21)
    assert body.raw == b"synthetic transcript text"
    assert body.filename.endswith(".txt")
    assert body.content_type.startswith("text/plain")
    assert recorder.requests[0].url.path == TENANT_TOKEN_PATH


def test_transcript_falls_back_to_artifacts_on_missing_scope():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path == TENANT_TOKEN_PATH:
            return _tenant(request)
        if request.url.path.endswith("/transcript"):
            return httpx.Response(200, json={"code": 2091005, "msg": "permission deny"})
        assert request.url.path == MINUTES_ARTIFACTS_PATH.format(token="obc" + "0" * 21)
        return httpx.Response(200, json={"code": 0, "data": {"transcript": "逐字稿正文"}})

    body = _provider(handler).body(USER, "obc" + "0" * 21)
    assert body.raw.decode("utf-8") == "逐字稿正文"
    assert calls[-1].endswith("/artifacts")


def test_calendar_range_is_seconds_and_rejects_pagination_cursor():
    recorder = Recorder()
    start = datetime(2026, 10, 9, tzinfo=UTC)
    end = start + timedelta(days=1)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TENANT_TOKEN_PATH:
            return _tenant(request)
        assert request.url.params["start_time"] == str(int(start.timestamp()))
        assert request.url.params["end_time"] == str(int(end.timestamp()))
        assert int(request.url.params["page_size"]) >= 50
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "items": [
                        {
                            "event_id": "evt-1",
                            "summary": "合成日程",
                            "start_time": {"timestamp": "1602504000", "timezone": "Asia/Shanghai"},
                            "end_time": {"timestamp": "1602507600", "timezone": "Asia/Shanghai"},
                        },
                        {
                            "event_id": "evt-2",
                            "summary": "全天日程",
                            "start_time": {"date": "2026-10-09"},
                            "end_time": {"date": "2026-10-10"},
                        },
                    ]
                },
            },
        )

    page = _provider(handler, recorder).calendar(USER, start, end, "Asia/Shanghai", None, 20)
    assert [event.event_id for event in page.items] == ["evt-1", "evt-2"]
    assert page.items[0].start == datetime.fromtimestamp(1602504000, tz=UTC)
    assert page.items[1].start.date().isoformat() == "2026-10-09"

    with pytest.raises(FeishuError) as error:
        _provider(handler).calendar(USER, start, end, "Asia/Shanghai", "cursor", 20)
    assert error.value.code == "invalid_cursor"


def test_calendar_primary_and_events_are_bounded_to_three_http_calls_without_retry():
    recorder = Recorder()
    start = datetime(2026, 10, 9, tzinfo=UTC)
    end = start + timedelta(days=1)
    calendar_id = "feishu.cn_synthetic@group.calendar.feishu.cn"
    event_path = CALENDAR_EVENTS_PATH.format(calendar_id=calendar_id)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TENANT_TOKEN_PATH:
            return _tenant(request)
        if request.url.path == CALENDAR_PRIMARY_PATH:
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"calendars": [{"calendar": {"calendar_id": calendar_id}}]},
                },
            )
        assert request.url.path == event_path
        return httpx.Response(200, json={"code": 0, "data": {"items": []}})

    config = _config(calendar_id="")
    page = _provider(handler, recorder, config=config).calendar(
        None, start, end, "Asia/Shanghai", None, 20
    )
    assert page.items == []
    assert [request.url.path for request in recorder.requests] == [
        TENANT_TOKEN_PATH,
        CALENDAR_PRIMARY_PATH,
        event_path,
    ]

    recorder = Recorder()

    def timeout_after_primary(request: httpx.Request) -> httpx.Response:
        if request.url.path == TENANT_TOKEN_PATH:
            return _tenant(request)
        if request.url.path == CALENDAR_PRIMARY_PATH:
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"calendars": [{"calendar": {"calendar_id": calendar_id}}]},
                },
            )
        assert request.url.path == event_path
        return httpx.Response(503, json={"code": 100, "msg": "synthetic unavailable"})

    with pytest.raises(FeishuError) as error:
        _provider(timeout_after_primary, recorder, config=config).calendar(
            None, start, end, "Asia/Shanghai", None, 20
        )
    assert error.value.code == "provider_unavailable"
    assert [request.url.path for request in recorder.requests] == [
        TENANT_TOKEN_PATH,
        CALENDAR_PRIMARY_PATH,
        event_path,
    ]


def test_task_list_uses_user_token_and_maps_due_and_completion():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == TASKS_PATH
        assert request.headers["authorization"] == f"Bearer {USER.access_token}"
        assert request.url.params["type"] == "my_tasks"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "items": [
                        {
                            "guid": "task-1",
                            "summary": "合成任务",
                            "description": "合成描述",
                            "due": {"timestamp": "1675454764000", "is_all_day": True},
                            "completed_at": "0",
                        }
                    ],
                    "has_more": True,
                    "page_token": "next",
                },
            },
        )

    page = _provider(handler).tasks(USER, None, 50)
    assert page.next_cursor == "next"
    assert page.items[0].due == ProviderDue(timestamp=1675454764000, is_all_day=True)
    assert page.items[0].completed_at == 0


def test_task_create_and_patch_post_documented_bodies():
    recorder = Recorder()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == TENANT_TOKEN_PATH:
            return _tenant(request)
        if request.method == "POST":
            assert request.url.path == TASKS_PATH
            assert b'"summary":"\\u5408\\u6210\\u4efb\\u52a1"' in request.read() or (
                "合成任务" in request.read().decode()
            )
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "task": {
                            "guid": "task-created",
                            "summary": "合成任务",
                            "description": "",
                            "completed_at": "0",
                        }
                    },
                },
            )
        assert request.method == "PATCH"
        assert request.url.path == TASK_PATH.format(guid="task-created")
        payload = request.read().decode()
        assert '"update_fields"' in payload and '"completed_at"' in payload
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "task": {
                        "guid": "task-created",
                        "summary": "合成任务",
                        "description": "",
                        "completed_at": "1675742789470",
                    }
                },
            },
        )

    provider = _provider(handler, recorder)
    created = provider.task_create(USER, {"summary": "合成任务", "client_token": "tok-1"})
    assert created.guid == "task-created"
    patched = provider.task_patch(
        USER,
        "task-created",
        {"task": {"completed_at": "1675742789470"}, "update_fields": ["completed_at"]},
        "tok-1",
    )
    assert patched.completed_at == 1675742789470


def test_task_result_is_never_invented():
    provider = _provider(lambda request: httpx.Response(500))
    assert provider.task_result(USER, "tok-1") is None


def test_oversized_response_stops_reading_and_closes():
    delivered = {"bytes": 0}

    class Large(httpx.SyncByteStream):
        def __iter__(self):  # type: ignore[no-untyped-def]
            for _ in range(50):
                delivered["bytes"] += 10_000
                yield b" " * 10_000

    provider = _provider(
        lambda request: httpx.Response(200, stream=Large()),
    )
    provider.max_response_bytes = 100_000
    with pytest.raises(FeishuError) as error:
        provider.materials(USER, "", None, None, 10)
    assert error.value.code == "malformed_response"
    assert delivered["bytes"] <= 110_000


def test_http_200_business_error_and_unavailable_are_sanitized():
    def business_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 2095001, "msg": "leaked-synthetic-provider-body-marker"},
        )

    with pytest.raises(FeishuError) as error:
        _provider(business_error).materials(USER, "", None, None, 10)
    assert error.value.code == "provider_unavailable"
    assert "marker" not in str(error.value)

    def server_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, content=b"synthetic-internal-detail")

    with pytest.raises(FeishuError) as server:
        _provider(server_error).materials(USER, "", None, None, 10)
    assert server.value.code == "provider_unavailable"
    assert "detail" not in str(server.value)


def test_transport_timeout_maps_to_provider_timeout():
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("synthetic timeout")

    with pytest.raises(FeishuError) as error:
        _provider(timeout).tasks(USER, None, 10)
    assert error.value.code == "provider_timeout"


def test_user_identity_mode_uses_user_token_for_app_capable_endpoints():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == MINUTES_TRANSCRIPT_PATH.format(token="obc" + "0" * 21)
        assert request.headers["authorization"] == f"Bearer {USER.access_token}"
        return httpx.Response(200, content=b"transcript")

    provider = _provider(handler, config=_config(identity="user"))
    assert provider.body(USER, "obc" + "0" * 21).raw == b"transcript"
