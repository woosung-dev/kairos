# Memory DI 조립 — Depends() 유일 위치
"""Memory dependencies.

backend rules §3 — Depends 조립은 dependencies.py에서만.
session_factory 주입으로 BackgroundTask 내부에서 별도 session 생성 가능.
"""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.common.database import get_async_session, get_session_factory
from src.common.r2 import R2Service
from src.memory.repository import MemoryRepository
from src.memory.service import MemoryService


async def get_memory_repository(
    session: AsyncSession = Depends(get_async_session),
) -> MemoryRepository:
    return MemoryRepository(session)


def get_memory_service(
    repo: MemoryRepository = Depends(get_memory_repository),
    session_factory: async_sessionmaker[AsyncSession] = Depends(
        get_session_factory
    ),
) -> MemoryService:
    return MemoryService(
        repo=repo,
        session_factory=session_factory,
        r2_service=R2Service(),
    )
