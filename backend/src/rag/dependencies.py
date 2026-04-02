# backend/src/rag/dependencies.py
"""RAG 서비스 의존성."""
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import get_async_session
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.rag.service import RagService
from src.services.ai_processing import AIProcessingService


async def get_rag_service(
    session: AsyncSession = Depends(get_async_session),
) -> RagService:
    repo = EmbeddingRepository(session)
    return RagService(
        embedding_repo=repo,
        embedding_service=EmbeddingService(repo),
        ai_service=AIProcessingService(),
    )
