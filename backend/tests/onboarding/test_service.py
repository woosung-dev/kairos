# Onboarding service — idempotency + get_status 검증
import uuid

import pytest

from src.onboarding.service import OnboardingService


@pytest.mark.asyncio
async def test_increment_step_advances_when_target_higher(
    integration_session, auth_user
):
    service = OnboardingService(integration_session)
    await service.increment_step(auth_user.id, 1)
    await integration_session.flush()

    status = await service.get_status(auth_user.id)
    assert status.step == 1
    assert status.is_completed is False
    assert status.onboarded_at is None


@pytest.mark.asyncio
async def test_increment_step_idempotent_when_target_lower(
    integration_session, auth_user
):
    """target ≤ current → no-op (regression 방지)."""
    service = OnboardingService(integration_session)
    await service.increment_step(auth_user.id, 3)
    await service.increment_step(auth_user.id, 1)
    await integration_session.flush()

    status = await service.get_status(auth_user.id)
    assert status.step == 3


@pytest.mark.asyncio
async def test_step_4_sets_onboarded_at_and_completed(
    integration_session, auth_user
):
    service = OnboardingService(integration_session)
    await service.increment_step(auth_user.id, 4)
    await integration_session.flush()

    status = await service.get_status(auth_user.id)
    assert status.step == 4
    assert status.is_completed is True
    assert status.onboarded_at is not None


@pytest.mark.asyncio
async def test_get_status_returns_zero_for_missing_user(integration_session):
    """존재하지 않는 user → step=0 default."""
    service = OnboardingService(integration_session)
    status = await service.get_status(uuid.uuid4())
    assert status.step == 0
    assert status.is_completed is False
    assert status.onboarded_at is None
    assert status.total_steps == 4


@pytest.mark.asyncio
async def test_get_status_total_steps_is_4(integration_session, auth_user):
    service = OnboardingService(integration_session)
    status = await service.get_status(auth_user.id)
    assert status.total_steps == 4
