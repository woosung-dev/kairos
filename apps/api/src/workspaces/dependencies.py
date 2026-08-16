# apps/backend/src/workspaces/dependencies.py
"""Workspace 의존성 — Depends() 조립의 유일한 위치."""
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.repository import UserRepository
from src.common.database import get_async_session
from src.projects.repository import ProjectRepository
from src.workspaces.invite_service import InviteService
from src.workspaces.repository import WorkspaceRepository
from src.workspaces.service import WorkspaceService


async def get_workspace_service(
    session: AsyncSession = Depends(get_async_session),
) -> WorkspaceService:
    """동일 session을 workspace + project repo에 주입 (크로스 레포 트랜잭션)."""
    return WorkspaceService(
        repo=WorkspaceRepository(session),
        project_repo=ProjectRepository(session),
    )


async def get_invite_service(
    session: AsyncSession = Depends(get_async_session),
) -> InviteService:
    """초대/멤버 관리 서비스. 동일 session으로 workspace + user repo 조립."""
    return InviteService(
        repo=WorkspaceRepository(session),
        user_repo=UserRepository(session),
    )
