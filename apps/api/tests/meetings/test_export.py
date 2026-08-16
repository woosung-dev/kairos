# apps/api/tests/meetings/test_export.py
"""회의 내보내기 API 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.rbac import require_viewer
from src.main import app
from src.meetings.dependencies import get_meeting_service
from src.workspaces.models import WorkspaceMember

WID = str(uuid.uuid4())
MID = str(uuid.uuid4())


def _make_mock_member(role="viewer"):
    member = MagicMock(spec=WorkspaceMember)
    member.user_id = uuid.uuid4()
    member.workspace_id = uuid.UUID(WID)
    member.role = role
    return member


@pytest_asyncio.fixture
async def mock_service():
    return AsyncMock()


@pytest_asyncio.fixture
async def client(mock_service):
    app.dependency_overrides[require_viewer] = lambda: _make_mock_member("viewer")
    app.dependency_overrides[get_meeting_service] = lambda: mock_service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_export_meeting_md(client, mock_service):
    mock_service.export_meeting.return_value = (
        "# 테스트 회의\n\n## 요약\n테스트 요약입니다",
        "테스트 회의.md",
        "text/markdown; charset=utf-8",
    )
    res = await client.get(f"/api/v1/workspaces/{WID}/meetings/{MID}/export?format=md")
    assert res.status_code == 200
    assert "테스트 회의" in res.text


@pytest.mark.asyncio
async def test_export_meeting_json(client, mock_service):
    mock_service.export_meeting.return_value = (
        '{"title": "테스트 회의"}',
        "테스트 회의.json",
        "application/json; charset=utf-8",
    )
    res = await client.get(f"/api/v1/workspaces/{WID}/meetings/{MID}/export?format=json")
    assert res.status_code == 200
    assert res.json()["title"] == "테스트 회의"
