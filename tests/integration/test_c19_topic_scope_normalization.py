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
from summit_everything.retrieval.planner import plan_retrieval, supported_dimensions
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import (
    create_line,
    create_project,
    create_workspace,
    load_manifest,
)
from summit_everything.workspace.reader import list_pages
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


def build_query(
    tmp_path: Path,
    pages: list[tuple[str, str, str]],
    *,
    line_name: str = "活动运营线",
):
    root = tmp_path / "workspace"
    profile = tmp_path / "profile"
    create_workspace(root, "C19 归一化", profile, "c19-normalization")
    line = create_line(root, line_name, "c19-line")
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


def test_explicit_date_or_clock_value_supports_only_a_co_located_schedule_action() -> None:
    schedule_action = ("schedule&term:举行",)
    assert (
        supported_dimensions(
            "纸飞机读书会定于 2026 年 10 月 30 日 14:00 至 16:00 举行。",
            schedule_action,
        )
        == schedule_action
    )
    assert supported_dimensions("场地最晚 16:30 清场。", ("schedule&term:清场",)) == (
        "schedule&term:清场",
    )
    assert (
        supported_dimensions(
            "纸飞机读书会定于2026年10月30日14:00至16:00举行。",
            ("schedule&term:举行&term:人数",),
        )
        == ()
    )
    assert supported_dimensions("项目排期确认在十一月开始。", ("schedule",)) == ("schedule",)

    # A date alone cannot establish a missing action or a different topic.
    assert supported_dimensions("活动编号为 2026 年 10 月 30 日。", schedule_action) == ()
    assert supported_dimensions("活动是否举行尚未确定。", schedule_action) == ()
    assert supported_dimensions("项目编号为 2026 年 10 月 30 日。", ("budget",)) == ()
    assert supported_dimensions("仅有数值 2026 年 10 月 30 日。", ("schedule",)) == ()
    assert supported_dimensions("活动将在 2026 年 13 月 40 日举行。", schedule_action) == ()
    assert supported_dimensions("活动定于 2026-10/30 举行。", schedule_action) == ()
    assert supported_dimensions("活动将在 116:300 举行。", ("schedule&term:举行",)) == ()


def test_explicit_date_covers_asked_event_time_without_weakening_topic_gaps(tmp_path: Path) -> None:
    root, service, _answerer = build_query(
        tmp_path,
        [
            (
                "纸飞机读书会",
                "活动安排",
                "纸飞机读书会定于2026年10月30日14:00至16:00举行，预计参加人数为 24 人。",
            ),
            (
                "纸飞机读书会",
                "清场规则",
                "活动结束后由两名志愿者清点六本签到册。场地最晚 16:30 清场。",
            ),
        ],
    )
    event = ask(service, root, "纸飞机读书会何时举行，人数上限是多少？", "fact")
    assert len(event.citations) == 1
    assert event.missing_information == []

    cleanup = ask(service, root, "纸飞机读书会的清场时间和清场志愿者人数是多少？", "fact")
    assert len(cleanup.citations) == 1
    assert any("清场志愿者人数" in item for item in cleanup.missing_information)
    assert not any("清场时间" in item or "清场依据" in item for item in cleanup.missing_information)


@pytest.mark.parametrize(
    "body",
    [
        "纸飞机读书会活动编号为2026-10-30且活动是否举行尚未确定。",
        "纸飞机读书会活动编号为2026-02-31且活动是否举行尚未确定。",
        "纸飞机读书会定于2026-02-31举行。",
    ],
)
def test_identifier_or_impossible_date_does_not_prove_event_schedule(
    tmp_path: Path, body: str
) -> None:
    root, service, answerer = build_query(
        tmp_path,
        [("纸飞机读书会", "活动记录", body)],
    )
    answer = ask(service, root, "纸飞机读书会何时举行？", "fact")
    assert answer.citations == []
    assert any("举行" in item for item in answer.missing_information)
    assert answerer.calls == []


def test_unrelated_date_does_not_cover_an_unconfirmed_schedule_action(tmp_path: Path) -> None:
    root, service, answerer = build_query(
        tmp_path,
        [
            (
                "纸飞机读书会",
                "活动记录",
                "活动编号为 2026 年 10 月 30 日。活动是否举行尚未确定。",
            )
        ],
    )
    answer = ask(service, root, "纸飞机读书会何时举行？", "fact")
    assert answer.citations == []
    assert any("举行" in item for item in answer.missing_information)
    assert answerer.calls == []


def excerpts(answer) -> str:
    return "\n".join(citation.excerpt for citation in answer.citations)


def passages(answerer: RecordingAnswerer, index: int = 0) -> str:
    return "\n".join(item["excerpt"] for item in answerer.calls[index][1])


def test_single_subject_carries_to_later_sentence_in_same_paragraph(tmp_path: Path) -> None:
    body = "合成事实：活动于 2026-10-30 14:00 至 16:00，最多 24 人。集合地点：东门合成大厅。"
    root, service, answerer = build_query(
        tmp_path,
        [("纸飞机读书会", "合成规则 dcb1aa2a", body)],
        line_name="合成验收主线",
    )

    planned = scope(service, root, "活动的集合地点是什么？")
    assert planned.explicit_subjects == ("活动",)
    assert planned.required_pairs == (("活动", "term:集合地点"),)

    answer = ask(service, root, "活动的集合地点是什么？", "fact")
    assert len(answer.citations) == 1, answer.model_dump()
    assert "集合地点：东门合成大厅" in excerpts(answer)
    assert answerer.calls


def test_single_subject_cannot_carry_across_competing_object_in_same_paragraph(
    tmp_path: Path,
) -> None:
    root, service, answerer = build_query(
        tmp_path,
        [
            (
                "纸飞机读书会",
                "合成记录",
                "活动于 2026-10-30 举行。赤陶活动集合地点：西门大厅。",
            ),
            ("赤陶活动", "赤陶活动地点", "赤陶活动集合地点：西门大厅。"),
        ],
        line_name="合成验收主线",
    )

    answer = ask(service, root, "活动的集合地点是什么？", "fact")
    assert answer.citations == [], answer.model_dump()
    assert answerer.calls == []


@pytest.mark.parametrize(
    "body",
    [
        "活动于 2026-10-30 举行。\n\n集合地点：东门大厅。",
        "- 活动于 2026-10-30 举行。\n- 集合地点：东门大厅。",
        "活动于 2026-10-30 举行。\n### 地点记录\n集合地点：东门大厅。",
        "| 项目 | 说明 |\n|---|---|\n| 活动 | 2026-10-30 举行 |\n| 集合地点 | 东门大厅 |",
    ],
    ids=["separate-paragraphs", "separate-list-items", "new-heading", "separate-table-rows"],
)
def test_single_subject_does_not_carry_across_paragraph_or_list_item(
    tmp_path: Path, body: str
) -> None:
    root, service, answerer = build_query(
        tmp_path,
        [("纸飞机读书会", "合成记录", body)],
        line_name="合成验收主线",
    )

    answer = ask(service, root, "活动的集合地点是什么？", "fact")
    assert answer.citations == [], answer.model_dump()
    assert answerer.calls == []


def test_two_subject_topics_keep_their_own_scope_within_one_paragraph(tmp_path: Path) -> None:
    body = "枫湾活动预算上限为七万二千元。玄石展览访客设备领用须登记姓名。"
    root, service, answerer = build_query(
        tmp_path,
        [
            ("枫湾活动", "经费与访客设备", body),
            ("玄石展览", "访客设备", "玄石展览访客设备领用须登记姓名。"),
        ],
        line_name="合成验收主线",
    )
    question = "比较枫湾活动预算与玄石展览的访客设备领用办法"

    planned = scope(service, root, question)
    assert set(planned.required_pairs) == {
        ("枫湾活动", "budget"),
        ("玄石展览", "term:访客设备领用"),
    }

    answer = ask(service, root, question, "comparison")
    text = excerpts(answer)
    assert "预算上限为七万二千元" in text, answer.model_dump()
    assert "访客设备领用须登记姓名" in text, answer.model_dump()
    assert answer.missing_information == []
    assert answerer.calls


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


@pytest.mark.parametrize(
    ("project", "topic", "positive_body", "near_miss_body", "question"),
    [
        (
            "白萤会展",
            "年度访客信息登记",
            "白萤会展年度访客信息登记须核验身份。",
            "白萤会展年度访客登记须核验身份。",
            "白萤会展的年度访客信息登记办法是什么？",
        ),
        (
            "松墨展会",
            "访客资料提交",
            "松墨展会访客资料提交须附来源清单。",
            "松墨展会访客提交须附来源清单。",
            "松墨展会的访客资料提交办法是什么？",
        ),
    ],
)
@pytest.mark.parametrize("mode", ["fact", "comparison", "plan"])
def test_information_words_inside_topics_are_not_global_shell(
    tmp_path: Path,
    project: str,
    topic: str,
    positive_body: str,
    near_miss_body: str,
    question: str,
    mode: str,
) -> None:
    root, service, answerer = build_query(tmp_path, [(project, topic, positive_body)])
    planned = scope(service, root, question)
    assert planned.required_pairs == ((project, f"term:{topic}"),)
    answer = ask(service, root, question, mode)
    assert positive_body.rstrip("。").split("须")[0] in excerpts(answer)
    assert answer.missing_information == []
    assert answerer.calls and positive_body.rstrip("。").split("须")[0] in passages(answerer)

    root, service, answerer = build_query(
        tmp_path / "near-miss", [(project, topic, near_miss_body)]
    )
    answer = ask(service, root, question, mode)
    assert answer.citations == [], answer.model_dump()
    assert answer.missing_information and project in answer.missing_information[0]
    assert topic in answer.missing_information[0]
    assert answerer.calls == []


@pytest.mark.parametrize("mode", ["fact", "comparison", "plan"])
def test_plan_work_scheme_suffix_is_request_shell_but_compound_topic_survives(
    tmp_path: Path, mode: str
) -> None:
    project = "白萤会展"
    pages = [
        (project, "登记", "白萤会展年度访客信息登记须核验身份。"),
        (project, "工作证", "白萤会展访客工作证领取须本人签名。"),
    ]
    root, service, answerer = build_query(tmp_path, pages)
    query = "为白萤会展制定年度访客信息登记工作方案"
    planned = scope(service, root, query)
    assert planned.required_pairs == ((project, "term:年度访客信息登记"),)
    answer = ask(service, root, query, mode)
    assert "年度访客信息登记须核验身份" in excerpts(answer)
    assert answer.missing_information == []
    assert answerer.calls

    compound = "白萤会展的访客工作证领取办法是什么"
    compound_plan = scope(service, root, compound)
    assert compound_plan.required_pairs == ((project, "term:访客工作证领取"),)
    compound_answer = ask(service, root, compound, "fact")
    assert "访客工作证领取须本人签名" in excerpts(compound_answer)


@pytest.mark.parametrize("mode", ["fact", "comparison", "plan"])
def test_limit_notice_does_not_replace_real_absence_or_invent_omitted_support(
    tmp_path: Path, mode: str
) -> None:
    pages = [
        ("云岬营地", f"预算记录{i}", f"云岬营地预算额度第{i}项为{i * 10000 + 30000}元。")
        for i in range(1, 7)
    ] + [("汀屿计划", "流程记录", "汀屿计划访客登记须由前台核验。")]
    root, service, answerer = build_query(tmp_path, pages)
    question = "比较云岬营地预算与汀屿计划的排期"
    answer = service.query(root, question, fingerprint=FINGERPRINT, answer_mode=mode, limit=5)
    assert len(answer.citations) == 5
    assert any("汀屿计划" in item and "缺少" in item for item in answer.missing_information)
    # The unquoted sixth budget passage is real current support for an already
    # covered pair; a neutral cap note may report that omission without claiming
    # the independently missing B schedule might exist.
    assert any("上限" in item for item in answer.missing_information)
    assert "排期" not in passages(answerer)

    complete = service.query(root, question, fingerprint=FINGERPRINT, answer_mode=mode, limit=20)
    assert any("汀屿计划" in item and "缺少" in item for item in complete.missing_information)
    assert not any("上限" in item for item in complete.missing_information)


def test_candidate_budget_cap_requires_current_in_scope_support(tmp_path: Path) -> None:
    # Twenty high-overlap but out-of-scope chunks must not make a genuinely
    # absent requested pair look like it was merely omitted by the candidate cap.
    pages = [
        ("岚桥计划", f"预算记录{i}", f"岚桥计划预算额度第{i}项为{i * 10000}元。")
        for i in range(1, 24)
    ] + [("汀屿计划", "流程记录", "汀屿计划访客登记须由前台核验。")]
    root, service, _answerer = build_query(tmp_path, pages)
    answer = ask(service, root, "比较岚桥计划的预算与汀屿计划的排期", "comparison")
    assert any("汀屿计划" in item and "缺少" in item for item in answer.missing_information)
    assert not any("候选" in item and "汀屿计划" in item for item in answer.missing_information)


def test_hybrid_fts_can_surface_support_beyond_dense_top_twenty(
    tmp_path: Path,
) -> None:
    pages = [
        ("岚桥计划", f"预算记录{i}", f"岚桥计划预算额度第{i}项为{i * 10000}元。")
        for i in range(1, 24)
    ] + [("汀屿计划", "排期", "汀屿计划排期为十一月。")]
    root, service, _answerer = build_query(tmp_path, pages)
    question = "比较岚桥计划的预算与汀屿计划的排期"
    plan = scope(service, root, question)
    generation = service.store.active_generation(load_manifest(root).workspace_id)
    assert generation is not None
    query_vector = service.embedding.embed(plan.search_question, fingerprint=FINGERPRINT)
    dense, lexical = service.store.search(generation, query_vector, plan.search_question, limit=24)
    target_page = next(page for page in list_pages(root) if page.metadata["title"] == "排期")
    target_dense_rank = next(
        rank for rank, item in enumerate(dense, start=1) if item["page_id"] == target_page.page_id
    )
    assert target_dense_rank > 20
    assert lexical[0]["page_id"] == target_page.page_id
    answer = service.query(
        root,
        question,
        fingerprint=FINGERPRINT,
        answer_mode="comparison",
        limit=24,
    )
    assert "汀屿计划排期" in excerpts(answer)
    assert not any("汀屿计划" in item and "候选" in item for item in answer.missing_information)
    assert not any("汀屿计划" in item and "缺少" in item for item in answer.missing_information)


def test_stale_tail_candidate_does_not_count_as_limit_coverage(tmp_path: Path) -> None:
    pages = [
        ("岚桥计划", f"预算记录{i}", f"岚桥计划预算额度第{i}项为{i * 10000}元。")
        for i in range(1, 7)
    ] + [("汀屿计划", "排期", "汀屿计划排期为十一月。")]
    root, service, _answerer = build_query(tmp_path, pages)
    tail_page = next(page for page in list_pages(root) if page.metadata["title"] == "排期")
    path = root / tail_page.relative_path
    path.write_text(
        path.read_text(encoding="utf-8").replace("排期为十一月", "开放时间为周六"),
        encoding="utf-8",
    )
    answer = ask(
        service,
        root,
        "比较岚桥计划的预算与汀屿计划的排期",
        "comparison",
    )
    assert any("汀屿计划" in item and "缺少" in item for item in answer.missing_information)
    assert not any("候选" in item and "汀屿计划" in item for item in answer.missing_information)
    assert not any(
        "汀屿计划" in item and "引用条数已达上限，以下所问范围" in item
        for item in answer.missing_information
    )


def test_single_citation_limit_reports_an_existing_uncovered_pair_as_truncated(
    tmp_path: Path,
) -> None:
    pages = [
        ("云岬营地", "预算", "云岬营地预算上限为八万元。"),
        ("汀屿计划", "排期", "汀屿计划排期为十一月。"),
    ]
    root, service, _answerer = build_query(tmp_path, pages)
    answer = service.query(
        root,
        "比较云岬营地预算与汀屿计划排期",
        fingerprint=FINGERPRINT,
        answer_mode="comparison",
        limit=1,
    )
    assert len(answer.citations) == 1
    assert any("条数已达上限" in item for item in answer.missing_information)
    assert not any("缺少" in item and "依据" in item for item in answer.missing_information)


@pytest.mark.parametrize("mode", ["fact", "comparison", "plan"])
def test_family_terms_do_not_join_separated_topic_fragments(tmp_path: Path, mode: str) -> None:
    project = "银杏工作坊"
    full = "银杏工作坊年度资料保管签领须双人登记。"
    question = {
        "fact": "银杏工作坊的年度资料保管签领办法是什么？",
        "comparison": "比较银杏工作坊的年度资料保管签领办法",
        "plan": "为银杏工作坊制定年度资料保管签领方案",
    }[mode]
    root, service, answerer = build_query(tmp_path, [(project, "资料保管", full)])
    planned = scope(service, root, question)
    assert planned.required_pairs == ((project, "storage&term:年度资料&term:签领"),)
    answer = ask(service, root, question, mode)
    assert full.rstrip("。") in excerpts(answer)
    assert answer.missing_information == []
    assert answerer.calls and full.rstrip("。") in passages(answerer)

    root, service, answerer = build_query(
        tmp_path / "missing-tail",
        [(project, "资料保管", "银杏工作坊年度资料保管须双人登记。")],
    )
    answer = ask(service, root, question, mode)
    assert answer.citations == [], answer.model_dump()
    assert answer.missing_information and "签领" in answer.missing_information[0]
    assert answerer.calls == []


def test_request_tail_does_not_become_a_missing_topic_dimension(tmp_path: Path) -> None:
    root, service, _answerer = build_query(
        tmp_path, [("其他项目", "其他", "其他项目的会场布置已确认。")]
    )
    question = "为彩色牙刷储存规则提出建议并列出缺失信息。"

    planned = scope(service, root, question)
    assert planned.explicit_subjects == ("彩色牙刷",)
    assert planned.required_pairs == (("彩色牙刷", "storage"),)

    answer = ask(service, root, question, "fact")
    assert answer.citations == []
    assert answer.missing_information == ["彩色牙刷：缺少存储或保管规则依据。"]


def test_plan_question_suffix_keeps_supported_budget_and_schedule_pairs(
    tmp_path: Path,
) -> None:
    root, service, _answerer = build_query(
        tmp_path,
        [
            ("青松计划", "预算", "青松计划预算已确认上限为十二万元。"),
            ("青松计划", "排期", "青松计划排期确认在十一月开始。"),
        ],
    )
    question = "青松计划预算和排期下一步需要补什么？"

    planned = scope(service, root, question)
    assert set(planned.required_pairs) == {
        ("青松计划", "budget"),
        ("青松计划", "schedule"),
    }
    answer = ask(service, root, question, "plan")
    assert answer.citations
    assert answer.advice == ["建议"]
    assert answer.missing_information == []


def test_lookup_verb_at_the_start_of_an_unknown_name_does_not_match_shorter_object(
    tmp_path: Path,
) -> None:
    root, service, _answerer = build_query(
        tmp_path,
        [
            ("明细项目", "预算", "明细项目预算为四万元。"),
            ("松墨展会", "预算", "松墨展会预算为八万元。"),
        ],
    )
    answer = ask(
        service,
        root,
        "比较查看明细项目与松墨展会的预算",
        "comparison",
    )

    assert set(scope(service, root, "比较查看明细项目与松墨展会的预算").explicit_subjects) == {
        "查看明细项目",
        "松墨展会",
    }
    assert [citation.excerpt for citation in answer.citations] == ["松墨展会预算为八万元。"]
    assert answer.missing_information == ["查看明细项目：缺少预算依据。"]


def test_page_title_supports_a_topic_question_without_a_known_object_alias(tmp_path: Path) -> None:
    """A confirmed page title is part of the topic even when it is absent from the body.

    Real case: the page title is “系统增加学员28号晚住宿需求自动勾选流程”, the body
    says “28号晚住宿”; a question repeating the title was rejected because the
    body-only scope match never saw the title. The title fallback must return the
    body citation, while a vague question without the title still returns none.
    """
    root, service, answerer = build_query(
        tmp_path,
        [
            (
                "IT测试",
                "系统增加学员28号晚住宿需求自动勾选流程",
                "目前学员是否需28号晚住宿需告知EC，EC手动写备注再整理给logistic。"
                "计划在系统中增加流程让学员自动勾选。",
            )
        ],
    )

    answer = ask(service, root, "学员28号晚住宿需求自动勾选流程是什么？", "fact")
    assert answer.citations, answer.model_dump()
    assert "28号晚住宿" in excerpts(answer)
    assert answer.missing_information == []
    assert answerer.calls
    assert "28号晚住宿" in passages(answerer)

    calls_before = len(answerer.calls)
    vague = ask(service, root, "28个学员是什么", "fact")
    assert vague.citations == []
    assert vague.missing_information
    assert len(answerer.calls) == calls_before
