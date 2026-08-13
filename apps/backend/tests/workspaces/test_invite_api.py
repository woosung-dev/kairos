# apps/backend/tests/workspaces/test_invite_api.py
"""초대/멤버 API 통합 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.rbac import require_admin, require_owner, require_viewer
from src.main import app
from src.workspaces.dependencies import get_invite_service
from src.workspaces.models import WorkspaceMember

WID = str(uuid.uuid4())
USER_ID = uuid.uuid4()


def _make_mock_member(role: str = "admin") -> WorkspaceMember:
    member = MagicMock(spec=WorkspaceMember)
    member.user_id = USER_ID
    member.workspace_id = uuid.UUID(WID)
    member.role = role
    return member


def _make_mock_user() -> User:
    user = MagicMock(spec=User)
    user.id = USER_ID
    user.clerk_id = "user_test"
    user.display_name = "테스트"
    user.email = "test@example.com"
    return user


@pytest_asyncio.fixture
async def mock_service():
    return AsyncMock()


@pytest_asyncio.fixture
async def client(mock_service):
    app.dependency_overrides[require_admin] = lambda: _make_mock_member("admin")
    app.dependency_overrides[require_owner] = lambda: _make_mock_member("owner")
    app.dependency_overrides[require_viewer] = lambda: _make_mock_member("viewer")
    app.dependency_overrides[get_current_user] = lambda: _make_mock_user()
    app.dependency_overrides[get_invite_service] = lambda: mock_service

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


# --- 초대 링크 테스트 ---


@pytest.mark.asyncio
async def test_create_invite(client, mock_service):
    """POST /workspaces/{id}/invites → 201."""
    mock_service.create_invite.return_value = {
        "id": str(uuid.uuid4()),
        "workspaceId": WID,
        "code": "abc123def456",
        "role": "member",
        "inviteUrl": f"http://localhost:3000/invite/abc123def456",
        "maxUses": None,
        "useCount": 0,
        "expiresAt": "2026-04-11T00:00:00",
        "isActive": True,
        "createdAt": "2026-04-04T00:00:00",
    }

    res = await client.post(
        f"/api/v1/workspaces/{WID}/invites",
        json={"role": "member"},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "abc123def456"
    assert data["role"] == "member"


@pytest.mark.asyncio
async def test_list_invites(client, mock_service):
    """GET /workspaces/{id}/invites → 200."""
    mock_service.list_invites.return_value = []

    res = await client.get(f"/api/v1/workspaces/{WID}/invites")
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_deactivate_invite(client, mock_service):
    """DELETE /workspaces/{id}/invites/{inviteId} → 204."""
    invite_id = str(uuid.uuid4())
    res = await client.delete(f"/api/v1/workspaces/{WID}/invites/{invite_id}")
    assert res.status_code == 204


# --- 공개 초대 링크 테스트 ---


@pytest.mark.asyncio
async def test_get_invite_info(client, mock_service):
    """GET /invites/{code} → 200."""
    mock_service.get_invite_info.return_value = {
        "workspaceName": "우리팀",
        "inviterName": "홍길동",
        "role": "member",
        "isValid": True,
        "reason": None,
    }

    res = await client.get("/api/v1/invites/abc123def456")
    assert res.status_code == 200
    assert res.json()["workspaceName"] == "우리팀"
    assert res.json()["isValid"] is True


@pytest.mark.asyncio
async def test_accept_invite(client, mock_service):
    """POST /invites/{code}/accept → 200."""
    mock_service.accept_invite.return_value = {
        "workspaceId": WID,
        "memberId": str(uuid.uuid4()),
        "role": "member",
    }

    res = await client.post("/api/v1/invites/abc123def456/accept")
    assert res.status_code == 200
    assert res.json()["role"] == "member"


# --- 멤버 관리 테스트 ---


@pytest.mark.asyncio
async def test_list_members(client, mock_service):
    """GET /workspaces/{id}/members → 200."""
    mock_service.list_members.return_value = [
        {
            "id": str(uuid.uuid4()),
            "userId": str(USER_ID),
            "email": "test@example.com",
            "displayName": "테스트",
            "role": "owner",
        }
    ]

    res = await client.get(f"/api/v1/workspaces/{WID}/members")
    assert res.status_code == 200
    assert len(res.json()) == 1


@pytest.mark.asyncio
async def test_update_member_role(client, mock_service):
    """PATCH /workspaces/{id}/members/{memberId} → 200."""
    member_id = str(uuid.uuid4())
    mock_service.update_member_role.return_value = {
        "id": member_id,
        "userId": str(USER_ID),
        "role": "admin",
    }

    res = await client.patch(
        f"/api/v1/workspaces/{WID}/members/{member_id}",
        json={"role": "admin"},
    )
    assert res.status_code == 200
    assert res.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_remove_member(client, mock_service):
    """DELETE /workspaces/{id}/members/{memberId} → 204."""
    member_id = str(uuid.uuid4())
    res = await client.delete(f"/api/v1/workspaces/{WID}/members/{member_id}")
    assert res.status_code == 204


# --- 유효성 검증 테스트 ---


@pytest.mark.asyncio
async def test_create_invite_invalid_role(client, mock_service):
    """잘못된 역할로 초대 → 422."""
    res = await client.post(
        f"/api/v1/workspaces/{WID}/invites",
        json={"role": "owner"},  # owner는 초대 불가
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_update_member_invalid_role(client, mock_service):
    """잘못된 역할로 변경 → 422."""
    member_id = str(uuid.uuid4())
    res = await client.patch(
        f"/api/v1/workspaces/{WID}/members/{member_id}",
        json={"role": "owner"},  # owner로 변경 불가
    )
    assert res.status_code == 422
