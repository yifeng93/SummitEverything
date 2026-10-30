"""Replaceable local embedding boundary used by the M1 acceptance workflow."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx

from summit_everything.integrations.http_boundary import (
    ProviderError,
    bounded_json_post,
    provider_usage_record,
    reject_business_error,
)
from summit_everything.integrations.transport import create_http_client


class EmbeddingProviderError(ProviderError):
    """The embedding service failed; carries its sanitized code/message/id."""


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


class LocalBgeEmbedding:
    """Pinned CPU-only BGE embedding with explicit token windows for long text.

    FastEmbed is configured with ``local_files_only`` and ``specific_model_path``
    so an index or query can never cause an implicit model download. Windowing
    keeps every input token represented instead of silently accepting ONNX's
    512-token truncation.
    """

    dimensions = 512
    is_local = True
    max_batch_size = 20
    max_text_bytes = 1_000_000
    window_tokens = 480
    overlap_tokens = 64

    def __init__(self, model_directory: Path, *, model: Any | None = None) -> None:
        if model is None:
            import onnxruntime  # type: ignore[import-untyped]
            from fastembed import TextEmbedding
            from tokenizers import Tokenizer

            # FastEmbed's ONNX session may otherwise emit anonymous runtime
            # telemetry; local inference must stay on-device and quiet.
            onnxruntime.disable_telemetry_events()
            model = TextEmbedding(
                model_name="BAAI/bge-small-zh-v1.5",
                specific_model_path=str(model_directory),
                local_files_only=True,
                threads=2,
                providers=["CPUExecutionProvider"],
            )
            self._tokenizer: Any = Tokenizer.from_file(str(model_directory / "tokenizer.json"))
            self._tokenizer.no_truncation()
            self._tokenizer.no_padding()
        else:
            # Synthetic model doubles can expose the small tokenizer contract.
            self._tokenizer = getattr(model, "tokenizer", None)
        self._model = model
        self.calls = 0

    def _token_windows(self, text: str) -> list[tuple[str, int]]:
        if not text.strip() or len(text.encode("utf-8")) > self.max_text_bytes:
            raise ValueError("local embedding text is outside the supported size range")
        tokenizer = self._tokenizer
        if tokenizer is None:
            return [(text, 1)]
        encoding = tokenizer.encode(text, add_special_tokens=False)
        token_ids = encoding.ids
        if not token_ids:
            return [(text, 1)]
        result: list[tuple[str, int]] = []
        stride = self.window_tokens - self.overlap_tokens
        start = 0
        while start < len(token_ids):
            end = min(len(token_ids), start + self.window_tokens)
            start_char = encoding.offsets[start][0]
            end_char = encoding.offsets[end - 1][1]
            window = text[start_char:end_char]
            if window:
                result.append((window, end - start))
            if end == len(token_ids):
                break
            start += stride
        return result or [(text, 1)]

    def _windows(self, text: str) -> list[tuple[str, int]]:
        return self._token_windows(text)

    def split_for_index(self, chunks: Sequence[Any]) -> list[Any]:
        """Store long passages as independently retrievable token windows.

        Each window keeps its source page/version/heading, while a stable ID
        prevents an incremental build from confusing different window contents.
        This preserves rare tail facts that a whole-chunk mean vector would dilute.
        """
        tokenizer = self._tokenizer
        if tokenizer is None:
            return list(chunks)
        result: list[Any] = []
        stride = self.window_tokens - self.overlap_tokens
        for chunk in chunks:
            encoding = tokenizer.encode(chunk.text, add_special_tokens=False)
            token_ids = encoding.ids
            if len(token_ids) <= self.window_tokens:
                result.append(chunk)
                continue
            for window_index, start in enumerate(range(0, len(token_ids), stride)):
                end = min(len(token_ids), start + self.window_tokens)
                start_char = encoding.offsets[start][0]
                end_char = encoding.offsets[end - 1][1]
                text = chunk.text[start_char:end_char]
                if not text:
                    continue
                chunk_id = hashlib.sha256(
                    f"{chunk.chunk_id}:{window_index}:{text}".encode()
                ).hexdigest()
                result.append(
                    type(chunk)(
                        page_id=chunk.page_id,
                        content_sha256=chunk.content_sha256,
                        chunk_id=chunk_id,
                        heading=chunk.heading,
                        text=text,
                    )
                )
                if end == len(token_ids):
                    break
        return result

    @staticmethod
    def _normalize(vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if not math.isfinite(norm) or norm <= 0:
            raise ValueError("local embedding returned an invalid vector")
        return [value / norm for value in vector]

    def _embed_texts(self, texts: Sequence[str], *, query: bool) -> list[list[float]]:
        if not texts or len(texts) > self.max_batch_size:
            raise ValueError("local embedding batch size is outside the supported range")
        windows = [self._windows(text) for text in texts]
        flat = [window for text_windows in windows for window, _weight in text_windows]
        self.calls += 1
        embed = self._model.query_embed if query else self._model.embed
        raw = list(embed(flat, batch_size=self.max_batch_size, parallel=None))
        if len(raw) != len(flat):
            raise ValueError("local embedding returned an incomplete batch")
        vectors: list[list[float]] = []
        position = 0
        for text_windows in windows:
            combined = [0.0] * self.dimensions
            weight_total = 0
            for _window, weight in text_windows:
                value = raw[position]
                position += 1
                vector = [float(item) for item in value]
                if len(vector) != self.dimensions or not all(
                    math.isfinite(item) for item in vector
                ):
                    raise ValueError("local embedding returned an invalid vector")
                for index, item in enumerate(vector):
                    combined[index] += item * weight
                weight_total += weight
            if weight_total <= 0:
                raise ValueError("local embedding returned no tokens")
            vectors.append(self._normalize([item / weight_total for item in combined]))
        return vectors

    def embed(self, text: str, *, fingerprint: str) -> list[float]:
        del fingerprint
        return self._embed_texts([text], query=True)[0]

    def embed_many(self, texts: Sequence[str], *, fingerprint: str) -> list[list[float]]:
        del fingerprint
        return self._embed_texts(texts, query=False)


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
        self._owns_client = client is None
        self._client = client or create_http_client()
        self.usage_records: list[dict[str, Any]] = []

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

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
            wire = bounded_json_post(
                self._client,
                self.endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                payload={
                    "model": self.model,
                    "input": list(texts),
                    "dimensions": self.dimensions,
                },
                max_response_bytes=8_000_000,
                deadline_seconds=30.0,
            )
            self.usage_records.append(provider_usage_record(self.model, wire))
            reject_business_error(wire)
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
        except ProviderError as exc:
            # Keep the service's own wording: an opaque 500 hid a bad key, a
            # missing model permission and a malformed key during first use.
            raise EmbeddingProviderError(
                f"向量服务返回错误：{exc.describe()}",
                provider_code=exc.provider_code,
                provider_message=exc.provider_message,
                request_id=exc.request_id,
                reason=exc.reason or "provider",
            ) from exc
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError(
                "向量服务连接失败：请检查网络、代理或证书设置。", reason="transport"
            ) from exc
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            # A 200 response whose content is unusable (missing or empty ``data``,
            # non-JSON body, wrong vector shape) is still a provider failure, not
            # a local one: it must surface as a typed 502 instead of a bare 500.
            # Local parameter checks run before this block and stay unchanged.
            raise EmbeddingProviderError(
                "向量服务返回了无法解析的响应：请检查所选模型与接口是否匹配。",
                reason="schema",
            ) from exc


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        return 0
    return sum(a * b for a, b in zip(left, right, strict=True))
