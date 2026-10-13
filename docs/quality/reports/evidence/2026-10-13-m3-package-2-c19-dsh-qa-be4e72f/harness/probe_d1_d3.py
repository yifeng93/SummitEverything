from __future__ import annotations
import json, tempfile
from pathlib import Path
from test_c19_r2_expanded_matrix import make_query


def result(answer, answerer):
    return {
        "citations": [{"heading": c.heading, "excerpt": c.excerpt} for c in answer.citations],
        "missing": answer.missing_information,
        "text": answer.text,
        "source_statements": answer.source_statements,
        "provider_calls": len(answerer.calls),
        "provider_passages": [p["excerpt"] for _q, ps in answerer.calls for p in ps],
    }

out=[]
with tempfile.TemporaryDirectory(prefix="c19-d1-d3-") as td:
    root=Path(td)
    cases=[
      ("D1-title-only-anonymous", [("玄石展览","枫湾活动预算","预算上限为九万元。",None)], "枫湾活动的预算上限是多少？"),
      ("D1-alias-only-anonymous", [("玄石展览","资金记录","预算上限为九万元。",["枫湾活动"])], "枫湾活动的预算上限是多少？"),
      ("D1-title-but-explicit-opposite-body", [("玄石展览","枫湾活动预算","枫湾活动预算上限为九万元。",None)], "玄石展览的预算上限是多少？"),
      ("D1-title-and-same-name-real-project", [("玄石展览","枫湾活动预算","预算上限为九万元。",None),("枫湾活动","预算数据","预算上限为三万元。",None)], "枫湾活动的预算上限是多少？"),
    ]
    for i,(name,pages,q) in enumerate(cases):
        _root,svc,ans=make_query(root/str(i),pages)
        answer=svc.query(_root,q,fingerprint="fresh-holdout-v1",answer_mode="fact")
        out.append({"case":name,"question":q,**result(answer,ans)})
    pages=[
      ("云岬营地","预算1","云岬营地预算额度为八万六千元。",None),
      ("云岬营地","预算2","云岬营地预算额度另含两万元备用金。",None),
      ("云岬营地","预算3","云岬营地预算额度还有三万元机动款。",None),
    ]
    _root,svc,ans=make_query(root/"d3",pages)
    for mode in ("fact","comparison","plan"):
        q="比较云岬营地预算与汀屿计划的排期"
        answer=svc.query(_root,q,fingerprint="fresh-holdout-v1",answer_mode=mode,limit=1)
        out.append({"case":f"D3-limit-plus-real-absence-{mode}","question":q,**result(answer,ans)})
    print(json.dumps(out,ensure_ascii=False,indent=2))
