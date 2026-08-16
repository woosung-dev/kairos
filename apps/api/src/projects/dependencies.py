# apps/backend/src/projects/dependencies.py
"""Project 의존성 — Depends() 조립의 유일한 위치.

Sprint 19 PR #1 C9 (Codex F-2): MeetingRepository 동반 주입 (동일 session).
apps/backend/AGENTS.md §3 크로스 레포지토리 트랜잭션 패턴.
"""
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session
from src.meetings.repository import MeetingRepository
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.repository import WorkspaceRepository


async def get_project_service(
    session: AsyncSession = Depends(get_async_session),
) -> ProjectService:
    """동일 session으로 ProjectRepository + WorkspaceRepository + MeetingRepository 조립.

    apps/backend/AGENTS.md §3 크로스 레포지토리 트랜잭션 패턴 — commit은 service에서 1회만.
    Sprint 19 PR #1 C9: MeetingRepository 추가 주입 (secondary FK fail-closed).
    """
    return ProjectService(
        repo=ProjectRepository(session),
        ws_repo=WorkspaceRepository(session),
        meeting_repo=MeetingRepository(session),
    )
