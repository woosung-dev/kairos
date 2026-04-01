# backend/src/meetings/dependencies.py
"""Meeting 의존성 — Depends() 조립의 유일한 위치."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.meetings.repository import MeetingRepository
from src.meetings.service import MeetingService


async def get_meeting_repository(
    session: AsyncSession = Depends(get_async_session),
) -> MeetingRepository:
    return MeetingRepository(session)


async def get_meeting_service(
    repo: MeetingRepository = Depends(get_meeting_repository),
) -> MeetingService:
    return MeetingService(repo)
