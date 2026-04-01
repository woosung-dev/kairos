# backend/tests/services/test_ai_processing.py
"""Claude AI 요약 서비스 테스트."""
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
    settings.anthropic_api_key.get_secret_value.return_value = "sk-ant-test"
    return settings


@pytest.mark.asyncio
async def test_summarize_returns_structured_dict():
    """Claude 응답을 구조화된 dict로 반환."""
    mock_content = MagicMock()
    mock_content.text = MOCK_SUMMARY_RESPONSE

    mock_response = MagicMock()
    mock_response.content = [mock_content]

    with patch("src.services.ai_processing.get_settings", return_value=_mock_settings()):
        with patch("src.services.ai_processing.anthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            from src.services.ai_processing import AIProcessingService
            service = AIProcessingService()
            result = await service.summarize("안녕하세요. 오늘 회의를 시작하겠습니다.")

    assert "summary" in result
    assert "key_decisions" in result
    assert isinstance(result["key_decisions"], list)


@pytest.mark.asyncio
async def test_summarize_with_code_fence():
    """코드펜스 포함된 Claude 응답도 파싱."""
    fenced = f"```json\n{MOCK_SUMMARY_RESPONSE}\n```"
    mock_content = MagicMock()
    mock_content.text = fenced

    mock_response = MagicMock()
    mock_response.content = [mock_content]

    with patch("src.services.ai_processing.get_settings", return_value=_mock_settings()):
        with patch("src.services.ai_processing.anthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            from src.services.ai_processing import AIProcessingService
            service = AIProcessingService()
            result = await service.summarize("테스트 트랜스크립트")

    assert result["summary"] is not None


@pytest.mark.asyncio
async def test_summarize_uses_correct_model():
    """claude-sonnet-4-20250514 모델 고정 확인."""
    mock_content = MagicMock()
    mock_content.text = MOCK_SUMMARY_RESPONSE

    mock_response = MagicMock()
    mock_response.content = [mock_content]

    with patch("src.services.ai_processing.get_settings", return_value=_mock_settings()):
        with patch("src.services.ai_processing.anthropic") as mock_anthropic:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_response)
            mock_anthropic.AsyncAnthropic.return_value = mock_client

            from src.services.ai_processing import AIProcessingService
            service = AIProcessingService()
            await service.summarize("테스트")

            # create 호출 인자 확인
            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs["model"] == "claude-sonnet-4-20250514"
