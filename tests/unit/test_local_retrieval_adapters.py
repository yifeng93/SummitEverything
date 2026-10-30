from __future__ import annotations

import sys
import types
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import pytest

from summit_everything.integrations.embedding import LocalBgeEmbedding
from summit_everything.integrations.rerank import (
    FakeReranker,
    LocalSemanticReranker,
    lexical_overlap_score,
)
from summit_everything.retrieval.chunking import TextChunk


@dataclass
class _Encoding:
    ids: list[int]
    offsets: list[tuple[int, int]]


class _Tokenizer:
    def no_truncation(self) -> None:
        return None

    def no_padding(self) -> None:
        return None

    def encode(self, text: str, *, add_special_tokens: bool) -> _Encoding:
        assert not add_special_tokens
        return _Encoding(list(range(len(text))), [(index, index + 1) for index in range(len(text))])


class _Model:
    tokenizer = _Tokenizer()

    def embed(self, texts: list[str], **_kwargs):
        return [[1.0] + [0.0] * 511 for _ in texts]

    def query_embed(self, texts: list[str], **_kwargs):
        return [[1.0] + [0.0] * 511 for _ in texts]


def test_local_model_disables_onnx_telemetry_before_runtime_creation(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[str] = []
    onnxruntime = types.SimpleNamespace(disable_telemetry_events=lambda: calls.append("telemetry"))
    fastembed = types.SimpleNamespace(
        TextEmbedding=lambda **_kwargs: calls.append("runtime") or _Model()
    )
    tokenizers = types.SimpleNamespace(
        Tokenizer=types.SimpleNamespace(
            from_file=lambda _path: calls.append("tokenizer") or _Tokenizer()
        )
    )
    monkeypatch.setitem(sys.modules, "onnxruntime", onnxruntime)
    monkeypatch.setitem(sys.modules, "fastembed", fastembed)
    monkeypatch.setitem(sys.modules, "tokenizers", tokenizers)

    LocalBgeEmbedding(tmp_path)

    assert calls == ["telemetry", "runtime", "tokenizer"]


def test_local_windows_preserve_source_substrings_and_include_tail() -> None:
    source = (
        "背景信息。" * 170 + "访客𰻞字（合成）：费用 1800 元，项目A-01。尾部事实：证章在西侧领取。"
    )
    chunk = TextChunk(
        page_id=uuid4(),
        content_sha256="a" * 64,
        chunk_id="source-chunk",
        heading="办理方式",
        text=source,
    )
    provider = LocalBgeEmbedding.__new__(LocalBgeEmbedding)
    provider._tokenizer = _Tokenizer()
    provider._model = _Model()
    provider.calls = 0

    windows = provider.split_for_index([chunk])
    assert len(windows) > 1
    assert all(window.text in source for window in windows)
    assert all(
        "访客𰻞字（合成）：费用 1800 元，项目A-01。" not in window.text for window in windows[:-1]
    )
    assert "尾部事实：证章在西侧领取。" in windows[-1].text
    assert windows[-1].heading == chunk.heading
    assert windows[-1].page_id == chunk.page_id
    assert len({window.chunk_id for window in windows}) == len(windows)


def test_local_embedding_checks_vector_shape_and_query_windows() -> None:
    provider = LocalBgeEmbedding.__new__(LocalBgeEmbedding)
    provider._tokenizer = _Tokenizer()
    provider._model = _Model()
    provider.calls = 0

    vector = provider.embed("查询内容" * 170, fingerprint="test")
    vectors = provider.embed_many(["正文内容" * 170], fingerprint="test")
    assert len(vector) == len(vectors[0]) == 512
    assert sum(value * value for value in vector) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "query,texts",
    [
        ("", ["candidate"]),
        ("q", []),
        ("q", [""]),
        ("q", ["x" * (LocalSemanticReranker.max_document_bytes + 1)]),
    ],
)
def test_local_reranker_rejects_invalid_bounds(query: str, texts: list[str]) -> None:
    reranker = LocalSemanticReranker(_ModelEmbedding())
    with pytest.raises(ValueError):
        reranker.rank(query, texts)


class _ModelEmbedding:
    max_batch_size = 20

    def embed(self, _text: str, *, fingerprint: str) -> list[float]:
        return [1.0, 0.0]

    def embed_many(self, texts: list[str], *, fingerprint: str) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


def test_local_reranker_returns_each_duplicate_candidate_once_with_bounded_scores() -> None:
    reranker = LocalSemanticReranker(_ModelEmbedding())  # type: ignore[arg-type]
    ranking = reranker.rank("target fact", ["target fact", "target fact", "other"])
    assert sorted(index for index, _score in ranking) == [0, 1, 2]
    assert all(0 <= score <= 1 for _index, score in ranking)


def test_runtime_lexical_overlap_keeps_the_fake_score_calculation_exact() -> None:
    cases = [
        ("DeepSeek Harness update replace", "update and replace settings"),
        ("地点 联系人", "会议地点与联系人待确认"),
        ("无匹配术语", "完全不同的一段文字"),
    ]
    fake = FakeReranker()
    for query, text in cases:
        assert lexical_overlap_score(query, text) == fake.score(query, text)
