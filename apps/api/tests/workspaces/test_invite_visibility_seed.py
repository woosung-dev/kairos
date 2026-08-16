# W-5 연결 회귀 가드 — 초대 수락 시 default_project_visibility 가 멤버로 복사되고,
# 이후 프로젝트 생성 시 visibility 미지정이면 시드가 적용되는지 검증.
import uuid

import pytest
from sqlmodel import select

from src.auth.models import User
from src.auth.repository import UserRepository
from src.projects.models import ProjectMember
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.invite_service import InviteService
from src.workspaces.models import Workspace, WorkspaceInvite, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository


async def _seed_team_ws(session, *, invite_visibility: str) -> tuple[Workspace, User, str]:
    """team ws + owner + 수락자 user + invite(code) 시드. (ws, acceptor, code) 반환."""
    owner = User(
        auth_user_id=f"ba_owner_{uuid.uuid4()}",
        display_name="owner",
        email=f"owner_{uuid.uuid4()}@seed.test",
    )
    acceptor = User(
        auth_user_id=f"ba_acceptor_{uuid.uuid4()}",
        display_name="acceptor",
        email=f"acceptor_{uuid.uuid4()}@seed.test",
    )
    session.add(owner)
    session.add(acceptor)
    await session.flush()

    ws = Workspace(name="Seed Team", owner_id=owner.id, type="team")
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner"))

    code = f"seed{uuid.uuid4().hex[:8]}"
    session.add(
        WorkspaceInvite(
            workspace_id=ws.id,
            code=code,
            role="member",
            default_project_visibility=invite_visibility,
            created_by_id=owner.id,
        )
    )
    await session.flush()
    return ws, acceptor, code


@pytest.mark.asyncio
async def test_accept_invite_copies_default_project_visibility(integration_session):
    """초대 수락 → WorkspaceMember.default_project_visibility 에 invite 값 복사 (W-5)."""
    ws, acceptor, code = await _seed_team_ws(
        integration_session, invite_visibility="draft"
    )
    service = InviteService(
        repo=WorkspaceRepository(integration_session),
        user_repo=UserRepository(integration_session),
    )

    result = await service.accept_invite(code, acceptor.id)
    assert result["role"] == "member"

    member = (
        await integration_session.exec(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.user_id == acceptor.id,
            )
        )
    ).one()
    assert member.default_project_visibility == "draft"


@pytest.mark.asyncio
async def test_create_project_applies_member_visibility_seed(integration_session):
    """visibility 미지정 프로젝트 생성 → 멤버 시드 적용 (라우터 폴백 체인과 동일 규칙)."""
    ws, acceptor, code = await _seed_team_ws(
        integration_session, invite_visibility="private"
    )
    invite_service = InviteService(
        repo=WorkspaceRepository(integration_session),
        user_repo=UserRepository(integration_session),
    )
    await invite_service.accept_invite(code, acceptor.id)
    member = (
        await integration_session.exec(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == ws.id,
                WorkspaceMember.user_id == acceptor.id,
            )
        )
    ).one()

    # 라우터의 폴백 체인: data.visibility or member.seed or "public"
    resolved = None or member.default_project_visibility or "public"
    assert resolved == "private"

    project_service = ProjectService(
        ProjectRepository(integration_session),
        ws_repo=WorkspaceRepository(integration_session),
    )
    created = await project_service.create_project(
        workspace_id=ws.id,
        title="시드 적용 프로젝트",
        created_by_id=acceptor.id,
        visibility=resolved,
    )
    assert created["visibility"] == "private"


@pytest.mark.asyncio
async def test_create_private_project_adds_creator_as_project_member(
    integration_session,
):
    """private 프로젝트 생성 시 creator 가 ProjectMember 로 자동 추가 — 락아웃 방지.

    visibility 필터(L-6)는 private 을 ProjectMember 로만 통과시키므로, 자동 추가가
    없으면 member 역할 creator 는 생성 직후 본인 프로젝트에 404 로 접근 불가.
    """
    ws, acceptor, code = await _seed_team_ws(
        integration_session, invite_visibility="private"
    )
    invite_service = InviteService(
        repo=WorkspaceRepository(integration_session),
        user_repo=UserRepository(integration_session),
    )
    await invite_service.accept_invite(code, acceptor.id)

    repo = ProjectRepository(integration_session)
    service = ProjectService(repo, ws_repo=WorkspaceRepository(integration_session))
    created = await service.create_project(
        workspace_id=ws.id,
        title="비공개 프로젝트",
        created_by_id=acceptor.id,
        visibility="private",
    )
    project_id = uuid.UUID(created["id"])

    pm = (
        await integration_session.exec(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == acceptor.id,
            )
        )
    ).one_or_none()
    assert pm is not None, "private 생성 시 creator ProjectMember 자동 추가 실패"

    # creator (member 역할) 가 본인 private 프로젝트를 조회할 수 있어야 한다
    fetched = await service.get_project(
        workspace_id=ws.id,
        project_id=project_id,
        requester_user_id=acceptor.id,
        requester_role="member",
    )
    assert fetched["id"] == created["id"]

    # 목록에서도 노출
    listed = await repo.find_by_workspace(
        ws.id, requester_user_id=acceptor.id, requester_role="member"
    )
    assert any(p.id == project_id for p in listed)


@pytest.mark.asyncio
async def test_create_public_project_does_not_add_project_member(integration_session):
    """public 생성은 ProjectMember 를 만들지 않는다 (기존 동작 보존)."""
    ws, acceptor, code = await _seed_team_ws(
        integration_session, invite_visibility="public"
    )
    invite_service = InviteService(
        repo=WorkspaceRepository(integration_session),
        user_repo=UserRepository(integration_session),
    )
    await invite_service.accept_invite(code, acceptor.id)

    service = ProjectService(
        ProjectRepository(integration_session),
        ws_repo=WorkspaceRepository(integration_session),
    )
    created = await service.create_project(
        workspace_id=ws.id,
        title="공개 프로젝트",
        created_by_id=acceptor.id,
        visibility="public",
    )
    pm_count = (
        await integration_session.exec(
            select(ProjectMember).where(
                ProjectMember.project_id == uuid.UUID(created["id"])
            )
        )
    ).all()
    assert len(pm_count) == 0
