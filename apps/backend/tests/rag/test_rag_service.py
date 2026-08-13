# apps/backend/tests/rag/test_rag_service.py
"""RagService 단위 테스트 — RRF + 캐시 HIT/MISS."""
import json
import logging
import uuid

import pytest
from unittest.mock import AsyncMock

from src.embeddings.repository import EmbeddingRepository
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
        # CAND-E completeness: fresh 검색이 부여한 sourceId 를 포함해야 cache HIT 으로
        # serve 된다 (sourceId-less 캐시는 bypass → fresh path). 실 저장 캐시는 항상 sourceId 보유.
        "sources": [{"id": "s1", "sourceId": "m1", "text": "소스", "source": "회의"}],
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
    async for event in service.ask("테스트 질문", uuid.uuid4(), requester_user_id=uuid.uuid4(), requester_role="owner"):
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
    async for event in service.ask("테스트 질문", uuid.uuid4(), requester_user_id=uuid.uuid4(), requester_role="owner"):
        events.append(event)

    # 검색 결과 없으면 "정보 없음" 답변
    answer_events = [e for e in events if e["event"] == "answer"]
    assert len(answer_events) == 1
    answer_data = json.loads(answer_events[0]["data"])
    assert "찾지 못했습니다" in answer_data["token"]

    # Gemini 호출 안 됨
    mock_ai.stream_rag_answer.assert_not_called()


# ── BL-003: _enrich_context 배치 쿼리 테스트 ──
import uuid as _uuid
from unittest.mock import MagicMock


@pytest.mark.asyncio
async def test_enrich_context_uses_batch_query():
    """parent_chunk_id가 있는 결과 → find_chunks_by_ids 1회 호출."""
    parent_id = _uuid.uuid4()
    mock_chunk = MagicMock()
    mock_chunk.chunk_text = "부모 청크 텍스트"

    mock_repo = AsyncMock()
    mock_repo.find_chunks_by_ids.return_value = {parent_id: mock_chunk}

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=AsyncMock(),
        ai_service=AsyncMock(),
    )

    results = [
        {"id": str(_uuid.uuid4()), "chunk_text": "자식1", "parent_chunk_id": str(parent_id)},
        {"id": str(_uuid.uuid4()), "chunk_text": "자식2", "parent_chunk_id": str(parent_id)},
    ]
    enriched = await service._enrich_context(results)

    mock_repo.find_chunks_by_ids.assert_called_once()
    mock_repo.find_chunk_by_id.assert_not_called()
    assert enriched[0]["parent_text"] == "부모 청크 텍스트"
    assert enriched[1]["parent_text"] == "부모 청크 텍스트"


@pytest.mark.asyncio
async def test_enrich_context_no_parent_ids():
    """parent_chunk_id 없는 결과 → DB 호출 없음, parent_text 빈 문자열."""
    mock_repo = AsyncMock()

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=AsyncMock(),
        ai_service=AsyncMock(),
    )

    results = [
        {"id": str(_uuid.uuid4()), "chunk_text": "부모 없는 청크"},
    ]
    enriched = await service._enrich_context(results)

    mock_repo.find_chunks_by_ids.assert_not_called()
    assert enriched[0]["parent_text"] == ""


@pytest.mark.asyncio
async def test_enrich_context_empty_results():
    """빈 결과 → DB 미호출."""
    mock_repo = AsyncMock()

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=AsyncMock(),
        ai_service=AsyncMock(),
    )

    enriched = await service._enrich_context([])

    mock_repo.find_chunks_by_ids.assert_not_called()
    assert enriched == []


# ── T-1 BUG-C01: Gemini 예외 graceful degrade ──


def _make_async_iter(*items):
    """AsyncIterable 헬퍼 — items를 차례로 yield. mock 인자 *_args 무시."""
    async def _gen(*_args, **_kwargs):
        for item in items:
            yield item
    return _gen


def _make_raising_async_iter(exc: Exception):
    """AsyncIterable 헬퍼 — 첫 iter 에서 예외 raise. mock 인자 *_args 무시."""
    async def _gen(*_args, **_kwargs):
        if False:  # type: ignore[unreachable] — async generator 표식 유지용
            yield
        raise exc
    return _gen


@pytest.mark.asyncio
async def test_gemini_safety_filter_raises_graceful_error_event():
    """Gemini SafetyFilter / API 오류 → 5xx 대신 SSE error + done. 캐시 미저장."""
    mock_repo = AsyncMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = [
        {"id": _uuid.uuid4(), "chunk_text": "콘텐츠", "score": 0.9, "source_type": "meeting"}
    ]
    mock_repo.text_search.return_value = []
    mock_repo.find_chunks_by_ids.return_value = {}

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]

    # Gemini 호출 시 예외 — SafetyFilter 류 시뮬레이션
    mock_ai = AsyncMock()
    mock_ai.stream_rag_answer = _make_raising_async_iter(
        RuntimeError("BlockedPromptError: safety filter")
    )

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    events = []
    async for event in service.ask("악의적 입력?", _uuid.uuid4(), requester_user_id=_uuid.uuid4(), requester_role="owner"):
        events.append(event)

    # error 이벤트 + done 이벤트 (순서 보장)
    error_events = [e for e in events if e["event"] == "error"]
    done_events = [e for e in events if e["event"] == "done"]
    assert len(error_events) == 1
    assert len(done_events) == 1

    error_data = json.loads(error_events[0]["data"])
    assert "질문을 처리할 수 없습니다" in error_data["message"]
    assert error_data["retryAfter"] == 3

    done_data = json.loads(done_events[0]["data"])
    assert done_data["cached"] is False
    assert done_data["sourceCount"] == 0

    # 캐시 오염 방지 — save_cache 호출되지 않아야 함
    mock_repo.save_cache.assert_not_called()


@pytest.mark.asyncio
async def test_gemini_empty_answer_skips_cache_store():
    """Gemini 가 빈 답변 토큰만 돌려주면 캐시 저장 skip (오염 방지)."""
    mock_repo = AsyncMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = [
        {"id": _uuid.uuid4(), "chunk_text": "콘텐츠", "score": 0.9, "source_type": "meeting"}
    ]
    mock_repo.text_search.return_value = []
    mock_repo.find_chunks_by_ids.return_value = {}

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]

    # 빈 토큰만 yield (whitespace) — full_answer.strip() == ""
    mock_ai = AsyncMock()
    mock_ai.stream_rag_answer = _make_async_iter("  ", "\n", "")

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    events = []
    async for event in service.ask("정상 질문입니다?", _uuid.uuid4(), requester_user_id=_uuid.uuid4(), requester_role="owner"):
        events.append(event)

    # 정상 흐름은 진행됐지만 캐시 저장 안 됨
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) == 1
    mock_repo.save_cache.assert_not_called()


@pytest.mark.asyncio
async def test_gemini_successful_answer_saves_cache():
    """정상 답변 → 캐시 저장 시도 (기존 동작 회귀 확인)."""
    mock_repo = AsyncMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = [
        {"id": _uuid.uuid4(), "chunk_text": "콘텐츠", "score": 0.9, "source_type": "meeting"}
    ]
    mock_repo.text_search.return_value = []
    mock_repo.find_chunks_by_ids.return_value = {}
    mock_repo.all_chunks_exist.return_value = True

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]

    mock_ai = AsyncMock()
    mock_ai.stream_rag_answer = _make_async_iter("정상 답변 ", "토큰 스트림")

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    async for _event in service.ask("정상 질문?", _uuid.uuid4(), requester_user_id=_uuid.uuid4(), requester_role="owner"):
        pass

    mock_repo.save_cache.assert_called_once()
    # PERF-SSE-COMMIT: 스트리밍 진입 전 커넥션 반납 commit + 캐시 저장 commit = 2회
    assert mock_repo.commit.call_count == 2


@pytest.mark.asyncio
async def test_gemini_successful_answer_skips_cache_when_source_chunks_disappear():
    """F1: 존재 fence 가 실패하면 정상 done 뒤 캐시 저장을 건너뛴다."""
    mock_repo = AsyncMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = [
        {"id": _uuid.uuid4(), "chunk_text": "콘텐츠", "score": 0.9, "source_type": "meeting"}
    ]
    mock_repo.text_search.return_value = []
    mock_repo.find_chunks_by_ids.return_value = {}
    mock_repo.compute_max_visibility.return_value = "public"
    mock_repo.count_existing_chunks.return_value = 0

    existence_session = AsyncMock()
    existence_result = MagicMock()
    existence_result.first.return_value = object()
    existence_session.execute.return_value = existence_result
    existence_repo = EmbeddingRepository(existence_session)
    mock_repo.all_chunks_exist.side_effect = existence_repo.all_chunks_exist

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]

    mock_ai = AsyncMock()
    mock_ai.stream_rag_answer = _make_async_iter("정상 답변")

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    events = []
    async for event in service.ask(
        "정상 질문?", _uuid.uuid4(), requester_user_id=_uuid.uuid4(), requester_role="owner"
    ):
        events.append(event)

    mock_repo.save_cache.assert_not_called()
    done_events = [event for event in events if event["event"] == "done"]
    assert len(done_events) == 1
    assert json.loads(done_events[0]["data"])["cached"] is False


@pytest.mark.asyncio
async def test_gemini_successful_answer_saves_cache_when_source_chunks_exist():
    """F2: 존재 fence 가 통과하면 기존 캐시 저장 경로를 유지한다."""
    mock_repo = AsyncMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = [
        {"id": _uuid.uuid4(), "chunk_text": "콘텐츠", "score": 0.9, "source_type": "meeting"}
    ]
    mock_repo.text_search.return_value = []
    mock_repo.find_chunks_by_ids.return_value = {}
    mock_repo.all_chunks_exist.return_value = True

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]

    mock_ai = AsyncMock()
    mock_ai.stream_rag_answer = _make_async_iter("정상 답변")

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    async for _event in service.ask(
        "정상 질문?", _uuid.uuid4(), requester_user_id=_uuid.uuid4(), requester_role="owner"
    ):
        pass

    mock_repo.save_cache.assert_awaited_once()


class _TimingLogCollector(logging.Handler):
    """caplog 는 suite 전역 로깅 상태에 따라 유실될 수 있어 module logger 에 직접 부착."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@pytest.mark.asyncio
async def test_rag_timing_log_includes_vector_text_fields():
    """rag.timing 로그에 vector=/text= 개별 계측 필드 존재 (PERF-r2-3 판정 근거 가드)."""
    mock_repo = AsyncMock()
    mock_repo.find_similar_cache.return_value = None
    mock_repo.vector_search.return_value = [
        {"id": _uuid.uuid4(), "chunk_text": "콘텐츠", "score": 0.9, "source_type": "meeting"}
    ]
    mock_repo.text_search.return_value = []
    mock_repo.find_chunks_by_ids.return_value = {}

    mock_embedding_service = AsyncMock()
    mock_embedding_service.generate_embeddings.return_value = [[0.1] * 1536]

    mock_ai = AsyncMock()
    mock_ai.stream_rag_answer = _make_async_iter("답변")

    service = RagService(
        embedding_repo=mock_repo,
        embedding_service=mock_embedding_service,
        ai_service=mock_ai,
    )

    collector = _TimingLogCollector()
    rag_logger = logging.getLogger("src.rag.service")
    old_level = rag_logger.level
    old_disabled = rag_logger.disabled
    rag_logger.addHandler(collector)
    rag_logger.setLevel(logging.INFO)
    # alembic env.py 의 fileConfig(disable_existing_loggers) 가 suite 내 기존 로거를
    # disabled 로 만듦 (test_alembic_upgrade.py 선행 시) — 명시 복구.
    rag_logger.disabled = False
    try:
        async for _event in service.ask(
            "타이밍 질문?",
            _uuid.uuid4(),
            requester_user_id=_uuid.uuid4(),
            requester_role="owner",
        ):
            pass
    finally:
        rag_logger.removeHandler(collector)
        rag_logger.setLevel(old_level)
        rag_logger.disabled = old_disabled

    timing_lines = [m for m in collector.messages if "rag.timing" in m]
    assert len(timing_lines) == 1
    for field in ("embed=", "search=", "vector=", "text=", "llm=", "total="):
        assert field in timing_lines[0]
