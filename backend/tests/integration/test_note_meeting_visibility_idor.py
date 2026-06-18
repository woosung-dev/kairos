# CAND-A — note/meeting get+export visibility-residue IDOR 회귀 (real DB)
"""private/draft 프로젝트에 속한 note/meeting 을 ProjectMember 가 아닌 워크스페이스
멤버가 GET/export 로 읽어가는 visibility-residue IDOR 회귀 가드.

배경 (CAND-A, PROBE-SENTINEL-01):
- get_note/export_note 와 get_meeting_detail/export_meeting 은 workspace_id 만 필터하고
  project visibility 게이트가 없어, private/draft project 의 confidential 본문 (+ 트랜스크립트/
  요약/export md·json) 이 비-ProjectMember 워크스페이스 멤버에게 노출됐다.
- 기대: get_project 와 동일한 visibility 게이트 — 비-멤버는 private 에서 404,
  비-작성자는 draft 에서 404, admin/owner 우회, 멤버/작성자는 200.

anti-hollow-green: service mock 금지 — 실제 NoteService/MeetingService + repository seam 을
integration_session (실 PostgreSQL) 위에서 직접 행사한다 (QA-0617-A lesson). 외부 경계
(OpenAI/Gemini/R2) 는 본 경로에서 호출되지 않으므로 stub 불필요.
"""
from __future__ import annotations

import uuid

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

pytestmark = pytest.mark.integration


# --- 공용 헬퍼 ---------------------------------------------------------------


async def _create_user(session: AsyncSession, tag: str) -> uuid.UUID:
    from src.auth.models import User

    user = User(
        clerk_id=f"clerk_{uuid.uuid4().hex}",
        display_name=f"유저 {tag}",
        email=f"vis_{tag}_{uuid.uuid4().hex}@example.com",
    )
    session.add(user)
    await session.flush()
    return user.id


async def _create_team_ws(
    session: AsyncSession, owner_id: uuid.UUID
) -> uuid.UUID:
    from src.workspaces.models import Workspace, WorkspaceMember

    ws = Workspace(name=f"팀 {uuid.uuid4().hex[:6]}", owner_id=owner_id, type="team")
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner_id, role="owner"))
    await session.flush()
    return ws.id


async def _add_ws_member(
    session: AsyncSession, ws_id: uuid.UUID, user_id: uuid.UUID, role: str
) -> None:
    from src.workspaces.models import WorkspaceMember

    session.add(WorkspaceMember(workspace_id=ws_id, user_id=user_id, role=role))
    await session.flush()


async def _create_project(
    session: AsyncSession,
    ws_id: uuid.UUID,
    creator_id: uuid.UUID,
    visibility: str,
):
    from src.projects.models import Project

    project = Project(
        workspace_id=ws_id,
        title=f"프로젝트 {visibility}",
        created_by_id=creator_id,
        status="active",
        visibility=visibility,
    )
    session.add(project)
    await session.flush()
    return project


async def _add_project_member(
    session: AsyncSession,
    project_id: uuid.UUID,
    ws_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    from src.projects.models import ProjectMember

    session.add(
        ProjectMember(
            project_id=project_id,
            workspace_id=ws_id,
            user_id=user_id,
            role="member",
        )
    )
    await session.flush()


async def _create_note(
    session: AsyncSession,
    ws_id: uuid.UUID,
    project_id: uuid.UUID | None,
    creator_id: uuid.UUID,
    secret: str,
):
    from src.notes.models import Note

    note = Note(
        workspace_id=ws_id,
        project_id=project_id,
        title="비밀 노트",
        content={"type": "doc", "content": []},
        plain_text=secret,
        created_by_id=creator_id,
    )
    session.add(note)
    await session.flush()
    return note


async def _create_meeting_in_project(
    session: AsyncSession,
    ws_id: uuid.UUID,
    project,
    creator_id: uuid.UUID,
    secret: str,
):
    """meeting + transcript + summary 생성 후 project 에 링크."""
    from src.meetings.models import Meeting, MeetingSummary, TranscriptSegment
    from src.projects.models import MeetingProjectLink

    meeting = Meeting(
        workspace_id=ws_id,
        title="비밀 회의",
        file_key=f"uploads/{uuid.uuid4().hex}.mp3",
        created_by_id=creator_id,
        status="completed",
        has_transcript=True,
        has_summary=True,
    )
    session.add(meeting)
    await session.flush()
    session.add(
        TranscriptSegment(
            meeting_id=meeting.id,
            speaker="Speaker",
            start_sec=0.0,
            end_sec=5.0,
            text=secret,
        )
    )
    session.add(
        MeetingSummary(
            meeting_id=meeting.id,
            summary=secret,
            key_decisions=[secret],
            topics=["topic"],
        )
    )
    session.add(
        MeetingProjectLink(
            meeting_id=meeting.id,
            project_id=project.id,
            workspace_id=ws_id,
        )
    )
    await session.flush()
    return meeting


def _note_service(session: AsyncSession):
    from src.notes.repository import NoteRepository
    from src.notes.service import NoteService
    from src.projects.repository import ProjectRepository

    return NoteService(
        repo=NoteRepository(session),
        project_repo=ProjectRepository(session),
    )


def _meeting_service(session: AsyncSession):
    from src.actions.repository import ActionItemRepository
    from src.meetings.repository import MeetingRepository
    from src.meetings.service import MeetingService
    from src.projects.repository import ProjectRepository

    return MeetingService(
        repo=MeetingRepository(session),
        action_repo=ActionItemRepository(session),
        project_repo=ProjectRepository(session),
    )


# --- NOTES: private project visibility ---------------------------------------


class TestNotePrivateVisibilityIDOR:
    SECRET = "NONCE-NOTE-PRIVATE-7f3a"

    @pytest.mark.asyncio
    async def test_non_project_member_cannot_get_private_note(
        self, integration_session: AsyncSession
    ):
        from src.notes.exceptions import NoteNotFoundError

        owner = await _create_user(integration_session, "owner")
        outsider = await _create_user(integration_session, "outsider")
        ws = await _create_team_ws(integration_session, owner)
        # outsider 는 워크스페이스 멤버 (viewer) 지만 ProjectMember 는 아님
        await _add_ws_member(integration_session, ws, outsider, "viewer")
        project = await _create_project(integration_session, ws, owner, "private")
        note = await _create_note(
            integration_session, ws, project.id, owner, self.SECRET
        )

        service = _note_service(integration_session)

        # 비-ProjectMember viewer → 404 (NoteNotFoundError)
        with pytest.raises(NoteNotFoundError):
            await service.get_note(
                note.id, ws, requester_user_id=outsider, requester_role="viewer"
            )

    @pytest.mark.asyncio
    async def test_non_project_member_cannot_export_private_note(
        self, integration_session: AsyncSession
    ):
        from src.notes.exceptions import NoteNotFoundError

        owner = await _create_user(integration_session, "owner")
        outsider = await _create_user(integration_session, "outsider")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, outsider, "member")
        project = await _create_project(integration_session, ws, owner, "private")
        note = await _create_note(
            integration_session, ws, project.id, owner, self.SECRET
        )

        service = _note_service(integration_session)

        with pytest.raises(NoteNotFoundError):
            await service.export_note(
                note.id, ws, "md", requester_user_id=outsider, requester_role="member"
            )

    @pytest.mark.asyncio
    async def test_project_member_can_get_private_note(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        insider = await _create_user(integration_session, "insider")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, insider, "member")
        project = await _create_project(integration_session, ws, owner, "private")
        await _add_project_member(integration_session, project.id, ws, insider)
        note = await _create_note(
            integration_session, ws, project.id, owner, self.SECRET
        )

        service = _note_service(integration_session)

        # ProjectMember → 200 (정상 접근 보존)
        result = await service.get_note(
            note.id, ws, requester_user_id=insider, requester_role="member"
        )
        assert result["plainText"] == self.SECRET

    @pytest.mark.asyncio
    async def test_admin_bypasses_private_note(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        admin = await _create_user(integration_session, "admin")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, admin, "admin")
        project = await _create_project(integration_session, ws, owner, "private")
        note = await _create_note(
            integration_session, ws, project.id, owner, self.SECRET
        )

        service = _note_service(integration_session)

        # admin 은 비-ProjectMember 라도 우회 → 200
        result = await service.get_note(
            note.id, ws, requester_user_id=admin, requester_role="admin"
        )
        assert result["plainText"] == self.SECRET


class TestNoteDraftVisibilityIDOR:
    SECRET = "NONCE-NOTE-DRAFT-2c9e"

    @pytest.mark.asyncio
    async def test_non_creator_member_cannot_get_draft_note(
        self, integration_session: AsyncSession
    ):
        from src.notes.exceptions import NoteNotFoundError

        creator = await _create_user(integration_session, "creator")
        other = await _create_user(integration_session, "other")
        ws = await _create_team_ws(integration_session, creator)
        await _add_ws_member(integration_session, ws, other, "member")
        project = await _create_project(integration_session, ws, creator, "draft")
        note = await _create_note(
            integration_session, ws, project.id, creator, self.SECRET
        )

        service = _note_service(integration_session)

        # draft → 작성자가 아닌 멤버는 404
        with pytest.raises(NoteNotFoundError):
            await service.get_note(
                note.id, ws, requester_user_id=other, requester_role="member"
            )

    @pytest.mark.asyncio
    async def test_creator_can_get_draft_note(
        self, integration_session: AsyncSession
    ):
        creator = await _create_user(integration_session, "creator")
        ws = await _create_team_ws(integration_session, creator)
        project = await _create_project(integration_session, ws, creator, "draft")
        note = await _create_note(
            integration_session, ws, project.id, creator, self.SECRET
        )

        service = _note_service(integration_session)

        # 작성자(owner role) → 200
        result = await service.get_note(
            note.id, ws, requester_user_id=creator, requester_role="owner"
        )
        assert result["plainText"] == self.SECRET


class TestNotePublicAndNullProject:
    SECRET = "NONCE-NOTE-PUBLIC-aa01"

    @pytest.mark.asyncio
    async def test_member_can_get_public_project_note(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        member = await _create_user(integration_session, "member")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, member, "member")
        project = await _create_project(integration_session, ws, owner, "public")
        note = await _create_note(
            integration_session, ws, project.id, owner, self.SECRET
        )

        service = _note_service(integration_session)

        result = await service.get_note(
            note.id, ws, requester_user_id=member, requester_role="member"
        )
        assert result["plainText"] == self.SECRET

    @pytest.mark.asyncio
    async def test_member_can_get_unscoped_note(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        member = await _create_user(integration_session, "member")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, member, "member")
        note = await _create_note(integration_session, ws, None, owner, self.SECRET)

        service = _note_service(integration_session)

        # project_id=None → 워크스페이스 멤버 누구나 OK
        result = await service.get_note(
            note.id, ws, requester_user_id=member, requester_role="member"
        )
        assert result["plainText"] == self.SECRET


# --- MEETINGS: linked private project visibility -----------------------------


class TestMeetingPrivateVisibilityIDOR:
    SECRET = "NONCE-MEETING-PRIVATE-91d4"

    @pytest.mark.asyncio
    async def test_non_project_member_cannot_get_private_meeting(
        self, integration_session: AsyncSession
    ):
        from src.meetings.exceptions import MeetingNotFoundError

        owner = await _create_user(integration_session, "owner")
        outsider = await _create_user(integration_session, "outsider")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, outsider, "viewer")
        project = await _create_project(integration_session, ws, owner, "private")
        meeting = await _create_meeting_in_project(
            integration_session, ws, project, owner, self.SECRET
        )

        service = _meeting_service(integration_session)

        # 비-ProjectMember viewer → 404 (transcript/summary leak 차단)
        with pytest.raises(MeetingNotFoundError):
            await service.get_meeting_detail(
                meeting.id, ws, requester_user_id=outsider, requester_role="viewer"
            )

    @pytest.mark.asyncio
    async def test_non_project_member_cannot_export_private_meeting(
        self, integration_session: AsyncSession
    ):
        from src.meetings.exceptions import MeetingNotFoundError

        owner = await _create_user(integration_session, "owner")
        outsider = await _create_user(integration_session, "outsider")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, outsider, "member")
        project = await _create_project(integration_session, ws, owner, "private")
        meeting = await _create_meeting_in_project(
            integration_session, ws, project, owner, self.SECRET
        )

        service = _meeting_service(integration_session)

        with pytest.raises(MeetingNotFoundError):
            await service.export_meeting(
                meeting.id, ws, "md",
                requester_user_id=outsider, requester_role="member",
            )

    @pytest.mark.asyncio
    async def test_project_member_can_get_private_meeting(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        insider = await _create_user(integration_session, "insider")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, insider, "member")
        project = await _create_project(integration_session, ws, owner, "private")
        await _add_project_member(integration_session, project.id, ws, insider)
        meeting = await _create_meeting_in_project(
            integration_session, ws, project, owner, self.SECRET
        )

        service = _meeting_service(integration_session)

        result = await service.get_meeting_detail(
            meeting.id, ws, requester_user_id=insider, requester_role="member"
        )
        assert result["summary"]["summary"] == self.SECRET

    @pytest.mark.asyncio
    async def test_owner_bypasses_private_meeting(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        ws = await _create_team_ws(integration_session, owner)
        project = await _create_project(integration_session, ws, owner, "private")
        meeting = await _create_meeting_in_project(
            integration_session, ws, project, owner, self.SECRET
        )

        service = _meeting_service(integration_session)

        # owner 우회 → 200
        result = await service.get_meeting_detail(
            meeting.id, ws, requester_user_id=owner, requester_role="owner"
        )
        assert result["summary"]["summary"] == self.SECRET


class TestMeetingUnlinkedAccessible:
    SECRET = "NONCE-MEETING-OPEN-5b22"

    @pytest.mark.asyncio
    async def test_member_can_get_meeting_with_no_project_links(
        self, integration_session: AsyncSession
    ):
        from src.meetings.models import Meeting, MeetingSummary

        owner = await _create_user(integration_session, "owner")
        member = await _create_user(integration_session, "member")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, member, "member")

        meeting = Meeting(
            workspace_id=ws,
            title="링크 없는 회의",
            file_key=f"uploads/{uuid.uuid4().hex}.mp3",
            created_by_id=owner,
            status="completed",
            has_summary=True,
        )
        integration_session.add(meeting)
        await integration_session.flush()
        integration_session.add(
            MeetingSummary(
                meeting_id=meeting.id,
                summary=self.SECRET,
                key_decisions=[],
                topics=[],
            )
        )
        await integration_session.flush()

        service = _meeting_service(integration_session)

        # 프로젝트 링크 없음 → 워크스페이스 멤버 누구나 OK (회귀 방지)
        result = await service.get_meeting_detail(
            meeting.id, ws, requester_user_id=member, requester_role="member"
        )
        assert result["summary"]["summary"] == self.SECRET
