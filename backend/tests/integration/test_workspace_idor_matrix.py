# Sprint 19 BUG-C01-EXT v3 회귀 매트릭스 — workspace-scoped endpoint 45개 전수 IDOR 가드
"""Sprint 19 PR #1 회귀 테스트 골격 (TDD failing).

배경:
- Sprint 18 BUG-C01 fix (workspaces/router.py:35 require_viewer 4 LOC) 후속
- 2차 codex review (VERDICT: BLOCK, 2026-05-17): CONTEXT-MAP.md:208 헌법 I-9
  "모든 Repository workspace filter 강제" 위반. 4 도메인을 넘어 30+ endpoint에서
  service/repo가 workspace_id 미전달 → repo가 ID-only fetch → cross-tenant leak 잠재.
- PR #1 진입 직전 ripgrep 매트릭스 lock-in (2026-05-17): 총 45 endpoint.

매트릭스 (45 endpoint, 도메인별):
- projects     11  (router.py:47,65,80,98,121,133,150,161,171,185,196)
- meetings      6  (router.py:25,46,69,79,90,106)
- notes         6  (router.py:29,42,53,70,93,117)
- memory        5  (router.py:56,94,107,118,133)
- workspaces    8  (main 2 + member 3 + invite 3)
- inbox         3  (router.py:25,41,52)
- actions       3  (router.py:27,39,59)
- upload        2  (router.py:31,46)
- rag           1  (router.py:24)
- 합계         45

검증 기준 (TDD 실패 → PR #1 도메인별 fix → PASS, Codex F-3/F-4 반영):
1. require_viewer 통과 후 service mock 호출 시 workspace_id 정확 값 전달
   (kwargs.get("workspace_id") == workspace_a_id 또는 positional 정확 위치, Codex F-3)
2. cross-tenant resource_id 시도 → 404
   (path workspace 안에 없는 resource = NotFound, Codex F-4 lock-in)
3. cross-tenant secondary FK (project_id / meeting_id / assignee_id) 시도 → 404
   (notes update / inbox classify / actions update, Codex F-2 Critical)
4. 응답 시간 timing side-channel 검증은 nightly heavy spec 으로 격하 (Codex F-4)

본 골격은 PR #1 진입점. 도메인별 commit에서 TODO 마커를 채워나간다.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.rbac import require_viewer
from src.common.database import get_async_session
from src.main import app
from src.workspaces.models import WorkspaceMember


# --- 매트릭스 정의 ---------------------------------------------------------

# 45 endpoint 매트릭스 — PR #1 도메인별 commit 시 도메인 단위로 활성화
WORKSPACE_SCOPED_ENDPOINTS: dict[str, list[dict]] = {
    "meetings": [
        # (method, path 템플릿, service method, 검증 인자 키)
        {"method": "GET", "path": "/api/v1/workspaces/{ws}/meetings/{rid}",
         "service": "get_meeting_detail", "rid_field": "meeting_id"},
        {"method": "GET", "path": "/api/v1/workspaces/{ws}/meetings/{rid}/export",
         "service": "export_meeting", "rid_field": "meeting_id"},
        {"method": "GET", "path": "/api/v1/workspaces/{ws}/meetings/{rid}/status",
         "service": "get_meeting_status", "rid_field": "meeting_id"},
        # TODO PR #1 meetings commit: list_meetings + POST upload + processing endpoints
    ],
    "notes": [
        # TODO PR #1 notes commit: get/export/patch/delete 6 endpoint
    ],
    "inbox": [
        # TODO PR #1 inbox commit: 3 endpoint
    ],
    "actions": [
        # TODO PR #1 actions commit: 3 endpoint
    ],
    "projects": [
        # TODO PR #1 projects commit: 11 endpoint (가장 큰 분산)
    ],
    "memory": [
        # TODO PR #1 memory commit: 5 endpoint (2차 codex 누락 발견 — matrix lock-in 추가)
    ],
    "rag": [
        # TODO PR #1 rag commit: 1 endpoint (ask)
    ],
    "workspaces": [
        # TODO PR #1 workspaces commit: main 2 + member 3 + invite 3
    ],
    "upload": [
        # TODO PR #1 upload commit: 2 endpoint
    ],
}


# --- 공용 fixture ----------------------------------------------------------

@pytest_asyncio.fixture
async def client():
    mock_session = AsyncMock()
    app.dependency_overrides[get_async_session] = lambda: mock_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def workspace_a_id() -> uuid.UUID:
    return uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


@pytest.fixture
def workspace_b_id() -> uuid.UUID:
    return uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


@pytest.fixture
def user_a() -> User:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.clerk_id = "user_a"
    user.display_name = "User A"
    user.email = "a@kairos.test"
    user.avatar_url = None
    return user


@pytest.fixture
def member_a(user_a, workspace_a_id) -> WorkspaceMember:
    member = MagicMock(spec=WorkspaceMember)
    member.user_id = user_a.id
    member.workspace_id = workspace_a_id
    member.role = "member"
    return member


# --- 도메인별 failing test (PR #1 진입 시 도메인 commit으로 채움) -------------

class TestMeetingsIDORMatrix:
    """meetings 도메인 6 endpoint — service workspace_id 인자 전달 검증.

    현재 상태 (PR #1 진입 전): meetings/service.py:130,136,142 의
    get_meeting_detail / export_meeting / get_meeting_status 가 workspace_id 미수신.
    본 test는 service mock 호출 시 workspace_id kwarg 부재로 TDD failing.
    PR #1 meetings commit 후 PASS.
    """

    @pytest.mark.asyncio
    async def test_get_meeting_detail_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """BUG-C01-EXT v3 meetings #1: GET /meetings/{id} → service에 workspace_id 전달.

        Failing 조건: service.get_meeting_detail 호출 시 kwargs에 workspace_id 없음.
        Fix: meetings/service.py get_meeting_detail(meeting_id, workspace_id)
             + meetings/router.py:82 호출 시 workspace_id 전달.
        """
        from src.meetings.dependencies import get_meeting_service

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_viewer] = lambda: member_a

        meeting_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.get_meeting_detail.return_value = {
            "id": str(meeting_id),
            "workspaceId": str(workspace_a_id),
        }
        app.dependency_overrides[get_meeting_service] = lambda: mock_service

        response = await client.get(
            f"/api/v1/workspaces/{workspace_a_id}/meetings/{meeting_id}",
            headers={"Authorization": "Bearer user_a_token"},
        )

        assert response.status_code == 200
        # 핵심 assertion (Codex F-3 강한 패턴): 값 동치 비교
        call_args = mock_service.get_meeting_detail.call_args
        kwargs = call_args.kwargs if call_args else {}
        args = call_args.args if call_args else ()
        workspace_id_seen = kwargs.get("workspace_id") or (
            args[1] if len(args) > 1 else None
        )
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 meetings #1 (Codex F-3): "
            f"service.get_meeting_detail 호출 시 workspace_id 정확 값 미전달. "
            f"기대={workspace_a_id} 실제={workspace_id_seen} "
            f"kwargs={kwargs} args={args}"
        )

    @pytest.mark.asyncio
    async def test_export_meeting_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """meetings #2: GET /meetings/{id}/export — service.export_meeting workspace_id 정확 값 (Codex F-3)."""
        from src.meetings.dependencies import get_meeting_service

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_viewer] = lambda: member_a

        meeting_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.export_meeting.return_value = ("data", "f.md", "text/markdown; charset=utf-8")
        app.dependency_overrides[get_meeting_service] = lambda: mock_service

        response = await client.get(
            f"/api/v1/workspaces/{workspace_a_id}/meetings/{meeting_id}/export?format=md",
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 200
        call_args = mock_service.export_meeting.call_args
        kwargs = call_args.kwargs if call_args else {}
        args = call_args.args if call_args else ()
        workspace_id_seen = kwargs.get("workspace_id") or (
            args[1] if len(args) > 1 else None
        )
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 meetings #2 (Codex F-3): export_meeting workspace_id 정확 값 미전달. "
            f"기대={workspace_a_id} 실제={workspace_id_seen} kwargs={kwargs} args={args}"
        )

    @pytest.mark.asyncio
    async def test_get_meeting_status_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """meetings #3: GET /meetings/{id}/status — service.get_meeting_status workspace_id 정확 값 (Codex F-3)."""
        from src.meetings.dependencies import get_meeting_service

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_viewer] = lambda: member_a

        meeting_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.get_meeting_status.return_value = {"status": "ready", "errorMessage": None}
        app.dependency_overrides[get_meeting_service] = lambda: mock_service

        response = await client.get(
            f"/api/v1/workspaces/{workspace_a_id}/meetings/{meeting_id}/status",
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 200
        call_args = mock_service.get_meeting_status.call_args
        kwargs = call_args.kwargs if call_args else {}
        args = call_args.args if call_args else ()
        workspace_id_seen = kwargs.get("workspace_id") or (
            args[1] if len(args) > 1 else None
        )
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 meetings #3 (Codex F-3): get_meeting_status workspace_id 정확 값 미전달. "
            f"기대={workspace_a_id} 실제={workspace_id_seen} kwargs={kwargs} args={args}"
        )

    @pytest.mark.asyncio
    async def test_meeting_repository_find_by_id_requires_workspace_id(self):
        """Codex F-1 anchor: MeetingRepository.find_by_id 시그니처 workspace_id 필수."""
        import inspect
        from src.meetings.repository import MeetingRepository

        sig = inspect.signature(MeetingRepository.find_by_id)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: MeetingRepository.find_by_id 시그니처에 "
            f"workspace_id 필수. 현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_meeting_pipeline_process_meeting_requires_workspace_id(self):
        """Codex F-1 Critical anchor: pipeline 진입점 process_meeting workspace_id 필수."""
        import inspect
        from src.meetings.pipeline_service import MeetingPipelineService

        sig = inspect.signature(MeetingPipelineService.process_meeting)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1 (Critical): MeetingPipelineService.process_meeting "
            f"진입점 시그니처에 workspace_id 필수. 현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_meeting_pipeline_capture_text_requires_workspace_id(self):
        """Codex F-1 anchor: pipeline 진입점 capture_text workspace_id 필수."""
        import inspect
        from src.meetings.pipeline_service import MeetingPipelineService

        sig = inspect.signature(MeetingPipelineService.capture_text)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: MeetingPipelineService.capture_text "
            f"진입점 시그니처에 workspace_id 필수. 현재 params={list(sig.parameters)}"
        )


class TestNotesIDORMatrix:
    """notes 도메인 6 endpoint + secondary FK (Codex F-2) + pipeline 옵션 A (Codex H2).

    실제 fix 필요 endpoint:
    - GET /{id} (get_note), GET /{id}/export, PATCH /{id} (update_note), DELETE /{id}
    - list_notes / create_note 는 이미 workspace_id 전달 중 (회귀 PASS 확인)
    - F-2 anchor: update_note 가 cross-tenant project_id 거부 → 404
    """

    @pytest.mark.asyncio
    async def test_get_note_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """notes #1: GET /notes/{id} — service.get_note workspace_id 정확 값 (Codex F-3)."""
        from src.notes.dependencies import get_note_service

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_viewer] = lambda: member_a

        note_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.get_note.return_value = {
            "id": str(note_id), "workspaceId": str(workspace_a_id),
        }
        app.dependency_overrides[get_note_service] = lambda: mock_service

        response = await client.get(
            f"/api/v1/workspaces/{workspace_a_id}/notes/{note_id}",
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 200
        call_args = mock_service.get_note.call_args
        kwargs = call_args.kwargs if call_args else {}
        args = call_args.args if call_args else ()
        workspace_id_seen = kwargs.get("workspace_id") or (
            args[1] if len(args) > 1 else None
        )
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 notes #1 (Codex F-3): get_note workspace_id 정확 값 미전달. "
            f"기대={workspace_a_id} 실제={workspace_id_seen} kwargs={kwargs} args={args}"
        )

    @pytest.mark.asyncio
    async def test_export_note_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """notes #2: GET /notes/{id}/export — workspace_id 정확 값 (Codex F-3)."""
        from src.notes.dependencies import get_note_service

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_viewer] = lambda: member_a

        note_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.export_note.return_value = ("data", "f.md", "text/markdown; charset=utf-8")
        app.dependency_overrides[get_note_service] = lambda: mock_service

        response = await client.get(
            f"/api/v1/workspaces/{workspace_a_id}/notes/{note_id}/export?format=md",
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 200
        call_args = mock_service.export_note.call_args
        kwargs = call_args.kwargs if call_args else {}
        args = call_args.args if call_args else ()
        workspace_id_seen = kwargs.get("workspace_id") or (
            args[1] if len(args) > 1 else None
        )
        assert workspace_id_seen == workspace_a_id

    @pytest.mark.asyncio
    async def test_update_note_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """notes #3: PATCH /notes/{id} — workspace_id 정확 값 (Codex F-3)."""
        from src.notes.dependencies import get_note_service, get_note_pipeline_service

        app.dependency_overrides[get_current_user] = lambda: user_a
        # update_note 는 require_member 통과 — member_a 그대로 활용
        from src.auth.rbac import require_member
        app.dependency_overrides[require_member] = lambda: member_a

        note_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.update_note.return_value = {
            "id": str(note_id), "workspaceId": str(workspace_a_id),
        }
        mock_pipeline = AsyncMock()
        app.dependency_overrides[get_note_service] = lambda: mock_service
        app.dependency_overrides[get_note_pipeline_service] = lambda: mock_pipeline

        response = await client.patch(
            f"/api/v1/workspaces/{workspace_a_id}/notes/{note_id}",
            json={"title": "new title"},
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 200
        call_args = mock_service.update_note.call_args
        kwargs = call_args.kwargs if call_args else {}
        workspace_id_seen = kwargs.get("workspace_id")
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 notes #3 (Codex F-3): update_note workspace_id 미전달. "
            f"kwargs={kwargs}"
        )

    @pytest.mark.asyncio
    async def test_update_note_rejects_cross_tenant_project_id(
        self, client, user_a, member_a, workspace_a_id
    ):
        """Codex F-2 Critical: update_note 가 cross-workspace project_id 거부 → 404."""
        from src.notes.dependencies import get_note_service, get_note_pipeline_service
        from src.projects.exceptions import ProjectNotFoundError
        from src.auth.rbac import require_member

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a

        note_id = uuid.uuid4()
        foreign_project_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.update_note.side_effect = ProjectNotFoundError()
        mock_pipeline = AsyncMock()
        app.dependency_overrides[get_note_service] = lambda: mock_service
        app.dependency_overrides[get_note_pipeline_service] = lambda: mock_pipeline

        response = await client.patch(
            f"/api/v1/workspaces/{workspace_a_id}/notes/{note_id}",
            json={"projectId": str(foreign_project_id)},
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 404, (
            f"BUG-C01-EXT v3 notes F-2 Critical: update_note 가 cross-tenant project_id 거부 안 함. "
            f"응답={response.status_code} body={response.text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_delete_note_passes_workspace_id_to_pipeline(
        self, client, user_a, member_a, workspace_a_id
    ):
        """notes #4: DELETE /notes/{id} — pipeline.delete_note_with_cleanup workspace_id (Codex F-2 옵션 A)."""
        from src.notes.dependencies import get_note_pipeline_service
        from src.auth.rbac import require_member

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a

        note_id = uuid.uuid4()
        mock_pipeline = AsyncMock()
        mock_pipeline.delete_note_with_cleanup.return_value = None
        app.dependency_overrides[get_note_pipeline_service] = lambda: mock_pipeline

        response = await client.delete(
            f"/api/v1/workspaces/{workspace_a_id}/notes/{note_id}",
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 204
        call_args = mock_pipeline.delete_note_with_cleanup.call_args
        kwargs = call_args.kwargs if call_args else {}
        args = call_args.args if call_args else ()
        workspace_id_seen = kwargs.get("workspace_id") or (
            args[1] if len(args) > 1 else None
        )
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 notes #4 옵션 A: delete_note_with_cleanup workspace_id 미전달. "
            f"call_args={call_args}"
        )

    @pytest.mark.asyncio
    async def test_note_repository_find_by_id_requires_workspace_id(self):
        """Codex F-1 anchor: NoteRepository.find_by_id 시그니처."""
        import inspect
        from src.notes.repository import NoteRepository

        sig = inspect.signature(NoteRepository.find_by_id)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: NoteRepository.find_by_id workspace_id 필수. "
            f"params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_pipeline_delete_note_with_cleanup_requires_workspace_id(self):
        """Codex H2 / 옵션 A anchor: pipeline 시그니처 자체 변경."""
        import inspect
        from src.notes.pipeline_service import NotePipelineService

        sig = inspect.signature(NotePipelineService.delete_note_with_cleanup)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 옵션 A: delete_note_with_cleanup workspace_id 필수. "
            f"params={list(sig.parameters)}"
        )


class TestInboxIDORMatrix:
    """inbox 도메인 3 endpoint + secondary FK (Codex F-2).

    실제 fix 필요: classify (workspace_id + project_ids F-2), dismiss (workspace_id).
    list_inbox 는 이미 workspace_id 전달 중 — 회귀 PASS 확인.
    """

    @pytest.mark.asyncio
    async def test_classify_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """inbox #1: POST /inbox/{id}/classify — workspace_id 정확 값 (Codex F-3)."""
        from src.inbox.dependencies import get_inbox_service
        from src.auth.rbac import require_member

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a

        inbox_id = uuid.uuid4()
        project_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.classify.return_value = {
            "id": str(inbox_id), "workspaceId": str(workspace_a_id),
            "linkedProjects": [],
        }
        app.dependency_overrides[get_inbox_service] = lambda: mock_service

        response = await client.post(
            f"/api/v1/workspaces/{workspace_a_id}/inbox/{inbox_id}/classify",
            json={"projectIds": [str(project_id)]},
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 200
        call_args = mock_service.classify.call_args
        kwargs = call_args.kwargs if call_args else {}
        args = call_args.args if call_args else ()
        workspace_id_seen = kwargs.get("workspace_id") or (
            args[1] if len(args) > 1 else None
        )
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 inbox #1 (Codex F-3): classify workspace_id 미전달. "
            f"call_args={call_args}"
        )

    @pytest.mark.asyncio
    async def test_classify_rejects_cross_tenant_project_ids(
        self, client, user_a, member_a, workspace_a_id
    ):
        """Codex F-2 Critical: classify 가 cross-workspace project_id 거부 → 404."""
        from src.inbox.dependencies import get_inbox_service
        from src.projects.exceptions import ProjectNotFoundError
        from src.auth.rbac import require_member

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a

        inbox_id = uuid.uuid4()
        foreign_project_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.classify.side_effect = ProjectNotFoundError()
        app.dependency_overrides[get_inbox_service] = lambda: mock_service

        response = await client.post(
            f"/api/v1/workspaces/{workspace_a_id}/inbox/{inbox_id}/classify",
            json={"projectIds": [str(foreign_project_id)]},
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 404, (
            f"BUG-C01-EXT v3 inbox F-2 Critical: classify 가 cross-tenant project_id 거부 안 함. "
            f"응답={response.status_code} body={response.text[:200]}"
        )

    @pytest.mark.asyncio
    async def test_dismiss_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """inbox #2: POST /inbox/{id}/dismiss — workspace_id 정확 값 (Codex F-3)."""
        from src.inbox.dependencies import get_inbox_service
        from src.auth.rbac import require_member

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a

        inbox_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.dismiss.return_value = {
            "id": str(inbox_id), "workspaceId": str(workspace_a_id),
        }
        app.dependency_overrides[get_inbox_service] = lambda: mock_service

        response = await client.post(
            f"/api/v1/workspaces/{workspace_a_id}/inbox/{inbox_id}/dismiss",
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 200
        call_args = mock_service.dismiss.call_args
        kwargs = call_args.kwargs if call_args else {}
        args = call_args.args if call_args else ()
        workspace_id_seen = kwargs.get("workspace_id") or (
            args[1] if len(args) > 1 else None
        )
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 inbox #2 (Codex F-3): dismiss workspace_id 미전달. "
            f"call_args={call_args}"
        )

    @pytest.mark.asyncio
    async def test_inbox_repository_find_by_id_requires_workspace_id(self):
        """Codex F-1 anchor: InboxRepository.find_by_id 시그니처."""
        import inspect
        from src.inbox.repository import InboxRepository

        sig = inspect.signature(InboxRepository.find_by_id)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: InboxRepository.find_by_id workspace_id 필수. "
            f"params={list(sig.parameters)}"
        )


class TestActionsIDORMatrix:
    """actions 도메인 3 endpoint + 3 secondary FK (Codex F-2 가장 큰 분량).

    실제 fix 필요: update_action_item (workspace_id + project/meeting/assignee F-2).
    list_action_items / create_action_item 는 이미 workspace_id 받음 — 회귀 확인.
    """

    @pytest.mark.asyncio
    async def test_update_action_item_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """actions #1: PATCH /action-items/{id} — workspace_id 정확 값 (Codex F-3)."""
        from src.actions.dependencies import get_action_service
        from src.auth.rbac import require_member

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a

        action_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.update_action_item.return_value = {
            "id": str(action_id), "workspaceId": str(workspace_a_id),
        }
        app.dependency_overrides[get_action_service] = lambda: mock_service

        response = await client.patch(
            f"/api/v1/workspaces/{workspace_a_id}/action-items/{action_id}",
            json={"title": "new title"},
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 200
        call_args = mock_service.update_action_item.call_args
        kwargs = call_args.kwargs if call_args else {}
        workspace_id_seen = kwargs.get("workspace_id")
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 actions #1 (Codex F-3): update_action_item workspace_id 미전달. "
            f"kwargs={kwargs}"
        )

    @pytest.mark.asyncio
    async def test_update_action_item_rejects_cross_tenant_project_id(
        self, client, user_a, member_a, workspace_a_id
    ):
        """Codex F-2 Critical: update_action_item 의 project_id cross-workspace 거부 → 404."""
        from src.actions.dependencies import get_action_service
        from src.projects.exceptions import ProjectNotFoundError
        from src.auth.rbac import require_member

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a

        action_id = uuid.uuid4()
        foreign_project_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.update_action_item.side_effect = ProjectNotFoundError()
        app.dependency_overrides[get_action_service] = lambda: mock_service

        response = await client.patch(
            f"/api/v1/workspaces/{workspace_a_id}/action-items/{action_id}",
            json={"projectId": str(foreign_project_id)},
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_action_item_rejects_cross_tenant_meeting_id(
        self, client, user_a, member_a, workspace_a_id
    ):
        """Codex F-2 Critical: update_action_item 의 meeting_id cross-workspace 거부 → 404."""
        from src.actions.dependencies import get_action_service
        from src.meetings.exceptions import MeetingNotFoundError
        from src.auth.rbac import require_member

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a

        action_id = uuid.uuid4()
        foreign_meeting_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.update_action_item.side_effect = MeetingNotFoundError()
        app.dependency_overrides[get_action_service] = lambda: mock_service

        response = await client.patch(
            f"/api/v1/workspaces/{workspace_a_id}/action-items/{action_id}",
            json={"meetingId": str(foreign_meeting_id)},
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_action_item_rejects_cross_tenant_assignee_id(
        self, client, user_a, member_a, workspace_a_id
    ):
        """Codex F-2 Critical: update_action_item 의 assignee_id (다른 workspace 멤버) 거부 → 404."""
        from src.actions.dependencies import get_action_service
        from src.common.exceptions import NotFoundError
        from src.auth.rbac import require_member

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a

        action_id = uuid.uuid4()
        foreign_user_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.update_action_item.side_effect = NotFoundError("워크스페이스 멤버")
        app.dependency_overrides[get_action_service] = lambda: mock_service

        response = await client.patch(
            f"/api/v1/workspaces/{workspace_a_id}/action-items/{action_id}",
            json={"assigneeId": str(foreign_user_id)},
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_action_repository_find_by_id_requires_workspace_id(self):
        """Codex F-1 anchor: ActionItemRepository.find_by_id 시그니처."""
        import inspect
        from src.actions.repository import ActionItemRepository

        sig = inspect.signature(ActionItemRepository.find_by_id)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: ActionItemRepository.find_by_id workspace_id 필수. "
            f"params={list(sig.parameters)}"
        )


class TestProjectsIDORMatrix:
    """projects 도메인 11 endpoint — TODO PR #1 projects commit (가장 큰 분산)."""

    @pytest.mark.skip(reason="PR #1 projects commit 진입 시 활성화")
    def test_placeholder(self):
        pass


class TestMemoryIDORMatrix:
    """memory 도메인 5 endpoint — TODO PR #1 memory commit (matrix lock-in 추가)."""

    @pytest.mark.skip(reason="PR #1 memory commit 진입 시 활성화")
    def test_placeholder(self):
        pass


class TestRagIDORMatrix:
    """rag 도메인 1 endpoint (ask) — TODO PR #1 rag commit (matrix lock-in 추가)."""

    @pytest.mark.skip(reason="PR #1 rag commit 진입 시 활성화")
    def test_placeholder(self):
        pass


class TestWorkspacesIDORMatrix:
    """workspaces main 2 + member 3 + invite 3 = 8 endpoint — TODO PR #1 workspaces commit.

    `member_router.py:23,35,51` + `invite_router.py:37,54,65` + `invite_service.py:222,243,119`
    `find_member_by_id(member_id, workspace_id)` / `find_invite_by_id(invite_id, workspace_id)` 변경.
    """

    @pytest.mark.skip(reason="PR #1 workspaces commit 진입 시 활성화")
    def test_placeholder(self):
        pass


class TestUploadIDORMatrix:
    """upload 도메인 2 endpoint — TODO PR #1 upload commit.

    file_key path 패턴 (BUG-UPL-OWN)은 PR #4에서 별도. PR #1은 workspace_id 시그니처만.
    """

    @pytest.mark.skip(reason="PR #1 upload commit 진입 시 활성화")
    def test_placeholder(self):
        pass
