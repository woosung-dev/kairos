# lazy seed path (signup primary) onboarding step=1 hook 검증 (Sprint 22 OBN-02)
import pytest
import pytest_asyncio
from sqlalchemy import text

from src.auth.dependencies import get_current_user
from src.onboarding.service import OnboardingService


@pytest_asyncio.fixture
async def with_partial_index(integration_session):
    """lazy seed 의 ON CONFLICT (owner_id) WHERE type='personal' 을 위해
    partial unique index 를 test schema 에 보강.

    alembic R2 migration (a1b2c3d4e5f6) 에서 생성되지만 testcontainers 의
    SQLModel.metadata.create_all 은 partial index 미생성 → 명시적 보강.
    """
    await integration_session.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_workspaces_owner_personal "
            "ON workspaces (owner_id) WHERE type = 'personal'"
        )
    )
    await integration_session.flush()
    return integration_session


@pytest.mark.asyncio
async def test_lazy_seed_signup_advances_onboarding_step_to_1(
    with_partial_index, integration_session
):
    """첫 로그인 (신규 user) → personal workspace seed → step=1 advance."""
    claims = {
        "sub": "user_test_onboarding_lazy_seed",
        "email": "lazy_seed@kairos.test",
        "name": "Lazy Seed Tester",
    }

    user = await get_current_user(claims=claims, session=integration_session)

    onboarding = OnboardingService(integration_session)
    status = await onboarding.get_status(user.id)
    assert status.step == 1


@pytest.mark.asyncio
async def test_lazy_seed_existing_user_advances_step_to_1_if_lower(
    with_partial_index, integration_session, auth_user
):
    """기존 user (step=0) → lazy seed path → step=1 backfill."""
    # 기존 user 이지만 onboarding_step=0 인 상태에서 get_current_user 재호출
    claims = {"sub": auth_user.clerk_id, "email": auth_user.email}
    user = await get_current_user(claims=claims, session=integration_session)
    assert user.id == auth_user.id

    onboarding = OnboardingService(integration_session)
    status = await onboarding.get_status(user.id)
    assert status.step == 1
