from __future__ import annotations
import json, os, re, uuid
from pathlib import Path
import httpx
from summit_everything.workspace.manifest import load_manifest
from summit_everything.workspace.reader import read_page
from uuid import UUID

BASE = Path(os.environ['QA_M3_BASE']).resolve()
API = 'http://127.0.0.1:18373/api/v1'
TOKEN = os.environ['QA_M3_SESSION_TOKEN']
H = {'Authorization': f'Bearer {TOKEN}'}
WORKSPACE = BASE / 'workspace-A'
CAPTURE = BASE / 'harness' / 'deepseek-payloads.jsonl'

def calls() -> int:
    return len(CAPTURE.read_text(encoding='utf-8').splitlines()) if CAPTURE.exists() else 0

def events(response: httpx.Response) -> list[dict]:
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]

def run_query(c: httpx.Client, question: str, mode: str = 'fact') -> tuple[httpx.Response, dict, list[dict]]:
    fp = c.get(API + '/settings').json()['embedding_fingerprint']
    response = c.post(API + '/queries', json={'request_id': str(uuid.uuid4()), 'question': question, 'fingerprint': fp, 'answer_mode': mode, 'purpose': 'current'})
    ev = events(response)
    completed = next((e.get('data', {}) for e in ev if e.get('type') == 'completed'), {})
    return response, completed, ev

results: list[dict] = []
with httpx.Client(headers=H, timeout=30) as c:
    status = c.get(API + '/index/status').json()
    before = calls()
    for mode, question in [
        ('fact', '风铃工程的彩色牙刷储存规则是什么？'),
        ('comparison', '比较风铃工程与霜塔项目的彩色牙刷储存规则。'),
        ('plan', '为风铃工程的彩色牙刷储存规则提出方案，并列出缺失信息。'),
    ]:
        response, answer, ev = run_query(c, question, mode)
        text_value = answer.get('text', '')
        missing = answer.get('missing_information', [])
        prohibited = any(token in (text_value + ' '.join(missing)) for token in ('缓存', '资格检查未通过', '资料版本与当前工作库不一致'))
        fabricated_numbers = bool(re.search(r'(?<![\w])\d+(?:\.\d+)?\s*(?:万|元|天|%|个|项)', text_value))
        ok = response.status_code == 200 and answer.get('index_status') == 'ready' and not answer.get('citations') and not answer.get('source_statements') and not answer.get('inferences') and not answer.get('advice') and isinstance(missing, list) and bool(missing) and not prohibited and not fabricated_numbers and calls() == before
        results.append({'case': f'C19-fresh-ready-no-evidence-{mode}', 'status': 'PASS' if ok else 'FAIL', 'http': response.status_code, 'index': status, 'answer': answer, 'event_types': [e.get('type') for e in ev], 'provider_calls_before': before, 'provider_calls_after': calls(), 'prohibited_cache_diagnosis': prohibited, 'fabricated_number': fabricated_numbers})

    # A nonmatching stale page must not be attributed to an unrelated no-evidence query.
    target = read_page(WORKSPACE, UUID(int=1001))
    target_path = WORKSPACE / target.relative_path
    target_path.write_text(target_path.read_text(encoding='utf-8').replace('18 万元', '19 万元'), encoding='utf-8')
    unrelated_status = c.get(API + '/index/status').json()
    before_unrelated = calls()
    response, answer, ev = run_query(c, '为风铃工程的彩色牙刷储存规则提出方案，并列出缺失信息。', 'plan')
    joined = answer.get('text', '') + ' '.join(answer.get('missing_information', []))
    false_stale_report = any(token in joined for token in ('缓存', '版本与当前工作库不一致', '资格检查未通过'))
    ok = unrelated_status.get('state') == 'stale' and unrelated_status.get('stale_pages', 0) > 0 and not answer.get('citations') and not false_stale_report and calls() == before_unrelated
    results.append({'case': 'C19-unrelated-stale-page-does-not-contaminate-diagnostic', 'status': 'PASS' if ok else 'FAIL', 'index': unrelated_status, 'answer': answer, 'provider_calls_before': before_unrelated, 'provider_calls_after': calls(), 'false_stale_report': false_stale_report})

    # Restore the selected approved page to exactly the original semantic version.
    # The writer is real; this is independent fixture restoration after the controlled external edit.
    from summit_everything.workspace.writer import PageWriter
    manifest = load_manifest(WORKSPACE)
    line = manifest.lines[0]; project = manifest.projects[0]
    PageWriter().confirm(WORKSPACE, metadata={'id':str(UUID(int=1001)),'title':'设备预算备案','role':'knowledge','kind':'topic','line_id':str(line.id),'project_id':str(project.id),'validity':'current','aliases':['青岚计划']}, body='青岚计划的设备采购预算上限为 18 万元，负责人已确认。排期为 11 月启动；运维费用未提供。', confirmation_id='qa-extra2-restore-page-confirm', operation_id='qa-extra2-restore-page-write', expected_base_sha256=read_page(WORKSPACE, UUID(int=1001)).content_sha256)
    restored_index = c.get(API + '/index/status').json()
    # A still-indexed page whose approval proof was externally removed must be excluded from CURRENT.
    target = read_page(WORKSPACE, UUID(int=1001)); original_raw = (WORKSPACE / target.relative_path).read_bytes()
    import yaml
    raw_text = original_raw.decode('utf-8')
    _, rest = raw_text.split('---\n', 1)
    frontmatter, body_text = rest.split('\n---\n', 1)
    metadata = yaml.safe_load(frontmatter)
    metadata.pop('approval', None)
    (WORKSPACE / target.relative_path).write_text('---\n' + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False) + '---\n' + body_text, encoding='utf-8')
    before_unapproved = calls()
    unapproved_response, unapproved_answer, _ = run_query(c, '青岚计划的预算上限是多少？', 'fact')
    unapproved_ok = unapproved_response.status_code == 200 and not unapproved_answer.get('citations') and calls() == before_unapproved
    results.append({'case':'C19-current-excludes-unapproved-indexed-page', 'status':'PASS' if unapproved_ok else 'FAIL', 'answer':unapproved_answer, 'provider_calls_before':before_unapproved, 'provider_calls_after':calls()})
    (WORKSPACE / target.relative_path).write_bytes(original_raw)

    # An actual expected-hash mismatch is now isolated from the no-data cases.
    target = read_page(WORKSPACE, UUID(int=1001)); expected_hash = target.content_sha256
    target_path = WORKSPACE / target.relative_path
    target_path.write_text(target_path.read_text(encoding='utf-8').replace('18 万元', '19 万元'), encoding='utf-8')
    before_hash = calls()
    response, answer, ev = run_query(c, '青岚计划的预算上限是多少？', 'fact')
    has_hash_reason = any(token in answer.get('text','') for token in ('正文与确认记录不一致','版本与当前已确认内容不一致'))
    ok = response.status_code == 200 and not answer.get('citations') and has_hash_reason and calls() == before_hash and expected_hash != read_page(WORKSPACE, UUID(int=1001)).content_sha256
    results.append({'case':'C19-real-content-hash-mismatch', 'status':'PASS' if ok else 'FAIL', 'expected_hash_sha256':expected_hash, 'actual_hash_sha256':read_page(WORKSPACE, UUID(int=1001)).content_sha256, 'index_before_query':restored_index, 'answer':answer, 'provider_calls_before':before_hash, 'provider_calls_after':calls()})

    # Restore fixture again and exercise true no-ready state through the same API route.
    PageWriter().confirm(WORKSPACE, metadata={'id':str(UUID(int=1001)),'title':'设备预算备案','role':'knowledge','kind':'topic','line_id':str(line.id),'project_id':str(project.id),'validity':'current','aliases':['青岚计划']}, body='青岚计划的设备采购预算上限为 18 万元，负责人已确认。排期为 11 月启动；运维费用未提供。', confirmation_id='qa-extra2-restore-page-confirm-2', operation_id='qa-extra2-restore-page-write-2', expected_base_sha256=read_page(WORKSPACE, UUID(int=1001)).content_sha256)
    empty_root = BASE / 'workspace-empty'
    opened = c.post(API + '/workspaces', json={'root':str(empty_root),'mode':'create','name':'QA empty index workspace','operation_id':'qa-extra2-empty-create'})
    assert opened.status_code == 201, (opened.status_code, opened.text)
    empty_manifest = load_manifest(empty_root)
    from summit_everything.retrieval.query import QueryService
    from summit_everything.retrieval.store import IndexStore
    from summit_everything.integrations.embedding import FakeEmbedding
    local_profile = Path(opened.json()['local_profile_dir'])
    store = IndexStore(local_profile / 'index.sqlite3')
    service = QueryService(store, FakeEmbedding())
    fp = c.get(API + '/settings').json()['embedding_fingerprint']
    plan = service.plan(empty_root, fingerprint=fp, mode='initial')
    service.execute_plan(empty_root, plan)
    service.close()
    empty_status = c.get(API + '/index/status').json()
    empty_before = calls()
    c.post(API + '/workspaces', json={'root':str(empty_root),'mode':'open','operation_id':'qa-extra2-empty-open'})
    empty_status = c.get(API + '/index/status').json()
    for mode in ('fact','comparison','plan'):
        response, answer, ev = run_query(c, f'空索引的{mode}缺少什么资料？', mode)
        ok = response.status_code == 200 and answer.get('index_status') == 'empty' and not answer.get('citations') and bool(answer.get('missing_information')) and calls() == empty_before
        results.append({'case':f'C19-empty-index-no-evidence-{mode}', 'status':'PASS' if ok else 'FAIL', 'index':empty_status, 'answer':answer, 'provider_calls_before':empty_before, 'provider_calls_after':calls()})

out = BASE / 'harness' / 'extra2-c19-results.json'
out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(results, ensure_ascii=False, indent=2))
