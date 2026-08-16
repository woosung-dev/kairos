# Sprint 29 R1 (svc-breaker) 회귀 가드 — RAG 스트리밍 mid-stream 실패 집계.
"""stream init 성공 후 async for 중 vendor 실패가 circuit breaker 에 집계되는지 검증.

이전엔 init 만 with_gemini_timeout 으로 감싸 mid-stream 실패가 breaker 밖 →
vendor 가 매번 init 후 mid-stream 실패해도 circuit 이 열리지 않는 구멍이 있었다.
"""
from unittest.mock import MagicMock, patch

import pytest

from src.services.ai_resilience import gemini_breaker, reset_breakers_for_test


def _mock_settings():
    settings = MagicMock()
    settings.gemini_api_key.get_secret_value.return_value = "test-gemini-key"
    return settings


class _Chunk:
    def __init__(self, text: str) -> None:
        self.text = text


@pytest.fixture(autouse=True)
def _reset():
    reset_breakers_for_test()
    yield
    reset_breakers_for_test()


@pytest.mark.asyncio
async def test_stream_rag_answer_counts_midstream_failure():
    """init 성공(breaker reset) 후 mid-stream 실패 → on_failure 집계(연속 실패 1)."""
    async def _init_stream(*a, **kw):
        async def _agen():
            yield _Chunk("부분 ")
            raise RuntimeError("mid-stream vendor drop")
        return _agen()

    with patch("src.services.ai_processing.get_settings", return_value=_mock_settings()):
        with patch("src.services.ai_processing.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.aio.models.generate_content_stream = _init_stream
            mock_genai.Client.return_value = mock_client

            from src.services.ai_processing import AIProcessingService
            service = AIProcessingService()

            collected: list[str] = []
            with pytest.raises(RuntimeError):
                async for tok in service.stream_rag_answer("질문", "출처들"):
                    collected.append(tok)

    assert collected == ["부분 "]  # 실패 전 토큰은 정상 전달
    assert gemini_breaker._consecutive_failures == 1  # mid-stream 실패 집계됨


@pytest.mark.asyncio
async def test_stream_rag_answer_clean_stream_no_failure():
    """정상 완료 스트림 → breaker 실패 카운터 증가 없음(회귀 안전)."""
    async def _init_stream(*a, **kw):
        async def _agen():
            yield _Chunk("완전 ")
            yield _Chunk("답변")
        return _agen()

    with patch("src.services.ai_processing.get_settings", return_value=_mock_settings()):
        with patch("src.services.ai_processing.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.aio.models.generate_content_stream = _init_stream
            mock_genai.Client.return_value = mock_client

            from src.services.ai_processing import AIProcessingService
            service = AIProcessingService()

            tokens = [tok async for tok in service.stream_rag_answer("질문", "출처들")]

    assert tokens == ["완전 ", "답변"]
    assert gemini_breaker._consecutive_failures == 0
