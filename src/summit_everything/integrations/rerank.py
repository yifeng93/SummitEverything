"""Local deterministic reranker for repeatable retrieval tests."""

from __future__ import annotations

import math

import httpx

from summit_everything.integrations.embedding import tokenize
from summit_everything.integrations.http_boundary import bounded_json_post


class FakeReranker:
    def score(self, query: str, text: str) -> float:
        query_terms = set(tokenize(query))
        text_terms = set(tokenize(text))
        return len(query_terms & text_terms) / max(1, len(query_terms))

    def rank(self, query: str, texts: list[str]) -> list[tuple[int, float]]:
        scored = [(index, self.score(query, text)) for index, text in enumerate(texts)]
        return sorted(scored, key=lambda item: item[1], reverse=True)


class ModelStudioReranker:
    base_url = "https://dashscope.aliyuncs.com/api/v1"
    endpoint = base_url + "/services/rerank/text-rerank/text-rerank"
    model = "qwen3.7-text-rerank"
    max_documents = 100
    max_request_bytes = 1_000_000

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = base_url,
        client: httpx.Client | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("provider credential is not configured")
        self._api_key = api_key
        self.endpoint = base_url.rstrip("/") + "/services/rerank/text-rerank/text-rerank"
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=30.0, follow_redirects=False)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def score(self, query: str, text: str) -> float:
        result = self.rank(query, [text])
        return result[0][1]

    def rank(self, query: str, texts: list[str]) -> list[tuple[int, float]]:
        if not texts or len(texts) > self.max_documents:
            raise ValueError("rerank candidate count is outside the supported range")
        if not query.strip() or len(query.encode("utf-8")) > 20_000:
            raise ValueError("rerank query is outside the supported size range")
        if any(not text.strip() for text in texts):
            raise ValueError("rerank candidates must not be empty")
        request_bytes = sum(len(text.encode("utf-8")) for text in texts)
        if request_bytes > self.max_request_bytes:
            raise ValueError("rerank request exceeded the size limit")
        try:
            wire = bounded_json_post(
                self._client,
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                payload={
                    "model": self.model,
                    "input": {"query": query, "documents": texts},
                    "parameters": {"return_documents": False},
                },
                max_response_bytes=8_000_000,
            )
            results = wire["output"]["results"]
            if not isinstance(results, list) or len(results) != len(texts):
                raise ValueError("provider returned incomplete rerank results")
            indexed: dict[int, float] = {}
            for result in results:
                index = result["index"]
                raw_score = result["relevance_score"]
                if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
                    raise ValueError("provider returned a non-numeric rerank score")
                score = float(raw_score)
                if (
                    isinstance(index, bool)
                    or not isinstance(index, int)
                    or not 0 <= index < len(texts)
                    or index in indexed
                    or not math.isfinite(score)
                    or not 0 <= score <= 1
                ):
                    raise ValueError("provider returned invalid rerank results")
                indexed[index] = score
            if set(indexed) != set(range(len(texts))):
                raise ValueError("provider returned incomplete rerank results")
            ranked = sorted(indexed.items(), key=lambda item: item[1], reverse=True)
            return ranked
        except (httpx.HTTPError, KeyError, TypeError, ValueError, IndexError) as exc:
            raise ValueError("rerank provider failed validation") from exc
