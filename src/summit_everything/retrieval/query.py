"""Plan and build a local index, then recheck every retrieved page before citation."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from summit_everything.domain.content import (
    RetrievalPurpose,
    StorageArea,
    retrieval_eligibility,
)
from summit_everything.domain.models import Answer, Citation, IndexPlan, IndexResult, PageSnapshot
from summit_everything.integrations.embedding import FakeEmbedding, cosine_similarity
from summit_everything.integrations.llm import GroundedAnswer
from summit_everything.integrations.rerank import FakeReranker
from summit_everything.retrieval.chunking import TextChunk, chunk_markdown
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import WorkspaceError, load_manifest
from summit_everything.workspace.reader import list_pages, read_page


class IndexPlanStale(ValueError):
    """Workspace content changed after the user reviewed an index plan."""


class EmbeddingProvider(Protocol):
    def embed(self, text: str, *, fingerprint: str) -> list[float]: ...

    def embed_many(self, texts: list[str], *, fingerprint: str) -> list[list[float]]: ...


class RerankerProvider(Protocol):
    def rank(self, query: str, texts: list[str]) -> list[tuple[int, float]]: ...


class AnswerProvider(Protocol):
    def answer(self, question: str, passages: list[dict[str, str]]) -> GroundedAnswer: ...


class QueryService:
    def __init__(
        self,
        store: IndexStore,
        embedding: EmbeddingProvider | None = None,
        reranker: RerankerProvider | None = None,
        answer_provider: AnswerProvider | None = None,
    ) -> None:
        self.store = store
        self.embedding = embedding or FakeEmbedding()
        self.reranker = reranker or FakeReranker()
        self.answer_provider = answer_provider

    def status(self, root: Path) -> dict[str, int | str | None]:
        manifest = load_manifest(root)
        status = self.store.status(manifest.workspace_id)
        fingerprint = status["fingerprint"]
        if fingerprint is None:
            return {**status, "state": "not_ready", "current_pages": 0, "stale_pages": 0}
        current = {
            str(page.page_id): page.content_sha256
            for page in self._eligible_pages(list_pages(root), purpose=RetrievalPurpose.HISTORY)
        }
        indexed = {
            str(chunk["page_id"]): str(chunk["content_sha256"])
            for chunk in self.store.get_chunks(manifest.workspace_id, str(fingerprint))
        }
        stale = sum(
            current.get(page_id) != indexed.get(page_id)
            for page_id in current.keys() | indexed.keys()
        )
        return {
            **status,
            "state": "ready" if stale == 0 else "stale",
            "current_pages": len(current),
            "stale_pages": stale,
        }

    def plan(self, root: Path, *, fingerprint: str, mode: str) -> IndexPlan:
        if not fingerprint.strip():
            raise WorkspaceError("Model fingerprint is required")
        if mode not in {"initial", "incremental", "full", "model_change"}:
            raise WorkspaceError("Index mode is not supported")
        manifest = load_manifest(root)
        current = self.store.active_fingerprint(manifest.workspace_id)
        if mode == "initial" and current is not None:
            raise WorkspaceError("An index already exists; choose incremental or full")
        if mode == "incremental" and current != fingerprint:
            raise WorkspaceError("Incremental indexing requires the active model fingerprint")
        if mode == "model_change" and current in {None, fingerprint}:
            raise WorkspaceError("Model change requires a different active fingerprint")
        eligible = self._eligible_pages(list_pages(root), purpose=RetrievalPurpose.HISTORY)
        return IndexPlan(
            plan_id=uuid4(),
            workspace_id=manifest.workspace_id,
            mode=mode,  # type: ignore[arg-type]
            fingerprint=fingerprint,
            page_ids=[page.page_id for page in eligible],
            page_versions={str(page.page_id): page.content_sha256 for page in eligible},
            estimated_tokens=sum(max(1, len(page.body) // 4) for page in eligible),
            estimated_cost=0 if fingerprint == "summit-fake-embedding-v1" else None,
        )

    def execute_plan(self, root: Path, plan: IndexPlan) -> IndexResult:
        root = root.resolve()
        manifest = load_manifest(root)
        if plan.workspace_id != manifest.workspace_id:
            raise WorkspaceError("Index plan belongs to a different workspace")
        active_fingerprint = self.store.active_fingerprint(manifest.workspace_id)
        if plan.mode == "initial" and active_fingerprint is not None:
            raise WorkspaceError("An index already exists; choose incremental or full")
        if plan.mode == "incremental" and active_fingerprint != plan.fingerprint:
            raise WorkspaceError("Incremental indexing requires the active model fingerprint")
        if plan.mode == "model_change" and active_fingerprint in {
            None,
            plan.fingerprint,
        }:
            raise WorkspaceError("Model change requires a different active fingerprint")
        current_pages = {
            page.page_id: page
            for page in self._eligible_pages(list_pages(root), purpose=RetrievalPurpose.HISTORY)
        }
        if any(
            page_id not in current_pages
            or current_pages[page_id].content_sha256 != expected_version
            for page_id, expected_version in (
                (UUID(page_id), version) for page_id, version in plan.page_versions.items()
            )
        ) or set(current_pages) != set(plan.page_ids):
            raise IndexPlanStale("Workspace pages changed after the index plan was reviewed")
        existing = self.store.existing_chunks(manifest.workspace_id, plan.fingerprint)
        prepared: list[tuple[TextChunk, list[float] | None]] = []
        for page in current_pages.values():
            for chunk in chunk_markdown(page.page_id, page.content_sha256, page.body):
                prepared.append((chunk, existing.get(chunk.chunk_id)))
        missing = [chunk for chunk, vector in prepared if vector is None]
        newly_embedded: list[list[float]] = []
        batch_size = getattr(self.embedding, "max_batch_size", 20)
        for offset in range(0, len(missing), batch_size):
            batch = missing[offset : offset + batch_size]
            newly_embedded.extend(
                self.embedding.embed_many(
                    [chunk.text for chunk in batch], fingerprint=plan.fingerprint
                )
            )
        if len(newly_embedded) != len(missing):
            raise ValueError("Embedding provider returned an incomplete batch")
        missing_vectors = iter(newly_embedded)
        embedded = [
            (chunk, vector if vector is not None else next(missing_vectors))
            for chunk, vector in prepared
        ]
        embedded_count = len(missing)
        self.store.replace_generation(manifest.workspace_id, plan.fingerprint, embedded)
        return IndexResult(
            indexed_pages=len(current_pages),
            indexed_chunks=len(embedded),
            embedded_chunks=embedded_count,
            reused_chunks=len(embedded) - embedded_count,
            active_fingerprint=plan.fingerprint,
        )

    def rebuild(self, root: Path, *, fingerprint: str) -> IndexResult:
        manifest = load_manifest(root)
        current = self.store.active_fingerprint(manifest.workspace_id)
        mode = "initial" if current is None else "incremental"
        return self.execute_plan(root, self.plan(root, fingerprint=fingerprint, mode=mode))

    def query(
        self,
        root: Path,
        question: str,
        *,
        fingerprint: str,
        purpose: RetrievalPurpose = RetrievalPurpose.CURRENT,
        limit: int = 5,
    ) -> Answer:
        root = root.resolve()
        manifest = load_manifest(root)
        if self.store.active_fingerprint(manifest.workspace_id) != fingerprint:
            return Answer(
                answer_id=uuid4(),
                question=question,
                text="本地索引尚未就绪。",
                purpose=purpose.value,
                index_status="not_ready",
                missing_information=["请先完成当前模型版本的索引。"],
            )
        chunks = self.store.get_chunks(manifest.workspace_id, fingerprint)
        if not chunks:
            return Answer(
                answer_id=uuid4(),
                question=question,
                text="没有找到经确认且仍为当前版本的相关资料。",
                purpose=purpose.value,
                index_status="empty",
                missing_information=["当前索引中没有可引用的知识页。"],
            )
        query_vector = self.embedding.embed(question, fingerprint=fingerprint)
        dense = sorted(
            chunks,
            key=lambda item: cosine_similarity(query_vector, item["vector"]),
            reverse=True,
        )
        reranked = self.reranker.rank(question, [str(item["text"]) for item in chunks])
        if len(reranked) != len(chunks):
            raise ValueError("Reranker returned an incomplete ranking")
        lexical_scores: dict[str, float] = {}
        lexical = []
        for index, score in reranked:
            if index < 0 or index >= len(chunks) or chunks[index]["chunk_id"] in lexical_scores:
                raise ValueError("Reranker returned an invalid candidate index")
            item = chunks[index]
            lexical.append(item)
            lexical_scores[str(item["chunk_id"])] = score
        ranks: dict[str, float] = {}
        for rank, item in enumerate(dense, start=1):
            ranks[item["chunk_id"]] = ranks.get(item["chunk_id"], 0) + 1 / (60 + rank)
        for rank, item in enumerate(lexical, start=1):
            ranks[item["chunk_id"]] = ranks.get(item["chunk_id"], 0) + 1 / (60 + rank)
        ranked = sorted(chunks, key=lambda item: ranks[item["chunk_id"]], reverse=True)
        relevant = [item for item in ranked if lexical_scores.get(str(item["chunk_id"]), 0) > 0]
        related_ids = self._related_page_ids(root, relevant[: min(limit, 3)])
        ranked = relevant
        if related_ids:
            seen = {item["chunk_id"] for item in ranked}
            ranked.extend(
                item
                for item in chunks
                if item["page_id"] in related_ids and item["chunk_id"] not in seen
            )
        citations: list[Citation] = []
        for item in ranked:
            if len(citations) >= limit:
                break
            try:
                page = read_page(root, item["page_id"])
            except (WorkspaceError, OSError):
                continue
            try:
                area = StorageArea(page.storage_area)
            except ValueError:
                continue
            eligibility = retrieval_eligibility(
                page.metadata,
                page.body,
                area=area,
                purpose=purpose,
                expected_content_sha256=item["content_sha256"],
            )
            if not eligibility.eligible:
                continue
            validity = page.metadata.get("validity", "current")
            if validity not in {"current", "superseded", "invalid"}:
                continue
            citations.append(
                Citation(
                    page_id=page.page_id,
                    content_sha256=item["content_sha256"],
                    chunk_id=item["chunk_id"],
                    heading=item["heading"],
                    excerpt=item["text"][:600],
                    validity=validity,
                )
            )
        if not citations:
            return Answer(
                answer_id=uuid4(),
                question=question,
                text="没有找到经确认且仍为当前版本的相关资料。",
                purpose=purpose.value,
                index_status="ready",
                missing_information=["已缓存的资料版本与当前工作库不一致，或当前资格检查未通过。"],
            )
        passages = [
            {"heading": citation.heading or "页面内容", "excerpt": citation.excerpt}
            for citation in citations
        ]
        answer = self.answer_provider.answer(question, passages) if self.answer_provider else None
        return Answer(
            answer_id=uuid4(),
            question=question,
            text=(
                answer.text
                if answer is not None
                else "根据以下已确认资料：\n\n"
                + "\n\n".join(
                    f"【{passage['heading']}】\n{passage['excerpt']}" for passage in passages
                )
            ),
            citations=citations,
            inferences=answer.inferences if answer is not None else [],
            missing_information=answer.missing_information if answer is not None else [],
            purpose=purpose.value,
            index_status="ready",
        )

    def _eligible_pages(
        self,
        pages: list[PageSnapshot],
        *,
        purpose: RetrievalPurpose = RetrievalPurpose.CURRENT,
    ) -> list[PageSnapshot]:
        qualified: list[PageSnapshot] = []
        for page in pages:
            try:
                area = StorageArea(page.storage_area)
            except ValueError:
                continue
            eligibility = retrieval_eligibility(
                page.metadata, page.body, area=area, purpose=purpose
            )
            if eligibility.eligible:
                qualified.append(page)
        return qualified

    def _related_page_ids(self, root: Path, chunks: list[dict[str, object]]) -> set[UUID]:
        related: set[UUID] = set()
        visited: set[UUID] = set()
        for chunk in chunks:
            page_id = chunk["page_id"]
            if not isinstance(page_id, UUID) or page_id in visited:
                continue
            visited.add(page_id)
            try:
                page = read_page(root, page_id)
            except (WorkspaceError, OSError):
                continue
            values = page.metadata.get("related_page_ids", [])
            if isinstance(values, list):
                for value in values:
                    try:
                        related.add(UUID(str(value)))
                    except ValueError:
                        continue
        return related - visited
