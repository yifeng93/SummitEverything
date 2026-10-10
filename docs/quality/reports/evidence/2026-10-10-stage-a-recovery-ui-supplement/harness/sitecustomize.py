"""External QA-only fault harness for Stage A round four; Fake provider only."""
from __future__ import annotations
import json, os, time
from pathlib import Path
from datetime import datetime
from summit_everything.integrations.feishu.fake import FakeFeishu
from summit_everything.workspace import transactions
from summit_everything.workspace import action_receipts

REMOTE = Path(os.environ['SUMMIT_QA_REMOTE_ROOT'])
TRACE = Path(os.environ['SUMMIT_QA_TRACE_PATH'])
CONTROL = Path(os.environ['SUMMIT_QA_CONTROL_PATH'])
REMOTE.mkdir(parents=True, exist_ok=True)


def _record(event, **data):
    TRACE.parent.mkdir(parents=True, exist_ok=True)
    with TRACE.open('a', encoding='utf-8') as out:
        out.write(json.dumps({'event': event, **data}, sort_keys=True) + '\n')

def _counts():
    path = REMOTE / 'simulated_remote_tasks.json'
    if not path.exists(): return {'tasks': 0, 'results': 0}
    value = json.loads(path.read_text())
    return {'tasks': len(value.get('tasks', {})), 'results': len(value.get('results', {}))}

def _active_control():
    try: return json.loads(CONTROL.read_text())
    except (OSError, ValueError): return {'mode': None, 'fired': False}

def _fire(mode, **fields):
    value = _active_control()
    if value.get('mode') != mode or value.get('fired'): return False
    value['fired'] = True
    CONTROL.write_text(json.dumps(value, sort_keys=True))
    _record('fault_fired', mode=mode, **fields)
    return True

_orig_init = FakeFeishu.__init__
def _init(self, simulated_remote_root=None):
    _orig_init(self, REMOTE)
FakeFeishu.__init__ = _init

_orig_create = FakeFeishu.task_create
def _task_create(self, credentials, body):
    summary = body.get('summary', '')
    before = _counts()
    _record('task_create_before', summary=summary, counts=before)
    if summary == 'QA R4 concurrent double': time.sleep(2.5)
    result = _orig_create(self, credentials, body)
    after = _counts()
    _record('task_create_persisted', summary=summary, counts=after)
    if summary in {'QA R4 mismatch result', 'QA supplement mismatch'}:
        _record('task_create_mismatch_response', summary=summary)
        return result.model_copy(update={'summary': 'synthetic provider mismatch'})
    if summary == 'QA R4 unknown timeout':
        _record('task_create_timeout_after_persist', summary=summary, counts=after)
        raise TimeoutError('synthetic lost response after persisted result')
    if summary == 'QA R4 process exit':
        _record('task_create_process_exit_after_persist', summary=summary, counts=after)
        os._exit(72)
    return result
FakeFeishu.task_create = _task_create

_orig_atomic = transactions.atomic_write
def _atomic_write(path, content):
    path = Path(path)
    # Real temp-file write and fsync followed by injected interruption before os.replace.
    ctl = _active_control()
    if ctl.get('mode') == 'atomic_manifest_before_replace' and not ctl.get('fired') and path.name == 'manifest.json':
        import tempfile
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=f'.{path.name}.qa-interrupt.', dir=path.parent)
        try:
            with os.fdopen(fd, 'wb') as temp:
                temp.write(content); temp.flush(); os.fsync(temp.fileno())
            _fire('atomic_manifest_before_replace', target=path.name, temp_written=True)
            raise OSError('QA injected interruption before atomic replace')
        finally:
            if os.path.exists(temp_name): os.unlink(temp_name)
    _orig_atomic(path, content)
transactions.atomic_write = _atomic_write

_orig_receipt_atomic = action_receipts.atomic_write
def _receipt_atomic_write(path, content):
    path = Path(path)
    try: doc = json.loads(content)
    except (ValueError, TypeError): doc = {}
    if path.parent.name == 'active' and doc.get('state') == 'succeeded' and _fire('receipt_success_write_failure', action_id=doc.get('action_id')):
        raise OSError('QA injected failed success-receipt write')
    _orig_receipt_atomic(path, content)
    if path.name == 'summary.json' and _fire('archive_after_summary_before_delete', target=path.name):
        raise OSError('QA injected interruption after monthly summary replace')
action_receipts.atomic_write = _receipt_atomic_write

_orig_delete = action_receipts.atomic_delete
def _receipt_delete(path):
    if Path(path).parent.name == 'active' and _fire('archive_delete_interruption', target=Path(path).name):
        raise OSError('QA injected interruption before active receipt delete')
    _orig_delete(path)
action_receipts.atomic_delete = _receipt_delete

_record('harness_ready', pid=os.getpid(), remote_root=str(REMOTE))

_orig_patch = FakeFeishu.task_patch
def _task_patch(self, credentials, guid, body, token):
    _record('task_patch_before', task_guid=guid, update_fields=body.get('update_fields'))
    result = _orig_patch(self, credentials, guid, body, token)
    _record('task_patch_after', task_guid=guid, update_fields=body.get('update_fields'))
    return result
FakeFeishu.task_patch = _task_patch
