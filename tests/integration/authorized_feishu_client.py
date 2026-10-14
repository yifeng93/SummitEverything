"""Test client helper for legacy synthetic Feishu adapter conformance tests.

The wrapped GET still executes the original product route. It first creates and
confirms a one-shot plan through the public API for that exact synthetic scope.
Gate-specific tests use a plain TestClient so unplanned requests remain denied.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient


class AuthorizedFeishuReadClient(TestClient):
    def _create_and_confirm(
        self, operation: str, scope: dict[str, Any], headers: Any
    ) -> str | None:
        created = super().post(
            "/api/v1/acceptance-plans",
            headers=headers,
            json={"operation": operation, "scope": scope},
        )
        if created.status_code != 201:
            return None
        plan = created.json()["plan"]
        confirmed = super().post(
            f"/api/v1/acceptance-plans/{plan['plan_id']}/confirm",
            headers=headers,
            json={"scope_sha256": plan["scope_sha256"]},
        )
        return plan["plan_id"] if confirmed.status_code == 200 else None

    def get(self, url: Any, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        path = urlsplit(str(url)).path
        request_params = kwargs.get("params")
        params: dict[str, Any] = dict(parse_qs(urlsplit(str(url)).query, keep_blank_values=True))
        # URL query values arrive as singleton lists; TestClient params can be
        # mappings or sequences. Normalize both to the values FastAPI receives.
        params = {
            key: value[-1] if isinstance(value, list) else value for key, value in params.items()
        }
        if isinstance(request_params, Mapping):
            params.update(request_params)
        elif request_params:
            params.update(dict(request_params))

        operation: str | None = None
        scope: dict[str, Any] | None = None
        if path == "/api/v1/integrations/feishu/materials":
            operation = "feishu.materials.read"
            scope = {
                "query": params.get("query", ""),
                "visibility": params.get("visibility"),
                "cursor": params.get("cursor"),
                "limit": int(params.get("limit", 20)),
            }
        elif path == "/api/v1/integrations/feishu/calendar":
            operation = "feishu.calendar.read"
            scope = {
                "start": params.get("start"),
                "end": params.get("end"),
                "timezone": params.get("timezone"),
                "cursor": params.get("cursor"),
                "limit": int(params.get("limit", 20)),
            }
        elif path == "/api/v1/integrations/feishu/tasks":
            operation = "feishu.tasks.read"
            scope = {"cursor": params.get("cursor"), "limit": int(params.get("limit", 20))}
        elif path.startswith("/api/v1/integrations/feishu/tasks/"):
            operation = "feishu.task.read"
            scope = {"task_guid": path.rsplit("/", 1)[-1]}

        if operation is not None and scope is not None and "plan_id" not in params:
            request_headers = kwargs.get("headers")
            plan_id = self._create_and_confirm(operation, scope, request_headers)
            if plan_id:
                params["plan_id"] = plan_id
                kwargs["params"] = params

        return super().get(url, *args, **kwargs)

    def post(self, url: Any, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        path = urlsplit(str(url)).path
        payload = kwargs.get("json")
        params = dict(kwargs.get("params") or {})
        if path == "/api/v1/integrations/feishu/imports" and isinstance(payload, dict):
            operation = "feishu.materials.import"
            scope = {
                "material_ids": payload.get("material_ids", []),
                "operation_id": payload.get("operation_id"),
            }
            plan_id = self._create_and_confirm(operation, scope, kwargs.get("headers"))
            if plan_id:
                params["plan_id"] = plan_id
                kwargs["params"] = params
        return super().post(url, *args, **kwargs)
