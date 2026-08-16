# 동시 초대 수락 race 회귀 가드 (QA-0617-D)
"""같은 초대 코드를 같은 user 가 동시에 2회 수락해도 500/IntegrityError 가
발생하지 않고, 정확히 1건만 성공 + 나머지는 MemberAlreadyExistsError 로 graceful
처리되며, 최종 WorkspaceMember row 가 1개임을 검증.

기존 버그: accept_invite 가 find_member 사전체크 후 add_member INSERT.
두 요청이 동시에 사전체크를 통과 → 둘 다 INSERT → uq_workspace_member UNIQUE
위반 → 처리되지 않은 IntegrityError → HTTP 500 (live: [500, 200]).

Fix: add_member 가 INSERT ... ON CONFLICT (workspace_id, user_id) DO NOTHING
RETURNING 으로 race-safe. 충돌(이미 멤버) 시 None 반환 → accept_invite 가
기존 멤버 re-fetch 후 MemberAlreadyExistsError raise.
(feedback_asyncpg_greenlet_precheck: flush + try/except IntegrityError 금지)
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.repository import UserRepository
from src.workspaces.exceptions import MemberAlreadyExistsError
from src.workspaces.invite_service import InviteService
from src.workspaces.repository import WorkspaceRepository


@pytest_asyncio.fixture
async def concurrent_engine(postgres_container):
    """별개 connection 동시 사용을 위한 engine (function-scoped, pool 충분)."""
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(url, echo=False, pool_size=10, max_overflow=5)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    yield engine
    await engine.dispose()


async def _seed_team_ws_and_invite(engine) -> tuple[uuid.UUID, uuid.UUID, str]:
    """team workspace + owner user + acceptor user + 활성 초대 코드 seed.

    반환: (workspace_id, acceptor_user_id, invite_code)
    """
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    owner_id = uuid.uuid4()
    acceptor_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    invite_id = uuid.uuid4()
    code = "concurrentcode"
    async with sm() as session:
        for uid, ba in [(owner_id, "owner"), (acceptor_id, "acceptor")]:
            await session.execute(
                text(
                    "INSERT INTO users (id, auth_user_id, display_name, email, created_at, updated_at) "
                    "VALUES (:id, :ba, :name, :email, now(), now())"
                ),
                {
                    "id": str(uid),
                    "ba": f"ba_{ba}_{uid}",
                    "name": ba,
                    "email": f"{uid}@concurrent.test",
                },
            )
        await session.execute(
            text(
                "INSERT INTO workspaces (id, owner_id, name, type, inbox_threshold, created_at, updated_at) "
                "VALUES (:id, :owner, 'Team', 'team', 0.9, now(), now())"
            ),
            {"id": str(ws_id), "owner": str(owner_id)},
        )
        # owner 멤버십
        await session.execute(
            text(
                "INSERT INTO workspace_members (id, workspace_id, user_id, role) "
                "VALUES (gen_random_uuid(), :ws, :owner, 'owner')"
            ),
            {"ws": str(ws_id), "owner": str(owner_id)},
        )
        await session.execute(
            text(
                "INSERT INTO workspace_invites "
                "(id, workspace_id, code, role, default_project_visibility, created_by_id, "
                " max_uses, use_count, is_active, created_at) "
                "VALUES (:id, :ws, :code, 'member', 'public', :owner, NULL, 0, true, now())"
            ),
            {"id": str(invite_id), "ws": str(ws_id), "code": code, "owner": str(owner_id)},
        )
        await session.commit()
    return ws_id, acceptor_id, code


def _barrier_repo(session, barrier: asyncio.Barrier) -> WorkspaceRepository:
    """add_member INSERT 직전에 barrier.wait() 를 끼운 repo.

    accept_invite 의 사전체크(find_member)와 INSERT 사이의 race window 를
    결정적으로 재현하려면, 두 task 가 정확히 INSERT 직전에 정렬돼야 한다.
    (task 시작점 barrier 만으로는 await 라운드트립 수가 많아 commit 순서가
    직렬화될 수 있어 race 가 안정적으로 재현되지 않음.)
    """
    repo = WorkspaceRepository(session)
    original_add_member = repo.add_member

    async def _add_member_with_barrier(member):
        await barrier.wait()  # 두 task 가 INSERT 직전에 정렬 후 동시 진입
        return await original_add_member(member)

    repo.add_member = _add_member_with_barrier  # type: ignore[method-assign]
    return repo


async def _accept_task(engine, code: str, user_id: uuid.UUID, barrier: asyncio.Barrier):
    """별개 session 으로 accept_invite 호출. 성공/예외를 분류 반환.

    반환: ("ok", member_dict) | ("already", None)
    """
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as session:
        service = InviteService(
            repo=_barrier_repo(session, barrier),
            user_repo=UserRepository(session),
        )
        try:
            result = await service.accept_invite(code, user_id)
            return ("ok", result)
        except MemberAlreadyExistsError:
            return ("already", None)


@pytest.mark.asyncio
async def test_concurrent_accept_invite_no_500_single_membership(concurrent_engine):
    """동시 2회 accept → 1 성공 + 1 MemberAlreadyExistsError, 500/IntegrityError 없음, 멤버십 1개."""
    ws_id, acceptor_id, code = await _seed_team_ws_and_invite(concurrent_engine)

    barrier = asyncio.Barrier(2)
    tasks = [
        _accept_task(concurrent_engine, code, acceptor_id, barrier),
        _accept_task(concurrent_engine, code, acceptor_id, barrier),
    ]
    # return_exceptions=True 로 unhandled 예외(IntegrityError/MissingGreenlet)도 포착
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 어떤 task 도 unhandled 예외(IntegrityError/MissingGreenlet 등 = 500 유발)를
    # 던지지 않아야 한다.
    for r in results:
        assert not isinstance(r, BaseException), (
            f"동시 accept 가 unhandled 예외로 500 유발: {type(r).__name__}: {r}"
        )

    outcomes = [r[0] for r in results]
    assert outcomes.count("ok") == 1, f"정확히 1건만 성공해야: {outcomes}"
    assert outcomes.count("already") == 1, (
        f"나머지 1건은 MemberAlreadyExistsError 여야: {outcomes}"
    )

    # 최종 멤버십 검증 — (ws, acceptor) 조합 정확히 1 row
    sm = async_sessionmaker(concurrent_engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as verify:
        member_count = (
            await verify.execute(
                text(
                    "SELECT COUNT(*) FROM workspace_members "
                    "WHERE workspace_id = :ws AND user_id = :uid"
                ),
                {"ws": str(ws_id), "uid": str(acceptor_id)},
            )
        ).scalar_one()
    assert member_count == 1, (
        f"동시 accept 후 멤버십 row 가 정확히 1개여야: got {member_count}"
    )
