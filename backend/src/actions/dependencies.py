# backend/src/actions/dependencies.py
"""ActionItem 의존성 — Depends() 조립의 유일한 위치.

Codex F-2 Critical: secondary FK (project / meeting / assignee) cross-tenant 검증을 위해
ProjectRepository / MeetingRepository / WorkspaceRepository 동반 주입.
"""
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session
from src.actions.repository import ActionItemRepository
from src.actions.service import ActionItemService
from src.meetings.repository import MeetingRepository
from src.projects.repository import ProjectRepository
from src.workspaces.repository import WorkspaceRepository


async def get_action_service(
    session: AsyncSession = Depends(get_async_session),
) -> ActionItemService:
    # Codex F-2: 3 secondary FK 검증용 repo 의존성 함께 주입 (동일 session 공유)
    return ActionItemService(
        repo=ActionItemRepository(session),
        project_repo=ProjectRepository(session),
        meeting_repo=MeetingRepository(session),
        workspace_repo=WorkspaceRepository(session),
    )
