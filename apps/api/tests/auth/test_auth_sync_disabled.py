# `POST /api/v1/users/sync` endpoint 비활성화 회귀 테스트 (BUG-SENTINEL-005)
"""
Sprint 25 T-SEC-1 — BUG-SENTINEL-005 endpoint 비활성화 verify.

배경: Multi-Agent QA 2026-05-21 Sentinel 페르소나가 `POST /api/v1/users/sync`에
인증/Svix 서명 검증 없이 임의 페이로드로 user row 생성·덮어쓰기 가능 PoC 실측 (200 OK).
사용자 결정 (2026-05-21 memory `project_gcp_migration_jetaime_dev_done.md`):
Clerk webhook 의도적 SKIP + Clerk Production 인스턴스 미발급. → endpoint 비활성화.
"""
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.common.database import get_async_session
from src.main import app


@pytest_asyncio.fixture
async def client():
    """테스트용 HTTP 클라이언트. DB 세션을 mock으로 교체."""
    mock_session = AsyncMock()
    app.dependency_overrides[get_async_session] = lambda: mock_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_sync_endpoint_disabled_post(client):
    """POST /api/v1/users/sync → 404 또는 405 (endpoint 비활성화)."""
    payload = {
        "data": {
            "id": "user_test_should_be_blocked",
            "email_addresses": [{"email_address": "blocked@kairos.test"}],
            "first_name": "Test",
            "last_name": "Blocked",
        }
    }
    response = await client.post("/api/v1/users/sync", json=payload)
    assert response.status_code in (404, 405, 410), (
        f"sync_user endpoint should be disabled (404/405/410), got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_sync_endpoint_disabled_no_body(client):
    """빈 본문도 차단."""
    response = await client.post("/api/v1/users/sync")
    assert response.status_code in (404, 405, 410)


@pytest.mark.asyncio
async def test_get_me_route_still_works(client):
    """회귀 방지 — /users/me 라우트는 정상(401 인증 필요)."""
    response = await client.get("/api/v1/users/me")
    # 인증 없이 호출 → 401 또는 422 (validation). 200/404가 아님(라우트는 존재)
    assert response.status_code in (401, 422), (
        f"/users/me should still be routed (401/422), got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_users_prefix_still_registered(client):
    """회귀 방지 — `/api/v1/users` prefix 자체는 살아있다 (다른 라우트 정상)."""
    # 존재하지 않는 sub-path는 404, 그러나 prefix가 살아있다면 /me는 401
    me_resp = await client.get("/api/v1/users/me")
    nonexistent_resp = await client.get("/api/v1/users/does_not_exist")
    # /me는 401 (라우트 존재), nonexistent는 404 (라우트 없음) → prefix 정상
    assert me_resp.status_code != 404, "/api/v1/users prefix가 깨졌습니다 (router include 실패)"
    assert nonexistent_resp.status_code == 404
