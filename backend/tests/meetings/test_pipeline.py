# backend/tests/meetings/test_pipeline.py
"""Meeting 파이프라인 오케스트레이터 테스트."""
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.meetings.models import TranscriptSegment


@pytest.mark.asyncio
async def test_pipeline_success():
    """정상 파이프라인: uploading → transcribing → summarizing → completed."""
    from src.meetings.pipeline_service import MeetingPipelineService

    meeting_id = uuid.uuid4()

    # Mock 의존성
    mock_repo = AsyncMock()
    mock_meeting = MagicMock()
    mock_meeting.file_key = "uploads/test/audio.mp3"
    mock_repo.find_by_id.return_value = mock_meeting

    mock_r2 = AsyncMock()
    mock_r2.get_download_url.return_value = "https://r2.example.com/audio.mp3"

    mock_transcription = AsyncMock()
    segments = [
        TranscriptSegment(speaker="Speaker", start_sec=0.0, end_sec=5.0, text="테스트"),
    ]
    mock_transcription.download_audio.return_value = b"fake_audio"
    mock_transcription.transcribe.return_value = (segments, 5.0)

    mock_ai = AsyncMock()
    mock_ai.summarize.return_value = {
        "summary": "테스트 요약",
        "key_decisions": [],
        "topics": ["테스트"],
    }

    pipeline = MeetingPipelineService(
        meeting_repo=mock_repo,
        r2_service=mock_r2,
        transcription_service=mock_transcription,
        ai_service=mock_ai,
    )

    await pipeline.process_meeting(meeting_id)

    # 상태 전이 확인
    status_calls = [call.args[1] for call in mock_repo.update_status.call_args_list]
    assert "transcribing" in status_calls
    assert "summarizing" in status_calls
    assert "completed" in status_calls

    # 세그먼트 저장 확인
    mock_repo.save_segments.assert_called_once()
    mock_repo.save_summary.assert_called_once()
    mock_repo.set_has_transcript.assert_called_once_with(meeting_id, True)
    mock_repo.set_has_summary.assert_called_once_with(meeting_id, True)


@pytest.mark.asyncio
async def test_pipeline_failure_sets_failed():
    """파이프라인 실패 시 status: failed + error_message 저장."""
    from src.meetings.pipeline_service import MeetingPipelineService

    meeting_id = uuid.uuid4()

    mock_repo = AsyncMock()
    mock_meeting = MagicMock()
    mock_meeting.file_key = "uploads/test/audio.mp3"
    mock_repo.find_by_id.return_value = mock_meeting

    mock_r2 = AsyncMock()
    mock_r2.get_download_url.return_value = "https://example.com"

    mock_transcription = AsyncMock()
    mock_transcription.download_audio.side_effect = Exception("네트워크 오류")

    mock_ai = AsyncMock()

    pipeline = MeetingPipelineService(
        meeting_repo=mock_repo,
        r2_service=mock_r2,
        transcription_service=mock_transcription,
        ai_service=mock_ai,
    )

    await pipeline.process_meeting(meeting_id)

    # failed 상태로 업데이트 확인
    last_call = mock_repo.update_status.call_args_list[-1]
    assert last_call.args[1] == "failed"
    # error_message 확인 (positional 또는 keyword)
    error_msg = last_call.kwargs.get("error_message", "")
    if not error_msg and len(last_call.args) > 2:
        error_msg = last_call.args[2]
    assert "네트워크 오류" in error_msg
