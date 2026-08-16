# apps/api/tests/projects/test_members.py
"""ProjectMember 추가 API 시나리오 매트릭스 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.auth.rbac import require_admin
from src.common.database import get_async_session
from src.main import app
from src.projects.dependencies import get_project_service
from src.projects.exceptions import (
    CrossWorkspaceMemberError,
    ProjectNotFoundError,
    WorkspaceMismatchError,
)
from src.workspaces.models import WorkspaceMember

WS_A_ID = uuid.uuid4()
WS_B_ID = uuid.uuid4()
USER_A_ID = uuid.uuid4()
USER_B_ID = uuid.uuid4()
PROJECT_A_ID = uuid.uuid4()
PROJECT_B_ID = uuid.uuid4()


def _make_mock_ws_member(role: str = "admin") -> WorkspaceMember:
    m = MagicMock(spec=WorkspaceMember)
    m.user_id = USER_A_ID
    m.workspace_id = WS_A_ID
    m.role = role
    return m


@pytest_asyncio.fixture
async def client():
    mock_session = AsyncMock()
    app.dependency_overrides[get_async_session] = lambda: mock_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# 시나리오 1: 정상 추가 → 201
@pytest.mark.asyncio
async def test_add_member_same_workspace_201(client):
    app.dependency_overrides[require_admin] = lambda: _make_mock_ws_member()
    mock_service = AsyncMock()
    mock_service.add_member.return_value = {
        "id": str(uuid.uuid4()), "projectId": str(PROJECT_A_ID),
        "userId": str(USER_A_ID), "role": "member",
        "createdAt": "2026-01-01T00:00:00",
    }
    app.dependency_overrides[get_project_service] = lambda: mock_service
    response = await client.post(
        f"/api/v1/workspaces/{WS_A_ID}/projects/{PROJECT_A_ID}/members",
        json={"userId": str(USER_A_ID), "role": "member"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 201


# 시나리오 2: cross-workspace → 403
@pytest.mark.asyncio
async def test_add_member_cross_workspace_403(client):
    app.dependency_overrides[require_admin] = lambda: _make_mock_ws_member()
    mock_service = AsyncMock()
    mock_service.add_member.side_effect = CrossWorkspaceMemberError()
    app.dependency_overrides[get_project_service] = lambda: mock_service
    response = await client.post(
        f"/api/v1/workspaces/{WS_A_ID}/projects/{PROJECT_A_ID}/members",
        json={"userId": str(USER_B_ID), "role": "member"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 403


# 시나리오 3: 미존재 user_id → 403 (not 404)
@pytest.mark.asyncio
async def test_add_member_nonexistent_user_403(client):
    app.dependency_overrides[require_admin] = lambda: _make_mock_ws_member()
    mock_service = AsyncMock()
    mock_service.add_member.side_effect = CrossWorkspaceMemberError()
    app.dependency_overrides[get_project_service] = lambda: mock_service
    response = await client.post(
        f"/api/v1/workspaces/{WS_A_ID}/projects/{PROJECT_A_ID}/members",
        json={"userId": str(uuid.uuid4()), "role": "member"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 403


# 시나리오 4: viewer role 호출자 → 403 (RBAC gate)
@pytest.mark.asyncio
async def test_add_member_viewer_forbidden_403(client):
    def _raise_forbidden():
        raise HTTPException(status_code=403, detail="admin 이상 권한이 필요합니다")
    app.dependency_overrides[require_admin] = _raise_forbidden
    response = await client.post(
        f"/api/v1/workspaces/{WS_A_ID}/projects/{PROJECT_A_ID}/members",
        json={"userId": str(USER_A_ID), "role": "member"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 403


# 시나리오 5: 이미 ProjectMember 재추가 → 409
@pytest.mark.asyncio
async def test_add_member_duplicate_409(client):
    app.dependency_overrides[require_admin] = lambda: _make_mock_ws_member()
    mock_service = AsyncMock()
    mock_service.add_member.side_effect = HTTPException(
        status_code=409, detail="이미 프로젝트 멤버입니다"
    )
    app.dependency_overrides[get_project_service] = lambda: mock_service
    response = await client.post(
        f"/api/v1/workspaces/{WS_A_ID}/projects/{PROJECT_A_ID}/members",
        json={"userId": str(USER_A_ID), "role": "member"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 409


# 시나리오 6: workspace mismatch → 404
@pytest.mark.asyncio
async def test_add_member_workspace_mismatch_404(client):
    app.dependency_overrides[require_admin] = lambda: _make_mock_ws_member()
    mock_service = AsyncMock()
    mock_service.add_member.side_effect = WorkspaceMismatchError()
    app.dependency_overrides[get_project_service] = lambda: mock_service
    response = await client.post(
        f"/api/v1/workspaces/{WS_A_ID}/projects/{PROJECT_B_ID}/members",
        json={"userId": str(USER_A_ID), "role": "member"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 404


# 시나리오 7: 미존재 project_id → 404
@pytest.mark.asyncio
async def test_add_member_project_not_found_404(client):
    app.dependency_overrides[require_admin] = lambda: _make_mock_ws_member()
    mock_service = AsyncMock()
    mock_service.add_member.side_effect = ProjectNotFoundError()
    app.dependency_overrides[get_project_service] = lambda: mock_service
    response = await client.post(
        f"/api/v1/workspaces/{WS_A_ID}/projects/{uuid.uuid4()}/members",
        json={"userId": str(USER_A_ID), "role": "member"},
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 404
