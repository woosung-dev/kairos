# Memory DB 접근 — AsyncSession 유일 보유자
"""Memory Repository — DB access only.

backend rules §3 — AsyncSession은 Repository만 보유. service는 import 금지.
"""
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.memory.models import MemoryAICall, MemoryEvent, MemoryItem


class MemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_item(self, item: MemoryItem) -> MemoryItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def get_by_id(
        self, memory_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> MemoryItem | None:
        stmt = select(MemoryItem).where(
            MemoryItem.id == memory_id,
            MemoryItem.workspace_id == workspace_id,
            MemoryItem.deleted_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_distilled(
        self,
        memory_id: uuid.UUID,
        distilled_json: dict,
        status: str,
    ) -> None:
        await self.session.execute(
            update(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .values(distilled_json=distilled_json, status=status)
        )

    async def update_embedding(
        self,
        memory_id: uuid.UUID,
        embedding_chunk_id: uuid.UUID,
        status: str,
    ) -> None:
        await self.session.execute(
            update(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .values(embedding_chunk_id=embedding_chunk_id, status=status)
        )

    async def update_status(
        self, memory_id: uuid.UUID, status: str
    ) -> None:
        await self.session.execute(
            update(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .values(status=status)
        )

    async def update_transcript(
        self, memory_id: uuid.UUID, raw_content: str
    ) -> None:
        await self.session.execute(
            update(MemoryItem)
            .where(MemoryItem.id == memory_id)
            .values(raw_content=raw_content)
        )

    async def save_ai_call(self, call: MemoryAICall) -> None:
        self.session.add(call)

    async def save_event(self, event: MemoryEvent) -> None:
        self.session.add(event)

    async def commit(self) -> None:
        await self.session.commit()
