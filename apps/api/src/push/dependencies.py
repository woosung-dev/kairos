# push 서비스 DI — AsyncSession → repository → service
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session
from src.push.repository import PushRepository
from src.push.service import PushService


async def get_push_service(
    session: AsyncSession = Depends(get_async_session),
) -> PushService:
    return PushService(PushRepository(session))
