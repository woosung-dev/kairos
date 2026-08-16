# 회의-프로젝트 링크 멱등성 실 DB 통합 테스트 (Sprint 29 R1 inbox-IB5).
"""ProjectRepository.add_meeting_link 멱등성 회귀 가드.

기존 inbox 테스트는 add_meeting_link 를 mock 으로 우회 → 실제 uq_meeting_project
위반(재분류 시 500)을 검출 못했다. 본 테스트는 실 DB 로 멱등성을 직접 검증한다.
"""
import uuid

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.projects.models import MeetingProjectLink, Project
from src.projects.repository import ProjectRepository

pytestmark = pytest.mark.integration


async def _seed(session: AsyncSession):
    """user + team workspace + project + meeting 시드."""
    from src.auth.models import User
    from src.meetings.models import Meeting
    from src.workspaces.models import Workspace

    user = User(
        auth_user_id=f"ba_{uuid.uuid4().hex}",
        display_name="유저",
        email=f"{uuid.uuid4().hex}@example.test",
    )
    session.add(user)
    await session.flush()
    ws = Workspace(name="테스트 ws", owner_id=user.id, type="team")
    session.add(ws)
    await session.flush()
    project = Project(
        title="P", workspace_id=ws.id, visibility="public", created_by_id=user.id
    )
    session.add(project)
    await session.flush()
    meeting = Meeting(
        workspace_id=ws.id, title="M", file_key="k", created_by_id=user.id
    )
    session.add(meeting)
    await session.flush()
    return ws, project, meeting


async def test_add_meeting_link_idempotent(integration_session: AsyncSession):
    """inbox-IB5: 동일 (meeting, project) 재연결은 no-op.

    이전엔 재분류 시 uq_meeting_project 위반 → IntegrityError → 500.
    이제 add_meeting_link 가 기존 행을 멱등 반환하고 단일 commit 모델을 유지한다.
    """
    ws, project, meeting = await _seed(integration_session)
    repo = ProjectRepository(integration_session)

    link1 = await repo.add_meeting_link(meeting.id, project.id, ws.id)
    link2 = await repo.add_meeting_link(meeting.id, project.id, ws.id)  # 재분류

    assert link1.id == link2.id  # 동일 행 반환 (no-op)
    rows = (
        await integration_session.exec(
            select(MeetingProjectLink).where(
                MeetingProjectLink.meeting_id == meeting.id,
                MeetingProjectLink.project_id == project.id,
            )
        )
    ).all()
    assert len(rows) == 1  # 중복 행 미생성


async def test_add_meeting_link_many_to_many_allowed(
    integration_session: AsyncSession,
):
    """같은 meeting 을 다른 project 에 연결하는 건 정상 (many-to-many)."""
    ws, project_a, meeting = await _seed(integration_session)
    project_b = Project(
        title="PB",
        workspace_id=ws.id,
        visibility="public",
        created_by_id=project_a.created_by_id,
    )
    integration_session.add(project_b)
    await integration_session.flush()
    repo = ProjectRepository(integration_session)

    await repo.add_meeting_link(meeting.id, project_a.id, ws.id)
    await repo.add_meeting_link(meeting.id, project_b.id, ws.id)

    rows = (
        await integration_session.exec(
            select(MeetingProjectLink).where(
                MeetingProjectLink.meeting_id == meeting.id
            )
        )
    ).all()
    assert len(rows) == 2  # 서로 다른 project → 2 링크
