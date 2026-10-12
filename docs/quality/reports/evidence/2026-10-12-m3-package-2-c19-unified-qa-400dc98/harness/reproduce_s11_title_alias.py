import json
from pathlib import Path
from tempfile import TemporaryDirectory
from test_c19_holdout import ask, make_query
from summit_everything.retrieval.planner import plan_retrieval
from summit_everything.workspace.manifest import load_manifest

with TemporaryDirectory(prefix="qa-c19-s11-title-alias-") as td:
    root, service, spy = make_query(Path(td), [
        ("白榆工程", "预算汇总", "白榆工程预算上限为二十万元。"),
        ("玄岩项目", "排期", "玄岩项目启动时间为十二月。"),
    ], high_score=True)
    question = "比较预算和排期建议"
    plan = plan_retrieval(question, [], service._subject_aliases(root, load_manifest(root)))
    answer = ask(service, root, question, "comparison")
    record = {
        "question": question,
        "mode": "comparison",
        "expected": "将预算、排期解析为两个维度；引用预算汇总和排期材料，不将‘排期’标题误判为对象；不报告缺失。",
        "plan": {"subjects": plan.explicit_subjects, "dimensions": plan.dimensions, "required_pairs": plan.required_pairs},
        "answer": answer.model_dump(mode="json"),
        "provider_calls": [{"question": q, "passages": p} for q, p in spy.calls],
    }
    output = Path(".local/qa/c19-unified/evidence/s11-title-alias.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output.read_text(encoding="utf-8"))
