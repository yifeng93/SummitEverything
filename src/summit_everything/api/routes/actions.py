"""Action routes are separate from knowledge confirmation routes."""

from collections.abc import Callable
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, Query, Response

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
from summit_everything.integrations.feishu.tasks import FeishuTask, TaskPage


def register_actions(
    app: FastAPI,
    actions_for: Callable[[WorkspaceContext], ActionService],
    authenticated: Callable[..., None],
    active_workspace: Callable[..., WorkspaceContext],
) -> None:
    @app.post("/api/v1/actions", status_code=201, dependencies=[Depends(authenticated)])
    def propose(
        payload: ActionProposal, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> Action:
        return actions_for(workspace).propose(Path(workspace.root), payload)

    @app.get("/api/v1/action-intents", dependencies=[Depends(authenticated)])
    def list_actions(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        cursor: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
    ) -> ActionPage:
        return actions_for(workspace).list(Path(workspace.root), cursor, limit)

    @app.get("/api/v1/actions/{action_id}", dependencies=[Depends(authenticated)])
    def get_action(
        action_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> Action:
        return actions_for(workspace).get(Path(workspace.root), action_id)

    @app.patch("/api/v1/actions/{action_id}", dependencies=[Depends(authenticated)])
    def edit_action(
        action_id: UUID,
        payload: ActionEdit,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Action:
        return actions_for(workspace).edit(Path(workspace.root), action_id, payload)

    @app.post("/api/v1/actions/{action_id}/confirmations", dependencies=[Depends(authenticated)])
    def confirm_action(
        action_id: UUID,
        payload: ActionConfirmation,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Action:
        return actions_for(workspace).confirm(Path(workspace.root), action_id, payload)

    @app.post("/api/v1/actions/{action_id}/executions", dependencies=[Depends(authenticated)])
    def execute_action(
        action_id: UUID,
        response: Response,
        payload: ActionConfirmation,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Action:
        result = actions_for(workspace).execute(Path(workspace.root), action_id, payload)
        if result.state == "running":
            response.status_code = 202
            response.headers["Location"] = f"/api/v1/actions/{action_id}"
        return result

    @app.post("/api/v1/actions/{action_id}/reconciliations", dependencies=[Depends(authenticated)])
    def reconcile_action(
        action_id: UUID, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> Action:
        return actions_for(workspace).reconcile(Path(workspace.root), action_id)

    @app.post("/api/v1/actions/{action_id}/outcomes", dependencies=[Depends(authenticated)])
    def outcome_action(
        action_id: UUID,
        payload: UserOutcome,
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
    ) -> Action:
        return actions_for(workspace).outcome(Path(workspace.root), action_id, payload)

    @app.get("/api/v1/integrations/feishu/tasks", dependencies=[Depends(authenticated)])
    def task_list(
        workspace: Annotated[WorkspaceContext, Depends(active_workspace)],
        cursor: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
    ) -> TaskPage:
        return actions_for(workspace).tasks.list(cursor, limit)

    @app.get("/api/v1/integrations/feishu/tasks/{task_guid}", dependencies=[Depends(authenticated)])
    def task_get(
        task_guid: str, workspace: Annotated[WorkspaceContext, Depends(active_workspace)]
    ) -> FeishuTask:
        return actions_for(workspace).tasks.get(task_guid)
