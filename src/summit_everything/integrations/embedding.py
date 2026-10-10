"""Replaceable local embedding boundary used by the M1 acceptance workflow."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

import httpx


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for word in re.findall(r"[\w]+", text.casefold(), flags=re.UNICODE):
        if re.search(r"[\u3400-\u9fff]", word):
            tokens.extend(word[index : index + 2] for index in range(len(word) - 1))
            if len(word) == 1:
                tokens.append(word)
        else:
            tokens.append(word)
    return tokens


class FakeEmbedding:
    """Deterministic hashed bag-of-words vectors; never contacts a model service."""

    dimensions = 64
    max_batch_size = 20

    def __init__(self) -> None:
        self.calls = 0

    def embed(self, text: str, *, fingerprint: str) -> list[float]:
        self.calls += 1
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            seed = hashlib.sha256(f"{fingerprint}:{token}".encode()).digest()
            bucket = int.from_bytes(seed[:2], "big") % self.dimensions
            vector[bucket] += 1.0 if seed[2] & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]

    def embed_many(self, texts: Sequence[str], *, fingerprint: str) -> list[list[float]]:
        return [self.embed(text, fingerprint=fingerprint) for text in texts]


class ModelStudioEmbedding:
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    endpoint = base_url + "/embeddings"
    model = "qwen3.7-text-embedding"
    dimensions = 1024
    max_batch_size = 20
    max_text_bytes = 50_000

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
        self.endpoint = base_url.rstrip("/") + "/embeddings"
        self._client = client or httpx.Client(timeout=30.0, follow_redirects=False)

    def embed(self, text: str, *, fingerprint: str) -> list[float]:
        del fingerprint
        return self.embed_many([text])[0]

    def embed_many(
        self, texts: Sequence[str], *, fingerprint: str | None = None
    ) -> list[list[float]]:
        del fingerprint
        if not texts or len(texts) > self.max_batch_size:
            raise ValueError("embedding batch size is outside the supported range")
        if any(
            not text.strip() or len(text.encode("utf-8")) > self.max_text_bytes for text in texts
        ):
            raise ValueError("embedding text is outside the supported size range")
        try:
            response = self._client.post(
                self.endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self.model, "input": list(texts), "dimensions": self.dimensions},
            )
            if len(response.content) > 8_000_000:
                raise ValueError("provider response exceeded the size limit")
            response.raise_for_status()
            wire = response.json()
            data = wire["data"]
            if wire.get("model") != self.model or not isinstance(data, list):
                raise ValueError("provider returned an invalid response")
            vectors: list[list[float] | None] = [None] * len(texts)
            for item in data:
                index = item["index"]
                vector = item["embedding"]
                if (
                    isinstance(index, bool)
                    or not isinstance(index, int)
                    or not 0 <= index < len(texts)
                    or vectors[index] is not None
                    or not isinstance(vector, list)
                    or len(vector) != self.dimensions
                ):
                    raise ValueError("provider returned an invalid embedding vector")
                if any(
                    isinstance(value, bool) or not isinstance(value, (int, float))
                    for value in vector
                ):
                    raise ValueError("provider returned a non-numeric embedding vector")
                parsed = [float(value) for value in vector]
                if not all(math.isfinite(value) for value in parsed):
                    raise ValueError("provider returned a non-finite embedding vector")
                vectors[index] = parsed
            if any(vector is None for vector in vectors):
                raise ValueError("provider omitted an embedding vector")
            return [vector for vector in vectors if vector is not None]
        except (httpx.HTTPError, KeyError, TypeError, ValueError, IndexError) as exc:
            raise ValueError("embedding provider failed validation") from exc


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0
    return sum(a * b for a, b in zip(left, right, strict=True))
