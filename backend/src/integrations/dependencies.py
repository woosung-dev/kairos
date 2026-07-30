"""Integrations 의존성 주입 — request-scoped repository와 service 조립."""
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session
from src.integrations.repository import IntegrationRepository
from src.integrations.service import IntegrationService


async def get_integration_repository(
    session: AsyncSession = Depends(get_async_session),
) -> IntegrationRepository:
    return IntegrationRepository(session)


async def get_integration_service(
    repo: IntegrationRepository = Depends(get_integration_repository),
) -> IntegrationService:
    return IntegrationService(repo)
