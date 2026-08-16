# Sprint 15 R5 — Personal workspace 내 ProjectMember 추가 차단 invariant
"""Personal workspace는 항상 1명 — Project 생성 후 다른 user 멤버 추가 시 PersonalWorkspaceProtected(403)."""
import pytest

from src.auth.models import User
from src.projects.models import Project
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.exceptions import PersonalWorkspaceProtected
from src.workspaces.repository import WorkspaceRepository


@pytest.mark.asyncio
async def test_add_project_member_to_personal_ws_blocked(
    integration_session, auth_user, personal_ws
):
    """Personal workspace 내 project에 다른 user 멤버 추가 시도 → 403 PersonalWorkspaceProtected."""
    # Personal workspace 내 project 생성 (owner 본인)
    p = Project(
        title="개인 프로젝트",
        workspace_id=personal_ws.id,
        created_by_id=auth_user.id,
    )
    integration_session.add(p)
    await integration_session.flush()

    # 다른 user 생성
    other = User(
        auth_user_id="other_user_for_invariant_test",
        display_name="다른 사용자",
        email="other_invariant@kairos.test",
    )
    integration_session.add(other)
    await integration_session.flush()

    repo = ProjectRepository(integration_session)
    ws_repo = WorkspaceRepository(integration_session)
    service = ProjectService(repo, ws_repo=ws_repo)
    with pytest.raises(PersonalWorkspaceProtected):
        await service.add_member(
            workspace_id=personal_ws.id,
            project_id=p.id,
            user_id=other.id,
            role="member",
        )


@pytest.mark.asyncio
async def test_add_project_member_to_team_ws_allowed(
    integration_session, auth_user, team_ws
):
    """Team workspace 내 project에는 멤버 추가 정상 (단, 같은 ws 멤버일 때만)."""
    from src.workspaces.models import WorkspaceMember

    p = Project(
        title="팀 프로젝트",
        workspace_id=team_ws.id,
        created_by_id=auth_user.id,
    )
    integration_session.add(p)
    await integration_session.flush()

    # 다른 user + team_ws 멤버로 추가
    other = User(
        auth_user_id="other_team_member_for_invariant_test",
        display_name="팀원",
        email="other_team@kairos.test",
    )
    integration_session.add(other)
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(workspace_id=team_ws.id, user_id=other.id, role="member")
    )
    await integration_session.flush()

    repo = ProjectRepository(integration_session)
    ws_repo = WorkspaceRepository(integration_session)
    service = ProjectService(repo, ws_repo=ws_repo)
    result = await service.add_member(
        workspace_id=team_ws.id,
        project_id=p.id,
        user_id=other.id,
        role="member",
    )
    assert result["userId"] == str(other.id)
    assert result["role"] == "member"
