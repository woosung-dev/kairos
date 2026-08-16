# Onboarding 도메인 테스트 전용 fixture (Sprint 22)
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def onboarding_client(integration_session, auth_user):
    """onboarding router 테스트용 client — get_current_user + get_async_session override."""
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session, get_session_factory
    from src.main import app

    def _dummy_factory():
        return None

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_session_factory] = _dummy_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()
