from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from summit_everything.domain.content import RetrievalPurpose  # noqa: E402
from summit_everything.integrations.embedding import FakeEmbedding, tokenize  # noqa: E402
from summit_everything.integrations.rerank import FakeReranker  # noqa: E402
from summit_everything.retrieval.query import QueryService, cosine_similarity  # noqa: E402
from summit_everything.retrieval.store import IndexStore  # noqa: E402
from summit_everything.workspace.manifest import load_manifest  # noqa: E402
from summit_everything.workspace.reader import list_pages  # noqa: E402

workspace = ROOT / "workspace-B"
workspace_id = load_manifest(workspace).workspace_id
index_path = ROOT / "profiles-A" / str(workspace_id) / "index.sqlite3"
fingerprint = "summit-fake-embedding-v1"
question = "青岚计划的预算上限是多少？"
embedding = FakeEmbedding()
reranker = FakeReranker()
service = QueryService(IndexStore(index_path), embedding, reranker=reranker)
chunks = service.store.get_chunks(workspace_id, fingerprint)
query_vector = embedding.embed(question, fingerprint=fingerprint)
dense = sorted(chunks, key=lambda item: cosine_similarity(query_vector, item["vector"]), reverse=True)
qualified = service._qualified_chunks(workspace, dense, purpose=RetrievalPurpose.CURRENT)
candidates = qualified[:20]
rerank_scores = reranker.rank(question, [str(item["text"]) for item in candidates])
pages = list_pages(workspace)
ranking: list[dict] = []
for item in dense:
    page = next((page for page in pages if page.page_id == item["page_id"]), None)
    ranking.append(
        {
            "page_id": str(item["page_id"]),
            "excerpt": item["text"],
            "validity": page.metadata.get("validity") if page else None,
            "page_content_sha256": page.content_sha256 if page else None,
            "indexed_content_sha256": item["content_sha256"],
            "qualified_for_current": any(candidate["chunk_id"] == item["chunk_id"] for candidate in qualified),
            "cosine_similarity": cosine_similarity(query_vector, item["vector"]),
            "rerank_score": next(
                (score for index, score in rerank_scores if candidates[index]["chunk_id"] == item["chunk_id"]),
                None,
            ),
            "vector_sha256": hashlib.sha256(
                json.dumps(item["vector"], separators=(",", ":")).encode()
            ).hexdigest(),
        }
    )
service.close()

api = "http://127.0.0.1:18793/api/v1"
headers = {"Authorization": f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}
with httpx.Client(headers=headers, timeout=30) as client:
    response = client.post(
        api + "/queries",
        json={
            "request_id": str(uuid.uuid4()),
            "question": question,
            "fingerprint": fingerprint,
            "purpose": "current",
            "answer_mode": "fact",
        },
    )
    events = [
        json.loads(line[6:])
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    completed = next((event["data"] for event in events if event["type"] == "completed"), {})
    result = {
        "case": "C19-current-fact-retrieval-relevance",
        "question": question,
        "query_tokens": tokenize(question),
        "index_fingerprint": fingerprint,
        "dense_and_rerank": ranking,
        "reranker_input_order": [candidate["text"] for candidate in candidates],
        "reranker_raw_index_score": rerank_scores,
        "http": response.status_code,
        "answer_index_status": completed.get("index_status"),
        "final_citations": completed.get("citations", []),
        "provider_source_statements": completed.get("source_statements", []),
        "missing_information": completed.get("missing_information", []),
    }
    output = ROOT / "harness" / "retrieval-diagnostics.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
