# backend/src/inbox/router.py
"""Inbox 라우터 — HTTP 전용."""
import uuid

from fastapi import APIRouter, Depends, Query

from src.auth.rbac import require_member, require_viewer
from src.workspaces.models import WorkspaceMember
from src.inbox.dependencies import get_inbox_service
from src.inbox.schemas import ClassifyInboxRequest
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
    return await service.classify(inbox_id, project_ids)


@router.post("/{inbox_id}/dismiss")
async def dismiss_inbox(
    workspace_id: uuid.UUID,
    inbox_id: uuid.UUID,
    member: WorkspaceMember = Depends(require_member),
    service: InboxService = Depends(get_inbox_service),
):
    return await service.dismiss(inbox_id)
