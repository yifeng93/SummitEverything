from __future__ import annotations
import json, uuid, sys, os
from datetime import UTC, datetime
from pathlib import Path
import yaml, httpx
BASE=Path(__file__).resolve().parents[1]
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'src'))
from summit_everything.domain.content import content_sha256
from summit_everything.integrations.embedding import FakeEmbedding
from summit_everything.retrieval.query import QueryService
from summit_everything.retrieval.store import IndexStore
from summit_everything.workspace.manifest import load_manifest, open_workspace
workspace=BASE/'workspace-A'; manifest=load_manifest(workspace); line=manifest.lines[0]; project=manifest.projects[0]
items=[
 ('pending','knowledge','current',False,'无批准合成正文：紫楠条目标识 PENDING-R2-551。'),
 ('source','source','current',True,'原件合成正文：白榆条目标识 SOURCE-R2-552。'),
 ('draft','draft','current',True,'待审合成正文：墨竹条目标识 DRAFT-R2-553。'),
 ('invalid','knowledge','invalid',True,'失效合成正文：石杉条目标识 INVALID-R2-554。'),
]
page_ids={}; outdir=workspace/project.directory/'QA包2修复2信任边界'
outdir.mkdir(parents=True,exist_ok=True)
for i,(label,role,validity,approved,body) in enumerate(items):
 pid=str(uuid.uuid5(uuid.NAMESPACE_URL,'qa-r2-trust-'+label));page_ids[label]=pid
 metadata={'id':pid,'title':f'R2 合成{label}记录','role':role,'kind':'topic','line_id':str(line.id),'project_id':str(project.id),'validity':validity}
 if approved:
  metadata['approval']={'version':1,'content_sha256':content_sha256(metadata,body),'confirmed_at':datetime.now(UTC).isoformat(),'confirmation_id':'qa-r2-trust-'+label}
 (outdir/f'{label}.md').write_text('---\n'+yaml.safe_dump(metadata,allow_unicode=True,sort_keys=False)+'---\n'+body,encoding='utf-8')
context=open_workspace(workspace,BASE/'profiles-r2-A')
service=QueryService(IndexStore(Path(context.local_profile_dir)/'index.sqlite3'),FakeEmbedding())
fp='summit-fake-embedding-v1'; active=service.store.active_fingerprint(manifest.workspace_id); mode='incremental' if active==fp else 'initial'
plan=service.plan(workspace,fingerprint=fp,mode=mode); index=service.execute_plan(workspace,plan); service.close()
api='http://127.0.0.1:18793/api/v1'; client=httpx.Client(headers={'Authorization':f'Bearer {os.environ["QA_M3_SESSION_TOKEN"]}'},timeout=30)
results={'case':'C13-hard-trust-boundaries','page_ids':page_ids,'index':{'mode':mode,'indexed_pages':index.indexed_pages,'indexed_chunks':index.indexed_chunks,'embedded_chunks':index.embedded_chunks,'reused_chunks':index.reused_chunks},'checks':{}}
queries={'pending':'紫楠条目标识是什么？','source':'白榆条目标识是什么？','draft':'墨竹条目标识是什么？','invalid':'石杉条目标识是什么？'}
for purpose in ['current','history']:
 for label,question in queries.items():
  r=client.post(api+'/queries',json={'request_id':str(uuid.uuid4()),'question':question,'fingerprint':fp,'purpose':purpose,'answer_mode':'fact'})
  events=[json.loads(line[6:]) for line in r.text.splitlines() if line.startswith('data: ')]
  done=next(e['data'] for e in events if e['type']=='completed')
  ids=[x['page_id'] for x in done['citations']]
  results['checks'][f'{purpose}:{label}']={'http':r.status_code,'citation_ids':ids,'target_cited':page_ids[label] in ids,'validities':[x['validity'] for x in done['citations']],'availability':[x['availability'] for x in done['citations']]}
results['expected']={'current_target_citation':False,'history_allows_only_approved_invalid':True}
(BASE/'harness/trust-boundary-r2-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(results,ensure_ascii=False,indent=2))
