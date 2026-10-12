from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
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
    # The fixture includes the requested red-clay seal-handout rule, so this is a
    # complete two-pair positive control. See the original R1 harness, line 132,
    # which incorrectly expected this present fact to remain missing.
    assert not answer.missing_information, answer.model_dump()
    assert "活动证章领取须出示邀请函" in joined
    sent = "\n".join(p["excerpt"] for p in answerer.calls[0][1]) if answerer.calls else ""
    assert "白鹭工程预算上限" in sent
    assert "白鹭工程启动时间" not in sent and "赤陶项目预算" not in sent


def test_fresh_same_page_multiple_objects_partial_reports_only_absent_pair(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("白鹭工程", "双维度记录", "白鹭工程预算上限为十八万元，启动时间为九月。", None),
        ("赤陶项目", "财务", "赤陶项目预算为四万元。", None),
    ])
    answer = ask(service, root, "比较白鹭工程预算与赤陶项目的活动证章领取办法", "comparison")
    observed = {
        "citations": [c.model_dump(mode="json") for c in answer.citations],
        "missing_information": answer.missing_information,
        "provider_calls": len(answerer.calls),
        "body": answer.text,
    }
    print(observed)
    joined = excerpts(answer)
    assert "白鹭工程预算上限" in joined
    assert "活动证章领取" not in joined
    assert len(answer.missing_information) == 1 and "赤陶" in answer.missing_information[0]
    assert answerer.calls and "白鹭工程预算上限" in "\n".join(
        p["excerpt"] for p in answerer.calls[0][1]
    )
    assert "启动时间" not in "\n".join(p["excerpt"] for p in answerer.calls[0][1])


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


@pytest.mark.parametrize("mode", ["fact", "comparison", "plan"])
@pytest.mark.parametrize("reverse", [False, True])
def test_r2_new_family_exact_full_partial_and_zero_matrix(tmp_path, mode, reverse):
    a, b = "枫湾活动", "玄石展览"
    q = f"比较{b}访客设备领用办法与{a}预算" if reverse else f"比较{a}预算与{b}的访客设备领用办法"
    root, service, answerer = make_query(tmp_path, [
        (a, "经费", "枫湾活动预算上限为七万二千元。", None),
        (b, "场务", "玄石展览访客设备领用须登记姓名并归还胸牌。", None),
        (b, "无关", "玄石展览开放时间为周六。", None),
    ])
    full = ask(service, root, q, mode)
    full_text = excerpts(full)
    assert "预算上限为七万二千元" in full_text, full.model_dump()
    assert "访客设备领用须登记姓名" in full_text, full.model_dump()
    assert not full.missing_information, full.model_dump()
    assert answerer.calls and all(
        text in "\n".join(p["excerpt"] for p in answerer.calls[0][1])
        for text in ("预算上限为七万二千元", "访客设备领用须登记姓名")
    )

    # Use isolated fixtures for partial and no-evidence cases.
    partial_root, partial_service, partial_answerer = make_query(tmp_path / "partial", [
        (a, "经费", "枫湾活动预算上限为七万二千元。", None),
        (b, "无关", "玄石展览开放时间为周六。", None),
    ])
    partial = ask(partial_service, partial_root, q, mode)
    assert "枫湾活动预算上限" in excerpts(partial)
    assert "访客设备领用" not in excerpts(partial)
    assert len(partial.missing_information) == 1 and "玄石展览" in partial.missing_information[0]
    assert partial_answerer.calls and "预算上限" in "\n".join(
        p["excerpt"] for p in partial_answerer.calls[0][1]
    )
    assert "开放时间" not in "\n".join(p["excerpt"] for p in partial_answerer.calls[0][1])

    empty_root, empty_service, empty_answerer = make_query(tmp_path / "empty", [
        (a, "经费", "枫湾活动预算上限为七万二千元。", None),
        (b, "无关", "玄石展览开放时间为周六。", None),
    ])
    # The requested A pair is also unknown in this isolated corpus.
    empty = ask(empty_service, empty_root,
                "比较枫湾活动访客设备领用办法与玄石展览预算", mode)
    assert empty.citations == [] and empty.source_statements == []
    assert empty.inferences == [] and empty.advice == [] and empty.missing_information
    assert empty_answerer.calls == []


def test_r2_same_object_two_independent_topics_and_unscoped_topics(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("枫湾活动", "财务", "枫湾活动预算上限为七万二千元。", None),
        ("枫湾活动", "餐券", "枫湾活动预算之外的活动餐券登记须核对参与者姓名。", None),
        ("玄石展览", "餐券", "玄石展览活动餐券登记须核对参与者姓名。", None),
        ("榆木论坛", "餐券", "榆木论坛活动餐券登记在签到台办理。", None),
    ])
    same = ask(service, root, "枫湾活动预算和活动餐券登记办法分别是什么？", "comparison")
    assert "预算上限为七万二千元" in excerpts(same)
    assert "活动餐券登记须核对参与者姓名" in excerpts(same)
    assert not same.missing_information
    unscoped = ask(service, root, "比较预算和活动餐券登记办法", "comparison")
    assert "预算上限为七万二千元" in excerpts(unscoped)
    assert "活动餐券登记须核对参与者姓名" in excerpts(unscoped)
    assert "活动餐券登记在签到台办理" in excerpts(unscoped)
    assert not unscoped.missing_information
    assert all(len(call[1]) > 0 for call in answerer.calls)


def test_r2_two_unknown_exact_topics_zero_calls_across_modes(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("枫湾活动", "预算", "枫湾活动预算上限为七万二千元。", None),
        ("玄石展览", "排期", "玄石展览启动时间为十月。", None),
    ])
    for mode in ("fact", "comparison", "plan"):
        result = ask(service, root, "比较枫湾活动志愿者证件销毁与玄石展览临时储柜领取流程", mode)
        assert result.citations == []
        assert not result.source_statements and not result.inferences and not result.advice
        assert result.missing_information
    assert answerer.calls == []


@pytest.mark.parametrize("question", [
    "比较云岬营地与松墨展会的预算和排期",
    "比较云岬营地与松墨展会预算和排期",
])
def test_r2_shared_suffix_four_pairs_and_order_variants(tmp_path, question):
    root, service, answerer = make_query(tmp_path, [
        ("云岬营地", "预算", "云岬营地预算额度为八万六千元。", None),
        ("云岬营地", "排期", "云岬营地启动时间为上午九点。", None),
        ("松墨展会", "预算", "松墨展会预算额度为十三万元。", None),
        ("松墨展会", "排期", "松墨展会启动时间为上午十点。", None),
    ])
    answer = ask(service, root, question, "comparison")
    for evidence in ("云岬营地预算额度", "云岬营地启动时间", "松墨展会预算额度", "松墨展会启动时间"):
        assert evidence in excerpts(answer), answer.model_dump()
    assert not answer.missing_information
    sent = "\n".join(p["excerpt"] for p in answerer.calls[0][1])
    for evidence in ("云岬营地预算额度", "云岬营地启动时间", "松墨展会预算额度", "松墨展会启动时间"):
        assert evidence in sent


def test_r2_explicit_reverse_local_topics_remain_two_pairs(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("云岬营地", "预算", "云岬营地预算额度为八万六千元。", None),
        ("云岬营地", "排期", "云岬营地启动时间为上午九点。", None),
        ("松墨展会", "预算", "松墨展会预算额度为十三万元。", None),
        ("松墨展会", "排期", "松墨展会启动时间为上午十点。", None),
    ])
    answer = ask(service, root, "比较松墨展会排期与云岬营地预算", "comparison")
    assert "松墨展会启动时间" in excerpts(answer)
    assert "云岬营地预算额度" in excerpts(answer)
    assert "松墨展会预算额度" not in excerpts(answer)
    assert "云岬营地启动时间" not in excerpts(answer)
    assert not answer.missing_information
    sent = "\n".join(p["excerpt"] for p in answerer.calls[0][1])
    assert "松墨展会启动时间" in sent and "云岬营地预算额度" in sent
    assert "松墨展会预算额度" not in sent and "云岬营地启动时间" not in sent


def test_r2_same_chunk_does_not_cross_pair_and_name_budget_time_does_not_pollute(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("预算时间创作坊", "综合登记", "预算时间创作坊预算额度为两万元。云岬营地经费为八万六千元，松墨展会启动时间为十月。", None),
        ("云岬营地", "设备", "云岬营地访客设备领用要填写领用单。", None),
    ])
    answer = ask(service, root, "比较云岬营地经费与松墨展会访客设备领用办法", "comparison")
    assert "云岬营地经费为八万六千元" in excerpts(answer)
    assert "松墨展会启动时间" not in excerpts(answer)
    assert "领用单" not in excerpts(answer)
    assert any("松墨展会" in item for item in answer.missing_information)
    assert answerer.calls and "领用单" not in "\n".join(p["excerpt"] for p in answerer.calls[0][1])


def test_r2_bare_unknown_topic_has_zero_evidence_and_known_exact_remains_positive(tmp_path):
    root, service, answerer = make_query(tmp_path, [
        ("访客设备中心", "预算", "预算时间创作坊预算额度为两万元。", None),
        ("玄石展览", "设备", "玄石展览访客设备领用须签收胸牌。", None),
    ])
    unknown = ask(service, root, "活动餐券登记办法怎么安排？", "plan")
    assert unknown.citations == [] and unknown.missing_information
    assert not unknown.source_statements and not unknown.inferences and not unknown.advice
    assert answerer.calls == []
    known = ask(service, root, "玄石展览的访客设备领用办法是什么？", "fact")
    assert "签收胸牌" in excerpts(known)
    assert answerer.calls and "签收胸牌" in "\n".join(p["excerpt"] for p in answerer.calls[-1][1])
