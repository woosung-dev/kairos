# apps/api/src/inbox/repository.py
"""Inbox Repository — AsyncSession 유일 보유자."""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, or_, select

from src.common.promote_models import ItemPromotionAudit
from src.common.visibility import RequesterContext, meeting_access_clause
from src.inbox.models import InboxItem


def _inbox_visibility_filter(
    stmt,
    requester_user_id: uuid.UUID | None,
    requester_role: str | None,
):
    """C-015 (2026-09-26 정검): 회의 요약 인박스 항목에 원본 회의 가시성 적용.

    source_type='meeting' 항목의 요약은 회의 내용 그 자체다 — 회의를 못 보는 사용자는
    항목도 못 본다. 그 외 source_type(promote 사본 'attachment' 등)은 통과.
    role=None 내부호출 skip / admin·owner 우회 (meetings 게이트와 같은 계보).
    """
    ctx = RequesterContext(requester_user_id, requester_role)
    if ctx.is_internal or ctx.is_admin:
        return stmt
    return stmt.where(
        or_(
            InboxItem.source_type != "meeting",
            meeting_access_clause(InboxItem.source_id, ctx.user_id),
        )
    )


class InboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(
        self,
        inbox_id: uuid.UUID,
        workspace_id: uuid.UUID,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> InboxItem | None:
        """헌법 I-9 (Codex F-1): inbox_id + workspace_id 동시 필터.

        C-015: requester 를 넘기면 목록과 같은 회의 가시성 규칙 적용 (안 보이면 None → 404).
        """
        stmt = select(InboxItem).where(
            InboxItem.id == inbox_id,
            InboxItem.workspace_id == workspace_id,
        )
        stmt = _inbox_visibility_filter(stmt, requester_user_id, requester_role)
        return (await self.session.exec(stmt)).one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        is_processed: bool | None = None,
        offset: int = 0,
        limit: int = 20,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> list[InboxItem]:
        stmt = select(InboxItem).where(InboxItem.workspace_id == workspace_id)
        if is_processed is not None:
            stmt = stmt.where(InboxItem.is_processed == is_processed)
        stmt = _inbox_visibility_filter(stmt, requester_user_id, requester_role)
        stmt = stmt.order_by(InboxItem.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        is_processed: bool | None = None,
        requester_user_id: uuid.UUID | None = None,
        requester_role: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(InboxItem)
            .where(InboxItem.workspace_id == workspace_id)
        )
        if is_processed is not None:
            stmt = stmt.where(InboxItem.is_processed == is_processed)
        # 목록과 같은 필터 (B-15 ② list/count 동일 계약).
        stmt = _inbox_visibility_filter(stmt, requester_user_id, requester_role)
        return (await self.session.exec(stmt)).one()

    async def save(self, item: InboxItem) -> InboxItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def commit(self) -> None:
        await self.session.commit()

    # ── Sprint 23 D4 Task 2 Step 2.4: promote 지원 메서드 ──

    async def save_promoted_inbox_item(self, item: InboxItem) -> InboxItem:
        """promote 복제본 InboxItem INSERT — workspace_id 는 호출자가 target 으로 설정.

        save() 와 시그니처 동일하지만, promote 흐름에서 명시적으로 호출 출처 분리.
        I-9 검증은 호출자 (service.promote) 가 사전에 target workspace 멤버십을 확인.
        """
        self.session.add(item)
        await self.session.flush()
        return item

    async def save_item_promotion_audit(
        self, audit: ItemPromotionAudit
    ) -> ItemPromotionAudit:
        """4 도메인 공통 ItemPromotionAudit INSERT — commit 은 호출자."""
        self.session.add(audit)
        await self.session.flush()
        return audit
