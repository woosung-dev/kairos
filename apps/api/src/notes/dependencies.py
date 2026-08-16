# apps/api/src/notes/dependencies.py
"""노트 서비스 의존성 주입 — ADR-014 옵션 A 정합 (D-2 부채 해소).

NoteService = 순수 CRUD. NotePipelineService = embedding orchestrator + 권한 검증.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session, get_session_factory
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.notes.pipeline_service import NotePipelineService
from src.notes.repository import NoteRepository
from src.notes.service import NoteService
from src.projects.repository import ProjectRepository


async def get_note_service(
    session: AsyncSession = Depends(get_async_session),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> NoteService:
    # Sprint 23 D4 (Task 2 Step 2.3): workspace_repo + session_factory 주입.
    # promote 흐름 (cross-workspace 검증 + BG embedding 복제) 필수.
    # Codex F-2: secondary FK (project_id) cross-tenant 검증용 project_repo 주입.
    from src.workspaces.repository import WorkspaceRepository

    return NoteService(
        repo=NoteRepository(session),
        project_repo=ProjectRepository(session),
        workspace_repo=WorkspaceRepository(session),
        session_factory=session_factory,
    )


async def get_note_pipeline_service(
    session: AsyncSession = Depends(get_async_session),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> NotePipelineService:
    # P0 fix (2026-06-01): session_factory 주입 — embed_note_async(BG task)가
    # request-scoped 세션 대신 fresh 세션을 쓰도록 (meetings 패턴 정합).
    # delete_note_with_cleanup / check_project_access 는 동기 await 라 request 세션 유지.
    embedding_repo = EmbeddingRepository(session)
    return NotePipelineService(
        note_repo=NoteRepository(session),
        embedding_service=EmbeddingService(embedding_repo),
        project_repo=ProjectRepository(session),
        session_factory=session_factory,
    )
