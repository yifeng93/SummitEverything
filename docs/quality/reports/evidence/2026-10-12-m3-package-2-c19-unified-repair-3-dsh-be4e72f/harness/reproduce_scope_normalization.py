"""Observe object/topic normalization boundaries around request-shell stripping.

Prints observations only; its exit code is not a product verdict.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from test_c19_fresh_holdout import ask, excerpts, make_query
from summit_everything.retrieval.planner import plan_retrieval, query_scope
from summit_everything.workspace.manifest import load_manifest


def aliases_of(service, root):
    object_aliases: list[str] = []
    aliases = service._subject_aliases(root, load_manifest(root), object_aliases=object_aliases)
    return aliases, tuple(object_aliases)


DEVICE_PAGES = [
    ("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。", None),
    ("玄石展览", "场务", "玄石展览访客设备领用须登记姓名并归还胸牌。", None),
]

CASES = [
    # (case name, pages, question, mode)
    (
        "device-forward-full",
        DEVICE_PAGES,
        "比较枫湾活动预算与玄石展览的访客设备领用办法",
        "comparison",
    ),
    (
        "device-reverse-full",
        DEVICE_PAGES,
        "比较玄石展览的访客设备领用办法与枫湾活动预算",
        "comparison",
    ),
    (
        "device-single-full",
        DEVICE_PAGES,
        "玄石展览的访客设备领用办法是什么？",
        "fact",
    ),
    (
        "device-partial-b-topic-replaced",
        [
            ("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。", None),
            ("玄石展览", "场务", "玄石展览开放时间为周六。", None),
        ],
        "比较枫湾活动预算与玄石展览的访客设备领用办法",
        "comparison",
    ),
    (
        "device-zero-both-removed",
        [("玄石展览", "场务", "玄石展览开放时间为周六。", None)],
        "比较枫湾活动预算与玄石展览的访客设备领用办法",
        "comparison",
    ),
    (
        "year-qualifier-positive",
        [("玄石展览", "场务", "玄石展览年度访客登记办法为提前一天报备。", None)],
        "玄石展览的年度访客登记办法是什么",
        "fact",
    ),
    (
        "year-qualifier-negative-missing-qualifier",
        [("玄石展览", "场务", "玄石展览访客登记办法为提前一天报备。", None)],
        "玄石展览的年度访客登记办法是什么",
        "fact",
    ),
    (
        "special-qualifier-positive",
        [("玄石展览", "场务", "玄石展览专项证章领取须本人签名。", None)],
        "玄石展览的专项证章领取办法是什么",
        "fact",
    ),
    (
        "special-qualifier-negative-no-pseudo-object",
        [("玄石展览", "场务", "玄石展览证章领取须本人签名。", None)],
        "玄石展览的专项证章领取办法是什么",
        "fact",
    ),
    (
        "generic-plan-work-scheme",
        [("白榆工程", "综合", "白榆工程已批准预算五万元。", None)],
        "为白榆工程和玄岩项目制定下一步工作方案",
        "plan",
    ),
    (
        "device-budget-root-term-regression",
        [
            ("白鹭工程", "白鹭预算", "白鹭工程的设备预算上限为 24 万元。", None),
            ("白鹭工程", "白鹭补充预算", "白鹭工程的年度专项预算为 30 万元。", None),
        ],
        "白鹭工程的设备预算上限是多少？",
        "fact",
    ),
]


def main() -> None:
    for name, pages, question, mode in CASES:
        with tempfile.TemporaryDirectory(prefix="c19-norm-") as temp:
            root, service, answerer = make_query(Path(temp), pages)
            aliases, object_aliases = aliases_of(service, root)
            plan = plan_retrieval(question, [], aliases, object_aliases=object_aliases)
            answer = ask(service, root, question, mode)
            pairs = query_scope(question, plan.explicit_subjects)[1]
            print(
                json.dumps(
                    {
                        "case": name,
                        "question": question,
                        "mode": mode,
                        "aliases": list(aliases),
                        "object_aliases": list(object_aliases),
                        "subjects": list(plan.explicit_subjects),
                        "dimensions": list(plan.dimensions),
                        "required_pairs": [list(pair) for pair in pairs],
                        "scope_kind": plan.scope_kind,
                        "citation_count": len(answer.citations),
                        "citation_excerpts": excerpts(answer),
                        "provider_call_count": len(answerer.calls),
                        "provider_passages": [
                            p["excerpt"] for _, passages in answerer.calls for p in passages
                        ],
                        "missing_information": answer.missing_information,
                        "support_statements": len(answer.source_statements),
                        "support_inferences": len(answer.inferences),
                        "support_advice": len(answer.advice),
                    },
                    ensure_ascii=False,
                    default=str,
                )
            )


if __name__ == "__main__":
    main()
