from __future__ import annotations
import json, os
from pathlib import Path
import httpx
base = Path(os.environ['QA_M3_BASE'])
token = os.environ['QA_M3_SESSION_TOKEN']
for port, root, name in [(18373, base/'workspace-A', 'qa-extra2-open-A'), (18375, base/'workspace-A', 'qa-extra2-open-B')]:
    with httpx.Client(base_url=f'http://127.0.0.1:{port}/api/v1', headers={'Authorization': f'Bearer {token}'}) as c:
        r = c.post('/workspaces', json={'root': str(root), 'mode': 'open', 'operation_id': name})
        print(json.dumps({'port':port, 'status':r.status_code, 'body':r.json()},ensure_ascii=False))
        assert r.status_code in {200, 201}, r.text
