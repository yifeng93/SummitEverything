"""Independent QA harness for D1 (silently dropped diagnostic events).

Black-box: drives the real FastAPI endpoints over TestClient, then reads the
profile ``diagnostics.log`` off disk and inspects the raw bytes/lines.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app, record_diagnostic
from summit_everything.intake.review import IntakeReviewService
from summit_everything.integrations.embedding import EmbeddingProviderError, FakeEmbedding
from summit_everything.integrations.http_boundary import sanitize_provider_text
from summit_everything.integrations.llm import LLMProviderError
from summit_everything.integrations.settings import MemorySecretBackend
from summit_everything.local import event_log
from summit_everything.local.event_log import clean_reason
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore

TOKEN = "qa-synthetic-session"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

RAW_KEY = "sk-abcdefghijklmnop"
MASKED = "sk-***"
# The realistic provider echo: the key is already masked by the HTTP boundary.
MASKED_ECHO = "Authentication Fails, Your api key: sk-*** is invalid"


# ---------------------------------------------------------------- helpers


def diagnostics_text(profile_root: Path) -> str:
    files = sorted(profile_root.rglob("diagnostics.log"))
    return "\n".join(path.read_text(encoding="utf-8") for path in files)


def diagnostics_events(profile_root: Path) -> list[dict[str, object]]:
    text = diagnostics_text(profile_root).strip()
    return [json.loads(line) for line in text.splitlines() if line]


def diagnostics_raw_lines(profile_root: Path) -> list[str]:
    text = diagnostics_text(profile_root).strip()
    return [line for line in text.splitlines() if line]


def open_workspace(client: TestClient, root: Path) -> None:
    opened = client.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={"root": str(root), "mode": "create", "name": "模拟库", "operation_id": "ws"},
    )
    assert opened.status_code == 201, opened.text


class FailingProvider:
    def __init__(self, error: BaseException) -> None:
        self.error = error

    def organize(self, inputs: object) -> list[object]:  # noqa: ANN001
        raise self.error


def assist_client(profile: Path, error: BaseException) -> TestClient:
    return TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=profile,
            review_service=IntakeReviewService(FailingProvider(error)),
            secret_backend=MemorySecretBackend(),
        )
    )


def assist_expect_failure(profile: Path, error: BaseException, tmp_path: Path) -> None:
    client = assist_client(profile, error)
    open_workspace(client, tmp_path / "workspace")
    response = client.post("/api/v1/journal/assist", headers=HEADERS, json={"text": "合成日志正文"})
    assert response.status_code == 502, response.text


class RaisingEmbedding(FakeEmbedding):
    """FakeEmbedding that starts failing on demand with a chosen error."""

    def __init__(self, error: BaseException) -> None:
        super().__init__()
        self.error = error
        self.fail = False

    def embed(self, text: str, *, fingerprint: str) -> list[float]:
        if self.fail:
            raise self.error
        return super().embed(text, fingerprint=fingerprint)


def index_expect_failure(profile: Path, tmp_path: Path, error: BaseException) -> None:
    """Drive a real incremental index failure through POST /api/v1/pages."""
    embedding = RaisingEmbedding(error)
    service = QueryService(IndexStore(profile / "index.sqlite3"), embedding=embedding)
    client = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=profile,
            query_service=service,
            secret_backend=MemorySecretBackend(),
        )
    )
    open_workspace(client, tmp_path / "workspace")
    line = client.post(
        "/api/v1/lines", headers=HEADERS, json={"name": "合成线", "operation_id": "line"}
    ).json()
    project = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={"line_id": line["id"], "name": "合成项目", "operation_id": "project"},
    ).json()
    metadata = {
        "id": str(uuid4()),
        "title": "基线知识",
        "role": "knowledge",
        "kind": "topic",
        "line_id": line["id"],
        "project_id": project["id"],
    }
    baseline = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": metadata,
            "body": "稳定内容琥珀四二。",
            "confirmation_id": "base-confirmation",
            "operation_id": "base-write",
        },
    )
    assert baseline.status_code == 201, baseline.text
    plan = client.post(
        "/api/v1/index/plans",
        headers=HEADERS,
        json={"mode": "initial", "fingerprint": "qa-failure-v1"},
    ).json()
    assert client.post("/api/v1/index/jobs", headers=HEADERS, json=plan).status_code == 200

    embedding.fail = True
    failed = client.post(
        "/api/v1/pages",
        headers=HEADERS,
        json={
            "metadata": {**metadata, "id": str(uuid4()), "title": "中断知识"},
            "body": "新内容不应从旧索引引用独特词海蓝八六。",
            "confirmation_id": "new-confirmation",
            "operation_id": "new-write",
        },
    )
    assert failed.status_code == 201, failed.text
    assert failed.json()["index_update"] == "update_failed", failed.text


# The tracked test labels this "258 characters"; measured it is 278. Test the
# exact 258-char case from the brief *and* the tracked test's real 278-char value.
TRACKED_LONG_MESSAGE = "Invalid API-key provided. " + "detail " * 36
LONG_MESSAGE = "Invalid API-key provided. " + "x" * (258 - 26)


# ------------------------------------------- item 2: trigger A (masked key)


@pytest.mark.parametrize("endpoint", ["assist", "index"])
def test_trigger_a_masked_key_event_is_written(tmp_path: Path, endpoint: str) -> None:
    profile = tmp_path / "profile"
    error = LLMProviderError(
        "模型服务返回错误：invalid_api_key — masked",
        provider_code="invalid_api_key",
        provider_message=MASKED_ECHO,
        reason="provider",
    )
    if endpoint == "assist":
        assist_expect_failure(profile, error, tmp_path)
        expected_event = "assistant_failed"
    else:
        index_expect_failure(profile, tmp_path, error)
        expected_event = "index_update_failed"

    events = diagnostics_events(profile)
    assert events, "no diagnostic event was written at all"
    assert events[-1]["event"] == expected_event
    assert events[-1]["state"] == "failed"
    reason = str(events[-1]["reason"])
    assert MASKED in reason, reason
    assert len(reason) <= 200
    assert RAW_KEY not in diagnostics_text(profile)


def test_trigger_a_realistic_boundary_masking_then_record(tmp_path: Path) -> None:
    """The exact composition the live boundary produces: mask first, then record."""
    raw_echo = "Authentication Fails, Your api key: sk-abcdefghijklmnop is invalid"
    sanitized = sanitize_provider_text(raw_echo)
    assert sanitized == MASKED_ECHO, sanitized
    profile = tmp_path / "profile"
    error = LLMProviderError(
        "模型服务返回错误：invalid_api_key",
        provider_code="invalid_api_key",
        provider_message=sanitized,
        reason="provider",
    )
    assist_expect_failure(profile, error, tmp_path)
    events = diagnostics_events(profile)
    assert events[-1]["event"] == "assistant_failed"
    assert MASKED in str(events[-1]["reason"])
    assert RAW_KEY not in diagnostics_text(profile)


# ---------------------------------------------- item 3: trigger B (>200 chars)


@pytest.mark.parametrize("endpoint", ["assist", "index"])
@pytest.mark.parametrize(
    "message",
    [LONG_MESSAGE, TRACKED_LONG_MESSAGE],
    ids=["exactly-258", "tracked-278"],
)
def test_trigger_b_long_reason_event_is_written_and_truncated(
    tmp_path: Path, endpoint: str, message: str
) -> None:
    assert len(message) > 200
    LONG_MESSAGE_LEN = len(message)
    profile = tmp_path / "profile"
    error = LLMProviderError(
        "模型服务返回错误：invalid_api_key — long",
        provider_code="invalid_api_key",
        provider_message=message,
        reason="provider",
    )
    if endpoint == "assist":
        assist_expect_failure(profile, error, tmp_path)
        expected_event = "assistant_failed"
    else:
        index_expect_failure(profile, tmp_path, error)
        expected_event = "index_update_failed"

    events = diagnostics_events(profile)
    assert events, "no diagnostic event was written at all"
    assert events[-1]["event"] == expected_event
    reason = str(events[-1]["reason"])
    assert 0 < len(reason) <= 200, len(reason)
    # An un-truncated message would leak past the ceiling.
    assert reason != message, f"reason was not truncated ({len(reason)} vs {LONG_MESSAGE_LEN})"
    assert "invalid_api_key" in reason or "Invalid API-key" in reason


# ------------------------------- item 4: safety constraints are not relaxed


@pytest.mark.parametrize("endpoint", ["assist", "index"])
def test_unmasked_credential_is_masked_before_it_reaches_disk(
    tmp_path: Path, endpoint: str
) -> None:
    profile = tmp_path / "profile"
    # Bypasses the HTTP boundary: this is defense in depth inside the log itself.
    error = LLMProviderError(
        f"模型服务返回错误：invalid_api_key — leaked {RAW_KEY} now",
        provider_code="invalid_api_key",
        provider_message=f"leaked {RAW_KEY} now",
        reason="provider",
    )
    if endpoint == "assist":
        assist_expect_failure(profile, error, tmp_path)
    else:
        index_expect_failure(profile, tmp_path, error)

    text = diagnostics_text(profile)
    assert text, "no diagnostic event was written at all"
    assert RAW_KEY not in text, "unmasked credential reached diagnostics.log"
    assert MASKED in text
    events = diagnostics_events(profile)
    assert MASKED in str(events[-1]["reason"])
    assert len(str(events[-1]["reason"])) <= 200


def test_newlines_are_collapsed_to_one_line_on_disk(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    record_diagnostic(
        profile,
        "assistant_failed",
        state="failed",
        reason="line one\nline two\r\nline three\ttabbed",
    )
    lines = diagnostics_raw_lines(profile)
    assert len(lines) == 1, lines
    assert "\n" not in json.loads(lines[0])["reason"]
    assert json.loads(lines[0])["reason"] == "line one line two line three tabbed"


@pytest.mark.parametrize("reason", ["", "   ", "\t\n ", None, 5, b"bytes", ["list"]])
def test_empty_or_non_string_reason_still_lands_as_fallback(
    tmp_path: Path, reason: object
) -> None:
    profile = tmp_path / "profile"
    record_diagnostic(profile, "assistant_failed", state="failed", reason=reason)
    events = diagnostics_events(profile)
    assert [event["event"] for event in events] == ["assistant_failed"]
    assert events[0]["reason"] == "unrecorded"


def test_profile_event_still_refuses_empty_and_non_string(tmp_path: Path) -> None:
    for reason in ("", "   ", "\t\n ", 5, b"bytes"):
        with pytest.raises(ValueError):
            event_log.profile_event(
                tmp_path, "assistant_failed", state="failed", reason=reason  # type: ignore[arg-type]
            )
    # ``None`` is *not* a refusal: it means "no reason field at all".
    event_log.profile_event(tmp_path, "assistant_failed", state="failed", reason=None)
    assert "reason" not in json.loads(diagnostics_raw_lines(tmp_path)[0])


def test_profile_event_whitelist_and_metadata_still_enforced(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        event_log.profile_event(tmp_path, "not_an_event", state="failed")
    with pytest.raises(ValueError):
        event_log.profile_event(tmp_path, "assistant_failed", state="nonsense")
    with pytest.raises(ValueError):
        event_log.profile_event(tmp_path, "assistant_failed", record_id="bad id!")
    with pytest.raises(ValueError):
        event_log.profile_event(tmp_path, "assistant_failed", count=-1)
    # No file is created by a rejected event.
    assert not (tmp_path / "diagnostics.log").exists()


def test_no_secret_ever_lands_even_when_masking_runs_after_truncation_input() -> None:
    """Masking must happen before truncation, so a key near the cut is still gone."""
    reason = "x" * 190 + " " + RAW_KEY + " tail"
    cleaned = clean_reason(reason)
    assert len(cleaned) <= 200
    assert RAW_KEY not in cleaned
    assert MASKED in cleaned


# ------------------------- item 5: no other silent-drop path must remain


def test_other_profile_event_call_sites_fail_loudly_not_silently(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The remaining (reason-less) call sites must not swallow a log failure."""
    import summit_everything.api.app as app_module

    def boom(*args: object, **kwargs: object) -> None:
        raise ValueError("synthetic diagnostic refusal")

    monkeypatch.setattr(app_module, "profile_event", boom)
    client = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
        )
    )
    open_workspace(client, tmp_path / "workspace")
    with pytest.raises(ValueError):
        client.post(
            "/api/v1/intake/items",
            headers=HEADERS,
            json={"text": "合成收件箱正文", "operation_id": "intake-1"},
        )


def test_record_diagnostic_survives_double_refusal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Even if cleaning refuses everything, the fallback attempt must be made."""
    calls: list[str] = []
    real = event_log.profile_event

    def wrapped(profile: Path, event: str, **kwargs: object) -> None:
        calls.append(str(kwargs.get("reason")))
        real(profile, event, **kwargs)  # type: ignore[arg-type]

    import summit_everything.api.app as app_module

    monkeypatch.setattr(app_module, "profile_event", wrapped)
    profile = tmp_path / "profile"
    record_diagnostic(profile, "assistant_failed", state="failed", reason="   ")
    assert calls == ["   ", "unrecorded"], calls
    assert diagnostics_events(profile)[0]["reason"] == "unrecorded"


def test_record_diagnostic_only_swallows_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import summit_everything.api.app as app_module

    def os_boom(*args: object, **kwargs: object) -> None:
        raise OSError("synthetic disk failure")

    monkeypatch.setattr(app_module, "profile_event", os_boom)
    # A disk failure may be swallowed (diagnostics must not mask the real error)...
    record_diagnostic(tmp_path, "assistant_failed", state="failed", reason="x")

    def type_boom(*args: object, **kwargs: object) -> None:
        raise TypeError("unexpected programming error")

    monkeypatch.setattr(app_module, "profile_event", type_boom)
    # ...but an unexpected error type must still surface.
    with pytest.raises(TypeError):
        record_diagnostic(tmp_path, "assistant_failed", state="failed", reason="x")
