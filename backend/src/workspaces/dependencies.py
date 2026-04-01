# backend/src/workspaces/dependencies.py
"""Workspace 의존성 — Depends() 조립의 유일한 위치."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.repository import UserRepository
from src.common.database import get_async_session
from src.workspaces.repository import WorkspaceRepository
from src.workspaces.service import WorkspaceService


async def get_workspace_service(
    session: AsyncSession = Depends(get_async_session),
) -> WorkspaceService:
    """동일 session을 workspace_repo + user_repo에 주입 (크로스 레포 트랜잭션)."""
    return WorkspaceService(
        repo=WorkspaceRepository(session),
        user_repo=UserRepository(session),
    )
