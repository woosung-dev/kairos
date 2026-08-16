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

import json
import uuid

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

pytestmark = pytest.mark.integration


# --- 공용 헬퍼 ---------------------------------------------------------------


async def _create_user(session: AsyncSession, tag: str) -> uuid.UUID:
    from src.auth.models import User

    user = User(
        auth_user_id=f"ba_{uuid.uuid4().hex}",
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


def _note_pipeline(session: AsyncSession):
    """CAND-A completeness: delete_note_with_cleanup 게이트 검증용 pipeline."""
    from src.embeddings.repository import EmbeddingRepository
    from src.embeddings.service import EmbeddingService
    from src.notes.pipeline_service import NotePipelineService
    from src.notes.repository import NoteRepository
    from src.projects.repository import ProjectRepository

    return NotePipelineService(
        note_repo=NoteRepository(session),
        embedding_service=EmbeddingService(EmbeddingRepository(session)),
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


# ===========================================================================
# CAND-A completeness — sibling 경로 회귀 (codex NO-GO findings)
# list / status / write / promote 가 prior fix 의 get+export 게이트를 우회하던 갭.
# ===========================================================================


# --- NOTES list: visibility filter (P0 본문 누출) ---------------------------


class TestNoteListVisibilityIDOR:
    PRIVATE = "NONCE-LIST-PRIVATE-3a7c"
    DRAFT = "NONCE-LIST-DRAFT-9f2b"
    PUBLIC = "NONCE-LIST-PUBLIC-cc14"

    async def _seed(self, session: AsyncSession):
        owner = await _create_user(session, "owner")
        outsider = await _create_user(session, "outsider")
        ws = await _create_team_ws(session, owner)
        await _add_ws_member(session, ws, outsider, "member")
        priv = await _create_project(session, ws, owner, "private")
        draft = await _create_project(session, ws, owner, "draft")
        pub = await _create_project(session, ws, owner, "public")
        await _create_note(session, ws, priv.id, owner, self.PRIVATE)
        await _create_note(session, ws, draft.id, owner, self.DRAFT)
        await _create_note(session, ws, pub.id, owner, self.PUBLIC)
        await _create_note(session, ws, None, owner, "unscoped")
        return owner, outsider, ws, priv

    @pytest.mark.asyncio
    async def test_non_member_list_excludes_private_and_draft(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, priv = await self._seed(integration_session)
        service = _note_service(integration_session)

        # 필터 없는 전체 목록 — 비-멤버는 private/draft 본문을 못 봐야 한다.
        result = await service.list_notes(
            ws, requester_user_id=outsider, requester_role="member"
        )
        bodies = {item["plainText"] for item in result["items"]}
        assert self.PRIVATE not in bodies
        assert self.DRAFT not in bodies
        # public + unscoped 는 보임 (정상 접근 보존)
        assert self.PUBLIC in bodies
        assert "unscoped" in bodies
        # total 도 필터된 집합 기준 (pagination 정합) — 2개만
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_non_member_list_by_private_project_id_empty(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, priv = await self._seed(integration_session)
        service = _note_service(integration_session)

        # projectId=<private> 명시 필터 — 비-멤버는 0건 (본문 누출 차단)
        result = await service.list_notes(
            ws,
            project_id=priv.id,
            requester_user_id=outsider,
            requester_role="member",
        )
        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_member_list_includes_all_accessible(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, priv = await self._seed(integration_session)
        # outsider 를 private project 멤버로 승격
        await _add_project_member(integration_session, priv.id, ws, outsider)
        service = _note_service(integration_session)

        result = await service.list_notes(
            ws, requester_user_id=outsider, requester_role="member"
        )
        bodies = {item["plainText"] for item in result["items"]}
        # ProjectMember → private 도 보임 (draft 는 비-작성자라 여전히 제외)
        assert self.PRIVATE in bodies
        assert self.DRAFT not in bodies

    @pytest.mark.asyncio
    async def test_creator_list_sees_own_draft(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, priv = await self._seed(integration_session)
        service = _note_service(integration_session)

        # 작성자(owner role) → 자기 draft 포함 전부 보임
        result = await service.list_notes(
            ws, requester_user_id=owner, requester_role="owner"
        )
        bodies = {item["plainText"] for item in result["items"]}
        assert self.PRIVATE in bodies
        assert self.DRAFT in bodies
        assert self.PUBLIC in bodies

    @pytest.mark.asyncio
    async def test_admin_list_sees_everything(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, priv = await self._seed(integration_session)
        admin = await _create_user(integration_session, "admin")
        await _add_ws_member(integration_session, ws, admin, "admin")
        service = _note_service(integration_session)

        result = await service.list_notes(
            ws, requester_user_id=admin, requester_role="admin"
        )
        assert result["total"] == 4  # private + draft + public + unscoped 전부


# --- NOTES status / update / delete / promote write IDOR --------------------


class TestNoteWritePathVisibilityIDOR:
    SECRET = "NONCE-WRITE-PRIVATE-4d8e"

    async def _seed_private_note(self, session: AsyncSession):
        owner = await _create_user(session, "owner")
        outsider = await _create_user(session, "outsider")
        ws = await _create_team_ws(session, owner)
        await _add_ws_member(session, ws, outsider, "member")
        project = await _create_project(session, ws, owner, "private")
        note = await _create_note(session, ws, project.id, owner, self.SECRET)
        return owner, outsider, ws, project, note

    @pytest.mark.asyncio
    async def test_non_member_embedding_status_404(
        self, integration_session: AsyncSession
    ):
        from src.notes.exceptions import NoteNotFoundError

        owner, outsider, ws, project, note = await self._seed_private_note(
            integration_session
        )
        service = _note_service(integration_session)

        with pytest.raises(NoteNotFoundError):
            await service.get_embedding_status(
                ws, note.id, requester_user_id=outsider, requester_role="member"
            )

    @pytest.mark.asyncio
    async def test_member_embedding_status_ok(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, project, note = await self._seed_private_note(
            integration_session
        )
        await _add_project_member(integration_session, project.id, ws, outsider)
        service = _note_service(integration_session)

        # ProjectMember → 정상 (status 응답)
        result = await service.get_embedding_status(
            ws, note.id, requester_user_id=outsider, requester_role="member"
        )
        assert result.status in ("pending", "completed")

    @pytest.mark.asyncio
    async def test_non_member_update_404(
        self, integration_session: AsyncSession
    ):
        from src.notes.exceptions import NoteNotFoundError

        owner, outsider, ws, project, note = await self._seed_private_note(
            integration_session
        )
        service = _note_service(integration_session)

        with pytest.raises(NoteNotFoundError):
            await service.update_note(
                note_id=note.id,
                workspace_id=ws,
                title="hijacked",
                requester_user_id=outsider,
                requester_role="member",
            )

    @pytest.mark.asyncio
    async def test_member_update_ok(self, integration_session: AsyncSession):
        owner, outsider, ws, project, note = await self._seed_private_note(
            integration_session
        )
        await _add_project_member(integration_session, project.id, ws, outsider)
        service = _note_service(integration_session)

        result = await service.update_note(
            note_id=note.id,
            workspace_id=ws,
            title="legit edit",
            requester_user_id=outsider,
            requester_role="member",
        )
        assert result["title"] == "legit edit"

    @pytest.mark.asyncio
    async def test_non_member_delete_404(
        self, integration_session: AsyncSession
    ):
        from src.notes.exceptions import NoteNotFoundError

        owner, outsider, ws, project, note = await self._seed_private_note(
            integration_session
        )
        pipeline = _note_pipeline(integration_session)

        with pytest.raises(NoteNotFoundError):
            await pipeline.delete_note_with_cleanup(
                note.id, ws, requester_user_id=outsider, requester_role="member"
            )

    @pytest.mark.asyncio
    async def test_member_delete_ok(self, integration_session: AsyncSession):
        owner, outsider, ws, project, note = await self._seed_private_note(
            integration_session
        )
        await _add_project_member(integration_session, project.id, ws, outsider)
        # BL-NOTE-DELETE-POLICY-1 (2026-08-02): 삭제가 작성자 본인 + admin 이상으로 좁혀졌다.
        # 이 테스트의 원 의도는 "ProjectMember 는 visibility 게이트를 통과한다" 이므로
        # 작성자 조건을 만족하는 노트(outsider 본인 작성)로 그 의도를 유지한다.
        # 비-작성자 ProjectMember 가 403 을 받는 것은 test_note_delete_authorship.py 가 덮는다.
        own_note = await _create_note(
            integration_session, ws, project.id, outsider, self.SECRET
        )
        pipeline = _note_pipeline(integration_session)

        # ProjectMember + 작성자 → 삭제 성공 (예외 없음)
        await pipeline.delete_note_with_cleanup(
            own_note.id, ws, requester_user_id=outsider, requester_role="member"
        )

    @pytest.mark.asyncio
    async def test_non_member_promote_404(
        self, integration_session: AsyncSession
    ):
        from fastapi import BackgroundTasks
        from sqlalchemy.ext.asyncio import async_sessionmaker

        from src.notes.exceptions import NoteNotFoundError
        from src.notes.repository import NoteRepository
        from src.notes.service import NoteService
        from src.projects.repository import ProjectRepository
        from src.workspaces.repository import WorkspaceRepository

        owner, outsider, ws, project, note = await self._seed_private_note(
            integration_session
        )
        # target team workspace (promote 대상) — outsider 가 멤버
        target_ws = await _create_team_ws(integration_session, outsider)

        bind = integration_session.get_bind()
        factory = async_sessionmaker(bind, class_=AsyncSession, expire_on_commit=False)
        service = NoteService(
            repo=NoteRepository(integration_session),
            project_repo=ProjectRepository(integration_session),
            workspace_repo=WorkspaceRepository(integration_session),
            session_factory=factory,
        )

        # 비-ProjectMember 가 private 노트를 promote 시도 → 404 (visibility 게이트 우선)
        with pytest.raises(NoteNotFoundError):
            await service.promote(
                note_id=note.id,
                source_workspace_id=ws,
                target_workspace_id=target_ws,
                promoted_by_user_id=outsider,
                background_tasks=BackgroundTasks(),
                requester_role="member",
            )


# --- MEETINGS list + status visibility --------------------------------------


class TestMeetingListVisibilityIDOR:
    SECRET = "NONCE-MLIST-PRIVATE-7b91"

    async def _seed(self, session: AsyncSession):
        owner = await _create_user(session, "owner")
        outsider = await _create_user(session, "outsider")
        ws = await _create_team_ws(session, owner)
        await _add_ws_member(session, ws, outsider, "member")
        priv = await _create_project(session, ws, owner, "private")
        priv_meeting = await _create_meeting_in_project(
            session, ws, priv, owner, self.SECRET
        )
        # 링크 없는 회의 (워크스페이스 레벨 — 누구나)
        from src.meetings.models import Meeting

        open_meeting = Meeting(
            workspace_id=ws,
            title="open",
            file_key=f"uploads/{uuid.uuid4().hex}.mp3",
            created_by_id=owner,
            status="completed",
        )
        session.add(open_meeting)
        await session.flush()
        return owner, outsider, ws, priv, priv_meeting, open_meeting

    @pytest.mark.asyncio
    async def test_non_member_list_excludes_private_linked(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, priv, priv_m, open_m = await self._seed(
            integration_session
        )
        service = _meeting_service(integration_session)

        result = await service.list_meetings(
            ws, requester_user_id=outsider, requester_role="member"
        )
        ids = {item["id"] for item in result["items"]}
        # private-linked 회의 제외, 링크 없는 회의는 포함
        assert str(priv_m.id) not in ids
        assert str(open_m.id) in ids
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_member_list_includes_private_linked(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, priv, priv_m, open_m = await self._seed(
            integration_session
        )
        await _add_project_member(integration_session, priv.id, ws, outsider)
        service = _meeting_service(integration_session)

        result = await service.list_meetings(
            ws, requester_user_id=outsider, requester_role="member"
        )
        ids = {item["id"] for item in result["items"]}
        assert str(priv_m.id) in ids
        assert str(open_m.id) in ids
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_admin_list_includes_private_linked(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, priv, priv_m, open_m = await self._seed(
            integration_session
        )
        admin = await _create_user(integration_session, "admin")
        await _add_ws_member(integration_session, ws, admin, "admin")
        service = _meeting_service(integration_session)

        result = await service.list_meetings(
            ws, requester_user_id=admin, requester_role="admin"
        )
        assert result["total"] == 2

    @pytest.mark.asyncio
    async def test_non_member_status_404(
        self, integration_session: AsyncSession
    ):
        from src.meetings.exceptions import MeetingNotFoundError

        owner, outsider, ws, priv, priv_m, open_m = await self._seed(
            integration_session
        )
        service = _meeting_service(integration_session)

        with pytest.raises(MeetingNotFoundError):
            await service.get_meeting_status(
                priv_m.id, ws, requester_user_id=outsider, requester_role="member"
            )

    @pytest.mark.asyncio
    async def test_member_status_ok(self, integration_session: AsyncSession):
        owner, outsider, ws, priv, priv_m, open_m = await self._seed(
            integration_session
        )
        await _add_project_member(integration_session, priv.id, ws, outsider)
        service = _meeting_service(integration_session)

        result = await service.get_meeting_status(
            priv_m.id, ws, requester_user_id=outsider, requester_role="member"
        )
        assert result["status"] == "completed"


# --- CAND-E: sourceId-less cache hit bypass (real RagService.ask seam) -------


def _rag_service_with_cache(cache_hit: dict | None):
    """RagService 를 실제 인스턴스화하되, cache lookup(외부 DB seam)과 fresh 검색 seam만
    stub. bug point(ask 의 cache-hit 가드)는 실제 코드 그대로 실행된다.
    """
    from unittest.mock import AsyncMock, MagicMock

    from src.rag.service import RagService

    embedding_repo = MagicMock()
    embedding_repo.find_similar_cache = AsyncMock(return_value=cache_hit)
    # fresh 검색 path stub — fall-through 가 일어나면 호출됨 (빈 결과 → no-source done).
    embedding_repo.vector_search = AsyncMock(return_value=[])
    embedding_repo.text_search = AsyncMock(return_value=[])

    embedding_service = MagicMock()
    embedding_service.generate_embeddings = AsyncMock(return_value=[[0.0] * 1536])

    ai_service = MagicMock()

    svc = RagService(
        embedding_repo=embedding_repo,
        embedding_service=embedding_service,
        ai_service=ai_service,
    )
    # _advance_onboarding 는 cache-hit path 에서 호출됨 — DB 접근 stub.
    svc._advance_onboarding = AsyncMock()
    return svc, embedding_repo


async def _collect_events(svc, **kwargs) -> list[dict]:
    return [ev async for ev in svc.ask(**kwargs)]


class TestCandECacheBypass:
    """CAND-E completeness: sourceId 없는 cache hit 은 MISS 처리 → fresh 검색 fall-through.

    실제 RagService.ask 를 구동한다 (bug point 에 mock 없음). cache lookup / fresh 검색
    DB seam 만 stub — 가드는 실제 코드가 평가한다.
    """

    _ASK_KWARGS = dict(
        question="비밀이 뭐야?",
        workspace_id=uuid.uuid4(),
        requester_user_id=uuid.uuid4(),
        requester_role="member",
    )

    @pytest.mark.asyncio
    async def test_sourceid_less_cache_bypassed_to_fresh_path(self):
        # CAND-A fix 이전 캐시 — sourceId 키 없음 → cache MISS 처리되어 fresh 검색 실행.
        stale_cache = {
            "answer": "stale answer",
            "sources": [{"id": "chunk-1", "text": "x"}],
        }
        svc, repo = _rag_service_with_cache(stale_cache)

        events = await _collect_events(svc, **self._ASK_KWARGS)

        # fresh 검색 seam 이 호출됐어야 한다 (cache bypass 증명).
        repo.vector_search.assert_awaited_once()
        # done 이벤트의 cached=False (캐시 serve 안 함).
        done = next(e for e in events if e["event"] == "done")
        assert json.loads(done["data"])["cached"] is False
        # stale answer 가 토큰으로 흘러나오지 않았다.
        answer_tokens = [
            json.loads(e["data"]).get("token", "")
            for e in events
            if e["event"] == "answer"
        ]
        assert "stale answer" not in "".join(answer_tokens)

    @pytest.mark.asyncio
    async def test_mixed_sourceid_cache_bypassed(self):
        # 일부만 sourceId — 하나라도 부재면 MISS → fresh 검색.
        mixed_cache = {
            "answer": "mixed",
            "sources": [
                {"id": "c1", "sourceId": "m1"},
                {"id": "c2", "text": "no sourceId"},
            ],
        }
        svc, repo = _rag_service_with_cache(mixed_cache)

        await _collect_events(svc, **self._ASK_KWARGS)

        repo.vector_search.assert_awaited_once()  # bypass → fresh

    @pytest.mark.asyncio
    async def test_complete_cache_is_served(self):
        # fresh 검색이 부여한 sourceId 가 모두 있으면 정상 cache HIT (serve, fresh 미실행).
        fresh_cache = {
            "answer": "cached answer",
            "sources": [
                {"id": "c1", "sourceId": "m1"},
                {"id": "c2", "sourceId": "n2"},
            ],
        }
        svc, repo = _rag_service_with_cache(fresh_cache)

        events = await _collect_events(svc, **self._ASK_KWARGS)

        # cache HIT → fresh 검색 미실행 + cached=True + cached answer serve.
        repo.vector_search.assert_not_awaited()
        done = next(e for e in events if e["event"] == "done")
        assert json.loads(done["data"])["cached"] is True
        answer_tokens = [
            json.loads(e["data"]).get("token", "")
            for e in events
            if e["event"] == "answer"
        ]
        assert "cached answer" in "".join(answer_tokens)

    @pytest.mark.asyncio
    async def test_empty_sources_cache_is_served(self):
        # sources 빈 캐시는 all() == True → HIT (sourceId 누락 위험 없음, 회귀 방지).
        empty_cache = {"answer": "empty-src", "sources": []}
        svc, repo = _rag_service_with_cache(empty_cache)

        events = await _collect_events(svc, **self._ASK_KWARGS)

        repo.vector_search.assert_not_awaited()
        done = next(e for e in events if e["event"] == "done")
        assert json.loads(done["data"])["cached"] is True


# --- MEETINGS multi-link (M2M) visibility — CAND-A completeness round 2 (codex) ---


class TestMeetingMultiLinkVisibilityIDOR:
    """회의가 public + private 프로젝트에 동시 링크된 경우: public 링크로 접근은
    허용하되, 비-멤버에게 private 링크의 존재/메타(list projectId 필터·detail projects)는
    노출하지 않아야 한다 (codex 재검증 finding)."""

    SECRET = "NONCE-MMULTI-9c2f"

    async def _seed(self, session: AsyncSession):
        owner = await _create_user(session, "mm-owner")
        outsider = await _create_user(session, "mm-outsider")
        ws = await _create_team_ws(session, owner)
        await _add_ws_member(session, ws, outsider, "member")
        pub = await _create_project(session, ws, owner, "public")
        priv = await _create_project(session, ws, owner, "private")
        # public 에 링크된 회의 생성 후 private 에도 추가 링크 (cross-link).
        meeting = await _create_meeting_in_project(session, ws, pub, owner, self.SECRET)
        from src.projects.models import MeetingProjectLink

        session.add(
            MeetingProjectLink(meeting_id=meeting.id, project_id=priv.id, workspace_id=ws)
        )
        await session.flush()
        return owner, outsider, ws, pub, priv, meeting

    @pytest.mark.asyncio
    async def test_list_filtered_by_inaccessible_private_returns_empty(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, pub, priv, meeting = await self._seed(integration_session)
        service = _meeting_service(integration_session)
        # 비-멤버가 private projectId 로 필터 → cross-link 회의 노출 금지 (빈 결과).
        result = await service.list_meetings(
            ws, project_id=priv.id, requester_user_id=outsider, requester_role="member"
        )
        assert result["items"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_list_filtered_by_public_includes_meeting(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, pub, priv, meeting = await self._seed(integration_session)
        service = _meeting_service(integration_session)
        # public 링크로 필터하면 정상 노출 (over-block 회귀 방지).
        result = await service.list_meetings(
            ws, project_id=pub.id, requester_user_id=outsider, requester_role="member"
        )
        ids = {i["id"] for i in result["items"]}
        assert str(meeting.id) in ids

    @pytest.mark.asyncio
    async def test_detail_hides_inaccessible_linked_project(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, pub, priv, meeting = await self._seed(integration_session)
        service = _meeting_service(integration_session)
        # public 링크로 detail 접근은 허용되지만 private 링크 메타는 가려져야 함.
        result = await service.get_meeting_detail(
            meeting.id, ws, requester_user_id=outsider, requester_role="member"
        )
        proj_ids = {p["id"] for p in result["projects"]}
        assert str(pub.id) in proj_ids
        assert str(priv.id) not in proj_ids

    @pytest.mark.asyncio
    async def test_owner_detail_sees_all_links(
        self, integration_session: AsyncSession
    ):
        owner, outsider, ws, pub, priv, meeting = await self._seed(integration_session)
        service = _meeting_service(integration_session)
        result = await service.get_meeting_detail(
            meeting.id, ws, requester_user_id=owner, requester_role="owner"
        )
        proj_ids = {p["id"] for p in result["projects"]}
        assert str(pub.id) in proj_ids and str(priv.id) in proj_ids
