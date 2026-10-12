"""DSH subagent pre-QA black-box helpers for C19 (fresh, independent construction).

Only fake/offline providers are used: deterministic hashed embeddings, a recording
answer provider that never touches the network, and an adversarial high-score
reranker. Workspaces are isolated synthetic temp directories.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.llm import GroundedAnswer
from summit_everything.retrieval.planner import plan_retrieval
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import (
    create_line,
    create_project,
    create_workspace,
    load_manifest,
)
from summit_everything.workspace.writer import PageWriter

FINGERPRINT = "dsh-preqa-c19-v1"


@dataclass
class RecordingAnswerer:
    """Records every provider call. Default is the *permissive* provider."""

    text: str = "依据所给材料。"
    missing: list[str] = field(default_factory=list)
    inferences: list[str] = field(default_factory=lambda: ["推断"])
    advice: list[str] = field(default_factory=lambda: ["建议"])
    calls: list[tuple[str, list[dict[str, str]], Any]] = field(default_factory=list)

    def answer(self, question, passages, context=None):
        self.calls.append((question, [dict(p) for p in passages], context))
        return GroundedAnswer(
            text=self.text,
            missing_information=list(self.missing),
            inferences=list(self.inferences),
            advice=list(self.advice),
        )


class MaxReranker:
    """Adversarial reranker: every candidate gets an extreme score.

    Ordering is *reverse* of the input, so a single high-scoring out-of-scope
    neighbour would be promoted first if the scope gate were score-based.
    """

    def __init__(self, score: float = 99999.0) -> None:
        self.score = score
        self.calls: list[tuple[str, list[str]]] = []

    def rank(self, query: str, texts: list[str]):
        self.calls.append((query, list(texts)))
        return [(index, self.score - index) for index in reversed(range(len(texts)))]


class PromoteReranker:
    """Promotes candidates matching `predicate` to the very top."""

    def __init__(self, predicate) -> None:
        self.predicate = predicate
        self.calls: list[tuple[str, list[str]]] = []

    def rank(self, query: str, texts: list[str]):
        self.calls.append((query, list(texts)))
        top = [i for i, text in enumerate(texts) if self.predicate(text)]
        rest = [i for i in range(len(texts)) if i not in top]
        ordered = top + rest
        return [(index, 50000.0 - rank) for rank, index in enumerate(ordered)]


class Probe:
    def __init__(self, root: Path, profile: Path, service: QueryService,
                 answerer: RecordingAnswerer, reranker: Any, projects: dict[str, Any],
                 line_id: Any) -> None:
        self.root = root
        self.profile = profile
        self.service = service
        self.answerer = answerer
        self.reranker = reranker
        self.projects = projects
        self.line_id = line_id

    def ask(self, question: str, mode: str = "fact", **kwargs):
        return self.service.query(
            root=self.root,
            question=question,
            fingerprint=FINGERPRINT,
            answer_mode=mode,
            **kwargs,
        )

    def plan(self, question: str, previous: list[str] | None = None):
        object_aliases: list[str] = []
        aliases = self.service._subject_aliases(
            self.root, load_manifest(self.root), object_aliases=object_aliases
        )
        return plan_retrieval(
            question, previous or [], aliases, object_aliases=tuple(object_aliases)
        )

    def ensure_project(self, project_name: str):
        if project_name not in self.projects:
            self.projects[project_name] = create_project(
                self.root, self.line_id, project_name,
                f"dsh-p-{len(self.projects)}-{uuid4().hex[:8]}",
            )
        return self.projects[project_name]

    def add_page(self, project: str, title: str, body: str, *, kind: str = "topic") -> None:
        row = self.ensure_project(project)
        PageWriter().confirm(
            self.root,
            metadata={
                "id": str(uuid4()),
                "title": title,
                "role": "knowledge",
                "kind": kind,
                "line_id": str(self.line_id),
                "project_id": str(row.id),
            },
            body=body,
            confirmation_id=f"dsh-confirm-{uuid4().hex}",
            operation_id=f"dsh-write-{uuid4().hex}",
        )

    def reindex(self) -> None:
        self.service.rebuild(self.root, fingerprint=FINGERPRINT)


def build(
    tmp_path: Path,
    pages: list[tuple[str, str, str]],
    *,
    name: str = "DSH PreQA",
    reranker: Any | None = None,
    answerer: RecordingAnswerer | None = None,
    line_name: str = "综合运营线",
) -> Probe:
    """Create an isolated synthetic workspace with one confirmed page per tuple."""
    root = tmp_path / "workspace"
    profile = tmp_path / "profile"
    create_workspace(root, name, profile, f"dsh-preqa-{uuid4()}")
    line = create_line(root, line_name, f"dsh-line-{uuid4()}")
    probe = Probe(
        root=root,
        profile=profile,
        service=None,  # type: ignore[arg-type]
        answerer=answerer or RecordingAnswerer(),
        reranker=reranker or MaxReranker(),
        projects={},
        line_id=line.id,
    )
    for project_name, title, body in pages:
        probe.add_page(project_name, title, body)
    probe.service = QueryService(
        IndexStore(profile / "index.sqlite3"),
        FakeEmbedding(),
        reranker=probe.reranker,
        answer_provider=probe.answerer,
    )
    probe.service.rebuild(root, fingerprint=FINGERPRINT)
    return probe


def excerpt_text(answer) -> str:
    return "\n".join(citation.excerpt for citation in answer.citations)


def sent_text(answerer: RecordingAnswerer, index: int = 0) -> str:
    if len(answerer.calls) <= index:
        return ""
    return "\n".join(p["excerpt"] for p in answerer.calls[index][1])


def sent_all_text(answerer: RecordingAnswerer) -> str:
    return "\n".join(
        p["excerpt"] for _, passages, _ in answerer.calls for p in passages
    )


def dump(answer) -> str:
    return (
        f"text={answer.text[:200]!r} | citations={len(answer.citations)} | "
        f"excerpts={[c.excerpt[:60] for c in answer.citations]} | "
        f"source_statements={answer.source_statements} | "
        f"inferences={answer.inferences} | advice={answer.advice} | "
        f"missing={answer.missing_information} | status={answer.index_status}"
    )
