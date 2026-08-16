# apps/backend/tests/services/test_transcription.py
"""Whisper 트랜스크립션 서비스 테스트."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _mock_settings():
    """테스트용 Settings mock."""
    settings = MagicMock()
    settings.openai_api_key.get_secret_value.return_value = "sk-test"
    return settings


async def _fake_convert_to_wav(input_path: str) -> str:
    """convert_to_wav stub — ffmpeg 실제 호출 회피. fake bytes 환경 의존성 차단 (BL-030).

    transcribe() 가 finally 블록에서 wav_path 가 input_tmp 와 다르면 unlink 시도하므로
    input_tmp 자체를 그대로 반환하여 cleanup branch 일관성 유지.
    """
    return input_path


@pytest.mark.asyncio
async def test_transcribe_returns_segments():
    """Whisper API 응답을 TranscriptSegment 리스트로 변환."""
    # Whisper API mock 응답
    mock_segment_1 = MagicMock()
    mock_segment_1.start = 0.0
    mock_segment_1.end = 5.5
    mock_segment_1.text = "안녕하세요"

    mock_segment_2 = MagicMock()
    mock_segment_2.start = 5.5
    mock_segment_2.end = 12.3
    mock_segment_2.text = "회의를 시작하겠습니다"

    mock_response = MagicMock()
    mock_response.segments = [mock_segment_1, mock_segment_2]
    mock_response.duration = 12.3

    with patch("src.services.transcription.get_settings", return_value=_mock_settings()):
        with patch("src.services.transcription.convert_to_wav", _fake_convert_to_wav):
            with patch("src.services.transcription.AsyncOpenAI") as MockOpenAI:
                mock_client = AsyncMock()
                mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
                MockOpenAI.return_value = mock_client

                from src.services.transcription import TranscriptionService
                service = TranscriptionService()
                segments, duration = await service.transcribe(b"fake_audio_bytes")

    assert len(segments) == 2
    assert segments[0].speaker == "Speaker"
    assert segments[0].start_sec == 0.0
    assert segments[0].text == "안녕하세요"
    assert segments[1].end_sec == 12.3
    assert duration == 12.3


@pytest.mark.asyncio
async def test_transcribe_empty_audio():
    """빈 응답 시 빈 리스트 반환."""
    mock_response = MagicMock()
    mock_response.segments = []
    mock_response.duration = 0.0

    with patch("src.services.transcription.get_settings", return_value=_mock_settings()):
        with patch("src.services.transcription.convert_to_wav", _fake_convert_to_wav):
            with patch("src.services.transcription.AsyncOpenAI") as MockOpenAI:
                mock_client = AsyncMock()
                mock_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)
                MockOpenAI.return_value = mock_client

                from src.services.transcription import TranscriptionService
                service = TranscriptionService()
                segments, duration = await service.transcribe(b"empty")

    assert segments == []
    assert duration == 0.0
