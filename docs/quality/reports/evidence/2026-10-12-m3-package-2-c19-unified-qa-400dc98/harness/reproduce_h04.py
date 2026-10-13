import json
from pathlib import Path
from tempfile import TemporaryDirectory
from test_c19_holdout import make_query, ask

with TemporaryDirectory(prefix="qa-c19-unknown-topic-") as td:
    root, service, spy = make_query(Path(td), [
        ("白榆工程", "综合事实", "白榆工程预算上限为二十万元。白榆工程启动时间为五月。"),
        ("玄岩项目", "玄岩排期", "玄岩项目启动时间为十二月。"),
    ], high_score=True)
    answer = ask(service, root, "白榆工程的培训签到办法是什么", "plan")
    result = {
        "question": "白榆工程的培训签到办法是什么",
        "mode": "plan",
        "answer": answer.model_dump(mode="json"),
        "provider_calls": [{"question": q, "passages": p} for q, p in spy.calls],
        "expected": {"citations": [], "provider_calls": 0, "missing": "培训签到办法资料不足"},
        "actual": {"citation_excerpts": [c.excerpt for c in answer.citations], "provider_calls": len(spy.calls), "missing": answer.missing_information, "text": answer.text},
    }
    Path(".local/qa/c19-unified/evidence").mkdir(parents=True, exist_ok=True)
    Path(".local/qa/c19-unified/evidence/h04-unknown-dimension.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
