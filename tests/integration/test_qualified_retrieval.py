from __future__ import annotations

from pathlib import Path
from uuid import UUID

import yaml

from summit_everything.domain.content import RetrievalPurpose, content_sha256
from summit_everything.intake.sources import IntakeService
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.llm import GroundedAnswer
from summit_everything.local.answer_context import AnswerContext
from summit_everything.retrieval.planner import plan_retrieval
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import (
    WorkspaceError,
    create_line,
    create_project,
    create_workspace,
    load_manifest,
)
from summit_everything.workspace.reader import list_pages, read_page
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


def test_unrelated_query_reports_missing_relevance_without_claiming_index_failure(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    approve_page(root, line_id, project_id, body="预算上限已确认是十二万元。", title="预算")
    approve_page(root, line_id, project_id, body="启动时间已确认在十一月。", title="排期")
    calls: list[str] = []

    class Answerer:
        def answer(self, question, passages, context=None):
            calls.append(question)
            return GroundedAnswer(text="不应由无关材料生成回答。")

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    retrieval.rebuild(root, fingerprint="fake-v1")

    for mode in ("fact", "comparison", "plan"):
        answer = retrieval.query(
            root,
            "为彩色牙刷储存规则提出建议并列出缺失信息。",
            fingerprint="fake-v1",
            answer_mode=mode,
        )

        assert answer.index_status == "ready"
        assert answer.citations == []
        expected = "彩色牙刷：缺少存储或保管规则依据。"
        assert answer.missing_information == [expected]
        assert expected in answer.text
        assert "缓存" not in answer.missing_information[0]
        assert "资格检查未通过" not in answer.missing_information[0]
    assert calls == []


def test_current_scope_explains_historical_qualification_without_cache_warning(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    page_id, _ = approve_page(
        root,
        line_id,
        project_id,
        body="云杉工程的档案规则已确认。",
        title="档案规则",
    )
    invalid_id, _ = approve_page(
        root,
        line_id,
        project_id,
        body="白桦工程的保管规则已确认。",
        title="保管规则",
    )
    pages = {page.page_id: page for page in list_pages(root)}
    for target_id, validity in ((page_id, "superseded"), (invalid_id, "invalid")):
        page = pages[target_id]
        PageWriter().confirm(
            root,
            metadata={**page.metadata, "validity": validity},
            body=page.body,
            confirmation_id=f"confirm-{validity}-diagnostic",
            operation_id=f"write-{validity}-diagnostic",
            expected_base_sha256=page.content_sha256,
        )
    calls: list[str] = []

    class Answerer:
        def answer(self, question, passages, context=None):
            calls.append(question)
            return GroundedAnswer(text="历史范围中的受限回答。")

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    retrieval.rebuild(root, fingerprint="fake-v1")

    current_answers = [
        retrieval.query(
            root,
            "云杉工程的档案规则是什么？",
            fingerprint="fake-v1",
            answer_mode=mode,
        )
        for mode in ("fact", "comparison", "plan")
    ]
    invalid_answers = [
        retrieval.query(
            root,
            "白桦工程的保管规则是什么？",
            fingerprint="fake-v1",
            answer_mode=mode,
        )
        for mode in ("fact", "comparison", "plan")
    ]
    assert calls == []
    history = retrieval.query(
        root,
        "云杉工程的档案规则是什么？",
        fingerprint="fake-v1",
        purpose=RetrievalPurpose.HISTORY,
    )
    history_invalid = retrieval.query(
        root,
        "白桦工程的保管规则是什么？",
        fingerprint="fake-v1",
        purpose=RetrievalPurpose.HISTORY,
    )

    for answer in (*current_answers, *invalid_answers):
        assert answer.citations == []
        assert answer.missing_information == [
            "当前范围没有可引用的已确认资料；历史版本仅在历史范围中可查。"
        ]
        assert "缓存" not in answer.missing_information[0]
    assert history.citations and history.citations[0].page_id == page_id
    assert history_invalid.citations and history_invalid.citations[0].page_id == invalid_id
    assert calls == ["云杉工程的档案规则是什么？", "白桦工程的保管规则是什么？"]


def test_rejected_stale_hash_is_reported_as_version_change(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    page_id, _ = approve_page(
        root,
        line_id,
        project_id,
        body="白桦工程的备份规则已确认。",
        title="备份规则",
    )
    calls: list[str] = []

    class Answerer:
        def answer(self, question, passages, context=None):
            calls.append(question)
            return GroundedAnswer(text="不应使用旧索引回答。")

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    retrieval.rebuild(root, fingerprint="fake-v1")
    page = next(page for page in list_pages(root) if page.page_id == page_id)
    PageWriter().confirm(
        root,
        metadata={key: value for key, value in page.metadata.items() if key != "approval"},
        body="白桦工程的备份规则已更新。",
        confirmation_id="confirm-updated-backup-rule",
        operation_id="write-updated-backup-rule",
        expected_base_sha256=page.content_sha256,
    )

    answers = [
        retrieval.query(
            root,
            "白桦工程的备份规则是什么？",
            fingerprint="fake-v1",
            answer_mode=mode,
        )
        for mode in ("fact", "comparison", "plan")
    ]

    for answer in answers:
        assert answer.citations == []
        assert answer.missing_information == [
            "索引中的页面版本与当前已确认内容不一致；请更新索引后重新查询。"
        ]
        assert answer.text == answer.missing_information[0]
        assert "资格检查未通过" not in answer.missing_information[0]
    assert retrieval.status(root)["state"] == "stale"
    assert calls == []


def test_unrelated_stale_page_does_not_pollute_scoped_query_diagnostics(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    relevant_id, _ = approve_page(
        root,
        line_id,
        project_id,
        body="白鹭工程的预算上限为 19 万元。",
        title="白鹭预算",
    )
    unrelated_id, _ = approve_page(
        root,
        line_id,
        project_id,
        body="朱雀项目的保管规则为每月检查。",
        title="朱雀保管规则",
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")
    unrelated = next(page for page in list_pages(root) if page.page_id == unrelated_id)
    page_path = root / unrelated.relative_path
    page_path.write_text(
        page_path.read_text(encoding="utf-8").replace("每月检查", "每周检查"),
        encoding="utf-8",
    )

    answer = retrieval.query(
        root,
        "白鹭工程预算上限",
        fingerprint="fake-v1",
    )

    assert {citation.page_id for citation in answer.citations} == {relevant_id}
    assert "缓存" not in answer.text
    assert "索引" not in answer.text


def test_not_ready_and_empty_index_are_distinct_and_never_call_answer_provider(
    tmp_path: Path,
) -> None:
    root, _line_id, _project_id = create_test_workspace(tmp_path / "workspace")
    calls: list[str] = []

    class Answerer:
        def answer(self, question, passages, context=None):
            calls.append(question)
            return GroundedAnswer(text="无可引用内容时不应调用回答模型。")

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    not_ready = retrieval.query(root, "需要确认的规则是什么？", fingerprint="fake-v1")
    retrieval.rebuild(root, fingerprint="fake-v1")
    empty = retrieval.query(root, "需要确认的规则是什么？", fingerprint="fake-v1")

    assert not_ready.index_status == "not_ready"
    assert not_ready.missing_information == ["请先完成当前模型版本的索引。"]
    assert empty.index_status == "empty"
    assert empty.missing_information == ["当前索引中没有可引用的知识页。"]
    assert calls == []


def test_grounded_answer_receives_only_server_qualified_citations(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    relevant_id, _ = approve_page(root, line_id, project_id, body="正式确认的地点是北馆。")
    captured: list[dict[str, str]] = []

    class Answerer:
        def answer(
            self, question: str, passages: list[dict[str, str]], context=None
        ) -> GroundedAnswer:
            del context
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
    assert captured == [
        {"source_id": str(relevant_id), "heading": "页面内容", "excerpt": "正式确认的地点是北馆。"}
    ]


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
    after_reapproval_followup = retrieval.query(
        root,
        "它呢？",
        fingerprint="fake-v1",
        purpose=RetrievalPurpose.CURRENT,
        context=AnswerContext(
            previous_user_questions=["蓝松项目的演示地点在哪里？"], answer_mode="fact"
        ),
    )
    assert after_reapproval_followup.citations == []


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


def test_approval_state_is_independent_of_knowledge_validity_and_still_hash_bound(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    page_id, _ = approve_page(
        root,
        line_id,
        project_id,
        body="经确认的旧规则正文。",
        title="旧规则",
        metadata_extra={"validity": "superseded"},
    )

    superseded = read_page(root, page_id)
    assert superseded.approval_state == "confirmed"
    assert superseded.validity == "superseded"

    # Reconfirming an invalidated page records the reviewed content without
    # changing its knowledge lifecycle status or making it current.
    invalid_metadata = {**superseded.metadata, "validity": "invalid"}
    invalid_path = root / superseded.relative_path
    metadata_text = yaml.safe_dump(invalid_metadata, allow_unicode=True, sort_keys=False)
    invalid_path.write_text(f"---\n{metadata_text}---\n{superseded.body}", encoding="utf-8")
    approval = invalid_metadata["approval"]
    assert isinstance(approval, dict)
    approval["content_sha256"] = content_sha256(invalid_metadata, superseded.body)
    metadata_text = yaml.safe_dump(invalid_metadata, allow_unicode=True, sort_keys=False)
    invalid_path.write_text(f"---\n{metadata_text}---\n{superseded.body}", encoding="utf-8")

    invalid = read_page(root, page_id)
    assert invalid.approval_state == "confirmed"
    assert invalid.validity == "invalid"
    result = PageWriter().confirm(
        root,
        metadata=invalid.metadata,
        body=invalid.body,
        confirmation_id="confirm-invalid-version",
        operation_id="confirm-invalid-version",
        expected_base_sha256=invalid.content_sha256,
    )
    assert result.page_versions[str(page_id)] == invalid.content_sha256
    reapproved = read_page(root, page_id)
    assert reapproved.approval_state == "confirmed"
    assert reapproved.validity == "invalid"

    invalid_path.write_text(
        invalid_path.read_text(encoding="utf-8").replace("经确认的旧规则正文。", "外部改动正文。"),
        encoding="utf-8",
    )
    changed = read_page(root, page_id)
    assert changed.approval_state == "invalid"
    assert changed.validity == "invalid"


def test_explicit_fact_subject_excludes_a_different_project_but_comparison_keeps_both(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    qinglan_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="青岚预算",
        body="青岚计划的设备采购预算上限为 19 万元，负责人已确认。",
    )
    zhuque_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="朱雀预算",
        body="朱雀项目的设备采购预算上限为 12 万元，负责人已确认。",
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")

    fact = retrieval.query(root, "青岚计划的预算上限是多少？", fingerprint="fake-v1")
    missing_subject = retrieval.query(root, "紫藤计划的预算上限是多少？", fingerprint="fake-v1")
    comparison = retrieval.query(
        root,
        "青岚计划和朱雀项目的预算上限分别是多少？",
        fingerprint="fake-v1",
        answer_mode="comparison",
    )
    plan = retrieval.query(
        root,
        "请为青岚计划和朱雀项目制定下一步方案。",
        fingerprint="fake-v1",
        answer_mode="plan",
    )

    assert qinglan_id in {citation.page_id for citation in fact.citations}
    assert zhuque_id not in {citation.page_id for citation in fact.citations}
    assert missing_subject.citations == []
    assert "没有找到能确认该对象" in missing_subject.text
    assert {qinglan_id, zhuque_id} <= {citation.page_id for citation in comparison.citations}
    assert {qinglan_id, zhuque_id} <= {citation.page_id for citation in plan.citations}


def test_fact_subject_is_found_inside_a_polite_request_without_filtering_the_prefix(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    qinglan_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="QA 青岚预算与排期",
        body="青岚计划的设备采购预算上限为 19 万元，负责人已确认。",
    )
    zhuque_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="朱雀项目预算",
        body="朱雀项目的设备采购预算上限为 12 万元，负责人已确认。",
    )
    songshi_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="松石项目预算",
        body="松石项目的设备采购预算上限为 16 万元，负责人已确认。",
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")

    answer = retrieval.query(
        root,
        "你能告诉我青岚计划的预算上限是多少吗？",
        fingerprint="fake-v1",
    )
    plan = plan_retrieval("你能告诉我青岚计划的预算上限是多少吗？", [], ("青岚计划",))
    assert plan.explicit_subjects == ("青岚计划",)
    assert plan.required_pairs == (("青岚计划", "budget"),)

    citation_ids = {citation.page_id for citation in answer.citations}
    assert qinglan_id in citation_ids
    assert zhuque_id not in citation_ids

    songshi = retrieval.query(
        root,
        "我想知道松石项目的预算上限。",
        fingerprint="fake-v1",
    )
    assert {citation.page_id for citation in songshi.citations} == {songshi_id}

    unknown = retrieval.query(
        root,
        "麻烦帮我确认紫藤计划的预算上限。",
        fingerprint="fake-v1",
    )
    assert unknown.citations == []


def test_fact_subject_matching_uses_qualified_page_and_workspace_names(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    title_only_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="青岚计划预算",
        body="预算上限为 19 万元。",
    )
    alias_only_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="独立预算记录",
        body="预算上限为 12 万元。",
        metadata_extra={"aliases": ["朱雀项目"]},
    )
    project_only = create_project(Path(root), UUID(line_id), "松石项目", "project-only")
    project_only_id, _ = approve_page(
        root,
        line_id,
        str(project_only.id),
        title="独立项目预算记录",
        body="预算上限为 16 万元。",
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")

    answers = [
        retrieval.query(root, "青岚计划预算上限是多少？", fingerprint="fake-v1"),
        retrieval.query(root, "朱雀项目预算上限是多少？", fingerprint="fake-v1"),
        retrieval.query(root, "松石项目预算上限是多少？", fingerprint="fake-v1"),
    ]

    expected_ids = [title_only_id, alias_only_id, project_only_id]
    for answer, expected_id in zip(answers, expected_ids, strict=True):
        assert {citation.page_id for citation in answer.citations} == {expected_id}
        assert all(
            subject not in citation.excerpt
            for citation in answer.citations
            for subject in ("青岚计划", "朱雀项目", "松石项目")
        )


def test_c19_scopes_every_answer_mode_to_named_objects_and_requested_dimensions(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    known_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="白鹭预算与排期",
        body="白鹭工程的设备预算上限为 24 万元。",
    )
    other_budget_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="白鹭补充预算",
        body="白鹭工程的年度专项预算为 30 万元。",
    )
    unrelated_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="玄武预算",
        body="玄武项目的设备预算上限为 12 万元。",
    )
    other_dimension_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="玄武排期",
        body="玄武项目预计于十月启动。",
    )
    approve_page(
        root,
        line_id,
        project_id,
        title="白鹭仓库保管规则",
        body="白鹭工程的仓库文件由专人保管并每周核验。",
    )
    approve_page(
        root,
        line_id,
        project_id,
        title="玄武备份规则",
        body="玄武项目每周备份一次合同文件。",
    )
    calls: list[tuple[str, list[str]]]

    class Answerer:
        def answer(self, question, passages, context=None):
            calls.append((question, [passage["excerpt"] for passage in passages]))
            # A permissive provider must not erase product-known missing scope.
            return GroundedAnswer(text="资料已经完整。", missing_information=[])

    class HighScoreReranker:
        def rank(self, query, texts):
            return [(index, 99.0 - index) for index in reversed(range(len(texts)))]

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        HighScoreReranker(),
        Answerer(),
    )
    retrieval.rebuild(root, fingerprint="fake-v1")

    # Two unknown objects and an unknown dimension must never fall back to
    # globally high-scoring budget pages, in any answer mode.
    for mode in ("fact", "comparison", "plan"):
        calls = []
        answer = retrieval.query(
            root,
            "比较风铃工程与霜塔项目的彩色牙刷储存规则。",
            fingerprint="fake-v1",
            answer_mode=mode,
        )
        assert answer.citations == []
        assert answer.source_statements == []
        assert answer.inferences == []
        assert answer.advice == []
        assert calls == []

    # Missing “的” does not turn a parallel unknown subject into an unscoped
    # request; both comparison and planning forms preserve the named objects.
    for question in (
        "比较风铃工程和霜塔项目预算上限",
        "为风铃工程和霜塔项目制定下一步方案",
    ):
        for mode in ("fact", "comparison", "plan"):
            calls = []
            answer = retrieval.query(
                root,
                question,
                fingerprint="fake-v1",
                answer_mode=mode,
            )
            assert answer.citations == []
            assert calls == []

    # The same compact syntax preserves a known object and records only the
    # unknown peer as missing; a matching known-object page cannot imply the
    # second object's facts.
    for question, mode in (
        ("比较白鹭工程和霜塔项目预算上限", "comparison"),
        ("为白鹭工程和霜塔项目制定下一步方案", "plan"),
        ("白鹭工程预算上限和霜塔项目启动时间分别是什么", "comparison"),
    ):
        answer = retrieval.query(root, question, fingerprint="fake-v1", answer_mode=mode)
        assert answer.citations
        assert any("霜塔" in value for value in answer.missing_information)
        assert unrelated_id not in {citation.page_id for citation in answer.citations}
        assert "完整" not in answer.text

    # Two pages for one object do not fill the second object's budget slot;
    # a third project's budget is never a substitute for the unknown object.
    for mode in ("fact", "comparison", "plan"):
        calls = []
        answer = retrieval.query(
            root,
            "白鹭工程和霜塔项目的设备预算上限分别是多少？",
            fingerprint="fake-v1",
            answer_mode=mode,
        )
        cited = {citation.page_id for citation in answer.citations}
        assert known_id in cited or other_budget_id in cited
        assert unrelated_id not in cited
        assert other_dimension_id not in cited
        assert any("霜塔" in value for value in answer.missing_information)
        assert "完整" not in answer.text

    paired = retrieval.query(
        root,
        "白鹭工程的预算和玄武项目的启动时间分别是什么？",
        fingerprint="fake-v1",
        answer_mode="comparison",
    )
    paired_ids = {citation.page_id for citation in paired.citations}
    assert known_id in paired_ids or other_budget_id in paired_ids
    assert other_dimension_id in paired_ids
    assert paired.missing_information == []

    # A shared topic list applies to each named object, while partial coverage
    # remains explicit even when one object has several matching pages.
    shared = retrieval.query(
        root,
        "白鹭工程和玄武项目的预算和启动时间分别是什么？",
        fingerprint="fake-v1",
        answer_mode="comparison",
    )
    assert any("白鹭工程" in value and "启动" in value for value in shared.missing_information)

    # Known subjects do not make unfamiliar, more specifically named topics
    # relevant merely because their broad semantic family matches.
    for mode in ("fact", "comparison", "plan"):
        for topic in ("彩色牙刷储存规则", "橙色雨伞保管规则"):
            calls = []
            answer = retrieval.query(
                root,
                f"白鹭工程和玄武项目的{topic}是什么？",
                fingerprint="fake-v1",
                answer_mode=mode,
            )
            assert answer.citations == []
            assert calls == []

    # Broad wording without “的” still preserves the exact named topic. Pages
    # about other kinds of storage cannot support an umbrella rule.
    for mode in ("fact", "comparison", "plan"):
        calls = []
        answer = retrieval.query(
            root,
            "比较橙色雨伞保管规则",
            fingerprint="fake-v1",
            answer_mode=mode,
        )
        assert answer.citations == []
        assert calls == []

    # A known budget plus a missing schedule remains explicitly partial; the
    # other project's schedule cannot cover the missing requested pair.
    for mode in ("fact", "comparison", "plan"):
        calls = []
        answer = retrieval.query(
            root,
            "白鹭工程的预算和启动时间分别是什么？",
            fingerprint="fake-v1",
            answer_mode=mode,
        )
        cited = {citation.page_id for citation in answer.citations}
        assert known_id in cited or other_budget_id in cited
        assert other_dimension_id not in cited
        assert any("启动" in value or "时间" in value for value in answer.missing_information), (
            answer
        )
        assert "完整" not in answer.text


def test_c19_same_chunk_does_not_cross_assign_subjects_to_other_dimensions(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    approve_page(
        root,
        line_id,
        project_id,
        title="混合预算与排期",
        body=(
            "白鹭工程的预算上限为 19 万元；玄武项目预计于十一月启动。"
            "白鹭工程预算上限为 19 万元，玄武项目预计于十一月启动。"
            "白鹭工程预算上限为 19 万元, 玄武项目预计于十一月启动。"
            "白鹭工程预算上限为 19 万元，以及玄武项目预计于十一月启动。"
        ),
    )
    calls: list[str] = []

    class Answerer:
        def answer(self, question, passages, context=None):
            calls.append(question)
            return GroundedAnswer(text="不应发生跨对象推断。")

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    retrieval.rebuild(root, fingerprint="fake-v1")

    for mode in ("fact", "comparison", "plan"):
        for question in (
            "白鹭工程的启动时间和玄武项目的预算分别是什么？",
            "白鹭工程启动时间和玄武项目预算分别是什么？",
        ):
            answer = retrieval.query(
                root,
                question,
                fingerprint="fake-v1",
                answer_mode=mode,
            )
            assert answer.citations == []
            assert answer.source_statements == []
        assert calls == []


def test_c19_neighbor_expansion_reuses_scope_and_keeps_valid_same_topic_neighbor(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    from uuid import uuid4

    same_topic_id = uuid4()
    unrelated_id = uuid4()
    approve_page(
        root,
        line_id,
        project_id,
        title="白鹭主预算",
        body="白鹭工程的预算上限为 19 万元，详情见关联页面。",
        metadata_extra={"related_page_ids": [str(same_topic_id), str(unrelated_id)]},
    )
    approve_page(
        root,
        line_id,
        project_id,
        title="白鹭补充预算",
        body="白鹭工程的设备预算另有 4 万元专项额度。",
        page_id=same_topic_id,
    )
    approve_page(
        root,
        line_id,
        project_id,
        title="朱雀储存规则",
        body="朱雀项目的设备保管规则是双人登记。",
        page_id=unrelated_id,
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")

    answer = retrieval.query(
        root,
        "白鹭工程预算上限是多少？",
        fingerprint="fake-v1",
        answer_mode="fact",
    )

    cited = {citation.page_id for citation in answer.citations}
    assert same_topic_id in cited
    assert unrelated_id not in cited
    assert all("保管规则" not in citation.excerpt for citation in answer.citations)


def test_c19_general_comparison_keeps_multiple_material_path_without_object_gate(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    budget_id, _ = approve_page(
        root, line_id, project_id, title="预算汇总", body="专项储备上限为 3.6 万元。"
    )
    schedule_id, _ = approve_page(
        root, line_id, project_id, title="时间安排", body="各项工作计划于九月启动。"
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")

    answer = retrieval.query(
        root,
        "比较预算和排期，并汇总现有资料。",
        fingerprint="fake-v1",
        answer_mode="comparison",
    )

    assert {budget_id, schedule_id} <= {citation.page_id for citation in answer.citations}
    assert answer.missing_information == []

    polite = plan_retrieval("我希望先核对预算和排期，再给简短结论。", [], ())
    assert not polite.unresolved_topic
    assert polite.explicit_subjects == ()
    assert set(polite.dimensions) == {"budget", "schedule"}


def test_c19_unknown_exact_topics_are_separated_from_object_names_and_keep_positive_matches(
    tmp_path: Path,
) -> None:
    root, line_id, _ = create_test_workspace(tmp_path / "workspace")
    project = create_project(root, UUID(line_id), "预算时间工作坊", "scope-workshop")
    budget_id, _ = approve_page(
        root,
        line_id,
        str(project.id),
        title="预算记录",
        body="预算时间工作坊预算上限为五万元，开会时间为六月。",
    )
    signin_id, _ = approve_page(
        root,
        line_id,
        str(project.id),
        title="培训签到",
        body="培训签到须现场登记并核验姓名。",
    )
    visitor_id, _ = approve_page(
        root,
        line_id,
        str(project.id),
        title="访客登记",
        body="青榆的访客登记须由前台核验姓名并记录来访时间。",
        metadata_extra={"aliases": ["青榆"]},
    )
    asset_id, _ = approve_page(
        root,
        line_id,
        str(project.id),
        title="资产借还",
        body="资产借还应记录设备编号并由经手人签收。",
    )
    calls: list[tuple[str, list[str]]]

    class Answerer:
        def answer(self, question, passages, context=None):
            calls.append((question, [passage["excerpt"] for passage in passages]))
            return GroundedAnswer(text="根据材料回答。")

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    retrieval.rebuild(root, fingerprint="fake-v1")

    cases = (
        ("预算时间工作坊的培训签到办法是什么", "fact", signin_id),
        ("为预算时间工作坊制定培训签到流程", "plan", signin_id),
        ("比较预算时间工作坊培训签到安排", "comparison", signin_id),
        ("青榆访客登记办法是什么", "fact", visitor_id),
        ("培训签到办法怎么安排", "plan", signin_id),
        ("访客登记流程是什么", "fact", visitor_id),
        ("资产借还手续怎么处理", "plan", asset_id),
    )
    for question, mode, expected_id in cases:
        calls = []
        object_aliases: list[str] = []
        aliases = retrieval._subject_aliases(
            root, load_manifest(root), object_aliases=object_aliases
        )
        plan = plan_retrieval(question, [], aliases, object_aliases=object_aliases)
        answer = retrieval.query(
            root,
            question,
            fingerprint="fake-v1",
            answer_mode=mode,
        )
        assert not plan.unresolved_topic, (question, plan)
        if question == "青榆访客登记办法是什么":
            assert plan.explicit_subjects == ("青榆",)
            assert plan.dimensions == ("term:访客登记",)
        assert {citation.page_id for citation in answer.citations} == {expected_id}, (
            question,
            plan,
            answer.model_dump(),
        )
        assert all(citation.page_id != budget_id for citation in answer.citations), (
            question,
            answer.model_dump(),
        )
        expected_term = (
            "培训签到"
            if expected_id == signin_id
            else "访客登记"
            if expected_id == visitor_id
            else "资产借还"
        )
        assert calls and expected_term in "\n".join(calls[-1][1])


def test_c19_unknown_exact_topic_without_evidence_is_fail_closed_in_all_modes(
    tmp_path: Path,
) -> None:
    root, line_id, _ = create_test_workspace(tmp_path / "workspace")
    project = create_project(root, UUID(line_id), "青岚计划", "known-scope")
    approve_page(
        root,
        line_id,
        str(project.id),
        title="预算排期",
        body="青岚计划预算上限为五万元，预计六月启动。",
    )
    calls: list[str] = []

    class Answerer:
        def answer(self, question, passages, context=None):
            calls.append(question)
            return GroundedAnswer(text="不应以无关主题回答。", missing_information=[])

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    retrieval.rebuild(root, fingerprint="fake-v1")

    for question in (
        "青岚计划的访客登记办法是什么",
        "青岚计划访客登记办法是什么",
        "访客登记办法怎么安排",
        "访客登记",
        "青岚计划的资产借还流程是什么",
        "资产借还流程怎么处理",
        "培训签到",
    ):
        plan = plan_retrieval(question, [], retrieval._subject_aliases(root, load_manifest(root)))
        assert not plan.unresolved_topic, (question, plan)
        assert plan.dimensions, (question, plan)
        for mode in ("fact", "comparison", "plan"):
            calls.clear()
            answer = retrieval.query(
                root,
                question,
                fingerprint="fake-v1",
                answer_mode=mode,
            )
            assert answer.citations == [], (question, mode, plan, answer.model_dump())
            assert answer.source_statements == []
            assert answer.inferences == [] and answer.advice == []
            assert answer.missing_information
            assert calls == []


def test_c19_broad_dimensions_ignore_page_title_as_subject_but_keep_schedule_evidence(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    budget_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="预算汇总",
        body="专项预算上限为二十万元。",
    )
    schedule_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="排期",
        body="综合项目预计于十二月启动。",
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")
    aliases = retrieval._subject_aliases(root, load_manifest(root))
    plan = plan_retrieval("比较预算和排期建议", [], aliases)
    assert plan.explicit_subjects == ()
    assert set(plan.dimensions) == {"budget", "schedule"}
    answer = retrieval.query(
        root,
        "比较预算和排期建议",
        fingerprint="fake-v1",
        answer_mode="comparison",
    )
    assert {citation.page_id for citation in answer.citations} == {budget_id, schedule_id}
    assert answer.missing_information == []


def test_c19_limit_truncation_reports_uncovered_comparison_subject(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    for index in range(22):
        approve_page(
            root,
            line_id,
            project_id,
            title=f"白鹭预算记录 {index}",
            body=f"白鹭工程的预算上限记录 {index} 为 {index + 1} 万元。",
        )
    _, _ = approve_page(
        root,
        line_id,
        project_id,
        title="霜塔预算",
        body="霜塔项目的预算上限为 90 万元。",
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")

    answer = retrieval.query(
        root,
        "比较白鹭工程和霜塔项目的预算上限。",
        fingerprint="fake-v1",
        answer_mode="comparison",
        limit=1,
    )

    assert len(answer.citations) == 1
    assert answer.missing_information
    assert any("白鹭工程" in value or "霜塔项目" in value for value in answer.missing_information)


def test_c19_keeps_local_topics_paired_with_their_subjects(tmp_path: Path) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    budget_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="白鹭预算",
        body="白鹭工程预算上限为十八万元。",
    )
    topic_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="赤陶证章领取",
        body="赤陶项目活动证章领取须出示邀请函。",
    )
    visitor_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="青榆访客注销",
        body="青榆项目访客证件注销须交回实体卡。",
    )
    badge_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="橡果活动领取",
        body="橡果工程活动证章领取须出示邀请函。",
    )
    same_subject_topic_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="白鹭证章领取",
        body="白鹭工程活动证章领取须出示邀请函。",
    )
    calls: list[list[str]] = []

    class Answerer:
        def answer(self, question, passages, context=None):
            calls.append([str(passage["excerpt"]) for passage in passages])
            return GroundedAnswer(text="依据已确认资料。", missing_information=[])

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    retrieval.rebuild(root, fingerprint="fake-v1")

    full_questions = (
        "比较白鹭工程预算与赤陶项目的活动证章领取办法",
        "比较赤陶项目的活动证章领取办法与白鹭工程预算",
    )
    object_aliases: list[str] = []
    aliases = retrieval._subject_aliases(root, load_manifest(root), object_aliases=object_aliases)
    plan = plan_retrieval(full_questions[0], [], aliases, object_aliases=object_aliases)
    assert plan.required_pairs == (
        ("白鹭工程", "budget"),
        ("赤陶项目", "term:活动证章领取"),
    ), (plan, aliases, object_aliases)
    for question, expected in (
        (
            "比较青榆项目的访客证件注销办法与橡果工程的活动证章领取办法",
            {visitor_id, badge_id},
        ),
        (
            "比较白鹭工程的预算和活动证章领取办法",
            {budget_id, same_subject_topic_id},
        ),
    ):
        answer = retrieval.query(
            root,
            question,
            fingerprint="fake-v1",
            answer_mode="comparison",
        )
        assert {citation.page_id for citation in answer.citations} == expected, (
            question,
            answer.model_dump(),
        )
    scope_checks = (
        (
            "比较预算与活动证章领取办法",
            {("", "budget"), ("", "term:活动证章领取")},
        ),
        (
            "比较访客证件注销与活动证章领取办法",
            {("", "term:访客证件注销"), ("", "term:活动证章领取")},
        ),
        (
            "比较白鹭工程与赤陶项目的预算和排期",
            {
                ("白鹭工程", "budget"),
                ("白鹭工程", "schedule"),
                ("赤陶项目", "budget"),
                ("赤陶项目", "schedule"),
            },
        ),
        (
            "比较白鹭工程的预算和活动证章领取办法",
            {
                ("白鹭工程", "budget"),
                ("白鹭工程", "term:活动证章领取"),
            },
        ),
        (
            "比较青榆项目的访客证件注销办法与橡果工程的活动证章领取办法",
            {
                ("青榆项目", "term:访客证件注销"),
                ("橡果工程", "term:活动证章领取"),
            },
        ),
        (
            "比较白鹭工程与赤陶项目的彩色牙刷储存规则",
            {
                ("白鹭工程", "storage&term:彩色牙刷"),
                ("赤陶项目", "storage&term:彩色牙刷"),
            },
        ),
        (
            "比较白鹭工程预算与赤陶项目",
            {("白鹭工程", "budget"), ("赤陶项目", "")},
        ),
    )
    for question, expected_pairs in scope_checks:
        plan = plan_retrieval(question, [], aliases, object_aliases=object_aliases)
        assert set(plan.required_pairs) == expected_pairs, (question, plan)

    open_topic_answers = (
        retrieval.query(
            root,
            "比较预算与活动证章领取办法",
            fingerprint="fake-v1",
            answer_mode="comparison",
        ),
        retrieval.query(
            root,
            "比较访客证件注销与活动证章领取办法",
            fingerprint="fake-v1",
            answer_mode="comparison",
        ),
    )
    assert {
        budget_id,
        topic_id,
        badge_id,
        same_subject_topic_id,
    } <= {citation.page_id for citation in open_topic_answers[0].citations}
    assert {visitor_id, topic_id, badge_id} <= {
        citation.page_id for citation in open_topic_answers[1].citations
    }
    assert all(not answer.missing_information for answer in open_topic_answers)

    partial_open_root, partial_open_line, partial_open_project = create_test_workspace(
        tmp_path / "partial-open-workspace"
    )
    partial_budget_id, _ = approve_page(
        partial_open_root,
        partial_open_line,
        partial_open_project,
        title="预算记录",
        body="预算上限为十八万元。",
    )
    partial_open = QueryService(
        IndexStore(tmp_path / "partial-open-profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    partial_open.rebuild(partial_open_root, fingerprint="fake-v1")
    calls.clear()
    partial_answer = partial_open.query(
        partial_open_root,
        "比较预算与活动证章领取办法",
        fingerprint="fake-v1",
        answer_mode="comparison",
    )
    assert {citation.page_id for citation in partial_answer.citations} == {partial_budget_id}
    assert any("活动证章领取" in value for value in partial_answer.missing_information)
    assert not any("预算" in value for value in partial_answer.missing_information)
    assert calls and "预算上限为十八万元" in " ".join(calls[0])

    empty_open_root, empty_open_line, empty_open_project = create_test_workspace(
        tmp_path / "empty-open-workspace"
    )
    approve_page(
        empty_open_root,
        empty_open_line,
        empty_open_project,
        title="无关归档",
        body="每周存储并备份运营记录。",
    )
    empty_open_calls: list[str] = []

    class EmptyOpenAnswerer:
        def answer(self, question, passages, context=None):
            empty_open_calls.append(question)
            return GroundedAnswer(text="不应调用 answer provider。", missing_information=[])

    empty_open = QueryService(
        IndexStore(tmp_path / "empty-open-profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=EmptyOpenAnswerer(),
    )
    empty_open.rebuild(empty_open_root, fingerprint="fake-v1")
    empty_answer = empty_open.query(
        empty_open_root,
        "比较预算与活动证章领取办法",
        fingerprint="fake-v1",
        answer_mode="comparison",
    )
    assert empty_answer.citations == []
    assert empty_open_calls == []
    assert any("预算" in value for value in empty_answer.missing_information)
    assert any("活动证章领取" in value for value in empty_answer.missing_information)

    for mode in ("fact", "comparison", "plan"):
        for question in full_questions:
            calls.clear()
            answer = retrieval.query(
                root,
                question,
                fingerprint="fake-v1",
                answer_mode=mode,
            )
            cited = {citation.page_id for citation in answer.citations}
            assert cited == {budget_id, topic_id}, (question, mode, answer.model_dump())
            assert answer.missing_information == [], (question, mode, answer.model_dump())
            sent = " ".join(excerpt for call in calls for excerpt in call)
            assert "白鹭工程预算上限" in sent
            assert "活动证章领取须出示邀请函" in sent

    # With one pair absent, preserve the supported fact and report only the
    # missing subject/topic pair.
    partial_root, partial_line, partial_project = create_test_workspace(
        tmp_path / "partial-workspace"
    )
    partial_id, _ = approve_page(
        partial_root,
        partial_line,
        partial_project,
        title="白鹭预算",
        body="白鹭工程预算上限为十八万元。",
    )
    partial = QueryService(
        IndexStore(tmp_path / "partial-profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=Answerer(),
    )
    partial.rebuild(partial_root, fingerprint="fake-v1")
    calls.clear()
    answer = partial.query(
        partial_root,
        full_questions[0],
        fingerprint="fake-v1",
        answer_mode="comparison",
    )
    assert {citation.page_id for citation in answer.citations} == {partial_id}
    assert any("赤陶项目" in value for value in answer.missing_information)
    assert not any("白鹭工程" in value for value in answer.missing_information)
    assert "白鹭工程预算上限" in " ".join(excerpt for call in calls for excerpt in call)

    empty_root, empty_line, empty_project = create_test_workspace(tmp_path / "empty-workspace")
    approve_page(
        empty_root,
        empty_line,
        empty_project,
        title="朱雀储存规则",
        body="朱雀项目文件每周备份一次。",
    )
    empty_calls: list[str] = []

    class EmptyAnswerer:
        def answer(self, question, passages, context=None):
            empty_calls.append(question)
            return GroundedAnswer(text="不应调用 answer provider。", missing_information=[])

    empty = QueryService(
        IndexStore(tmp_path / "empty-profile" / "index.sqlite3"),
        FakeEmbedding(),
        answer_provider=EmptyAnswerer(),
    )
    empty.rebuild(empty_root, fingerprint="fake-v1")
    answer = empty.query(
        empty_root,
        full_questions[0],
        fingerprint="fake-v1",
        answer_mode="plan",
    )
    assert answer.citations == []
    assert empty_calls == []
    assert any("白鹭工程" in value for value in answer.missing_information)
    assert any("赤陶项目" in value for value in answer.missing_information)


def test_multi_turn_followup_skips_intermediate_pronouns_but_stops_at_new_topic(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    qinglan_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="青岚计划进度",
        body="青岚计划的预算上限为 19 万元，计划于 11 月启动。",
    )
    zhuque_id, _ = approve_page(
        root,
        line_id,
        project_id,
        title="朱雀项目进度",
        body="朱雀项目的预算上限为 12 万元，计划于 12 月启动。",
    )
    retrieval = QueryService(IndexStore(tmp_path / "profile" / "index.sqlite3"), FakeEmbedding())
    retrieval.rebuild(root, fingerprint="fake-v1")
    first = "青岚计划的预算上限是多少？"

    chained = retrieval.query(
        root,
        "它什么时候启动？",
        fingerprint="fake-v1",
        context=AnswerContext(previous_user_questions=[first, "它呢？"], answer_mode="fact"),
    )
    assert {citation.page_id for citation in chained.citations} == {qinglan_id}

    for mode in ("comparison", "plan"):
        cross_mode_followup = retrieval.query(
            root,
            "它什么时候启动？",
            fingerprint="fake-v1",
            answer_mode=mode,
            context=AnswerContext(previous_user_questions=[first], answer_mode=mode),
        )
        assert {citation.page_id for citation in cross_mode_followup.citations} == {qinglan_id}

    switched_to_known_topic = retrieval.query(
        root,
        "它什么时候启动？",
        fingerprint="fake-v1",
        context=AnswerContext(
            previous_user_questions=[
                first,
                "它呢？",
                "朱雀项目的预算上限是多少？",
            ],
            answer_mode="fact",
        ),
    )
    assert {citation.page_id for citation in switched_to_known_topic.citations} == {zhuque_id}

    switched_to_known_topic_with_followup_marker = retrieval.query(
        root,
        "它什么时候启动？",
        fingerprint="fake-v1",
        context=AnswerContext(
            previous_user_questions=[first, "那朱雀项目的预算呢？"], answer_mode="fact"
        ),
    )
    assert {
        citation.page_id for citation in switched_to_known_topic_with_followup_marker.citations
    } == {zhuque_id}

    switched = retrieval.query(
        root,
        "它什么时候启动？",
        fingerprint="fake-v1",
        context=AnswerContext(
            previous_user_questions=[first, "它呢？", "紫藤计划的预算上限是多少？"],
            answer_mode="fact",
        ),
    )
    assert switched.citations == []
    assert "没有找到能确认该对象" in switched.text

    switched_to_unknown_topic_with_followup_marker = retrieval.query(
        root,
        "它什么时候启动？",
        fingerprint="fake-v1",
        context=AnswerContext(
            previous_user_questions=[first, "那未知项目的预算呢？"], answer_mode="fact"
        ),
    )
    assert switched_to_unknown_topic_with_followup_marker.citations == []
    assert "没有找到能确认该对象" in switched_to_unknown_topic_with_followup_marker.text

    topicless_boundary = plan_retrieval(
        "它什么时候启动？",
        [first, "现在的预算情况如何？"],
        ["青岚计划", "朱雀项目"],
    )
    assert not topicless_boundary.used_history_hint
    assert topicless_boundary.unresolved_topic

    bounded_by_nonreferential_question = retrieval.query(
        root,
        "它什么时候启动？",
        fingerprint="fake-v1",
        context=AnswerContext(
            previous_user_questions=[first, "现在的预算情况如何？"],
            answer_mode="fact",
        ),
    )
    assert bounded_by_nonreferential_question.citations == []
    assert zhuque_id not in {
        citation.page_id for citation in bounded_by_nonreferential_question.citations
    }


def test_referential_followup_uses_only_latest_user_question_as_retrieval_hint(
    tmp_path: Path,
) -> None:
    root, line_id, project_id = create_test_workspace(tmp_path / "workspace")
    approve_page(
        root,
        line_id,
        project_id,
        title="青岚预算",
        body="青岚计划的预算上限是 19 万元。",
    )
    approve_page(
        root,
        line_id,
        project_id,
        title="银杏负责人",
        body="银杏项目的负责人是李明。",
    )
    embedded: list[str] = []
    reranked: list[str] = []
    answered: list[tuple[str, list[str]]] = []

    class RecordingEmbedding(FakeEmbedding):
        def embed(self, text: str, *, fingerprint: str) -> list[float]:
            embedded.append(text)
            return super().embed(text, fingerprint=fingerprint)

    class RecordingReranker:
        def rank(self, query: str, texts: list[str]) -> list[tuple[int, float]]:
            reranked.append(query)
            return [(index, 1.0) for index in range(len(texts))]

    class RecordingAnswerer:
        def answer(self, question, passages, context):
            answered.append((question, context.previous_user_questions))
            return GroundedAnswer(
                text="按当前资料回答。", source_statements=[p["excerpt"] for p in passages]
            )

    retrieval = QueryService(
        IndexStore(tmp_path / "profile" / "index.sqlite3"),
        RecordingEmbedding(),
        RecordingReranker(),
        RecordingAnswerer(),
    )
    retrieval.rebuild(root, fingerprint="fake-v1")
    previous = "青岚计划的预算上限是多少？"
    old_unrelated = "朱雀项目的负责人是谁？"

    answer = retrieval.query(
        root,
        "它呢？",
        fingerprint="fake-v1",
        context=AnswerContext(
            previous_user_questions=[old_unrelated, previous], answer_mode="fact"
        ),
    )

    assert answer.citations
    assert previous in embedded[-1] and "它呢" in embedded[-1]
    assert old_unrelated not in embedded[-1]
    assert previous in reranked[-1] and "它呢" in reranked[-1]
    assert answered[-1] == ("它呢？", [old_unrelated, previous])

    switched_topic = "银杏项目的负责人是谁？"
    retrieval.query(
        root,
        switched_topic,
        fingerprint="fake-v1",
        context=AnswerContext(
            previous_user_questions=[old_unrelated, previous], answer_mode="fact"
        ),
    )
    assert embedded[-1] == switched_topic
    assert reranked[-1] == switched_topic


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
