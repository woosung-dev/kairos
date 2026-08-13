# backend/tests/auth/test_auth_api.py
"""Auth API 통합 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user, verify_clerk_token
from src.auth.models import User
from src.common.database import get_async_session
from src.main import app


@pytest_asyncio.fixture
async def client():
    """테스트용 HTTP 클라이언트. DB 세션을 mock으로 교체."""
    # DB 세션 mock
    mock_session = AsyncMock()
    app.dependency_overrides[get_async_session] = lambda: mock_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# 테스트용 사용자
def _make_mock_user() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.clerk_id = "user_test123"
    user.display_name = "테스트 사용자"
    user.email = "test@example.com"
    user.avatar_url = None
    return user


@pytest.mark.asyncio
async def test_get_me_unauthorized(client):
    """인증 없이 /users/me 호출 시 401 또는 422."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code in (401, 422)


@pytest.mark.asyncio
async def test_get_me_success(client):
    """유효한 토큰으로 /users/me 호출 시 200 + 사용자 정보."""
    mock_user = _make_mock_user()
    # get_current_user 의존성 override
    app.dependency_overrides[get_current_user] = lambda: mock_user
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer fake_valid_token"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["clerkId"] == "user_test123"
    assert data["email"] == "test@example.com"
