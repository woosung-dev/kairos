# backend/src/actions/router.py
"""ActionItem 라우터 — HTTP 전용."""
import uuid

from fastapi import APIRouter, Depends, Query

from src.auth.rbac import require_member, require_viewer
from src.workspaces.models import WorkspaceMember
from src.actions.dependencies import get_action_service
from src.actions.schemas import CreateActionItemRequest, UpdateActionItemRequest
from src.actions.service import ActionItemService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/action-items",
    tags=["action-items"],
)


@router.get("")
async def list_action_items(
    workspace_id: uuid.UUID,
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    project_id: uuid.UUID | None = Query(default=None, alias="projectId"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    member: WorkspaceMember = Depends(require_viewer),
    service: ActionItemService = Depends(get_action_service),
):
    return await service.list_action_items(
        workspace_id, status=status, priority=priority, project_id=project_id, page=page, page_size=page_size
    )


@router.post("", status_code=201)
async def create_action_item(
    workspace_id: uuid.UUID,
    data: CreateActionItemRequest,
    member: WorkspaceMember = Depends(require_member),
    service: ActionItemService = Depends(get_action_service),
):
    return await service.create_action_item(
        workspace_id=workspace_id,
        title=data.title,
        description=data.description,
        meeting_id=uuid.UUID(data.meeting_id) if data.meeting_id else None,
        project_id=uuid.UUID(data.project_id) if data.project_id else None,
        assignee_id=uuid.UUID(data.assignee_id) if data.assignee_id else None,
        due_date=data.due_date,
        priority=data.priority,
    )


@router.patch("/{action_id}")
async def update_action_item(
    workspace_id: uuid.UUID,
    action_id: uuid.UUID,
    data: UpdateActionItemRequest,
    member: WorkspaceMember = Depends(require_member),
    service: ActionItemService = Depends(get_action_service),
):
    return await service.update_action_item(
        action_id=action_id,
        workspace_id=workspace_id,
        title=data.title,
        description=data.description,
        project_id=uuid.UUID(data.project_id) if data.project_id else None,
        assignee_id=uuid.UUID(data.assignee_id) if data.assignee_id else None,
        due_date=data.due_date,
        priority=data.priority,
        status=data.status,
    )
