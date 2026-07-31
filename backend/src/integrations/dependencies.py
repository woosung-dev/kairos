"""Integrations 의존성 주입 — request-scoped repository와 service 조립."""
from collections.abc import AsyncIterator

import httpx

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session, get_session_factory
from src.core.config import get_settings
from src.integrations.drive_client import GoogleDriveClient
from src.integrations.pipeline_service import GoogleDriveSyncPipelineService
from src.integrations.repository import IntegrationRepository
from src.integrations.service import IntegrationService
from src.projects.repository import ProjectRepository


async def get_integration_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IntegrationRepository:
    return IntegrationRepository(session)


async def get_integration_service(
    repo: IntegrationRepository = Depends(get_integration_repository),
) -> IntegrationService:
    return IntegrationService(repo)


async def get_integration_project_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ProjectRepository:
    return ProjectRepository(session)


async def get_google_drive_client() -> AsyncIterator[GoogleDriveClient]:
    """요청 경계의 OAuth code 교환용 HTTP 클라이언트."""
    async with httpx.AsyncClient() as client:
        yield GoogleDriveClient(client)


def _create_google_drive_client() -> GoogleDriveClient:
    """BackgroundTasks 진입 시 사용할 주입 가능한 Drive REST 클라이언트 factory."""
    return GoogleDriveClient(httpx.AsyncClient())


def get_google_drive_sync_pipeline_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> GoogleDriveSyncPipelineService:
    """Drive pipeline provider. DB 세션은 pipeline 진입점에서 fresh 생성한다."""
    settings = get_settings()
    client_id = settings.google_oauth_client_id
    client_secret = settings.google_oauth_client_secret
    if client_id is None or client_secret is None:
        raise HTTPException(status_code=503, detail="Google OAuth 설정이 필요합니다")
    return GoogleDriveSyncPipelineService(
        session_factory=session_factory,
        drive_client_factory=_create_google_drive_client,
        google_oauth_client_id=client_id,
        google_oauth_client_secret=client_secret.get_secret_value(),
    )
