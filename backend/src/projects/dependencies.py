# backend/src/projects/dependencies.py
"""Project 의존성 — Depends() 조립의 유일한 위치."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService


async def get_project_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ProjectRepository:
    return ProjectRepository(session)


async def get_project_service(
    repo: ProjectRepository = Depends(get_project_repository),
) -> ProjectService:
    return ProjectService(repo)
