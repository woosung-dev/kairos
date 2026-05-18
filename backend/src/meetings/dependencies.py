# backend/src/meetings/dependencies.py
"""Meeting 의존성 — Depends() 조립의 유일한 위치."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.actions.repository import ActionItemRepository
from src.common.database import get_async_session, get_session_factory
from src.common.r2 import R2Service
from src.meetings.pipeline_service import MeetingPipelineService
from src.meetings.repository import MeetingRepository
from src.meetings.service import MeetingService
from src.projects.repository import ProjectRepository
from src.services.ai_processing import AIProcessingService
from src.services.transcription import TranscriptionService


async def get_meeting_repository(
    session: AsyncSession = Depends(get_async_session),
) -> MeetingRepository:
    return MeetingRepository(session)


async def get_meeting_service(
    session: AsyncSession = Depends(get_async_session),
) -> MeetingService:
    return MeetingService(
        repo=MeetingRepository(session),
        action_repo=ActionItemRepository(session),
        project_repo=ProjectRepository(session),
    )


def get_pipeline_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> MeetingPipelineService:
    """파이프라인 의존성. 세션 팩토리만 주입 — 실제 세션은 백그라운드 태스크 내부에서 생성."""
    return MeetingPipelineService(
        session_factory=session_factory,
        r2_service=R2Service(),
        transcription_service=TranscriptionService(),
        ai_service=AIProcessingService(),
    )
