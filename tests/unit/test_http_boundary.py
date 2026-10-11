"""Bounded HTTP boundary, provider deadline and client-release behavior."""

from __future__ import annotations

import time
from collections.abc import Iterator

import httpx
import pytest

from summit_everything.integrations.http_boundary import (
    bounded_call,
    bounded_json_call,
    bounded_json_post,
    reject_business_error,
)
from summit_everything.retrieval.query import QueryService


def test_bounded_call_stops_at_size_limit_and_never_follows_redirects():
    calls: list[httpx.Request] = []

    class Chunks(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            for _ in range(20):
                yield b"x" * 1_000

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=Chunks(), request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(ValueError, match="size limit"):
        bounded_call(client, "GET", "https://example.invalid/x", headers={}, max_response_bytes=500)
    assert len(calls) == 1


def test_bounded_call_deadline_stops_a_slow_stream():
    class Slow(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            for _ in range(50):
                time.sleep(0.02)
                yield b"x"

    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Slow()))
    )
    started = time.monotonic()
    with pytest.raises(TimeoutError):
        bounded_call(
            client,
            "GET",
            "https://example.invalid/slow",
            headers={},
            deadline_seconds=0.05,
        )
    assert time.monotonic() - started < 2


def test_bounded_json_call_returns_status_and_none_for_invalid_json():
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(503, content=b"not json"))
    )
    status, payload = bounded_json_call(client, "GET", "https://example.invalid/x", headers={})
    assert status == 503
    assert payload is None


def test_bounded_json_post_rejects_unsuccessful_and_invalid_json():
    failure = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(500, content=b"{}"))
    )
    with pytest.raises(ValueError, match="unsuccessful"):
        bounded_json_post(
            failure, "https://example.invalid", headers={}, payload={}, max_response_bytes=1000
        )

    invalid = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"<html>"))
    )
    with pytest.raises(ValueError, match="invalid JSON"):
        bounded_json_post(
            invalid, "https://example.invalid", headers={}, payload={}, max_response_bytes=1000
        )


@pytest.mark.parametrize(
    "wire",
    [
        {"code": 401, "message": "synthetic auth failure"},
        {"code": "401", "message": "synthetic string code"},
        {"error": {"message": "synthetic error object"}},
        {"error": "synthetic error string"},
    ],
)
def test_reject_business_error_blocks_http_200_error_envelopes(wire):
    with pytest.raises(ValueError):
        reject_business_error(wire)


@pytest.mark.parametrize("wire", [{"code": 0}, {}, {"data": []}, {"output": {"results": []}}])
def test_reject_business_error_allows_clean_success_bodies(wire):
    reject_business_error(wire)


class _SpyProvider:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


def test_query_service_closes_owned_providers_once(tmp_path):
    embedding, reranker, answerer = _SpyProvider(), _SpyProvider(), _SpyProvider()
    service = QueryService(
        store=None,  # type: ignore[arg-type]
        embedding=embedding,  # type: ignore[arg-type]
        reranker=reranker,  # type: ignore[arg-type]
        answer_provider=answerer,  # type: ignore[arg-type]
    )
    service.close()
    service.close()
    assert (embedding.closed, reranker.closed, answerer.closed) == (1, 1, 1)


# --- R2-06: the overall deadline covers the whole request lifecycle ---------


class FakeClock:
    """Deterministic clock; tests advance it instead of sleeping."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class _EmptyStream(httpx.SyncByteStream):
    def __init__(self, clock: FakeClock | None = None, delay: float = 0.0) -> None:
        self.clock = clock
        self.delay = delay
        self.closed = False

    def __iter__(self) -> Iterator[bytes]:
        if self.clock is not None and self.delay:
            self.clock.advance(self.delay)
        return iter(())

    def close(self) -> None:
        self.closed = True


def test_r2_06_deadline_covers_waiting_for_response_headers():
    clock = FakeClock()
    stream = _EmptyStream()

    def handler(request: httpx.Request) -> httpx.Response:
        # The response headers only arrive long after the overall deadline.
        clock.advance(0.066)
        return httpx.Response(200, stream=stream, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(TimeoutError):
        bounded_call(
            client,
            "GET",
            "https://example.invalid/slow-headers",
            headers={},
            deadline_seconds=0.01,
            clock=clock,
        )
    assert stream.closed is True


def test_r2_06_deadline_covers_slow_first_byte():
    clock = FakeClock()

    class SlowFirstByte(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            clock.advance(0.05)
            yield b"x"

    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=SlowFirstByte()))
    )
    with pytest.raises(TimeoutError):
        bounded_call(
            client,
            "GET",
            "https://example.invalid/slow-first-byte",
            headers={},
            deadline_seconds=0.01,
            clock=clock,
        )


def test_r2_06_deadline_covers_sustained_small_chunks():
    clock = FakeClock()

    class Trickle(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            while True:
                clock.advance(0.004)
                yield b"x"

    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Trickle()))
    )
    with pytest.raises(TimeoutError):
        bounded_call(
            client,
            "GET",
            "https://example.invalid/trickle",
            headers={},
            deadline_seconds=0.01,
            clock=clock,
        )


def test_r2_06_normal_empty_body_within_the_deadline_is_accepted():
    clock = FakeClock()
    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=_EmptyStream()))
    )
    status, body = bounded_call(
        client,
        "GET",
        "https://example.invalid/empty",
        headers={},
        deadline_seconds=5.0,
        clock=clock,
    )
    assert status == 200 and body == b""


def test_r2_06_oversized_response_still_fails_with_a_deadline_set():
    clock = FakeClock()

    class Big(httpx.SyncByteStream):
        def __iter__(self) -> Iterator[bytes]:
            for _ in range(10):
                yield b"x" * 1000

    client = httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Big()))
    )
    with pytest.raises(ValueError, match="size limit"):
        bounded_call(
            client,
            "GET",
            "https://example.invalid/big",
            headers={},
            max_response_bytes=500,
            deadline_seconds=5.0,
            clock=clock,
        )


def test_r2_06_injected_client_must_not_follow_redirects():
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(302, headers={"Location": "https://example.invalid/elsewhere"})

    # A caller-supplied client that would otherwise follow redirects.
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=True)
    status, body = bounded_call(
        client,
        "GET",
        "https://example.invalid/redirect",
        headers={},
        deadline_seconds=5.0,
    )
    assert status == 302 and body == b""
    assert calls == ["https://example.invalid/redirect"], calls
