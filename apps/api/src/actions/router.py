# apps/api/src/actions/router.py
"""ActionItem 라우터 — HTTP 전용."""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from src.auth.rbac import require_member, require_member_fresh, require_viewer
from src.workspaces.models import WorkspaceMember
from src.actions.dependencies import get_action_service
from src.actions.schemas import (
    ActionPromoteIn,
    ActionPromoteOut,
    CreateActionItemRequest,
    UpdateActionItemRequest,
)
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
        workspace_id, status=status, priority=priority, project_id=project_id, page=page, page_size=page_size,
        # F1: project visibility 게이트 (비-멤버 private/draft 액션 누출 차단).
        requester_user_id=member.user_id, requester_role=member.role,
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
    member: WorkspaceMember = Depends(require_member_fresh),
    service: ActionItemService = Depends(get_action_service),
):
    return await service.update_action_item(
        action_id=action_id,
        workspace_id=workspace_id,
        title=data.title,
        description=data.description,
        # Codex F-2 2차: meeting 재배정 forwarding (C7 추가)
        meeting_id=uuid.UUID(data.meeting_id) if data.meeting_id else None,
        project_id=uuid.UUID(data.project_id) if data.project_id else None,
        assignee_id=uuid.UUID(data.assignee_id) if data.assignee_id else None,
        due_date=data.due_date,
        priority=data.priority,
        status=data.status,
        # F2: SOURCE 액션 project visibility 게이트 (비-멤버 write IDOR 차단).
        requester_user_id=member.user_id,
        requester_role=member.role,
    )


# Sprint 23 D4 Task 2 Step 2.5: action promote — I-18 복제 + audit (BG embedding 없음).
@router.post(
    "/{action_id}/promote",
    response_model=ActionPromoteOut,
    status_code=202,
)
async def promote_action(
    workspace_id: uuid.UUID,
    action_id: uuid.UUID,
    body: ActionPromoteIn,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member),
    service: ActionItemService = Depends(get_action_service),
) -> ActionPromoteOut:
    """ActionItem → team workspace 복제 + audit row.

    202 Accepted — ActionItem 은 임베딩 ledger 부재 → BG embedding 복제 없음.
    ItemPromotionAudit.embedding_status='n/a'. meeting_id / project_id / assignee_id
    모두 복제본에서 None reset (composite FK 제약 + 단순화).
    """
    return await service.promote(
        action_id=action_id,
        source_workspace_id=workspace_id,
        target_workspace_id=body.target_workspace_id,
        promoted_by_user_id=member.user_id,
        background_tasks=background_tasks,
    )
