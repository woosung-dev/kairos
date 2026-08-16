# apps/api/src/embeddings/dependencies.py
"""임베딩 서비스 의존성 주입."""
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService


async def get_embedding_repository(
    session: AsyncSession = Depends(get_async_session),
) -> EmbeddingRepository:
    return EmbeddingRepository(session)


async def get_embedding_service(
    repo: EmbeddingRepository = Depends(get_embedding_repository),
) -> EmbeddingService:
    return EmbeddingService(repo)
