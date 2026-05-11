# backend/src/projects/dependencies.py
"""Project 의존성 — Depends() 조립의 유일한 위치."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.repository import WorkspaceRepository


async def get_project_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ProjectRepository:
    return ProjectRepository(session)


async def get_project_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProjectService:
    """동일 session으로 ProjectRepository + WorkspaceRepository 조립.

    backend.md §3 크로스 레포지토리 트랜잭션 패턴 — commit은 service에서 1회만.
    """
    return ProjectService(
        repo=ProjectRepository(session),
        ws_repo=WorkspaceRepository(session),
    )
