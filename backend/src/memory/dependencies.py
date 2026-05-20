# Memory DI 조립 — Depends() 유일 위치
"""Memory dependencies.

backend rules §3 — Depends 조립은 dependencies.py에서만.
session_factory 주입으로 BackgroundTask 내부에서 별도 session 생성 가능.

Sprint 19 PR #1 C10 (Codex F-4): WorkspaceRepository 동반 주입 (promote target 검증).
Sprint 24 Wave 2 BL-006: MemoryPipelineService 동반 주입 (embeddings 호출 격리, 헌법 §4.2).
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session, get_session_factory
from src.common.r2 import R2Service
from src.memory.pipeline_service import MemoryPipelineService
from src.memory.repository import MemoryRepository
from src.memory.service import MemoryService
from src.workspaces.repository import WorkspaceRepository


async def get_memory_repository(
    session: AsyncSession = Depends(get_async_session),
) -> MemoryRepository:
    return MemoryRepository(session)


def get_memory_pipeline_service() -> MemoryPipelineService:
    """Stateless orchestrator — session 은 service 가 자체 BG task 에서 인자로 전달."""
    return MemoryPipelineService()


def get_memory_service(
    session: AsyncSession = Depends(get_async_session),
    session_factory: async_sessionmaker[AsyncSession] = Depends(
        get_session_factory
    ),
    pipeline: MemoryPipelineService = Depends(get_memory_pipeline_service),
) -> MemoryService:
    """동일 session으로 MemoryRepository + WorkspaceRepository 조립.

    Sprint 19 PR #1 C10 (Codex F-4): backend rule §3 회복 — promote target 검증을
    workspace_repo API 로 위임 (service 가 직접 session.execute 사용 금지).
    Sprint 24 Wave 2 BL-006: embeddings 호출은 MemoryPipelineService 경유 (헌법 §4.2 + ADR-014).
    """
    return MemoryService(
        repo=MemoryRepository(session),
        workspace_repo=WorkspaceRepository(session),
        session_factory=session_factory,
        r2_service=R2Service(),
        pipeline=pipeline,
    )
