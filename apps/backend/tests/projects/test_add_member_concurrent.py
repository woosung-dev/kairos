# F4 (2026-06-23 fullsweep) — ProjectMember 동시 추가 race 회귀 가드
"""같은 (project_id, user_id) 를 동시에 2회 add_member 해도 500/IntegrityError 가
발생하지 않고, 정확히 1건만 성공 + 나머지는 AlreadyExistsError(409) 로 graceful
처리되며, 최종 ProjectMember row 가 1개임을 검증.

기존 버그(BE-1): service.add_member 가 is_member 사전체크 후 repo.add_member 가
plain session.add+flush. 두 요청이 동시에 사전체크를 통과 → 둘 다 INSERT →
uq_project_member UNIQUE 위반 → 처리되지 않은 IntegrityError → asyncpg+greenlet
MissingGreenlet → HTTP 500. WorkspaceMember(QA-0617-D)는 ON CONFLICT 로 이미 해소.

Fix: repo.add_member 가 INSERT ... ON CONFLICT (project_id, user_id) DO NOTHING
RETURNING 으로 race-safe. 충돌 시 None → service 가 AlreadyExistsError raise.
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

from src.common.exceptions import AlreadyExistsError
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
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


async def _seed_ws_project(engine) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    """team workspace + owner + acceptor(ws member) + public project seed.

    반환: (workspace_id, project_id, acceptor_user_id)
    """
    from src.auth.models import User
    from src.projects.models import Project
    from src.workspaces.models import Workspace, WorkspaceMember

    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as s:
        owner = User(clerk_id=f"clerk_o_{uuid.uuid4().hex}", display_name="o", email=f"o_{uuid.uuid4().hex}@c.test")
        acceptor = User(clerk_id=f"clerk_a_{uuid.uuid4().hex}", display_name="a", email=f"a_{uuid.uuid4().hex}@c.test")
        s.add(owner)
        s.add(acceptor)
        await s.flush()
        ws = Workspace(name="Team", owner_id=owner.id, type="team")
        s.add(ws)
        await s.flush()
        s.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner"))
        s.add(WorkspaceMember(workspace_id=ws.id, user_id=acceptor.id, role="member"))
        project = Project(
            workspace_id=ws.id, title="P", created_by_id=owner.id,
            status="active", visibility="public",
        )
        s.add(project)
        await s.commit()
        return ws.id, project.id, acceptor.id


def _barrier_repo(session, barrier: asyncio.Barrier) -> ProjectRepository:
    """add_member INSERT 직전에 barrier.wait() 를 끼운 repo — race window 결정적 재현."""
    repo = ProjectRepository(session)
    original_add_member = repo.add_member

    async def _add_member_with_barrier(project_id, workspace_id, user_id, role="member"):
        await barrier.wait()
        return await original_add_member(project_id, workspace_id, user_id, role)

    repo.add_member = _add_member_with_barrier  # type: ignore[method-assign]
    return repo


async def _add_task(engine, ws_id, project_id, user_id, barrier: asyncio.Barrier):
    """별개 session 으로 add_member 호출. ('ok', dict) | ('already', None)."""
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as session:
        service = ProjectService(
            repo=_barrier_repo(session, barrier),
            ws_repo=WorkspaceRepository(session),
        )
        try:
            result = await service.add_member(
                workspace_id=ws_id, project_id=project_id, user_id=user_id
            )
            return ("ok", result)
        except AlreadyExistsError:
            return ("already", None)


@pytest.mark.asyncio
async def test_concurrent_add_member_no_500_single_membership(concurrent_engine):
    """동시 2회 add_member → 1 성공 + 1 AlreadyExistsError, 500 없음, 멤버십 1개."""
    ws_id, project_id, acceptor_id = await _seed_ws_project(concurrent_engine)

    barrier = asyncio.Barrier(2)
    tasks = [
        _add_task(concurrent_engine, ws_id, project_id, acceptor_id, barrier),
        _add_task(concurrent_engine, ws_id, project_id, acceptor_id, barrier),
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for r in results:
        assert not isinstance(r, BaseException), (
            f"동시 add_member 가 unhandled 예외로 500 유발: {type(r).__name__}: {r}"
        )

    outcomes = [r[0] for r in results]
    assert outcomes.count("ok") == 1, f"정확히 1건만 성공해야: {outcomes}"
    assert outcomes.count("already") == 1, f"나머지 1건은 AlreadyExistsError 여야: {outcomes}"

    sm = async_sessionmaker(concurrent_engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as verify:
        member_count = (
            await verify.execute(
                text(
                    "SELECT COUNT(*) FROM project_members "
                    "WHERE project_id = :pid AND user_id = :uid"
                ),
                {"pid": str(project_id), "uid": str(acceptor_id)},
            )
        ).scalar_one()
    assert member_count == 1, f"동시 add 후 멤버십 row 가 정확히 1개여야: got {member_count}"
