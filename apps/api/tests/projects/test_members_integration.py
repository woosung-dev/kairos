# ProjectMember 추가 API 실제 DB 통합 테스트.
import uuid

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from src.projects.exceptions import (
    CrossWorkspaceMemberError,
    ProjectNotFoundError,
    WorkspaceMismatchError,
)
from src.projects.models import Project
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.models import Workspace, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository

pytestmark = pytest.mark.integration


# ─── 헬퍼 함수 ────────────────────────────────────────────────────────────────

async def _create_user(session: AsyncSession) -> uuid.UUID:
    """FK 참조용 users 행 삽입. User 모델을 직접 사용."""
    from src.auth.models import User
    user = User(
        auth_user_id=f"ba_{uuid.uuid4().hex}",
        display_name="테스트 유저",
        email=f"test_{uuid.uuid4().hex}@example.com",
    )
    session.add(user)
    await session.flush()
    return user.id


async def _create_workspace(session: AsyncSession, owner_id: uuid.UUID) -> Workspace:
    """테스트용 워크스페이스 생성."""
    ws = Workspace(name="테스트 워크스페이스", owner_id=owner_id)
    session.add(ws)
    await session.flush()
    return ws


async def _create_project(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    created_by_id: uuid.UUID,
) -> Project:
    """테스트용 프로젝트 생성."""
    project = Project(
        title="테스트 프로젝트",
        workspace_id=workspace_id,
        visibility="public",
        created_by_id=created_by_id,
    )
    session.add(project)
    await session.flush()
    return project


async def _create_ws_member(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = "member",
) -> WorkspaceMember:
    """워크스페이스 멤버 생성."""
    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user_id,
        role=role,
    )
    session.add(member)
    await session.flush()
    return member


def _make_service(session: AsyncSession) -> ProjectService:
    return ProjectService(
        repo=ProjectRepository(session),
        ws_repo=WorkspaceRepository(session),
    )


# ─── 시나리오 ──────────────────────────────────────────────────────────────────

async def test_add_member_success(integration_session: AsyncSession):
    """시나리오 1: 정상 케이스 — 같은 워크스페이스 멤버 추가 → userId + role 반환."""
    owner_id = await _create_user(integration_session)
    user_id = await _create_user(integration_session)

    ws = await _create_workspace(integration_session, owner_id)
    await _create_ws_member(integration_session, ws.id, user_id)
    project = await _create_project(integration_session, ws.id, owner_id)

    service = _make_service(integration_session)
    result = await service.add_member(
        workspace_id=ws.id,
        project_id=project.id,
        user_id=user_id,
    )

    assert result["userId"] == str(user_id)
    assert result["role"] == "member"
    assert result["projectId"] == str(project.id)


async def test_add_member_cross_workspace_403(integration_session: AsyncSession):
    """시나리오 2: user 가 다른 워크스페이스 멤버 → CrossWorkspaceMemberError(403)."""
    owner_id = await _create_user(integration_session)
    user_b_id = await _create_user(integration_session)

    ws_a = await _create_workspace(integration_session, owner_id)
    ws_b = await _create_workspace(integration_session, owner_id)

    # user_b 는 ws_b 에만 속함 (ws_a 에는 없음)
    await _create_ws_member(integration_session, ws_b.id, user_b_id)
    project_a = await _create_project(integration_session, ws_a.id, owner_id)

    service = _make_service(integration_session)
    with pytest.raises(CrossWorkspaceMemberError):
        await service.add_member(
            workspace_id=ws_a.id,
            project_id=project_a.id,
            user_id=user_b_id,
        )


async def test_add_member_project_not_found_404(integration_session: AsyncSession):
    """시나리오 3: 존재하지 않는 project_id → ProjectNotFoundError(404)."""
    owner_id = await _create_user(integration_session)
    user_id = await _create_user(integration_session)

    ws = await _create_workspace(integration_session, owner_id)
    await _create_ws_member(integration_session, ws.id, user_id)

    service = _make_service(integration_session)
    with pytest.raises(ProjectNotFoundError):
        await service.add_member(
            workspace_id=ws.id,
            project_id=uuid.uuid4(),  # 존재하지 않음
            user_id=user_id,
        )


async def test_add_member_workspace_mismatch_404(integration_session: AsyncSession):
    """시나리오 4: ws_a 소속 user + ws_b 프로젝트 → ProjectNotFoundError(404).

    Sprint 19 PR #1 C9 (Codex F-4 lock-in): cross-tenant resource 는 정보 누설 방지를
    위해 WorkspaceMismatchError 가 아닌 ProjectNotFoundError (404) 로 통일. 둘 다
    HTTP 404 응답이지만 detail 이 다르고, '존재하지만 다른 워크스페이스' 단서를 노출하지 않음.
    """
    owner_id = await _create_user(integration_session)
    user_id = await _create_user(integration_session)

    ws_a = await _create_workspace(integration_session, owner_id)
    ws_b = await _create_workspace(integration_session, owner_id)

    await _create_ws_member(integration_session, ws_a.id, user_id)
    project_b = await _create_project(integration_session, ws_b.id, owner_id)

    service = _make_service(integration_session)
    with pytest.raises(ProjectNotFoundError):
        await service.add_member(
            workspace_id=ws_a.id,  # ws_a 로 요청
            project_id=project_b.id,  # 실제 프로젝트는 ws_b 소속
            user_id=user_id,
        )


async def test_add_member_duplicate_409(integration_session: AsyncSession):
    """시나리오 5: 동일 멤버 중복 추가 → AlreadyExistsError(409) + 세션 미오염.

    Sprint 29 R1 + F4 (2026-06-23 fullsweep): 이전엔 IntegrityError 가 service 를 통과해
    500 으로 노출됐다. 이제 service.add_member 가 is_member pre-check(순차 중복)로
    AlreadyExistsError(409) 를 던지고, 동시 race 는 repo.add_member 의 ON CONFLICT
    DO NOTHING(→ None)으로 backstop 한다. IntegrityError catch/rollback 패턴이 아니라
    pre-check + ON CONFLICT 이므로 세션 poison 없이 후속 쿼리가 정상 동작한다.
    동시 케이스 회귀는 test_add_member_concurrent.py 가 별도 가드.
    """
    from src.common.exceptions import AlreadyExistsError

    owner_id = await _create_user(integration_session)
    user_id = await _create_user(integration_session)

    ws = await _create_workspace(integration_session, owner_id)
    await _create_ws_member(integration_session, ws.id, user_id)
    project = await _create_project(integration_session, ws.id, owner_id)

    service = _make_service(integration_session)

    # 1차 추가 — 정상
    first = await service.add_member(
        workspace_id=ws.id, project_id=project.id, user_id=user_id
    )
    assert first["userId"] == str(user_id)

    # 2차 추가 — 동일 (project_id, user_id) → 409 (500 아님)
    with pytest.raises(AlreadyExistsError) as exc:
        await service.add_member(
            workspace_id=ws.id, project_id=project.id, user_id=user_id
        )
    assert exc.value.status_code == 409

    # rollback 으로 세션이 살아있어야 함 (poison 아님) — 후속 쿼리 정상
    members = await service.list_members(ws.id, project.id)
    assert len(members) == 1


async def test_get_project_workspace_mismatch_404(integration_session: AsyncSession):
    """시나리오 6: ws_a 요청 + ws_b 프로젝트 → get_project → ProjectNotFoundError(404).

    Sprint 19 PR #1 C9 (Codex F-4 lock-in): get_project 도 cross-tenant 정보 누설
    방지를 위해 ProjectNotFoundError (404) 로 통일. find_by_id(project_id, workspace_id)
    가 사전 차단하므로 visibility 검증 진입 전에 404.
    """
    owner_id = await _create_user(integration_session)

    ws_a = await _create_workspace(integration_session, owner_id)
    ws_b = await _create_workspace(integration_session, owner_id)
    project_b = await _create_project(integration_session, ws_b.id, owner_id)

    service = _make_service(integration_session)
    with pytest.raises(ProjectNotFoundError):
        await service.get_project(
            workspace_id=ws_a.id,  # ws_a 로 요청
            project_id=project_b.id,  # ws_b 소속 프로젝트
        )
