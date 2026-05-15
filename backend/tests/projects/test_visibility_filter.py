# Sprint 17 QA — ProjectRepository._apply_visibility_filter regression
"""ADR-014 옵션 A 의 visibility 분기 (public / draft / private) 가 requester
역할 + 소유 + ProjectMember 매핑에 따라 정확히 동작하는지 검증.

본 spec 은 _apply_visibility_filter 직접 단위 테스트가 아닌 통합 시나리오
— ProjectRepository.find_by_workspace 를 통한 end-to-end visibility 분기
검증. requester 컨텍스트별 노출 set 차이로 회귀 감지.
"""
import pytest

from src.auth.models import User
from src.projects.models import Project, ProjectMember
from src.projects.repository import ProjectRepository


@pytest.mark.asyncio
async def test_owner_sees_all_visibilities(integration_session, auth_user, team_ws):
    """owner 역할 requester 는 public + draft + private 모두 조회."""
    # 다른 user (draft creator)
    other = User(
        clerk_id="other_for_owner_vis_test",
        display_name="다른 작성자",
        email="other_owner_vis@kairos.test",
    )
    integration_session.add(other)
    await integration_session.flush()

    p_public = Project(
        title="공개", workspace_id=team_ws.id, visibility="public",
        created_by_id=auth_user.id,
    )
    p_draft_others = Project(
        title="다른사람 작업중", workspace_id=team_ws.id, visibility="draft",
        created_by_id=other.id,
    )
    p_private = Project(
        title="비공개", workspace_id=team_ws.id, visibility="private",
        created_by_id=other.id,
    )
    integration_session.add_all([p_public, p_draft_others, p_private])
    await integration_session.flush()

    repo = ProjectRepository(integration_session)
    results = await repo.find_by_workspace(
        team_ws.id,
        requester_user_id=auth_user.id,
        requester_role="owner",
    )
    titles = {r.title for r in results}
    assert "공개" in titles
    assert "다른사람 작업중" in titles  # owner 는 다른 사람 draft 도 보임
    assert "비공개" in titles  # owner 는 private 도 보임


@pytest.mark.asyncio
async def test_member_hides_others_draft(integration_session, auth_user, team_ws):
    """member 역할은 본인이 만들지 않은 draft project 미노출."""
    other = User(
        clerk_id="other_draft_owner_member_test",
        display_name="다른 작성자",
        email="other_draft_member@kairos.test",
    )
    integration_session.add(other)
    await integration_session.flush()
    # auth_user 를 team_ws 의 member 로 (기본 conftest team_ws 가 owner 시드 가정)
    # 본 테스트는 requester_role="member" 명시로 분기만 확인

    p_public = Project(
        title="공개2", workspace_id=team_ws.id, visibility="public",
        created_by_id=other.id,
    )
    p_my_draft = Project(
        title="내 작업중", workspace_id=team_ws.id, visibility="draft",
        created_by_id=auth_user.id,
    )
    p_others_draft = Project(
        title="다른사람 draft", workspace_id=team_ws.id, visibility="draft",
        created_by_id=other.id,
    )
    integration_session.add_all([p_public, p_my_draft, p_others_draft])
    await integration_session.flush()

    repo = ProjectRepository(integration_session)
    results = await repo.find_by_workspace(
        team_ws.id,
        requester_user_id=auth_user.id,
        requester_role="member",
    )
    titles = {r.title for r in results}
    assert "공개2" in titles
    assert "내 작업중" in titles  # 본인 draft 는 노출
    assert "다른사람 draft" not in titles  # 다른 사람 draft 는 미노출


@pytest.mark.asyncio
async def test_member_private_only_when_mapped(integration_session, auth_user, team_ws):
    """private project 는 ProjectMember 매핑된 member 에게만 노출."""
    other = User(
        clerk_id="other_private_creator_member_test",
        display_name="다른 사람",
        email="other_private_creator@kairos.test",
    )
    integration_session.add(other)
    await integration_session.flush()

    p_private_mapped = Project(
        title="매핑된 비공개", workspace_id=team_ws.id, visibility="private",
        created_by_id=other.id,
    )
    p_private_not_mapped = Project(
        title="매핑X 비공개", workspace_id=team_ws.id, visibility="private",
        created_by_id=other.id,
    )
    integration_session.add_all([p_private_mapped, p_private_not_mapped])
    await integration_session.flush()
    # auth_user 를 p_private_mapped 의 ProjectMember 로
    integration_session.add(
        ProjectMember(
            project_id=p_private_mapped.id,
            user_id=auth_user.id,
            workspace_id=team_ws.id,
            role="member",
        )
    )
    await integration_session.flush()

    repo = ProjectRepository(integration_session)
    results = await repo.find_by_workspace(
        team_ws.id,
        requester_user_id=auth_user.id,
        requester_role="member",
    )
    titles = {r.title for r in results}
    assert "매핑된 비공개" in titles
    assert "매핑X 비공개" not in titles


@pytest.mark.asyncio
async def test_no_requester_info_public_only(integration_session, auth_user, team_ws):
    """requester_user_id 없으면 보수적으로 public 만 노출 (legacy 호환 경로)."""
    p_public = Project(
        title="공개3", workspace_id=team_ws.id, visibility="public",
        created_by_id=auth_user.id,
    )
    p_draft = Project(
        title="비공개 draft", workspace_id=team_ws.id, visibility="draft",
        created_by_id=auth_user.id,
    )
    integration_session.add_all([p_public, p_draft])
    await integration_session.flush()

    repo = ProjectRepository(integration_session)
    results = await repo.find_by_workspace(
        team_ws.id,
        requester_user_id=None,
        requester_role=None,
    )
    titles = {r.title for r in results}
    assert "공개3" in titles
    assert "비공개 draft" not in titles
