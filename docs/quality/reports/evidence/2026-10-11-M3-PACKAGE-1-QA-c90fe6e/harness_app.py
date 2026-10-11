from __future__ import annotations

import os
import time
from pathlib import Path

from summit_everything.api.app import create_app
from summit_everything.domain.content import RetrievalPurpose
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.feishu.provider import FeishuConfig
from summit_everything.integrations.llm import FakeLLM, GroundedAnswer
from summit_everything.integrations.rerank import FakeReranker
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore


class DelayedFakeEmbedding(FakeEmbedding):
    def embed(self, text: str, *, fingerprint: str) -> list[float]:
        if text.startswith("QA-CANCEL-PROBE:"):
            time.sleep(8)
        return super().embed(text, fingerprint=fingerprint)


class FakeGroundedAnswer(FakeLLM):
    def answer(self, question: str, passages: list[dict[str, str]]) -> GroundedAnswer:
        return GroundedAnswer(
            text="合成回答：" + (passages[0]["excerpt"] if passages else question),
            inferences=[],
            missing_information=[],
        )


profile_root = Path(os.environ["SUMMIT_PROFILE_ROOT"])
query_service = QueryService(
    IndexStore(profile_root / "index.sqlite3"),
    embedding=DelayedFakeEmbedding(),
    reranker=FakeReranker(),
    answer_provider=FakeGroundedAnswer(),
)
app = create_app(
    session_token=os.environ["SUMMIT_SESSION_TOKEN"],
    profile_root=profile_root,
    query_service=query_service,
    feishu_config=FeishuConfig(
        allowed_origins=(
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8793",
            "http://127.0.0.1:5275",
        )
    ),
)
