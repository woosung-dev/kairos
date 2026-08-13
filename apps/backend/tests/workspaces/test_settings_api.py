# backend/tests/workspaces/test_settings_api.py
"""워크스페이스 설정 API 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.rbac import require_owner
from src.main import app
from src.workspaces.dependencies import get_workspace_service
from src.workspaces.models import WorkspaceMember

WID = str(uuid.uuid4())


def _make_mock_member(role: str = "owner") -> WorkspaceMember:
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
    app.dependency_overrides[require_owner] = lambda: _make_mock_member("owner")
    app.dependency_overrides[get_workspace_service] = lambda: mock_service

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_threshold(client, mock_service):
    """PATCH /workspaces/{id}/settings → 200."""
    mock_service.update_settings.return_value = {"inboxThreshold": 0.8}

    res = await client.patch(
        f"/api/v1/workspaces/{WID}/settings",
        json={"inbox_threshold": 0.8},
    )
    assert res.status_code == 200
    assert res.json()["inboxThreshold"] == 0.8


@pytest.mark.asyncio
async def test_update_threshold_invalid_low(client, mock_service):
    """임계값 0.5 미만 → 422."""
    res = await client.patch(
        f"/api/v1/workspaces/{WID}/settings",
        json={"inbox_threshold": 0.3},
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_threshold_invalid_high(client, mock_service):
    """임계값 1.0 초과 → 422."""
    res = await client.patch(
        f"/api/v1/workspaces/{WID}/settings",
        json={"inbox_threshold": 1.5},
    )
    assert res.status_code == 422
