# backend/src/inbox/repository.py
"""Inbox Repository — AsyncSession 유일 보유자."""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, select

from src.inbox.models import InboxItem


class InboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_id(
        self, inbox_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> InboxItem | None:
        """헌법 I-9 (Codex F-1): inbox_id + workspace_id 동시 필터."""
        return (await self.session.exec(
            select(InboxItem).where(
                InboxItem.id == inbox_id,
                InboxItem.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        is_processed: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[InboxItem]:
        stmt = select(InboxItem).where(InboxItem.workspace_id == workspace_id)
        if is_processed is not None:
            stmt = stmt.where(InboxItem.is_processed == is_processed)
        stmt = stmt.order_by(InboxItem.created_at.desc())
        stmt = stmt.offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        is_processed: bool | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(InboxItem)
            .where(InboxItem.workspace_id == workspace_id)
        )
        if is_processed is not None:
            stmt = stmt.where(InboxItem.is_processed == is_processed)
        return (await self.session.exec(stmt)).one()

    async def save(self, item: InboxItem) -> InboxItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def commit(self) -> None:
        await self.session.commit()
