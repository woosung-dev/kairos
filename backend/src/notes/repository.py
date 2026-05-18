# backend/src/notes/repository.py
"""노트 DB 접근."""
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import func, select

from src.notes.models import Note


class NoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save(self, note: Note) -> Note:
        self.session.add(note)
        await self.session.flush()
        return note

    async def find_by_id(
        self, note_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Note | None:
        """헌법 I-9 (Codex F-1): note_id + workspace_id 동시 필터."""
        return (await self.session.exec(
            select(Note).where(
                Note.id == note_id,
                Note.workspace_id == workspace_id,
            )
        )).one_or_none()

    async def find_by_workspace(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Note]:
        stmt = select(Note).where(Note.workspace_id == workspace_id)
        if project_id:
            stmt = stmt.where(Note.project_id == project_id)
        stmt = stmt.order_by(Note.updated_at.desc()).offset(offset).limit(limit)
        return list((await self.session.exec(stmt)).all())

    async def count_by_workspace(
        self,
        workspace_id: uuid.UUID,
        project_id: uuid.UUID | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(Note)
            .where(Note.workspace_id == workspace_id)
        )
        if project_id:
            stmt = stmt.where(Note.project_id == project_id)
        return (await self.session.exec(stmt)).one()

    async def delete(self, note: Note) -> None:
        await self.session.delete(note)
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()
