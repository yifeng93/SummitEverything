"""Shared bounded, single-attempt HTTP boundary for remote provider adapters.

Every helper reads incrementally, enforces a byte ceiling, honours an overall
deadline, never follows redirects and never retries. Failures raise ValueError
subclasses whose message contains no request body, header or credential.

Provider-side failures raise :class:`ProviderError`, which keeps the provider's
own error code, message and request id in bounded, single-line, credential-free
form so callers can surface a reason instead of a generic failure.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from time import monotonic
from typing import Any

import httpx

from summit_everything.integrations.transport import DeadlineTransport
from summit_everything.integrations.transport import live_transfer_workers as live_transfer_workers

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)

# A provider message is shown to the user, so it is bounded and stripped of
# anything that looks like a credential before it leaves this module.
PROVIDER_TEXT_LIMIT = 300
PROVIDER_CODE_LIMIT = 100
_SECRET_LIKE = re.compile(r"sk-[A-Za-z0-9_-]{8,}")
_IDENTIFIER_SHAPE = re.compile(r"[A-Za-z0-9._:-]{1,200}")


def sanitize_provider_text(value: object, *, limit: int = PROVIDER_TEXT_LIMIT) -> str | None:
    """Collapse provider text to one bounded line without credential shapes."""
    if not isinstance(value, str):
        return None
    collapsed = " ".join(value.split())
    if not collapsed:
        return None
    return _SECRET_LIKE.sub("sk-***", collapsed)[:limit]


def _identifier(value: object) -> str | None:
    if isinstance(value, str) and _IDENTIFIER_SHAPE.fullmatch(value):
        return value
    return None


def provider_error_fields(payload: object) -> tuple[str | None, str | None, str | None]:
    """Read ``(code, message, request_id)`` from either provider error shape.

    DashScope-style bodies carry ``code``/``message``/``request_id`` at the top
    level; OpenAI-compatible bodies nest them under ``error``. Both are accepted
    and sanitized; anything unreadable stays ``None`` rather than being guessed.
    """
    if not isinstance(payload, dict):
        return None, None, None
    request_id = _identifier(getattr(payload, "request_id", None)) or _identifier(
        payload.get("request_id")
    )
    if request_id is None:
        request_id = _identifier(payload.get("id"))
    error = payload.get("error")
    if isinstance(error, dict):
        raw_code = error.get("code") or error.get("type")
        return (
            sanitize_provider_text(raw_code, limit=PROVIDER_CODE_LIMIT),
            sanitize_provider_text(error.get("message")),
            request_id,
        )
    code = payload.get("code")
    if isinstance(code, bool) or code in (None, "", 0, "0"):
        code_value = None
    elif isinstance(code, str):
        code_value = sanitize_provider_text(code, limit=PROVIDER_CODE_LIMIT)
    else:
        code_value = sanitize_provider_text(str(code), limit=PROVIDER_CODE_LIMIT)
    return code_value, sanitize_provider_text(payload.get("message")), request_id


class ProviderError(ValueError):
    """A provider-side failure carrying sanitized, bounded provider details.

    It subclasses ``ValueError`` so adapters and their callers keep working with
    the existing ``except ValueError`` handling, including the M4.2 acceptance
    paths that assert a bare ``ValueError``.

    User-facing text is rendered from the structured fields (``describe`` /
    ``reason``); the free-form ``str(exc)`` is never echoed to a client, because
    arbitrary exception text can carry credentials or local paths.
    """

    def __init__(
        self,
        message: str,
        *,
        provider_code: str | None = None,
        provider_message: str | None = None,
        request_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider_code = provider_code
        self.provider_message = provider_message
        self.request_id = request_id
        self.reason = reason

    def describe(self) -> str:
        return describe_provider_failure(
            provider_code=self.provider_code,
            provider_message=self.provider_message,
            request_id=self.request_id,
        )

    def details(self) -> dict[str, str]:
        return provider_details(
            provider_code=self.provider_code,
            provider_message=self.provider_message,
            request_id=self.request_id,
        )


REASON_TEXT = {
    "transport": "连接失败（请检查网络、代理或证书）",
    "deadline": "请求超时",
    "provider": "服务返回错误",
    "schema": "返回内容不符合应用要求的字段",
}


def describe_provider_failure(
    *,
    provider_code: str | None = None,
    provider_message: str | None = None,
    request_id: str | None = None,
) -> str:
    parts = [part for part in (provider_code, provider_message) if part]
    detail = " — ".join(parts) if parts else "provider did not describe the failure"
    if request_id:
        detail += f"（request {request_id}）"
    return detail


def provider_details(
    *,
    provider_code: str | None = None,
    provider_message: str | None = None,
    request_id: str | None = None,
) -> dict[str, str]:
    details: dict[str, str] = {}
    if provider_code:
        details["code"] = provider_code
    if provider_message:
        details["message"] = provider_message
    if request_id:
        details["request_id"] = request_id
    return details


def describe_failure(service: str, exc: object) -> str:
    """A controlled, credential-free sentence for a typed provider failure.

    Only structured, already-sanitized fields are rendered; when the failure
    carries none (transport, deadline, unclassified) a fixed reason is used.
    Free-form exception text is never included.
    """
    details = getattr(exc, "details", None)
    describe = getattr(exc, "describe", None)
    if callable(details) and callable(describe) and details():
        return f"{service}返回错误：{describe()}"
    reason = getattr(exc, "reason", None)
    return f"{service}不可用：{REASON_TEXT.get(reason or '', '原因未说明')}。"


def provider_failure(status: int, body: bytes) -> ProviderError:
    """A typed failure for a non-2xx provider response with a bounded body."""
    try:
        payload: object = json.loads(body)
    except (ValueError, TypeError):
        payload = None
    code, message, request_id = provider_error_fields(payload)
    return ProviderError(
        f"provider returned an unsuccessful response (HTTP {status})",
        provider_code=code,
        provider_message=message,
        request_id=request_id,
        reason="provider",
    )


class ProviderResponse(dict[str, Any]):
    """Parsed provider JSON with a sanitized transport request identifier."""

    def __init__(self, value: dict[str, Any], request_id: str | None) -> None:
        super().__init__(value)
        self.request_id = request_id


def _bounded_timeout(remaining: float) -> httpx.Timeout:
    """Phase timeouts that never grant a fresh full budget past the deadline."""
    budget = max(0.001, remaining)
    return httpx.Timeout(
        connect=min(DEFAULT_TIMEOUT.connect or 5.0, budget),
        read=min(DEFAULT_TIMEOUT.read or 20.0, budget),
        write=min(DEFAULT_TIMEOUT.write or 10.0, budget),
        pool=min(DEFAULT_TIMEOUT.pool or 5.0, budget),
    )


def _read_once(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None,
    json_body: Any | None,
    files: Any | None,
    max_response_bytes: int,
    timeout: httpx.Timeout,
    deadline_at: float | None,
    clock: Callable[[], float],
    response_box: dict[str, httpx.Response],
) -> tuple[int, bytes]:
    """One bounded read; the caller owns the overall deadline."""
    body = bytearray()
    kwargs: dict[str, Any] = {
        "headers": {**headers, "Accept-Encoding": "identity"},
        "timeout": timeout,
        # Never follow a redirect, even when the injected client would.
        "follow_redirects": False,
        "extensions": {
            "summit_deadline_seconds": None if deadline_at is None else deadline_at - clock(),
            "summit_max_response_bytes": max_response_bytes,
        },
    }
    if params:
        kwargs["params"] = params
    if json_body is not None:
        kwargs["json"] = json_body
    if files is not None:
        kwargs["files"] = files
    with client.stream(method, url, **kwargs) as response:
        response_box["response"] = response
        status = response.status_code
        if response.headers.get("content-encoding", "identity").lower().strip() not in {
            "",
            "identity",
        }:
            raise ValueError("provider response uses unsupported content encoding")
        for chunk in response.iter_bytes():
            if deadline_at is not None and clock() >= deadline_at:
                raise TimeoutError("provider request exceeded the overall deadline")
            if len(body) + len(chunk) > max_response_bytes:
                raise ValueError("provider response exceeded the size limit")
            body.extend(chunk)
        if deadline_at is not None and clock() >= deadline_at:
            raise TimeoutError("provider request exceeded the overall deadline")
    return status, bytes(body)


def _read_bounded(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None,
    json_body: Any | None,
    files: Any | None,
    max_response_bytes: int,
    timeout: httpx.Timeout | None,
    deadline_seconds: float | None,
    clock: Callable[[], float] = monotonic,
    response_box: dict[str, httpx.Response] | None = None,
) -> tuple[int, bytes]:
    # MockTransport is a synthetic external boundary. Live clients must use the
    # request-owned transport; never silently fall back to uncancellable HTTP.
    transport = client._transport_for_url(httpx.URL(url))
    if not isinstance(transport, (DeadlineTransport, httpx.MockTransport)):
        raise ValueError("provider HTTP client requires DeadlineTransport")
    deadline_at = None if deadline_seconds is None else clock() + deadline_seconds
    left = None if deadline_at is None else deadline_at - clock()
    if left is not None and left <= 0:
        raise TimeoutError("provider request exceeded the overall deadline")
    effective = timeout or (DEFAULT_TIMEOUT if left is None else _bounded_timeout(left))
    return _read_once(
        client,
        method,
        url,
        headers=headers,
        params=params,
        json_body=json_body,
        files=files,
        max_response_bytes=max_response_bytes,
        timeout=effective,
        deadline_at=deadline_at,
        clock=clock,
        response_box=response_box if response_box is not None else {},
    )


def bounded_json_post(
    client: httpx.Client,
    endpoint: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    max_response_bytes: int,
    max_request_bytes: int = 1_000_000,
    deadline_seconds: float | None = None,
    clock: Callable[[], float] = monotonic,
) -> Any:
    """Read a successful JSON response incrementally and close it on every exit."""
    # Match HTTPX's wire serialization, including escaping, system prompt and
    # envelope overhead. Reject before entering any external transport.
    if len(httpx.Request("POST", endpoint, json=payload).content) > max_request_bytes:
        raise ValueError("provider request exceeded the size limit")
    response_box: dict[str, httpx.Response] = {}
    try:
        status, body = _read_bounded(
            client,
            "POST",
            endpoint,
            headers=headers,
            params=None,
            json_body=payload,
            files=None,
            max_response_bytes=max_response_bytes,
            timeout=None,
            deadline_seconds=deadline_seconds,
            clock=clock,
            response_box=response_box,
        )
    except TimeoutError:
        raise ProviderError("provider request exceeded the deadline", reason="deadline") from None
    if not 200 <= status < 300:
        # The body was read under the byte ceiling above, so the provider's own
        # code/message can be preserved without unbounded reads.
        raise provider_failure(status, body)
    parsed = _parse_json(body)
    if not isinstance(parsed, dict):
        return parsed
    response = response_box.get("response")
    request_id = None
    if response is not None:
        candidate = next(
            (
                response.headers.get(name)
                for name in ("x-request-id", "request-id", "x-dashscope-request-id")
                if response.headers.get(name)
            ),
            None,
        )
        if candidate and re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", candidate):
            request_id = candidate
    return ProviderResponse(parsed, request_id)


def provider_usage_record(provider: str, response: Any) -> dict[str, Any]:
    usage = response.get("usage") if isinstance(response, dict) else None

    def token_count(*keys: str) -> int | None:
        if not isinstance(usage, dict):
            return None
        for key in keys:
            value = usage.get(key)
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                return value
        return None

    request_id = getattr(response, "request_id", None)
    if request_id is None and isinstance(response, dict):
        candidate = response.get("id")
        if isinstance(candidate, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,200}", candidate):
            request_id = candidate
    input_tokens = token_count("prompt_tokens", "input_tokens")
    output_tokens = token_count("completion_tokens", "output_tokens")
    total_tokens = token_count("total_tokens")
    return {
        "provider": provider,
        "request_id": request_id,
        "usage_reported": input_tokens is not None
        or output_tokens is not None
        or total_tokens is not None,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def reject_business_error(wire: Any) -> None:
    """Reject an HTTP 200 body that carries a provider-side error envelope.

    Some providers report authentication, quota and parameter failures with a
    200 status and a non-zero ``code`` (or an ``error`` field). Those bodies must
    never be parsed as successful results.
    """
    if not isinstance(wire, dict):
        raise ValueError("provider returned an invalid response")
    code = wire.get("code")
    if isinstance(code, bool):
        raise ValueError("provider returned an invalid response")
    if isinstance(code, (int, float)) and code != 0:
        raise _business_error(wire)
    if isinstance(code, str) and code.strip() not in {"", "0"}:
        raise _business_error(wire)
    error = wire.get("error")
    if error not in (None, "", False):
        raise _business_error(wire)


def _business_error(wire: Any) -> ProviderError:
    code, message, request_id = provider_error_fields(wire)
    return ProviderError(
        "provider reported an error response",
        provider_code=code,
        provider_message=message,
        request_id=request_id,
        reason="provider",
    )


def _parse_json(body: bytes) -> Any:
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        raise ValueError("provider returned invalid JSON") from None


def bounded_call(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    json_body: Any | None = None,
    files: Any | None = None,
    max_response_bytes: int = 2 * 1024 * 1024,
    deadline_seconds: float | None = 30.0,
    clock: Callable[[], float] = monotonic,
) -> tuple[int, bytes]:
    """Perform one bounded, non-redirecting, non-retrying request.

    Returns the HTTP status and at most ``max_response_bytes`` of the raw body.
    Transport timeouts propagate as TimeoutError so callers can map them.
    """
    if max_response_bytes <= 0:
        raise ValueError("a positive response size limit is required")
    try:
        return _read_bounded(
            client,
            method,
            url,
            headers=headers,
            params=params,
            json_body=json_body,
            files=files,
            max_response_bytes=max_response_bytes,
            timeout=None,
            deadline_seconds=deadline_seconds,
            clock=clock,
        )
    except TimeoutError:
        raise
    except httpx.TimeoutException:
        raise TimeoutError("provider request timed out") from None
    except httpx.HTTPError:
        raise ValueError("provider transport failed") from None


def bounded_json_call(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    params: dict[str, Any] | None = None,
    json_body: Any | None = None,
    max_response_bytes: int = 2 * 1024 * 1024,
    deadline_seconds: float | None = 30.0,
    require_success: bool = False,
    clock: Callable[[], float] = monotonic,
) -> tuple[int, Any]:
    """Bounded JSON call returning ``(status, parsed_body)``.

    A non-JSON body parses to ``None`` rather than raising so error mapping can
    inspect the status. ``require_success`` rejects non-2xx statuses when set.
    """
    status, body = bounded_call(
        client,
        method,
        url,
        headers=headers,
        params=params,
        json_body=json_body,
        max_response_bytes=max_response_bytes,
        deadline_seconds=deadline_seconds,
        clock=clock,
    )
    if require_success and not 200 <= status < 300:
        raise ValueError("provider returned an unsuccessful response")
    if not body:
        return status, None
    try:
        return status, json.loads(body)
    except (ValueError, TypeError):
        return status, None
