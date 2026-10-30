from __future__ import annotations

import asyncio

from summit_everything import mcp_server


def test_calendar_tool_works_without_plan_and_does_not_forward_legacy_plan_id(monkeypatch):
    class BridgeStub:
        calls = []

        async def request(self, method, path, **kwargs):
            self.calls.append((method, path, kwargs))
            return {"items": [], "timezone": "Asia/Shanghai"}

    bridge = BridgeStub()
    monkeypatch.setattr(mcp_server, "bridge", bridge)
    common = {
        "start": "2026-10-29T00:00:00+08:00",
        "end": "2026-10-30T00:00:00+08:00",
        "timezone": "Asia/Shanghai",
    }

    first = asyncio.run(mcp_server.list_calendar(**common))
    second = asyncio.run(
        mcp_server.list_calendar(
            **common,
            approved_plan_id="00000000-0000-0000-0000-000000000001",
        )
    )

    assert first == second
    assert len(bridge.calls) == 2
    for method, path, kwargs in bridge.calls:
        assert method == "GET"
        assert path == "api/v1/agent/calendar"
        assert "plan_id" not in kwargs["params"]
