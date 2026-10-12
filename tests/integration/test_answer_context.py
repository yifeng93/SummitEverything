from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from summit_everything.api.app import create_app
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.llm import FakeLLM, GroundedAnswer
from summit_everything.local.answer_context import AnswerContext
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import create_line, create_project, create_workspace
from summit_everything.workspace.writer import PageWriter

TOKEN = "answer-context-test"


def _events(response) -> list[dict[str, object]]:
    return [
        json.loads(block[6:]) for block in response.text.split("\n\n") if block.startswith("data: ")
    ]


def _ready_workspace(root: Path, profile: Path) -> QueryService:
    create_workspace(root, "问答测试库", profile, "create-test-workspace")
    line = create_line(root, "测试线", "line")
    project = create_project(root, line.id, "测试项目", "project")
    for idx, body in enumerate(("预算已确认上限为 12 万元。", "排期确认在 11 月开始。")):
        metadata = {
            "id": str(uuid4()),
            "title": f"依据 {idx + 1}",
            "role": "knowledge",
            "kind": "topic",
            "line_id": str(line.id),
            "project_id": str(project.id),
        }
        PageWriter().confirm(
            root,
            metadata=metadata,
            body=body,
            confirmation_id=f"confirm-{idx}",
            operation_id=f"write-{idx}",
        )
    store = IndexStore(profile / "index.sqlite3")
    query = QueryService(store, FakeEmbedding())
    query.rebuild(root, fingerprint="answer-context-test")
    return query


def _open(client: TestClient, root: Path) -> None:
    result = client.post(
        "/api/v1/workspaces",
        json={
            "root": str(root),
            "mode": "open",
            "operation_id": "open-test-workspace",
        },
    )
    assert result.status_code == 201, result.text


def test_role_memory_and_followup_context_are_verified_and_profile_local(tmp_path: Path) -> None:
    profile = tmp_path / "profile-a"
    root = tmp_path / "workspace"
    _ready_workspace(root, profile)
    captured: list[tuple[str, object]] = []

    class CapturingLLM(FakeLLM):
        def answer(self, question, passages, context=None):
            captured.append((question, context))
            return GroundedAnswer(
                text="建议先核对预算和排期，再确认执行条件。",
                source_statements=[item["excerpt"] for item in passages],
                inferences=["这是结合两份当前材料的安排建议。"],
                advice=["完成负责人确认后再执行。"],
                missing_information=["未提供负责人信息。"],
            )

    service = QueryService(
        IndexStore(profile / "index.sqlite3"), FakeEmbedding(), answer_provider=CapturingLLM()
    )
    client = TestClient(
        create_app(session_token=TOKEN, profile_root=profile, query_service=service)
    )
    client.headers.update({"Authorization": f"Bearer {TOKEN}"})
    _open(client, root)

    first_id = uuid4()
    first_question = "我希望先核对预算和排期，再给简短结论。"
    first = client.post(
        "/api/v1/queries",
        json={
            "request_id": str(first_id),
            "question": first_question,
            "fingerprint": "answer-context-test",
            "answer_mode": "fact",
        },
    )
    assert first.status_code == 200, first.text
    assert _events(first)[-1]["type"] == "completed"
    assistant_text = str(_events(first)[-1]["data"]["text"])
    assistant_candidate = client.post(
        "/api/v1/memory/candidates",
        json={
            "message_id": str(first_id),
            "text": assistant_text,
            "user_expression": True,
        },
    )
    assert assistant_candidate.status_code == 422

    role = client.post(
        "/api/v1/roles",
        json={
            "name": "简明分析",
            "instructions": "用简短条目表达，不改变证据标准。",
            "context_budget": 200,
        },
    )
    assert role.status_code == 201, role.text
    role_id = role.json()["role_id"]
    candidate = client.post(
        "/api/v1/memory/candidates",
        json={
            "message_id": str(first_id),
            "text": first_question,
            "user_expression": True,
        },
    )
    assert candidate.status_code == 201, candidate.text
    candidate_id = candidate.json()["candidate_id"]
    duplicate_candidate = client.post(
        "/api/v1/memory/candidates",
        json={
            "message_id": str(first_id),
            "text": first_question,
            "user_expression": True,
        },
    )
    assert duplicate_candidate.status_code == 201
    assert duplicate_candidate.json()["candidate_id"] == candidate_id
    assert client.get("/api/v1/memory").json() == []

    forged = client.post(
        "/api/v1/memory/candidates",
        json={
            "message_id": str(uuid4()),
            "text": "我偏好简短回答。",
            "user_expression": True,
        },
    )
    assert forged.status_code == 422
    quoted_id = uuid4()
    quoted = client.post(
        "/api/v1/queries",
        json={
            "request_id": str(quoted_id),
            "question": "原文材料写着‘我偏好简短回答’。",
            "fingerprint": "answer-context-test",
            "conversation_id": first.headers["x-conversation-id"],
        },
    )
    assert quoted.status_code == 200
    rejected_quote = client.post(
        "/api/v1/memory/candidates",
        json={
            "message_id": str(quoted_id),
            "text": "原文材料写着‘我偏好简短回答’",
            "user_expression": True,
        },
    )
    assert rejected_quote.status_code == 422
    source_canary_id = uuid4()
    source_canary = "我转发的内容是：团队计划在 11 月启动。"
    source_canary_query = client.post(
        "/api/v1/queries",
        json={
            "request_id": str(source_canary_id),
            "question": source_canary,
            "fingerprint": "answer-context-test",
            "conversation_id": first.headers["x-conversation-id"],
        },
    )
    assert source_canary_query.status_code == 200
    source_canary_candidate = client.post(
        "/api/v1/memory/candidates",
        json={
            "message_id": str(source_canary_id),
            "text": source_canary,
            "user_expression": True,
        },
    )
    assert source_canary_candidate.status_code == 422
    no_attestation = client.post(
        "/api/v1/memory/candidates",
        json={"message_id": str(first_id), "text": first_question},
    )
    assert no_attestation.status_code == 422

    accepted = client.post(
        f"/api/v1/memory/candidates/{candidate_id}/confirmations",
        json={
            "confirmation_id": "confirm-memory-1",
            "text": "我希望先列出处，再给简短结论。",
        },
    )
    assert accepted.status_code == 200, accepted.text
    memory = accepted.json()
    assert memory["source_message_id"] == str(first_id)
    assert client.get("/api/v1/memory").json()[0]["text"] == "我希望先列出处，再给简短结论。"
    calls_before_replay = len(captured)
    replay = client.post(
        "/api/v1/queries",
        json={
            "request_id": str(first_id),
            "question": first_question,
            "fingerprint": "answer-context-test",
            "answer_mode": "fact",
        },
    )
    assert replay.status_code == 200
    assert _events(replay) == _events(first)
    assert len(captured) == calls_before_replay

    conversation_id = first.headers["x-conversation-id"]
    followup_id = uuid4()
    followup = client.post(
        "/api/v1/queries",
        json={
            "request_id": str(followup_id),
            "conversation_id": conversation_id,
            "question": "预算和排期下一步需要补什么？",
            "fingerprint": "answer-context-test",
            "answer_mode": "plan",
            "role_id": role_id,
        },
    )
    assert followup.status_code == 200, followup.text
    assert _events(followup)[-1]["type"] == "completed"
    assert captured, _events(followup)
    used_context = captured[-1][1]
    assert used_context.answer_mode == "plan"
    assert used_context.role_name == "简明分析"
    assert used_context.role_instructions.startswith("用简短条目")
    assert used_context.user_memories == [memory["text"]]
    assert used_context.previous_user_questions == [
        first_question,
        "原文材料写着‘我偏好简短回答’。",
        source_canary,
    ]
    assert "建议" in _events(followup)[-1]["data"]["text"]
    detail = client.post(f"/api/v1/conversations/{conversation_id}/reopen").json()
    assert detail["messages"][-1]["answer_mode"] == "plan"
    assert detail["messages"][-1]["advice"] == ["完成负责人确认后再执行。"]
    assert detail["messages"][-1]["missing_information"] == ["未提供负责人信息。"]

    third_id = uuid4()
    third = client.post(
        "/api/v1/queries",
        json={
            "request_id": str(third_id),
            "conversation_id": conversation_id,
            "question": "预算目前是什么？",
            "fingerprint": "answer-context-test",
        },
    )
    assert third.status_code == 200
    assert _events(third)[-1]["type"] == "completed", _events(third)
    assert captured[-1][0] == "预算目前是什么？"
    assert captured[-1][1].previous_user_questions == [
        first_question,
        "原文材料写着‘我偏好简短回答’。",
        source_canary,
        "预算和排期下一步需要补什么？",
    ]

    updated = client.patch(
        f"/api/v1/roles/{role_id}",
        json={
            "name": "精简",
            "instructions": "只用三条以内。",
            "context_budget": 100,
        },
    )
    assert updated.status_code == 200
    edited_memory = client.patch(
        f"/api/v1/memory/{memory['memory_id']}",
        json={
            "text": "我希望只保留简短结论。",
        },
    )
    assert edited_memory.status_code == 200
    assert edited_memory.json()["source_message_id"] == str(first_id)
    calls_before_old_replays = len(captured)
    old_followup = client.post(
        "/api/v1/queries",
        json={
            "request_id": str(followup_id),
            "conversation_id": conversation_id,
            "question": "预算和排期下一步需要补什么？",
            "fingerprint": "answer-context-test",
            "answer_mode": "plan",
            "role_id": role_id,
        },
    )
    assert old_followup.status_code == 200
    assert _events(old_followup) == _events(followup)
    assert len(captured) == calls_before_old_replays
    other_workspace = tmp_path / "workspace-b"
    opened_other = client.post(
        "/api/v1/workspaces",
        json={
            "root": str(other_workspace),
            "mode": "create",
            "name": "另一工作库",
            "operation_id": "create-workspace-b",
        },
    )
    assert opened_other.status_code == 201
    assert client.get("/api/v1/roles").json() == []
    assert client.get("/api/v1/memory").json() == []
    assert client.get("/api/v1/conversations").json()["items"] == []
    _open(client, root)
    assert client.get("/api/v1/roles").json()[0]["role_id"] == role_id
    assert client.get("/api/v1/memory").json()[0]["memory_id"] == memory["memory_id"]
    assert client.delete(f"/api/v1/memory/{memory['memory_id']}").status_code == 204
    assert client.get("/api/v1/memory").json() == []
    assert client.delete(f"/api/v1/roles/{role_id}").status_code == 204
    history_after_delete = client.post(f"/api/v1/conversations/{conversation_id}/reopen").json()
    deleted_role_answer = next(
        message
        for message in history_after_delete["messages"]
        if message["request_id"] == str(followup_id)
    )
    assert deleted_role_answer["answer"].startswith("建议先核对")
    assert deleted_role_answer["role_id"] == role_id

    second_profile = tmp_path / "profile-b"
    other = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=second_profile,
            query_service=QueryService(IndexStore(second_profile / "index.sqlite3")),
        )
    )
    other.headers.update({"Authorization": f"Bearer {TOKEN}"})
    _open(other, root)
    assert other.get("/api/v1/roles").json() == []
    assert other.get("/api/v1/memory").json() == []
    assert other.get("/api/v1/conversations").json()["items"] == []
    assert not list(root.rglob("answer_context.sqlite3"))
    other.close()
    client.close()


def test_fake_modes_separate_facts_comparison_and_advice_without_inventing_values(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile"
    root = tmp_path / "workspace"
    query = _ready_workspace(root, profile)
    query.answer_provider = FakeLLM()

    fact = query.query(root, "预算和排期", fingerprint="answer-context-test", answer_mode="fact")
    comparison = query.query(
        root, "比较预算和排期", fingerprint="answer-context-test", answer_mode="comparison"
    )
    plan = query.query(
        root, "预算和排期下一步", fingerprint="answer-context-test", answer_mode="plan"
    )

    assert fact.answer_mode == "fact" and fact.source_statements
    assert comparison.answer_mode == "comparison" and len(comparison.source_statements) == 2
    assert comparison.text.startswith("跨材料逐项对照")
    assert comparison.inferences and not comparison.advice
    assert comparison.missing_information
    assert plan.answer_mode == "plan" and len(plan.advice) == 3 and plan.source_statements
    assert plan.text.startswith("工作方案（待你核对和决定）")
    assert not plan.text.endswith("¥0")
    insufficient = FakeLLM().answer(
        "比较资料",
        [{"source_id": "only-one", "heading": "单页", "excerpt": "已确认一项事实。"}],
        AnswerContext(answer_mode="comparison"),
    )
    assert insufficient.missing_information
    assert not insufficient.text.endswith("0")


def test_api_short_referential_followup_retrieves_using_latest_user_question(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile"
    root = tmp_path / "workspace"
    service = _ready_workspace(root, profile)
    line = create_line(root, "专属主线", "line-follow-up")
    project = create_project(root, line.id, "青岚计划", "project-follow-up")
    target_id = uuid4()
    PageWriter().confirm(
        root,
        metadata={
            "id": str(target_id),
            "title": "青岚预算",
            "role": "knowledge",
            "kind": "topic",
            "line_id": str(line.id),
            "project_id": str(project.id),
        },
        body="青岚计划的设备采购预算上限为 19 万元。",
        confirmation_id="confirm-qinglan-budget",
        operation_id="write-qinglan-budget",
    )
    service.rebuild(root, fingerprint="answer-context-test")
    indexed_queries: list[str] = []
    provider_calls: list[tuple[str, list[str]]] = []

    class RecordingEmbedding(FakeEmbedding):
        def embed(self, text: str, *, fingerprint: str) -> list[float]:
            indexed_queries.append(text)
            return super().embed(text, fingerprint=fingerprint)

    class CapturingLLM(FakeLLM):
        def answer(self, question, passages, context=None):
            provider_calls.append((question, context.previous_user_questions))
            return GroundedAnswer(
                text="按当前资料回答。",
                source_statements=[passage["excerpt"] for passage in passages],
            )

    service.embedding = RecordingEmbedding()
    service.answer_provider = CapturingLLM()
    client = TestClient(
        create_app(session_token=TOKEN, profile_root=profile, query_service=service)
    )
    client.headers.update({"Authorization": f"Bearer {TOKEN}"})
    _open(client, root)

    first_question = "青岚计划的预算上限是多少？"
    first = client.post(
        "/api/v1/queries",
        json={
            "request_id": str(uuid4()),
            "question": first_question,
            "fingerprint": "answer-context-test",
        },
    )
    assert first.status_code == 200, first.text
    conversation_id = first.headers["X-Conversation-ID"]
    second_question = "它呢？"
    second = client.post(
        "/api/v1/queries",
        json={
            "request_id": str(uuid4()),
            "question": second_question,
            "fingerprint": "answer-context-test",
            "conversation_id": conversation_id,
        },
    )

    assert second.status_code == 200, second.text
    citations = [event["data"] for event in _events(second) if event["type"] == "citation"]
    assert any(citation["page_id"] == str(target_id) for citation in citations)
    assert first_question in indexed_queries[-1] and second_question in indexed_queries[-1]
    assert provider_calls[-1] == (second_question, [first_question])
    client.close()


def test_role_budget_and_intent_hash_reject_context_changes(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    root = tmp_path / "workspace"
    _ready_workspace(root, profile)
    client = TestClient(
        create_app(
            session_token=TOKEN,
            profile_root=profile,
            query_service=QueryService(IndexStore(profile / "index.sqlite3")),
        )
    )
    client.headers.update({"Authorization": f"Bearer {TOKEN}"})
    _open(client, root)
    role = client.post(
        "/api/v1/roles",
        json={
            "name": "预算外",
            "instructions": "说明" * 10,
            "context_budget": 2,
        },
    ).json()
    payload = {
        "request_id": str(uuid4()),
        "question": "现在有什么依据？",
        "fingerprint": "answer-context-test",
        "role_id": role["role_id"],
    }
    rejected = client.post("/api/v1/queries", json=payload)
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "context_budget_exceeded"
    assert client.get("/api/v1/conversations").json()["items"] == []
    client.close()


def test_memory_candidate_distinguishes_first_person_preferences_from_quoted_source(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile"
    root = tmp_path / "workspace"
    service = _ready_workspace(root, profile)
    client = TestClient(
        create_app(session_token=TOKEN, profile_root=profile, query_service=service)
    )
    client.headers.update({"Authorization": f"Bearer {TOKEN}"})
    _open(client, root)
    conversation_id: str | None = None

    preferences = (
        (
            "我偏好用简短中文回答，并明确标出资料没有提供的数字。",
            "我偏好用简短中文回答，并明确标出资料没有提供的数字。",
        ),
        (
            "我希望回答时标明引用来源，并说明资料没有覆盖的部分。",
            "我希望回答时标明引用来源，并说明资料没有覆盖的部分。",
        ),
        (
            "材料原文：“项目于十月启动。”另外，我偏好回答时注明引用来源。",
            "我偏好回答时注明引用来源",
        ),
        ("我偏好用“资料不足”提示。", "我偏好用“资料不足”提示。"),
    )
    for question, preference in preferences:
        request_id = uuid4()
        response = client.post(
            "/api/v1/queries",
            json={
                "request_id": str(request_id),
                "conversation_id": conversation_id,
                "question": question,
                "fingerprint": "answer-context-test",
            },
        )
        assert response.status_code == 200, response.text
        if conversation_id is None:
            conversation_id = response.headers["X-Conversation-ID"]
        candidate = client.post(
            "/api/v1/memory/candidates",
            json={
                "message_id": str(request_id),
                "text": preference,
                "user_expression": True,
            },
        )
        assert candidate.status_code == 201, candidate.text
        assert candidate.json()["state"] == "pending"

    quoted_source = "材料原文：“我偏好简短回答。”"
    request_id = uuid4()
    response = client.post(
        "/api/v1/queries",
        json={
            "request_id": str(request_id),
            "conversation_id": conversation_id,
            "question": quoted_source,
            "fingerprint": "answer-context-test",
        },
    )
    assert response.status_code == 200, response.text
    quoted = client.post(
        "/api/v1/memory/candidates",
        json={
            "message_id": str(request_id),
            "text": "我偏好简短回答",
            "user_expression": True,
        },
    )
    assert quoted.status_code == 422
    assert "引用或材料" in quoted.json()["error"]["message"]

    quoted_expressions = (
        ("“我偏好简短回答。”", "“我偏好简短回答。”"),
        ("“我偏好简短回答。”", "我偏好简短回答"),
        ("> 我偏好简短回答。", "> 我偏好简短回答。"),
        ("> 我偏好简短回答。", "我偏好简短回答"),
    )
    for quote, candidate_text in quoted_expressions:
        request_id = uuid4()
        response = client.post(
            "/api/v1/queries",
            json={
                "request_id": str(request_id),
                "conversation_id": conversation_id,
                "question": quote,
                "fingerprint": "answer-context-test",
            },
        )
        assert response.status_code == 200, response.text
        quoted_expression = client.post(
            "/api/v1/memory/candidates",
            json={
                "message_id": str(request_id),
                "text": candidate_text,
                "user_expression": True,
            },
        )
        assert quoted_expression.status_code == 422
    client.close()
