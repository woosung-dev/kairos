# backend/tests/services/test_ai_processing.py
"""Gemini AI 요약 서비스 테스트."""
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

MOCK_SUMMARY_RESPONSE = json.dumps({
    "summary": "CMS 고도화 프로젝트 킥오프 회의. 3월 내 완료 목표 확정.",
    "key_decisions": ["CMS 3월 내 완료", "React 마이그레이션 진행"],
    "risks_and_issues": ["인력 부족"],
    "participants": ["김철수", "이영희"],
    "topics": ["CMS", "프론트엔드"],
    "next_meeting_agenda": ["진행 상황 공유"],
})


def _mock_settings():
    settings = MagicMock()
    settings.gemini_api_key.get_secret_value.return_value = "test-gemini-key"
    return settings


@pytest.mark.asyncio
async def test_summarize_returns_structured_dict():
    """Gemini 응답을 구조화된 dict로 반환."""
    mock_response = MagicMock()
    mock_response.text = MOCK_SUMMARY_RESPONSE

    with patch("src.services.ai_processing.get_settings", return_value=_mock_settings()):
        with patch("src.services.ai_processing.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
            mock_genai.Client.return_value = mock_client

            from src.services.ai_processing import AIProcessingService
            service = AIProcessingService()
            result = await service.summarize("안녕하세요. 오늘 회의를 시작하겠습니다.")

    assert "summary" in result
    assert "key_decisions" in result
    assert isinstance(result["key_decisions"], list)


@pytest.mark.asyncio
async def test_summarize_with_code_fence():
    """코드펜스 포함된 Gemini 응답도 파싱."""
    fenced = f"```json\n{MOCK_SUMMARY_RESPONSE}\n```"
    mock_response = MagicMock()
    mock_response.text = fenced

    with patch("src.services.ai_processing.get_settings", return_value=_mock_settings()):
        with patch("src.services.ai_processing.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
            mock_genai.Client.return_value = mock_client

            from src.services.ai_processing import AIProcessingService
            service = AIProcessingService()
            result = await service.summarize("테스트 트랜스크립트")

    assert result["summary"] is not None


@pytest.mark.asyncio
async def test_summarize_uses_correct_model():
    """gemini-2.5-flash 모델 고정 확인."""
    mock_response = MagicMock()
    mock_response.text = MOCK_SUMMARY_RESPONSE

    with patch("src.services.ai_processing.get_settings", return_value=_mock_settings()):
        with patch("src.services.ai_processing.genai") as mock_genai:
            mock_client = MagicMock()
            mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
            mock_genai.Client.return_value = mock_client

            from src.services.ai_processing import AIProcessingService
            service = AIProcessingService()
            await service.summarize("테스트")

            call_kwargs = mock_client.aio.models.generate_content.call_args.kwargs
            assert call_kwargs["model"] == "gemini-2.5-flash"
