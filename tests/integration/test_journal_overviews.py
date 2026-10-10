from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.intake.review import IntakeReviewService
from summit_everything.integrations.llm import FakeLLM


@pytest.fixture
def journal_api(tmp_path: Path) -> tuple[TestClient, dict[str, str]]:
    token = "journal-overview-token"
    api = TestClient(create_app(session_token=token, profile_root=tmp_path / "profiles"))
    api.headers.update({"Authorization": f"Bearer {token}"})
    assert (
        api.post(
            "/api/v1/workspaces",
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "模拟库",
                "operation_id": "workspace",
            },
        ).status_code
        == 201
    )
    line = api.post("/api/v1/lines", json={"name": "模拟线", "operation_id": "line"}).json()
    project = api.post(
        "/api/v1/projects",
        json={"line_id": line["id"], "name": "模拟项目", "operation_id": "project"},
    ).json()
    return api, {"line": line["id"], "project": project["id"], "overview": project["overview_id"]}


@pytest.mark.parametrize("kind", ["log", "thought"])
def test_journal_retry_is_idempotent_and_changed_payload_conflicts(journal_api, kind: str) -> None:
    api, _ = journal_api
    request = {
        "title": "模拟记录",
        "body": "已确认的模拟正文。",
        "confirmation_id": f"confirm-{kind}",
        "operation_id": f"save-{kind}",
    }
    first = api.post(f"/api/v1/journal/{kind}", json=request)
    retry = api.post(f"/api/v1/journal/{kind}", json=request)
    assert first.status_code == retry.status_code == 201
    assert first.json() == retry.json()
    pages = api.get("/api/v1/pages").json()
    assert len(pages) == 1
    assert pages[0]["metadata"]["kind"] == kind
    assert (
        api.post(f"/api/v1/journal/{kind}", json={**request, "body": "不同正文"}).status_code == 409
    )


def test_journal_association_validation_rejects_mismatched_project(journal_api) -> None:
    api, ids = journal_api
    other_line = api.post(
        "/api/v1/lines", json={"name": "另一条线", "operation_id": "other-line"}
    ).json()
    other_project = api.post(
        "/api/v1/projects",
        json={"line_id": other_line["id"], "name": "另一项目", "operation_id": "other-project"},
    ).json()
    response = api.post(
        "/api/v1/journal/log",
        json={
            "title": "模拟",
            "body": "正文",
            "line_id": ids["line"],
            "project_id": other_project["id"],
            "confirmation_id": "c",
            "operation_id": "o",
        },
    )
    assert response.status_code == 422


def test_journal_supports_no_association_line_only_and_line_with_project(journal_api) -> None:
    api, ids = journal_api
    for index, association in enumerate(
        ({}, {"line_id": ids["line"]}, {"line_id": ids["line"], "project_id": ids["project"]})
    ):
        response = api.post(
            "/api/v1/journal/thought",
            json={
                "title": f"记录 {index}",
                "body": "模拟正文",
                **association,
                "confirmation_id": f"confirm-{index}",
                "operation_id": f"operation-{index}",
            },
        )
        assert response.status_code == 201, response.text
    pages = api.get("/api/v1/pages").json()
    assert len(pages) == 3
    assert ["line_id" in page["metadata"] for page in pages] == [False, True, True]
    assert ["project_id" in page["metadata"] for page in pages] == [False, False, True]


def test_concurrent_journal_retries_commit_exactly_one_page(journal_api) -> None:
    api, _ = journal_api
    request = {
        "title": "并发日志",
        "body": "同一份模拟正文。",
        "confirmation_id": "concurrent-confirm",
        "operation_id": "concurrent-operation",
    }
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _index: api.post("/api/v1/journal/log", json=request), range(4))
        )
    assert all(result.status_code == 201 for result in results), [result.text for result in results]
    assert all(result.json() == results[0].json() for result in results)
    assert len(api.get("/api/v1/pages").json()) == 1


def test_lost_journal_response_can_be_replayed_after_application_restart(
    tmp_path: Path,
) -> None:
    token = "journal-restart-token"
    profile = tmp_path / "profiles"
    root = tmp_path / "workspace"
    first_api = TestClient(create_app(session_token=token, profile_root=profile))
    first_api.headers.update({"Authorization": f"Bearer {token}"})
    assert (
        first_api.post(
            "/api/v1/workspaces",
            json={"root": str(root), "mode": "create", "name": "模拟库", "operation_id": "create"},
        ).status_code
        == 201
    )
    request = {
        "title": "保存结果丢失",
        "body": "可重放的模拟内容。",
        "confirmation_id": "restart-confirmation",
        "operation_id": "restart-operation",
    }
    assert first_api.post("/api/v1/journal/log", json=request).status_code == 201
    first_api.close()

    restarted_api = TestClient(create_app(session_token=token, profile_root=profile))
    restarted_api.headers.update({"Authorization": f"Bearer {token}"})
    assert (
        restarted_api.post(
            "/api/v1/workspaces",
            json={"root": str(root), "mode": "open", "name": "模拟库", "operation_id": "reopen"},
        ).status_code
        == 201
    )
    replay = restarted_api.post("/api/v1/journal/log", json=request)
    assert replay.status_code == 201, replay.text
    assert len(restarted_api.get("/api/v1/pages").json()) == 1


def test_overview_uses_stable_id_and_requires_current_content_version(journal_api) -> None:
    api, ids = journal_api
    before = api.get("/api/v1/projects").json()[0]
    request = {
        "title": "项目概览",
        "body": "目标：完成模拟项目。\n\n依据：[模拟事实](page-fact)",
        "confirmation_id": "overview-confirm-1",
        "operation_id": "overview-op-1",
    }
    created = api.post(f"/api/v1/projects/{before['id']}/overview/confirmations", json=request)
    assert created.status_code == 201, created.text
    assert ids["overview"] in created.json()["page_versions"]
    page = api.get(f"/api/v1/pages/{ids['overview']}").json()
    assert page["metadata"]["kind"] == "project_overview"
    assert page["approval_state"] == "confirmed"
    assert api.get("/api/v1/projects").json()[0]["progress"] == before["progress"]

    updated = api.post(
        f"/api/v1/projects/{before['id']}/overview/confirmations",
        json={
            **request,
            "body": "更新的目标。",
            "confirmation_id": "overview-confirm-2",
            "operation_id": "overview-op-2",
            "expected_content_sha256": page["content_sha256"],
        },
    )
    assert updated.status_code == 201, updated.text
    stale = api.post(
        f"/api/v1/projects/{before['id']}/overview/confirmations",
        json={
            **request,
            "body": "过期覆盖。",
            "confirmation_id": "overview-confirm-3",
            "operation_id": "overview-op-3",
            "expected_content_sha256": page["content_sha256"],
        },
    )
    assert stale.status_code == 409
    assert api.get(f"/api/v1/pages/{ids['overview']}").json()["body"] == "更新的目标。"
    assert api.get("/api/v1/projects").json()[0]["progress"] == before["progress"]


def test_journal_ai_assist_is_explicit_and_returns_an_uncommitted_suggestion(
    tmp_path: Path,
) -> None:
    provider = FakeLLM()
    token = "journal-assist-token"
    api = TestClient(
        create_app(
            session_token=token,
            profile_root=tmp_path / "profiles",
            review_service=IntakeReviewService(provider),
        )
    )
    api.headers.update({"Authorization": f"Bearer {token}"})
    assert (
        api.post(
            "/api/v1/workspaces",
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "模拟库",
                "operation_id": "workspace",
            },
        ).status_code
        == 201
    )
    assert provider.calls == 0
    assert api.get("/api/v1/pages").status_code == 200
    assert provider.calls == 0
    saved = api.post(
        "/api/v1/journal/log",
        json={
            "title": "未调用辅助",
            "body": "普通保存仍为纯本地操作。",
            "confirmation_id": "plain-save-confirmation",
            "operation_id": "plain-save-operation",
        },
    )
    assert saved.status_code == 201
    assert provider.calls == 0
    suggestion = api.post("/api/v1/journal/assist", json={"text": "我今天检查了模拟页面。"})
    assert suggestion.status_code == 200, suggestion.text
    assert provider.calls == 1
    assert suggestion.json()["body"]
    assert len(api.get("/api/v1/pages").json()) == 1


def test_journal_ai_failure_does_not_write_or_change_existing_pages(tmp_path: Path) -> None:
    provider = FakeLLM(scenario="timeout")
    token = "journal-assist-failure-token"
    api = TestClient(
        create_app(
            session_token=token,
            profile_root=tmp_path / "profiles",
            review_service=IntakeReviewService(provider),
        )
    )
    api.headers.update({"Authorization": f"Bearer {token}"})
    assert (
        api.post(
            "/api/v1/workspaces",
            json={
                "root": str(tmp_path / "workspace"),
                "mode": "create",
                "name": "模拟库",
                "operation_id": "workspace",
            },
        ).status_code
        == 201
    )
    original = api.post(
        "/api/v1/journal/log",
        json={
            "title": "保留内容",
            "body": "原始保存正文。",
            "confirmation_id": "save-confirmation",
            "operation_id": "save-operation",
        },
    )
    assert original.status_code == 201
    failed = api.post("/api/v1/journal/assist", json={"text": "请求建议"})
    assert failed.status_code == 502
    assert provider.calls == 1
    pages = api.get("/api/v1/pages").json()
    assert len(pages) == 1
    assert pages[0]["body"] == "原始保存正文。"
