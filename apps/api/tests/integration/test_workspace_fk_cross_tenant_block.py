# Sprint 19 PR #2 — composite FK 가 cross-workspace insert 를 차단함을 검증.
"""DB-level constraint hardening (헌법 I-9 (9) 신설).

PR #1 의 service-level 가드 우회 시나리오 — service 검증을 건너뛰고 ORM 으로 직접 mismatch row insert 시도.
composite FK 가 PostgreSQL FK violation 으로 차단해야 함.

Codex 1차 F-1 fix: raw SQL 대신 ORM (SQLModel) 사용 — schema column 변경에 자동 대응.
Codex 1차 F-5 fix: MPL 3 case 분리 (project mismatch / meeting mismatch / valid insert).
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel.ext.asyncio.session import AsyncSession

from src.actions.models import ActionItem
from src.auth.models import User
from src.meetings.models import Meeting
from src.notes.models import Note
from src.projects.models import MeetingProjectLink, Project
from src.workspaces.models import Workspace

pytestmark = pytest.mark.integration


async def _seed_two_workspaces(session: AsyncSession) -> dict:
    """공통 setup: user + workspace A/B + project A/B + meeting A."""
    suffix = uuid.uuid4().hex[:8]
    user = User(
        auth_user_id=f"ba_fk_{suffix}",
        display_name="FK Tester",
        email=f"fk_{suffix}@k.test",
    )
    session.add(user)
    await session.flush()

    ws_a = Workspace(name=f"WS A {suffix}", owner_id=user.id)
    ws_b = Workspace(name=f"WS B {suffix}", owner_id=user.id)
    session.add_all([ws_a, ws_b])
    await session.flush()

    project_a = Project(workspace_id=ws_a.id, title="P A", created_by_id=user.id)
    project_b = Project(workspace_id=ws_b.id, title="P B", created_by_id=user.id)
    meeting_a = Meeting(
        workspace_id=ws_a.id, title="M A", file_key=f"k_{suffix}", created_by_id=user.id
    )
    session.add_all([project_a, project_b, meeting_a])
    await session.flush()
    await session.commit()

    return {
        "user": user,
        "ws_a": ws_a,
        "ws_b": ws_b,
        "project_a": project_a,
        "project_b": project_b,
        "meeting_a": meeting_a,
    }


@pytest.mark.asyncio
async def test_action_items_cross_workspace_project_blocked(
    integration_session: AsyncSession,
):
    """action_items.workspace_id != projects.workspace_id 인 insert 가 FK violation."""
    s = await _seed_two_workspaces(integration_session)
    # cross-tenant: ws_b 의 action_items 에 ws_a 의 project_a 연결
    item = ActionItem(
        workspace_id=s["ws_b"].id, project_id=s["project_a"].id, title="X"
    )
    integration_session.add(item)
    with pytest.raises(IntegrityError):
        await integration_session.commit()
    await integration_session.rollback()


@pytest.mark.asyncio
async def test_notes_cross_workspace_project_blocked(
    integration_session: AsyncSession,
):
    """notes.workspace_id != projects.workspace_id insert 차단."""
    s = await _seed_two_workspaces(integration_session)
    note = Note(
        workspace_id=s["ws_b"].id,
        project_id=s["project_a"].id,
        title="X",
        created_by_id=s["user"].id,
    )
    integration_session.add(note)
    with pytest.raises(IntegrityError):
        await integration_session.commit()
    await integration_session.rollback()


@pytest.mark.asyncio
async def test_notes_nullable_project_id_allowed(
    integration_session: AsyncSession,
):
    """notes.project_id IS NULL = MATCH SIMPLE → composite FK 면제 (의도)."""
    s = await _seed_two_workspaces(integration_session)
    note = Note(
        workspace_id=s["ws_a"].id,
        project_id=None,
        title="Free",
        created_by_id=s["user"].id,
    )
    integration_session.add(note)
    await integration_session.commit()  # 통과 = OK
    assert note.id is not None


@pytest.mark.asyncio
async def test_action_items_nullable_project_id_allowed(
    integration_session: AsyncSession,
):
    """action_items.project_id IS NULL = MATCH SIMPLE → composite FK 면제 (Codex v2 F-3).

    PR #2 가 추가한 fk_action_items_project_workspace 가 nullable project_id 에서도
    PostgreSQL MATCH SIMPLE default 동작으로 면제됨을 검증. notes 와 동일 의도.
    """
    s = await _seed_two_workspaces(integration_session)
    item = ActionItem(
        workspace_id=s["ws_a"].id,
        project_id=None,
        title="Standalone action",
    )
    integration_session.add(item)
    await integration_session.commit()  # 통과 = OK
    assert item.id is not None


@pytest.mark.asyncio
async def test_mpl_cross_workspace_project_blocked(
    integration_session: AsyncSession,
):
    """MPL: project FK violation (workspace=A, meeting=A, project=B)."""
    s = await _seed_two_workspaces(integration_session)
    link = MeetingProjectLink(
        workspace_id=s["ws_a"].id,
        meeting_id=s["meeting_a"].id,
        project_id=s["project_b"].id,
    )
    integration_session.add(link)
    with pytest.raises(IntegrityError):
        await integration_session.commit()
    await integration_session.rollback()


@pytest.mark.asyncio
async def test_mpl_cross_workspace_meeting_blocked(
    integration_session: AsyncSession,
):
    """MPL: meeting FK violation (workspace=B, meeting=A(ws_a), project=B)."""
    s = await _seed_two_workspaces(integration_session)
    link = MeetingProjectLink(
        workspace_id=s["ws_b"].id,
        meeting_id=s["meeting_a"].id,
        project_id=s["project_b"].id,
    )
    integration_session.add(link)
    with pytest.raises(IntegrityError):
        await integration_session.commit()
    await integration_session.rollback()


@pytest.mark.asyncio
async def test_mpl_valid_insert_allowed(integration_session: AsyncSession):
    """MPL: 정상 case (workspace=A, meeting=A, project=A) 통과."""
    s = await _seed_two_workspaces(integration_session)
    link = MeetingProjectLink(
        workspace_id=s["ws_a"].id,
        meeting_id=s["meeting_a"].id,
        project_id=s["project_a"].id,
    )
    integration_session.add(link)
    await integration_session.commit()
    assert link.id is not None
