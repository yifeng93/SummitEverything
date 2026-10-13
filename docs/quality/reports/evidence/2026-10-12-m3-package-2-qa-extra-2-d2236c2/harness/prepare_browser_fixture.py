from __future__ import annotations
import json, os
from pathlib import Path
from uuid import UUID
import httpx
from summit_everything.domain.models import PageSnapshot
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import load_manifest
from summit_everything.workspace.reader import list_pages
from summit_everything.workspace.writer import PageWriter

BASE=Path(os.environ['QA_M3_BASE']).resolve(); ROOT=BASE/'workspace-A'; API='http://127.0.0.1:18373/api/v1'; H={'Authorization':f"Bearer {os.environ['QA_M3_SESSION_TOKEN']}"}
with httpx.Client(headers=H) as c:
    opened=c.post(API+'/workspaces',json={'root':str(ROOT),'mode':'open','operation_id':'qa-extra2-browser-open'})
    assert opened.status_code==201,opened.text
    current=opened.json(); fp=c.get(API+'/settings').json()['embedding_fingerprint']
manifest=load_manifest(ROOT); line=manifest.lines[0]; project=manifest.projects[0]; writer=PageWriter()
current_meta={'id':str(UUID(int=1001)),'title':'设备预算备案','role':'knowledge','kind':'topic','line_id':str(line.id),'project_id':str(project.id),'validity':'current','aliases':['青岚计划']}
try:
    from summit_everything.workspace.reader import read_page
    existing=read_page(ROOT,UUID(int=1001)); expected=existing.content_sha256
except Exception:
    expected=None
writer.confirm(ROOT,metadata=current_meta,body='青岚计划的设备采购预算上限为 18 万元，负责人已确认。排期为 11 月启动；运维费用未提供。',confirmation_id='qa-extra2-browser-restore-current',operation_id='qa-extra2-browser-restore-current',expected_base_sha256=expected)
for idx, title, body, validity in [(1007,'霁川废止预算规则','霁川项目的废止预算上限为 4.1 万元，仅供历史核对。','invalid')]:
    metadata={'id':str(UUID(int=idx)),'title':title,'role':'knowledge','kind':'topic','line_id':str(line.id),'project_id':str(project.id),'validity':validity}
    try:
        existing=next(page for page in list_pages(ROOT) if page.page_id==UUID(int=idx)); expected=existing.content_sha256
    except StopIteration: expected=None
    writer.confirm(ROOT,metadata=metadata,body=body,confirmation_id=f'qa-extra2-confirm-{idx}',operation_id=f'qa-extra2-write-{idx}',expected_base_sha256=expected)
profile=Path(current['local_profile_dir']); service=QueryService(IndexStore(profile/'index.sqlite3'),FakeEmbedding()); mode='incremental'; plan=service.plan(ROOT,fingerprint=fp,mode=mode); result=service.execute_plan(ROOT,plan); service.close()
print(json.dumps({'workspace_id':current['workspace_id'],'current_profile':str(profile),'index':result.model_dump(mode='json'),'pages':[(str(p.page_id),p.validity,p.approval_state) for p in list_pages(ROOT)]},ensure_ascii=False))
