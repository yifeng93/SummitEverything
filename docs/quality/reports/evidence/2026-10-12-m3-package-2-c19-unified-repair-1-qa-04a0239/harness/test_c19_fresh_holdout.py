from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.integrations.llm import GroundedAnswer
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import create_line, create_project, create_workspace
from summit_everything.workspace.writer import PageWriter


class RecordingAnswerer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def answer(self, question, passages, context=None):
        self.calls.append((question, passages))
        return GroundedAnswer(
            text="依据所给材料。",
            missing_information=[],
            inferences=["推断"],
            advice=["建议"],
        )


class HighestScoreReranker:
    def rank(self, query, texts):
        return [(i, 10000.0 - i) for i in reversed(range(len(texts)))]


def make_query(tmp_path: Path, pages: list[tuple[str, str, str, list[str] | None]]):
    root = tmp_path / "workspace"
    profile = tmp_path / "profile"
    create_workspace(root, "Fresh Holdout", profile, "fresh-holdout")
    line = create_line(root, "活动运营线", "fresh-line")
    projects = {}
    for project_name, _, _, _ in pages:
        if project_name not in projects:
            projects[project_name] = create_project(root, line.id, project_name, f"fresh-p-{len(projects)}")
    for project_name, title, body, aliases in pages:
        metadata = {
            "id": str(uuid4()),
            "title": title,
            "role": "knowledge",
            "kind": "topic",
            "line_id": str(line.id),
            "project_id": str(projects[project_name].id),
        }
        if aliases:
            metadata["aliases"] = aliases
        PageWriter().confirm(
            root,
            metadata=metadata,
            body=body,
            confirmation_id=f"fresh-confirm-{project_name}-{title}",
            operation_id=f"fresh-write-{project_name}-{title}",
        )
    answerer = RecordingAnswerer()
    service = QueryService(
        IndexStore(profile / "index.sqlite3"),
        FakeEmbedding(),
        reranker=HighestScoreReranker(),
        answer_provider=answerer,
    )
    service.rebuild(root, fingerprint="fresh-holdout-v1")
    return root, service, answerer


def ask(service, root, question: str, mode: str):
    return service.query(root, question, fingerprint="fresh-holdout-v1", answer_mode=mode)


def excerpts(answer) -> str:
    return "\n".join(c.excerpt for c in answer.citations)


def test_fresh_unknown_named_topic_fails_closed_across_modes(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("经费时间研究坊", "基础安排", "经费时间研究坊预算上限为九万元，启动时间为十月。", None),
        ("橡果活动", "活动计划", "橡果活动预算为三万元，启动时间为十一月。", None),
    ])
    questions = [
        ("麻烦查经费时间研究坊的访客证件注销流程", "fact"),
        ("比较经费时间研究坊访客证件注销和橡果活动证章领取办法", "comparison"),
        ("请为经费时间研究坊制定访客证件注销方案", "plan"),
        ("访客证件注销办法怎么安排", "plan"),
    ]
    for question, mode in questions:
        answer = ask(service, root, question, mode)
        assert answer.citations == [], (question, answer.model_dump())
        assert not answer.source_statements and not answer.inferences and not answer.advice
        assert answer.missing_information, (question, answer.model_dump())
    assert answerer.calls == []


def test_fresh_unknown_topic_with_exact_body_support_is_answerable(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("经费时间研究坊", "访客说明", "访客证件注销须交回实体卡，并在登记簿签名。", None),
        ("经费时间研究坊", "预算说明", "预算上限为九万元，启动时间为十月。", None),
    ])
    answer = ask(service, root, "经费时间研究坊访客证件注销流程是什么？", "fact")
    text = excerpts(answer)
    assert answer.citations and "交回实体卡" in text
    assert "预算上限" not in text and "启动时间" not in text
    assert answerer.calls and "交回实体卡" in "\n".join(p["excerpt"] for p in answerer.calls[0][1])
    assert not answer.missing_information


def test_fresh_alias_match_does_not_supply_unasked_topic(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("正式项目名称", "一般事项", "青榆项目预算为六万元，启动时间为十月。", ["青榆"]),
    ])
    answer = ask(service, root, "青榆的访客证件注销流程是什么？", "fact")
    assert answer.citations == []
    assert answer.missing_information
    assert not answerer.calls


def test_fresh_same_page_multiple_objects_do_not_cross_pair_dimensions(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("白鹭工程", "双维度记录", "白鹭工程预算上限为十八万元，启动时间为九月。", None),
        ("赤陶项目", "活动安排", "赤陶项目活动证章领取须出示邀请函。", None),
        ("赤陶项目", "财务", "赤陶项目预算为四万元。", None),
    ])
    answer = ask(service, root, "比较白鹭工程预算与赤陶项目的活动证章领取办法", "comparison")
    joined = excerpts(answer)
    assert "白鹭工程预算上限" in joined, answer.model_dump()
    assert "白鹭工程启动时间" not in joined
    assert "赤陶项目预算" not in joined
    assert any("赤陶" in item for item in answer.missing_information), answer.model_dump()
    sent = "\n".join(p["excerpt"] for p in answerer.calls[0][1]) if answerer.calls else ""
    assert "白鹭工程预算上限" in sent
    assert "白鹭工程启动时间" not in sent and "赤陶项目预算" not in sent


def test_fresh_mixed_topics_are_not_collapsed_into_one_dimension(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("白鹭工程", "预算记录", "白鹭工程预算上限为十八万元。", None),
        ("赤陶项目", "活动安排", "赤陶项目活动证章领取须出示邀请函。", None),
    ])
    answers = []
    for mode in ("fact", "comparison", "plan"):
        answer = ask(
            service,
            root,
            "比较白鹭工程预算与赤陶项目的活动证章领取办法",
            mode,
        )
        observed = {
            "mode": mode,
            "citations": [citation.model_dump(mode="json") for citation in answer.citations],
            "missing_information": answer.missing_information,
            "provider_calls": len(answerer.calls),
            "body": answer.text,
        }
        print(observed)
        answers.append(answer)
    assert all(
        answer.citations
        and "白鹭工程预算上限" in excerpts(answer)
        and "活动证章领取须出示邀请函" in excerpts(answer)
        and not answer.missing_information
        for answer in answers
    )
    sent = "\n".join(p["excerpt"] for _, passages in answerer.calls for p in passages)
    assert "白鹭工程预算上限" in sent
    assert "活动证章领取须出示邀请函" in sent


def test_fresh_reversed_mixed_topics_still_keep_the_supported_pair(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("白鹭工程", "预算记录", "白鹭工程预算上限为十八万元。", None),
        ("赤陶项目", "活动安排", "赤陶项目活动证章领取须出示邀请函。", None),
    ])
    answer = ask(
        service,
        root,
        "比较赤陶项目的活动证章领取办法与白鹭工程预算",
        "comparison",
    )
    actual = {
        "citations": [citation.model_dump(mode="json") for citation in answer.citations],
        "missing_information": answer.missing_information,
        "provider_calls": len(answerer.calls),
        "body": answer.text,
    }
    print(actual)
    assert answer.citations and len(answer.citations) == 2, actual


def test_fresh_shared_budget_schedule_pairing_remains_complete(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("白鹭工程", "预算", "白鹭工程预算上限为十八万元。", None),
        ("白鹭工程", "排期", "白鹭工程启动时间为九月。", None),
        ("赤陶项目", "预算", "赤陶项目预算为四万元。", None),
        ("赤陶项目", "排期", "赤陶项目启动时间为十一月。", None),
    ])
    answer = ask(service, root, "比较白鹭工程与赤陶项目的预算和排期", "comparison")
    joined = excerpts(answer)
    expected = ("白鹭工程预算上限", "白鹭工程启动时间", "赤陶项目预算", "赤陶项目启动时间")
    assert all(item in joined for item in expected), answer.model_dump()
    assert not answer.missing_information, answer.model_dump()
    assert answerer.calls and all(
        item in "\n".join(p["excerpt"] for p in answerer.calls[0][1]) for item in expected
    )


def test_fresh_exact_schedule_title_and_open_attributes_stay_usable(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("白鹭工程", "财务汇总", "白鹭工程预算上限为十八万元。", None),
        ("赤陶项目", "排期", "赤陶项目启动时间为九月，活动地址为云杉路八号。", None),
    ])
    broad = ask(service, root, "麻烦比较预算和排期建议", "comparison")
    assert "白鹭工程预算上限" in excerpts(broad)
    assert "赤陶项目启动时间" in excerpts(broad)
    assert not broad.missing_information

    address = ask(service, root, "活动地址在哪里？", "fact")
    assert "云杉路八号" in excerpts(address), address.model_dump()

    plan = ask(service, root, "请给白鹭工程和赤陶项目安排下一步工作", "plan")
    assert plan.citations and len(plan.citations) >= 2
    assert answerer.calls
