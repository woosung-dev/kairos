# backend/tests/test_cors.py
"""CORS 헤더 핸들러 시나리오 테스트."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.common.database import get_async_session
from src.main import ALLOWED_ORIGINS, app

# 허용 Origin 은 설정에서 가져온다 — main.py 의 ALLOWED_ORIGINS 와 같은 소스다.
# 하드코딩하면 로컬 .env 의 CORS_ORIGINS 가 그 값을 포함하지 않을 때 코드와 무관하게 깨진다
# (2026-07-31: CORS_ORIGINS 에 3000 이 없어 3건이 실패했다).
ALLOWED_ORIGIN = ALLOWED_ORIGINS[0]
DISALLOWED_ORIGIN = "http://evil.com"


@pytest_asyncio.fixture
async def client():
    """세션만 모킹하는 기본 클라이언트 (auth 미우회)."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_async_session] = lambda: mock_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def authed_client():
    """세션 + auth 모두 모킹한 클라이언트 (인증 우회).

    raise_app_exceptions=False: 5xx 예외를 재발생시키지 않고 응답으로 반환 (test_cors_5xx 테스트용).
    """
    mock_session = AsyncMock()
    mock_user = MagicMock(spec=User)
    mock_user.id = uuid.uuid4()

    app.dependency_overrides[get_async_session] = lambda: mock_session
    app.dependency_overrides[get_current_user] = lambda: mock_user
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


# (a) 허용 Origin → 200 + CORS 헤더
@pytest.mark.asyncio
async def test_cors_allowed_origin_200(client):
    response = await client.get(
        "/api/v1/health",
        headers={"Origin": ALLOWED_ORIGIN},
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


# (b) 5xx + 허용 Origin → CORS 헤더 포함
@pytest.mark.asyncio
async def test_cors_5xx_has_cors_headers(authed_client):
    # get_async_session을 RuntimeError로 오버라이드하여 5xx 유발
    def _raise_500():
        raise RuntimeError("의도적 500")
    app.dependency_overrides[get_async_session] = _raise_500
    response = await authed_client.get(
        "/api/v1/workspaces/00000000-0000-0000-0000-000000000001/projects",
        headers={"Origin": ALLOWED_ORIGIN, "Authorization": "Bearer fake"},
    )
    assert response.status_code == 500
    assert "access-control-allow-origin" in response.headers


# (c) 차단 Origin → CORS 헤더 없음
@pytest.mark.asyncio
async def test_cors_disallowed_origin_no_headers(client):
    response = await client.get(
        "/api/v1/health",
        headers={"Origin": DISALLOWED_ORIGIN},
    )
    assert "access-control-allow-origin" not in response.headers


# (d) RequestValidationError 422 + 허용 Origin → CORS 헤더 포함
@pytest.mark.asyncio
async def test_cors_422_request_validation_error(authed_client):
    response = await authed_client.post(
        "/api/v1/workspaces/invalid-uuid-here/projects",
        json={},
        headers={"Origin": ALLOWED_ORIGIN},
    )
    assert response.status_code == 422
    assert "access-control-allow-origin" in response.headers
