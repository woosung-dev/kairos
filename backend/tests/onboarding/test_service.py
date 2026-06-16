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


# ── Sprint 29 R1 (auth-cache): step 변경 시 User cache 무효화 회귀 가드 ──


@pytest.mark.asyncio
async def test_increment_step_invalidates_user_cache(integration_session, auth_user):
    """step 변경 시 User cache(clerk_id, 60s TTL) 무효화 → /me onboardingStep stale 제거.

    이전엔 invalidate_user_cache 호출자가 0건 → 최대 60s stale. 이제 increment_step 이
    RETURNING clerk_id 로 변경을 감지해 중앙에서 무효화한다.
    """
    from src.auth import dependencies as auth_deps

    auth_deps._user_cache_set(auth_user.clerk_id, auth_user)
    assert auth_deps._user_cache_get(auth_user.clerk_id) is not None

    service = OnboardingService(integration_session)
    await service.increment_step(auth_user.id, 2)  # 0 → 2 (변경)

    assert auth_deps._user_cache_get(auth_user.clerk_id) is None


@pytest.mark.asyncio
async def test_increment_step_noop_keeps_user_cache(integration_session, auth_user):
    """이미 advance 된 step → no-op(clerk_id=None) → cache 유지(불필요 무효화 방지)."""
    from src.auth import dependencies as auth_deps

    service = OnboardingService(integration_session)
    await service.increment_step(auth_user.id, 3)  # 0 → 3 (변경)

    auth_deps._user_cache_set(auth_user.clerk_id, auth_user)
    await service.increment_step(auth_user.id, 1)  # 3 ≥ 1 → no-op

    assert auth_deps._user_cache_get(auth_user.clerk_id) is not None
