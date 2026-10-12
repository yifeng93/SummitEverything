from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from summit_everything.domain.content import RetrievalPurpose
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.llm import GroundedAnswer
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import create_line, create_project, create_workspace
from summit_everything.workspace.writer import PageWriter


class SpyAnswerer:
    def __init__(self, *, claim_complete: bool = False) -> None:
        self.calls: list[tuple[str, list[dict[str, str]]]] = []
        self.claim_complete = claim_complete

    def answer(self, question, passages, context=None):
        self.calls.append((question, passages))
        return GroundedAnswer(
            text="完整比较已经完成" if self.claim_complete else "根据提供的材料回答。",
            missing_information=[],
            inferences=["推断"],
            advice=["建议"],
        )


class HighScoreReranker:
    def rank(self, query, texts):
        return [(i, 999.0 - i) for i in reversed(range(len(texts)))]


def make_query(tmp_path: Path, pages: list[tuple[str, str, str]], *, high_score=False, complete=False):
    root = tmp_path / "workspace"
    profile = tmp_path / "profile"
    create_workspace(root, "Holdout", profile, "holdout")
    line = create_line(root, "综合运营线", "line")
    projects = {}
    for project_name, _, _ in pages:
        if project_name not in projects:
            projects[project_name] = create_project(root, line.id, project_name, f"p-{len(projects)}")
    for project_name, title, body in pages:
        metadata = {
            "id": str(uuid4()), "title": title, "role": "knowledge", "kind": "topic",
            "line_id": str(line.id), "project_id": str(projects[project_name].id),
        }
        PageWriter().confirm(
            root, metadata=metadata, body=body,
            confirmation_id=f"confirm-{project_name}-{title}", operation_id=f"write-{project_name}-{title}",
        )
    spy = SpyAnswerer(claim_complete=complete)
    service = QueryService(
        IndexStore(profile / "index.sqlite3"), FakeEmbedding(),
        reranker=HighScoreReranker() if high_score else None,
        answer_provider=spy,
    )
    service.rebuild(root, fingerprint="qa-holdout-v1")
    return root, service, spy


def ask(service, root, question, mode):
    return service.query(root, question, fingerprint="qa-holdout-v1", answer_mode=mode)


def test_h01_zero_scope_never_leaks_broadly_matching_pages_or_calls_provider(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("青砾工程", "预算材料", "青砾工程预算上限为十四万元。"),
        ("琥珀项目", "排期材料", "琥珀项目启动时间为九月。"),
    ], high_score=True, complete=True)
    for mode in ("fact", "comparison", "plan"):
        answer = ask(service, root, "比较青砾工程与琥珀项目的纸伞保管办法", mode)
        assert answer.citations == [], (mode, answer.model_dump())
        assert answer.source_statements == [] and answer.inferences == [] and answer.advice == []
        assert answer.missing_information and "纸伞" in " ".join(answer.missing_information)
        assert "缓存" not in " ".join(answer.missing_information)
    assert spy.calls == []


def test_h02_partial_unknown_subject_cannot_be_filled_by_second_page_or_third_project(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("白榆工程", "白榆预算1", "白榆工程已确认预算为二十万元。"),
        ("白榆工程", "白榆预算2", "白榆工程预算上限为二十万元，已批准。"),
        ("赤松工程", "赤松预算", "赤松工程预算为七万元。"),
    ], high_score=True, complete=True)
    answer = ask(service, root, "比较白榆工程与玄岩项目的预算", "comparison")
    assert answer.citations and all("白榆" in c.excerpt for c in answer.citations)
    assert any("玄岩" in item for item in answer.missing_information), answer.model_dump()
    assert "完整比较已经完成" not in answer.text
    assert len(spy.calls) == 1
    sent = "\n".join(p["excerpt"] for p in spy.calls[0][1])
    assert "赤松" not in sent and "玄岩" not in sent


def test_h03_pair_scope_does_not_cross_assign_subject_or_dimension(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("白榆工程", "白榆预算", "白榆工程预算上限为二十万元。"),
        ("玄岩项目", "玄岩排期", "玄岩项目启动时间为十二月。"),
        ("玄岩项目", "玄岩预算", "玄岩项目预算为八万元。"),
        ("白榆工程", "白榆排期", "白榆工程启动时间为五月。"),
    ], high_score=True)
    answer = ask(service, root, "白榆工程预算与玄岩项目排期", "comparison")
    joined = "\n".join(c.excerpt for c in answer.citations)
    assert "白榆工程预算" in joined and "玄岩项目启动时间" in joined, answer.model_dump()
    assert "白榆工程启动时间" not in joined and "玄岩项目预算" not in joined
    assert not answer.missing_information
    sent = "\n".join(p["excerpt"] for p in spy.calls[0][1])
    assert "白榆工程预算" in sent and "玄岩项目启动时间" in sent
    assert "白榆工程启动时间" not in sent and "玄岩项目预算" not in sent


def test_h04_metadata_owner_does_not_turn_other_body_dimension_into_evidence(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("白榆工程", "综合事实", "白榆工程预算上限为二十万元。白榆工程启动时间为五月。"),
        ("玄岩项目", "玄岩排期", "玄岩项目启动时间为十二月。"),
    ], high_score=True)
    answer = ask(service, root, "白榆工程的培训签到办法是什么", "plan")
    assert answer.citations == [] and not spy.calls
    assert answer.source_statements == [] and answer.advice == []
    assert answer.missing_information


def test_h05_general_topic_and_known_plan_remain_answerable_with_supported_passages(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("白榆工程", "预算记录", "白榆工程预算上限为二十万元。"),
        ("玄岩项目", "预算记录", "玄岩项目预算已批准八万元。"),
    ])
    broad = ask(service, root, "汇总预算资料", "fact")
    plan = ask(service, root, "为白榆工程和玄岩项目制定下一步工作方案", "plan")
    assert broad.citations and len(broad.citations) >= 2
    assert plan.citations and {"白榆工程", "玄岩项目"} <= {name for c in plan.citations for name in ("白榆工程", "玄岩项目") if name in c.excerpt}
    assert plan.advice or "方案" in plan.text or "根据提供" in plan.text
    assert len(spy.calls) == 2


def test_h06_unknown_object_followup_does_not_return_to_previous_topic(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("白榆工程", "白榆预算", "白榆工程预算上限为二十万元。"),
    ])
    first = ask(service, root, "白榆工程的预算是多少？", "fact")
    second = service.query(
        root, "它的金额呢？", fingerprint="qa-holdout-v1", answer_mode="fact",
        context=__import__("summit_everything.local.answer_context", fromlist=["AnswerContext"]).AnswerContext(
            previous_user_questions=["白榆工程的预算是多少？", "玄岩项目的储存规程是什么？"],
        ),
    )
    assert first.citations
    assert second.citations == []
    assert any("玄岩" in missing for missing in second.missing_information), second.model_dump()


def test_h07_accepted_alias_and_no_de_phrase_still_retrieve_positive_fact(tmp_path):
    root = tmp_path / "workspace"
    profile = tmp_path / "profile"
    create_workspace(root, "Alias Holdout", profile, "alias")
    line = create_line(root, "运营线", "alias-line")
    project = create_project(root, line.id, "正式项目长名称", "alias-project")
    metadata = {
        "id": str(uuid4()), "title": "年度额度", "role": "knowledge", "kind": "topic",
        "line_id": str(line.id), "project_id": str(project.id), "aliases": ["青榆"],
    }
    PageWriter().confirm(
        root, metadata=metadata, body="青榆计划预算额度已确认为三十万元。",
        confirmation_id="alias-confirm-budget", operation_id="alias-write-budget",
    )
    spy = SpyAnswerer()
    service = QueryService(
        IndexStore(profile / "index.sqlite3"), FakeEmbedding(), answer_provider=spy,
    )
    service.rebuild(root, fingerprint="qa-holdout-v1")
    answer = ask(service, root, "麻烦查青榆预算额度", "fact")
    assert answer.citations and "三十万元" in answer.citations[0].excerpt
    assert spy.calls and "三十万元" in spy.calls[0][1][0]["excerpt"]
    assert not answer.missing_information


def test_h08_unknown_named_and_general_topic_is_not_satisfied_by_other_dimensions(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("预算时间专项", "综合安排", "预算时间专项已批准预算五万元，启动时间为六月。"),
    ], high_score=True, complete=True)
    questions = [
        ("预算时间专项的培训签到办法是什么", "fact"),
        ("为预算时间专项制定培训签到流程", "plan"),
        ("比较预算时间专项培训签到安排", "comparison"),
        ("培训签到办法怎么安排", "plan"),
    ]
    for question, mode in questions:
        answer = ask(service, root, question, mode)
        assert answer.citations == [], (question, answer.model_dump())
        assert not answer.source_statements and not answer.inferences and not answer.advice
        assert answer.missing_information, (question, answer.model_dump())
    assert spy.calls == []


def test_h09_named_object_with_dimension_words_does_not_lend_them_to_other_topic(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("预算时间工作坊", "预算记录", "预算时间工作坊预算已批五万元，开会时间是六月。"),
        ("预算时间工作坊", "培训记录", "培训签到须现场登记并核验姓名。"),
    ], high_score=True)
    answer = ask(service, root, "预算时间工作坊签到办法是什么", "fact")
    assert answer.citations and all("培训签到" in c.excerpt for c in answer.citations)
    assert all("预算已批" not in c.excerpt and "开会时间" not in c.excerpt for c in answer.citations)
    assert spy.calls and all("预算已批" not in p["excerpt"] for p in spy.calls[0][1])


def test_h10_open_ended_plan_remains_a_positive_general_retrieval_path(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("白榆工程", "项目材料", "已确认资料包括预算上限二十万元，待补齐供应商报价。"),
        ("玄岩项目", "项目材料", "已确认资料包括启动时间十二月，待补齐人员安排。"),
    ])
    answer = ask(service, root, "比较预算和排期，并制定下一步方案", "plan")
    assert answer.citations
    assert spy.calls
    assert answer.advice or answer.inferences or "根据提供" in answer.text


def test_h11_unknown_topic_without_named_object_does_not_take_unrelated_pages(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("白榆工程", "资金情况", "白榆工程预算上限为二十万元。"),
        ("玄岩项目", "进度情况", "玄岩项目启动时间为十二月。"),
    ], high_score=True, complete=True)
    answer = ask(service, root, "培训签到办法怎么安排", "plan")
    assert answer.citations == []
    assert not answer.source_statements and not answer.inferences and not answer.advice
    assert answer.missing_information
    assert spy.calls == []


def test_h12_schedule_page_title_does_not_turn_broad_dimension_into_subject(tmp_path):
    root, service, spy = make_query(tmp_path, [
        ("白榆工程", "预算汇总", "白榆工程预算上限为二十万元。"),
        ("玄岩项目", "排期", "玄岩项目启动时间为十二月。"),
    ], high_score=True)
    answer = ask(service, root, "比较预算和排期建议", "comparison")
    excerpts = "\n".join(c.excerpt for c in answer.citations)
    assert "白榆工程预算" in excerpts and "玄岩项目启动时间" in excerpts, answer.model_dump()
    assert not answer.missing_information, answer.model_dump()
    sent = "\n".join(p["excerpt"] for p in spy.calls[0][1])
    assert "白榆工程预算" in sent and "玄岩项目启动时间" in sent
