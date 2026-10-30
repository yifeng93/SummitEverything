"""Contract and regression replay for provider organize responses (synthetic only)."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from summit_everything.integrations.llm import DeepSeekLLM, LLMProviderError

REPLAY = Path(__file__).parents[1] / "fixtures" / "deepseek-organize-success-replay.json"


@pytest.mark.parametrize("record", json.loads(REPLAY.read_text(encoding="utf-8")))
def test_replays_all_18_previously_successful_synthetic_organize_payloads(record: dict) -> None:
    body = json.dumps({"proposals": record["proposals"]}, ensure_ascii=False)
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": body}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
                request=request,
            )
        )
    )
    result = DeepSeekLLM("synthetic-api-key", client=client).organize(
        [(uuid4(), uuid4(), "合成来源：人数上限24人。")]
    )

    assert len(result) == len(record["proposals"])
    assert all(proposal.title.strip() and proposal.body.strip() for proposal in result)
    assert all(proposal.input_indexes == [0] for proposal in result)


def test_organize_prompt_spells_out_typed_strict_proposal_contract() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "proposals": [
                                        {
                                            "title": "合成标题",
                                            "kind": "topic",
                                            "body": "合成正文",
                                            "input_indexes": [0],
                                            "important_conflicts": [],
                                            "action_suggestions": [],
                                        }
                                    ]
                                },
                                ensure_ascii=False,
                            )
                        },
                        "finish_reason": "stop",
                    }
                ]
            },
            request=request,
        )

    model = DeepSeekLLM(
        "synthetic-api-key", client=httpx.Client(transport=httpx.MockTransport(handler))
    )
    model.organize([(uuid4(), uuid4(), "合成输入")])
    system = json.loads(seen[0].content)["messages"][0]["content"]
    for field in (
        "title (non-empty string)",
        "kind (one of the strings object, case, topic, decision)",
        "input_indexes (array of integer input indexes)",
        "important_conflicts (array of objects with id:string",
        "action_suggestions (array of objects with kind: todo or progress_change",
        "Do not add fields",
    ):
        assert field in system


def test_organize_schema_diagnostic_names_fields_without_echoing_bad_values() -> None:
    bad_secret = "synthetic-private-provider-content"
    response = json.dumps(
        {
            "proposals": [
                {
                    "title": "合成标题",
                    "kind": "topic",
                    "body": "合成正文",
                    "input_indexes": [bad_secret],
                    "important_conflicts": [],
                    "action_suggestions": [],
                }
            ]
        },
        ensure_ascii=False,
    )
    model = DeepSeekLLM(
        "synthetic-api-key",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"choices": [{"message": {"content": response}, "finish_reason": "stop"}]},
                    request=request,
                )
            )
        ),
    )

    with pytest.raises(LLMProviderError) as caught:
        model.organize([(uuid4(), uuid4(), "合成输入")])

    assert caught.value.reason == "schema"
    assert "input_indexes.0" in str(caught.value)
    assert bad_secret not in str(caught.value)
    assert "synthetic-api-key" not in str(caught.value)


def test_schema_diagnostic_redacts_provider_chosen_unknown_field_names() -> None:
    private_key = "sk-synthetic-never-echo-this"
    response = json.dumps(
        {
            "proposals": [
                {
                    "title": "合成标题",
                    "kind": "topic",
                    "body": "合成正文",
                    "input_indexes": [0],
                    "important_conflicts": [],
                    "action_suggestions": [],
                    private_key: "private-value",
                }
            ]
        },
        ensure_ascii=False,
    )
    model = DeepSeekLLM(
        "synthetic-api-key",
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={"choices": [{"message": {"content": response}, "finish_reason": "stop"}]},
                    request=request,
                )
            )
        ),
    )

    with pytest.raises(LLMProviderError) as caught:
        model.organize([(uuid4(), uuid4(), "合成输入")])

    message = str(caught.value)
    assert caught.value.reason == "schema"
    assert "proposals.0" in message
    assert "<extra>" in message
    assert private_key not in message
    assert "private-value" not in message
    assert "synthetic-api-key" not in message
