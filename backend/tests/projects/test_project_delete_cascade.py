# 프로젝트 삭제 시 join 행(ProjectMember/MeetingProjectLink) 정리 — FK 500 회귀 가드 (2026-07-05 T20 발견)
"""BUG-PROJECT-DELETE-FK: private 생성 시 creator 가 ProjectMember 로 자동 추가(락아웃 fix)되면서
DELETE /projects/{id} 가 fk_project_members_project_workspace 위반으로 500.
delete_project 는 join 행(멤버십/미팅 링크)을 같은 트랜잭션에서 먼저 지워야 한다.
콘텐츠 FK(notes/actions 의 project_id)는 별도 정책 결정 (REFACTORING-BACKLOG 등재).
"""
import uuid

import pytest
from sqlalchemy import text as sa_text

from src.auth.models import User
from src.meetings.models import Meeting
from src.projects.models import MeetingProjectLink, Project, ProjectMember
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.models import Workspace, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository


async def _count(session, table: str, project_id: uuid.UUID) -> int:
    result = await session.execute(
        sa_text(f"SELECT COUNT(*) FROM {table} WHERE project_id = :pid"),
        {"pid": str(project_id)},
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_delete_project_removes_members_and_meeting_links(integration_session):
    """멤버십 + 미팅 링크가 있는 프로젝트 삭제가 FK 위반 없이 완료 + join 행 0."""
    session = integration_session
    owner = User(
        clerk_id=f"clerk_pdel_{uuid.uuid4()}",
        display_name="pdel",
        email=f"pdel_{uuid.uuid4()}@del.test",
    )
    session.add(owner)
    await session.flush()

    ws = Workspace(name="pdel ws", owner_id=owner.id, type="team")
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner"))

    project = Project(
        workspace_id=ws.id, title="pdel-private", created_by_id=owner.id,
        visibility="private",
    )
    session.add(project)
    await session.flush()
    session.add(
        ProjectMember(project_id=project.id, workspace_id=ws.id, user_id=owner.id)
    )
    meeting = Meeting(
        workspace_id=ws.id, title="pdel-m", file_key="pdel/m.webm",
        created_by_id=owner.id,
    )
    session.add(meeting)
    await session.flush()
    session.add(
        MeetingProjectLink(
            meeting_id=meeting.id, project_id=project.id, workspace_id=ws.id
        )
    )
    await session.flush()
    project_id = project.id

    service = ProjectService(
        repo=ProjectRepository(session), ws_repo=WorkspaceRepository(session)
    )
    await service.delete_project(ws.id, project_id)

    assert await _count(session, "project_members", project_id) == 0
    assert await _count(session, "meeting_project_links", project_id) == 0
    result = await session.execute(
        sa_text("SELECT COUNT(*) FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )
    assert int(result.scalar_one()) == 0
