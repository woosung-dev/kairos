# backend/src/meetings/dependencies.py
"""Meeting 의존성 — Depends() 조립의 유일한 위치."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.common.r2 import R2Service
from src.meetings.pipeline_service import MeetingPipelineService
from src.meetings.repository import MeetingRepository
from src.meetings.service import MeetingService
from src.services.ai_processing import AIProcessingService
from src.services.transcription import TranscriptionService


async def get_meeting_repository(
    session: AsyncSession = Depends(get_async_session),
) -> MeetingRepository:
    return MeetingRepository(session)


async def get_meeting_service(
    repo: MeetingRepository = Depends(get_meeting_repository),
) -> MeetingService:
    return MeetingService(repo)


async def get_pipeline_service(
    session: AsyncSession = Depends(get_async_session),
) -> MeetingPipelineService:
    """파이프라인 의존성. BackgroundTasks용."""
    return MeetingPipelineService(
        meeting_repo=MeetingRepository(session),
        r2_service=R2Service(),
        transcription_service=TranscriptionService(),
        ai_service=AIProcessingService(),
    )
