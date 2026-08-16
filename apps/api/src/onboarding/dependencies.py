# Onboarding 도메인 — FastAPI DI provider
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session
from src.onboarding.service import OnboardingService


async def get_onboarding_service(
    session: AsyncSession = Depends(get_async_session),
) -> OnboardingService:
    return OnboardingService(session)
