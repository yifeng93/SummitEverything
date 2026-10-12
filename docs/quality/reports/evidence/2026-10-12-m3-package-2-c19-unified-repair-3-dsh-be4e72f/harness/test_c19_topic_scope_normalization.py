"""C19 regressions: object spans, local topics and request-shell stripping.

The shared normalization boundary must keep information-bearing qualifiers
(设备 / 年度 / 专项) inside an unfamiliar topic, must not turn a possessive 的 into
a pseudo object, and must separate an object span from the topic that follows it.
Only the request shell (question form, politeness, generic plan vocabulary) is
removed.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

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

FINGERPRINT = "c19-normalization-v1"


class RecordingAnswerer:
    """A permissive provider: an empty missing list must not erase product scope."""

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
        return [(index, 10000.0 - index) for index in reversed(range(len(texts)))]


def build_query(tmp_path: Path, pages: list[tuple[str, str, str]]):
    root = tmp_path / "workspace"
    profile = tmp_path / "profile"
    create_workspace(root, "C19 归一化", profile, "c19-normalization")
    line = create_line(root, "活动运营线", "c19-line")
    projects: dict[str, object] = {}
    for project_name, _, _ in pages:
        if project_name not in projects:
            projects[project_name] = create_project(
                root, line.id, project_name, f"c19-p-{len(projects)}"
            )
    for index, (project_name, title, body) in enumerate(pages):
        PageWriter().confirm(
            root,
            metadata={
                "id": str(uuid4()),
                "title": title,
                "role": "knowledge",
                "kind": "topic",
                "line_id": str(line.id),
                "project_id": str(projects[project_name].id),
            },
            body=body,
            confirmation_id=f"c19-confirm-{index}",
            operation_id=f"c19-write-{index}",
        )
    answerer = RecordingAnswerer()
    service = QueryService(
        IndexStore(profile / "index.sqlite3"),
        FakeEmbedding(),
        reranker=HighestScoreReranker(),
        answer_provider=answerer,
    )
    service.rebuild(root, fingerprint=FINGERPRINT)
    return root, service, answerer


def ask(service: QueryService, root: Path, question: str, mode: str):
    return service.query(root, question, fingerprint=FINGERPRINT, answer_mode=mode)


def scope(service: QueryService, root: Path, question: str):
    object_aliases: list[str] = []
    aliases = service._subject_aliases(root, load_manifest(root), object_aliases=object_aliases)
    return plan_retrieval(question, [], aliases, object_aliases=tuple(object_aliases))


def excerpts(answer) -> str:
    return "\n".join(citation.excerpt for citation in answer.citations)


def passages(answerer: RecordingAnswerer, index: int = 0) -> str:
    return "\n".join(item["excerpt"] for item in answerer.calls[index][1])


DEVICE_PAGES = [
    ("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。"),
    ("玄石展览", "场务", "玄石展览访客设备领用须登记姓名并归还胸牌。"),
]


@pytest.mark.parametrize("mode", ["fact", "comparison", "plan"])
@pytest.mark.parametrize("reverse", [False, True])
def test_device_qualifier_keeps_both_supports_in_every_mode(
    tmp_path: Path, mode: str, reverse: bool
) -> None:
    a, b = "枫湾活动", "玄石展览"
    question = (
        f"比较{b}访客设备领用办法与{a}预算" if reverse else f"比较{a}预算与{b}的访客设备领用办法"
    )
    root, service, answerer = build_query(tmp_path, DEVICE_PAGES)

    planned = scope(service, root, question)
    assert set(planned.explicit_subjects) == {a, b}
    assert dict(planned.required_pairs) == {a: "budget", b: "term:访客设备领用"}

    answer = ask(service, root, question, mode)
    text = excerpts(answer)
    assert "预算上限为七万二千元" in text, answer.model_dump()
    assert "访客设备领用须登记姓名" in text, answer.model_dump()
    assert answer.missing_information == [], answer.model_dump()
    assert answerer.calls
    sent = passages(answerer)
    assert "预算上限为七万二千元" in sent and "访客设备领用须登记姓名" in sent


def test_device_qualifier_single_object_positive(tmp_path: Path) -> None:
    b = "玄石展览"
    root, service, answerer = build_query(tmp_path, [DEVICE_PAGES[1]])
    answer = ask(service, root, f"{b}的访客设备领用办法是什么？", "fact")
    assert "访客设备领用须登记姓名" in excerpts(answer)
    assert answer.missing_information == []
    assert answerer.calls and "访客设备领用须登记姓名" in passages(answerer)


@pytest.mark.parametrize("mode", ["fact", "comparison", "plan"])
def test_device_qualifier_absence_is_reported_and_never_filled(tmp_path: Path, mode: str) -> None:
    a, b = "枫湾活动", "玄石展览"
    question = f"比较{a}预算与{b}的访客设备领用办法"
    root, service, answerer = build_query(
        tmp_path,
        [DEVICE_PAGES[0], (b, "无关", "玄石展览开放时间为周六。")],
    )

    partial = ask(service, root, question, mode)
    assert "枫湾活动预算上限" in excerpts(partial)
    assert "访客设备领用" not in excerpts(partial)
    assert len(partial.missing_information) == 1
    assert b in partial.missing_information[0]
    assert "开放时间" not in passages(answerer)

    # Both asked topics are absent from this corpus: no citation and no provider call,
    # and the second object's budget page cannot stand in for the first object's topic.
    calls_before = len(answerer.calls)
    zero = ask(service, root, f"比较{a}访客设备领用办法与{b}预算", mode)
    assert zero.citations == []
    assert zero.source_statements == [] and zero.inferences == [] and zero.advice == []
    assert zero.missing_information
    assert len(answerer.calls) == calls_before


QUALIFIER_PAGES = [
    ("玄石展览", "年度登记", "玄石展览年度访客登记办法为提前一天报备。"),
    ("玄石展览", "日常登记", "玄石展览访客登记办法为提前一天报备。"),
    ("玄石展览", "专项证章", "玄石展览专项证章领取须本人签名。"),
    ("玄石展览", "普通证章", "玄石展览证章领取须本人签名。"),
]


def test_year_qualifier_is_kept_and_a_nearer_topic_is_not_over_claimed(tmp_path: Path) -> None:
    root, service, answerer = build_query(tmp_path, QUALIFIER_PAGES)
    question = "玄石展览的年度访客登记办法是什么"

    planned = scope(service, root, question)
    assert planned.explicit_subjects == ("玄石展览",)
    assert planned.required_pairs == (("玄石展览", "term:年度访客登记"),)

    answer = ask(service, root, question, "fact")
    assert "年度访客登记办法为提前一天报备" in excerpts(answer)
    # The page that only says “访客登记” must not be presented as this topic.
    assert "玄石展览访客登记办法为提前一天报备" not in excerpts(answer)
    assert answer.missing_information == []


def test_special_qualifier_is_kept_and_never_becomes_a_pseudo_object(tmp_path: Path) -> None:
    root, service, answerer = build_query(tmp_path, QUALIFIER_PAGES)
    question = "玄石展览的专项证章领取办法是什么"

    planned = scope(service, root, question)
    assert "的专项" not in planned.explicit_subjects
    assert planned.explicit_subjects == ("玄石展览",)
    assert planned.required_pairs == (("玄石展览", "term:专项证章领取"),)

    answer = ask(service, root, question, "fact")
    assert "专项证章领取须本人签名" in excerpts(answer)
    assert "玄石展览证章领取须本人签名" not in excerpts(answer)
    assert answer.missing_information == []


def test_work_qualifier_survives_while_a_pure_plan_shell_states_no_topic(tmp_path: Path) -> None:
    root, service, _answerer = build_query(
        tmp_path, [("玄石展览", "工作证", "玄石展览访客工作证领取须本人签名。")]
    )

    # 工作 is informational inside a topic and must not be deleted globally.
    question = "玄石展览的访客工作证领取办法是什么"
    planned = scope(service, root, question)
    assert planned.required_pairs == (("玄石展览", "term:访客工作证领取"),)
    answer = ask(service, root, question, "fact")
    assert "访客工作证领取须本人签名" in excerpts(answer)
    assert answer.missing_information == []

    # A span made only of plan vocabulary still yields no exact topic.
    shell = scope(service, root, "请给白鹭工程和玄岩项目安排下一步工作")
    assert shell.dimensions == ()
    assert dict(shell.required_pairs) == {"白鹭工程": "", "玄岩项目": ""}


def test_object_span_and_request_shell_stay_separate(tmp_path: Path) -> None:
    root, service, _answerer = build_query(tmp_path, DEVICE_PAGES)

    # A compact comparison without “的” keeps both known objects and their own topics.
    planned = scope(service, root, "比较枫湾活动访客设备领用办法与玄石展览预算")
    assert dict(planned.required_pairs) == {
        "枫湾活动": "term:访客设备领用",
        "玄石展览": "budget",
    }

    # A generic work plan still strips its request shell rather than inventing a topic.
    generic = scope(service, root, "为白榆工程和玄岩项目制定下一步工作方案")
    assert generic.scope_kind == "generic_plan"
    assert generic.dimensions == ()
    assert dict(generic.required_pairs) == {"白榆工程": "", "玄岩项目": ""}


def test_unmatched_name_with_trailing_topic_keeps_the_object_span(tmp_path: Path) -> None:
    # Only 玄石展览 exists here, so 枫湾活动 is an unmatched comparison object; the
    # possessive form makes the object/topic boundary explicit.
    root, service, _answerer = build_query(tmp_path, [DEVICE_PAGES[1]])
    planned = scope(service, root, "比较枫湾活动预算与玄石展览的访客设备领用办法")
    assert dict(planned.required_pairs) == {
        "枫湾活动": "budget",
        "玄石展览": "term:访客设备领用",
    }


def test_polite_lookup_verbs_are_request_shell_not_objects(tmp_path: Path) -> None:
    root, service, _answerer = build_query(
        tmp_path, [("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。")]
    )
    for question in (
        "麻烦帮我看看枫湾活动的经费上限是多少？",
        "帮我查一下枫湾活动的预算上限。",
        "看看枫湾活动的预算",
    ):
        planned = scope(service, root, question)
        assert dict(planned.required_pairs) == {"枫湾活动": "budget"}, question
        answer = ask(service, root, question, "fact")
        assert "预算上限为七万二千元" in excerpts(answer), question
        assert answer.missing_information == [], (question, answer.missing_information)


def test_missing_wording_is_business_language_without_internal_markers(tmp_path: Path) -> None:
    root, service, _answerer = build_query(tmp_path, [DEVICE_PAGES[0]])
    answer = ask(service, root, "比较枫湾活动预算与玄石展览的访客设备领用办法", "fact")
    assert answer.missing_information
    joined = " ".join(answer.missing_information)
    assert "term:" not in joined, joined
    assert "玄石展览" in joined and "访客设备领用" in joined
    assert "预算上限为七万二千元" in excerpts(answer)


def test_limit_truncation_is_reported_as_truncation_not_absent_evidence(tmp_path: Path) -> None:
    pages = [
        ("枫湾活动", "枫湾预算", "枫湾活动预算上限为七万二千元。"),
        ("枫湾活动", "枫湾排期", "枫湾活动启动时间为十月。"),
        ("玄石展览", "玄石预算", "玄石展览预算上限为三万元。"),
        ("玄石展览", "玄石排期", "玄石展览启动时间为十一月。"),
        ("云岬营地", "云岬预算", "云岬营地预算上限为八万元。"),
        ("云岬营地", "云岬排期", "云岬营地启动时间为十二月。"),
    ]
    root, service, _answerer = build_query(tmp_path, pages)
    question = "比较枫湾活动、玄石展览和云岬营地的预算和排期。"

    truncated = service.query(
        root, question, fingerprint=FINGERPRINT, answer_mode="comparison", limit=5
    )
    assert len(truncated.citations) == 5
    # A truncation shortfall must not be presented as absent knowledge.
    assert not [
        item for item in truncated.missing_information if "缺少" in item and "依据" in item
    ], truncated.missing_information
    notice = next((item for item in truncated.missing_information if "条数已达上限" in item), None)
    assert notice is not None, truncated.missing_information
    assert any(name in notice for name in ("枫湾活动", "玄石展览", "云岬营地")), notice

    # Without truncation the answer keeps only real scope gaps.
    complete = service.query(
        root, question, fingerprint=FINGERPRINT, answer_mode="comparison", limit=12
    )
    assert complete.missing_information == []
    assert len({citation.page_id for citation in complete.citations}) == 6


def test_unregistered_names_starting_with_request_words_survive(tmp_path: Path) -> None:
    root, service, _answerer = build_query(
        tmp_path,
        [
            ("松墨展会", "预算", "松墨展会预算上限为七万元。"),
            ("榆木论坛", "无关", "榆木论坛开放时间为周六。"),
        ],
    )
    # 总结报告 is an unregistered object name: stripping the request verb from a
    # standalone candidate would silently rename it to 报告.
    planned = scope(service, root, "比较总结报告与松墨展会的预算")
    assert "总结报告" in planned.explicit_subjects, planned.explicit_subjects
    assert "报告" not in planned.explicit_subjects, planned.explicit_subjects

    answer = ask(service, root, "比较总结报告与松墨展会的预算", "comparison")
    assert "松墨展会预算上限为七万元" in excerpts(answer)
    assert any("总结报告" in item for item in answer.missing_information), (
        answer.missing_information
    )
