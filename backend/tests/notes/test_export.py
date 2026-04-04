# backend/tests/notes/test_export.py
"""노트 내보내기 API 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.rbac import require_viewer
from src.main import app
from src.notes.dependencies import get_note_service
from src.workspaces.models import WorkspaceMember

WID = str(uuid.uuid4())
NID = str(uuid.uuid4())


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
    app.dependency_overrides[get_note_service] = lambda: mock_service
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_export_note_md(client, mock_service):
    mock_service.export_note.return_value = (
        "# 테스트 노트\n\n노트 내용입니다",
        "테스트 노트.md",
        "text/markdown; charset=utf-8",
    )
    res = await client.get(f"/api/v1/workspaces/{WID}/notes/{NID}/export?format=md")
    assert res.status_code == 200
    assert "테스트 노트" in res.text


@pytest.mark.asyncio
async def test_export_note_json(client, mock_service):
    mock_service.export_note.return_value = (
        '{"title": "테스트 노트", "plainText": "노트 내용입니다"}',
        "테스트 노트.json",
        "application/json; charset=utf-8",
    )
    res = await client.get(f"/api/v1/workspaces/{WID}/notes/{NID}/export?format=json")
    assert res.status_code == 200
    assert res.json()["title"] == "테스트 노트"
