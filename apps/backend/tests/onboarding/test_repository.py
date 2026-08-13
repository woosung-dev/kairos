# Onboarding repository — idempotent UPDATE 검증
import uuid

import pytest

from src.onboarding.repository import OnboardingRepository


@pytest.mark.asyncio
async def test_increment_advances_when_target_higher(integration_session, auth_user):
    """target > current → step UPDATE 적용."""
    repo = OnboardingRepository(integration_session)
    await repo.increment(auth_user.id, 2)
    await integration_session.flush()

    result = await integration_session.execute(
        __import__("sqlalchemy").text(
            "SELECT onboarding_step FROM users WHERE id = :uid"
        ),
        {"uid": auth_user.id},
    )
    assert result.first()[0] == 2


@pytest.mark.asyncio
async def test_increment_idempotent_when_target_lower(integration_session, auth_user):
    """target <= current → no-op (UPDATE 적용 안 됨)."""
    repo = OnboardingRepository(integration_session)
    await repo.increment(auth_user.id, 3)
    await repo.increment(auth_user.id, 1)  # 1 ≤ 3 → no-op
    await integration_session.flush()

    result = await integration_session.execute(
        __import__("sqlalchemy").text(
            "SELECT onboarding_step FROM users WHERE id = :uid"
        ),
        {"uid": auth_user.id},
    )
    assert result.first()[0] == 3


@pytest.mark.asyncio
async def test_increment_to_4_sets_onboarded_at(integration_session, auth_user):
    """target=4 → onboarded_at = now() set."""
    repo = OnboardingRepository(integration_session)
    await repo.increment(auth_user.id, 4)
    await integration_session.flush()

    result = await integration_session.execute(
        __import__("sqlalchemy").text(
            "SELECT onboarding_step, onboarded_at FROM users WHERE id = :uid"
        ),
        {"uid": auth_user.id},
    )
    row = result.first()
    assert row[0] == 4
    assert row[1] is not None


@pytest.mark.asyncio
async def test_increment_missing_user_no_error(integration_session):
    """존재하지 않는 user_id → no row updated, 에러 없음."""
    repo = OnboardingRepository(integration_session)
    await repo.increment(uuid.uuid4(), 1)
    await integration_session.flush()
    # 에러 없이 완료되면 PASS
