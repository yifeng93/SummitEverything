"""Local deterministic reranker for repeatable retrieval tests."""

from __future__ import annotations

import math

import httpx

from summit_everything.integrations.embedding import LocalBgeEmbedding, cosine_similarity, tokenize
from summit_everything.integrations.http_boundary import (
    ProviderError,
    bounded_json_post,
    provider_usage_record,
    reject_business_error,
)
from summit_everything.integrations.transport import create_http_client


class RerankProviderError(ProviderError):
    """The rerank service failed; carries its sanitized code/message/id."""


def lexical_overlap_score(query: str, text: str) -> float:
    query_terms = set(tokenize(query))
    text_terms = set(tokenize(text))
    return len(query_terms & text_terms) / max(1, len(query_terms))


class FakeReranker:
    def score(self, query: str, text: str) -> float:
        return lexical_overlap_score(query, text)

    def rank(self, query: str, texts: list[str]) -> list[tuple[int, float]]:
        scored = [(index, self.score(query, text)) for index, text in enumerate(texts)]
        return sorted(scored, key=lambda item: item[1], reverse=True)


class LocalSemanticReranker:
    """Rank the locally retrieved candidates with the installed BGE model."""

    # Positive cosine alone is not evidence: unrelated passages can still have
    # positive scores. Preserve a candidate only on semantic or lexical evidence.
    max_documents = 20
    max_query_bytes = 20_000
    max_document_bytes = 1_000_000
    semantic_cosine_threshold = 0.54
    lexical_overlap_threshold = 0.20

    def __init__(self, embedding: LocalBgeEmbedding) -> None:
        self.embedding = embedding

    def rank(self, query: str, texts: list[str]) -> list[tuple[int, float]]:
        if not texts or len(texts) > self.max_documents:
            raise ValueError("rerank candidate count is outside the supported range")
        if not query.strip() or len(query.encode("utf-8")) > self.max_query_bytes:
            raise ValueError("rerank query is outside the supported size range")
        if any(
            not text.strip() or len(text.encode("utf-8")) > self.max_document_bytes
            for text in texts
        ):
            raise ValueError("rerank candidates are outside the supported size range")
        query_vector = self.embedding.embed(query, fingerprint="local")
        candidates: list[list[float]] = []
        for offset in range(0, len(texts), self.embedding.max_batch_size):
            candidates.extend(
                self.embedding.embed_many(
                    texts[offset : offset + self.embedding.max_batch_size], fingerprint="local"
                )
            )
        scored = []
        for index, (text, vector) in enumerate(zip(texts, candidates, strict=True)):
            overlap = lexical_overlap_score(query, text)
            cosine = cosine_similarity(query_vector, vector)
            if overlap >= self.lexical_overlap_threshold:
                score = max(0.55, min(1.0, overlap))
            elif cosine >= self.semantic_cosine_threshold:
                score = 0.55 + min(1.0, (cosine - self.semantic_cosine_threshold) / 0.46) * 0.45
            else:
                score = 0.0
            scored.append((index, score))
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
        self._client = client or create_http_client()
        self.usage_records: list[dict[str, object]] = []

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
                max_request_bytes=self.max_request_bytes,
                deadline_seconds=30.0,
            )
            self.usage_records.append(provider_usage_record(self.model, wire))
            reject_business_error(wire)
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
        except ProviderError as exc:
            raise RerankProviderError(
                f"排序服务返回错误：{exc.describe()}",
                provider_code=exc.provider_code,
                provider_message=exc.provider_message,
                request_id=exc.request_id,
                reason=exc.reason or "provider",
            ) from exc
        except httpx.HTTPError as exc:
            raise RerankProviderError(
                "排序服务连接失败：请检查网络、代理或证书设置。", reason="transport"
            ) from exc
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            # Unusable 200 content is a provider failure too; local candidate and
            # size checks above stay plain ValueError.
            raise RerankProviderError(
                "排序服务返回了无法解析的响应：请检查所选模型与接口是否匹配。",
                reason="schema",
            ) from exc
