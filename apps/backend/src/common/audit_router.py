# Sprint 24 Wave 2 T-AUDIT-VIEW (BUG-POW-008) — Settings Audit 탭 read endpoint
"""ItemPromotionAudit 조회 endpoint — Settings 4번째 Audit 탭 (admin only).

Sprint 23 D4 의 4 도메인 promote 흐름이 ItemPromotionAudit 에 row 를 적재하지만
사용자가 자기 workspace 의 promote 이력을 볼 read endpoint 가 없었음 (BUG-POW-008).
admin/owner 만 노출 — workspace 내 cross-tenant 데이터가 음성·문서로 들어왔는지
audit trail 로 확인. viewer/member 는 403.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.rbac import require_admin
from src.common.audit_repository import ItemPromotionAuditRepository
from src.common.audit_schemas import AuditPromotionItem, AuditPromotionPage
from src.common.database import get_async_session
from src.workspaces.models import WorkspaceMember

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/audit",
    tags=["audit"],
)


@router.get("/promotions", response_model=AuditPromotionPage)
async def list_promotions(
    workspace_id: uuid.UUID,
    item_type: str | None = Query(default=None, alias="itemType"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    member: WorkspaceMember = Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
) -> AuditPromotionPage:
    """target_workspace = path workspace 인 ItemPromotionAudit 조회 (cursor 페이지).

    - admin/owner 만 (RBAC 가 require_admin 으로 강제, 403 fall-through).
    - item_type ∈ {meeting, note, inbox, action} 또는 미지정 → 모두.
    - cursor = 직전 응답의 nextCursor (created_at ISO). 첫 페이지는 미지정.
    - 다음 페이지 존재 시 nextCursor 반환 (마지막 row 의 created_at).
    """
    repo = ItemPromotionAuditRepository(session)
    rows = await repo.find_by_workspace(
        workspace_id=workspace_id,
        item_type=item_type,
        limit=limit + 1,  # has-more 판단용 +1
        before_created_at=cursor,
    )
    has_more = len(rows) > limit
    page_rows = rows[:limit]

    items = [
        AuditPromotionItem(
            id=str(r.id),
            itemType=r.item_type,
            sourceItemId=str(r.source_item_id),
            newItemId=str(r.new_item_id),
            sourceWorkspaceId=str(r.source_workspace_id),
            targetWorkspaceId=str(r.target_workspace_id),
            promotedByUserId=str(r.promoted_by_user_id),
            embeddingStatus=r.embedding_status,
            createdAt=r.created_at,
        )
        for r in page_rows
    ]
    next_cursor = (
        page_rows[-1].created_at.isoformat()
        if has_more and page_rows
        else None
    )
    return AuditPromotionPage(items=items, nextCursor=next_cursor)
