# pipeline distillation 완료 시 onboarding step=3 hook 검증 (Sprint 22 OBN-02)
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.meetings.models import TranscriptSegment


def _make_session_factory():
    """테스트용 mock 세션 팩토리: async context manager 반환."""
    mock_session = AsyncMock()

    @asynccontextmanager
    async def factory():
        yield mock_session

    return factory


@pytest.mark.asyncio
async def test_pipeline_advances_onboarding_step_3_with_creator_id():
    """distillation 완료 → meeting.created_by_id 기준 step=3 advance.

    workspace owner 가 아닌 actual creator (회의 업로드한 user) 의 funnel 이 advance 되는지 검증.
    """
    from src.meetings.pipeline_service import MeetingPipelineService

    meeting_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    creator_id = uuid.uuid4()

    mock_meeting_repo = AsyncMock()
    mock_meeting = MagicMock()
    mock_meeting.id = meeting_id
    mock_meeting.workspace_id = workspace_id
    mock_meeting.title = "테스트 회의"
    mock_meeting.file_key = "uploads/test/audio.mp3"
    mock_meeting.created_by_id = creator_id
    mock_meeting_repo.find_by_id.return_value = mock_meeting
    mock_meeting_repo.session = MagicMock()  # OnboardingService(meeting_repo.session)

    mock_r2 = AsyncMock()
    mock_r2.get_download_url.return_value = "https://r2.example.com/audio.mp3"

    mock_transcription = AsyncMock()
    segments = [
        TranscriptSegment(speaker="화자", start_sec=0.0, end_sec=5.0, text="테스트"),
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
        "actionItems": [],
        "suggestedProject": {
            "existingProjectId": None,
            "newProjectTitle": "새 프로젝트",
            "confidence": 0.3,
        },
        "suggestedTags": [],
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
    mock_embedding_service.embed_meeting.return_value = 0
    mock_embedding_service.invalidate_cache.return_value = None

    with (
        patch(
            "src.meetings.pipeline_service.MeetingRepository",
            return_value=mock_meeting_repo,
        ),
        patch(
            "src.meetings.pipeline_service.ProjectRepository",
            return_value=mock_project_repo,
        ),
        patch(
            "src.meetings.pipeline_service.ActionItemRepository",
            return_value=mock_action_repo,
        ),
        patch(
            "src.meetings.pipeline_service.InboxRepository",
            return_value=mock_inbox_repo,
        ),
        patch(
            "src.meetings.pipeline_service.WorkspaceRepository",
            return_value=mock_workspace_repo,
        ),
        patch(
            "src.meetings.pipeline_service.EmbeddingRepository",
            return_value=AsyncMock(),
        ),
        patch(
            "src.meetings.pipeline_service.EmbeddingService",
            return_value=mock_embedding_service,
        ),
        patch(
            "src.onboarding.service.OnboardingService.increment_step"
        ) as mock_increment,
    ):
        mock_increment.return_value = None
        pipeline = MeetingPipelineService(
            session_factory=_make_session_factory(),
            r2_service=mock_r2,
            transcription_service=mock_transcription,
            ai_service=mock_ai,
        )
        await pipeline.process_meeting(meeting_id, workspace_id)

        # creator_id 기준으로 step=3 호출 검증
        mock_increment.assert_any_call(creator_id, 3)


@pytest.mark.asyncio
async def test_pipeline_skips_onboarding_when_created_by_id_is_none():
    """meeting.created_by_id is None → step=3 hook 호출 안 됨 (safety)."""
    from src.meetings.pipeline_service import MeetingPipelineService

    meeting_id = uuid.uuid4()
    workspace_id = uuid.uuid4()

    mock_meeting_repo = AsyncMock()
    mock_meeting = MagicMock()
    mock_meeting.id = meeting_id
    mock_meeting.workspace_id = workspace_id
    mock_meeting.title = "익명 회의"
    mock_meeting.file_key = "uploads/test/audio.mp3"
    mock_meeting.created_by_id = None
    mock_meeting_repo.find_by_id.return_value = mock_meeting
    mock_meeting_repo.session = MagicMock()

    mock_r2 = AsyncMock()
    mock_r2.get_download_url.return_value = "https://r2.example.com/audio.mp3"
    mock_transcription = AsyncMock()
    mock_transcription.download_audio.return_value = b"fake_audio"
    mock_transcription.transcribe.return_value = (
        [TranscriptSegment(speaker="화자", start_sec=0.0, end_sec=5.0, text="x")],
        5.0,
    )
    mock_ai = AsyncMock()
    mock_ai.summarize.return_value = {
        "summary": "x", "key_decisions": [], "topics": []
    }
    mock_ai.extract_actions_and_link.return_value = {
        "actionItems": [],
        "suggestedProject": {
            "existingProjectId": None, "newProjectTitle": None, "confidence": 0.0
        },
        "suggestedTags": [],
    }
    mock_workspace = MagicMock()
    mock_workspace.inbox_threshold = 0.9
    mock_workspace_repo = AsyncMock()
    mock_workspace_repo.find_by_id.return_value = mock_workspace
    mock_embedding_service = AsyncMock()
    mock_embedding_service.embed_meeting.return_value = 0
    mock_embedding_service.invalidate_cache.return_value = None

    with (
        patch(
            "src.meetings.pipeline_service.MeetingRepository",
            return_value=mock_meeting_repo,
        ),
        patch(
            "src.meetings.pipeline_service.ProjectRepository",
            return_value=AsyncMock(find_by_workspace=AsyncMock(return_value=[])),
        ),
        patch(
            "src.meetings.pipeline_service.ActionItemRepository",
            return_value=AsyncMock(),
        ),
        patch(
            "src.meetings.pipeline_service.InboxRepository", return_value=AsyncMock()
        ),
        patch(
            "src.meetings.pipeline_service.WorkspaceRepository",
            return_value=mock_workspace_repo,
        ),
        patch(
            "src.meetings.pipeline_service.EmbeddingRepository",
            return_value=AsyncMock(),
        ),
        patch(
            "src.meetings.pipeline_service.EmbeddingService",
            return_value=mock_embedding_service,
        ),
        patch(
            "src.onboarding.service.OnboardingService.increment_step"
        ) as mock_increment,
    ):
        mock_increment.return_value = None
        pipeline = MeetingPipelineService(
            session_factory=_make_session_factory(),
            r2_service=mock_r2,
            transcription_service=mock_transcription,
            ai_service=mock_ai,
        )
        await pipeline.process_meeting(meeting_id, workspace_id)

        # created_by_id None → step=3 hook 호출 안 됨
        for call in mock_increment.call_args_list:
            args = call.args
            assert not (len(args) >= 2 and args[1] == 3), (
                f"step=3 should not be called when created_by_id is None, got {args}"
            )
