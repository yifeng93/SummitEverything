from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID
import summit_everything.intake.review as module
from summit_everything.intake.review import IntakeReviewService
from summit_everything.intake.sources import IntakeService
from summit_everything.workspace.manifest import create_workspace, create_line, create_project
from summit_everything.workspace.transactions import atomic_write as real_atomic_write

with TemporaryDirectory() as td:
    base=Path(td); root=base/'workspace'
    context=create_workspace(root,'MCP recovery probe',base/'profiles','workspace-create')
    line=create_line(root,'主线','line'); project=create_project(root,line.id,'项目','project')
    item=IntakeService().add_text(root,'合成来源待确认。',filename='source.txt',operation_id='source')
    svc=IntakeReviewService(); args=dict(operation_id='same-op',item_ids=[item.item_id],line_id=line.id,project_id=project.id,title='草稿',kind='topic',body='待审核正文。',workspace_id=context.workspace_id)
    def fail_at_job(path:Path, data:bytes)->None:
        if path.parent.name=='jobs': raise OSError('injected after draft')
        real_atomic_write(path,data)
    module.atomic_write=fail_at_job
    try: svc.create_agent_draft(root,**args)
    except OSError: pass
    else: raise AssertionError('fault injection did not fire')
    visible=svc.list_drafts(root,pending_only=True)
    draft=visible[0]
    print(f'after_draft_before_job: visible={len(visible)} state={draft.state} job_id={draft.job_id}')
    got=svc.get_draft(root,draft.draft_id)
    print(f'get_before_recovery: visible_state={got.state}')
    confirmed=svc.confirm_draft(root,draft.draft_id,expected_version=1,confirmation_id='simulated-user-click',operation_id='confirm-before-retry',conflict_resolutions={})
    print(f'confirm_before_recovery: result={confirmed.state}')
    module.atomic_write=real_atomic_write
    replay=svc.create_agent_draft(root,**args)
    print(f'replay: idempotent={replay.draft_id==draft.draft_id} state={replay.state} version={replay.version}')
    print(f'replay_after_confirmation: preserved={replay.state=="confirmed"} source_states={[x.state for x in IntakeService().list_items(root)]}')
