# backend/src/notes/dependencies.py
"""노트 서비스 의존성 주입."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.notes.repository import NoteRepository
from src.notes.service import NoteService


async def get_note_service(
    session: AsyncSession = Depends(get_async_session),
) -> NoteService:
    embedding_repo = EmbeddingRepository(session)
    return NoteService(
        repo=NoteRepository(session),
        embedding_service=EmbeddingService(embedding_repo),
    )
