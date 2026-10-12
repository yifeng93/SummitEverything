"""DSH subagent pre-QA round 3 — assertions against the NEW SHA (be4e72f / HEAD 7e772ea).

Re-checks D1/D2/D3/D4 and the two-tier request shell after the round-3 fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from preqa_lib import build, excerpt_text, sent_all_text

FENG = ("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。")
XUAN = ("玄石展览", "场务", "玄石展览访客设备领用须登记姓名并归还胸牌。")


def detail(probe, answer, question):
    return (
        f"\nquestion={question!r}"
        f"\nsubjects={probe.plan(question).explicit_subjects}"
        f"\npairs={probe.plan(question).required_pairs}"
        f"\ncitations={len(answer.citations)} excerpts={[c.excerpt for c in answer.citations]}"
        f"\nmissing={answer.missing_information}"
        f"\ntext={answer.text[:200]!r}"
        f"\nprovider_calls={len(answer.answerer_calls) if hasattr(answer, 'answerer_calls') else len(probe.answerer.calls)}"
        f"\nprovider_passages={sent_all_text(probe.answerer)!r}"
    )


def has_absence_wording(missing: list[str]) -> bool:
    """Detect the per-pair 'X：缺少<topic>依据。' absence claim, not the generic
    '仍缺少：' lead-in used in front of a truncation notice."""
    return any("缺少" in item and "依据" in item for item in missing)


# ---------------------------------------------------------- D2 still fixed
POLITE = [
    "麻烦帮我看看枫湾活动的经费上限是多少？",
    "帮我查一下枫湾活动的预算上限。",
    "看看枫湾活动的预算",
    "查一下枫湾活动的预算",
]


@pytest.mark.parametrize("question", POLITE)
def test_d2_still_fixed(tmp_path: Path, question):
    probe = build(tmp_path, [FENG, XUAN])
    answer = probe.ask(question, "fact")
    ctx = detail(probe, answer, question)
    assert probe.plan(question).explicit_subjects == ("枫湾活动",), ctx
    assert answer.missing_information == [], ctx


# ---------------------------------------------------------- D4 still fixed
@pytest.mark.parametrize("mode", ["fact", "comparison", "plan"])
def test_d4_still_fixed(tmp_path: Path, mode):
    probe = build(tmp_path, [FENG, ("玄石展览", "经费", "玄石展览预算上限为九万元。")])
    q = "比较枫湾活动预算与玄石展览的访客设备领用办法"
    answer = probe.ask(q, mode)
    ctx = detail(probe, answer, q)
    assert "term:" not in " ".join(answer.missing_information), ctx
    assert "term:" not in answer.text, ctx


# ---------------------------------------------------------- D3 truncation
@pytest.mark.parametrize("mode", ["fact", "comparison", "plan"])
def test_d3_limit1_no_absence_wording_and_names_uncovered_scope(tmp_path: Path, mode):
    probe = build(tmp_path, [FENG, XUAN])
    q = "比较枫湾活动的预算与玄石展览的访客设备领用"
    answer = probe.ask(q, mode, limit=1)
    ctx = detail(probe, answer, q)
    assert not has_absence_wording(answer.missing_information), ctx
    joined = " ".join(answer.missing_information)
    assert "上限" in joined, ctx
    assert "枫湾活动" in joined and "预算" in joined, ctx
    assert not has_absence_wording([answer.text]), ctx


def test_d3_default_limit5_no_absence_wording(tmp_path: Path):
    pages = []
    for name, budget, sched in [
        ("云岬营地", "云岬营地预算额度为八万六千元。", "云岬营地启动时间为上午九点。"),
        ("松墨展会", "松墨展会预算额度为十三万元。", "松墨展会启动时间为上午十点。"),
        ("汀屿计划", "汀屿计划预算额度为五万元。", "汀屿计划启动时间为十一点。"),
    ]:
        pages.append((name, "预算", budget))
        pages.append((name, "排期", sched))
    probe = build(tmp_path, pages)
    q = "比较云岬营地、松墨展会与汀屿计划的预算和排期"
    answer = probe.ask(q, "comparison")  # API default limit=5
    ctx = detail(probe, answer, q)
    assert len(answer.citations) == 5, ctx
    assert not has_absence_wording(answer.missing_information), ctx
    joined = " ".join(answer.missing_information)
    assert "云岬营地" in joined and "排期" in joined, ctx


def test_d3_no_truncation_keeps_real_absence_wording(tmp_path: Path):
    """Without truncation genuine gaps still use the normal missing wording."""
    probe = build(tmp_path, [
        ("云岬营地", "预算", "云岬营地预算额度为八万六千元。"),
        ("松墨展会", "预算", "松墨展会预算额度为十三万元。"),
        ("汀屿计划", "预算", "汀屿计划预算额度为五万元。"),
        ("云岬营地", "排期", "云岬营地启动时间为上午九点。"),
        ("松墨展会", "排期", "松墨展会启动时间为上午十点。"),
    ])
    q = "比较云岬营地、松墨展会与汀屿计划的预算和排期"
    answer = probe.ask(q, "comparison")
    ctx = detail(probe, answer, q)
    assert answer.missing_information == ["汀屿计划：缺少排期或启动时间依据。"], ctx
    assert "上限" not in " ".join(answer.missing_information), ctx


# ---------------------------------------------------------- D1 unchanged
def test_d1_unchanged_as_declared(tmp_path: Path):
    probe = build(tmp_path, [("玄石展览", "枫湾活动预算", "预算上限为九万元。")])
    q = "枫湾活动的预算上限是多少？"
    answer = probe.ask(q, "fact")
    ctx = detail(probe, answer, q)
    assert [c.excerpt for c in answer.citations] == ["预算上限为九万元。"], ctx


# ---------------------------------------------------------- two-tier shell
@pytest.mark.parametrize("name", ["看看项目", "总结项目", "梳理项目", "查看项目", "告诉我项目"])
def test_two_tier_registered_object_name_intact(tmp_path: Path, name):
    probe = build(tmp_path, [(name, "经费", f"{name}预算上限为七万二千元。")])
    q = f"{name}的预算上限是多少？"
    answer = probe.ask(q, "fact")
    ctx = detail(probe, answer, q)
    assert name in probe.plan(q).explicit_subjects, ctx
    assert answer.missing_information == [], ctx


@pytest.mark.parametrize("name", ["总结报告", "查看细则", "梳理记录", "告诉我台账",
                                 "看看报告", "说明一下记录", "查一查报告"])
def test_two_tier_unregistered_object_name_intact(tmp_path: Path, name):
    probe = build(tmp_path, [("松墨展会", "经费", "松墨展会预算上限为七万元。")])
    q = f"比较{name}与松墨展会的预算"
    answer = probe.ask(q, "comparison")
    ctx = detail(probe, answer, q)
    assert name in probe.plan(q).explicit_subjects, ctx


def test_two_tier_registered_lookup_prefix_is_cleaned(tmp_path: Path):
    """Round-2 regression: a registered object after a lookup verb must stay clean."""
    probe = build(tmp_path, [
        ("云岬营地", "经费", "云岬营地预算上限为八万六千元。"),
        ("松墨展会", "经费", "松墨展会预算上限为七万元。"),
    ])
    for q in ("麻烦帮我看看云岬营地的预算上限", "看看云岬营地的预算上限",
              "看看云岬营地预算"):
        answer = probe.ask(q, "fact")
        ctx = detail(probe, answer, q)
        assert probe.plan(q).explicit_subjects == ("云岬营地",), ctx
        assert answer.missing_information == [], ctx
        assert "云岬营地预算上限为八万六千元。" in excerpt_text(answer), ctx


def test_two_tier_overstrip_does_not_pull_unrelated_evidence(tmp_path: Path):
    """Round-2 regression: the mangled object 报告 must no longer pull 报告 evidence."""
    probe = build(tmp_path, [
        ("松墨展会", "经费", "松墨展会预算上限为七万元。"),
        ("无关项目", "说明", "报告预算上限为二万元。"),
    ])
    q = "比较总结报告与松墨展会的预算"
    answer = probe.ask(q, "comparison")
    ctx = detail(probe, answer, q)
    assert "总结报告" in probe.plan(q).explicit_subjects, ctx
    assert "报告预算上限为二万元。" not in sent_all_text(probe.answerer), ctx
    assert "总结报告" in " ".join(answer.missing_information), ctx
