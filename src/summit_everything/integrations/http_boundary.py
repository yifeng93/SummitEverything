"""Shared bounded, single-attempt HTTP boundary for remote model adapters."""

from __future__ import annotations

import json
from typing import Any

import httpx


def bounded_json_post(
    client: httpx.Client,
    endpoint: str,
    *,
    headers: dict[str, str],
    payload: dict[str, Any],
    max_response_bytes: int,
) -> Any:
    """Read a successful JSON response incrementally and close it on every exit."""
    timeout = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)
    body = bytearray()
    with client.stream(
        "POST", endpoint, headers=headers, json=payload, timeout=timeout
    ) as response:
        if not 200 <= response.status_code < 300:
            raise ValueError("provider returned an unsuccessful response")
        for chunk in response.iter_bytes():
            if len(body) + len(chunk) > max_response_bytes:
                raise ValueError("provider response exceeded the size limit")
            body.extend(chunk)
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        raise ValueError("provider returned invalid JSON") from None
