# backend/tests/notes/test_notes_api.py
"""노트 API 통합 테스트."""
import uuid

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.auth.rbac import require_member, require_member_fresh, require_viewer
from src.notes.dependencies import get_note_pipeline_service, get_note_service
from src.workspaces.models import WorkspaceMember

WID = "00000000-0000-0000-0000-000000000002"
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _make_mock_member(role: str = "member") -> WorkspaceMember:
    """테스트용 WorkspaceMember mock 생성."""
    member = MagicMock(spec=WorkspaceMember)
    member.user_id = USER_ID
    member.workspace_id = uuid.UUID(WID)
    member.role = role
    return member


@pytest_asyncio.fixture
async def mock_service():
    service = AsyncMock()
    service.create_note.return_value = {
        "id": "00000000-0000-0000-0000-000000000010",
        "workspaceId": "00000000-0000-0000-0000-000000000002",
        "projectId": None,
        "title": "테스트 노트",
        "content": {},
        "plainText": "",
        "createdById": "00000000-0000-0000-0000-000000000001",
        "createdAt": "2026-04-02T00:00:00",
        "updatedAt": "2026-04-02T00:00:00",
    }
    service.list_notes.return_value = {
        "items": [],
        "total": 0,
        "page": 1,
        "pageSize": 20,
        "hasNext": False,
    }
    service.get_note.return_value = service.create_note.return_value
    service.update_note.return_value = service.create_note.return_value
    service.embed_note_async = AsyncMock()
    return service


@pytest_asyncio.fixture
async def mock_pipeline():
    """Sprint 6 ADR-014 옵션 A: NotePipelineService mock (embed/delete orchestrator)."""
    pipeline = AsyncMock()
    pipeline.embed_note_async = AsyncMock(return_value=None)
    pipeline.delete_note_with_cleanup = AsyncMock(return_value=None)
    return pipeline


@pytest_asyncio.fixture
async def client(mock_service, mock_pipeline):
    app.dependency_overrides[require_member] = lambda: _make_mock_member("member")
    app.dependency_overrides[require_member_fresh] = lambda: _make_mock_member("member")
    app.dependency_overrides[require_viewer] = lambda: _make_mock_member("viewer")
    app.dependency_overrides[get_note_service] = lambda: mock_service
    app.dependency_overrides[get_note_pipeline_service] = lambda: mock_pipeline

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_note(client):
    res = await client.post(
        f"/api/v1/workspaces/{WID}/notes",
        json={"title": "테스트 노트"},
    )
    assert res.status_code == 201
    assert res.json()["title"] == "테스트 노트"


@pytest.mark.asyncio
async def test_list_notes(client):
    res = await client.get(f"/api/v1/workspaces/{WID}/notes")
    assert res.status_code == 200
    assert "items" in res.json()


@pytest.mark.asyncio
async def test_get_note(client):
    note_id = "00000000-0000-0000-0000-000000000010"
    res = await client.get(f"/api/v1/workspaces/{WID}/notes/{note_id}")
    assert res.status_code == 200
    assert res.json()["id"] == note_id


@pytest.mark.asyncio
async def test_update_note(client):
    note_id = "00000000-0000-0000-0000-000000000010"
    res = await client.patch(
        f"/api/v1/workspaces/{WID}/notes/{note_id}",
        json={"title": "수정된 노트"},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_delete_note(client):
    note_id = "00000000-0000-0000-0000-000000000010"
    res = await client.delete(f"/api/v1/workspaces/{WID}/notes/{note_id}")
    assert res.status_code == 204


@pytest.mark.asyncio
async def test_list_notes_with_project_filter(client):
    pid = "00000000-0000-0000-0000-000000000003"
    res = await client.get(f"/api/v1/workspaces/{WID}/notes?projectId={pid}")
    assert res.status_code == 200
