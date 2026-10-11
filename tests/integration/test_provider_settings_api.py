from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.settings import MemorySecretBackend, UnavailableSecretBackend


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
    assert response.json()["mode"] == "fake"

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
        json={"account_id": "team-account", "secret": "synthetic-secret"},
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
        json={"account_id": "unsaved-account", "secret": "synthetic-key"},
    )
    assert mismatched.status_code == 422
    saved = client.put(
        "/api/v1/credentials/dashscope",
        headers=headers,
        json={"account_id": "saved-account", "secret": "synthetic-key"},
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
        json={"account_id": "default", "secret": "synthetic-secret"},
    )

    assert response.status_code == 503
    assert "synthetic-secret" not in response.text
    assert all(
        "synthetic-secret" not in path.read_text() for path in (tmp_path / "profile").rglob("*")
    )


def test_registered_localhost_callback_is_used_by_fake_authorization(tmp_path):
    app = create_app(
        session_token="synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
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


def test_real_embedding_defers_approval_index_and_rejects_stale_fingerprint(tmp_path):
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
    page = client.post(
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
    assert page.status_code == 201
    fake_fingerprint = "summit-fake-embedding-v1"
    plan = client.post(
        "/api/v1/index/plans",
        headers=headers,
        json={"mode": "initial", "fingerprint": fake_fingerprint},
    )
    assert plan.status_code == 200
    assert client.post("/api/v1/index/jobs", headers=headers, json=plan.json()).status_code == 200

    configured = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "mode": "real",
            "embedding": {
                "provider": "dashscope",
                "model": "qwen3.7-text-embedding",
                "enabled": True,
            },
        },
    )
    assert configured.status_code == 200
    stale_plan = client.post(
        "/api/v1/index/plans",
        headers=headers,
        json={"mode": "model_change", "fingerprint": fake_fingerprint},
    )
    assert stale_plan.status_code == 409

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
        json={"account_id": "default", "secret": "synthetic-api-key"},
    )
    assert credential.status_code == 200
    configured = client.get("/api/v1/settings", headers=headers)
    capability = configured.json()["capabilities"]["llm"]
    assert capability["available"] is False
    assert capability["disabled_reason"] == "limited_synthetic_smoke_only"

    attempted = client.post(
        "/api/v1/journal/assist",
        headers=headers,
        json={"text": "不得发送的普通业务正文"},
    )
    assert attempted.status_code == 409
    assert attempted.json()["error"]["code"] == "provider_disabled"
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

    def synthetic_answer(self, question, passages):
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
            json={"account_id": "default", "secret": "synthetic-key"},
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


def test_limited_model_studio_smokes_use_fixed_candidates_and_one_shot(tmp_path, monkeypatch):
    from summit_everything.integrations.embedding import ModelStudioEmbedding
    from summit_everything.integrations.rerank import ModelStudioReranker
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

    embedding_inputs = []
    rerank_inputs = []
    monkeypatch.setattr(
        ModelStudioEmbedding,
        "embed_many",
        lambda self, texts, *, fingerprint=None: (
            embedding_inputs.append((texts, fingerprint)) or [[0.0] * 1024]
        ),
    )
    monkeypatch.setattr(
        ModelStudioReranker,
        "rank",
        lambda self, query, texts: rerank_inputs.append((query, texts)) or [(0, 1.0), (1, 0.0)],
    )
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
                "name": "Model Studio 合成冒烟库",
                "operation_id": "open-model-studio-smoke",
            },
        ).status_code
        == 201
    )
    configured = client.patch(
        "/api/v1/settings",
        headers=headers,
        json={
            "mode": "real",
            "embedding": {
                "provider": "dashscope",
                "model": "qwen3.7-text-embedding",
                "enabled": True,
            },
            "rerank": {
                "provider": "dashscope",
                "model": "qwen3.7-text-rerank",
                "enabled": True,
            },
        },
    )
    assert configured.status_code == 200
    assert (
        client.put(
            "/api/v1/credentials/dashscope",
            headers=headers,
            json={"account_id": "default", "secret": "synthetic-model-studio-key"},
        ).status_code
        == 200
    )

    embedding = client.post("/api/v1/provider-smoke/model-studio-embedding", headers=headers)
    rerank = client.post("/api/v1/provider-smoke/model-studio-rerank", headers=headers)
    assert embedding.status_code == rerank.status_code == 200
    assert embedding_inputs == [(["synthetic connection check"], None)]
    assert rerank_inputs == [
        (
            "synthetic connection query",
            ["synthetic candidate alpha", "synthetic candidate beta"],
        )
    ]
    assert (
        client.post("/api/v1/provider-smoke/model-studio-embedding", headers=headers).status_code
        == 409
    )
    assert (
        client.post("/api/v1/provider-smoke/model-studio-rerank", headers=headers).status_code
        == 409
    )


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
            json={"account_id": "default", "secret": "synthetic-key"},
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
