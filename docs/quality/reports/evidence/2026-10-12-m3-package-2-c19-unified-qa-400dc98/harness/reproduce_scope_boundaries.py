import json
from pathlib import Path
from tempfile import TemporaryDirectory
from test_c19_holdout import make_query, ask
from summit_everything.retrieval.planner import plan_retrieval
from summit_everything.workspace.manifest import load_manifest

records = []
with TemporaryDirectory(prefix="qa-c19-scope-boundaries-") as td:
    root, service, spy = make_query(Path(td), [
        ("预算时间专项", "综合安排", "预算时间专项已批准预算五万元，启动时间为六月。"),
        ("预算时间专项", "培训签到", "培训签到须现场登记并核验姓名。"),
    ], high_score=True, complete=True)
    aliases = service._subject_aliases(root, load_manifest(root))
    cases = [
        ("预算时间专项的培训签到办法是什么", "fact"),
        ("为预算时间专项制定培训签到流程", "plan"),
        ("比较预算时间专项培训签到安排", "comparison"),
        ("培训签到办法怎么安排", "plan"),
        ("预算时间专项签到办法是什么", "fact"),
    ]
    for question, mode in cases:
        plan = plan_retrieval(question, [], aliases)
        answer = ask(service, root, question, mode)
        records.append({
            "question": question, "mode": mode,
            "retrieval_plan": {"subjects": plan.explicit_subjects, "dimensions": plan.dimensions, "required_pairs": plan.required_pairs},
            "answer": answer.model_dump(mode="json"),
            "provider_calls_for_question": [{"question": q, "passages": p} for q,p in spy.calls if q == question],
            "expected": "只引用主题匹配的培训签到材料；预算/时间不得成为问题维度",
        })
    output = {"cases": records, "total_provider_calls": len(spy.calls)}
    Path(".local/qa/c19-unified/evidence").mkdir(parents=True, exist_ok=True)
    Path(".local/qa/c19-unified/evidence/unknown-topic-and-object-name-dimension.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
