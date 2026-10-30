import json, os, runpy, statistics, subprocess, tempfile, time
from pathlib import Path
from uuid import uuid4
import summit_everything.workspace.reader as reader
from summit_everything.workspace.reader import WorkspaceError
helper = runpy.run_path('tests/unit/test_page_directory_cache.py')
with tempfile.TemporaryDirectory(prefix='summit-revision-probe-') as temp:
    root, line, project = helper['_workspace'](Path(temp) / 'workspace')
    helper['_page'](root, line, project, '旧正文')
    page = next((root / '模拟线' / '模拟项目').glob('*.md'))
    raw = page.read_text()
    initial_id = str(helper['list_pages'](root)[0].page_id)
    for i in range(179):
        (page.parent / f'合成页-{i}.md').write_text(raw.replace(initial_id, str(uuid4())))
    def reject(*_args): raise AssertionError('Markdown was parsed during revision polling')
    reader._split_markdown = reject
    values=[]
    for _ in range(30):
        start=time.perf_counter(); revision=reader.formal_pages_revision(root); values.append((time.perf_counter()-start)*1000)
    oldstat=page.stat()
    staging=page.with_suffix('.tmp'); staging.write_text(raw.replace('旧正文','新正文'))
    os.utime(staging, ns=(oldstat.st_atime_ns,oldstat.st_mtime_ns)); staging.replace(page)
    same_size_mtime=page.stat().st_size == oldstat.st_size and page.stat().st_mtime_ns == oldstat.st_mtime_ns
    replacement_changed=reader.formal_pages_revision(root)!=revision
    before=reader.formal_pages_revision(root)
    (root/'来源').mkdir(exist_ok=True);(root/'来源'/'忽略.md').write_text('未批准原件')
    (page.parent/'忽略.tmp').write_text('未完成保存')
    ignored=reader.formal_pages_revision(root)==before
    outside=Path(temp)/'outside.md';outside.write_text('外部文件')
    link=page.parent/'链接.md';link.symlink_to(outside)
    try: reader.formal_pages_revision(root); symlink_rejected=False
    except WorkspaceError: symlink_rejected=True
    result={'candidate':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'pages':180,'samples':len(values),'median_ms':statistics.median(values),'max_ms':max(values),'markdown_parse_calls':0,'same_size_mtime_preserved':same_size_mtime,'atomic_replacement_detected':replacement_changed,'source_tmp_ignored':ignored,'outside_symlink_rejected':symlink_rejected,'fixture_note':'180 metadata polling files derived from one synthetic page with unique IDs; no retrieval assertion'}
    assert same_size_mtime and replacement_changed and ignored and symlink_rejected
    Path('/Users/hanwenbo/ai/SummitEverything/.local/qa/external-watch-20261030/sol-revision-probe.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
