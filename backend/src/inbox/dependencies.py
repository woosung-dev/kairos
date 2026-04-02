# backend/src/inbox/dependencies.py
"""Inbox 의존성 — 크로스 레포지토리 패턴 (동일 session 공유)."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.inbox.repository import InboxRepository
from src.inbox.service import InboxService
from src.projects.repository import ProjectRepository


async def get_inbox_service(
    session: AsyncSession = Depends(get_async_session),
) -> InboxService:
    """동일 session으로 InboxRepo + ProjectRepo 주입."""
    return InboxService(
        inbox_repo=InboxRepository(session),
        project_repo=ProjectRepository(session),
    )
