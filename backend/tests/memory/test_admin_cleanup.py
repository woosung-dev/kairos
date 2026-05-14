# Sprint 15 R-CRON — admin cleanup endpoint 통합 테스트
"""Cron secret token + days 파라미터 검증 + cleanup_expired_r2_audio 동작."""
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_r2_cleanup_invalid_token_returns_403(integration_session):
    """잘못된 X-Cron-Token → 403."""
    from src.common.database import get_async_session
    from src.main import app

    from src.common.database import get_session_factory
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_session_factory] = lambda: None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.post(
            "/api/v1/admin/memory/r2-cleanup",
            headers={"X-Cron-Token": "wrong-token"},
        )
    app.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_r2_cleanup_no_token_returns_403(integration_session):
    """X-Cron-Token 헤더 누락 → 403."""
    from src.common.database import get_async_session
    from src.main import app

    from src.common.database import get_session_factory
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_session_factory] = lambda: None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.post("/api/v1/admin/memory/r2-cleanup")
    app.dependency_overrides.clear()
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_r2_cleanup_valid_token_returns_200(integration_session, monkeypatch):
    """올바른 token + 빈 DB → 200 + deleted_count=0."""
    from src.common.database import get_async_session
    from src.core.config import get_settings
    from src.main import app
    from src.memory import service as memory_service

    settings = get_settings()
    valid_token = settings.cron_secret_token.get_secret_value()

    # 실제 R2 호출 차단 — 빈 DB이므로 어차피 0건이지만 안전 monkeypatch
    async def _noop_cleanup(*args, **kwargs):
        return 0

    monkeypatch.setattr(memory_service.MemoryService, "cleanup_expired_r2_audio", _noop_cleanup)

    from src.common.database import get_session_factory
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_session_factory] = lambda: None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.post(
            "/api/v1/admin/memory/r2-cleanup",
            headers={"X-Cron-Token": valid_token},
        )
    app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["deleted_count"] == 0
    assert body["ttl_days"] == 30


@pytest.mark.asyncio
async def test_r2_cleanup_days_param_validated(integration_session):
    """days < 1 → 422."""
    from src.common.database import get_async_session
    from src.core.config import get_settings
    from src.main import app

    settings = get_settings()
    valid_token = settings.cron_secret_token.get_secret_value()

    from src.common.database import get_session_factory
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_session_factory] = lambda: None
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        response = await c.post(
            "/api/v1/admin/memory/r2-cleanup?days=0",
            headers={"X-Cron-Token": valid_token},
        )
    app.dependency_overrides.clear()
    assert response.status_code == 422
