from pathlib import Path
import json,hashlib,re,sqlite3,yaml
from dataclasses import asdict
from summit_everything.domain.content import retrieval_eligibility,StorageArea
root=Path.cwd(); e=root/'docs/quality/reports/evidence/2026-10-11-stage-b-independent-ui-qa';w=root/'.local/qa-ui/workspace';p=root/'.local/qa-ui/profile'
page=next(w.glob('合成*/*/*.md'));raw=page.read_text();_,fm,body=raw.split('---',2);body=body.lstrip('\n');meta=yaml.safe_load(fm);gate=retrieval_eligibility(meta,body,area=StorageArea.FORMAL);assert gate.eligible
source=next(w.glob('原件/*/*.md'));assert '24 人' in source.read_text()
before=json.loads((e/'manifest-before-progress.json').read_text());confirmed=json.loads((e/'manifest-confirmed-not-executed.json').read_text());after=json.loads((e/'manifest-after-progress.json').read_text());assert before==confirmed; assert before['projects'][0]['progress_version']==0 and after['projects'][0]['progress_version']==1
settings=json.loads(next(p.rglob('provider-settings.json')).read_text());assert settings['mode']=='real';assert settings['feishu']['app_id']=='cli_synthetic_independent_ui'; assert settings['feishu']['real_data_enabled'] is False
receipts=[json.loads(x.read_text()) for x in (w/'.summit-everything/action_receipts/active').glob('*.json')]; assert len(receipts)==3
sqlite=sqlite3.connect(next(p.rglob('index.sqlite3')));tables=sqlite.execute("select name from sqlite_master where type='table'").fetchall();counts={t[0]:sqlite.execute('select count(*) from "'+t[0]+'"').fetchone()[0] for t in tables};sqlite.close()
requests=re.findall(r'INFO: +127\.0\.0\.1:\d+ - "(\w+) ([^ ]+) HTTP/1\.1" (\d+)',(root/'.local/qa-ui/browser-server.log').read_text());assert requests and all(int(x[2])<400 or x == ('GET','/api/v1/workspaces/current','409') for x in requests)
smoke=[x for x in requests if x[0]=='POST' and ('provider-smoke' in x[1] or 'smoke' in x[1])];assert not smoke
out={'workspace_id':after['workspace_id'],'formal_file':str(page.relative_to(w)),'eligibility':asdict(gate),'source_count':1,'draft_count':len(list((w/'.summit-everything/drafts').glob('*.json'))),'action_count':len(receipts),'index_counts':counts,'before_progress':before['projects'][0],'after_progress':after['projects'][0],'real_settings':settings,'api_request_count':len(requests),'smoke_post_count':len(smoke),'assertions_pass':True};(e/'disk-assertions.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));(e/'loopback-api-requests.json').write_text(json.dumps(requests,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
