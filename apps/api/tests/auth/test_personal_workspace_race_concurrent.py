# Sprint 27e BUG-S27e-TEST-2 — lazy seed 진정한 concurrent race 회귀 가드.
"""Sprint 27c BL-S27c-1 fix (auth/dependencies.py:158-221) 의 진정한 동시성 검증.

기존 test_personal_workspace_race.py 는 자체 주석에서 "진정한 동시 race (별개
connection) 는 carry-over — sequential INSERT 로 idempotency 만 검증" 명시.
본 spec 이 그 carry 를 해소 — 별개 connection 5개가 asyncio.gather 로 동시
호출되어도 Personal workspace 가 정확히 1개만 생성되는지.

ON CONFLICT (owner_id) WHERE type = 'personal' DO NOTHING + partial unique index
uq_workspaces_owner_personal 이 동시 INSERT 5건에서 1 row 만 살아남게 한다.
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession


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


@pytest_asyncio.fixture
async def concurrent_engine(postgres_container):
    """별개 connection 동시 사용을 위한 engine (function-scoped, pool_size 충분)."""
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(url, echo=False, pool_size=10, max_overflow=5)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
        # alembic partial unique index 가 testcontainers 에는 없음 → 명시 생성
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_workspaces_owner_personal "
                "ON workspaces (owner_id) WHERE type = 'personal'"
            )
        )

    yield engine
    await engine.dispose()


async def _seed_user(engine, user_id: uuid.UUID) -> None:
    """Pre-seed user row in own session (race 시작 전)."""
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as session:
        await session.execute(
            text(
                "INSERT INTO users (id, auth_user_id, display_name, email, created_at, updated_at) "
                "VALUES (:id, :ba, :name, :email, now(), now())"
            ),
            {
                "id": str(user_id),
                "ba": f"ba_concurrent_{user_id}",
                "name": "Concurrent Tester",
                "email": f"{user_id}@concurrent.test",
            },
        )
        await session.commit()


async def _concurrent_lazy_seed_task(
    engine,
    user_id: uuid.UUID,
    barrier: asyncio.Barrier,
    display_name: str = "Concurrent Tester",
) -> None:
    """별개 session 으로 lazy seed (dependencies.py:get_current_user 의 SQL 패턴 복제).

    asyncio.Barrier 가 N 개 task 가 모두 INSERT 직전까지 도달한 뒤 동시에 release.
    """
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as session:
        # barrier 직전까지 session 열어 connection 확보
        await barrier.wait()
        await session.execute(
            text(LAZY_SEED_WORKSPACE_SQL),
            {"owner_id": str(user_id), "name": f"{display_name}의 개인 Kairos"},
        )
        await session.execute(
            text(LAZY_SEED_MEMBER_SQL),
            {"owner_id": str(user_id)},
        )
        await session.commit()


@pytest.mark.asyncio
async def test_lazy_seed_concurrent_5_tasks_yields_single_workspace(concurrent_engine):
    """5 task 가 동시에 (asyncio.Barrier 로 race 정렬) lazy seed → personal workspace 1개만 생성."""
    user_id = uuid.uuid4()
    await _seed_user(concurrent_engine, user_id)

    n_concurrent = 5
    barrier = asyncio.Barrier(n_concurrent)
    tasks = [
        _concurrent_lazy_seed_task(concurrent_engine, user_id, barrier)
        for _ in range(n_concurrent)
    ]
    await asyncio.gather(*tasks)

    # 검증: 정확히 1개 personal workspace + 1개 WorkspaceMember(owner)
    sm = async_sessionmaker(concurrent_engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as verify_session:
        ws_count = (
            await verify_session.execute(
                text(
                    "SELECT COUNT(*) FROM workspaces "
                    "WHERE owner_id = :owner AND type = 'personal'"
                ),
                {"owner": str(user_id)},
            )
        ).scalar_one()
        member_count = (
            await verify_session.execute(
                text(
                    "SELECT COUNT(*) FROM workspace_members wm "
                    "JOIN workspaces w ON w.id = wm.workspace_id "
                    "WHERE w.owner_id = :owner AND w.type = 'personal' "
                    "AND wm.user_id = :owner AND wm.role = 'owner'"
                ),
                {"owner": str(user_id)},
            )
        ).scalar_one()

    assert ws_count == 1, (
        f"Concurrent race regression: expected 1 personal workspace, got {ws_count}. "
        "ON CONFLICT (owner_id) WHERE type='personal' DO NOTHING 가 무력화됨."
    )
    assert member_count == 1, (
        f"Concurrent member race regression: expected 1 owner member, got {member_count}. "
        "NOT EXISTS guard 가 동시성에서 깨짐."
    )


@pytest.mark.asyncio
async def test_lazy_seed_concurrent_10_tasks_yields_single_workspace(concurrent_engine):
    """더 가혹한 N=10 동시 race — 부하 증가 시에도 1 row 보장."""
    user_id = uuid.uuid4()
    await _seed_user(concurrent_engine, user_id)

    n_concurrent = 10
    barrier = asyncio.Barrier(n_concurrent)
    tasks = [
        _concurrent_lazy_seed_task(concurrent_engine, user_id, barrier)
        for _ in range(n_concurrent)
    ]
    await asyncio.gather(*tasks)

    sm = async_sessionmaker(concurrent_engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as verify_session:
        ws_count = (
            await verify_session.execute(
                text(
                    "SELECT COUNT(*) FROM workspaces "
                    "WHERE owner_id = :owner AND type = 'personal'"
                ),
                {"owner": str(user_id)},
            )
        ).scalar_one()

    assert ws_count == 1, f"N=10 concurrent race regression: got {ws_count} workspaces"
