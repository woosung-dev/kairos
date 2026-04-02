# backend/src/actions/dependencies.py
"""ActionItem 의존성 — Depends() 조립의 유일한 위치."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.actions.repository import ActionItemRepository
from src.actions.service import ActionItemService


async def get_action_repository(
    session: AsyncSession = Depends(get_async_session),
) -> ActionItemRepository:
    return ActionItemRepository(session)


async def get_action_service(
    repo: ActionItemRepository = Depends(get_action_repository),
) -> ActionItemService:
    return ActionItemService(repo)
