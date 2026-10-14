"""The answer and proposal schemas tolerate harmless provider variation.

The production failure this pins: DeepSeek returned a correct answer whose
``source_statements`` were objects ``{"source_id": ..., "quote": ...}`` plus an
extra ``type`` key, and the strict model rejected the whole answer, which the
query route then reported as a generic failure.
"""

from __future__ import annotations

import json
from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from summit_everything.integrations.http_boundary import ProviderError
from summit_everything.integrations.llm import DeepSeekLLM, GroundedAnswer, LLMProviderError

KEY = "sk-synthetic-deepseek-key-0001"

REAL_WORLD_ANSWER = {
    "text": "测试会场 A 的报价为每晚 200 元，合计 6000 元；未签约、未批准。",
    "source_statements": [
        {"source_id": "8b21aa29", "quote": "测试会场 A 的报价为每晚 200 元"},
        "第二段是纯字符串",
    ],
    "inferences": "单一字符串也应被接受",
    "advice": [],
    "missing_information": None,
    "type": "json_object",
}


def chat_response(content: str, status: int = 200) -> httpx.Response:
    if status != 200:
        return httpx.Response(status, json=json.loads(content))
    return httpx.Response(
        status,
        json={
            "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
        },
    )


def client_for(content: str, status: int = 200) -> httpx.Client:
    return httpx.Client(
        transport=httpx.MockTransport(lambda _request: chat_response(content, status))
    )


def test_grounded_answer_normalizes_objects_lists_and_extra_keys():
    answer = GroundedAnswer.model_validate(REAL_WORLD_ANSWER)
    assert answer.source_statements == [
        "8b21aa29: 测试会场 A 的报价为每晚 200 元",
        "第二段是纯字符串",
    ]
    assert answer.inferences == ["单一字符串也应被接受"]
    assert answer.missing_information == []
    assert answer.advice == []


def test_grounded_answer_still_rejects_unreadable_content():
    with pytest.raises(ValidationError):
        GroundedAnswer.model_validate({"text": "", "source_statements": []})
    with pytest.raises(ValidationError):
        GroundedAnswer.model_validate({"text": "t", "source_statements": [5]})
    with pytest.raises(ValidationError):
        GroundedAnswer.model_validate({"text": "t", "source_statements": [{"no": "body"}]})
    with pytest.raises(ValidationError):
        GroundedAnswer.model_validate({"text": "t", "advice": {"not": "a list"}})


def test_deepseek_answer_accepts_the_real_world_payload():
    llm = DeepSeekLLM(
        KEY,
        client=client_for(json.dumps(REAL_WORLD_ANSWER, ensure_ascii=False)),
    )
    answer = llm.answer(
        "测试会场 A 的报价、签约和批准状态分别是什么？",
        [{"heading": "h", "excerpt": "e"}],
    )
    assert answer.text.startswith("测试会场 A")
    assert answer.source_statements[0].startswith("8b21aa29:")


def test_deepseek_organize_ignores_extra_envelope_keys_only():
    content = json.dumps(
        {
            "proposals": [{"title": "合成标题", "kind": "topic", "body": "合成正文"}],
            "type": "json_object",
        },
        ensure_ascii=False,
    )
    llm = DeepSeekLLM(KEY, client=client_for(content))
    proposals = llm.organize([(uuid4(), uuid4(), "## 小节\n正文")])
    assert [proposal.title for proposal in proposals] == ["合成标题"]


def test_proposal_with_a_path_or_trust_field_is_rejected_with_the_field_name():
    content = json.dumps(
        {
            "proposals": [
                {
                    "title": "合成标题",
                    "kind": "topic",
                    "body": "合成正文",
                    "path": "/outside/workspace.md",
                }
            ]
        },
        ensure_ascii=False,
    )
    llm = DeepSeekLLM(KEY, client=client_for(content))
    with pytest.raises(LLMProviderError) as caught:
        llm.organize([(uuid4(), uuid4(), "正文")])
    error = caught.value
    assert error.reason == "schema"
    # Only the field location is named; the offending value is never carried.
    assert "path" in str(error)
    assert "/outside/workspace.md" not in str(error)


def test_non_json_answer_content_is_a_schema_failure():
    llm = DeepSeekLLM(KEY, client=client_for("这不是 JSON"))
    with pytest.raises(LLMProviderError) as caught:
        llm.answer("问题", [{"heading": "h", "excerpt": "e"}])
    assert caught.value.reason == "schema"


def test_deepseek_provider_failure_keeps_structured_details():
    llm = DeepSeekLLM(
        KEY,
        client=client_for(
            json.dumps(
                {
                    "error": {
                        "code": "InsufficientBalance",
                        "message": "Insufficient Balance",
                        "type": "invalid_request_error",
                    }
                }
            ),
            status=402,
        ),
    )
    with pytest.raises(LLMProviderError) as caught:
        llm.answer("问题", [])
    error = caught.value
    assert error.provider_code == "InsufficientBalance"
    assert error.reason == "provider"
    assert error.describe().startswith("InsufficientBalance")
    assert error.details()["message"] == "Insufficient Balance"
    assert isinstance(error, RuntimeError)


def test_provider_error_details_survive_into_the_llm_error():
    original = ProviderError(
        "provider returned an unsuccessful response (HTTP 401)",
        provider_code="invalid_api_key",
        provider_message="Invalid API-key provided.",
        request_id="request-9",
        reason="provider",
    )
    assert original.details() == {
        "code": "invalid_api_key",
        "message": "Invalid API-key provided.",
        "request_id": "request-9",
    }


@pytest.mark.parametrize("blank", ["   ", "\n\t ", "　"])
def test_blank_answer_text_is_rejected(blank):
    with pytest.raises(ValidationError):
        GroundedAnswer.model_validate({"text": blank, "source_statements": []})


def test_answer_text_is_stripped_but_preserved():
    answer = GroundedAnswer.model_validate({"text": "  有内容的回答  ", "source_statements": []})
    assert answer.text == "有内容的回答"


def test_deepseek_blank_content_is_a_schema_failure():
    content = json.dumps({"text": "   ", "source_statements": []}, ensure_ascii=False)
    llm = DeepSeekLLM(KEY, client=client_for(content))
    with pytest.raises(LLMProviderError) as caught:
        llm.answer("问题", [{"heading": "h", "excerpt": "e"}])
    assert caught.value.reason == "schema"
