"""Item 9 — the two declared safety deviations must genuinely hold."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from summit_everything.integrations.llm import (
    DeepSeekLLM,
    DraftProposal,
    LLMProviderError,
    schema_failure_message,
)

from qa_helpers import SENTINEL_KEY, deepseek_wire, json_response, mock_client


def _complete(payload: object, capture: dict | None = None) -> list[DraftProposal]:
    content = json.dumps(payload, ensure_ascii=False)

    def handler(request):  # noqa: ANN001, ANN202
        if capture is not None:
            capture["body"] = json.loads(request.content)
        return json_response(deepseek_wire(content))

    llm = DeepSeekLLM(SENTINEL_KEY, client=mock_client(handler))
    return llm.organize([("11111111-1111-1111-1111-111111111111", "22222222-2222-2222-2222-222222222222", "合成文本")])


VALID_PROPOSAL = {
    "title": "合成整理稿",
    "kind": "topic",
    "body": "## 合成\n\n合成正文。\n",
    "input_indexes": [0],
    "important_conflicts": [],
    "action_suggestions": [],
}


@pytest.mark.parametrize(
    "extra",
    [
        {"approval": {"version": 1}},
        {"path": "/outside/workspace.md"},
        {"confirmation_id": "model-issued"},
        {"published": True},
    ],
)
def test_proposal_still_forbids_extra_trust_and_path_fields(extra: dict) -> None:
    with pytest.raises(ValidationError):
        DraftProposal.model_validate({**VALID_PROPOSAL, **extra})
    # And through the real adapter, not only the model class.
    with pytest.raises(LLMProviderError) as caught:
        _complete({"proposals": [{**VALID_PROPOSAL, **extra}]})
    assert caught.value.reason == "schema"


def test_envelope_tolerates_extra_keys_but_items_do_not() -> None:
    """The declared deviation: only the envelope layer is lenient."""
    proposals = _complete({"proposals": [VALID_PROPOSAL], "type": "organize_result", "extra": 1})
    assert len(proposals) == 1
    assert proposals[0].title == "合成整理稿"

    with pytest.raises(LLMProviderError):
        _complete({"type": "organize_result"})  # no proposals key
    with pytest.raises(LLMProviderError):
        _complete({"proposals": []})  # silently empty would be a silent acceptance
    with pytest.raises(LLMProviderError):
        _complete({"proposals": "not-a-list"})
    with pytest.raises(LLMProviderError):
        _complete({"proposals": [{"title": "只有标题"}]})


def test_schema_failure_message_names_locations_without_values() -> None:
    secret_value = "秘密正文内容"
    with pytest.raises(ValidationError) as caught:
        DraftProposal.model_validate({"title": "", "kind": "topic", "body": secret_value, "x": 1})
    message = schema_failure_message("proposals", caught.value)
    assert message.startswith("proposals schema mismatch")
    assert secret_value not in message
    assert len(message) <= 300


def test_unknown_exception_text_is_never_confirmed_as_accepted_elsewhere() -> None:
    """A sanity guard for this QA harness itself: no silent-accept pass-through."""
    with pytest.raises(LLMProviderError):
        _complete({"proposals": [{"title": "t", "kind": "topic", "body": "b", "input_indexes": [0], "important_conflicts": [], "action_suggestions": [], "unknown": 1}]})
