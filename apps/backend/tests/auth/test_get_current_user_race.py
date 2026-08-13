# Sprint 27c P0-S27c-1 — get_current_user lazy seed User race-safety 회귀 test
"""dependencies.py:get_current_user() inline lazy seed (line 158-178) +
`ix_users_clerk_id` UNIQUE index 의 idempotency 검증.

배경 (Sprint 27c audit): Dashboard 첫 진입 시 FE 가 5+ API 동시 호출 → 각 transaction 의
User INSERT race → UniqueViolation `ix_users_clerk_id` → 500.

Fix (`dependencies.py:165-178`): User INSERT 에 `ON CONFLICT (clerk_id) DO NOTHING` 추가
(workspace INSERT 패턴 정합). Re-fetch after race-safe INSERT.

본 test 는 신규 코드 0건, 새 fix 의 ON CONFLICT 동작 verify. 진정한 동시 race (별개 connection)
는 carry-over — test_personal_workspace_race.py 와 같이 sequential INSERT 로 idempotency
만 검증.
"""
import uuid

import pytest
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession


# dependencies.py:165-178 inline SQL 패턴 복제
LAZY_SEED_USER_SQL = """
    INSERT INTO users (id, clerk_id, display_name, email, created_at, updated_at, onboarding_step)
    VALUES (gen_random_uuid(), :clerk_id, :name, :email, now(), now(), 0)
    ON CONFLICT (clerk_id) DO NOTHING
"""


async def _lazy_seed_user(
    session: AsyncSession, clerk_id: str, name: str, email: str
) -> None:
    """dependencies.py:get_current_user() 의 User INSERT 정합 복제."""
    await session.execute(
        text(LAZY_SEED_USER_SQL),
        {"clerk_id": clerk_id, "name": name, "email": email},
    )


@pytest.mark.asyncio
async def test_user_lazy_seed_idempotent_single_user(
    integration_session: AsyncSession,
):
    """동일 clerk_id 로 lazy seed sequential 2회 호출 → user row 정확히 1개.

    ON CONFLICT (clerk_id) DO NOTHING 가 두 번째 호출을 차단.
    """
    clerk_id = f"clerk_test_{uuid.uuid4()}"

    # 2회 lazy seed
    await _lazy_seed_user(integration_session, clerk_id, "Alice", "alice@test.com")
    await _lazy_seed_user(integration_session, clerk_id, "Alice", "alice@test.com")
    await integration_session.flush()

    # 검증: user 정확히 1개
    result = await integration_session.execute(
        text("SELECT COUNT(*) FROM users WHERE clerk_id = :clerk"),
        {"clerk": clerk_id},
    )
    count = result.scalar_one()
    assert count == 1, f"Expected 1 user row, got {count}"


@pytest.mark.asyncio
async def test_user_lazy_seed_5_sequential_no_integrity_error(
    integration_session: AsyncSession,
):
    """Dashboard 첫 진입 시뮬레이션 — 동일 clerk_id 로 5회 sequential INSERT.

    Race condition fix 이전: 두 번째부터 IntegrityError raise.
    Fix 후 (ON CONFLICT): 5회 모두 성공 + user row 1개 유지.
    """
    clerk_id = f"clerk_dashboard_{uuid.uuid4()}"

    # 5회 sequential lazy seed (Dashboard 의 5+ API 동시 호출 simulation)
    for i in range(5):
        await _lazy_seed_user(
            integration_session,
            clerk_id,
            f"User{i}",
            f"user{i}@test.com",
        )
    await integration_session.flush()

    # 검증: IntegrityError 없이 모두 통과 + user 1개
    result = await integration_session.execute(
        text("SELECT COUNT(*) FROM users WHERE clerk_id = :clerk"),
        {"clerk": clerk_id},
    )
    count = result.scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_user_lazy_seed_empty_name_email_allowed(
    integration_session: AsyncSession,
):
    """Clerk JWT claims 에 name/email 누락 시 fallback ("사용자", "") 으로 INSERT 통과.

    `verify_clerk_token` 이 `{"sub": ...}` 만 return → claims.get("name", "사용자") +
    claims.get("email", "") fallback 적용. User.email 은 NOT NULL but UNIQUE 아님
    (auth/models.py:15) → 빈 문자열 다수 row 허용.
    """
    clerk_id_1 = f"clerk_empty1_{uuid.uuid4()}"
    clerk_id_2 = f"clerk_empty2_{uuid.uuid4()}"

    # 다른 clerk_id 인데 email 둘 다 "" — 통과 verify
    await _lazy_seed_user(integration_session, clerk_id_1, "사용자", "")
    await _lazy_seed_user(integration_session, clerk_id_2, "사용자", "")
    await integration_session.flush()

    result = await integration_session.execute(
        text("SELECT COUNT(*) FROM users WHERE email = ''"),
    )
    count = result.scalar_one()
    assert count >= 2  # 본 test 추가 2건 (이전 test 영향 가능, >= 로 robust)
