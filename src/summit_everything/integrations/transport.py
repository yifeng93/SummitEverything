"""Request-owned HTTP transport with cancellable DNS and an overall deadline.

Each request owns its async pool and DNS resolver. Cancelling one request cannot
close another request's connection, and no synchronous getaddrinfo worker can
send an HTTP request after the deadline. The sync facade also works inside the
FastAPI event loop; its non-daemon runner is always joined before returning.
"""

from __future__ import annotations

import asyncio
import ipaddress
import socket
import ssl
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from threading import Lock, Thread
from time import monotonic
from typing import Any

import aiodns
import httpcore
import httpx

_lock = Lock()
_running = 0


def live_transfer_workers() -> int:
    with _lock:
        return _running


class _DNSBackend(httpcore.AsyncNetworkBackend):
    def __init__(self) -> None:
        self.streams: list[httpcore.AsyncNetworkStream] = []

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: float | None = None,
        local_address: str | None = None,
        socket_options: Iterable[Any] | None = None,
    ) -> httpcore.AsyncNetworkStream:
        async with asyncio.timeout(timeout):
            try:
                ipaddress.ip_address(host)
                addresses = [host]
            except ValueError:
                async with aiodns.DNSResolver() as resolver:
                    try:
                        result = await resolver.getaddrinfo(
                            host, port=port, type=socket.SOCK_STREAM
                        )
                    except aiodns.error.DNSError:
                        raise httpcore.ConnectError("provider name resolution failed") from None
                    try:
                        addresses = list(
                            dict.fromkeys(
                                str(
                                    ipaddress.ip_address(
                                        node.addr[0].decode("ascii")
                                        if isinstance(node.addr[0], bytes)
                                        else node.addr[0]
                                    )
                                )
                                for node in result.nodes
                            )
                        )
                    except (ValueError, UnicodeError, TypeError, IndexError):
                        raise httpcore.ConnectError(
                            "provider name resolution returned invalid addresses"
                        ) from None
            if not addresses:
                raise httpcore.ConnectError("provider name resolution returned no addresses")
            backend = httpcore.AnyIOBackend()
            last_error: Exception | None = None
            for address in addresses:
                try:
                    stream = await backend.connect_tcp(
                        address,
                        port,
                        timeout,
                        local_address,
                        socket_options,
                    )
                    # Own TCP even before HTTPcore installs the TLS connection.
                    self.streams.append(stream)
                    return stream
                except httpcore.ConnectError as exc:
                    last_error = exc
            raise httpcore.ConnectError("provider connection failed") from last_error


@asynccontextmanager
async def _network_backend() -> AsyncIterator[_DNSBackend]:
    backend = _DNSBackend()
    try:
        yield backend
    finally:
        for stream in backend.streams:
            await stream.aclose()


class _ResponseStream(httpx.AsyncByteStream):
    def __init__(self, response: httpcore.Response) -> None:
        self.response = response

    async def __aiter__(self) -> AsyncIterator[bytes]:
        async for chunk in self.response.aiter_stream():
            yield chunk

    async def aclose(self) -> None:
        await self.response.aclose()


class DeadlineTransport(httpx.BaseTransport):
    """Single-attempt transport; request extensions carry budget and size limit."""

    def __init__(self) -> None:
        self._closed = False
        self._ssl_context = ssl.create_default_context()

    def close(self) -> None:
        self._closed = True

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if self._closed:
            raise httpx.TransportError("provider transport is closed")
        started = monotonic()
        deadline = request.extensions.get("summit_deadline_seconds", 30.0)
        maximum = request.extensions.get("summit_max_response_bytes", 2 * 1024 * 1024)
        result: dict[str, Any] = {}

        async def read() -> httpx.Response:
            remaining = None if deadline is None else deadline - (monotonic() - started)
            async with (
                _network_backend() as backend,
                httpcore.AsyncConnectionPool(
                    ssl_context=self._ssl_context,
                    network_backend=backend,
                    retries=0,
                    max_connections=1,
                    max_keepalive_connections=0,
                ) as pool,
            ):
                async with asyncio.timeout(remaining):
                    core_request = httpcore.Request(
                        request.method,
                        str(request.url),
                        headers=request.headers.raw,
                        content=request.read(),
                        extensions=request.extensions,
                    )
                    core_response = await pool.handle_async_request(core_request)
                    response = httpx.Response(
                        core_response.status,
                        headers=core_response.headers,
                        stream=_ResponseStream(core_response),
                        request=request,
                    )
                    body = bytearray()
                    try:
                        if response.headers.get(
                            "content-encoding", "identity"
                        ).lower().strip() not in {"", "identity"}:
                            raise ValueError("provider response uses unsupported content encoding")
                        async for chunk in response.aiter_raw():
                            if len(body) + len(chunk) > maximum:
                                raise ValueError("provider response exceeded the size limit")
                            body.extend(chunk)
                    finally:
                        await response.aclose()
                    # The body is already decoded and bounded. Do not decode it a
                    # second time when returning through HTTPX's sync interface.
                    headers = [
                        (key, value)
                        for key, value in core_response.headers
                        if key.lower()
                        not in (b"content-encoding", b"content-length", b"transfer-encoding")
                    ]
                    headers.append((b"content-length", str(len(body)).encode()))
                    return httpx.Response(
                        core_response.status,
                        headers=headers,
                        content=bytes(body),
                        request=request,
                    )

        def transfer() -> None:
            global _running
            with _lock:
                _running += 1
            try:
                result["response"] = asyncio.run(read())
            except BaseException as exc:
                result["error"] = exc
            finally:
                with _lock:
                    _running -= 1

        worker = Thread(target=transfer, name="summit-http-transfer", daemon=False)
        worker.start()
        worker.join()
        if "error" in result:
            error = result["error"]
            if isinstance(error, (TimeoutError, httpcore.TimeoutException)):
                raise TimeoutError("provider request exceeded the overall deadline") from None
            if isinstance(
                error, (httpcore.NetworkError, httpcore.ProtocolError, httpcore.UnsupportedProtocol)
            ):
                raise httpx.TransportError("provider transport failed") from None
            raise error
        response: httpx.Response = result["response"]
        return response


def create_http_client() -> httpx.Client:
    return httpx.Client(transport=DeadlineTransport(), trust_env=False, follow_redirects=False)
