# backend/tests/meetings/test_meeting_service.py
"""MeetingService 단위 테스트 — Sprint 14 T-8 (BUG-H04) projects 동기화 + 회귀 차단."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.meetings.service import MeetingService


def _make_meeting(meeting_id: uuid.UUID) -> MagicMock:
    """MeetingService._to_list_item 가 참조하는 필드만 채운 mock."""
    from datetime import datetime
    m = MagicMock()
    m.id = meeting_id
    m.workspace_id = uuid.uuid4()
    m.title = "테스트 회의"
    m.recorded_at = None
    m.duration_sec = 0
    m.status = "completed"
    m.has_transcript = False
    m.has_summary = False
    m.action_item_count = 0
    m.created_at = datetime(2026, 5, 13, 12, 0, 0)
    m.updated_at = datetime(2026, 5, 13, 12, 0, 0)
    return m


@pytest.mark.asyncio
async def test_get_meeting_detail_returns_linked_projects():
    """MeetingProjectLink 로 연결된 프로젝트가 projects 필드에 노출된다."""
    meeting_id = uuid.uuid4()
    proj_a = MagicMock(id=uuid.uuid4(), title="제품 로드맵", status="active", visibility="public")
    proj_b = MagicMock(id=uuid.uuid4(), title="신규 기능 spike", status="active", visibility="draft")

    mock_repo = AsyncMock()
    mock_repo.find_by_id.return_value = _make_meeting(meeting_id)
    mock_repo.get_segments.return_value = []
    mock_repo.get_summary.return_value = None

    mock_project_repo = AsyncMock()
    mock_project_repo.find_projects_by_meeting.return_value = [proj_a, proj_b]

    service = MeetingService(repo=mock_repo, project_repo=mock_project_repo)
    result = await service.get_meeting_detail(meeting_id)

    assert len(result["projects"]) == 2
    assert {p["title"] for p in result["projects"]} == {"제품 로드맵", "신규 기능 spike"}
    # camelCase 정합 (CONTEXT-MAP I-16) — id/title/status/visibility 4 필드
    for p in result["projects"]:
        assert set(p.keys()) == {"id", "title", "status", "visibility"}
        assert isinstance(p["id"], str)


@pytest.mark.asyncio
async def test_get_meeting_detail_empty_projects_when_no_links():
    """링크 없으면 projects 는 빈 배열."""
    meeting_id = uuid.uuid4()

    mock_repo = AsyncMock()
    mock_repo.find_by_id.return_value = _make_meeting(meeting_id)
    mock_repo.get_segments.return_value = []
    mock_repo.get_summary.return_value = None

    mock_project_repo = AsyncMock()
    mock_project_repo.find_projects_by_meeting.return_value = []

    service = MeetingService(repo=mock_repo, project_repo=mock_project_repo)
    result = await service.get_meeting_detail(meeting_id)

    assert result["projects"] == []


@pytest.mark.asyncio
async def test_get_meeting_detail_without_project_repo_still_returns_empty():
    """project_repo 주입 안 됐을 때도 안전하게 빈 배열 (테스트/하위호환)."""
    meeting_id = uuid.uuid4()

    mock_repo = AsyncMock()
    mock_repo.find_by_id.return_value = _make_meeting(meeting_id)
    mock_repo.get_segments.return_value = []
    mock_repo.get_summary.return_value = None

    service = MeetingService(repo=mock_repo)  # project_repo 없음
    result = await service.get_meeting_detail(meeting_id)

    assert result["projects"] == []
