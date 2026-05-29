# feedback 서비스 DI — AsyncSession → repository → service
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session
from src.feedback.repository import FeedbackRepository
from src.feedback.service import FeedbackService


async def get_feedback_service(
    session: AsyncSession = Depends(get_async_session),
) -> FeedbackService:
    return FeedbackService(feedback_repo=FeedbackRepository(session))
