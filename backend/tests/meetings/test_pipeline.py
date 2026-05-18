# backend/tests/meetings/test_pipeline.py
"""Meeting 파이프라인 오케스트레이터 테스트."""
import uuid
from contextlib import asynccontextmanager

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.meetings.models import TranscriptSegment


def _make_session_factory():
    """테스트용 mock 세션 팩토리: async context manager를 반환한다."""
    mock_session = AsyncMock()

    @asynccontextmanager
    async def factory():
        yield mock_session

    return factory


@pytest.mark.asyncio
async def test_pipeline_success():
    """정상 파이프라인: uploading → transcribing → analyzing → completed."""
    from src.meetings.pipeline_service import MeetingPipelineService

    meeting_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    mock_meeting_repo = AsyncMock()
    mock_meeting = MagicMock()
    mock_meeting.id = meeting_id
    mock_meeting.workspace_id = workspace_id
    mock_meeting.title = "테스트 회의"
    mock_meeting.file_key = "uploads/test/audio.mp3"
    mock_meeting_repo.find_by_id.return_value = mock_meeting

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
    mock_ai.extract_actions_and_link.return_value = {
        "actionItems": [
            {"title": "액션1", "priority": "high"},
        ],
        "suggestedProject": {
            "existingProjectId": None,
            "newProjectTitle": "새 프로젝트",
            "confidence": 0.5,
        },
        "suggestedTags": ["테스트"],
    }

    mock_project_repo = AsyncMock()
    mock_project_repo.find_by_workspace.return_value = []
    mock_action_repo = AsyncMock()
    mock_inbox_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_workspace = MagicMock()
    mock_workspace.inbox_threshold = 0.9
    mock_workspace_repo.find_by_id.return_value = mock_workspace
    mock_embedding_service = AsyncMock()
    mock_embedding_service.embed_meeting.return_value = 3
    mock_embedding_service.invalidate_cache.return_value = None

    with (
        patch("src.meetings.pipeline_service.MeetingRepository", return_value=mock_meeting_repo),
        patch("src.meetings.pipeline_service.ProjectRepository", return_value=mock_project_repo),
        patch("src.meetings.pipeline_service.ActionItemRepository", return_value=mock_action_repo),
        patch("src.meetings.pipeline_service.InboxRepository", return_value=mock_inbox_repo),
        patch("src.meetings.pipeline_service.WorkspaceRepository", return_value=mock_workspace_repo),
        patch("src.meetings.pipeline_service.EmbeddingRepository", return_value=AsyncMock()),
        patch("src.meetings.pipeline_service.EmbeddingService", return_value=mock_embedding_service),
    ):
        pipeline = MeetingPipelineService(
            session_factory=_make_session_factory(),
            r2_service=mock_r2,
            transcription_service=mock_transcription,
            ai_service=mock_ai,
        )
        await pipeline.process_meeting(meeting_id, workspace_id)

    # 임베딩 생성 확인
    mock_embedding_service.embed_meeting.assert_called_once()

    # 상태 전이 확인 (Codex F-1: update_status 시그니처가 (meeting_id, workspace_id, status))
    status_calls = [call.args[2] for call in mock_meeting_repo.update_status.call_args_list]
    assert "transcribing" in status_calls
    assert "analyzing" in status_calls
    assert "completed" in status_calls

    # 세그먼트/요약 저장 확인
    mock_meeting_repo.save_segments.assert_called_once()
    mock_meeting_repo.save_summary.assert_called_once()
    mock_meeting_repo.set_has_transcript.assert_called_once_with(meeting_id, workspace_id, True)
    mock_meeting_repo.set_has_summary.assert_called_once_with(meeting_id, workspace_id, True)

    # 액션 아이템 저장 확인
    mock_action_repo.save.assert_called_once()

    # Inbox 저장 확인
    mock_inbox_repo.save.assert_called_once()

    # 자동 확정 안 됨 (confidence < 0.9)
    mock_project_repo.add_meeting_link.assert_not_called()


@pytest.mark.asyncio
async def test_pipeline_auto_confirm():
    """confidence >= 0.9이고 기존 프로젝트 있으면 자동 확정."""
    from src.meetings.pipeline_service import MeetingPipelineService

    meeting_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    project_id = uuid.uuid4()

    mock_meeting_repo = AsyncMock()
    mock_meeting = MagicMock()
    mock_meeting.id = meeting_id
    mock_meeting.workspace_id = workspace_id
    mock_meeting.title = "설계 리뷰"
    mock_meeting.file_key = "uploads/test/audio.mp3"
    mock_meeting_repo.find_by_id.return_value = mock_meeting

    mock_r2 = AsyncMock()
    mock_r2.get_download_url.return_value = "https://r2.example.com/audio.mp3"

    mock_transcription = AsyncMock()
    segments = [
        TranscriptSegment(speaker="Speaker", start_sec=0.0, end_sec=10.0, text="설계 논의"),
    ]
    mock_transcription.download_audio.return_value = b"fake_audio"
    mock_transcription.transcribe.return_value = (segments, 10.0)

    mock_ai = AsyncMock()
    mock_ai.summarize.return_value = {
        "summary": "설계 리뷰 요약",
        "key_decisions": [],
        "topics": [],
    }
    mock_ai.extract_actions_and_link.return_value = {
        "actionItems": [],
        "suggestedProject": {
            "existingProjectId": str(project_id),
            "newProjectTitle": None,
            "confidence": 0.9,
        },
        "suggestedTags": ["설계"],
    }

    mock_project_repo = AsyncMock()
    mock_project_repo.find_by_workspace.return_value = []
    mock_action_repo = AsyncMock()
    mock_inbox_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_workspace = MagicMock()
    mock_workspace.inbox_threshold = 0.9
    mock_workspace_repo.find_by_id.return_value = mock_workspace
    mock_embedding_service = AsyncMock()
    mock_embedding_service.embed_meeting.return_value = 3
    mock_embedding_service.invalidate_cache.return_value = None

    with (
        patch("src.meetings.pipeline_service.MeetingRepository", return_value=mock_meeting_repo),
        patch("src.meetings.pipeline_service.ProjectRepository", return_value=mock_project_repo),
        patch("src.meetings.pipeline_service.ActionItemRepository", return_value=mock_action_repo),
        patch("src.meetings.pipeline_service.InboxRepository", return_value=mock_inbox_repo),
        patch("src.meetings.pipeline_service.WorkspaceRepository", return_value=mock_workspace_repo),
        patch("src.meetings.pipeline_service.EmbeddingRepository", return_value=AsyncMock()),
        patch("src.meetings.pipeline_service.EmbeddingService", return_value=mock_embedding_service),
    ):
        pipeline = MeetingPipelineService(
            session_factory=_make_session_factory(),
            r2_service=mock_r2,
            transcription_service=mock_transcription,
            ai_service=mock_ai,
        )
        await pipeline.process_meeting(meeting_id, workspace_id)

    # 자동 확정 확인 (add_meeting_link 시그니처는 Phase 4 inbox commit 에서 workspace_id 추가 예정)
    mock_project_repo.add_meeting_link.assert_called_once_with(
        meeting_id, project_id
    )

    # InboxItem의 is_processed=True 확인
    inbox_call = mock_inbox_repo.save.call_args[0][0]
    assert inbox_call.is_processed is True


@pytest.mark.asyncio
async def test_pipeline_failure_sets_failed():
    """파이프라인 실패 시 status: failed + error_message 저장."""
    from src.meetings.pipeline_service import MeetingPipelineService

    meeting_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    mock_meeting_repo = AsyncMock()
    mock_meeting = MagicMock()
    mock_meeting.workspace_id = workspace_id
    mock_meeting.file_key = "uploads/test/audio.mp3"
    mock_meeting_repo.find_by_id.return_value = mock_meeting

    mock_r2 = AsyncMock()
    mock_r2.get_download_url.return_value = "https://example.com"

    mock_transcription = AsyncMock()
    mock_transcription.download_audio.side_effect = Exception("네트워크 오류")

    mock_ai = AsyncMock()
    mock_project_repo = AsyncMock()
    mock_action_repo = AsyncMock()
    mock_inbox_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_workspace_repo.find_by_id.return_value = None
    mock_embedding_service = AsyncMock()

    with (
        patch("src.meetings.pipeline_service.MeetingRepository", return_value=mock_meeting_repo),
        patch("src.meetings.pipeline_service.ProjectRepository", return_value=mock_project_repo),
        patch("src.meetings.pipeline_service.ActionItemRepository", return_value=mock_action_repo),
        patch("src.meetings.pipeline_service.InboxRepository", return_value=mock_inbox_repo),
        patch("src.meetings.pipeline_service.WorkspaceRepository", return_value=mock_workspace_repo),
        patch("src.meetings.pipeline_service.EmbeddingRepository", return_value=AsyncMock()),
        patch("src.meetings.pipeline_service.EmbeddingService", return_value=mock_embedding_service),
    ):
        pipeline = MeetingPipelineService(
            session_factory=_make_session_factory(),
            r2_service=mock_r2,
            transcription_service=mock_transcription,
            ai_service=mock_ai,
        )
        await pipeline.process_meeting(meeting_id, workspace_id)

    # failed 상태로 업데이트 확인 (Codex F-1: 시그니처 (meeting_id, workspace_id, status, ...))
    last_call = mock_meeting_repo.update_status.call_args_list[-1]
    assert last_call.args[2] == "failed"
    # error_message 확인 (positional 또는 keyword)
    error_msg = last_call.kwargs.get("error_message", "")
    if not error_msg and len(last_call.args) > 3:
        error_msg = last_call.args[3]
    assert "네트워크 오류" in error_msg


@pytest.mark.asyncio
async def test_capture_text_success():
    """capture_text: STT 없이 텍스트→분석→완료 경로."""
    from src.meetings.pipeline_service import MeetingPipelineService

    meeting_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    transcript_text = "오늘 회의에서 신규 기능 개발을 결정했습니다."

    mock_meeting_repo = AsyncMock()
    mock_meeting = MagicMock()
    mock_meeting.id = meeting_id
    mock_meeting.workspace_id = workspace_id
    mock_meeting.title = "텍스트 캡처 테스트"
    mock_meeting_repo.find_by_id.return_value = mock_meeting

    mock_r2 = AsyncMock()
    mock_transcription = AsyncMock()

    mock_ai = AsyncMock()
    mock_ai.summarize.return_value = {
        "summary": "기능 개발 결정",
        "key_decisions": ["신규 기능 개발"],
        "topics": ["개발"],
    }
    mock_ai.extract_actions_and_link.return_value = {
        "actionItems": [{"title": "기능 설계서 작성", "priority": "high"}],
        "suggestedProject": {
            "existingProjectId": None,
            "newProjectTitle": "신규 기능",
            "confidence": 0.6,
        },
        "suggestedTags": ["개발"],
    }

    mock_project_repo = AsyncMock()
    mock_project_repo.find_by_workspace.return_value = []
    mock_action_repo = AsyncMock()
    mock_inbox_repo = AsyncMock()
    mock_workspace_repo = AsyncMock()
    mock_workspace = MagicMock()
    mock_workspace.inbox_threshold = 0.9
    mock_workspace_repo.find_by_id.return_value = mock_workspace
    mock_embedding_service = AsyncMock()
    mock_embedding_service.embed_meeting.return_value = 1
    mock_embedding_service.invalidate_cache.return_value = None

    with (
        patch("src.meetings.pipeline_service.MeetingRepository", return_value=mock_meeting_repo),
        patch("src.meetings.pipeline_service.ProjectRepository", return_value=mock_project_repo),
        patch("src.meetings.pipeline_service.ActionItemRepository", return_value=mock_action_repo),
        patch("src.meetings.pipeline_service.InboxRepository", return_value=mock_inbox_repo),
        patch("src.meetings.pipeline_service.WorkspaceRepository", return_value=mock_workspace_repo),
        patch("src.meetings.pipeline_service.EmbeddingRepository", return_value=AsyncMock()),
        patch("src.meetings.pipeline_service.EmbeddingService", return_value=mock_embedding_service),
    ):
        pipeline = MeetingPipelineService(
            session_factory=_make_session_factory(),
            r2_service=mock_r2,
            transcription_service=mock_transcription,
            ai_service=mock_ai,
        )
        await pipeline.capture_text(meeting_id, workspace_id, transcript_text)

    # STT 메서드 호출 안 됨
    mock_r2.get_download_url.assert_not_called()
    mock_transcription.transcribe.assert_not_called()

    # 상태 전이 확인 (Codex F-1: update_status 시그니처 (meeting_id, workspace_id, status))
    status_calls = [call.args[2] for call in mock_meeting_repo.update_status.call_args_list]
    assert "transcribing" not in status_calls
    assert "analyzing" in status_calls
    assert "completed" in status_calls

    # 트랜스크립트/요약 저장 확인
    mock_meeting_repo.save_segments.assert_called_once()
    mock_meeting_repo.save_summary.assert_called_once()
    mock_meeting_repo.set_has_transcript.assert_called_once_with(meeting_id, workspace_id, True)
    mock_meeting_repo.set_has_summary.assert_called_once_with(meeting_id, workspace_id, True)

    # 액션 저장 확인
    mock_action_repo.save.assert_called_once()

    # Inbox 저장 확인
    mock_inbox_repo.save.assert_called_once()
