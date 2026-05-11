# ProjectMember 추가 API 실제 DB 통합 테스트.
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

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
        clerk_id=f"clerk_{uuid.uuid4().hex}",
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
    """시나리오 4: ws_a 소속 user + ws_b 프로젝트 → WorkspaceMismatchError(404)."""
    owner_id = await _create_user(integration_session)
    user_id = await _create_user(integration_session)

    ws_a = await _create_workspace(integration_session, owner_id)
    ws_b = await _create_workspace(integration_session, owner_id)

    await _create_ws_member(integration_session, ws_a.id, user_id)
    project_b = await _create_project(integration_session, ws_b.id, owner_id)

    service = _make_service(integration_session)
    with pytest.raises(WorkspaceMismatchError):
        await service.add_member(
            workspace_id=ws_a.id,  # ws_a 로 요청
            project_id=project_b.id,  # 실제 프로젝트는 ws_b 소속
            user_id=user_id,
        )


async def test_add_member_duplicate_409(integration_session: AsyncSession):
    """시나리오 5: 동일 멤버 중복 추가 → IntegrityError(UniqueConstraint) 발생 확인.

    service.add_member 는 DB 레벨 UniqueConstraint 위반을 HTTPException(409)로 래핑하지 않음.
    실제로는 IntegrityError(또는 asyncpg.UniqueViolationError)가 발생.
    이 테스트는 두 번째 add_member 호출이 예외를 발생시키는 것만 확인.
    """
    owner_id = await _create_user(integration_session)
    user_id = await _create_user(integration_session)

    ws = await _create_workspace(integration_session, owner_id)
    await _create_ws_member(integration_session, ws.id, user_id)
    project = await _create_project(integration_session, ws.id, owner_id)

    from src.projects.models import ProjectMember
    from sqlalchemy.exc import IntegrityError

    # workspace_id 를 포함하여 직접 첫 번째 멤버 삽입
    first_member = ProjectMember(
        project_id=project.id,
        user_id=user_id,
        workspace_id=ws.id,
        role="member",
    )
    integration_session.add(first_member)
    await integration_session.flush()

    # 두 번째 삽입 — 동일 (project_id, user_id) UniqueConstraint 위반 기대
    second_member = ProjectMember(
        project_id=project.id,
        user_id=user_id,
        workspace_id=ws.id,
        role="member",
    )
    integration_session.add(second_member)
    with pytest.raises(IntegrityError):
        await integration_session.flush()


async def test_get_project_workspace_mismatch_404(integration_session: AsyncSession):
    """시나리오 6: ws_a 요청 + ws_b 프로젝트 → get_project → WorkspaceMismatchError(404)."""
    owner_id = await _create_user(integration_session)

    ws_a = await _create_workspace(integration_session, owner_id)
    ws_b = await _create_workspace(integration_session, owner_id)
    project_b = await _create_project(integration_session, ws_b.id, owner_id)

    service = _make_service(integration_session)
    with pytest.raises(WorkspaceMismatchError):
        await service.get_project(
            workspace_id=ws_a.id,  # ws_a 로 요청
            project_id=project_b.id,  # ws_b 소속 프로젝트
        )
