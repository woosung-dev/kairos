# Sprint 19 PR #1 BUG-C01-EXT v3 — real DB cross-tenant 격리 검증 (Codex F-3 신설)
"""실제 PostgreSQL (TestContainers) 위에서 4 도메인 cross-tenant 격리 직접 검증.

배경 (Codex F-3 Major):
- 기존 matrix test 는 service mock + call_args 검증이라 repository WHERE 절이
  실제로 workspace_id 필터링하는지 검증하지 못함.
- 본 파일은 두 workspace (A/B) 실 DB 셋업 후 cross-tenant 시도 → None / 404 보장.

검증 시나리오 (도메인별 1 케이스 = 4 테스트):
1. meetings: A path 로 B meeting find_by_id → None (헌법 I-9 직접 검증)
2. notes: A update_note 가 B project_id 시도 → ProjectNotFoundError (Codex F-2 Critical)
3. inbox: A classify 가 B project_id 시도 → ProjectNotFoundError (Codex F-2 Critical)
4. actions: A update_action_item assignee_id 가 B 멤버 시도 → NotFoundError (Codex F-2 Critical)
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


# --- 공용 헬퍼 ---------------------------------------------------------------

async def _create_user(session: AsyncSession, email_tag: str = "") -> uuid.UUID:
    from src.auth.models import User
    user = User(
        clerk_id=f"clerk_{uuid.uuid4().hex}",
        display_name=f"테스트 유저 {email_tag}",
        email=f"test_{email_tag}_{uuid.uuid4().hex}@example.com",
    )
    session.add(user)
    await session.flush()
    return user.id


async def _create_workspace(session: AsyncSession, owner_id: uuid.UUID, name: str):
    from src.workspaces.models import Workspace, WorkspaceMember
    ws = Workspace(name=name, owner_id=owner_id)
    session.add(ws)
    await session.flush()
    # owner 를 멤버로 추가
    member = WorkspaceMember(workspace_id=ws.id, user_id=owner_id, role="owner")
    session.add(member)
    await session.flush()
    return ws


async def _create_project(session: AsyncSession, workspace_id: uuid.UUID, owner_id: uuid.UUID):
    from src.projects.models import Project
    project = Project(
        workspace_id=workspace_id,
        title=f"프로젝트 {uuid.uuid4().hex[:6]}",
        created_by_id=owner_id,
        status="active",
        visibility="public",
    )
    session.add(project)
    await session.flush()
    return project


async def _create_meeting(session: AsyncSession, workspace_id: uuid.UUID, owner_id: uuid.UUID):
    from src.meetings.models import Meeting
    meeting = Meeting(
        workspace_id=workspace_id,
        title="테스트 회의",
        file_key=f"uploads/{uuid.uuid4().hex}.mp3",
        created_by_id=owner_id,
        status="uploading",
    )
    session.add(meeting)
    await session.flush()
    return meeting


# --- 도메인별 cross-tenant 격리 검증 -----------------------------------------


class TestMeetingsRealDBIDOR:
    """Codex F-3 + F-1: A workspace path 로 B meeting_id 시도 시 None 반환."""

    @pytest.mark.asyncio
    async def test_workspace_a_cannot_access_workspace_b_meeting(
        self, integration_session: AsyncSession
    ):
        from src.meetings.repository import MeetingRepository

        # 두 workspace 셋업
        user_a = await _create_user(integration_session, "a")
        user_b = await _create_user(integration_session, "b")
        ws_a = await _create_workspace(integration_session, user_a, "워크스페이스 A")
        ws_b = await _create_workspace(integration_session, user_b, "워크스페이스 B")
        meeting_b = await _create_meeting(integration_session, ws_b.id, user_b)

        repo = MeetingRepository(integration_session)

        # A path 로 B meeting → None (헌법 I-9 직접 검증)
        result = await repo.find_by_id(meeting_b.id, ws_a.id)
        assert result is None, (
            f"BUG-C01-EXT v3 F-1/F-3 real DB: meetings cross-tenant 누출. "
            f"workspace_a({ws_a.id}) 가 workspace_b({ws_b.id}) meeting({meeting_b.id}) 조회 성공."
        )

        # 같은 workspace path → 정상 반환 (sanity)
        own = await repo.find_by_id(meeting_b.id, ws_b.id)
        assert own is not None and own.id == meeting_b.id


class TestNotesRealDBIDOR:
    """Codex F-2 Critical real DB: notes update_note 가 cross-workspace project_id 거부."""

    @pytest.mark.asyncio
    async def test_workspace_a_cannot_link_note_to_workspace_b_project(
        self, integration_session: AsyncSession
    ):
        from src.notes.exceptions import NoteNotFoundError  # noqa: F401
        from src.notes.models import Note
        from src.notes.repository import NoteRepository
        from src.notes.service import NoteService
        from src.projects.exceptions import ProjectNotFoundError
        from src.projects.repository import ProjectRepository

        user_a = await _create_user(integration_session, "a")
        user_b = await _create_user(integration_session, "b")
        ws_a = await _create_workspace(integration_session, user_a, "WS-A")
        ws_b = await _create_workspace(integration_session, user_b, "WS-B")
        project_b = await _create_project(integration_session, ws_b.id, user_b)

        # A workspace 의 note 생성
        note_a = Note(
            workspace_id=ws_a.id,
            project_id=None,
            title="A note",
            content={"type": "doc", "content": []},
            plain_text="",
            created_by_id=user_a,
        )
        integration_session.add(note_a)
        await integration_session.flush()

        service = NoteService(
            repo=NoteRepository(integration_session),
            project_repo=ProjectRepository(integration_session),
        )

        # A 가 note_a 에 B 의 project_id 연결 시도 → ProjectNotFoundError (404)
        with pytest.raises(ProjectNotFoundError):
            await service.update_note(
                note_id=note_a.id,
                workspace_id=ws_a.id,
                project_id=project_b.id,  # cross-workspace
            )


class TestInboxRealDBIDOR:
    """Codex F-2 Critical real DB: inbox classify 가 cross-workspace project_ids 거부."""

    @pytest.mark.asyncio
    async def test_workspace_a_classify_rejects_workspace_b_project_id(
        self, integration_session: AsyncSession
    ):
        from src.inbox.models import InboxItem
        from src.inbox.repository import InboxRepository
        from src.inbox.service import InboxService
        from src.projects.exceptions import ProjectNotFoundError
        from src.projects.repository import ProjectRepository

        user_a = await _create_user(integration_session, "a")
        user_b = await _create_user(integration_session, "b")
        ws_a = await _create_workspace(integration_session, user_a, "WS-A")
        ws_b = await _create_workspace(integration_session, user_b, "WS-B")
        project_b = await _create_project(integration_session, ws_b.id, user_b)

        # A workspace 의 inbox item 생성 (meeting 없이 source_type='note' 안전 케이스)
        inbox_a = InboxItem(
            workspace_id=ws_a.id,
            title="A inbox",
            summary="",
            source_type="note",
            source_id=uuid.uuid4(),
            ai_confidence=0.5,
            is_processed=False,
        )
        integration_session.add(inbox_a)
        await integration_session.flush()

        service = InboxService(
            inbox_repo=InboxRepository(integration_session),
            project_repo=ProjectRepository(integration_session),
        )

        # A 가 inbox_a 를 B 의 project 로 classify 시도 → 404
        with pytest.raises(ProjectNotFoundError):
            await service.classify(
                inbox_id=inbox_a.id,
                workspace_id=ws_a.id,
                project_ids=[project_b.id],
            )


class TestActionsRealDBIDOR:
    """Codex F-2 Critical real DB: actions update_action_item 가 cross-workspace assignee 거부."""

    @pytest.mark.asyncio
    async def test_workspace_a_update_rejects_workspace_b_member_assignee(
        self, integration_session: AsyncSession
    ):
        from src.actions.models import ActionItem
        from src.actions.repository import ActionItemRepository
        from src.actions.service import ActionItemService
        from src.common.exceptions import NotFoundError
        from src.meetings.repository import MeetingRepository
        from src.projects.repository import ProjectRepository
        from src.workspaces.repository import WorkspaceRepository

        user_a = await _create_user(integration_session, "a")
        user_b = await _create_user(integration_session, "b")  # 다른 workspace 멤버
        ws_a = await _create_workspace(integration_session, user_a, "WS-A")
        await _create_workspace(integration_session, user_b, "WS-B")  # user_b 는 ws_b 멤버

        # A workspace 의 action item 생성
        action_a = ActionItem(
            workspace_id=ws_a.id,
            title="A action",
            description=None,
            priority="medium",
            status="todo",
        )
        integration_session.add(action_a)
        await integration_session.flush()

        service = ActionItemService(
            repo=ActionItemRepository(integration_session),
            project_repo=ProjectRepository(integration_session),
            meeting_repo=MeetingRepository(integration_session),
            workspace_repo=WorkspaceRepository(integration_session),
        )

        # A 가 action_a 의 assignee 를 ws_b 의 user_b 로 변경 시도 → 404
        with pytest.raises(NotFoundError):
            await service.update_action_item(
                action_id=action_a.id,
                workspace_id=ws_a.id,
                assignee_id=user_b,
            )
