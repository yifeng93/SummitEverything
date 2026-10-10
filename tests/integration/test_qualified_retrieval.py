from __future__ import annotations

from pathlib import Path
from uuid import UUID

from summit_everything.domain.content import RetrievalPurpose
from summit_everything.intake.sources import IntakeService
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.llm import GroundedAnswer
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import (
    WorkspaceError,
    create_line,
    create_project,
    create_workspace,
)
from summit_everything.workspace.reader import list_pages
from summit_everything.workspace.writer import PageWriter


def create_test_workspace(root: Path) -> tuple[Path, str, str]:
    create_workspace(root, "检索模拟库", root.parent / "profile", "workspace")
    line = create_line(root, "模拟线", "line")
    project = create_project(root, line.id, "模拟项目", "project")
    return root, str(line.id), str(project.id)


def approve_page(
    root: Path,
    line_id: str,
    project_id: str,
    *,
    body: str,
    title: str = "模拟事实",
    metadata_extra: dict[str, object] | None = None,
    page_id: UUID | None = None,
) -> tuple[UUID, str]:
    from uuid import uuid4

    metadata = {
        "id": str(page_id or uuid4()),
        "title": title,
        "role": "knowledge",
        "kind": "topic",
        "line_id": line_id,
        "project_id": project_id,
        **(metadata_extra or {}),
    }
    result = PageWriter().confirm(
        root,
        metadata=metadata,
        body=body,
        confirmation_id=f"confirm-{title}-{body[:8]}",
        operation_id=f"write-{title}-{body[:8]}",
    )
    return UUID(str(metadata["id"])), result.page_versions[str(metadata["id"])]


def test_source_and_draft_material_never_enter_qualified_index(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    relevant_id, _ = approve_page(root, line_id, project_id, body="雪松项目的正式演示地点是北馆。")
    approve_page(
        root,
        line_id,
        project_id,
        body="石榴项目的合同签约日期是十月十日。",
        title="另一项事实",
    )
    IntakeService().add_text(
        root, "雪松项目的正式演示地点是南馆。", filename="original.txt", operation_id="source"
    )
    draft_root = root / ".summit-everything" / "drafts"
    draft_root.mkdir(parents=True)
    (draft_root / "unapproved.md").write_text(
        "---\nid: 00000000-0000-0000-0000-000000000001\n"
        "title: Unapproved\nrole: knowledge\nkind: topic\n"
        f"line_id: {line_id}\nproject_id: {project_id}\n"
        "approval:\n  version: 1\n"
        "  content_sha256: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
        "  confirmed_at: '2026-10-09T00:00:00+00:00'\n"
        "  confirmation_id: forged\n---\n南馆",
        encoding="utf-8",
    )
    embedding = FakeEmbedding()
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), embedding)

    result = retrieval.rebuild(root, fingerprint="fake-v1")
    answer = retrieval.query(
        root,
        "雪松项目演示地点",
        fingerprint="fake-v1",
        purpose=RetrievalPurpose.CURRENT,
        limit=1,
    )

    assert result.indexed_pages == 2
    assert answer.citations
    assert "北馆" in answer.text
    assert "南馆" not in answer.text
    assert answer.citations[0].page_id == relevant_id
    no_match = retrieval.query(root, "完全不相关的查询", fingerprint="fake-v1")
    assert no_match.citations == []
    assert "没有找到" in no_match.text


def test_grounded_answer_receives_only_server_qualified_citations(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    approve_page(root, line_id, project_id, body="正式确认的地点是北馆。")
    captured: list[dict[str, str]] = []

    class Answerer:
        def answer(self, question: str, passages: list[dict[str, str]]) -> GroundedAnswer:
            captured.extend(passages)
            return GroundedAnswer(
                text="北馆。", inferences=["来自正式资料"], missing_information=[]
            )

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    retrieval.rebuild(root, fingerprint="fake-v1")

    answer = retrieval.query(root, "地点在哪里？", fingerprint="fake-v1")

    assert answer.text == "北馆。"
    assert answer.citations
    assert answer.inferences == ["来自正式资料"]
    assert captured == [{"heading": "页面内容", "excerpt": "正式确认的地点是北馆。"}]


def test_external_edit_and_reapproval_reject_old_cached_chunk(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    page_id, first_version = approve_page(
        root, line_id, project_id, body="蓝松项目的演示地点是北馆。"
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")
    initial = retrieval.query(
        root, "蓝松演示地点", fingerprint="fake-v1", purpose=RetrievalPurpose.CURRENT
    )
    assert initial.citations and initial.citations[0].content_sha256 == first_version

    page = next(page for page in list_pages(root) if page.page_id == page_id)
    path = root / page.relative_path
    path.write_text(path.read_text(encoding="utf-8").replace("北馆", "西馆"), encoding="utf-8")
    after_external_edit = retrieval.query(
        root, "蓝松演示地点", fingerprint="fake-v1", purpose=RetrievalPurpose.CURRENT
    )
    assert after_external_edit.citations == []
    assert "西馆" not in after_external_edit.text

    externally_edited = next(page for page in list_pages(root) if page.page_id == page_id)
    PageWriter().confirm(
        root,
        metadata={
            key: value for key, value in externally_edited.metadata.items() if key != "approval"
        },
        body="蓝松项目的演示地点是西馆。",
        confirmation_id="confirm-reapproved",
        operation_id="write-reapproved",
        expected_base_sha256=externally_edited.content_sha256,
    )
    after_reapproval = retrieval.query(
        root, "蓝松演示地点", fingerprint="fake-v1", purpose=RetrievalPurpose.CURRENT
    )
    assert after_reapproval.citations == []


def test_unchanged_chunks_reuse_embedding_and_plan_reports_cost(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    approve_page(
        root,
        line_id,
        project_id,
        body="# 北馆项目\n\n## 地点\n\n会议演示在北馆。\n\n## 联系人\n\n联系人是林女士。",
    )
    embedding = FakeEmbedding()
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), embedding)

    plan = retrieval.plan(root, fingerprint="fake-v1", mode="initial")
    first = retrieval.execute_plan(root, plan)
    calls_after_first_build = embedding.calls
    second_plan = retrieval.plan(root, fingerprint="fake-v1", mode="incremental")
    second = retrieval.execute_plan(root, second_plan)

    assert plan.estimated_tokens > 0
    assert first.embedded_chunks >= 1
    assert second.reused_chunks == first.indexed_chunks
    assert embedding.calls == calls_after_first_build
    assert second.active_fingerprint == "fake-v1"


def test_archiving_project_keeps_its_confirmed_knowledge_searchable(tmp_path: Path) -> None:
    from summit_everything.workspace.manifest import delete_project, update_project

    root, _line_id, project_id = create_test_workspace(tmp_path / "workspace")
    page_id, _ = approve_page(
        root,
        _line_id,
        project_id,
        body="雪松案例的最终交付地点是东馆。",
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")

    update_project(
        root,
        UUID(project_id),
        name=None,
        archived=True,
        operation_id="archive-project",
    )
    answer = retrieval.query(
        root, "雪松案例最终交付地点", fingerprint="fake-v1", purpose=RetrievalPurpose.CURRENT
    )

    assert answer.citations
    assert answer.citations[0].page_id == page_id
    assert "东馆" in answer.text
    try:
        delete_project(root, UUID(project_id), "delete-nonempty-project")
    except WorkspaceError as error:
        assert error.status_code == 409
    else:
        raise AssertionError("a nonempty archived project was deleted")


def test_current_and_history_queries_label_superseded_knowledge(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    superseded_id, _ = approve_page(
        root,
        line_id,
        project_id,
        body="旧合同版本的付款日是六月一日。",
        title="旧付款安排",
        metadata_extra={"validity": "superseded"},
    )
    current_id, _ = approve_page(
        root,
        line_id,
        project_id,
        body="现行合同版本的付款日是七月一日。",
        title="现行付款安排",
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")

    current = retrieval.query(
        root, "合同版本付款日六月一日", fingerprint="fake-v1", purpose=RetrievalPurpose.CURRENT
    )
    history = retrieval.query(
        root, "合同版本付款日六月一日", fingerprint="fake-v1", purpose=RetrievalPurpose.HISTORY
    )

    assert superseded_id not in {citation.page_id for citation in current.citations}
    old_citation = next(c for c in history.citations if c.page_id == superseded_id)
    assert old_citation.validity == "superseded"


def test_neighbor_pages_are_rechecked_before_they_become_citations(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    from uuid import uuid4

    neighbor_id = uuid4()
    main_id, _ = approve_page(
        root,
        line_id,
        project_id,
        body="云杉大厦的地址信息见关联资料。",
        title="主页面",
        metadata_extra={"related_page_ids": [str(neighbor_id)]},
    )
    approve_page(
        root,
        line_id,
        project_id,
        body="云杉大厦地址是东路 18 号。",
        title="关联地址",
        page_id=neighbor_id,
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")
    answer = retrieval.query(root, "云杉大厦地址", fingerprint="fake-v1")
    assert {citation.page_id for citation in answer.citations} == {main_id, neighbor_id}

    neighbor = next(page for page in list_pages(root) if page.page_id == neighbor_id)
    neighbor_path = root / neighbor.relative_path
    neighbor_path.write_text(
        neighbor_path.read_text(encoding="utf-8").replace("东路 18 号", "西路 90 号"),
        encoding="utf-8",
    )
    refreshed = retrieval.query(root, "云杉大厦地址", fingerprint="fake-v1")
    assert neighbor_id not in {citation.page_id for citation in refreshed.citations}


def test_stale_plan_and_failed_model_change_keep_previous_index_active(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    page_id, _ = approve_page(root, line_id, project_id, body="银杏项目合同存放在档案柜。")
    embedding = FakeEmbedding()
    store = IndexStore(tmp_path / "profile" / "index.sqlite3")
    retrieval = QueryService(store, embedding)
    retrieval.rebuild(root, fingerprint="fake-v1")
    plan = retrieval.plan(root, fingerprint="fake-v1", mode="incremental")
    page = next(page for page in list_pages(root) if page.page_id == page_id)
    page_path = root / page.relative_path
    page_path.write_text(
        page_path.read_text(encoding="utf-8").replace("档案柜", "保险柜"), encoding="utf-8"
    )

    from summit_everything.retrieval.query import IndexPlanStale

    try:
        retrieval.execute_plan(root, plan)
    except IndexPlanStale:
        pass
    else:
        raise AssertionError("a plan created against older page versions was accepted")

    externally_edited = next(page for page in list_pages(root) if page.page_id == page_id)
    PageWriter().confirm(
        root,
        metadata={
            key: value for key, value in externally_edited.metadata.items() if key != "approval"
        },
        body="银杏项目合同存放在保险柜。",
        confirmation_id="confirm-edited",
        operation_id="write-edited",
        expected_base_sha256=externally_edited.content_sha256,
    )

    class FailingEmbedding(FakeEmbedding):
        def embed(self, text: str, *, fingerprint: str) -> list[float]:
            raise RuntimeError("simulated embedding failure")

    model_change = retrieval.plan(root, fingerprint="fake-v2", mode="model_change")
    failing = QueryService(store, FailingEmbedding())
    try:
        failing.execute_plan(root, model_change)
    except RuntimeError:
        pass
    else:
        raise AssertionError("model change failure was hidden")
    from summit_everything.workspace.manifest import load_manifest

    assert store.active_fingerprint(load_manifest(root).workspace_id) == "fake-v1"
