"""Standard stdio MCP bridge to this application's authenticated loopback API."""

from __future__ import annotations

import asyncio
import ipaddress
import os
import stat
import sys
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlsplit
from uuid import UUID

import httpx
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field


class MCPConfigurationError(RuntimeError):
    """A safe, user-facing local setup problem."""


class MCPAPIError(RuntimeError):
    def __init__(self, status: int, code: str, message: str) -> None:
        self.status = status
        self.code = code
        super().__init__(f"{code}: {message}")


def _token() -> str:
    value = os.environ.get("SUMMIT_MCP_TOKEN")
    if value is not None:
        token = value
    else:
        token_file = os.environ.get("SUMMIT_MCP_TOKEN_FILE")
        if not token_file:
            raise MCPConfigurationError("请设置 SUMMIT_MCP_TOKEN 或 SUMMIT_MCP_TOKEN_FILE。")
        token_path = Path(token_file)
        try:
            info = token_path.lstat()
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) & 0o077
            ):
                raise MCPConfigurationError("token 文件必须归当前用户所有，权限不宽于 0600。")
            token = token_path.read_text(encoding="utf-8")
            token = token.rstrip("\r\n")
        except OSError:
            raise MCPConfigurationError("无法安全读取 token 文件。") from None
    if not token or any(
        not (char.isascii() and (char.isalnum() or char in "-_.~")) for char in token
    ):
        raise MCPConfigurationError("token 不能为空，且只能包含安全 ASCII token 字符。")
    return token


def _base_url() -> str:
    raw = os.environ.get("SUMMIT_API_URL", "http://127.0.0.1:8793")
    try:
        parsed = urlsplit(raw)
        address = ipaddress.ip_address(parsed.hostname or "")
    except ValueError as exc:
        raise MCPConfigurationError("SUMMIT_API_URL 必须使用有效的 loopback IP 地址。") from exc
    if not address.is_loopback or parsed.scheme != "http" or parsed.username or parsed.password:
        raise MCPConfigurationError("SUMMIT_API_URL 仅允许无凭据的 HTTP loopback 地址。")
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        raise MCPConfigurationError("SUMMIT_API_URL 不得包含路径、查询或片段。")
    return raw.rstrip("/")


class Bridge:
    def __init__(self) -> None:
        self.base = _base_url()
        self.client: httpx.AsyncClient | None = None
        self.workspace_id = os.environ.get("SUMMIT_WORKSPACE_ID", "")

    async def request(self, method: str, path: str, **kwargs: Any) -> object:
        if path.startswith("/") or ".." in Path(path).parts or "?" in path or "#" in path:
            raise MCPConfigurationError("MCP API 路径无效。")
        if self.client is None:
            raise RuntimeError("MCP bridge 尚未完成认证初始化")
        headers = dict(kwargs.pop("headers", {}) or {})
        if self.workspace_id:
            headers["X-Summit-Workspace-Id"] = self.workspace_id
        response = await self.client.request(method, f"/{path}", headers=headers, **kwargs)
        if response.is_redirect:
            raise MCPAPIError(response.status_code, "redirect_rejected", "本机 API 重定向已拒绝。")
        if response.is_error:
            try:
                envelope = response.json()
            except ValueError:
                envelope = {}
            detail = envelope.get("detail", envelope.get("error", {}))
            code = detail.get("code", "api_error") if isinstance(detail, dict) else "api_error"
            message = (
                detail.get("message", "本机 API 请求失败。")
                if isinstance(detail, dict)
                else "本机 API 请求失败。"
            )
            raise MCPAPIError(response.status_code, str(code), str(message))
        return response.json()

    async def bind(self) -> None:
        self.client = httpx.AsyncClient(
            base_url=self.base,
            headers={"Authorization": f"Bearer {_token()}"},
            trust_env=False,
            follow_redirects=False,
            timeout=15.0,
        )
        result = await self.request("GET", "api/v1/agent/workspace")
        workspace_id = str(result["workspace_id"])  # type: ignore[index]
        if self.workspace_id and self.workspace_id != workspace_id:
            raise RuntimeError("当前工作库与预期 workspace_id 不一致")
        self.workspace_id = workspace_id


bridge: Bridge | None = None


def _active_bridge() -> Bridge:
    if bridge is None:
        raise RuntimeError("MCP bridge 尚未完成启动")
    return bridge


mcp = FastMCP(
    "SummitEverything", instructions="只访问当前绑定的本机工作库；正式页面必须由应用用户确认。"
)
READ = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
WRITE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
)
CALENDAR = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=False,
    idempotentHint=False,
    openWorldHint=True,
)


@mcp.tool(annotations=READ)
async def workspace_status() -> dict[str, object]:
    """读取当前工作库身份和索引状态；不读取凭据或调用模型。"""
    current = _active_bridge()
    workspace = await current.request("GET", "api/v1/agent/workspace/bound")
    status = await current.request("GET", "api/v1/agent/index")
    return {"workspace": workspace, "index": status}


@mcp.tool(annotations=READ)
async def list_lines() -> object:
    """列出知识主线。"""
    return await _active_bridge().request("GET", "api/v1/agent/lines")


@mcp.tool(annotations=READ)
async def list_projects() -> object:
    """列出项目目录。"""
    return await _active_bridge().request("GET", "api/v1/agent/projects")


@mcp.tool(annotations=READ)
async def list_confirmed_pages() -> object:
    """列出当前版本已确认且符合检索资格的知识页面。"""
    return await _active_bridge().request("GET", "api/v1/agent/pages")


@mcp.tool(annotations=READ)
async def search_confirmed_knowledge(query: str, limit: int = 10) -> object:
    """使用本机 LanceDB BM25 搜索，并在返回前按当前页面版本重验资格；不调用模型。"""
    if not 1 <= limit <= 30:
        raise ValueError("limit 必须介于 1 到 30")
    return await _active_bridge().request(
        "GET", "api/v1/agent/search", params={"q": query, "limit": limit}
    )


@mcp.tool(annotations=READ)
async def read_confirmed_page(page_id: str, content_sha256: str) -> object:
    """按版本读取已确认知识正文；外部改动或未确认内容会被拒绝。"""
    UUID(page_id)
    if len(content_sha256) != 64:
        raise ValueError("content_sha256 必须是 64 位 SHA-256")
    return await _active_bridge().request(
        "GET", f"api/v1/agent/pages/{page_id}", params={"expected_content_sha256": content_sha256}
    )


@mcp.tool(annotations=WRITE)
async def import_text(text: str, filename: str, operation_id: str) -> object:
    """将 UTF-8 文本幂等保存到待整理收件箱；不会调用模型或自动整理。"""
    return await _active_bridge().request(
        "POST",
        "api/v1/agent/import",
        json={
            "text": text,
            "filename": filename,
            "operation_id": operation_id,
        },
    )


@mcp.tool(annotations=READ)
async def list_intake() -> object:
    """列出收件箱材料及处理状态。"""
    return await _active_bridge().request("GET", "api/v1/agent/intake")


@mcp.tool(annotations=READ)
async def read_source(source_id: str) -> object:
    """读取选定的收件箱原件；结果是未确认来源材料，不是可信知识。"""
    UUID(source_id)
    return await _active_bridge().request("GET", f"api/v1/agent/sources/{source_id}")


@mcp.tool(annotations=CALENDAR)
async def list_calendar(
    start: str,
    end: str,
    timezone: str,
    approved_plan_id: str | None = None,
    limit: Annotated[int, Field(strict=True, ge=1, le=30)] = 20,
    cursor: str = "",
) -> object:
    """读取授权身份可访问的有界飞书日历。旧计划 ID 可选传入，仅为调用兼容，不签发或消费计划。"""
    if approved_plan_id is not None:
        UUID(approved_plan_id)
    params: dict[str, str | int] = {
        "start": start,
        "end": end,
        "timezone": timezone,
        "limit": limit,
    }
    if cursor:
        params["cursor"] = cursor
    return await _active_bridge().request("GET", "api/v1/agent/calendar", params=params)


@mcp.tool(annotations=READ)
async def list_pending_drafts() -> object:
    """列出等待应用用户审核的稿件。"""
    return await _active_bridge().request("GET", "api/v1/agent/drafts")


@mcp.tool(annotations=READ)
async def get_draft(draft_id: str) -> object:
    """读取待审稿完整正文和版本号。"""
    UUID(draft_id)
    return await _active_bridge().request("GET", f"api/v1/agent/drafts/{draft_id}")


@mcp.tool(annotations=WRITE)
async def create_draft(
    operation_id: str,
    item_ids: list[str],
    line_id: str,
    project_id: str,
    title: str,
    kind: str,
    body: str,
    target_page_id: str = "",
    expected_base_sha256: str = "",
) -> object:
    """提交完整待审稿，可关联收件箱材料或现有页面；稿件保持待审，不会入库。"""
    for value in [*item_ids, line_id, project_id]:
        UUID(value)
    payload: dict[str, object] = {
        "operation_id": operation_id,
        "item_ids": item_ids,
        "line_id": line_id,
        "project_id": project_id,
        "title": title,
        "kind": kind,
        "body": body,
    }
    if target_page_id:
        UUID(target_page_id)
        payload["target_page_id"] = target_page_id
        payload["expected_base_sha256"] = expected_base_sha256
    return await _active_bridge().request("POST", "api/v1/agent/drafts", json=payload)


@mcp.tool(annotations=WRITE)
async def edit_draft(
    draft_id: str,
    expected_version: Annotated[int, Field(strict=True, ge=1)],
    title: str,
    body: str,
    target_page_id: str = "",
    expected_base_sha256: str = "",
) -> object:
    """按稿件版本编辑待审稿；版本冲突返回 409，仍需应用用户审核。"""
    UUID(draft_id)
    payload: dict[str, object] = {
        "expected_version": expected_version,
        "title": title,
        "body": body,
    }
    if target_page_id:
        UUID(target_page_id)
        payload["target_page_id"] = target_page_id
        payload["expected_base_sha256"] = expected_base_sha256
    return await _active_bridge().request("PATCH", f"api/v1/agent/drafts/{draft_id}", json=payload)


def _enable_strict_tool_arguments() -> None:
    """FastMCP 1.x defaults generated argument models to extra=ignore."""
    for registered_tool in mcp._tool_manager.list_tools():
        registered_tool.fn_metadata.arg_model.model_config["extra"] = "forbid"
        registered_tool.fn_metadata.arg_model.model_rebuild(force=True)
        registered_tool.parameters["additionalProperties"] = False


_enable_strict_tool_arguments()


async def main() -> None:
    global bridge
    current = Bridge()
    bridge = current
    try:
        await current.bind()
        await mcp.run_stdio_async()
    finally:
        if current.client is not None:
            await current.client.aclose()


def _report_startup_error(exc: Exception) -> None:
    if isinstance(exc, MCPConfigurationError):
        print(f"SummitEverything MCP 配置错误：{exc}", file=sys.stderr)
    elif isinstance(exc, MCPAPIError):
        if exc.status == 401:
            message = "API token 无效或已过期。"
        elif exc.code == "workspace_not_open":
            message = "请先在 SummitEverything 应用中打开工作库。"
        else:
            message = f"本机 API 拒绝 MCP 连接（HTTP {exc.status}，{exc.code}）。"
        print(f"SummitEverything MCP 启动失败：{message}", file=sys.stderr)
    elif isinstance(exc, httpx.ConnectError):
        print(
            "SummitEverything MCP 启动失败：无法连接本机 API，请确认应用已启动。",
            file=sys.stderr,
        )
    else:
        print(f"SummitEverything MCP 启动失败：{type(exc).__name__}", file=sys.stderr)


def run_cli() -> int:
    try:
        asyncio.run(main())
    except Exception as exc:
        _report_startup_error(exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(run_cli())
