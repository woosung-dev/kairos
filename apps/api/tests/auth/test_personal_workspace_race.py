# Sprint 22 OBN-01 — personal workspace lazy seed race-safety 회귀 test
"""Sprint 15 dependencies.py:get_current_user() inline lazy seed (line 99-128) +
uq_workspaces_owner_personal partial unique index 의 idempotency 검증.

본 test 는 신규 코드 0건, 기존 lazy seed SQL 의 ON CONFLICT 동작 verify.
진정한 동시 race (별개 connection) 는 carry-over — 본 test 는 동일 session
sequential INSERT 로 idempotency 만 검증.
"""
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession


# Sprint 15 alembic a1b2c3d4e5f6 의 partial unique index — testcontainers DB 는
# SQLModel.metadata.create_all() 만 사용하므로 alembic migration 의 partial index 가 부재.
# 본 fixture 가 test scope 안에서 명시적으로 생성.
@pytest_asyncio.fixture
async def _ensure_partial_unique_index(integration_session: AsyncSession):
    await integration_session.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_workspaces_owner_personal "
            "ON workspaces (owner_id) WHERE type = 'personal'"
        )
    )
    await integration_session.flush()
    yield


# dependencies.py:get_current_user() 의 line 99-128 inline SQL 패턴 복제
LAZY_SEED_WORKSPACE_SQL = """
    INSERT INTO workspaces (id, owner_id, name, type, inbox_threshold, created_at, updated_at)
    VALUES (gen_random_uuid(), :owner_id, :name, 'personal', 0.9, now(), now())
    ON CONFLICT (owner_id) WHERE type = 'personal' DO NOTHING
"""

LAZY_SEED_MEMBER_SQL = """
    INSERT INTO workspace_members (id, workspace_id, user_id, role)
    SELECT gen_random_uuid(), w.id, w.owner_id, 'owner'
    FROM workspaces w
    WHERE w.owner_id = :owner_id AND w.type = 'personal'
      AND NOT EXISTS (
        SELECT 1 FROM workspace_members m
        WHERE m.workspace_id = w.id AND m.user_id = w.owner_id
      )
"""


async def _lazy_seed(session: AsyncSession, user_id: uuid.UUID, display_name: str) -> None:
    """dependencies.py:get_current_user() 의 line 99-128 inline SQL 복제."""
    await session.execute(
        text(LAZY_SEED_WORKSPACE_SQL),
        {"owner_id": str(user_id), "name": f"{display_name}의 개인 Kairos"},
    )
    await session.execute(
        text(LAZY_SEED_MEMBER_SQL),
        {"owner_id": str(user_id)},
    )


@pytest.mark.asyncio
async def test_lazy_seed_idempotent_single_personal_workspace(
    integration_session: AsyncSession, _ensure_partial_unique_index
):
    """동일 user_id 로 lazy seed 가 sequential 2회 호출되어도 personal workspace 1개만 생성.

    ON CONFLICT (owner_id) WHERE type = 'personal' DO NOTHING 가 두 번째 호출을 차단.
    """
    user_id = uuid.uuid4()

    # Pre-seed user row (인증 공급자 동기화 가정)
    await integration_session.execute(
        text(
            "INSERT INTO users (id, auth_user_id, display_name, email, created_at, updated_at) "
            "VALUES (:id, :ba, :name, :email, now(), now())"
        ),
        {
            "id": str(user_id),
            "ba": f"ba_{user_id}",
            "name": "Alice",
            "email": f"{user_id}@test.com",
        },
    )
    await integration_session.flush()

    # 2회 lazy seed
    await _lazy_seed(integration_session, user_id, "Alice")
    await _lazy_seed(integration_session, user_id, "Alice")
    await integration_session.flush()

    # 검증: personal workspace 정확히 1개
    result = await integration_session.execute(
        text(
            "SELECT COUNT(*) FROM workspaces "
            "WHERE owner_id = :owner AND type = 'personal'"
        ),
        {"owner": str(user_id)},
    )
    count = result.scalar_one()
    assert count == 1, f"Expected 1 personal workspace, got {count}"


@pytest.mark.asyncio
async def test_lazy_seed_creates_workspace_member_owner(
    integration_session: AsyncSession, _ensure_partial_unique_index
):
    """dependencies.py line 113-128 의 WorkspaceMember(owner) seed 검증."""
    user_id = uuid.uuid4()

    await integration_session.execute(
        text(
            "INSERT INTO users (id, auth_user_id, display_name, email, created_at, updated_at) "
            "VALUES (:id, :ba, :name, :email, now(), now())"
        ),
        {
            "id": str(user_id),
            "ba": f"ba_{user_id}",
            "name": "Bob",
            "email": f"{user_id}@test.com",
        },
    )
    await integration_session.flush()

    await _lazy_seed(integration_session, user_id, "Bob")
    await integration_session.flush()

    # WorkspaceMember(owner) row 1개 verify
    result = await integration_session.execute(
        text(
            "SELECT COUNT(*) FROM workspace_members wm "
            "JOIN workspaces w ON w.id = wm.workspace_id "
            "WHERE w.owner_id = :owner AND w.type = 'personal' "
            "AND wm.user_id = :owner AND wm.role = 'owner'"
        ),
        {"owner": str(user_id)},
    )
    count = result.scalar_one()
    assert count == 1


@pytest.mark.asyncio
async def test_lazy_seed_member_idempotent_on_repeat(
    integration_session: AsyncSession, _ensure_partial_unique_index
):
    """WorkspaceMember seed 의 NOT EXISTS guard 검증 (sequential 2회 호출 = 1 member)."""
    user_id = uuid.uuid4()

    await integration_session.execute(
        text(
            "INSERT INTO users (id, auth_user_id, display_name, email, created_at, updated_at) "
            "VALUES (:id, :ba, :name, :email, now(), now())"
        ),
        {
            "id": str(user_id),
            "ba": f"ba_{user_id}",
            "name": "Carol",
            "email": f"{user_id}@test.com",
        },
    )
    await integration_session.flush()

    await _lazy_seed(integration_session, user_id, "Carol")
    await _lazy_seed(integration_session, user_id, "Carol")
    await integration_session.flush()

    result = await integration_session.execute(
        text(
            "SELECT COUNT(*) FROM workspace_members wm "
            "JOIN workspaces w ON w.id = wm.workspace_id "
            "WHERE w.owner_id = :owner AND w.type = 'personal'"
        ),
        {"owner": str(user_id)},
    )
    count = result.scalar_one()
    assert count == 1, f"Expected 1 WorkspaceMember(owner), got {count}"
