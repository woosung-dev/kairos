# Onboarding router — GET /api/v1/users/me/onboarding 응답 검증
import pytest

from src.onboarding.service import OnboardingService


@pytest.mark.asyncio
async def test_get_onboarding_returns_current_status(
    onboarding_client, integration_session, auth_user
):
    """기본 step=0 응답 — 정확한 schema 검증."""
    response = await onboarding_client.get("/api/v1/users/me/onboarding")
    assert response.status_code == 200
    body = response.json()
    assert body["step"] == 0
    assert body["totalSteps"] == 4
    assert body["onboardedAt"] is None
    assert body["isCompleted"] is False


@pytest.mark.asyncio
async def test_get_onboarding_reflects_advanced_step(
    onboarding_client, integration_session, auth_user
):
    """advance 후 GET 응답 검증."""
    service = OnboardingService(integration_session)
    await service.increment_step(auth_user.id, 2)
    await integration_session.flush()

    response = await onboarding_client.get("/api/v1/users/me/onboarding")
    assert response.status_code == 200
    body = response.json()
    assert body["step"] == 2
    assert body["isCompleted"] is False


@pytest.mark.asyncio
async def test_get_onboarding_step_4_completed(
    onboarding_client, integration_session, auth_user
):
    """step=4 도달 시 isCompleted=True + onboardedAt 존재."""
    service = OnboardingService(integration_session)
    await service.increment_step(auth_user.id, 4)
    await integration_session.flush()

    response = await onboarding_client.get("/api/v1/users/me/onboarding")
    assert response.status_code == 200
    body = response.json()
    assert body["step"] == 4
    assert body["isCompleted"] is True
    assert body["onboardedAt"] is not None
