"""Item 11 — sweep other entry points for swallowed or flattened causes.

QA-only harness on fixed SHA 19078de. These tests assert the *desired* property
(a provider/exception cause stays visible somewhere the user or support can
reach). Tests that fail are recorded as residual defects.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from summit_everything.integrations.embedding import EmbeddingProviderError
from summit_everything.integrations.llm import LLMProviderError

from qa_common import (
    HEADERS,
    PLAIN_SENTINEL,
    SENTINEL,
    app_client,
    open_workspace,
)

from test_f2_f6_and_hygiene import FailingProvider


def _assist_client(tmp_path: Path, error: BaseException):  # noqa: ANN202
    from summit_everything.intake.review import IntakeReviewService

    client = app_client(tmp_path, review_service=IntakeReviewService(FailingProvider(error)))
    open_workspace(client, tmp_path / "workspace")
    return client


# --- Feishu read paths -----------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/integrations/feishu/status",
        "/api/v1/integrations/feishu/materials",
        "/api/v1/integrations/feishu/calendar?start=2026-01-01T00:00:00Z"
        "&end=2026-01-02T00:00:00Z&timezone=Asia%2FShanghai",
    ],
)
def test_feishu_paths_keep_a_coded_reason(tmp_path: Path, path: str) -> None:
    client = app_client(tmp_path)
    open_workspace(client, tmp_path / "workspace")
    response = client.get(path, headers=HEADERS)
    assert response.status_code in {200, 401, 403, 422, 503}, response.text
    if response.status_code != 200:
        error = response.json()["error"]
        assert error["code"], error
        assert error["message"].strip(), error
        # The code must be a designed value, not the generic request_error.
        assert error["code"] != "request_error", error


# --- settings / credentials ------------------------------------------------


def test_settings_and_credential_paths_keep_coded_reasons(tmp_path: Path) -> None:
    client = app_client(tmp_path)
    open_workspace(client, tmp_path / "workspace")
    bad_shape = client.put(
        "/api/v1/credentials/dashscope",
        headers=HEADERS,
        json={"account_id": "default", "secret": "sk-" + "a" * 600},
    )
    assert bad_shape.status_code == 422, bad_shape.text
    assert bad_shape.json()["error"]["code"] == "credential_shape_invalid"

    bad_settings = client.patch(
        "/api/v1/settings", headers=HEADERS, json={"mode": "not-a-mode"}
    )
    assert bad_settings.status_code == 422, bad_settings.text
    assert bad_settings.json()["error"]["code"] == "validation_error"


# --- memory / roles / conversations ---------------------------------------


def test_memory_and_role_write_paths_keep_coded_reasons(tmp_path: Path) -> None:
    client = app_client(tmp_path)
    open_workspace(client, tmp_path / "workspace")
    for method, path, body in [
        ("post", "/api/v1/roles", {"name": "", "operation_id": "qa-role"}),
        ("post", "/api/v1/memory/candidates", {"text": "", "operation_id": "qa-memory"}),
    ]:
        response = getattr(client, method)(path, headers=HEADERS, json=body)
        assert response.status_code == 422, (path, response.text)
        assert response.json()["error"]["code"] == "validation_error", (path, response.text)


def test_conversation_read_of_unknown_id_is_coded(tmp_path: Path) -> None:
    client = app_client(tmp_path)
    open_workspace(client, tmp_path / "workspace")
    response = client.get(f"/api/v1/conversations/{uuid4()}", headers=HEADERS)
    assert response.status_code in {404, 422}, response.text
    error = response.json()["error"]
    assert error["code"] not in {"request_error", ""}, error


# --- validate my own SweepResult: unknown assist exception in a typed shape -


def test_sweep_typed_assist_error_that_sanitizes_to_sk_star_star_star(tmp_path: Path) -> None:
    """Same defect class as R1, stated on the assist entry point.

    A provider message that was masked by ``sanitize_provider_text`` becomes
    ``sk-***``; that value still contains ``sk-`` and is rejected by the
    diagnostics guard, so no local record is written.
    """
    from summit_everything.integrations.http_boundary import sanitize_provider_text

    masked = sanitize_provider_text(f"bad key {SENTINEL}") or ""
    assert "sk-" in masked
    error = LLMProviderError(
        f"模型服务返回错误：invalid_api_key — {masked}",
        provider_code="invalid_api_key",
        provider_message=masked,
        request_id="req-sweep",
        reason="provider",
    )
    client = _assist_client(tmp_path, error)
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    assert response.status_code == 502, response.text
    assert SENTINEL not in response.text

    log = tmp_path / "profile" / "diagnostics.log"
    assert log.exists(), "no diagnostics.log at all after a typed assist failure"
    events = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]
    assert any(event["event"] == "assistant_failed" for event in events), events


def test_sweep_embedding_provider_error_text_is_sanitized_everywhere(tmp_path: Path) -> None:
    """A credential-shaped embedding failure never echoes the raw secret."""
    error = EmbeddingProviderError(
        f"向量服务返回错误：invalid_api_key — {PLAIN_SENTINEL} sk-qa-sweep-abcdefghijklmnop",
        provider_code="invalid_api_key",
        provider_message="Invalid API-key provided.",
        request_id="req-sweep",
        reason="provider",
    )
    client = _assist_client(tmp_path, error)
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    assert response.status_code == 502, response.text
    assert "sk-qa-sweep-abcdefghijklmnop" not in response.text
    # The secret must never reach the diagnostics file *if* one was written.
    # (Whether a file exists at all for this failure is the R1 defect.)
    for path in (tmp_path / "profile").rglob("diagnostics.log"):
        assert "sk-qa-sweep-abcdefghijklmnop" not in path.read_text(encoding="utf-8")
