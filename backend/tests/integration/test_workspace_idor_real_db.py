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
from sqlmodel.ext.asyncio.session import AsyncSession

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


class TestProjectsRealDBIDOR:
    """Codex F-1/F-3 real DB (Sprint 19 PR #1 C9): projects + meeting-link cross-tenant 격리.

    검증 시나리오:
    1. ProjectRepository.find_by_id(project_b_id, ws_a.id) → None
    2. ProjectService.get_project(workspace_id=ws_a, project_id=project_b) → ProjectNotFoundError (F-4 lock-in)
    3. ProjectRepository.add_meeting_link(meeting_a, project_b, ws_a) → ProjectNotFoundError
       (F-3 cascade: cross-workspace 링크 생성 차단)
    """

    @pytest.mark.asyncio
    async def test_workspace_a_cannot_access_workspace_b_project(
        self, integration_session: AsyncSession
    ):
        """헌법 I-9 직접 검증: ProjectRepository.find_by_id 가 cross-tenant 차단."""
        from src.projects.repository import ProjectRepository

        user_a = await _create_user(integration_session, "pa")
        user_b = await _create_user(integration_session, "pb")
        ws_a = await _create_workspace(integration_session, user_a, "워크스페이스 A proj")
        ws_b = await _create_workspace(integration_session, user_b, "워크스페이스 B proj")
        project_b = await _create_project(integration_session, ws_b.id, user_b)

        repo = ProjectRepository(integration_session)

        # A path 로 B project → None
        result = await repo.find_by_id(project_b.id, ws_a.id)
        assert result is None, (
            f"BUG-C01-EXT v3 F-1 real DB: projects cross-tenant 누출. "
            f"workspace_a({ws_a.id}) 가 workspace_b({ws_b.id}) project({project_b.id}) 조회 성공."
        )

        # 같은 workspace → 정상 반환 (sanity)
        own = await repo.find_by_id(project_b.id, ws_b.id)
        assert own is not None and own.id == project_b.id

    @pytest.mark.asyncio
    async def test_workspace_a_get_project_rejects_workspace_b_project(
        self, integration_session: AsyncSession
    ):
        """Codex F-4 lock-in: cross-tenant get_project → ProjectNotFoundError (정보 누설 방지)."""
        from src.projects.exceptions import ProjectNotFoundError
        from src.projects.repository import ProjectRepository
        from src.projects.service import ProjectService
        from src.workspaces.repository import WorkspaceRepository

        user_a = await _create_user(integration_session, "ga")
        user_b = await _create_user(integration_session, "gb")
        ws_a = await _create_workspace(integration_session, user_a, "워크스페이스 A get")
        ws_b = await _create_workspace(integration_session, user_b, "워크스페이스 B get")
        project_b = await _create_project(integration_session, ws_b.id, user_b)

        service = ProjectService(
            repo=ProjectRepository(integration_session),
            ws_repo=WorkspaceRepository(integration_session),
        )

        with pytest.raises(ProjectNotFoundError):
            await service.get_project(
                workspace_id=ws_a.id,
                project_id=project_b.id,
                requester_user_id=user_a,
                requester_role="member",
            )

    @pytest.mark.asyncio
    async def test_workspace_a_add_meeting_link_rejects_workspace_b_project(
        self, integration_session: AsyncSession
    ):
        """Codex F-3 cascade real DB: add_meeting_link 가 cross-workspace project 거부."""
        from src.projects.exceptions import ProjectNotFoundError
        from src.projects.repository import ProjectRepository

        user_a = await _create_user(integration_session, "la")
        user_b = await _create_user(integration_session, "lb")
        ws_a = await _create_workspace(integration_session, user_a, "워크스페이스 A link")
        ws_b = await _create_workspace(integration_session, user_b, "워크스페이스 B link")
        meeting_a = await _create_meeting(integration_session, ws_a.id, user_a)
        project_b = await _create_project(integration_session, ws_b.id, user_b)

        repo = ProjectRepository(integration_session)

        # A meeting + B project + ws_a 시도 → ProjectNotFoundError
        with pytest.raises(ProjectNotFoundError):
            await repo.add_meeting_link(meeting_a.id, project_b.id, ws_a.id)


class TestInboxClassifySourceMeetingRealDB:
    """Codex 2차 F-1 real DB (Sprint 19 PR #1 C13a): inbox classify 의 source_id cross-tenant.

    handoff v2 Codex 2차 Minor 2 였던 finding 이 본 C13a 에서 fix. InboxService 가
    MeetingRepository 동반 주입 받아 source_type='meeting' 시 item.source_id 검증.
    """

    @pytest.mark.asyncio
    async def test_inbox_classify_rejects_cross_tenant_meeting_source_id(
        self, integration_session: AsyncSession
    ):
        """workspace A inbox 에 workspace B meeting source_id → MeetingNotFoundError."""
        from src.inbox.models import InboxItem
        from src.inbox.repository import InboxRepository
        from src.inbox.service import InboxService
        from src.meetings.exceptions import MeetingNotFoundError
        from src.meetings.repository import MeetingRepository
        from src.projects.repository import ProjectRepository

        user_a = await _create_user(integration_session, "imA")
        user_b = await _create_user(integration_session, "imB")
        ws_a = await _create_workspace(integration_session, user_a, "워크스페이스 A inbox")
        ws_b = await _create_workspace(integration_session, user_b, "워크스페이스 B inbox")
        meeting_b = await _create_meeting(integration_session, ws_b.id, user_b)
        project_a = await _create_project(integration_session, ws_a.id, user_a)

        # workspace A 에 inbox item 생성 (source_id 는 workspace B meeting)
        inbox_item = InboxItem(
            workspace_id=ws_a.id,
            source_type="meeting",
            source_id=meeting_b.id,  # cross-workspace!
            title="A 의 inbox 이지만 B meeting source",
            ai_suggested_project_id=None,
            ai_suggested_project_title=None,
            ai_suggested_tags=[],
            ai_confidence=0.5,
            is_processed=False,
        )
        integration_session.add(inbox_item)
        await integration_session.flush()

        service = InboxService(
            inbox_repo=InboxRepository(integration_session),
            project_repo=ProjectRepository(integration_session),
            meeting_repo=MeetingRepository(integration_session),
        )

        # A user 가 classify(inbox_a.id, ws_a, [project_a]) 시도
        # → source_id 가 ws_b meeting 이라 MeetingNotFoundError
        with pytest.raises(MeetingNotFoundError):
            await service.classify(
                inbox_id=inbox_item.id,
                workspace_id=ws_a.id,
                project_ids=[project_a.id],
            )

    @pytest.mark.asyncio
    async def test_inbox_service_classify_fail_closed_without_meeting_repo(
        self,
    ):
        """Codex 2차 F-1 fail-closed: meeting_repo=None → RuntimeError."""
        from unittest.mock import AsyncMock, MagicMock
        from src.inbox.service import InboxService

        # source_type='meeting' inbox item mock
        mock_item = MagicMock()
        mock_item.source_type = "meeting"
        mock_item.source_id = uuid.uuid4()
        mock_item.is_processed = False
        mock_item.updated_at = None

        mock_inbox_repo = AsyncMock()
        mock_inbox_repo.find_by_id = AsyncMock(return_value=mock_item)
        mock_inbox_repo.save = AsyncMock()
        mock_inbox_repo.commit = AsyncMock()

        mock_project = MagicMock()
        mock_project.id = uuid.uuid4()
        mock_project.title = "p"
        mock_project_repo = AsyncMock()
        mock_project_repo.find_by_id = AsyncMock(return_value=mock_project)

        service = InboxService(
            inbox_repo=mock_inbox_repo,
            project_repo=mock_project_repo,
            meeting_repo=None,  # 의도적으로 None
        )

        with pytest.raises(RuntimeError, match="meeting_repo 필수"):
            await service.classify(
                inbox_id=uuid.uuid4(),
                workspace_id=uuid.uuid4(),
                project_ids=[mock_project.id],
            )
