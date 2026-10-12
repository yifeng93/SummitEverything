from pathlib import Path
from uuid import UUID
import json
from summit_everything.workspace.reader import read_page
root=Path('.local/qa/m3-package-2-extra-2/workspace-A').resolve(); page=read_page(root,UUID(int=1001)); path=root/page.relative_path; before=page.content_sha256
raw=path.read_text(encoding='utf-8'); path.write_text(raw.replace('18 万元','21 万元'),encoding='utf-8')
after=read_page(root,UUID(int=1001)).content_sha256
print(json.dumps({'page_id':str(page.page_id),'expected_sha256':before,'actual_sha256':after,'changed':before!=after},ensure_ascii=False))
