"""Item 6 — credential shape boundaries and the no-echo rule."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MemorySecretBackend

from qa_helpers import HEADERS, open_workspace

MAX = 512


def _client(tmp_path) -> TestClient:
    client = TestClient(
        create_app(
            session_token="qa-independent-session",
            profile_root=tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
        )
    )
    open_workspace(client, tmp_path / "workspace")
    return client


def _put(client: TestClient, provider: str, secret: str) -> tuple[int, str]:
    response = client.put(
        f"/api/v1/credentials/{provider}",
        headers=HEADERS,
        json={"account_id": "default", "secret": secret},
    )
    return response.status_code, response.text


@pytest.mark.parametrize(
    ("label", "secret", "expected"),
    [
        ("exactly-16-after-prefix", "sk-" + "a" * 16, 200),
        ("17-after-prefix", "sk-" + "a" * 17, 200),
        ("exactly-512-total", "sk-" + "a" * (MAX - 3), 200),
        ("513-total", "sk-" + "a" * (MAX - 2), 422),
        ("15-after-prefix", "sk-" + "a" * 15, 422),
        ("newline", "sk-" + "a" * 16 + "\n", 422),
        ("embedded-newline", "sk-aaaa\nbbbbbbbbbbbbbbbb", 422),
        ("space", "sk-" + "a" * 8 + " " + "b" * 8, 422),
        ("leading-space", " sk-" + "a" * 16, 422),
        ("tab", "sk-" + "a" * 8 + "\t" + "b" * 8, 422),
        ("no-prefix", "abcdefghijklmnopqrst", 422),
        ("uppercase-prefix", "SK-" + "a" * 16, 422),
        ("other-prefix", "pk-" + "a" * 16, 422),
        ("empty", "", 422),
        ("whitespace-only", "   ", 422),
        ("underscore-and-dash-body", "sk-" + "a_b-c" * 4, 200),
    ],
)
def test_api_key_shape_boundaries(tmp_path, label, secret, expected):
    client = _client(tmp_path)
    status, text = _put(client, "deepseek", secret)
    assert status == expected, (label, status, text)
    if secret.strip():
        assert secret not in text, label
    if expected == 422:
        body = client.put(
            "/api/v1/credentials/deepseek",
            headers=HEADERS,
            json={"account_id": "default", "secret": secret},
        ).json()
        # An empty secret is rejected by the request model, before the shape gate.
        expected_code = "validation_error" if label == "empty" else "credential_shape_invalid"
        assert body["error"]["code"] == expected_code, label
        assert body["error"]["message"], label


@pytest.mark.parametrize(
    ("label", "secret", "expected"),
    [
        ("exactly-8", "a" * 8, 200),
        ("exactly-512", "a" * MAX, 200),
        ("513", "a" * (MAX + 1), 422),
        ("7", "a" * 7, 422),
        ("newline", "abcd" + "\n" + "efgh", 422),
        ("trailing-newline", "abcdefgh\n", 422),
        ("space", "abcd efgh", 422),
        ("tab", "abcd\tefgh", 422),
        ("carriage-return", "abcd\refgh", 422),
        ("nul-control", "abcdefg\x00h", 422),
        ("non-ascii-with-space", "密钥 值", 422),
    ],
)
def test_feishu_app_secret_boundaries(tmp_path, label, secret, expected):
    client = _client(tmp_path)
    status, text = _put(client, "feishu_app", secret)
    assert status == expected, (label, status, text)
    assert secret not in text, label
    if expected == 422:
        assert "credential_shape_invalid" in text, label


def test_rejection_never_stores_the_value(tmp_path):
    client = _client(tmp_path)
    sentinel = "sk-should-not-be-stored-1234\n"
    status, _ = _put(client, "deepseek", sentinel)
    assert status == 422
    # The rejected value is absent from every local profile artefact.
    profile = tmp_path / "profile"
    for path in profile.rglob("*"):
        if path.is_file():
            assert sentinel.encode() not in path.read_bytes(), path


def test_accepting_shape_does_store_it(tmp_path):
    client = _client(tmp_path)
    accepted = "sk-" + "z" * 20
    status, _ = _put(client, "deepseek", accepted)
    assert status == 200
    settings = client.get("/api/v1/settings", headers=HEADERS)
    assert settings.status_code == 200
    assert accepted not in settings.text
