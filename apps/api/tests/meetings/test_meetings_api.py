# apps/backend/tests/meetings/test_meetings_api.py
"""Meetings API 통합 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.rbac import require_member, require_viewer
from src.common.database import get_async_session
from src.main import app
from src.meetings.dependencies import get_meeting_service, get_pipeline_service
from src.workspaces.models import WorkspaceMember

WORKSPACE_ID = str(uuid.uuid4())
USER_ID = uuid.uuid4()


def _make_mock_member(role: str = "member") -> WorkspaceMember:
    """테스트용 WorkspaceMember mock 생성."""
    member = MagicMock(spec=WorkspaceMember)
    member.user_id = USER_ID
    member.workspace_id = uuid.UUID(WORKSPACE_ID)
    member.role = role
    return member


@pytest_asyncio.fixture
async def client():
    mock_session = AsyncMock()
    app.dependency_overrides[get_async_session] = lambda: mock_session
    # RBAC 의존성 override — member 역할
    app.dependency_overrides[require_member] = lambda: _make_mock_member("member")
    app.dependency_overrides[require_viewer] = lambda: _make_mock_member("viewer")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_meeting_returns_202(client):
    """POST /meetings → 202 Accepted."""
    mock_service = AsyncMock()
    meeting_id = str(uuid.uuid4())
    mock_service.create_meeting.return_value = {
        "id": meeting_id,
        "status": "uploading",
        "message": "파이프라인이 시작되었습니다",
    }
    app.dependency_overrides[get_meeting_service] = lambda: mock_service

    # pipeline도 mock (BackgroundTasks에서 사용)
    mock_pipeline = AsyncMock()
    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline

    response = await client.post(
        f"/api/v1/workspaces/{WORKSPACE_ID}/meetings",
        json={
            "title": "테스트 회의",
            "fileKey": "uploads/test/meeting.mp3",
        },
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "uploading"


@pytest.mark.asyncio
async def test_get_meeting_status(client):
    """GET /meetings/{id}/status → 200."""
    meeting_id = str(uuid.uuid4())
    mock_service = AsyncMock()
    mock_service.get_meeting_status.return_value = {
        "status": "completed",
        "errorMessage": None,
    }
    app.dependency_overrides[get_meeting_service] = lambda: mock_service

    response = await client.get(
        f"/api/v1/workspaces/{WORKSPACE_ID}/meetings/{meeting_id}/status",
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_list_meetings(client):
    """GET /meetings → 200 + PaginatedResponse."""
    mock_service = AsyncMock()
    mock_service.list_meetings.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "pageSize": 20,
        "hasNext": False,
    }
    app.dependency_overrides[get_meeting_service] = lambda: mock_service

    response = await client.get(
        f"/api/v1/workspaces/{WORKSPACE_ID}/meetings",
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0
