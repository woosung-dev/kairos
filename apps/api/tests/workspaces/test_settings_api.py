# apps/api/tests/workspaces/test_settings_api.py
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


@pytest.mark.asyncio
async def test_update_threshold_camel_alias(client, mock_service):
    """FE 가 보내는 camelCase alias `inboxThreshold` 도 200."""
    mock_service.update_settings.return_value = {"inboxThreshold": 0.8, "name": "팀"}

    res = await client.patch(
        f"/api/v1/workspaces/{WID}/settings",
        json={"inboxThreshold": 0.8},
    )
    assert res.status_code == 200
    mock_service.update_settings.assert_awaited_once_with(
        uuid.UUID(WID), inbox_threshold=0.8, name=None
    )


@pytest.mark.asyncio
async def test_update_name(client, mock_service):
    """이름만 보내면 200 + 서비스에 name 만 전달 (threshold 는 None)."""
    mock_service.update_settings.return_value = {"inboxThreshold": 0.9, "name": "새 이름"}

    res = await client.patch(
        f"/api/v1/workspaces/{WID}/settings",
        json={"name": "새 이름"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "새 이름"
    mock_service.update_settings.assert_awaited_once_with(
        uuid.UUID(WID), inbox_threshold=None, name="새 이름"
    )


@pytest.mark.asyncio
async def test_update_name_strips_whitespace(client, mock_service):
    """앞뒤 공백은 잘라서 서비스에 전달."""
    mock_service.update_settings.return_value = {"inboxThreshold": 0.9, "name": "팀"}

    res = await client.patch(
        f"/api/v1/workspaces/{WID}/settings",
        json={"name": "  팀  "},
    )
    assert res.status_code == 200
    mock_service.update_settings.assert_awaited_once_with(
        uuid.UUID(WID), inbox_threshold=None, name="팀"
    )


@pytest.mark.asyncio
async def test_update_empty_body(client, mock_service):
    """빈 PATCH → 422 (updated_at 만 바꾸는 쓰기 차단)."""
    res = await client.patch(f"/api/v1/workspaces/{WID}/settings", json={})
    assert res.status_code == 422
    mock_service.update_settings.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_name_blank(client, mock_service):
    """공백만 있는 이름 → 422."""
    res = await client.patch(
        f"/api/v1/workspaces/{WID}/settings",
        json={"name": "   "},
    )
    assert res.status_code == 422
    mock_service.update_settings.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_name_too_long(client, mock_service):
    """61자 이름 → 422."""
    res = await client.patch(
        f"/api/v1/workspaces/{WID}/settings",
        json={"name": "가" * 61},
    )
    assert res.status_code == 422
    mock_service.update_settings.assert_not_awaited()
