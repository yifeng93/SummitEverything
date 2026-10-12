"""Reproduce the four findings from the DSH pre-verification on the current tree.

Prints observations only; exit code is not a product verdict.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from test_c19_fresh_holdout import ask, excerpts, make_query
from summit_everything.retrieval.planner import plan_retrieval
from summit_everything.workspace.manifest import load_manifest


def scope(service, root, question):
    object_aliases: list[str] = []
    aliases = service._subject_aliases(root, load_manifest(root), object_aliases=object_aliases)
    return plan_retrieval(question, [], aliases, object_aliases=tuple(object_aliases))


def record(name, note, observed, expectation):
    print(
        json.dumps(
            {
                "case": name,
                "note": note,
                "expectation": expectation,
                "observed": observed,
            },
            ensure_ascii=False,
            default=str,
        )
    )


def main() -> None:
    # D1: page filed under one project but titled/aliased with another object's name.
    with tempfile.TemporaryDirectory(prefix="c19-d1-") as temp:
        root, service, answerer = make_query(
            Path(temp),
            [
                ("玄石展览", "枫湾活动预算", "预算上限为九万元。", ["枫湾活动预算"]),
                ("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。", None),
            ],
        )
        question = "枫湾活动的预算上限是多少？"
        answer = ask(service, root, question, "fact")
        planned = scope(service, root, question)
        record(
            "D1-title-alias-binding",
            "page belongs to 玄石展览 but its title/alias is 枫湾活动预算; body has no object name.",
            {
                "pairs": [list(pair) for pair in planned.required_pairs],
                "citation_excerpts": excerpts(answer),
                "missing": answer.missing_information,
                "provider_excerpts": [
                    p["excerpt"] for _, passages in answerer.calls for p in passages
                ],
            },
            "contract question: metadata attribution is allowed by the plan "
            "(项目/页元数据可确定归属); flagged for QA rather than changed here.",
        )

    # D2: polite lookup verbs must not become pseudo objects.
    with tempfile.TemporaryDirectory(prefix="c19-d2-") as temp:
        root, service, answerer = make_query(
            Path(temp), [("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。", None)]
        )
        d2 = {}
        for question in (
            "麻烦帮我看看枫湾活动的经费上限是多少？",
            "帮我查一下枫湾活动的预算上限。",
            "看看枫湾活动的预算",
            "查一下枫湾活动的预算",
        ):
            planned = scope(service, root, question)
            answer = ask(service, root, question, "fact")
            d2[question] = {
                "subjects": list(planned.explicit_subjects),
                "pairs": [list(pair) for pair in planned.required_pairs],
                "missing": answer.missing_information,
                "citation_excerpts": excerpts(answer),
            }
        record(
            "D2-polite-lookup-verbs",
            "request-shell verbs 看看/查一下/看一下 must be stripped, not treated as objects.",
            d2,
            "no pseudo object (看看/查一下) and no false missing",
        )

    # D3: default limit truncation versus absence wording.
    with tempfile.TemporaryDirectory(prefix="c19-d3-") as temp:
        pages = [
            ("枫湾活动", "枫湾预算", "枫湾活动预算上限为七万二千元。", None),
            ("枫湾活动", "枫湾排期", "枫湾活动启动时间为十月。", None),
            ("玄石展览", "玄石预算", "玄石展览预算上限为三万元。", None),
            ("玄石展览", "玄石排期", "玄石展览启动时间为十一月。", None),
            ("云岬营地", "云岬预算", "云岬营地预算上限为八万元。", None),
            ("云岬营地", "云岬排期", "云岬营地启动时间为十二月。", None),
        ]
        root, service, answerer = make_query(Path(temp), pages)
        question = "比较枫湾活动、玄石展览和云岬营地的预算和排期。"
        answer_limit5 = service.query(
            root, question, fingerprint="fresh-holdout-v1", answer_mode="comparison", limit=5
        )
        answer_limit1 = service.query(
            root, question, fingerprint="fresh-holdout-v1", answer_mode="comparison", limit=1
        )
        record(
            "D3-limit-truncation-wording",
            "six pairs with limit=5/limit=1; the dropped pair is reported with the same wording "
            "as an absent-evidence gap.",
            {
                "limit5": {
                    "citations": len(answer_limit5.citations),
                    "missing": answer_limit5.missing_information,
                    "excerpts": excerpts(answer_limit5),
                },
                "limit1": {
                    "citations": len(answer_limit1.citations),
                    "missing": answer_limit1.missing_information,
                },
            },
            "S12 allows reporting the uncovered part; whether the wording must name truncation "
            "is a separate contract question for QA/Sol.",
        )

    # D4: user-visible missing text must not leak the internal term: marker.
    with tempfile.TemporaryDirectory(prefix="c19-d4-") as temp:
        root, service, answerer = make_query(
            Path(temp), [("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。", None)]
        )
        answer = ask(service, root, "比较枫湾活动预算与玄石展览的访客设备领用办法", "fact")
        record(
            "D4-missing-wording",
            "a bare exact topic has no family label; the internal term: marker must not be shown.",
            {
                "missing": answer.missing_information,
                "text": answer.text,
            },
            "business language only; no 'term:' substring",
        )


    # D5 (round 2): a shell verb must not truncate an unregistered object name.
    with tempfile.TemporaryDirectory(prefix="c19-d5-") as temp:
        root, service, answerer = make_query(
            Path(temp),
            [
                ("松墨展会", "预算", "松墨展会预算上限为七万元。", None),
                ("榆木论坛", "无关", "榆木论坛开放时间为周六。", None),
            ],
        )
        d5 = {}
        for question in (
            "比较总结报告与松墨展会的预算",
            "比较总结方案与松墨展会的预算",
            "比较查看细则与松墨展会的预算",
            "比较梳理工程与松墨展会的预算",
        ):
            planned = scope(service, root, question)
            answer = ask(service, root, question, "comparison")
            d5[question] = {
                "subjects": list(planned.explicit_subjects),
                "pairs": [list(pair) for pair in planned.required_pairs],
                "missing": answer.missing_information,
                "citation_excerpts": excerpts(answer),
            }
        record(
            "D5-shell-verb-over-strip",
            "unknown object names that begin with a shell word must survive intact.",
            d5,
            "object name kept whole; the unrelated page is never cited; the named object is reported, not dropped",
        )

    # D3 (round 2): a truncated pair must not be worded as absent knowledge.
    with tempfile.TemporaryDirectory(prefix="c19-d3b-") as temp:
        pages = [
            ("枫湾活动", "枫湾预算", "枫湾活动预算上限为七万二千元。", None),
            ("枫湾活动", "枫湾排期", "枫湾活动启动时间为十月。", None),
            ("玄石展览", "玄石预算", "玄石展览预算上限为三万元。", None),
            ("玄石展览", "玄石排期", "玄石展览启动时间为十一月。", None),
            ("云岬营地", "云岬预算", "云岬营地预算上限为八万元。", None),
            ("云岬营地", "云岬排期", "云岬营地启动时间为十二月。", None),
        ]
        root, service, answerer = make_query(Path(temp), pages)
        question = "比较枫湾活动、玄石展览和云岬营地的预算和排期。"
        for label, limit in (("limit5", 5), ("limit1", 1), ("no-truncation", 12)):
            answer = service.query(
                root, question, fingerprint="fresh-holdout-v1",
                answer_mode="comparison", limit=limit,
            )
            record(
                f"D3b-truncation-{label}",
                "truncated pairs must be reported as truncation, not as missing evidence.",
                {
                    "citations": len(answer.citations),
                    "missing": answer.missing_information,
                },
                "no '缺少…依据' entry when the cap cut candidates; truncation notice names the uncovered scope",
            )


if __name__ == "__main__":
    main()
