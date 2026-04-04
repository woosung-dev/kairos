# backend/src/meetings/dependencies.py
"""Meeting 의존성 — Depends() 조립의 유일한 위치."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.actions.repository import ActionItemRepository
from src.common.database import get_async_session
from src.common.r2 import R2Service
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.inbox.repository import InboxRepository
from src.meetings.pipeline_service import MeetingPipelineService
from src.meetings.repository import MeetingRepository
from src.meetings.service import MeetingService
from src.projects.repository import ProjectRepository
from src.services.ai_processing import AIProcessingService
from src.services.transcription import TranscriptionService
from src.workspaces.repository import WorkspaceRepository


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
    )


async def get_pipeline_service(
    session: AsyncSession = Depends(get_async_session),
) -> MeetingPipelineService:
    """파이프라인 의존성. BackgroundTasks용. 동일 session을 모든 repo에 공유."""
    return MeetingPipelineService(
        meeting_repo=MeetingRepository(session),
        project_repo=ProjectRepository(session),
        action_repo=ActionItemRepository(session),
        inbox_repo=InboxRepository(session),
        workspace_repo=WorkspaceRepository(session),
        r2_service=R2Service(),
        transcription_service=TranscriptionService(),
        ai_service=AIProcessingService(),
        embedding_service=EmbeddingService(EmbeddingRepository(session)),
    )
