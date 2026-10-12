from __future__ import annotations
import json, os, uuid
from pathlib import Path
from uuid import UUID
import httpx
from summit_everything.workspace.manifest import load_manifest
from summit_everything.workspace.reader import read_page
from summit_everything.workspace.writer import PageWriter

BASE=Path(os.environ['QA_M3_BASE']).resolve(); ROOT=BASE/'workspace-A'; API='http://127.0.0.1:18373/api/v1'; TOKEN=os.environ['QA_M3_SESSION_TOKEN']; H={'Authorization':f'Bearer {TOKEN}'}; CAPTURE=BASE/'harness'/'deepseek-payloads.jsonl'
def count(): return len(CAPTURE.read_text(encoding='utf-8').splitlines()) if CAPTURE.exists() else 0
def ev(resp): return [json.loads(line[6:]) for line in resp.text.splitlines() if line.startswith('data: ')]
def run(c, question):
    fp=c.get(API+'/settings').json()['embedding_fingerprint']
    r=c.post(API+'/queries',json={'request_id':str(uuid.uuid4()),'question':question,'fingerprint':fp,'answer_mode':'fact','purpose':'current'})
    events=ev(r); data=next((e.get('data',{}) for e in events if e.get('type')=='completed'),{})
    return r,data,events
def restore(c, suffix):
    manifest=load_manifest(ROOT); page=read_page(ROOT,UUID(int=1001)); metadata={'id':str(UUID(int=1001)),'title':'设备预算备案','role':'knowledge','kind':'topic','line_id':str(manifest.lines[0].id),'project_id':str(manifest.projects[0].id),'validity':'current','aliases':['青岚计划']}
    PageWriter().confirm(ROOT,metadata=metadata,body='青岚计划的设备采购预算上限为 18 万元，负责人已确认。排期为 11 月启动；运维费用未提供。',confirmation_id='qa-extra2-race-restore-'+suffix,operation_id='qa-extra2-race-restore-'+suffix,expected_base_sha256=page.content_sha256)

results=[]
with httpx.Client(headers=H,timeout=30) as c:
    for name,marker,expected in [
        ('content-changed','__qa_mutate_content__','生成期间引用资料版本发生变化'),
        ('moved-out-current','__qa_move_history__','生成期间引用资料版本发生变化'),
        ('page-unavailable','__qa_delete_page__','生成期间引用资料已不可用'),
    ]:
        before=count(); question='青岚计划的预算上限是多少？ '+marker
        r,answer,events=run(c,question)
        text=answer.get('text',''); calls=count()
        ok=r.status_code==200 and not answer.get('citations') and not answer.get('source_statements') and not answer.get('inferences') and not answer.get('advice') and answer.get('missing_information')==[text] and expected in text and calls==before+1 and '19 万元' not in text
        results.append({'case':'C19-provider-generation-'+name,'status':'PASS' if ok else 'FAIL','http':r.status_code,'expected_note':expected,'answer':answer,'event_types':[e.get('type') for e in events],'provider_calls_before':before,'provider_calls_after':calls})
        if name != 'page-unavailable':
            restore(c,name)

out=BASE/'harness'/'generation-races-results.json'; out.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8'); print(json.dumps(results,ensure_ascii=False,indent=2))
