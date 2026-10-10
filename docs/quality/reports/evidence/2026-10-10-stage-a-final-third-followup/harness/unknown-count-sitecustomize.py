"""External QA-only Fake provider fixture for Stage A round three."""
import json
import os
from datetime import datetime
from pathlib import Path

from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.integrations.feishu.provider import FeishuError, Material, MaterialBody, MaterialPage

TRACE = Path(os.environ["SUMMIT_QA_TRACE_PATH"])
REMOTE = Path(os.environ["SUMMIT_QA_REMOTE_ROOT"])
GOOD_BYTES = b"SYNTHETIC GOOD BODY\r\nExact bytes for round-three import verification.\r\n"

def _count_remote(root=REMOTE):
    p = Path(root) / "simulated_remote_tasks.json"
    if not p.exists():
        return {"tasks": 0, "results": 0}
    data = json.loads(p.read_text())
    return {"tasks": len(data.get("tasks", {})), "results": len(data.get("results", {}))}

def _record(event, **kwargs):
    TRACE.parent.mkdir(parents=True, exist_ok=True)
    with TRACE.open("a") as f:
        f.write(json.dumps({"event": event, **kwargs}, sort_keys=True) + "\n")

_original_init = FakeFeishu.__init__
def _init(self, simulated_remote_root=None):
    _original_init(self, REMOTE)
    _record("provider_init", remote_root=str(self.simulated_remote_root))
FakeFeishu.__init__ = _init

def _materials(self, credentials, query, visibility, cursor, limit):
    rows = [
        Material(material_id="qa-round3-good-body", title="QA Round 3 good body item", visibility="owner", updated_at=datetime.fromisoformat("2026-10-10T08:00:00+08:00")),
        Material(material_id="qa-round3-bad-body", title="QA Round 3 bad body item", visibility="shared", updated_at=datetime.fromisoformat("2026-10-10T08:00:00+08:00")),
    ]
    selected = [r for r in rows if query.casefold() in r.title.casefold() and (visibility is None or visibility == r.visibility)]
    offset = int(cursor.removeprefix("fake-page-")) if cursor else 0
    end = offset + limit
    return MaterialPage(items=selected[offset:end], next_cursor=f"fake-page-{end}" if end < len(selected) else None)
FakeFeishu.materials = _materials

_original_body = FakeFeishu.body
def _body(self, credentials, material_id):
    _record("body_call", material_id=material_id)
    if material_id == "qa-round3-bad-body":
        raise FeishuError("provider_timeout")
    if material_id == "qa-round3-good-body":
        return MaterialBody(raw=GOOD_BYTES, filename="qa-round3-good.txt", content_type="text/plain; charset=utf-8")
    return _original_body(self, credentials, material_id)
FakeFeishu.body = _body

_original_create = FakeFeishu.task_create
def _task_create(self, credentials, body):
    root = self.simulated_remote_root
    before = _count_remote(root)
    _record("task_create_before", summary=body.get("summary"), counts=before, remote_root=str(root))
    result = _original_create(self, credentials, body)
    after = _count_remote(root)
    _record("task_create_persisted", summary=body.get("summary"), counts=after, remote_root=str(root))
    if body.get("summary") == "QA round3 unknown exact count":
        _record("synthetic_timeout_raised", summary=body.get("summary"), counts=_count_remote(root), remote_root=str(root))
        raise TimeoutError("synthetic lost response after remote persistence")
    return result
FakeFeishu.task_create = _task_create

_original_result = FakeFeishu.task_result
def _task_result(self, credentials, token):
    root = self.simulated_remote_root
    _record("task_result_read_before", counts=_count_remote(root), remote_root=str(root))
    result = _original_result(self, credentials, token)
    _record("task_result_read_after", found=result is not None, counts=_count_remote(root), remote_root=str(root))
    return result
FakeFeishu.task_result = _task_result
