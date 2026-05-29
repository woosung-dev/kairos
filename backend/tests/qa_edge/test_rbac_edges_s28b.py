# Sprint 28 QA sweep — RBAC + 동시성 엣지 6건 경험적(empirical) 증거 테스트.
"""QA 보고서용 deterministic 증거. 로컬 TestContainers PostgreSQL 전용 (프로덕션 Neon 아님).

각 테스트는 "바람직한 동작"이 아니라 **실제 동작을 문서화**한다. 알려진 gap 은
ACTUAL 동작을 assert 하고 주석에 gap 임을 명시한다.

대상 6건:
  1. Member cache invalidation (BUG-RBAC-CACHE-STALE 회귀 가드) — update_member_role / remove_member
  2. Invite max_uses 소진 → 410 (InviteExpiredError)
  3. Invite expiry → 410 (InviteExpiredError)
  4. I-17 cross-workspace ProjectMember add → 403 (CrossWorkspaceMemberError)
  5. workspace_members UNIQUE (BUG-WS-MEMBER-UNIQUE FIX 회귀가드) — 제약 존재 + 중복 차단
  6. last-owner / last-admin 가드 — owner 보호 동작 / admin 가드 부재 문서화
"""
import asyncio
import uuid
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth import rbac as auth_rbac
from src.auth.models import User
from src.auth.repository import UserRepository
from src.projects.exceptions import CrossWorkspaceMemberError
from src.projects.models import Project, ProjectMember
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.exceptions import (
    CannotModifyOwnerError,
    InviteExpiredError,
)
from src.workspaces.invite_service import InviteService
from src.workspaces.models import Workspace, WorkspaceInvite, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository

pytestmark = pytest.mark.integration


# ─── 공통 헬퍼 ──────────────────────────────────────────────────────────────


async def _make_user(session: AsyncSession, name: str = "유저") -> User:
    user = User(
        clerk_id=f"clerk_{uuid.uuid4().hex}",
        display_name=name,
        email=f"{uuid.uuid4().hex}@kairos.test",
    )
    session.add(user)
    await session.flush()
    return user


async def _make_team_ws(session: AsyncSession, owner_id: uuid.UUID) -> Workspace:
    ws = Workspace(name="QA 팀", owner_id=owner_id, type="team")
    session.add(ws)
    await session.flush()
    return ws


async def _add_member(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = "member",
) -> WorkspaceMember:
    m = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
    session.add(m)
    await session.flush()
    return m


def _invite_service(session: AsyncSession) -> InviteService:
    return InviteService(
        repo=WorkspaceRepository(session),
        user_repo=UserRepository(session),
    )


def _project_service(session: AsyncSession) -> ProjectService:
    return ProjectService(
        repo=ProjectRepository(session),
        ws_repo=WorkspaceRepository(session),
    )


# ─── 1. Member cache invalidation (BUG-RBAC-CACHE-STALE 회귀 가드) ──────────


@pytest.fixture(autouse=True)
def _clear_member_cache():
    """각 테스트 전후로 in-process member cache 비움 (cross-test 오염 방지)."""
    auth_rbac._MEMBER_CACHE.clear()
    yield
    auth_rbac._MEMBER_CACHE.clear()


async def test_update_member_role_invalidates_member_cache(
    integration_session: AsyncSession,
):
    """warm cache → update_member_role → 해당 (ws, user) cache 엔트리 즉시 제거.

    EVIDENCE: invite_service.update_member_role() 가 invalidate_member_cache()
    를 호출(invite_service.py:245-247) 하므로 60s TTL 을 기다리지 않고 즉시 None.
    """
    owner = await _make_user(integration_session, "오너")
    target = await _make_user(integration_session, "대상")
    ws = await _make_team_ws(integration_session, owner.id)
    await _add_member(integration_session, ws.id, owner.id, "owner")
    member = await _add_member(integration_session, ws.id, target.id, "member")
    await integration_session.commit()

    # cache warm-up — RoleChecker 가 채우는 것과 동일
    auth_rbac._member_cache_set(ws.id, target.id, member)
    assert auth_rbac._member_cache_get(ws.id, target.id) is member

    service = _invite_service(integration_session)
    await service.update_member_role(ws.id, member.id, "admin")

    # 즉시 invalidate — getter 가 None 이어야 함 (stale 60s 미발생)
    assert auth_rbac._member_cache_get(ws.id, target.id) is None


async def test_remove_member_invalidates_member_cache(
    integration_session: AsyncSession,
):
    """warm cache → remove_member → 해당 (ws, user) cache 엔트리 즉시 제거.

    EVIDENCE: invite_service.remove_member() 가 invalidate_member_cache()
    를 호출(invite_service.py:271-274).
    """
    owner = await _make_user(integration_session, "오너")
    target = await _make_user(integration_session, "대상")
    ws = await _make_team_ws(integration_session, owner.id)
    await _add_member(integration_session, ws.id, owner.id, "owner")
    member = await _add_member(integration_session, ws.id, target.id, "member")
    await integration_session.commit()

    auth_rbac._member_cache_set(ws.id, target.id, member)
    assert auth_rbac._member_cache_get(ws.id, target.id) is member

    service = _invite_service(integration_session)
    await service.remove_member(ws.id, member.id)

    assert auth_rbac._member_cache_get(ws.id, target.id) is None


# ─── 2. Invite max_uses 소진 → InviteExpiredError (HTTP 410) ────────────────


async def test_invite_max_uses_exhaustion_raises_expired(
    integration_session: AsyncSession,
):
    """max_uses=1 invite — 첫 accept 성공, 두 번째 accept(다른 user) → InviteExpiredError.

    EMPIRICAL FINDING: max_uses=1 의 첫 accept 직후 accept_invite 가
    use_count+1 >= max_uses 조건으로 invite 를 즉시 deactivate(invite_service.py:195-196)
    한다. 따라서 두 번째 accept 는 _validate_invite 의 use_count>=max_uses 분기가 아니라
    is_active=False 분기를 **먼저** 타서 reason = "비활성화된 초대 링크입니다" 가 된다.
    어느 경로든 InviteExpiredError → invite_router.py:95-96 에서 HTTP 410 매핑은 동일.
    (use_count>=max_uses 분기는 max_uses>=2 이고 비활성화 전 동시 도달 시에만 직접 관측됨.)
    """
    inviter = await _make_user(integration_session, "초대자")
    ws = await _make_team_ws(integration_session, inviter.id)
    await _add_member(integration_session, ws.id, inviter.id, "owner")

    user_a = await _make_user(integration_session, "수락자A")
    user_b = await _make_user(integration_session, "수락자B")
    await integration_session.commit()

    service = _invite_service(integration_session)
    created = await service.create_invite(
        workspace_id=ws.id,
        created_by_id=inviter.id,
        role="member",
        max_uses=1,
    )
    code = created["code"]

    # 첫 accept — 성공
    result = await service.accept_invite(code, user_a.id)
    assert result["role"] == "member"

    # 두 번째 accept (다른 user) — 소진(자동 비활성화)됨 → InviteExpiredError
    with pytest.raises(InviteExpiredError) as exc_info:
        await service.accept_invite(code, user_b.id)
    # 첫 accept 가 invite 를 즉시 비활성화하므로 is_active=False 분기가 먼저 발동
    assert exc_info.value.reason == "비활성화된 초대 링크입니다"


async def test_invite_max_uses_router_maps_to_410(
    integration_session: AsyncSession,
):
    """HTTP 레벨 확인 — 소진된 invite accept → 410 (라우터 exception 매핑 실증).

    EVIDENCE: get_current_user + get_invite_service override 로 public accept
    엔드포인트 직접 호출. InviteExpiredError → HTTPException(410).
    """
    from httpx import ASGITransport, AsyncClient

    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session
    from src.main import app
    from src.workspaces.dependencies import get_invite_service

    inviter = await _make_user(integration_session, "초대자")
    ws = await _make_team_ws(integration_session, inviter.id)
    await _add_member(integration_session, ws.id, inviter.id, "owner")
    user_a = await _make_user(integration_session, "수락자A")
    user_b = await _make_user(integration_session, "수락자B")
    await integration_session.commit()

    service = _invite_service(integration_session)
    created = await service.create_invite(
        workspace_id=ws.id, created_by_id=inviter.id, role="member", max_uses=1
    )
    code = created["code"]
    await service.accept_invite(code, user_a.id)

    # user_b 로 두 번째 accept — 라우터 경유 → 410
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_current_user] = lambda: user_b
    app.dependency_overrides[get_invite_service] = lambda: _invite_service(
        integration_session
    )
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            res = await c.post(f"/api/v1/invites/{code}/accept")
    finally:
        app.dependency_overrides.clear()

    # 소진된 invite accept → HTTP 410 (InviteExpiredError 매핑).
    # detail 은 자동 비활성화 경로라 "비활성화된 초대 링크입니다" (위 테스트 주석 참조).
    assert res.status_code == 410, f"expected 410, got {res.status_code}: {res.text}"
    assert res.json()["detail"] == "비활성화된 초대 링크입니다"


# ─── 3. Invite expiry → InviteExpiredError (HTTP 410) ───────────────────────


async def test_invite_expiry_raises_expired(integration_session: AsyncSession):
    """invite 생성 후 expires_at 을 과거로 DB 직접 조작 → accept 시 InviteExpiredError.

    API 는 expiresInDays 1..30 만 허용하므로 만료 케이스는 DB 직접 조작으로 재현.
    EVIDENCE: _validate_invite 의 datetime.utcnow() > expires_at 분기.
    reason = "만료된 초대 링크입니다". 라우터에서 410 매핑.
    """
    inviter = await _make_user(integration_session, "초대자")
    ws = await _make_team_ws(integration_session, inviter.id)
    await _add_member(integration_session, ws.id, inviter.id, "owner")
    acceptor = await _make_user(integration_session, "수락자")
    await integration_session.commit()

    service = _invite_service(integration_session)
    created = await service.create_invite(
        workspace_id=ws.id, created_by_id=inviter.id, role="member"
    )
    code = created["code"]

    # expires_at 을 과거로 강제 (API 우회)
    past = datetime.utcnow() - timedelta(days=1)
    await integration_session.exec(
        text("UPDATE workspace_invites SET expires_at = :past WHERE code = :code"),
        params={"past": past, "code": code},
    )
    await integration_session.commit()

    with pytest.raises(InviteExpiredError) as exc_info:
        await service.accept_invite(code, acceptor.id)
    assert exc_info.value.reason == "만료된 초대 링크입니다"


# ─── 4. I-17 cross-workspace ProjectMember add → 403 ────────────────────────


async def test_cross_workspace_project_member_add_403(
    integration_session: AsyncSession,
):
    """W1 의 프로젝트에 W1 비멤버 user 추가 → CrossWorkspaceMemberError (403).

    EVIDENCE: ProjectService.add_member 가 ws_repo.find_member(W1, U) is None
    이면 CrossWorkspaceMemberError 발생 (projects/service.py:197-199).
    HTTP 403, detail = "해당 사용자가 워크스페이스 멤버가 아닙니다".
    """
    owner = await _make_user(integration_session, "오너")
    outsider = await _make_user(integration_session, "외부인")  # W1 비멤버
    ws1 = await _make_team_ws(integration_session, owner.id)
    await _add_member(integration_session, ws1.id, owner.id, "owner")

    project = Project(
        title="W1 프로젝트",
        workspace_id=ws1.id,
        visibility="public",
        created_by_id=owner.id,
    )
    integration_session.add(project)
    await integration_session.flush()
    await integration_session.commit()

    service = _project_service(integration_session)
    with pytest.raises(CrossWorkspaceMemberError) as exc_info:
        await service.add_member(
            workspace_id=ws1.id,
            project_id=project.id,
            user_id=outsider.id,
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "해당 사용자가 워크스페이스 멤버가 아닙니다"


# ─── 5. workspace_members UNIQUE gap (BUG-WS-MEMBER-UNIQUE) ──────────────────


async def test_workspace_members_has_unique_constraint(
    integration_session: AsyncSession,
):
    """회귀 가드 (BUG-WS-MEMBER-UNIQUE FIX) — UNIQUE 제약 존재 + 중복 INSERT 차단.

    2차 정검 P1 fix: 모델 __table_args__ + alembic c7e9f1a2b3d4 로
    (workspace_id, user_id) UNIQUE 제약 추가. 이전엔 제약 부재로 멀티워커 race 시
    중복 row 가 물리적으로 가능했으나, 이제 DB 레벨에서 차단된다.
    """
    def _collect(sync_conn):
        insp = inspect(sync_conn)
        return {
            "unique_constraints": insp.get_unique_constraints("workspace_members"),
            "pk": insp.get_pk_constraint("workspace_members"),
        }

    conn = await integration_session.connection()
    info = await conn.run_sync(_collect)

    # UNIQUE 제약: workspace_id+user_id 조합이 존재해야 함 (FIX)
    unique_cols = [set(uc["column_names"]) for uc in info["unique_constraints"]]
    assert {"workspace_id", "user_id"} in unique_cols, (
        f"UNIQUE 제약 부재 — FIX 회귀: {info['unique_constraints']}"
    )
    # PK 는 id 단일 (변경 없음)
    assert info["pk"]["constrained_columns"] == ["id"]
    # 동일 (workspace_id, user_id) 중복 INSERT → IntegrityError 로 차단되어야 함
    owner = await _make_user(integration_session, "오너")
    ws = await _make_team_ws(integration_session, owner.id)
    dup_user = await _make_user(integration_session, "중복")
    integration_session.add(
        WorkspaceMember(workspace_id=ws.id, user_id=dup_user.id, role="member")
    )
    integration_session.add(
        WorkspaceMember(workspace_id=ws.id, user_id=dup_user.id, role="member")
    )
    with pytest.raises(IntegrityError):
        await integration_session.flush()
    await integration_session.rollback()


# 동시성 race 용 별개 engine — test_personal_workspace_race_concurrent.py 패턴 복제
@pytest_asyncio.fixture
async def concurrent_engine(postgres_container):
    """별개 connection 동시 사용을 위한 engine (function-scoped)."""
    url = postgres_container.get_connection_url().replace("psycopg2", "asyncpg")
    engine = create_async_engine(url, echo=False, pool_size=10, max_overflow=5)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


async def _accept_invite_task(
    engine, code: str, user_id: uuid.UUID, barrier: asyncio.Barrier
) -> str:
    """별개 session 으로 accept_invite — N개 task 가 barrier 로 동시 정렬 후 실행."""
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sm() as session:
        service = InviteService(
            repo=WorkspaceRepository(session),
            user_repo=UserRepository(session),
        )
        await barrier.wait()
        try:
            await service.accept_invite(code, user_id)
            return "ok"
        except Exception as e:  # noqa: BLE001 — race 결과 분류 목적
            return type(e).__name__


async def test_concurrent_same_user_accept_duplicate_members(
    concurrent_engine,
):
    """동일 새 user 가 같은 워크스페이스로 N개 동시 accept → 중복 멤버 row 가능 여부 실측.

    DOCUMENTED GAP (BUG-WS-MEMBER-UNIQUE): app-level find_member 가드는 별개
    트랜잭션 동시 실행 시 서로의 미커밋 INSERT 를 보지 못하므로(READ COMMITTED),
    UNIQUE 제약 부재와 결합해 중복 row 가 생성될 수 있다. 본 테스트는 실제 결과
    (생성된 멤버 row 수)를 문서화한다. 1보다 크면 gap 이 실증된 것.
    """
    sm = async_sessionmaker(
        concurrent_engine, class_=AsyncSession, expire_on_commit=False
    )
    # seed: inviter + owner member + team ws + max_uses 없는 invite + 새 user
    async with sm() as setup:
        inviter = User(
            clerk_id=f"clerk_{uuid.uuid4().hex}",
            display_name="초대자",
            email=f"{uuid.uuid4().hex}@kairos.test",
        )
        setup.add(inviter)
        await setup.flush()
        ws = Workspace(name="QA 팀", owner_id=inviter.id, type="team")
        setup.add(ws)
        await setup.flush()
        setup.add(
            WorkspaceMember(workspace_id=ws.id, user_id=inviter.id, role="owner")
        )
        new_user = User(
            clerk_id=f"clerk_{uuid.uuid4().hex}",
            display_name="신규",
            email=f"{uuid.uuid4().hex}@kairos.test",
        )
        setup.add(new_user)
        await setup.flush()
        code = "qaracecode01"
        setup.add(
            WorkspaceInvite(
                workspace_id=ws.id,
                code=code,
                role="member",
                created_by_id=inviter.id,
                max_uses=None,
                expires_at=None,
                is_active=True,
            )
        )
        await setup.commit()
        ws_id = ws.id
        new_user_id = new_user.id

    n_concurrent = 5
    barrier = asyncio.Barrier(n_concurrent)
    results = await asyncio.gather(
        *[
            _accept_invite_task(concurrent_engine, code, new_user_id, barrier)
            for _ in range(n_concurrent)
        ]
    )

    async with sm() as verify:
        member_count = (
            await verify.exec(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == ws_id,
                    WorkspaceMember.user_id == new_user_id,
                )
            )
        ).all()
    actual = len(member_count)

    # EMPIRICAL FINDING (deterministic, 3회 반복 동일): asyncio 단일 event loop 에선
    # task 들이 await 지점에서 직렬화되어 첫 task 의 commit 이 나머지의 find_member
    # 보다 먼저 도달 → 나머지 4개는 MemberAlreadyExistsError, 최종 rows=1.
    # 즉 단일 event loop asyncio race 로는 중복이 재현되지 않는다(guard 가 사실상 막음).
    # 단, 이는 DB UNIQUE 제약 때문이 아니라 asyncio 직렬화 덕분이다 — 별개 OS 스레드/
    # 프로세스(실제 멀티 워커)에서 SELECT/INSERT 가 진짜로 인터리브되면 막지 못한다.
    # 그 인터리브 가능성은 test_guard_bypassed_when_select_interleaves 가 결정적으로 실증.
    assert actual >= 1, f"최소 1 멤버는 생성되어야 함. results={results}, rows={actual}"
    print(
        f"[BUG-WS-MEMBER-UNIQUE] N={n_concurrent} 동시 accept(asyncio) → "
        f"member rows={actual}, task results={results}"
    )


async def test_interleave_dup_blocked_by_unique_constraint(concurrent_engine):
    """회귀 가드 (BUG-WS-MEMBER-UNIQUE FIX) — 멀티워커 인터리브 중복을 DB UNIQUE 가 차단.

    별개 트랜잭션 2개의 find_member 가 둘 다 None 을 본 뒤(app-level 가드 우회) 각각
    INSERT 를 시도해도, (workspace_id, user_id) UNIQUE 제약이 두 번째 commit 을
    IntegrityError 로 차단한다. 이전엔 제약 부재로 2 row 가 생겼던 멀티워커 race 가
    이제 1 row 로 보장된다.
    """
    sm = async_sessionmaker(
        concurrent_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with sm() as setup:
        owner = User(
            clerk_id=f"clerk_{uuid.uuid4().hex}",
            display_name="오너",
            email=f"{uuid.uuid4().hex}@kairos.test",
        )
        setup.add(owner)
        await setup.flush()
        ws = Workspace(name="QA 팀", owner_id=owner.id, type="team")
        setup.add(ws)
        await setup.flush()
        target = User(
            clerk_id=f"clerk_{uuid.uuid4().hex}",
            display_name="대상",
            email=f"{uuid.uuid4().hex}@kairos.test",
        )
        setup.add(target)
        await setup.flush()
        await setup.commit()
        ws_id, target_id = ws.id, target.id

    # 두 별개 세션(=별개 트랜잭션) — 멀티워커 인터리브 모사
    async with sm() as s1, sm() as s2:
        repo1 = WorkspaceRepository(s1)
        repo2 = WorkspaceRepository(s2)
        # 두 트랜잭션 모두 INSERT 이전에 find_member 수행 → 둘 다 None
        assert await repo1.find_member(ws_id, target_id) is None
        assert await repo2.find_member(ws_id, target_id) is None
        # 이제 각자 add_member + commit — 두 번째 commit 이 UNIQUE 로 차단되어야 함(FIX)
        await repo1.add_member(
            WorkspaceMember(workspace_id=ws_id, user_id=target_id, role="member")
        )
        await s1.commit()
        # repo2.add_member 가 flush 하는 시점에 UNIQUE 위반 → IntegrityError
        # (s1 의 row 가 이미 commit 되어 visible). 멀티워커 인터리브 중복 차단.
        with pytest.raises(IntegrityError):
            await repo2.add_member(
                WorkspaceMember(workspace_id=ws_id, user_id=target_id, role="member")
            )
        await s2.rollback()

    async with sm() as verify:
        rows = (
            await verify.exec(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == ws_id,
                    WorkspaceMember.user_id == target_id,
                )
            )
        ).all()
    assert len(rows) == 1, (
        f"UNIQUE 제약으로 인터리브 중복이 차단되어 1 row 여야 함 (실측 {len(rows)})"
    )


# ─── 6. last-owner / last-admin 가드 ────────────────────────────────────────


async def test_cannot_demote_sole_owner(integration_session: AsyncSession):
    """단독 owner 의 역할 변경 시도 → CannotModifyOwnerError (403).

    EVIDENCE: update_member_role 가 member.role == 'owner' 이면
    CannotModifyOwnerError(invite_service.py:237-238). member_router.py:43-44 에서 403.
    """
    owner = await _make_user(integration_session, "유일오너")
    ws = await _make_team_ws(integration_session, owner.id)
    owner_member = await _add_member(integration_session, ws.id, owner.id, "owner")
    await integration_session.commit()

    service = _invite_service(integration_session)
    with pytest.raises(CannotModifyOwnerError):
        await service.update_member_role(ws.id, owner_member.id, "admin")


async def test_cannot_remove_sole_owner(integration_session: AsyncSession):
    """단독 owner 제거 시도 → CannotModifyOwnerError (403).

    EVIDENCE: remove_member 가 member.role == 'owner' 이면
    CannotModifyOwnerError(invite_service.py:265-266). member_router.py:59-60 에서 403.
    """
    owner = await _make_user(integration_session, "유일오너")
    ws = await _make_team_ws(integration_session, owner.id)
    owner_member = await _add_member(integration_session, ws.id, owner.id, "owner")
    await integration_session.commit()

    service = _invite_service(integration_session)
    with pytest.raises(CannotModifyOwnerError):
        await service.remove_member(ws.id, owner_member.id)


async def test_sole_admin_demote_and_remove_allowed_no_last_admin_guard(
    integration_session: AsyncSession,
):
    """단독 admin(owner 존재 하)의 강등/제거 → 허용됨 (last-admin 가드 부재 문서화).

    DOCUMENTED BEHAVIOR (codex 판정): owner 가 존재하는 한 admin-count=0 상태는
    허용 가능한 상태이지 버그가 아니다. update_member_role / remove_member 는
    member.role == 'owner' 만 차단하며 admin 수를 검사하지 않는다.
    """
    owner = await _make_user(integration_session, "오너")
    admin_user = await _make_user(integration_session, "단독어드민")
    ws = await _make_team_ws(integration_session, owner.id)
    await _add_member(integration_session, ws.id, owner.id, "owner")
    admin_member = await _add_member(
        integration_session, ws.id, admin_user.id, "admin"
    )
    await integration_session.commit()

    service = _invite_service(integration_session)

    # (a) 단독 admin 강등 → 예외 없이 허용 (admin → member)
    result = await service.update_member_role(ws.id, admin_member.id, "member")
    assert result["role"] == "member"

    # 다시 admin 으로 올린 뒤 (b) 제거 → 예외 없이 허용
    await service.update_member_role(ws.id, admin_member.id, "admin")
    await service.remove_member(ws.id, admin_member.id)  # 예외 없이 완료

    remaining = (
        await integration_session.exec(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.user_id == admin_user.id,
            )
        )
    ).all()
    assert remaining == [], "단독 admin 제거가 허용되어야 함 (last-admin 가드 없음)"

    # owner 는 여전히 존재 — admin-count=0 + owner=1 = 허용 상태
    admins = (
        await integration_session.exec(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.role == "admin",
            )
        )
    ).all()
    owners = (
        await integration_session.exec(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.role == "owner",
            )
        )
    ).all()
    assert len(admins) == 0 and len(owners) == 1
