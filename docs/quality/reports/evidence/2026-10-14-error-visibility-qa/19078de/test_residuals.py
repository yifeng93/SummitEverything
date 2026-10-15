"""Residual-defect probes on fixed SHA 19078de (expected to FAIL).

These tests assert the *desired* behaviour for the same "swallowed cause" class
the round was meant to close. Their failures are the evidence of the residual.

Defect R1/R2/R3/R4: ``profile_event``'s ``_validated_reason`` rejects any reason
that still contains the literal ``sk-`` or that exceeds 200 characters. But
``sanitize_provider_text`` masks a credential *to* ``sk-***`` (still containing
``sk-``), and a provider message is allowed up to 300 characters, so the
rendered reason routinely trips both guards. Every caller wraps the call in
``except (ValueError, OSError): pass``, so the diagnostics event is dropped with
no trace: the credential-bearing / long provider failure leaves no local record.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from summit_everything.integrations.embedding import EmbeddingProviderError, FakeEmbedding
from summit_everything.integrations.llm import LLMProviderError
from summit_everything.integrations.http_boundary import sanitize_provider_text
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore

from qa_common import (
    HEADERS,
    SENTINEL,
    app_client,
    diagnostics_events,
    diagnostics_text,
    open_workspace,
    seed_page,
)

from test_f2_f6_and_hygiene import FailingProvider, _index_once

CREDENTIAL_MESSAGE = sanitize_provider_text(f"bad key {SENTINEL}") or ""
LONG_MESSAGE = "m" * 250


def _assist_error(provider_message: str) -> LLMProviderError:
    return LLMProviderError(
        f"模型服务返回错误：invalid_api_key — {provider_message}",
        provider_code="invalid_api_key",
        provider_message=provider_message,
        request_id="req-cred-1",
        reason="provider",
    )


def _assist(tmp_path: Path, error: BaseException):  # noqa: ANN202
    from summit_everything.intake.review import IntakeReviewService

    client = app_client(tmp_path, review_service=IntakeReviewService(FailingProvider(error)))
    open_workspace(client, tmp_path / "workspace")
    return client


def test_r1_credential_masked_assist_failure_still_leaves_a_local_record(tmp_path: Path) -> None:
    client = _assist(tmp_path, _assist_error(CREDENTIAL_MESSAGE))
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    # The client surface is correct: a sanitized, reasoned 502.
    assert response.status_code == 502, response.text
    assert SENTINEL not in response.text

    # Desired: the local diagnostics file still records that an assist failed.
    events = diagnostics_events(tmp_path / "profile")
    assert any(event["event"] == "assistant_failed" for event in events), (
        "assist failure left NO assistant_failed event at all: "
        f"diagnostics={diagnostics_text(tmp_path / 'profile')!r}"
    )


def test_r2_long_provider_message_still_leaves_a_local_record(tmp_path: Path) -> None:
    client = _assist(tmp_path, _assist_error(LONG_MESSAGE))
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    assert response.status_code == 502, response.text

    events = diagnostics_events(tmp_path / "profile")
    assert any(event["event"] == "assistant_failed" for event in events), (
        "assist failure with a >200-char provider message left NO local record"
    )


class CredentialFailingEmbedding(FakeEmbedding):
    mode = "off"

    def embed(self, text: str, *, fingerprint: str) -> list[float]:
        if self.mode == "credential":
            raise EmbeddingProviderError(
                "向量服务返回错误：invalid_api_key",
                provider_code="invalid_api_key",
                provider_message=CREDENTIAL_MESSAGE,
                request_id="req-cred-1",
                reason="provider",
            )
        if self.mode == "long":
            raise EmbeddingProviderError(
                "向量服务返回错误：invalid_api_key",
                provider_code="invalid_api_key",
                provider_message=LONG_MESSAGE,
                request_id="req-long-1",
                reason="provider",
            )
        return super().embed(text, fingerprint=fingerprint)


def _incremental_write(client) -> object:  # noqa: ANN001
    metadata, _line, _project = seed_page(client)
    return metadata


def _write_new_page(client, metadata) -> object:  # noqa: ANN001
    return client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": {**metadata, "id": str(uuid4()), "title": "残留探针"},
            "body": "独特词苍梧五五。",
            "confirmation_id": "qa-residual-confirmation",
            "operation_id": "qa-residual-write",
        },
    )


def _residual_index_client(tmp_path: Path):  # noqa: ANN202
    embedding = CredentialFailingEmbedding()
    service = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), embedding=embedding)
    client = app_client(tmp_path, query_service=service)
    open_workspace(client, tmp_path / "workspace")
    metadata, _line, _project = seed_page(client)
    _index_once(client, "qa-residual-fingerprint")
    return client, embedding, metadata


def test_r3_credential_masked_index_failure_still_leaves_a_record(tmp_path: Path) -> None:
    client, embedding, metadata = _residual_index_client(tmp_path)
    embedding.mode = "credential"
    response = _write_new_page(client, metadata)
    assert response.status_code == 201, response.text
    assert response.json()["index_update"] == "update_failed"

    events = diagnostics_events(tmp_path / "profile")
    assert any(event["event"] == "index_update_failed" for event in events), (
        "index failure left NO index_update_failed event at all: "
        f"diagnostics={diagnostics_text(tmp_path / 'profile')!r}"
    )


def test_r4_long_provider_message_index_failure_still_leaves_a_record(tmp_path: Path) -> None:
    client, embedding, metadata = _residual_index_client(tmp_path)
    embedding.mode = "long"
    response = _write_new_page(client, metadata)
    assert response.status_code == 201, response.text
    assert response.json()["index_update"] == "update_failed"

    events = diagnostics_events(tmp_path / "profile")
    assert any(event["event"] == "index_update_failed" for event in events), (
        "index failure with a >200-char provider message left NO local record"
    )
