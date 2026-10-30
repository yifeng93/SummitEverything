import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.embedding import EmbeddingProviderError, FakeEmbedding
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.rerank import FakeReranker, RerankProviderError
from summit_everything.integrations.settings import MemorySecretBackend, UnavailableSecretBackend
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore


def test_production_metadata_paths_never_construct_fake_retrieval_adapters(tmp_path, monkeypatch):
    def forbidden_fake_init(self, *args, **kwargs):
        raise AssertionError("production metadata path constructed a Fake retrieval adapter")

    monkeypatch.setattr(FakeEmbedding, "__init__", forbidden_fake_init)
    monkeypatch.setattr(FakeReranker, "__init__", forbidden_fake_init)

    app = create_app(
        session_token="metadata-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer metadata-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "模拟库",
            "operation_id": "open-metadata-test",
        },
    )
    assert opened.status_code == 201
    assert client.get("/api/v1/settings", headers=headers).status_code == 200
    assert client.get("/api/v1/index/status", headers=headers).status_code == 200

    # A metadata-only service remains usable for status/plan work, but it cannot
    # silently execute generation or retrieval through a simulated adapter.
    from summit_everything.retrieval.query import QueryService

    service = QueryService(
        IndexStore(tmp_path / "metadata-only.sqlite3"), require_explicit_providers=True
    )
    with pytest.raises(EmbeddingProviderError, match="provider_not_configured"):
        service._require_embedding_provider()
    with pytest.raises(RerankProviderError, match="provider_not_configured"):
        service._require_reranker_provider()


def test_settings_reads_and_updates_are_local_and_redact_secret(tmp_path):
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "模拟库",
            "operation_id": "open-settings-test",
        },
    )
    assert opened.status_code == 201

    response = client.get("/api/v1/settings", headers=headers)
    assert response.status_code == 200
    assert response.json()["mode"] == "real"

    updated = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-flash",
                "account_id": "team-account",
            }
        },
    )
    assert updated.status_code == 200
    assert updated.json()["llm"]["provider"] == "deepseek"

    saved = client.put(
        "/api/v1/credentials/deepseek",
        headers=headers,
        json={"account_id": "team-account", "secret": "sk-synthetic-secret-00000000"},
    )
    assert saved.status_code == 200
    assert saved.json() == {"provider": "deepseek", "configured": True}
    assert "synthetic-secret" not in saved.text
    settings_response = client.get("/api/v1/settings", headers=headers)
    assert "synthetic-secret" not in settings_response.text
    assert settings_response.json()["credential_status"]["deepseek"] is True
    assert (
        client.get("/api/v1/settings", headers=headers).json()["credential_status"]["dashscope"]
        is False
    )
    switched = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"llm": {"account_id": "personal-account"}},
    )
    assert switched.json()["credential_status"]["deepseek"] is False
    deleted = client.request(
        "DELETE",
        "/api/v1/credentials/deepseek",
        headers=headers,
        json={"account_id": "team-account"},
    )
    assert deleted.status_code == 422
    client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"llm": {"account_id": "team-account"}},
    )
    deleted = client.request(
        "DELETE",
        "/api/v1/credentials/deepseek",
        headers=headers,
        json={"account_id": "team-account"},
    )
    assert deleted.status_code == 204
    assert all(
        "synthetic-secret" not in path.read_text()
        for path in (tmp_path / "profile").rglob("*provider-settings.json")
    )


def test_settings_reject_unknown_fields_and_credentials_require_auth(tmp_path):
    app = create_app(session_token="synthetic-session", profile_root=tmp_path / "profile")
    client = TestClient(app)
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "模拟库",
            "operation_id": "open-settings-test",
        },
    )
    assert opened.status_code == 201

    unauthorized = client.get("/api/v1/settings")
    assert unauthorized.status_code == 401
    bad_patch = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"arbitrary_url": "http://localhost/"},
    )
    assert bad_patch.status_code == 422


def test_real_query_reports_local_model_gap_before_provider_calls(tmp_path):
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "问答配置模拟库",
            "operation_id": "open-query-provider-gate",
        },
    )
    assert opened.status_code == 201
    enabled_real_mode = client.patch("/api/v1/settings", headers=headers, json={"mode": "real"})
    assert enabled_real_mode.status_code == 200

    response = client.post(
        "/api/v1/queries",
        headers=headers,
        json={
            "request_id": "1cb57049-9a32-4f1e-b54f-030d02cc9209",
            "question": "合成问题",
            "fingerprint": "synthetic-fingerprint",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "local_model_not_ready"
    assert "本地检索模型" in response.json()["error"]["message"]
    store = next((tmp_path / "profile").rglob("conversations.sqlite3"))
    with sqlite3.connect(store) as connection:
        count = connection.execute("SELECT count(*) FROM queries").fetchone()[0]
    assert count == 0


def test_acceptance_plan_configuration_errors_separate_model_and_feishu_requirements(tmp_path):
    client = TestClient(
        create_app(
            session_token="synthetic-session",
            profile_root=tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
        )
    )
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "索引提示模拟库",
            "operation_id": "open-index-copy",
        },
    )
    assert opened.status_code == 201

    fake_model_plan = client.post(
        "/api/v1/acceptance-plans",
        headers=headers,
        json={"operation": "model.index", "scope": {}},
    )
    assert fake_model_plan.status_code == 409
    assert fake_model_plan.json()["error"]["code"] == "local_index_plan_required"

    switched = client.patch("/api/v1/settings", headers=headers, json={"mode": "real"})
    assert switched.status_code == 200
    configured_model = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "embedding": {
                "provider": "dashscope",
                "model": "qwen3.7-text-embedding",
                "enabled": True,
            }
        },
    )
    assert configured_model.status_code == 422
    configured_settings = client.get("/api/v1/settings", headers=headers).json()
    local_index_plan = client.post(
        "/api/v1/index/plans",
        headers=headers,
        json={"mode": "initial", "fingerprint": configured_settings["embedding_fingerprint"]},
    )
    assert local_index_plan.status_code == 409
    real_model_plan = client.post(
        "/api/v1/acceptance-plans",
        headers=headers,
        json={
            "operation": "model.index",
            "scope": {},
        },
    )
    assert real_model_plan.status_code == 409, real_model_plan.text
    assert real_model_plan.json()["error"]["code"] == "local_index_plan_required"

    missing_feishu_app = client.post(
        "/api/v1/acceptance-plans",
        headers=headers,
        json={"operation": "feishu.calendar.read", "scope": {}},
    )
    assert missing_feishu_app.status_code == 409
    feishu_message = missing_feishu_app.json()["error"]["message"]
    assert feishu_message == "请先配置飞书 App ID，再预览飞书操作范围。"


def test_secret_must_match_saved_model_studio_account(tmp_path):
    client = TestClient(
        create_app(
            session_token="synthetic-session",
            profile_root=tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
        )
    )
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "模拟库",
            "operation_id": "open-model-studio-credentials",
        },
    )
    assert opened.status_code == 201
    client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"model_studio_account_id": "saved-account"},
    )
    mismatched = client.put(
        "/api/v1/credentials/dashscope",
        headers=headers,
        json={"account_id": "unsaved-account", "secret": "sk-synthetic-key-0000000000"},
    )
    assert mismatched.status_code == 422
    saved = client.put(
        "/api/v1/credentials/dashscope",
        headers=headers,
        json={"account_id": "saved-account", "secret": "sk-synthetic-key-0000000000"},
    )
    assert saved.status_code == 200
    assert client.get("/api/v1/settings", headers=headers).json()["credential_status"]["dashscope"]


def test_unavailable_keychain_fails_closed_without_file_fallback(tmp_path):
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=UnavailableSecretBackend(),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "模拟库",
            "operation_id": "unavailable-keychain",
        },
    )
    assert opened.status_code == 201

    response = client.put(
        "/api/v1/credentials/deepseek",
        headers=headers,
        json={"account_id": "default", "secret": "sk-synthetic-secret-00000000"},
    )

    assert response.status_code == 503
    assert "synthetic-secret" not in response.text
    assert all(
        "synthetic-secret" not in path.read_text() for path in (tmp_path / "profile").rglob("*")
    )


def test_legacy_fake_provider_profile_is_migrated_before_runtime_use(tmp_path):
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "旧版设置模拟库",
            "operation_id": "open-legacy-provider-profile",
        },
    )
    assert opened.status_code == 201
    current = client.get("/api/v1/workspaces/current", headers=headers).json()
    settings_path = Path(current["local_profile_dir"]) / "provider-settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        '{"mode":"fake","llm":{"provider":"fake","enabled":false},'
        '"embedding":{"provider":"fake","enabled":false},'
        '"rerank":{"provider":"fake","enabled":false}}',
        encoding="utf-8",
    )

    response = client.get("/api/v1/settings", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "real"
    assert payload["legacy_provider_migration_required"] is True
    assert payload["llm"]["provider"] == "deepseek"
    assert payload["llm"]["enabled"] is True
    assert payload["embedding"]["provider"] == "local"
    assert payload["rerank"]["provider"] == "local"
    assert settings_path.read_text(encoding="utf-8").count('"mode":"fake"') == 1


def test_normal_app_start_does_not_construct_fake_providers_or_fake_success(tmp_path, monkeypatch):
    from summit_everything.integrations.feishu.fake import FakeFeishu
    from summit_everything.integrations.llm import FakeLLM

    def fail_if_constructed(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("normal app startup must not construct Fake providers")

    monkeypatch.setattr(FakeFeishu, "__init__", fail_if_constructed)
    monkeypatch.setattr(FakeLLM, "__init__", fail_if_constructed)
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    assert app.state.feishu_service is None
    assert app.state.review_service.provider is None

    client = TestClient(app)
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "真实服务就绪门模拟库",
            "operation_id": "open-no-fake-runtime",
        },
    )
    assert opened.status_code == 201
    calendar = client.get(
        "/api/v1/integrations/feishu/calendar",
        headers=headers,
        params={
            "start": "2026-10-09T00:00:00Z",
            "end": "2026-10-10T00:00:00Z",
            "timezone": "UTC",
        },
    )
    assert calendar.status_code == 409
    assert calendar.json()["error"]["code"] == "provider_not_configured"


def test_registered_localhost_callback_is_used_with_injected_fake_feishu(tmp_path):
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
        feishu_provider=FakeFeishu(tmp_path / "synthetic-feishu"),
    )
    client = TestClient(app, base_url="http://localhost:8765")
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "模拟库",
            "operation_id": "open-feishu-settings-test",
        },
    )
    assert opened.status_code == 201
    saved = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "feishu": {
                "app_id": "synthetic-app",
                "redirect_uri": "http://localhost:8765/callback",
                "identity": "user",
            }
        },
    )
    assert saved.status_code == 200
    authorization = client.post("/api/v1/integrations/feishu/authorizations", headers=headers)
    callback = urlsplit(authorization.json()["authorization_url"])
    assert (
        f"{callback.scheme}://{callback.netloc}{callback.path}" == "http://localhost:8765/callback"
    )
    query = parse_qs(callback.query)
    completed = client.get("/callback", params={"state": query["state"][0], "code": "fake-ok"})
    assert completed.status_code == 200
    assert completed.json()["authorized"] is True


def test_unprepared_local_embedding_defers_index_but_keeps_approval(tmp_path):
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "模拟索引库",
            "operation_id": "open-index-settings-test",
        },
    )
    assert opened.status_code == 201
    line = client.post(
        "/api/v1/lines", headers=headers, json={"name": "模拟线", "operation_id": "line"}
    ).json()
    project = client.post(
        "/api/v1/projects",
        headers=headers,
        json={"line_id": line["id"], "name": "模拟项目", "operation_id": "project"},
    ).json()
    first_page = client.post(
        "/api/v1/pages",
        headers=headers,
        json={
            "metadata": {
                "id": "00000000-0000-4000-8000-000000000111",
                "title": "合成页面一",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
            },
            "body": "仅用于离线测试的内容。",
            "confirmation_id": "confirm-one",
            "operation_id": "page-one",
        },
    )
    assert first_page.status_code == 201
    assert first_page.json()["index_update"] == "not_enabled"
    current = client.get("/api/v1/workspaces/current", headers=headers).json()
    old_fake_fingerprint = "summit-fake-embedding-v1"
    old_generation = QueryService(
        IndexStore(Path(current["local_profile_dir"]) / "index.sqlite3"),
        embedding=FakeEmbedding(),
    )
    old_generation.rebuild(Path(tmp_path / "workspace"), fingerprint=old_fake_fingerprint)
    fake_selection = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={"embedding": {"provider": "fake"}, "rerank": {"provider": "fake"}},
    )
    assert fake_selection.status_code == 422

    status = client.get("/api/v1/index/status", headers=headers)
    assert status.status_code == 200
    assert status.json()["state"] == "stale"
    assert status.json()["vector"] == "simulated"
    blocked_plan = client.post(
        "/api/v1/index/plans",
        headers=headers,
        json={
            "mode": "model_change",
            "fingerprint": client.get("/api/v1/settings", headers=headers).json()[
                "embedding_fingerprint"
            ],
        },
    )
    assert blocked_plan.status_code == 409, blocked_plan.text
    assert blocked_plan.json()["error"]["code"] == "local_model_not_ready"

    blocked_query = client.post(
        "/api/v1/queries",
        headers=headers,
        json={
            "request_id": "00000000-0000-4000-8000-000000000201",
            "question": "合成页面内容是什么",
            "fingerprint": client.get("/api/v1/settings", headers=headers).json()[
                "embedding_fingerprint"
            ],
            "purpose": "current",
        },
    )
    assert blocked_query.status_code == 409
    assert blocked_query.json()["error"]["code"] == "local_model_not_ready"

    second_page = client.post(
        "/api/v1/pages",
        headers=headers,
        json={
            "metadata": {
                "id": "00000000-0000-4000-8000-000000000112",
                "title": "合成页面二",
                "role": "knowledge",
                "kind": "topic",
                "line_id": line["id"],
                "project_id": project["id"],
            },
            "body": "新增的合成内容。",
            "confirmation_id": "confirm-two",
            "operation_id": "page-two",
        },
    )
    assert second_page.status_code == 201
    assert second_page.json()["index_update"] == "manual_required"
    stale = client.get("/api/v1/index/status", headers=headers)
    assert stale.json()["state"] == "stale"
    assert stale.json()["fingerprint"] == old_fake_fingerprint


def test_disabled_real_model_status_cannot_reach_business_call_path(tmp_path):
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "模型门禁模拟库",
            "operation_id": "open-smoke-gate",
        },
    )
    assert opened.status_code == 201
    configured = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "mode": "real",
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-flash",
                "enabled": True,
            },
        },
    )
    assert configured.status_code == 200
    credential = client.put(
        "/api/v1/credentials/deepseek",
        headers=headers,
        json={"account_id": "default", "secret": "sk-synthetic-api-key-0000000"},
    )
    assert credential.status_code == 200
    configured = client.get("/api/v1/settings", headers=headers)
    capability = configured.json()["capabilities"]["llm"]
    assert capability["available"] is False
    assert capability["disabled_reason"] == "acceptance_plan_required"

    attempted = client.post(
        "/api/v1/journal/assist",
        headers=headers,
        json={"text": "不得发送的普通业务正文"},
    )
    assert attempted.status_code == 409
    assert attempted.json()["error"]["code"] == "acceptance_plan_required"
    assert "不得发送的普通业务正文" not in attempted.text


def test_limited_deepseek_smoke_is_synthetic_and_one_shot(tmp_path, monkeypatch):
    from summit_everything.integrations.llm import DeepSeekLLM, GroundedAnswer
    from summit_everything.integrations.settings import MacOSKeychainBackend

    class SyntheticKeychain(MacOSKeychainBackend):
        def __init__(self):
            self.values = {}

        def get(self, namespace, key):
            return self.values.get((namespace, key))

        def set(self, namespace, key, value):
            self.values[(namespace, key)] = value

        def delete(self, namespace, key):
            self.values.pop((namespace, key), None)

    sent = []

    def synthetic_answer(self, question, passages, context=None):
        sent.append((question, passages))
        return GroundedAnswer(text="连接正常", inferences=[], missing_information=[])

    monkeypatch.setattr(DeepSeekLLM, "answer", synthetic_answer)
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=SyntheticKeychain(),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer synthetic-session"}
    assert (
        client.post(
            "/api/v1/workspaces",
            headers=headers,
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "合成冒烟库",
                "operation_id": "open-synthetic-smoke",
            },
        ).status_code
        == 201
    )
    configured = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "mode": "real",
            "llm": {
                "provider": "deepseek",
                "model": "deepseek-flash",
                "enabled": True,
            },
        },
    )
    assert configured.status_code == 200
    assert (
        client.put(
            "/api/v1/credentials/deepseek",
            headers=headers,
            json={"account_id": "default", "secret": "sk-synthetic-key-0000000000"},
        ).status_code
        == 200
    )

    assert (
        client.get("/api/v1/provider-smoke", headers=headers).json()["remaining"]["deepseek_chat"]
        == 1
    )
    first = client.post("/api/v1/provider-smoke/deepseek-chat", headers=headers)
    assert first.status_code == 200
    assert first.json() == {
        "state": "succeeded",
        "operation": "deepseek_chat",
        "attempt": 1,
    }
    assert sent == [
        (
            "请仅复述合成短语。",
            [{"heading": "合成标题", "excerpt": "合成短语：连接正常。"}],
        )
    ]
    second = client.post("/api/v1/provider-smoke/deepseek-chat", headers=headers)
    assert second.status_code == 409
    assert (
        client.get("/api/v1/provider-smoke", headers=headers).json()["remaining"]["deepseek_chat"]
        == 0
    )
    assert len(sent) == 1


def test_legacy_retrieval_provider_configuration_and_smokes_are_rejected(tmp_path):
    client = TestClient(
        create_app(
            session_token="synthetic-session",
            profile_root=tmp_path / "profile",
            secret_backend=MemorySecretBackend(),
        )
    )
    headers = {"Authorization": "Bearer synthetic-session"}
    opened = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "root": str(tmp_path / "workspace"),
            "mode": "create",
            "name": "本地检索迁移模拟库",
            "operation_id": "open-local-retrieval-migration",
        },
    )
    assert opened.status_code == 201

    for endpoint, model in (
        ("embedding", "qwen3.7-text-embedding"),
        ("rerank", "qwen3.7-text-rerank"),
    ):
        rejected = client.patch(
            "/api/v1/settings",
            headers=headers,
            json={endpoint: {"provider": "dashscope", "model": model, "enabled": True}},
        )
        assert rejected.status_code == 422

    assert (
        client.get("/api/v1/settings", headers=headers).json()["embedding"]["provider"] == "local"
    )
    for endpoint in (
        "/api/v1/provider-smoke/model-studio-embedding",
        "/api/v1/provider-smoke/model-studio-rerank",
    ):
        response = client.post(endpoint, headers=headers)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "legacy_provider_migration_required"


def test_failed_smoke_attempt_consumes_its_authorized_slot(tmp_path, monkeypatch):
    from summit_everything.integrations.llm import DeepSeekLLM
    from summit_everything.integrations.settings import MacOSKeychainBackend

    class SyntheticKeychain(MacOSKeychainBackend):
        def __init__(self):
            self.values = {}

        def get(self, namespace, key):
            return self.values.get((namespace, key))

        def set(self, namespace, key, value):
            self.values[(namespace, key)] = value

        def delete(self, namespace, key):
            self.values.pop((namespace, key), None)

    calls = []

    def fail_once(self, question, passages):
        calls.append((question, passages))
        raise RuntimeError("synthetic secret body must not appear")

    monkeypatch.setattr(DeepSeekLLM, "answer", fail_once)
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=SyntheticKeychain(),
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer synthetic-session"}
    assert (
        client.post(
            "/api/v1/workspaces",
            headers=headers,
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "失败冒烟模拟库",
                "operation_id": "open-failed-smoke",
            },
        ).status_code
        == 201
    )
    assert (
        client.patch(
            "/api/v1/settings",
            headers=headers,
            json={
                "mode": "real",
                "llm": {"provider": "deepseek", "model": "deepseek-flash", "enabled": True},
            },
        ).status_code
        == 200
    )
    assert (
        client.put(
            "/api/v1/credentials/deepseek",
            headers=headers,
            json={"account_id": "default", "secret": "sk-synthetic-key-0000000000"},
        ).status_code
        == 200
    )

    failed = client.post("/api/v1/provider-smoke/deepseek-chat", headers=headers)
    assert failed.status_code == 502
    assert "synthetic secret body" not in failed.text
    assert (
        client.get("/api/v1/provider-smoke", headers=headers).json()["remaining"]["deepseek_chat"]
        == 0
    )
    assert client.post("/api/v1/provider-smoke/deepseek-chat", headers=headers).status_code == 409
    assert len(calls) == 1
