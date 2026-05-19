# backend/src/inbox/router.py
"""Inbox 라우터 — HTTP 전용."""
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from src.auth.rbac import require_member, require_viewer
from src.workspaces.models import WorkspaceMember
from src.inbox.dependencies import get_inbox_service
from src.inbox.schemas import ClassifyInboxRequest, InboxPromoteIn, InboxPromoteOut
from src.inbox.service import InboxService

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/inbox",
    tags=["inbox"],
)


@router.get("")
async def list_inbox(
    workspace_id: uuid.UUID,
    is_processed: bool | None = Query(default=None, alias="isProcessed"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    member: WorkspaceMember = Depends(require_viewer),
    service: InboxService = Depends(get_inbox_service),
):
    return await service.list_inbox(
        workspace_id,
        is_processed=is_processed,
        page=page,
        page_size=page_size,
    )


@router.post("/{inbox_id}/classify")
async def classify_inbox(
    workspace_id: uuid.UUID,
    inbox_id: uuid.UUID,
    data: ClassifyInboxRequest,
    member: WorkspaceMember = Depends(require_member),
    service: InboxService = Depends(get_inbox_service),
):
    project_ids = [uuid.UUID(pid) for pid in data.project_ids]
    return await service.classify(inbox_id, workspace_id, project_ids)


@router.post("/{inbox_id}/dismiss")
async def dismiss_inbox(
    workspace_id: uuid.UUID,
    inbox_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_member),
    service: InboxService = Depends(get_inbox_service),
):
    return await service.dismiss(inbox_id, workspace_id)


# Sprint 23 D4 Task 2 Step 2.4: inbox promote — I-18 복제 + audit (BG embedding 없음).
@router.post(
    "/{inbox_id}/promote",
    response_model=InboxPromoteOut,
    status_code=202,
)
async def promote_inbox(
    workspace_id: uuid.UUID,
    inbox_id: uuid.UUID,
    body: InboxPromoteIn,
    background_tasks: BackgroundTasks,
    member: WorkspaceMember = Depends(require_member),
    service: InboxService = Depends(get_inbox_service),
) -> InboxPromoteOut:
    """Inbox 아이템 → team workspace 복제 + audit row.

    202 Accepted — InboxItem 은 source_type='inbox' EmbeddingChunk 가 실제 인서트되지 않음
    (whitelist 만 존재) → BG embedding 복제 없음. ItemPromotionAudit.embedding_status='n/a'.
    ai_suggested_project_id 는 복제본에서 None (cross-workspace 제약 — composite FK).
    """
    return await service.promote(
        inbox_id=inbox_id,
        source_workspace_id=workspace_id,
        target_workspace_id=body.target_workspace_id,
        promoted_by_user_id=member.user_id,
        background_tasks=background_tasks,
    )
