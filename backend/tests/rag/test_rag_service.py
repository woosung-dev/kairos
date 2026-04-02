# backend/tests/rag/test_rag_service.py
"""RagService 단위 테스트 — RRF + 캐시 HIT/MISS."""
import json
import uuid

import pytest
from unittest.mock import AsyncMock

from src.rag.service import RagService


class TestReciprocalRankFusion:
    """RRF 융합 로직 테스트."""

    def test_rrf_merges_two_lists(self):
        """텍스트 + 벡터 결과를 RRF로 병합."""
        text_results = [
            {"id": "a", "chunk_text": "t1"},
            {"id": "b", "chunk_text": "t2"},
        ]
        vector_results = [
            {"id": "b", "chunk_text": "t2"},
            {"id": "c", "chunk_text": "t3"},
        ]
        fused = RagService._reciprocal_rank_fusion(
            text_results, vector_results, k=60, top_n=10
        )
        ids = [r["id"] for r in fused]
        # b가 양쪽 모두 있으므로 최상위
        assert ids[0] == "b"
        assert len(fused) == 3

    def test_rrf_respects_top_n(self):
        """top_n 제한 동작."""
        text_results = [{"id": str(i), "chunk_text": f"t{i}"} for i in range(20)]
        vector_results = [{"id": str(i + 10), "chunk_text": f"v{i}"} for i in range(20)]
        fused = RagService._reciprocal_rank_fusion(
            text_results, vector_results, k=60, top_n=5
        )
        assert len(fused) == 5

    def test_rrf_empty_results(self):
        """양쪽 모두 빈 결과 → 빈 리스트."""
        fused = RagService._reciprocal_rank_fusion([], [], top_n=10)
        assert fused == []


@pytest.mark.asyncio
async def test_cache_hit_returns_cached_answer():
    """similarity >= 0.93 → 캐시 답변 반환, Gemini 호출 없음."""
    mock_repo = AsyncMock()
    mock_repo.find_similar_cache.return_value = {
        "id": "cache-1",
        "answer": "캐시된 답변입니다.",
        "sources": [{"id": "s1", "text": "소스", "source": "회의"}],
        "hit_count": 1,
    }

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]

    mock_ai = AsyncMock()

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    events = []
    async for event in service.ask("테스트 질문", uuid.uuid4()):
        events.append(event)

    # Gemini 호출 없어야 함
    mock_ai.stream_rag_answer.assert_not_called()

    # done 이벤트에 cached=True
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) == 1
    done_data = json.loads(done_events[0]["data"])
    assert done_data["cached"] is True


@pytest.mark.asyncio
async def test_cache_miss_no_results():
    """캐시 미스 + 검색 결과 없음 → '정보 없음' 답변."""
    mock_repo = AsyncMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = []
    mock_repo.text_search.return_value = []

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]

    mock_ai = AsyncMock()

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    events = []
    async for event in service.ask("테스트 질문", uuid.uuid4()):
        events.append(event)

    # 검색 결과 없으면 "정보 없음" 답변
    answer_events = [e for e in events if e["event"] == "answer"]
    assert len(answer_events) == 1
    answer_data = json.loads(answer_events[0]["data"])
    assert "찾지 못했습니다" in answer_data["token"]

    # Gemini 호출 안 됨
    mock_ai.stream_rag_answer.assert_not_called()
