# CAND-B 보강 회귀 — codex P1(사전 잔재)/P2(list 상관관계) 미완결 결함 차단
"""CAND-B 후속 (codex REVISE): 1차 fix 가 닫지 못한 두 잔여 경로 회귀.

codex 가 지적한 두 미완결 결함을 실 seam 으로 재현한다 (mock 없음).

[P2] find_by_workspace LIST visibility 상관관계 결함
  1차 fix 의 ORM 중첩 exists() 는 서브쿼리 안에서 Project.workspace_id 를
  참조할 때 SQLAlchemy 가 FROM 절에 *새 projects 테이블*을 생성해 외부 행과
  상관(correlate)되지 않는다. 결과적으로 "요청자가 (어떤 프로젝트든 있는)
  아무 워크스페이스의 멤버이기만 하면" 가드가 참이 되어, orphan ProjectMember
  잔재가 있으면 LIST 에서 private project 가 노출된다.

[P1] accept_invite 사전 잔재 미정리
  1차 fix 의 정리는 이번 변경 이후의 remove 에만 동작한다. 과거 제거로 남은
  orphan ProjectMember 행은 살아남고, re-invite(accept_invite) 가 WorkspaceMember
  를 재생성하면 ws-membership 가드가 다시 참이 되어 stale private 접근이 복원된다.

두 케이스 모두 InviteService.accept_invite / ProjectService.get_project /
ProjectRepository.find_by_workspace 의 실 seam 을 그대로 탄다.
"""
import uuid

import pytest

from src.auth.models import User
from src.auth.repository import UserRepository
from src.projects.exceptions import ProjectNotFoundError
from src.projects.models import Project, ProjectMember
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.invite_service import InviteService
from src.workspaces.models import Workspace, WorkspaceInvite, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository

pytestmark = pytest.mark.integration


async def _create_user(session, tag: str) -> User:
    user = User(
        clerk_id=f"clerk_{tag}_{uuid.uuid4().hex}",
        display_name=tag,
        email=f"{tag}_{uuid.uuid4().hex}@example.com",
    )
    session.add(user)
    await session.flush()
    return user


def _make_invite_service(session) -> InviteService:
    return InviteService(
        repo=WorkspaceRepository(session),
        user_repo=UserRepository(session),
    )


def _make_project_service(session) -> ProjectService:
    return ProjectService(
        repo=ProjectRepository(session),
        ws_repo=WorkspaceRepository(session),
    )


async def test_list_visibility_does_not_leak_private_via_orphan_member(
    integration_session,
):
    """[codex P2] find_by_workspace 가 orphan ProjectMember 로 private 을 노출하면 안 됨.

    재현 핵심: 요청자가 *다른* 워크스페이스(프로젝트가 있는)의 멤버이면서,
    target 워크스페이스의 private project 에 대해 orphan ProjectMember 잔재만 가진
    경우. 상관관계 결함이 있으면 LIST 가드가 참이 되어 private 이 목록에 샌다.
    """
    session = integration_session

    owner = await _create_user(session, "p2owner")
    intruder = await _create_user(session, "p2intruder")

    # target 워크스페이스 — intruder 는 멤버가 아님 (제거됨 가정).
    target_ws = Workspace(name="타깃 워크스페이스", owner_id=owner.id, type="team")
    session.add(target_ws)
    await session.flush()
    session.add(
        WorkspaceMember(workspace_id=target_ws.id, user_id=owner.id, role="owner")
    )

    target_private = Project(
        title="타깃 비공개",
        workspace_id=target_ws.id,
        visibility="private",
        created_by_id=owner.id,
    )
    session.add(target_private)
    await session.flush()

    # orphan ProjectMember 잔재 — intruder 가 과거에 매핑됐던 행 (정리 안 됨).
    session.add(
        ProjectMember(
            project_id=target_private.id,
            workspace_id=target_ws.id,
            user_id=intruder.id,
            role="member",
        )
    )

    # intruder 는 *다른* 워크스페이스의 정상 멤버이고 그 ws 엔 프로젝트가 존재.
    other_ws = Workspace(name="인트루더 본거지", owner_id=intruder.id, type="team")
    session.add(other_ws)
    await session.flush()
    session.add(
        WorkspaceMember(workspace_id=other_ws.id, user_id=intruder.id, role="owner")
    )
    session.add(
        Project(
            title="인트루더 프로젝트",
            workspace_id=other_ws.id,
            visibility="public",
            created_by_id=intruder.id,
        )
    )
    await session.commit()

    repo = ProjectRepository(session)
    listed = await repo.find_by_workspace(
        workspace_id=target_ws.id,
        requester_user_id=intruder.id,
        requester_role="member",
    )
    leaked = [p for p in listed if p.id == target_private.id]
    assert not leaked, (
        "비-멤버 intruder 가 orphan ProjectMember + 타 워크스페이스 멤버십으로 "
        "private project 를 LIST 에서 되찾음 (codex P2 상관관계 결함)"
    )


async def test_reinvite_purges_preexisting_orphan_project_member(
    integration_session,
):
    """[codex P1] accept_invite 가 사전 orphan ProjectMember 를 정리해야 함.

    재현 핵심: remove_member 정리 경로를 거치지 않고 *직접* 남아 있는 orphan
    ProjectMember(과거 제거 잔재)를 둔 뒤 re-invite(accept_invite) 한다.
    accept 시점 정리가 없으면 WorkspaceMember 재생성으로 ws-membership 가드가
    참이 되어 stale private 접근(GET 200)이 복원된다.
    """
    session = integration_session

    owner = await _create_user(session, "p1owner")
    member = await _create_user(session, "p1member")

    ws = Workspace(name="P1 워크스페이스", owner_id=owner.id, type="team")
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner"))

    private_project = Project(
        title="P1 비공개",
        workspace_id=ws.id,
        visibility="private",
        created_by_id=owner.id,
    )
    session.add(private_project)
    await session.flush()

    # 사전 잔재: member 가 과거에 ProjectMember 였으나, 당시 정리 로직이 없던 시절
    # 워크스페이스에서 제거되어 orphan 행만 남은 상태를 직접 모사.
    # (현 WorkspaceMember 는 없음 — 즉 member 는 현재 비-멤버.)
    session.add(
        ProjectMember(
            project_id=private_project.id,
            workspace_id=ws.id,
            user_id=member.id,
            role="member",
        )
    )

    invite = WorkspaceInvite(
        workspace_id=ws.id,
        code="p1reinvite0001",
        role="member",
        created_by_id=owner.id,
    )
    session.add(invite)
    await session.commit()

    invite_service = _make_invite_service(session)
    project_service = _make_project_service(session)

    # re-invite 수락 — plain member 로 복귀 (ProjectMember 재추가 없음).
    await invite_service.accept_invite("p1reinvite0001", member.id)

    # 사전 잔재 행이 정리되지 않으면 ws-membership 가드가 다시 참이 되어
    # private project 접근(GET 200)이 복원된다 → 반드시 404 여야 함.
    with pytest.raises(ProjectNotFoundError):
        await project_service.get_project(
            workspace_id=ws.id,
            project_id=private_project.id,
            requester_user_id=member.id,
            requester_role="member",
        )
