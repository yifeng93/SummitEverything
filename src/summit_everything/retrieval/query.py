"""Plan and build a local index, then recheck every retrieved page before citation."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from threading import Event
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4

from summit_everything.domain.content import (
    Eligibility,
    RetrievalPurpose,
    StorageArea,
    retrieval_eligibility,
)
from summit_everything.domain.models import (
    Answer,
    Citation,
    IndexPlan,
    IndexResult,
    PageSnapshot,
    WorkspaceManifest,
)
from summit_everything.integrations.embedding import FakeEmbedding, cosine_similarity
from summit_everything.integrations.llm import GroundedAnswer
from summit_everything.integrations.rerank import FakeReranker
from summit_everything.local.answer_context import AnswerContext
from summit_everything.retrieval.chunking import TextChunk, chunk_markdown
from summit_everything.retrieval.planner import (
    aliases_from_subject_text,
    matches_explicit_subject,
    plan_retrieval,
    supported_dimensions,
)
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import WorkspaceError, load_manifest
from summit_everything.workspace.reader import list_pages, read_page


class IndexPlanStale(ValueError):
    """Workspace content changed after the user reviewed an index plan."""


class QueryCancelled(Exception):
    """The client cancelled a query before its next provider operation."""


class EmbeddingProvider(Protocol):
    def embed(self, text: str, *, fingerprint: str) -> list[float]: ...

    def embed_many(self, texts: list[str], *, fingerprint: str) -> list[list[float]]: ...


class RerankerProvider(Protocol):
    def rank(self, query: str, texts: list[str]) -> list[tuple[int, float]]: ...


class AnswerProvider(Protocol):
    def answer(
        self, question: str, passages: list[dict[str, str]], context: AnswerContext
    ) -> GroundedAnswer: ...


def _scope_segments(text: str, subjects: tuple[str, ...], dimensions: tuple[str, ...]) -> list[str]:
    """Split evidence where a new explicit object begins a different topic."""
    initial = [
        segment.strip() for segment in re.split(r"(?<=[。！？；;，,\n])", text) if segment.strip()
    ]
    if len(subjects) < 2 or not dimensions:
        return initial

    result: list[str] = []
    pending = list(initial)
    while pending:
        segment = pending.pop(0)
        occurrences = sorted(
            (position, subject) for subject in subjects if (position := segment.find(subject)) >= 0
        )
        split_at: int | None = None
        for position, _subject in occurrences[1:]:
            prefix = segment[:position]
            suffix = segment[position:]
            prefix_topics = set(supported_dimensions(prefix, dimensions))
            suffix_topics = set(supported_dimensions(suffix, dimensions))
            if prefix_topics and suffix_topics and prefix_topics != suffix_topics:
                split_at = position
                break
        if split_at is None:
            result.append(segment)
        else:
            prefix, suffix = segment[:split_at].strip(), segment[split_at:].strip()
            if prefix:
                result.append(prefix)
            if suffix:
                pending.insert(0, suffix)
    return result


class QueryService:
    def __init__(
        self,
        store: IndexStore,
        embedding: EmbeddingProvider | None = None,
        reranker: RerankerProvider | None = None,
        answer_provider: AnswerProvider | None = None,
        provider_guard: Callable[[], None] | None = None,
    ) -> None:
        self.store = store
        self.embedding = embedding or FakeEmbedding()
        self.reranker = reranker or FakeReranker()
        self.answer_provider = answer_provider
        self.provider_guard = provider_guard
        self._closed = False

    def close(self) -> None:
        """Release operation-scoped provider clients exactly once.

        Only providers that own their transport expose ``close``; injected test
        doubles and shared fakes are ignored.
        """
        if self._closed:
            return
        self._closed = True
        for provider in (self.embedding, self.reranker, self.answer_provider):
            close = getattr(provider, "close", None)
            if callable(close):
                close()

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
            if self.provider_guard is not None:
                self.provider_guard()
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
        cancelled: Event | None = None,
        answer_mode: Literal["fact", "comparison", "plan"] = "fact",
        context: AnswerContext | None = None,
    ) -> Answer:
        context = context or AnswerContext(answer_mode=answer_mode)
        self._check_cancelled(cancelled)
        root = root.resolve()
        manifest = load_manifest(root)
        if self.store.active_fingerprint(manifest.workspace_id) != fingerprint:
            return Answer(
                answer_id=uuid4(),
                question=question,
                text="本地索引尚未就绪。",
                purpose=purpose.value,
                answer_mode=answer_mode,
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
                answer_mode=answer_mode,
                index_status="empty",
                missing_information=["当前索引中没有可引用的知识页。"],
            )
        object_aliases: list[str] = []
        subject_aliases = self._subject_aliases(root, manifest, object_aliases=object_aliases)
        retrieval_plan = plan_retrieval(
            question,
            context.previous_user_questions,
            subject_aliases,
            object_aliases=object_aliases,
        )
        if retrieval_plan.unresolved_topic:
            return self._empty_answer(
                question,
                purpose,
                "没有足够线索确定本次查询对象；请补充对象或完整问题。",
                answer_mode=answer_mode,
            )
        if self.provider_guard is not None:
            self.provider_guard()
        query_vector = self.embedding.embed(retrieval_plan.search_question, fingerprint=fingerprint)
        self._check_cancelled(cancelled)
        dense = sorted(
            chunks,
            key=lambda item: cosine_similarity(query_vector, item["vector"]),
            reverse=True,
        )
        qualified, qualification_rejections = self._qualified_chunks(root, dense, purpose=purpose)
        subject_pages: dict[UUID, PageSnapshot | None] = {}
        scope_pairs_by_chunk: dict[str, set[tuple[str, str]]] = {}
        scope_excerpt_by_chunk: dict[str, str] = {}
        requested_exact_topics = {
            part.removeprefix("term:")
            for dimension in retrieval_plan.dimensions
            for part in dimension.split("&")
            if part.startswith("term:")
        }
        all_subject_aliases = tuple(
            alias
            for alias in subject_aliases
            if alias.casefold() not in {topic.casefold() for topic in requested_exact_topics}
        )

        def in_scope(item: dict[str, Any]) -> bool:
            page_id = item["page_id"]
            if page_id not in subject_pages:
                page, eligibility = self._read_page_eligibility(
                    root,
                    page_id,
                    purpose=purpose,
                    expected_content_sha256=str(item["content_sha256"]),
                )
                subject_pages[page_id] = page
                if page is None:
                    qualification_rejections[page_id] = eligibility.reason
            page = subject_pages[page_id]
            if page is None:
                return False
            subject_names = self._page_subject_names(page, manifest)
            text = str(item["text"])
            segments = _scope_segments(
                text, retrieval_plan.explicit_subjects, retrieval_plan.dimensions
            )
            if not retrieval_plan.explicit_subjects and not retrieval_plan.dimensions:
                # Unscoped exploratory questions retain the existing ranked path.
                scope_pairs_by_chunk[str(item["chunk_id"])] = set()
                scope_excerpt_by_chunk[str(item["chunk_id"])] = text
                return True

            pairs: set[tuple[str, str]] = set()
            supported_segments: list[str] = []
            for segment in segments:
                if not segment:
                    continue
                matching_dimensions = supported_dimensions(segment, retrieval_plan.dimensions)
                if retrieval_plan.dimensions and not matching_dimensions:
                    continue
                mentioned_query_subjects = tuple(
                    subject
                    for subject in retrieval_plan.explicit_subjects
                    if matches_explicit_subject(segment, (subject,))
                )
                mentions_any_subject = any(
                    matches_explicit_subject(segment, (alias,)) for alias in all_subject_aliases
                )
                if retrieval_plan.explicit_subjects:
                    if mentioned_query_subjects:
                        segment_subjects = mentioned_query_subjects
                    elif mentions_any_subject:
                        # A sentence naming a different object cannot inherit the
                        # page owner's project association.
                        continue
                    else:
                        segment_subjects = tuple(
                            subject
                            for subject in retrieval_plan.explicit_subjects
                            if matches_explicit_subject(subject_names, (subject,))
                        )
                    if not segment_subjects:
                        continue
                    segment_dimensions = matching_dimensions or ("",)
                    segment_pairs = {
                        (subject, dimension)
                        for subject in segment_subjects
                        for dimension in segment_dimensions
                    }
                    segment_pairs &= set(retrieval_plan.required_pairs)
                else:
                    segment_pairs = {("", dimension) for dimension in matching_dimensions}
                    segment_pairs &= set(retrieval_plan.required_pairs)
                if segment_pairs or (
                    not retrieval_plan.required_pairs and not retrieval_plan.dimensions
                ):
                    pairs.update(segment_pairs)
                    supported_segments.append(segment)
            if not supported_segments:
                return False
            chunk_id = str(item["chunk_id"])
            scope_pairs_by_chunk[chunk_id] = pairs
            scope_excerpt_by_chunk[chunk_id] = " ".join(supported_segments)
            return True

        scope_candidates = [item for item in qualified if in_scope(item)]
        if not scope_candidates:
            matching_rejections = self._scope_rejection_reasons(
                root,
                manifest,
                qualification_rejections,
                retrieval_plan.explicit_subjects,
                retrieval_plan.dimensions,
            )
            if matching_rejections:
                message = self._no_evidence_message(
                    matching_rejections, purpose, answer_mode=answer_mode
                )
                return self._empty_answer(question, purpose, message, answer_mode=answer_mode)
            if (
                not retrieval_plan.explicit_subjects
                and retrieval_plan.scope_kind == "explicit_topic"
            ):
                scope_missing = self._scope_missing_pairs(set(retrieval_plan.required_pairs))
                message = "当前已确认资料中没有找到该主题的依据；" + "；".join(scope_missing)
                return self._empty_answer(
                    question,
                    purpose,
                    message,
                    answer_mode=answer_mode,
                    missing=scope_missing,
                )
            if not retrieval_plan.explicit_subjects:
                message = self._no_evidence_message({}, purpose, answer_mode=answer_mode)
                return self._empty_answer(question, purpose, message, answer_mode=answer_mode)
            scope_missing = self._scope_missing_pairs(set(retrieval_plan.required_pairs))
            if scope_missing:
                message = "没有找到能确认该对象和主题的已确认资料；" + "；".join(scope_missing)
                return self._empty_answer(
                    question,
                    purpose,
                    message,
                    answer_mode=answer_mode,
                    missing=scope_missing,
                )
            matching_rejections = qualification_rejections
            return self._empty_answer(
                question,
                purpose,
                self._no_evidence_message(matching_rejections, purpose, answer_mode=answer_mode),
                answer_mode=answer_mode,
            )
        candidates = scope_candidates[:20]
        if not candidates:
            return self._empty_answer(
                question,
                purpose,
                self._no_evidence_message(
                    qualification_rejections, purpose, answer_mode=answer_mode
                ),
                answer_mode=answer_mode,
            )
        self._check_cancelled(cancelled)
        if self.provider_guard is not None:
            self.provider_guard()
        reranked = self.reranker.rank(
            retrieval_plan.search_question, [str(item["text"]) for item in candidates]
        )
        self._check_cancelled(cancelled)
        if len(reranked) != len(candidates):
            raise ValueError("Reranker returned an incomplete ranking")
        lexical_scores: dict[str, float] = {}
        lexical = []
        for index, score in reranked:
            if (
                index < 0
                or index >= len(candidates)
                or candidates[index]["chunk_id"] in lexical_scores
            ):
                raise ValueError("Reranker returned an invalid candidate index")
            item = candidates[index]
            lexical.append(item)
            lexical_scores[str(item["chunk_id"])] = score
        ranks: dict[str, float] = {}
        for rank, item in enumerate(dense, start=1):
            ranks[item["chunk_id"]] = ranks.get(item["chunk_id"], 0) + 1 / (60 + rank)
        for rank, item in enumerate(lexical, start=1):
            ranks[item["chunk_id"]] = ranks.get(item["chunk_id"], 0) + 1 / (60 + rank)
        ranked = sorted(candidates, key=lambda item: ranks[item["chunk_id"]], reverse=True)
        relevant = (
            ranked
            if retrieval_plan.explicit_subjects or retrieval_plan.dimensions
            else [item for item in ranked if lexical_scores.get(str(item["chunk_id"]), 0) > 0]
        )
        related_ids = self._related_page_ids(root, relevant[: min(limit, 3)])
        ranked = relevant
        if related_ids:
            seen = {item["chunk_id"] for item in ranked}
            ranked.extend(
                item
                for item in qualified
                if item["page_id"] in related_ids
                and item["chunk_id"] not in seen
                and in_scope(item)
            )
        citations: list[Citation] = []
        citation_rejections: dict[UUID, str] = {}
        truncated_by_limit = False
        for item in ranked:
            page, eligibility = self._read_page_eligibility(
                root,
                item["page_id"],
                purpose=purpose,
                expected_content_sha256=str(item["content_sha256"]),
            )
            if page is None:
                citation_rejections[item["page_id"]] = eligibility.reason
                continue
            validity = page.metadata.get("validity", "current")
            if validity not in {"current", "superseded", "invalid"}:
                continue
            if len(citations) >= limit:
                # Check omitted candidates against the same current qualification
                # gate before reporting a citation cap. A stale or invalid tail
                # item is not evidence that an uncovered pair could have been cited.
                truncated_by_limit = True
                continue
            citations.append(
                Citation(
                    page_id=page.page_id,
                    content_sha256=item["content_sha256"],
                    chunk_id=item["chunk_id"],
                    heading=item["heading"],
                    excerpt=scope_excerpt_by_chunk.get(str(item["chunk_id"]), str(item["text"])),
                    validity=validity,
                )
            )
        if not citations:
            # A zero lexical score means no relevant passage was found. Only
            # describe a cache/qualification problem when the selected passages
            # actually failed the corresponding version or trust gate.
            rejected = citation_rejections if ranked else {}
            message = self._no_evidence_message(rejected, purpose, answer_mode=answer_mode)
            return Answer(
                answer_id=uuid4(),
                question=question,
                text=message,
                purpose=purpose.value,
                answer_mode=answer_mode,
                index_status="ready",
                missing_information=[message],
            )
        passages = [
            {
                "source_id": str(citation.page_id),
                "heading": citation.heading or "页面内容",
                "excerpt": citation.excerpt,
            }
            for citation in citations
        ]
        context_bytes = len(
            json.dumps(
                {"question": question, "passages": passages, "context": context.model_dump()},
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")
        )
        if context_bytes > 90_000:
            raise ValueError("问答上下文超过本机 90 KB 预算；请缩短问题或编辑角色、记忆后重试。")
        self._check_cancelled(cancelled)
        if self.answer_provider is not None and self.provider_guard is not None:
            self.provider_guard()
        answer = (
            self.answer_provider.answer(question, passages, context)
            if self.answer_provider
            else None
        )
        self._check_cancelled(cancelled)
        changed = self._citation_change_reason(root, citations, purpose=purpose)
        if changed is not None:
            message = {
                "stale_snapshot": (
                    "生成期间引用资料版本发生变化，回答已作废；请更新索引或确认当前版本后重新查询。"
                ),
                "approval_mismatch": (
                    "生成期间引用资料的确认状态发生变化，回答已作废；请核验并重新查询。"
                ),
                "historical_only": (
                    "生成期间引用资料已不属于当前查询范围，回答已作废；请重新查询当前可用资料。"
                ),
                "unavailable": "生成期间引用资料已不可用，回答已作废；请重新查询。",
            }.get(
                changed,
                "生成期间引用资料不再符合本次查询资格，回答已作废；请重新查询当前可用资料。",
            )
            return self._empty_answer(
                question,
                purpose,
                message,
                answer_mode=answer_mode,
            )
        source_statements = [f"{passage['heading']}：{passage['excerpt']}" for passage in passages]
        source_count = len({passage["source_id"] for passage in passages})
        required_pairs = set(retrieval_plan.required_pairs)
        covered_pairs = {
            pair
            for citation in citations
            for pair in scope_pairs_by_chunk.get(citation.chunk_id, set())
        }
        missing_pairs = required_pairs - covered_pairs
        eligible_page_cache: dict[UUID, PageSnapshot | None] = {}
        eligible_scope_pairs: set[tuple[str, str]] = set()
        eligible_candidate_pairs: set[tuple[str, str]] = set()
        for item in scope_candidates:
            page_id = item["page_id"]
            if page_id not in eligible_page_cache:
                current_page, _ = self._read_page_eligibility(
                    root,
                    page_id,
                    purpose=purpose,
                    expected_content_sha256=str(item["content_sha256"]),
                )
                eligible_page_cache[page_id] = current_page
            current_page = eligible_page_cache[page_id]
            if current_page is None or current_page.metadata.get("validity", "current") not in {
                "current",
                "superseded",
                "invalid",
            }:
                continue
            pairs = scope_pairs_by_chunk.get(str(item["chunk_id"]), set())
            eligible_scope_pairs.update(pairs)
            if item in candidates:
                eligible_candidate_pairs.update(pairs)

        # A pair is “truncated” only when at least one still-qualified passage
        # actually supports it outside the cited set. A dense top-20 omission is
        # tracked separately from the public citation limit.
        citation_truncated_pairs = (eligible_candidate_pairs - covered_pairs) & missing_pairs
        candidate_truncated_pairs = (
            eligible_scope_pairs - eligible_candidate_pairs
        ) & missing_pairs
        candidate_truncated_pairs -= citation_truncated_pairs
        absent_pairs = missing_pairs - citation_truncated_pairs - candidate_truncated_pairs
        scope_missing = self._scope_missing_pairs(absent_pairs)
        if citation_truncated_pairs:
            scope_missing.append(self._truncated_scope_notice(citation_truncated_pairs))
        if candidate_truncated_pairs:
            scope_missing.append(self._candidate_limit_notice(candidate_truncated_pairs))
        if truncated_by_limit and not citation_truncated_pairs:
            # The cap may exclude redundant material for a pair that is already
            # covered. Report that observed limit neutrally, without suggesting it
            # could explain a different pair that has no qualified support.
            scope_missing.append(
                "本次引用条数已达上限，另有同范围材料未列入引用；这不表示未覆盖主题已有依据。"
            )
        comparison_missing = (
            ["可用材料不足两组，无法进行跨材料比较。"]
            if answer_mode == "comparison"
            and source_count < 2
            and not retrieval_plan.explicit_subjects
            else []
        )
        comparison_inference = (
            ["这里仅比较当前列出的已确认材料，不推断未提供的维度。"]
            if answer_mode == "comparison" and source_count >= 2 and not scope_missing
            else []
        )
        missing_information = list(
            dict.fromkeys(
                [
                    *scope_missing,
                    *comparison_missing,
                    *(answer.missing_information if answer is not None else []),
                ]
            )
        )
        partial_text = (
            "当前资料只覆盖了部分所问范围：\n\n"
            + "\n\n".join(source_statements)
            + "\n\n范围未覆盖说明："
            + "；".join(scope_missing)
            if scope_missing
            else None
        )
        return Answer(
            answer_id=uuid4(),
            question=question,
            text=(
                partial_text
                if partial_text is not None
                else answer.text
                if answer is not None
                else "根据以下已确认资料：\n\n"
                + "\n\n".join(
                    f"【{passage['heading']}】\n{passage['excerpt']}" for passage in passages
                )
            ),
            citations=citations,
            answer_mode=answer_mode,
            source_statements=source_statements,
            inferences=(
                []
                if partial_text is not None
                else answer.inferences
                if answer is not None
                else comparison_inference
            ),
            advice=(
                []
                if partial_text is not None
                else answer.advice
                if answer is not None
                else (
                    ["先核对以上依据，再补齐缺失条件后决定下一步。"]
                    if answer_mode == "plan"
                    else []
                )
            ),
            missing_information=missing_information,
            purpose=purpose.value,
            index_status="ready",
        )

    @staticmethod
    def _eligible_pages(
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

    def _subject_aliases(
        self,
        root: Path,
        manifest: WorkspaceManifest,
        *,
        object_aliases: list[str] | None = None,
    ) -> tuple[str, ...]:
        """Read temporary subject hints from workspace names and eligible pages."""
        aliases: list[str] = []
        object_names = object_aliases if object_aliases is not None else []
        for record in manifest.lines:
            aliases.append(record.name)
            object_names.append(record.name)
        for project in manifest.projects:
            aliases.append(project.name)
            object_names.append(project.name)
        for page in self._eligible_pages(list_pages(root), purpose=RetrievalPurpose.HISTORY):
            title = page.metadata.get("title")
            if isinstance(title, str):
                aliases.append(title)
            page_aliases = page.metadata.get("aliases", [])
            if isinstance(page_aliases, str):
                aliases.append(page_aliases)
                object_names.append(page_aliases)
            elif isinstance(page_aliases, list):
                string_aliases = [value for value in page_aliases if isinstance(value, str)]
                aliases.extend(string_aliases)
                object_names.extend(string_aliases)
            body_aliases = aliases_from_subject_text(page.body)
            aliases.extend(body_aliases)
            object_names.extend(body_aliases)
        return tuple(aliases)

    @staticmethod
    def _page_subject_names(page: PageSnapshot, manifest: WorkspaceManifest) -> str:
        """Return current page and manifest names used only for candidate matching."""
        names: list[str] = []
        title = page.metadata.get("title")
        if isinstance(title, str):
            names.append(title)
        aliases = page.metadata.get("aliases", [])
        if isinstance(aliases, str):
            names.append(aliases)
        elif isinstance(aliases, list):
            names.extend(value for value in aliases if isinstance(value, str))

        line_id = page.metadata.get("line_id")
        project_id = page.metadata.get("project_id")
        project = next(
            (item for item in manifest.projects if str(item.id) == str(project_id)), None
        )
        line = next((item for item in manifest.lines if str(item.id) == str(line_id)), None)
        if project is not None:
            names.append(project.name)
        if line is not None:
            names.append(line.name)
        return " ".join(names)

    def _qualified_chunks(
        self,
        root: Path,
        chunks: list[dict[str, Any]],
        *,
        purpose: RetrievalPurpose,
    ) -> tuple[list[dict[str, Any]], dict[UUID, str]]:
        page_eligibility: dict[UUID, bool] = {}
        rejections: dict[UUID, str] = {}
        qualified: list[dict[str, Any]] = []
        for chunk in chunks:
            page_id = chunk["page_id"]
            if not isinstance(page_id, UUID):
                continue
            if page_id not in page_eligibility:
                page, eligibility = self._read_page_eligibility(
                    root,
                    page_id,
                    purpose=purpose,
                    expected_content_sha256=str(chunk["content_sha256"]),
                )
                page_eligibility[page_id] = page is not None
                if page is None:
                    rejections[page_id] = eligibility.reason
            if page_eligibility[page_id]:
                qualified.append(chunk)
        return qualified, rejections

    def _scope_rejection_reasons(
        self,
        root: Path,
        manifest: WorkspaceManifest,
        rejections: dict[UUID, str],
        subjects: tuple[str, ...],
        dimensions: tuple[str, ...],
    ) -> dict[UUID, str]:
        """Keep version/trust diagnostics only for pages inside this query's scope."""
        matching: dict[UUID, str] = {}
        for page_id, reason in rejections.items():
            try:
                page = read_page(root, page_id)
            except (WorkspaceError, OSError):
                # An unavailable page has no readable content to establish scope.
                if reason == "unavailable":
                    continue
                continue
            names = self._page_subject_names(page, manifest)
            body = page.body
            object_match = not subjects or any(
                matches_explicit_subject(names, (subject,))
                or matches_explicit_subject(body, (subject,))
                for subject in subjects
            )
            dimension_match = not dimensions or bool(supported_dimensions(body, dimensions))
            if object_match and dimension_match:
                matching[page_id] = reason
        return matching

    @staticmethod
    def _no_evidence_message(
        rejections: dict[UUID, str],
        purpose: RetrievalPurpose,
        *,
        answer_mode: Literal["fact", "comparison", "plan"],
    ) -> str:
        reasons = set(rejections.values())
        if "stale_snapshot" in reasons:
            return "索引中的页面版本与当前已确认内容不一致；请更新索引后重新查询。"
        if "approval_mismatch" in reasons:
            return "页面正文与确认记录不一致，未作为依据；请核验并确认正式内容后查询。"
        if "unavailable" in reasons:
            return "部分检索页面当前无法读取，未作为依据；请检查页面后重新查询。"
        if reasons and reasons <= {"historical_only"} and purpose == RetrievalPurpose.CURRENT:
            return "当前范围没有可引用的已确认资料；历史版本仅在历史范围中可查。"
        if rejections:
            return "索引中的材料未通过本次查询的批准或资格核验，未作为依据。"
        return {
            "fact": "当前已确认资料中没有找到与问题相关的依据。",
            "comparison": "当前已确认资料中没有找到足以进行比较的相关材料。",
            "plan": "当前已确认资料中没有找到可支撑方案的相关依据。",
        }[answer_mode]

    @staticmethod
    def _read_page_eligibility(
        root: Path,
        page_id: UUID,
        *,
        purpose: RetrievalPurpose,
        expected_content_sha256: str | None = None,
    ) -> tuple[PageSnapshot | None, Eligibility]:
        try:
            page = read_page(root, page_id)
            area = StorageArea(page.storage_area)
        except (WorkspaceError, OSError, ValueError):
            return None, Eligibility(False, "unavailable")
        eligibility = retrieval_eligibility(
            page.metadata,
            page.body,
            area=area,
            purpose=purpose,
            expected_content_sha256=expected_content_sha256,
        )
        return (page if eligibility.eligible else None), eligibility

    def _citation_change_reason(
        self,
        root: Path,
        citations: list[Citation],
        *,
        purpose: RetrievalPurpose,
    ) -> str | None:
        for citation in citations:
            page, eligibility = self._read_page_eligibility(
                root,
                citation.page_id,
                purpose=purpose,
                expected_content_sha256=citation.content_sha256,
            )
            if page is not None:
                continue
            if eligibility.reason == "unavailable":
                return "unavailable"
            if eligibility.content_sha256 != citation.content_sha256:
                return "stale_snapshot"
            if eligibility.reason == "approval_mismatch":
                return eligibility.reason
            return eligibility.reason
        return None

    @staticmethod
    def _check_cancelled(cancelled: Event | None) -> None:
        if cancelled is not None and cancelled.is_set():
            raise QueryCancelled()

    @staticmethod
    def _empty_answer(
        question: str,
        purpose: RetrievalPurpose,
        message: str,
        *,
        answer_mode: Literal["fact", "comparison", "plan"] = "fact",
        missing: list[str] | None = None,
    ) -> Answer:
        return Answer(
            answer_id=uuid4(),
            question=question,
            text=message,
            purpose=purpose.value,
            answer_mode=answer_mode,
            index_status="ready",
            missing_information=missing or [message],
        )

    @staticmethod
    def _readable_dimension(dimension: str, subject: str) -> str:
        labels = {
            "budget": "预算",
            "schedule": "排期或启动时间",
            "storage": "存储或保管规则",
            "owner": "负责人信息",
        }
        base, *qualifiers = dimension.split("&")
        # A bare exact topic carries no family label; show its business text
        # instead of leaking the internal term: marker into the answer.
        base_parts = [item.removeprefix("term:") for item in base.split("+")]
        base_label = "、".join(labels.get(part, part) for part in base_parts)
        qualifier_labels = [
            item.removeprefix("term:")
            for item in qualifiers
            if item.startswith("term:") and item.removeprefix("term:") != subject
        ]
        return f"{base_label}（{'、'.join(qualifier_labels)}）" if qualifier_labels else base_label

    def _scope_missing_pairs(self, pairs: set[tuple[str, str]]) -> list[str]:
        return [
            f"{subject or '未限定对象'}：缺少"
            f"{self._readable_dimension(dimension, subject) or '可引用的主题资料'}依据。"
            for subject, dimension in sorted(pairs)
        ]

    def _truncated_scope_notice(self, pairs: set[tuple[str, str]]) -> str:
        labels = [
            f"{subject or '未限定对象'}："
            f"{self._readable_dimension(dimension, subject) or '所问主题'}"
            for subject, dimension in sorted(pairs)
        ]
        return (
            "本次引用条数已达上限，以下所问范围尚未覆盖："
            + "；".join(labels)
            + "。可缩小问题范围或减少所问对象/主题后重试。"
        )

    def _candidate_limit_notice(self, pairs: set[tuple[str, str]]) -> str:
        labels = [
            f"{subject or '未限定对象'}："
            f"{self._readable_dimension(dimension, subject) or '所问主题'}"
            for subject, dimension in sorted(pairs)
        ]
        return (
            "检索前20条候选未包含以下已有资料范围："
            + "；".join(labels)
            + "。可缩小问题范围后重试。"
        )

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
