"""Independent DEV review counterexamples. Synthetic data; no provider network/Keychain."""

import json

import httpx
from fastapi.testclient import TestClient
from test_qualified_retrieval import approve_page, create_test_workspace

from summit_everything.api.app import create_app
from summit_everything.integrations.llm import GroundedAnswer
from summit_everything.integrations.rerank import ModelStudioReranker
from summit_everything.integrations.settings import MemorySecretBackend
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.reader import list_pages

FP = "summit-fake-embedding-v1"
HEADERS = {"Authorization": "Bearer review-synthetic-session"}


def _workspace(tmp_path, body="SYNTHETIC_STALE_CANARY 合成地点北馆。"):
    root, line, project = create_test_workspace(tmp_path / "workspace")
    page_id, _ = approve_page(root, line, project, body=body)
    path = root / next(p.relative_path for p in list_pages(root) if p.page_id == page_id)
    return root, path


def _client(tmp_path, *, service=None):
    app = create_app(
        session_token="review-synthetic-session",
        profile_root=tmp_path / "profile",
        secret_backend=MemorySecretBackend(),
        query_service=service,
    )
    return TestClient(app)


def _open(c, path, mode="create"):
    return c.post(
        "/api/v1/workspaces",
        headers=HEADERS,
        json={"root": str(path), "mode": mode, "name": "Synthetic Review", "operation_id": "open"},
    )


def test_stale_cached_text_must_not_reach_reranker(tmp_path):
    root, path = _workspace(tmp_path)
    captured = []

    class Spy:
        def rank(self, question, texts):
            captured.extend(texts)
            return [(i, 1.0) for i in range(len(texts))]

    query = QueryService(IndexStore(tmp_path / "index.sqlite3"), reranker=Spy())
    query.rebuild(root, fingerprint=FP)
    path.write_text(path.read_text().replace("北馆", "西馆"))
    answer = query.query(root, "合成地点", fingerprint=FP)
    assert answer.citations == []  # Existing final gate works.
    assert not any("SYNTHETIC_STALE_CANARY" in t for t in captured), captured


def test_citations_must_be_rechecked_after_answer_provider_returns(tmp_path):
    root, path = _workspace(tmp_path)

    class EditingAnswerer:
        def answer(self, question, passages):
            path.write_text(path.read_text().replace("北馆", "西馆"))
            return GroundedAnswer(text="北馆。")

    query = QueryService(IndexStore(tmp_path / "index.sqlite3"), answer_provider=EditingAnswerer())
    query.rebuild(root, fingerprint=FP)
    answer = query.query(root, "合成地点", fingerprint=FP)
    assert not answer.citations, answer.model_dump()
    assert "北馆" not in answer.text


def test_query_with_101_chunks_uses_bounded_candidates(tmp_path):
    root, _ = _workspace(
        tmp_path,
        body="\n\n".join(f"## Section {i}\n合成地点 {i}。" for i in range(101)),
    )
    query = QueryService(IndexStore(tmp_path / "index.sqlite3"))
    result = query.rebuild(root, fingerprint=FP)
    assert result.indexed_chunks == 101
    seen = []

    def handler(request):
        seen.append(request)
        count = len(json.loads(request.content)["input"]["documents"])
        return httpx.Response(
            200,
            json={
                "output": {"results": [{"index": i, "relevance_score": 1.0} for i in range(count)]}
            },
        )

    query.reranker = ModelStudioReranker(
        "synthetic-key",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    answer = query.query(root, "合成地点", fingerprint=FP)
    sent = json.loads(seen[0].content)["input"]["documents"]
    assert answer.citations
    assert 0 < len(sent) <= 20
