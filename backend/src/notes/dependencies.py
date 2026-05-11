# backend/src/notes/dependencies.py
"""노트 서비스 의존성 주입 — ADR-014 옵션 A 정합 (D-2 부채 해소).

NoteService = 순수 CRUD. NotePipelineService = embedding orchestrator + 권한 검증.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.notes.pipeline_service import NotePipelineService
from src.notes.repository import NoteRepository
from src.notes.service import NoteService
from src.projects.repository import ProjectRepository


async def get_note_service(
    session: AsyncSession = Depends(get_async_session),
) -> NoteService:
    return NoteService(repo=NoteRepository(session))


async def get_note_pipeline_service(
    session: AsyncSession = Depends(get_async_session),
) -> NotePipelineService:
    embedding_repo = EmbeddingRepository(session)
    return NotePipelineService(
        note_repo=NoteRepository(session),
        embedding_service=EmbeddingService(embedding_repo),
        project_repo=ProjectRepository(session),
    )
