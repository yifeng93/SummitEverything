"""Shared bounded, single-attempt HTTP boundary for remote provider adapters.

Every helper reads incrementally, enforces a byte ceiling, honours an overall
deadline, never follows redirects and never retries. Failures raise ValueError
with a message that contains no request body, header or provider payload.
"""

from __future__ import annotations

import json
import socket
from collections.abc import Callable
from threading import Event, Thread
from time import monotonic
from typing import Any

import httpx

DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)


def _abort(response: httpx.Response) -> None:
    """Force a blocked transfer to stop.

    Closing the httpx response alone does not interrupt an in-flight blocking
    socket read in another thread, so the underlying socket is shut down first.
    """
    sock = _network_socket(response)
    if sock is not None:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            sock.close()
        except OSError:
            pass
    try:
        response.close()
    except Exception:
        pass


def _network_socket(response: httpx.Response) -> Any | None:
    """The real transport socket of a response, when the transport exposes one.

    Mock transports have no network stream, so this returns ``None`` and the
    caller falls back to deadline checks between chunks.
    """
    try:
        stream = response.extensions.get("network_stream")
    except Exception:
        return None
    if stream is None:
        return None
    try:
        return stream.get_extra_info("socket")
    except Exception:
        return None


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
        "headers": headers,
        "timeout": timeout,
        # Never follow a redirect, even when the injected client would.
        "follow_redirects": False,
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
        for chunk in response.iter_bytes():
            if deadline_at is not None and clock() >= deadline_at:
                raise TimeoutError("provider request exceeded the overall deadline")
            if len(body) + len(chunk) > max_response_bytes:
                raise ValueError("provider response exceeded the size limit")
            body.extend(chunk)
        if deadline_at is not None and clock() >= deadline_at:
            raise TimeoutError("provider request exceeded the overall deadline")
    return status, bytes(body)


# How long the deadline runner waits for an aborted transfer to unwind after it
# closes the response. The close aborts the socket, so this is a safety net
# rather than the normal path.
ABORT_GRACE_SECONDS = 5.0


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
) -> tuple[int, bytes]:
    """Read a bounded body under one overall deadline for the whole request.

    The deadline spans connecting, sending, waiting for response headers,
    reading every body chunk (including an empty body) and finishing the read.
    A synchronous httpx request cannot be given a single cancellable timeout,
    because httpcore derives each socket read timeout from the request timeout
    and therefore grants the body a fresh full budget after a slow header wait.
    To make the deadline real, the transfer runs in a worker that the caller can
    *cancel*: when the remaining budget reaches zero the response is closed
    (which aborts the socket) and the worker is joined before the error is
    raised, so no request continues in the background after this returns.
    """
    deadline_at = None if deadline_seconds is None else clock() + deadline_seconds
    left = None if deadline_at is None else deadline_at - clock()
    if left is not None and left <= 0:
        raise TimeoutError("provider request exceeded the overall deadline")
    effective = timeout or (DEFAULT_TIMEOUT if left is None else _bounded_timeout(left))
    if deadline_at is None:
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
            deadline_at=None,
            clock=clock,
            response_box={},
        )

    result: dict[str, Any] = {}
    response_box: dict[str, httpx.Response] = {}
    done = Event()

    def transfer() -> None:
        try:
            result["value"] = _read_once(
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
                response_box=response_box,
            )
        except BaseException as exc:  # noqa: BLE001 - re-raised or discarded by the caller
            result["error"] = exc
        finally:
            done.set()

    worker = Thread(target=transfer, daemon=True)
    worker.start()
    if not done.wait(max(0.0, deadline_at - clock())):
        response = response_box.get("response")
        if response is not None:
            _abort(response)
        worker.join(ABORT_GRACE_SECONDS)
        if worker.is_alive():
            raise TimeoutError("provider request could not be cancelled in time")
        raise TimeoutError("provider request exceeded the overall deadline")
    if "error" in result:
        raise result["error"]
    value = result["value"]
    assert isinstance(value, tuple)
    return value


def bounded_json_post(
    client: httpx.Client,
    endpoint: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    max_response_bytes: int,
    deadline_seconds: float | None = None,
    clock: Callable[[], float] = monotonic,
) -> Any:
    """Read a successful JSON response incrementally and close it on every exit."""
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
        )
    except TimeoutError:
        raise ValueError("provider request exceeded the deadline") from None
    if not 200 <= status < 300:
        raise ValueError("provider returned an unsuccessful response")
    return _parse_json(body)


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
        raise ValueError("provider reported an error response")
    if isinstance(code, str) and code.strip() not in {"", "0"}:
        raise ValueError("provider reported an error response")
    error = wire.get("error")
    if error not in (None, "", False):
        raise ValueError("provider reported an error response")


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
