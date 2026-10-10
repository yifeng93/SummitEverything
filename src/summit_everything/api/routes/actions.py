"""Action routes are separate from knowledge confirmation routes."""

from collections.abc import Callable
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Query

from summit_everything.domain.models import WorkspaceContext
from summit_everything.intake.actions import (
    Action,
    ActionConfirmation,
    ActionEdit,
    ActionPage,
    ActionProposal,
    ActionService,
    UserOutcome,
)
from summit_everything.integrations.feishu.tasks import FeishuTask, FeishuTasks, TaskPage


def register_actions(
    app: FastAPI,
    actions: ActionService,
    tasks: FeishuTasks,
    authenticated: Callable[..., None],
    active_workspace: Callable[..., WorkspaceContext],
) -> None:
    @app.post("/api/v1/actions", status_code=201, dependencies=[Depends(authenticated)])
    def propose(
        payload: ActionProposal, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> Action:
        return actions.propose(Path(workspace.root), payload)

    @app.get("/api/v1/action-intents", dependencies=[Depends(authenticated)])
    def list_actions(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        cursor: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
    ) -> ActionPage:
        return actions.list(Path(workspace.root), cursor, limit)

    @app.get("/api/v1/actions/{action_id}", dependencies=[Depends(authenticated)])
    def get_action(
        action_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> Action:
        return actions.get(Path(workspace.root), action_id)

    @app.patch("/api/v1/actions/{action_id}", dependencies=[Depends(authenticated)])
    def edit_action(
        action_id: UUID,
        payload: ActionEdit,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Action:
        return actions.edit(Path(workspace.root), action_id, payload)

    @app.post("/api/v1/actions/{action_id}/confirmations", dependencies=[Depends(authenticated)])
    def confirm_action(
        action_id: UUID,
        payload: ActionConfirmation,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Action:
        return actions.confirm(Path(workspace.root), action_id, payload)

    @app.post("/api/v1/actions/{action_id}/executions", dependencies=[Depends(authenticated)])
    def execute_action(
        action_id: UUID,
        payload: ActionConfirmation,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Action:
        return actions.execute(Path(workspace.root), action_id, payload)

    @app.post("/api/v1/actions/{action_id}/reconciliations", dependencies=[Depends(authenticated)])
    def reconcile_action(
        action_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> Action:
        return actions.reconcile(Path(workspace.root), action_id)

    @app.post("/api/v1/actions/{action_id}/outcomes", dependencies=[Depends(authenticated)])
    def outcome_action(
        action_id: UUID,
        payload: UserOutcome,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Action:
        return actions.outcome(Path(workspace.root), action_id, payload)

    @app.get("/api/v1/integrations/feishu/tasks", dependencies=[Depends(authenticated)])
    def task_list(
        cursor: str | None = None, limit: int = Query(default=20, ge=1, le=100)
    ) -> TaskPage:
        return tasks.list(cursor, limit)

    @app.get("/api/v1/integrations/feishu/tasks/{task_guid}", dependencies=[Depends(authenticated)])
    def task_get(task_guid: str) -> FeishuTask:
        return tasks.get(task_guid)
