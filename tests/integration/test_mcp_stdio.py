"""Real MCP stdio client against an isolated FastAPI workspace."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from summit_everything.api.app import create_app


def _text_result(result: Any) -> Any:
    assert not result.isError
    assert result.content
    return json.loads(result.content[0].text)


def test_mcp_stdio_initialize_list_and_draft_cycle(tmp_path: Path) -> None:
    token = "synthetic-mcp-token-123"
    app = create_app(session_token=token, profile_root=tmp_path / "profile")
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="critical", access_log=False)
    )
    thread = threading.Thread(target=lambda: asyncio.run(server.serve()), daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        headers = {"Authorization": f"Bearer {token}"}
        response = httpx.post(
            f"http://127.0.0.1:{port}/api/v1/workspaces",
            headers=headers,
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "MCP 合成验收库",
                "operation_id": "mcp-workspace-create",
            },
        )
        assert response.status_code == 201, response.text
        workspace_id = response.json()["workspace_id"]
        line = httpx.post(
            f"http://127.0.0.1:{port}/api/v1/lines",
            headers=headers,
            json={"name": "演示主线", "operation_id": "line-create"},
        )
        project = httpx.post(
            f"http://127.0.0.1:{port}/api/v1/projects",
            headers=headers,
            json={
                "line_id": line.json()["id"],
                "name": "演示项目",
                "operation_id": "project-create",
            },
        )
        assert line.status_code == 201 and project.status_code == 201

        env = {
            **os.environ,
            "SUMMIT_API_URL": f"http://127.0.0.1:{port}",
            "SUMMIT_MCP_TOKEN": token,
            "SUMMIT_WORKSPACE_ID": workspace_id,
            "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
        }
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "summit_everything.mcp_server"],
            env=env,
            cwd=str(Path(__file__).resolve().parents[2]),
        )

        async def interact() -> None:
            async with stdio_client(params) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    listing = await session.list_tools()
                    tool_map = {tool.name: tool for tool in listing.tools}
                    assert len(tool_map) == 14
                    assert all(
                        tool.inputSchema.get("additionalProperties") is False
                        for tool in listing.tools
                    )
                    assert "list_calendar" in tool_map
                    lines_result = await session.call_tool("list_lines", {})
                    line_result = _text_result(lines_result)
                    if isinstance(line_result, dict):
                        line_result = [line_result]
                    assert line_result[0]["name"] == "演示主线"
                    imported = _text_result(
                        await session.call_tool(
                            "import_text",
                            {
                                "text": "活动安排待确认。",
                                "filename": "notes.txt",
                                "operation_id": "source-import",
                            },
                        )
                    )
                    item_id = imported["item_id"]
                    source_id = imported["source_id"]
                    import_replay = _text_result(
                        await session.call_tool(
                            "import_text",
                            {
                                "text": "活动安排待确认。",
                                "filename": "notes.txt",
                                "operation_id": "source-import",
                            },
                        )
                    )
                    assert import_replay["item_id"] == item_id
                    source = _text_result(
                        await session.call_tool("read_source", {"source_id": source_id})
                    )
                    assert source["source"]["source_id"] == source_id
                    assert source["text"] == "活动安排待确认。"
                    assert source["trust_state"] == "unconfirmed_source_not_knowledge"
                    assert (
                        await session.call_tool(
                            "list_calendar",
                            {
                                "start": "2026-10-29T00:00:00+08:00",
                                "end": "2026-10-30T00:00:00+08:00",
                                "timezone": "Asia/Shanghai",
                                "approved_plan_id": "00000000-0000-0000-0000-000000000001",
                            },
                        )
                    ).isError
                    draft_args = {
                        "operation_id": "draft-create",
                        "item_ids": [item_id],
                        "line_id": line.json()["id"],
                        "project_id": project.json()["id"],
                        "title": "活动安排",
                        "kind": "topic",
                        "body": "日期和地点仍待确认。",
                    }
                    first = _text_result(await session.call_tool("create_draft", draft_args))
                    edited = _text_result(
                        await session.call_tool(
                            "edit_draft",
                            {
                                "draft_id": first["draft_id"],
                                "expected_version": 1,
                                "title": "活动安排修订",
                                "body": "日期仍待确认。",
                            },
                        )
                    )
                    assert edited["version"] == 2
                    replay = _text_result(await session.call_tool("create_draft", draft_args))
                    assert first["draft_id"] == replay["draft_id"]
                    assert replay["body"] == "日期仍待确认。"
                    conflict = dict(draft_args, body="不同正文")
                    assert (await session.call_tool("create_draft", conflict)).isError
                    forged = dict(draft_args, operation_id="forged", approval={"approved": True})
                    assert (await session.call_tool("create_draft", forged)).isError
                    draft = _text_result(
                        await session.call_tool("get_draft", {"draft_id": first["draft_id"]})
                    )
                    assert draft["state"] == "pending" and draft["version"] == 2
                    second_workspace = httpx.post(
                        f"http://127.0.0.1:{port}/api/v1/workspaces",
                        headers=headers,
                        json={
                            "root": str(tmp_path / "other-workspace"),
                            "mode": "create",
                            "name": "切库测试",
                            "operation_id": "other-workspace-create",
                        },
                    )
                    assert second_workspace.status_code == 201
                    assert (await session.call_tool("list_lines", {})).isError
                    assert (await session.call_tool("workspace_status", {})).isError

        asyncio.run(interact())
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _cli_command(entrypoint: str) -> list[str]:
    if entrypoint == "module":
        return [sys.executable, "-m", "summit_everything.mcp_server"]
    if entrypoint == "console_script":
        return [str(Path(sys.executable).with_name("summit-everything-mcp"))]
    raise AssertionError(f"unknown entrypoint: {entrypoint}")


@pytest.mark.parametrize("entrypoint", ["module", "console_script"])
@pytest.mark.parametrize(
    ("api_url", "expected_message"),
    [
        ("http://example.com:8793", "必须使用有效的 loopback IP"),
        ("http://8.8.8.8:8793", "仅允许无凭据的 HTTP loopback"),
        ("http://127.0.0.1:8793/api", "不得包含路径、查询或片段"),
        ("https://127.0.0.1:8793", "仅允许无凭据的 HTTP loopback"),
    ],
)
def test_mcp_invalid_api_url_exits_cleanly(
    tmp_path: Path, entrypoint: str, api_url: str, expected_message: str
) -> None:
    env = {
        **os.environ,
        "SUMMIT_API_URL": api_url,
        "SUMMIT_MCP_TOKEN": "synthetic-mcp-token-123",
        "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
    }
    result = subprocess.run(
        _cli_command(entrypoint),
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert expected_message in result.stderr


@pytest.mark.parametrize("entrypoint", ["module", "console_script"])
def test_mcp_missing_token_exits_cleanly(tmp_path: Path, entrypoint: str) -> None:
    env = {
        **os.environ,
        "SUMMIT_API_URL": "http://127.0.0.1:8793",
        "SUMMIT_MCP_TOKEN": "",
        "SUMMIT_MCP_TOKEN_FILE": "",
        "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
    }
    result = subprocess.run(
        _cli_command(entrypoint),
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert "token 不能为空" in result.stderr


@pytest.mark.parametrize("entrypoint", ["module", "console_script"])
def test_mcp_rejects_bad_token_without_echoing_it(tmp_path: Path, entrypoint: str) -> None:
    secret = "MCP-SENTINEL-SECRET with spaces"
    env = {
        **os.environ,
        "SUMMIT_API_URL": "http://127.0.0.1:8793",
        "SUMMIT_MCP_TOKEN": secret,
        "PYTHONPATH": str(Path(__file__).resolve().parents[2] / "src"),
    }
    result = subprocess.run(
        _cli_command(entrypoint),
        cwd=Path(__file__).resolve().parents[2],
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Traceback" not in result.stderr
    assert secret not in result.stderr
    assert "token 不能为空" in result.stderr
