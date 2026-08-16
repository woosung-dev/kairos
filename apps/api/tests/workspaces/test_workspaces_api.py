# apps/api/tests/workspaces/test_workspaces_api.py
"""Workspaces API 통합 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.common.database import get_async_session
from src.main import app
from src.workspaces.dependencies import get_workspace_service


@pytest_asyncio.fixture
async def client():
    mock_session = AsyncMock()
    app.dependency_overrides[get_async_session] = lambda: mock_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_user():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.clerk_id = "user_test123"
    user.display_name = "테스트"
    user.email = "test@example.com"
    user.avatar_url = None
    return user


@pytest.mark.asyncio
async def test_create_workspace(client, mock_user):
    """POST /workspaces → 201."""
    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_service = AsyncMock()
    mock_service.create_workspace.return_value = {
        "id": str(uuid.uuid4()),
        "name": "우리팀",
        "ownerId": str(mock_user.id),
        "createdAt": "2026-04-01T00:00:00",
        "updatedAt": "2026-04-01T00:00:00",
    }
    app.dependency_overrides[get_workspace_service] = lambda: mock_service

    response = await client.post(
        "/api/v1/workspaces",
        json={"name": "우리팀"},
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_list_workspaces(client, mock_user):
    """GET /workspaces → 200."""
    app.dependency_overrides[get_current_user] = lambda: mock_user

    mock_service = AsyncMock()
    mock_service.list_workspaces.return_value = []
    app.dependency_overrides[get_workspace_service] = lambda: mock_service

    response = await client.get(
        "/api/v1/workspaces",
        headers={"Authorization": "Bearer fake_token"},
    )
    assert response.status_code == 200
