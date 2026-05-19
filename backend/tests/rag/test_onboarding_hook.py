# RAG ask 첫 성공 시 onboarding step=4 hook 검증 (Sprint 22 OBN-02)
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.rag.service import RagService


@pytest.mark.asyncio
async def test_rag_cache_hit_advances_onboarding_step_4():
    """cache hit 도 첫 성공 응답 → step=4 advance."""
    mock_repo = AsyncMock()
    mock_repo.session = MagicMock()
    mock_repo.find_similar_cache.return_value = {
        "id": "cache-1",
        "answer": "캐시된 답변",
        "sources": [{"id": "s1", "text": "소스", "source": "회의"}],
        "hit_count": 1,
    }

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]
    mock_ai = AsyncMock()

    user_id = uuid.uuid4()
    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    with patch(
        "src.onboarding.service.OnboardingService.increment_step"
    ) as mock_increment:
        mock_increment.return_value = None
        events = []
        async for event in service.ask(
            "질문",
            uuid.uuid4(),
            requester_user_id=user_id,
            requester_role="owner",
        ):
            events.append(event)

        mock_increment.assert_any_call(user_id, 4)


@pytest.mark.asyncio
async def test_rag_generation_success_advances_onboarding_step_4():
    """RAG 정상 generation (full answer) → step=4 advance."""

    async def fake_stream(q, src):
        yield "답변 토큰 1"
        yield " 토큰 2"

    mock_repo = AsyncMock()
    mock_repo.session = MagicMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = [
        {"id": uuid.uuid4(), "chunk_text": "소스", "score": 0.8}
    ]
    mock_repo.text_search.return_value = []
    mock_repo.find_chunks_by_ids.return_value = {}
    mock_repo.compute_max_visibility.return_value = "public"
    mock_repo.save_cache.return_value = None
    mock_repo.commit.return_value = None

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]
    mock_ai = AsyncMock()
    mock_ai.stream_rag_answer = fake_stream

    user_id = uuid.uuid4()
    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    with patch(
        "src.onboarding.service.OnboardingService.increment_step"
    ) as mock_increment:
        mock_increment.return_value = None
        events = []
        async for event in service.ask(
            "질문",
            uuid.uuid4(),
            requester_user_id=user_id,
            requester_role="owner",
        ):
            events.append(event)

        mock_increment.assert_any_call(user_id, 4)


@pytest.mark.asyncio
async def test_rag_no_sources_skips_onboarding_advance():
    """빈 결과 → step=4 advance 안 함 (실 RAG 성공 아님)."""
    mock_repo = AsyncMock()
    mock_repo.session = MagicMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = []
    mock_repo.text_search.return_value = []

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]
    mock_ai = AsyncMock()

    user_id = uuid.uuid4()
    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    with patch(
        "src.onboarding.service.OnboardingService.increment_step"
    ) as mock_increment:
        mock_increment.return_value = None
        events = []
        async for event in service.ask(
            "질문",
            uuid.uuid4(),
            requester_user_id=user_id,
            requester_role="owner",
        ):
            events.append(event)

        # 빈 결과 path 에서는 step=4 advance 호출 없음
        for call in mock_increment.call_args_list:
            assert call.args[1] != 4, (
                f"step=4 should not be called when no sources, got {call.args}"
            )


@pytest.mark.asyncio
async def test_rag_generation_failure_skips_onboarding_advance():
    """Generation 중 예외 → step=4 advance 안 함."""

    async def failing_stream(q, src):
        raise RuntimeError("Gemini API error")
        yield  # unreachable

    mock_repo = AsyncMock()
    mock_repo.session = MagicMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = [
        {"id": uuid.uuid4(), "chunk_text": "소스"}
    ]
    mock_repo.text_search.return_value = []
    mock_repo.find_chunks_by_ids.return_value = {}

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]
    mock_ai = AsyncMock()
    mock_ai.stream_rag_answer = failing_stream

    user_id = uuid.uuid4()
    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    with patch(
        "src.onboarding.service.OnboardingService.increment_step"
    ) as mock_increment:
        mock_increment.return_value = None
        events = []
        async for event in service.ask(
            "질문",
            uuid.uuid4(),
            requester_user_id=user_id,
            requester_role="owner",
        ):
            events.append(event)

        for call in mock_increment.call_args_list:
            assert call.args[1] != 4, (
                f"step=4 should not be called on generation failure, got {call.args}"
            )
