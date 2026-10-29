"""Explicit renewed user authorization: at most five synthetic DeepSeek calls."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from uuid import UUID

from summit_everything.integrations.llm import DeepSeekLLM
import summit_everything.integrations.llm as llm_module

OUT = Path(__file__).parent / 'deepseek-verification'
OUT.mkdir(exist_ok=True)
LEDGER = OUT / 'attempts.jsonl'
RESULTS = OUT / 'results.jsonl'
KEY = os.environ['DEEPSEEK_API_KEY']
SOURCE_ROOT = Path(sys.argv[2]).resolve()
assert Path(llm_module.__file__).resolve().is_relative_to(SOURCE_ROOT / 'src')
SOURCE_SHA = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SOURCE_ROOT, text=True).strip()
assert SOURCE_SHA == sys.argv[1], 'fixed source SHA required'
assert not subprocess.check_output(['git', 'diff', 'HEAD', '--', 'src'], cwd=SOURCE_ROOT, text=True)

def append(path, value):
    serialized = json.dumps(value, ensure_ascii=False)
    assert KEY not in serialized
    with path.open('a') as stream:
        stream.write(serialized + '\n')
        stream.flush()
        os.fsync(stream.fileno())

cases = [
    ('organize', '合成纸飞机活动039仅为合成测试。人数上限63人，下午16:30开始。场地费用和负责人的电话尚未确定。', '63'),
    ('organize', '合成纸飞机活动058仅为合成测试。人数上限82人，下午16:30开始。场地费用和负责人的电话尚未确定。', '82'),
    ('organize', '合成活动：已确定人数上限24人。场地费用未定。有人建议增加一个签到环节，但尚未批准，也没有创建任务。', '24'),
    ('answer_fact', '合成活动人数上限24人，下午16:30开始。场地费用和负责人的电话尚未确定。', '24'),
    ('answer_missing', '合成活动人数上限24人，下午16:30开始。场地费用和负责人的电话尚未确定。', None),
]
assert not LEDGER.exists(), 'never reset or reuse a call ledger'
for index, (kind, source, expected) in enumerate(cases, 1):
    attempts = len(LEDGER.read_text().splitlines()) if LEDGER.exists() else 0
    assert attempts < 5
    append(LEDGER, {'attempt': index, 'kind': kind, 'source_sha': SOURCE_SHA, 'input_sha256': hashlib.sha256(source.encode()).hexdigest(), 'time': time.time(), 'max_tokens': 2048})
    provider = DeepSeekLLM(KEY, max_tokens=2048, reasoning_effort='low')
    started = time.monotonic()
    result = {'attempt': index, 'kind': kind}
    try:
        if kind == 'organize':
            value = provider.organize([(UUID(int=index), UUID(int=index+100), source)])
            checks = {'schema': True, 'source_indexes': all(p.input_indexes == [0] for p in value), 'capacity_retained': any(expected in p.body for p in value)}
            result['output'] = [p.model_dump(mode='json') for p in value]
        else:
            question = '人数上限是多少？' if kind == 'answer_fact' else '负责人的电话号码是多少？资料没有时明确说明缺失。'
            value = provider.answer(question, [{'heading': '合成活动', 'excerpt': source, 'page_id': str(UUID(int=500)), 'source_id': str(UUID(int=501))}])
            checks = {'schema': True}
            checks['grounded'] = expected in value.text if expected else bool(value.missing_information)
            result['output'] = value.model_dump(mode='json')
        result.update(status='PASS' if all(checks.values()) else 'FAIL', checks=checks)
    except Exception as error:
        result.update(status='ERROR', error_type=type(error).__name__, reason=getattr(error, 'reason', None))
        if getattr(error, 'reason', None) == 'schema':
            result['diagnostic'] = str(error)
    finally:
        provider.close()
        result.update(usage=provider.usage_records, seconds=round(time.monotonic()-started, 2))
        append(RESULTS, result)
        print(json.dumps({k:result[k] for k in ('attempt','kind','status','seconds')}, ensure_ascii=False), flush=True)
    if result['status'] != 'PASS':
        break
rows = [json.loads(row) for row in RESULTS.read_text().splitlines()]
summary = {'source_sha': SOURCE_SHA, 'attempts': len(rows), 'passed': sum(row['status'] == 'PASS' for row in rows), 'limit': 5, 'prior_budget_consumed': 100, 'new_authorization': 'user renewed DeepSeek synthetic test authorization; root narrowed to five', 'key_persisted': False, 'dashscope_calls': 0}
(OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(summary,ensure_ascii=False))
sys.exit(0 if all(row['status'] == 'PASS' for row in rows) else 1)
