# backend/src/rag/dependencies.py
"""RAG 서비스 의존성 — ADR-014 옵션 A 정합 (D-3 부채 해소 1차).

RagService = 6-Layer 비즈니스 로직. RagPipelineService = visibility 검증 + 위임.
"""
from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from src.common.database import get_async_session
from src.embeddings.repository import EmbeddingRepository
from src.embeddings.service import EmbeddingService
from src.projects.repository import ProjectRepository
from src.rag.pipeline_service import RagPipelineService
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


async def get_rag_pipeline_service(
    rag_service: RagService = Depends(get_rag_service),
    session: AsyncSession = Depends(get_async_session),
) -> RagPipelineService:
    return RagPipelineService(
        rag_service=rag_service,
        project_repo=ProjectRepository(session),
    )
