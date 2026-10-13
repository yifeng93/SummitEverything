from __future__ import annotations
import json
import tempfile
from pathlib import Path
from test_c19_fresh_holdout import ask, excerpts, make_query
from summit_everything.retrieval.planner import query_scope

cases = [
    ("mixed-full-forward-fact", "比较枫湾活动预算与玄石展览的访客设备领用办法", "fact", [("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。", None), ("玄石展览", "场务", "玄石展览访客设备领用须登记姓名并归还胸牌。", None)]),
    ("mixed-full-reverse-comparison", "比较玄石展览的访客设备领用办法与枫湾活动预算", "comparison", [("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。", None), ("玄石展览", "场务", "玄石展览访客设备领用须登记姓名并归还胸牌。", None)]),
    ("single-exact-positive-fact", "玄石展览的访客设备领用办法是什么？", "fact", [("玄石展览", "场务", "玄石展览访客设备领用须登记姓名并归还胸牌。", None)]),
    ("partial-no-exact-support", "比较枫湾活动预算与玄石展览的访客设备领用办法", "comparison", [("枫湾活动", "经费", "枫湾活动预算上限为七万二千元。", None), ("玄石展览", "场务", "玄石展览开放时间为周六。", None)]),
]
for index, (case, question, mode, pages) in enumerate(cases):
    with tempfile.TemporaryDirectory(prefix="c19-r2-repro-") as temp:
        root, service, answerer = make_query(Path(temp), pages)
        subjects = ("玄石展览",) if case == "single-exact-positive-fact" else ("枫湾活动", "玄石展览")
        plan = query_scope(question, subjects)
        answer = ask(service, root, question, mode)
        print(json.dumps({
            "case": case,
            "question": question,
            "mode": mode,
            "plan_dimensions_and_pairs": plan,
            "citations": [c.model_dump(mode="json") for c in answer.citations],
            "citation_excerpts": excerpts(answer),
            "provider_call_count": len(answerer.calls),
            "provider_passages": [p["excerpt"] for _, passages in answerer.calls for p in passages],
            "missing_information": answer.missing_information,
            "body": answer.text,
        }, ensure_ascii=False, default=str))
