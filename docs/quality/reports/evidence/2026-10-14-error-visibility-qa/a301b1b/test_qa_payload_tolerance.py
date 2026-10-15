"""Item 2/3 — real DeepSeek-shaped payload tolerance, rejection and citation source.

Everything here goes through the *real* adapter (``DeepSeekLLM``) with an
``httpx.MockTransport`` standing in for the provider. No network, no real key.
"""

from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import pytest

from summit_everything.domain.content import RetrievalPurpose
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.llm import DeepSeekLLM, GroundedAnswer, LLMProviderError
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import create_line, create_project, create_workspace
from summit_everything.workspace.writer import PageWriter

from qa_helpers import SENTINEL_KEY, deepseek_wire, json_response, mock_client

PASSAGES = [{"heading": "合成页", "excerpt": "合成事实：演示地点是北馆。", "source_id": "page-1"}]

#: The exact shape the user's real DeepSeek call produced: source_statements are
#: objects with source_id/quote, plus extra keys the strict schema forbade.
REAL_SHAPE = {
    "text": "演示地点是北馆。",
    "source_statements": [
        {"source_id": "x", "quote": "合成事实：演示地点是北馆。", "type": "fact", "confidence": 0.91}
    ],
    "inferences": [{"quote": "推断：北馆可用", "type": "inference"}],
    "advice": [],
    "missing_information": [],
    "type": "grounded_answer",
}


def adapter_answering(payload: object, *, capture: dict[str, object] | None = None) -> DeepSeekLLM:
    content = json.dumps(payload, ensure_ascii=False)

    def handler(request):  # noqa: ANN001, ANN202
        if capture is not None:
            capture["body"] = json.loads(request.content)
        return json_response(deepseek_wire(content))

    return DeepSeekLLM(SENTINEL_KEY, client=mock_client(handler))


def test_real_shape_is_accepted_and_normalized_to_plain_strings() -> None:
    llm = adapter_answering(REAL_SHAPE)
    answer = llm.answer("演示地点在哪？", PASSAGES)

    assert isinstance(answer, GroundedAnswer)
    assert answer.text.strip(), answer.text
    assert answer.source_statements, "source_statements must not be empty"
    assert all(isinstance(item, str) and item.strip() for item in answer.source_statements)
    # Object form is normalized to one single-line string; the extra keys are ignored.
    assert answer.source_statements == ["x: 合成事实：演示地点是北馆。"]
    assert all(isinstance(item, str) for item in answer.inferences)
    assert all(isinstance(item, str) for item in answer.advice)
    assert all(isinstance(item, str) for item in answer.missing_information)
    assert "type" not in answer.model_dump()


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"text": "答案", "source_statements": [{"foo": 1}]}, id="object-without-text"),
        pytest.param({"text": "答案", "source_statements": [1, 2]}, id="numeric-elements"),
        pytest.param({"text": "答案", "source_statements": [["nested"]]}, id="nested-list"),
        pytest.param({"text": "答案", "source_statements": [{"quote": ""}]}, id="empty-quote"),
        pytest.param({"text": "", "source_statements": ["x"]}, id="empty-text"),
        pytest.param({"source_statements": ["x"]}, id="missing-text"),
        pytest.param({"text": "答案", "advice": [{"foo": 1}]}, id="unreadable-advice"),
    ],
)
def test_unreadable_payload_is_rejected_not_silently_dropped(payload: dict) -> None:
    llm = adapter_answering(payload)
    with pytest.raises(LLMProviderError) as caught:
        llm.answer("问题", PASSAGES)
    assert caught.value.reason == "schema"
    # The rejection names field locations, never the offending provider values.
    assert "答案" not in str(caught.value) or "text" in str(caught.value)


def test_whitespace_only_text_observation() -> None:
    """Observation: ``text`` is only length-checked, so blank text still passes."""
    llm = adapter_answering({"text": "   ", "source_statements": []})
    answer = llm.answer("问题", PASSAGES)
    assert answer.text == "   "
    assert not answer.text.strip()


def test_prompt_states_the_target_json_shape_and_forbids_extra_keys() -> None:
    capture: dict[str, object] = {}
    llm = adapter_answering(REAL_SHAPE, capture=capture)
    llm.answer("演示地点在哪？", PASSAGES)

    body = capture["body"]
    assert isinstance(body, dict)
    system = body["messages"][0]["content"]
    user = body["messages"][1]["content"]
    assert body["messages"][0]["role"] == "system"

    for fragment in (
        "no additional keys",
        '"text": string',
        '"source_statements": [string]',
        '"inferences": [string]',
        '"advice": [string]',
        '"missing_information": [string]',
        "plain string",
        "never an object",
        "do not add extra keys such as type or confidence",
    ):
        assert fragment in system, fragment
    assert "untrusted" in system
    # The question and passages travel as data, not as instructions.
    assert "演示地点在哪？" in user
    assert "北馆" in user


def _workspace_with_one_page(tmp_path: Path) -> tuple[Path, str, str]:
    root = tmp_path / "workspace"
    create_workspace(root, "QA 检索库", tmp_path / "profile", "workspace")
    line = create_line(root, "QA 线", "line")
    project = create_project(root, line.id, "QA 项目", "project")
    metadata = {
        "id": "11111111-1111-1111-1111-111111111111",
        "title": "合成页",
        "role": "knowledge",
        "kind": "topic",
        "line_id": str(line.id),
        "project_id": str(project.id),
    }
    PageWriter().confirm(
        root,
        metadata=metadata,
        body="合成事实：雪松项目的正式演示地点是北馆。",
        confirmation_id="qa-confirm-1",
        operation_id="qa-write-1",
    )
    return root, str(line.id), str(project.id)


def test_citations_come_from_our_own_retrieval_not_the_model_claimed_id(tmp_path: Path) -> None:
    """Falsification attempt: a model-reported source_id must never become a citation."""
    root, _line_id, _project_id = _workspace_with_one_page(tmp_path)
    model_content = json.dumps(
        {
            "text": "模型正文。",
            "source_statements": [
                {
                    "source_id": "MODEL-CLAIMED-SOURCE-ID",
                    "quote": "模型自称引用自某个并不存在的来源。",
                }
            ],
        },
        ensure_ascii=False,
    )

    def handler(request):  # noqa: ANN001, ANN202
        return json_response(deepseek_wire(model_content))

    llm = DeepSeekLLM(SENTINEL_KEY, client=mock_client(handler))
    service = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=llm,
    )
    service.rebuild(root, fingerprint="fake-v1")
    answer = service.query(
        root,
        "雪松项目演示地点",
        fingerprint="fake-v1",
        purpose=RetrievalPurpose.CURRENT,
        limit=1,
    )

    assert answer is not None
    assert answer.citations, "the app must produce its own citation"
    cited_ids = {str(citation.page_id) for citation in answer.citations}
    assert cited_ids == {"11111111-1111-1111-1111-111111111111"}
    assert "MODEL-CLAIMED-SOURCE-ID" not in str(answer.source_statements)
    assert "MODEL-CLAIMED-SOURCE-ID" not in answer.text
    # Application-derived statements replace the model's entirely.
    assert answer.source_statements
    assert all("北馆" in item for item in answer.source_statements)
    assert "模型自称引用自某个并不存在的来源。" not in str(answer.source_statements)


def test_answer_text_from_the_model_is_still_used(tmp_path: Path) -> None:
    """The model's prose is used, so the parse tolerance is not a no-op."""
    root, _l, _p = _workspace_with_one_page(tmp_path)
    content = json.dumps({"text": "北馆是已确认的演示地点。", "source_statements": []})
    llm = DeepSeekLLM(
        SENTINEL_KEY, client=mock_client(lambda request: json_response(deepseek_wire(content)))
    )
    service = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=llm,
    )
    service.rebuild(root, fingerprint="fake-v1")
    answer = service.query(
        root,
        "雪松项目演示地点",
        fingerprint="fake-v1",
        purpose=RetrievalPurpose.CURRENT,
        limit=1,
    )
    assert "北馆是已确认的演示地点。" in answer.text
    assert answer.citations[0].chunk_id
    assert answer.citations[0].page_id == UUID("11111111-1111-1111-1111-111111111111")


def test_bare_string_notes_are_accepted_as_a_one_element_list() -> None:
    """Documented leniency: a bare string is wrapped, never dropped."""
    llm = adapter_answering({"text": "答案", "source_statements": "只有一条"})
    answer = llm.answer("问题", PASSAGES)
    assert answer.source_statements == ["只有一条"]
