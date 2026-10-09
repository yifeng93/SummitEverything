"""Local deterministic reranker for repeatable retrieval tests."""

from __future__ import annotations

from summit_everything.integrations.embedding import tokenize


class FakeReranker:
    def score(self, query: str, text: str) -> float:
        query_terms = set(tokenize(query))
        text_terms = set(tokenize(text))
        return len(query_terms & text_terms) / max(1, len(query_terms))
