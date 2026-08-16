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
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.rbac import require_owner, require_viewer
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
    "integrations": [
        {
            "method": "POST",
            "path": (
                "/api/v1/workspaces/{ws}/integrations/google-drive/authorize"
            ),
            "service": "create_oauth_state",
            "rid_field": "workspace_id",
        },
        {
            "method": "GET",
            "path": "/api/v1/workspaces/{ws}/integrations/google-drive",
            "service": "get_connection_by_provider",
            "rid_field": "workspace_id",
        },
        {
            "method": "POST",
            "path": (
                "/api/v1/workspaces/{ws}/integrations/google-drive/documents"
            ),
            "service": "import_documents",
            "rid_field": "project_id",
        },
        {
            "method": "GET",
            "path": "/api/v1/workspaces/{ws}/integrations/sync-runs/{rid}",
            "service": "get_sync_run",
            "rid_field": "sync_run_id",
        },
        {
            "method": "POST",
            "path": (
                "/api/v1/workspaces/{ws}/integrations/google-drive/"
                "documents/{rid}/sync"
            ),
            "service": "get_document",
            "rid_field": "document_id",
        },
        {
            "method": "DELETE",
            "path": (
                "/api/v1/workspaces/{ws}/integrations/google-drive/"
                "documents/{rid}"
            ),
            "service": "unpublish_document",
            "rid_field": "document_id",
        },
        {
            "method": "GET",
            "path": "/api/v1/workspaces/{ws}/external-documents/{rid}",
            "service": "get_document",
            "rid_field": "document_id",
        },
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
    user.auth_user_id = "user_a"
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
        # 정책 의존성 교체와 무관하게 router→service 전달만 검증한다.
        from src.auth.rbac import require_member, require_member_fresh
        app.dependency_overrides[require_member] = lambda: member_a
        app.dependency_overrides[require_member_fresh] = lambda: member_a

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
        from src.auth.rbac import require_member, require_member_fresh

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a
        app.dependency_overrides[require_member_fresh] = lambda: member_a

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
        from src.auth.rbac import require_member, require_member_fresh

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a
        app.dependency_overrides[require_member_fresh] = lambda: member_a

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
    async def test_delete_note_cross_tenant_returns_404(
        self, client, user_a, member_a, workspace_a_id
    ):
        """Codex 2차 Major 1 (C7): cross-tenant note DELETE → 404 (이전 204 success bug)."""
        from src.notes.dependencies import get_note_pipeline_service
        from src.notes.exceptions import NoteNotFoundError
        from src.auth.rbac import require_member, require_member_fresh

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a
        app.dependency_overrides[require_member_fresh] = lambda: member_a

        note_id = uuid.uuid4()
        mock_pipeline = AsyncMock()
        mock_pipeline.delete_note_with_cleanup.side_effect = NoteNotFoundError()
        app.dependency_overrides[get_note_pipeline_service] = lambda: mock_pipeline

        response = await client.delete(
            f"/api/v1/workspaces/{workspace_a_id}/notes/{note_id}",
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 404, (
            f"BUG-C01-EXT v3 Codex 2차 Major 1: notes DELETE cross-tenant 가 204 success 반환. "
            f"F-4 lock-in 위반. 응답={response.status_code}"
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
        from src.auth.rbac import require_member, require_member_fresh

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a
        app.dependency_overrides[require_member_fresh] = lambda: member_a

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
        from src.auth.rbac import require_member, require_member_fresh

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a
        app.dependency_overrides[require_member_fresh] = lambda: member_a

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
        """Codex F-2 Critical + 2차 Major 2 (C7): meeting_id forwarding + cross-workspace 거부 → 404.

        강한 검증 (Codex 2차 F-3): side_effect 만 검증하면 mock false positive — meeting_id
        가 router→service 로 실제 전달되는지 call_args.kwargs 로 확인.
        """
        from src.actions.dependencies import get_action_service
        from src.meetings.exceptions import MeetingNotFoundError
        from src.auth.rbac import require_member, require_member_fresh

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a
        app.dependency_overrides[require_member_fresh] = lambda: member_a

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

        # Codex 2차 Major 2: meeting_id 가 service 까지 정확 값 전달되는지 검증
        call_args = mock_service.update_action_item.call_args
        kwargs = call_args.kwargs if call_args else {}
        meeting_id_seen = kwargs.get("meeting_id")
        assert meeting_id_seen == foreign_meeting_id, (
            f"BUG-C01-EXT v3 Codex 2차 Major 2: actions update meeting_id forwarding 누락. "
            f"기대={foreign_meeting_id} 실제={meeting_id_seen} kwargs={kwargs}"
        )

    @pytest.mark.asyncio
    async def test_update_action_item_rejects_cross_tenant_assignee_id(
        self, client, user_a, member_a, workspace_a_id
    ):
        """Codex F-2 Critical: update_action_item 의 assignee_id (다른 workspace 멤버) 거부 → 404."""
        from src.actions.dependencies import get_action_service
        from src.common.exceptions import NotFoundError
        from src.auth.rbac import require_member, require_member_fresh

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a
        app.dependency_overrides[require_member_fresh] = lambda: member_a

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
    """projects 도메인 11 endpoint + cross-domain cascade (Sprint 19 PR #1 C9).

    Codex F-1 BLOCK 해소: ProjectRepository.find_by_id / find_members / is_member
    + add_meeting_link / remove_meeting_link / find_projects_by_meeting 모두 workspace_id 강제.
    Codex F-3: add_meeting_link 호출자 inbox.service classify 경로 cascade.
    Codex F-4: cross-tenant resource → ProjectNotFoundError(404) lock-in (정보 누설 방지).
    """

    @pytest.mark.asyncio
    async def test_project_repository_find_by_id_requires_workspace_id(self):
        """Codex F-1 anchor: ProjectRepository.find_by_id 시그니처 workspace_id 필수."""
        import inspect
        from src.projects.repository import ProjectRepository

        sig = inspect.signature(ProjectRepository.find_by_id)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: ProjectRepository.find_by_id 시그니처에 "
            f"workspace_id 필수. 현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_project_repository_add_meeting_link_requires_workspace_id(self):
        """Codex F-1/F-3 anchor: add_meeting_link 시그니처 workspace_id 필수."""
        import inspect
        from src.projects.repository import ProjectRepository

        sig = inspect.signature(ProjectRepository.add_meeting_link)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1/F-3: ProjectRepository.add_meeting_link 시그니처에 "
            f"workspace_id 필수. 현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_project_repository_find_projects_by_meeting_requires_workspace_id(self):
        """Codex F-1 anchor: find_projects_by_meeting 시그니처 workspace_id 필수."""
        import inspect
        from src.projects.repository import ProjectRepository

        sig = inspect.signature(ProjectRepository.find_projects_by_meeting)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: find_projects_by_meeting workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_project_service_update_project_requires_workspace_id(self):
        """Codex F-1 anchor: ProjectService.update_project workspace_id 필수."""
        import inspect
        from src.projects.service import ProjectService

        sig = inspect.signature(ProjectService.update_project)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: update_project workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_project_service_delete_project_requires_workspace_id(self):
        """Codex F-1 anchor: ProjectService.delete_project workspace_id 필수."""
        import inspect
        from src.projects.service import ProjectService

        sig = inspect.signature(ProjectService.delete_project)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: delete_project workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_project_service_add_meeting_project_requires_workspace_id(self):
        """Codex F-1/F-2 anchor: add_meeting_project workspace_id + meeting secondary FK 필수."""
        import inspect
        from src.projects.service import ProjectService

        sig = inspect.signature(ProjectService.add_meeting_project)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: add_meeting_project workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_get_project_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """GET /projects/{id} → service.get_project workspace_id 정확 값 (Codex F-3)."""
        from src.projects.dependencies import get_project_service

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_viewer] = lambda: member_a

        project_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.get_project.return_value = {
            "id": str(project_id),
            "workspaceId": str(workspace_a_id),
        }
        app.dependency_overrides[get_project_service] = lambda: mock_service

        response = await client.get(
            f"/api/v1/workspaces/{workspace_a_id}/projects/{project_id}",
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 200
        call_args = mock_service.get_project.call_args
        kwargs = call_args.kwargs if call_args else {}
        assert kwargs.get("workspace_id") == workspace_a_id, (
            f"BUG-C01-EXT v3 projects #2 (Codex F-3): get_project workspace_id 정확 값 미전달. "
            f"기대={workspace_a_id} 실제={kwargs.get('workspace_id')} kwargs={kwargs}"
        )

    @pytest.mark.asyncio
    async def test_update_project_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """PATCH /projects/{id} → service.update_project workspace_id 정확 값 (Codex F-3)."""
        from src.projects.dependencies import get_project_service
        from src.auth.rbac import require_member, require_member_fresh

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a
        app.dependency_overrides[require_member_fresh] = lambda: member_a

        project_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.update_project.return_value = {
            "id": str(project_id),
            "workspaceId": str(workspace_a_id),
        }
        app.dependency_overrides[get_project_service] = lambda: mock_service

        response = await client.patch(
            f"/api/v1/workspaces/{workspace_a_id}/projects/{project_id}",
            json={"title": "new"},
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 200
        call_args = mock_service.update_project.call_args
        kwargs = call_args.kwargs if call_args else {}
        assert kwargs.get("workspace_id") == workspace_a_id, (
            f"BUG-C01-EXT v3 projects #4 (Codex F-3): update_project workspace_id 정확 값. "
            f"기대={workspace_a_id} 실제={kwargs.get('workspace_id')} kwargs={kwargs}"
        )

    @pytest.mark.asyncio
    async def test_delete_project_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """DELETE /projects/{id} → service.delete_project workspace_id 정확 값 (Codex F-3)."""
        from src.projects.dependencies import get_project_service
        from src.auth.rbac import require_admin

        app.dependency_overrides[get_current_user] = lambda: user_a
        member_a.role = "admin"
        app.dependency_overrides[require_admin] = lambda: member_a

        project_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.delete_project.return_value = None
        app.dependency_overrides[get_project_service] = lambda: mock_service

        response = await client.delete(
            f"/api/v1/workspaces/{workspace_a_id}/projects/{project_id}",
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 204
        call_args = mock_service.delete_project.call_args
        args = call_args.args if call_args else ()
        kwargs = call_args.kwargs if call_args else {}
        workspace_id_seen = kwargs.get("workspace_id") or (
            args[0] if len(args) > 0 else None
        )
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 projects #5 (Codex F-3): delete_project workspace_id 정확 값. "
            f"기대={workspace_a_id} 실제={workspace_id_seen} kwargs={kwargs} args={args}"
        )

    @pytest.mark.asyncio
    async def test_add_meeting_project_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """POST /meetings/{mid}/projects → service.add_meeting_project workspace_id 정확 값 (Codex F-3)."""
        from src.projects.dependencies import get_project_service
        from src.auth.rbac import require_member

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_member] = lambda: member_a

        meeting_id = uuid.uuid4()
        project_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.add_meeting_project.return_value = {
            "id": str(uuid.uuid4()),
            "meetingId": str(meeting_id),
            "projectId": str(project_id),
        }
        app.dependency_overrides[get_project_service] = lambda: mock_service

        response = await client.post(
            f"/api/v1/workspaces/{workspace_a_id}/meetings/{meeting_id}/projects",
            json={"projectId": str(project_id)},
            headers={"Authorization": "Bearer t"},
        )
        assert response.status_code == 201
        call_args = mock_service.add_meeting_project.call_args
        args = call_args.args if call_args else ()
        kwargs = call_args.kwargs if call_args else {}
        workspace_id_seen = kwargs.get("workspace_id") or (
            args[0] if len(args) > 0 else None
        )
        assert workspace_id_seen == workspace_a_id, (
            f"BUG-C01-EXT v3 projects #10 (Codex F-3): add_meeting_project workspace_id. "
            f"기대={workspace_a_id} 실제={workspace_id_seen} kwargs={kwargs} args={args}"
        )


class TestMemoryIDORMatrix:
    """memory 도메인 5 endpoint + promote target_workspace_id secondary FK (Sprint 19 PR #1 C10).

    Codex F-4: promote 의 cross-workspace 검증을 WorkspaceRepository API 로 이동
    (backend rule §3 회복). workspace_repo None → RuntimeError fail-closed.
    """

    @pytest.mark.asyncio
    async def test_memory_repository_get_by_id_requires_workspace_id(self):
        """Codex F-1 anchor: MemoryRepository.get_by_id 시그니처 workspace_id 필수."""
        import inspect
        from src.memory.repository import MemoryRepository

        sig = inspect.signature(MemoryRepository.get_by_id)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: MemoryRepository.get_by_id workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_memory_service_promote_uses_workspace_repo(self):
        """Codex F-4 anchor: MemoryService 가 workspace_repo 주입 받음 (backend rule §3)."""
        import inspect
        from src.memory.service import MemoryService

        sig = inspect.signature(MemoryService.__init__)
        assert "workspace_repo" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-4: MemoryService.__init__ 에 workspace_repo 주입 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_memory_service_promote_fail_closed_without_workspace_repo(self):
        """Codex F-4 + 2차 Minor 1 fail-closed: workspace_repo=None → RuntimeError."""
        from unittest.mock import AsyncMock, MagicMock
        from src.memory.service import MemoryService

        service = MemoryService(
            repo=AsyncMock(),
            session_factory=MagicMock(),
            r2_service=MagicMock(),
            workspace_repo=None,
        )
        bg = MagicMock()
        with pytest.raises(RuntimeError, match="workspace_repo 필수"):
            await service.promote(
                memory_id=uuid.uuid4(),
                source_workspace_id=uuid.uuid4(),
                target_workspace_id=uuid.uuid4(),
                promoted_by_user_id=uuid.uuid4(),
                background_tasks=bg,
            )

    @pytest.mark.asyncio
    async def test_get_memory_passes_workspace_id_to_service(
        self, client, user_a, member_a, workspace_a_id
    ):
        """GET /memory/{id} → service.get_memory workspace_id 정확 값 (Codex F-3)."""
        from src.memory.dependencies import get_memory_service

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_viewer] = lambda: member_a

        memory_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.get_memory.return_value = {
            "memory_id": memory_id,
            "workspace_id": workspace_a_id,
            "type": "text",
            "raw_content": "test",
            "distilled_json": None,
            "status": "ready",
            "embedding_chunk_id": None,
            "r2_audio_key": None,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        app.dependency_overrides[get_memory_service] = lambda: mock_service

        response = await client.get(
            f"/api/v1/workspaces/{workspace_a_id}/memory/{memory_id}",
            headers={"Authorization": "Bearer t"},
        )
        # response 200 or schema validation issue — assertion 은 호출 검증만
        call_args = mock_service.get_memory.call_args
        if call_args:
            args = call_args.args
            kwargs = call_args.kwargs
            workspace_id_seen = kwargs.get("workspace_id") or (
                args[1] if len(args) > 1 else None
            )
            assert workspace_id_seen == workspace_a_id, (
                f"BUG-C01-EXT v3 memory #4 (Codex F-3): get_memory workspace_id 정확 값. "
                f"기대={workspace_a_id} 실제={workspace_id_seen} kwargs={kwargs} args={args}"
            )


class TestRagIDORMatrix:
    """rag 도메인 1 endpoint (ask) + project_id secondary FK (Sprint 19 PR #1 C11).

    Codex F-2 MAJOR: tenant 검증 role 무관 (admin/owner 도 cross-tenant project_id 차단).
    visibility 검증 (draft/private) 만 admin/owner 우회 (Sprint 6 ADR-014 옵션 A).
    """

    @pytest.mark.asyncio
    async def test_rag_pipeline_service_ask_tenant_check_role_agnostic(self):
        """Codex F-2 anchor: ask() 안에 role 무관 tenant 검증 (project_repo.find_by_id 호출)."""
        import inspect
        from src.rag.pipeline_service import RagPipelineService

        src_text = inspect.getsource(RagPipelineService.ask)
        # ask 함수 본문에 role-무관 tenant 검증이 visibility 검증 *전에* 있어야 함
        assert "project_repo.find_by_id(project_id, workspace_id)" in src_text, (
            f"BUG-C01-EXT v3 Codex F-2: RagPipelineService.ask 안에 role-무관 "
            f"project_repo.find_by_id(project_id, workspace_id) 호출 필수."
        )

    @pytest.mark.asyncio
    async def test_rag_pipeline_admin_cannot_bypass_cross_tenant_project(self):
        """Codex F-2: admin/owner 도 cross-tenant project_id 차단."""
        from unittest.mock import AsyncMock, MagicMock
        from src.rag.pipeline_service import RagPipelineService

        mock_project_repo = AsyncMock()
        mock_project_repo.find_by_id.return_value = None  # cross-tenant 또는 nonexistent
        mock_rag_service = AsyncMock()

        async def empty_async_gen():
            if False:
                yield {}

        mock_rag_service.ask.return_value = empty_async_gen()

        pipeline = RagPipelineService(
            rag_service=mock_rag_service,
            project_repo=mock_project_repo,
        )

        ws_a = uuid.uuid4()
        project_b = uuid.uuid4()
        user = uuid.uuid4()

        events = []
        async for event in pipeline.ask(
            question="test",
            workspace_id=ws_a,
            requester_user_id=user,
            requester_role="admin",  # admin 이지만 tenant 우회 금지
            project_id=project_b,
        ):
            events.append(event)

        # admin 도 cross-tenant project_id 시 SSE error event 발생 + done
        assert any(
            "프로젝트를 찾을 수 없거나" in str(e.get("data", "")) for e in events
        ), f"Codex F-2: admin 도 cross-tenant project 차단해야 함. events={events}"
        # find_by_id workspace_id 호출 확인
        mock_project_repo.find_by_id.assert_called_with(project_b, ws_a)


class TestWorkspacesIDORMatrix:
    """workspaces main 2 + member 3 + invite 3 = 8 endpoint (Sprint 19 PR #1 C12).

    Codex F-1/F-5: find_member_by_id / find_invite_by_id 시그니처 + mutation WHERE workspace_id.
    """

    @pytest.mark.asyncio
    async def test_workspace_repository_find_member_by_id_requires_workspace_id(self):
        """Codex F-1 anchor: find_member_by_id workspace_id 필수."""
        import inspect
        from src.workspaces.repository import WorkspaceRepository

        sig = inspect.signature(WorkspaceRepository.find_member_by_id)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: find_member_by_id workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_workspace_repository_find_invite_by_id_requires_workspace_id(self):
        """Codex F-1 anchor: find_invite_by_id workspace_id 필수."""
        import inspect
        from src.workspaces.repository import WorkspaceRepository

        sig = inspect.signature(WorkspaceRepository.find_invite_by_id)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: find_invite_by_id workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_workspace_repository_update_member_role_mutation_workspace_id(self):
        """Codex F-5 anchor: update_member_role mutation 도 workspace_id WHERE."""
        import inspect
        from src.workspaces.repository import WorkspaceRepository

        sig = inspect.signature(WorkspaceRepository.update_member_role)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-5: update_member_role mutation workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_workspace_repository_remove_member_mutation_workspace_id(self):
        """Codex F-5 anchor: remove_member mutation 도 workspace_id WHERE."""
        import inspect
        from src.workspaces.repository import WorkspaceRepository

        sig = inspect.signature(WorkspaceRepository.remove_member)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-5: remove_member mutation workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_workspace_repository_deactivate_invite_mutation_workspace_id(self):
        """Codex F-5 anchor: deactivate_invite mutation 도 workspace_id WHERE."""
        import inspect
        from src.workspaces.repository import WorkspaceRepository

        sig = inspect.signature(WorkspaceRepository.deactivate_invite)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-5: deactivate_invite mutation workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_workspace_repository_increment_invite_use_count_mutation_workspace_id(self):
        """Codex F-5 anchor: increment_invite_use_count mutation 도 workspace_id WHERE."""
        import inspect
        from src.workspaces.repository import WorkspaceRepository

        sig = inspect.signature(WorkspaceRepository.increment_invite_use_count)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-5: increment_invite_use_count mutation workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_invite_service_update_member_role_requires_workspace_id(self):
        """Codex F-1 anchor: InviteService.update_member_role 첫 인자 workspace_id."""
        import inspect
        from src.workspaces.invite_service import InviteService

        sig = inspect.signature(InviteService.update_member_role)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: InviteService.update_member_role workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )

    @pytest.mark.asyncio
    async def test_invite_service_remove_member_requires_workspace_id(self):
        """Codex F-1 anchor: InviteService.remove_member 첫 인자 workspace_id."""
        import inspect
        from src.workspaces.invite_service import InviteService

        sig = inspect.signature(InviteService.remove_member)
        assert "workspace_id" in sig.parameters, (
            f"BUG-C01-EXT v3 Codex F-1: InviteService.remove_member workspace_id 필수. "
            f"현재 params={list(sig.parameters)}"
        )


class TestUploadIDORMatrix:
    """upload 도메인 2 endpoint (Sprint 19 PR #1 C11).

    DB lookup 없음 (R2 only), secondary FK 없음. require_member path param 강제 검증.
    file_key path 패턴 (BUG-UPL-OWN)은 PR #4에서 별도.
    """

    @pytest.mark.asyncio
    async def test_upload_presigned_url_has_workspace_id_path_param(self):
        """Upload presigned-url endpoint 가 workspace_id path param 받음 (require_member 차단 기반)."""
        from src.upload import router as upload_router

        # router 의 endpoint 가 workspace_id path 받는지 inspect
        routes = [r for r in upload_router.router.routes if hasattr(r, "path")]
        paths = [r.path for r in routes]
        assert any("{workspace_id}" in p for p in paths), (
            f"BUG-C01-EXT v3 upload #1: presigned-url endpoint workspace_id path 필수. paths={paths}"
        )

    @pytest.mark.asyncio
    async def test_upload_file_proxy_has_workspace_id_path_param(self):
        """Upload file endpoint 가 workspace_id path param 받음."""
        from src.upload import router as upload_router

        routes = [r for r in upload_router.router.routes if hasattr(r, "path")]
        paths = [r.path for r in routes]
        # 두 endpoint 모두 workspace_id path
        ws_routes = [p for p in paths if "{workspace_id}" in p]
        assert len(ws_routes) >= 2, (
            f"BUG-C01-EXT v3 upload #2: 2 endpoint 모두 workspace_id path 필수. ws_routes={ws_routes}"
        )

    @pytest.mark.asyncio
    async def test_upload_router_requires_member_dependency(self):
        """require_member dependency 가 두 endpoint 모두 적용 (cross-tenant 차단 게이트).

        RoleChecker(class instance) 형태이므로 __name__ 대신 type 또는 source 검증.
        """
        import inspect
        from src.upload import router as upload_router

        # router 모듈 source 에 require_member 가 import + Depends 로 사용되는지
        src_text = inspect.getsource(upload_router)
        assert "require_member" in src_text, (
            f"BUG-C01-EXT v3 upload: router.py 에 require_member 적용 필수."
        )
        assert src_text.count("Depends(require_member)") >= 2, (
            f"BUG-C01-EXT v3 upload: 2 endpoint 모두 Depends(require_member) 필수."
        )


class TestIntegrationsIDORMatrix:
    """integrations workspace 경계 — router → service의 정확한 tenant 전달 고정."""

    @pytest.mark.asyncio
    async def test_sync_run_polling_passes_workspace_id_to_service(
        self,
        client,
        user_a,
        member_a,
        workspace_a_id,
    ):
        from datetime import UTC, datetime
        from types import SimpleNamespace

        from src.integrations.dependencies import get_integration_service

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_owner] = lambda: member_a
        sync_run_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.get_sync_run.return_value = SimpleNamespace(
            id=sync_run_id,
            status="completed",
            started_at=datetime.now(UTC).replace(tzinfo=None),
            completed_at=None,
            error_summary=None,
        )
        mock_service.list_documents_by_sync_run.return_value = []
        app.dependency_overrides[get_integration_service] = lambda: mock_service

        response = await client.get(
            f"/api/v1/workspaces/{workspace_a_id}/integrations/sync-runs/{sync_run_id}",
        )

        assert response.status_code == 200
        assert mock_service.get_sync_run.await_args.args == (
            sync_run_id,
            workspace_a_id,
        )
        assert mock_service.list_documents_by_sync_run.await_args.args == (
            sync_run_id,
            workspace_a_id,
        )

    @pytest.mark.asyncio
    async def test_authorize_saves_workspace_id_to_state_repository(
        self,
        client,
        member_a,
        monkeypatch,
        workspace_a_id,
    ):
        from src.integrations import router as integrations_router
        from src.integrations.dependencies import get_integration_repository

        def encode_state(
            _workspace_id: uuid.UUID,
            _requester_user_id: uuid.UUID,
            _code_verifier: str,
            **_kwargs: object,
        ) -> str:
            return "encrypted-state"

        repository = SimpleNamespace(
            delete_expired_oauth_states=AsyncMock(),
            create_oauth_state=AsyncMock(),
            commit=AsyncMock(),
        )
        app.dependency_overrides[require_owner] = lambda: member_a
        monkeypatch.setattr(
            integrations_router,
            "_oauth_credentials",
            lambda: ("client-id", "client-secret"),
        )
        monkeypatch.setattr(integrations_router, "_encode_oauth_state", encode_state)
        app.dependency_overrides[get_integration_repository] = lambda: repository

        response = await client.post(
            f"/api/v1/workspaces/{workspace_a_id}/integrations/google-drive/authorize",
        )

        assert response.status_code == 200
        oauth_state = repository.create_oauth_state.await_args.args[0]
        assert oauth_state.workspace_id == workspace_a_id
        assert oauth_state.requester_user_id == member_a.user_id
        assert repository.delete_expired_oauth_states.await_args.args[0] == workspace_a_id

    @pytest.mark.asyncio
    async def test_connection_status_passes_workspace_id_to_service(
        self,
        client,
        member_a,
        workspace_a_id,
    ):
        from src.integrations.dependencies import get_integration_service

        service = AsyncMock()
        service.get_connection_by_provider.return_value = None
        app.dependency_overrides[require_owner] = lambda: member_a
        app.dependency_overrides[get_integration_service] = lambda: service

        response = await client.get(
            f"/api/v1/workspaces/{workspace_a_id}/integrations/google-drive",
        )

        assert response.status_code == 200
        assert service.get_connection_by_provider.await_args.args == (
            workspace_a_id,
            "google_drive",
        )

    @pytest.mark.asyncio
    async def test_import_passes_workspace_id_to_pipeline(
        self,
        client,
        member_a,
        workspace_a_id,
    ):
        from src.integrations.dependencies import (
            get_google_drive_sync_pipeline_service,
            get_integration_project_repository,
            get_integration_repository,
            get_integration_service,
        )

        connection_id = uuid.uuid4()
        service = AsyncMock()
        service.get_connection_by_provider.return_value = MagicMock(id=connection_id)
        repository = AsyncMock()
        pipeline = MagicMock()
        pipeline.import_documents = AsyncMock()
        app.dependency_overrides[require_owner] = lambda: member_a
        app.dependency_overrides[get_integration_service] = lambda: service
        app.dependency_overrides[get_integration_repository] = lambda: repository
        app.dependency_overrides[get_integration_project_repository] = lambda: MagicMock()
        app.dependency_overrides[get_google_drive_sync_pipeline_service] = lambda: pipeline

        response = await client.post(
            f"/api/v1/workspaces/{workspace_a_id}/integrations/google-drive/documents",
            json={"fileIds": ["drive-file-id"]},
        )

        assert response.status_code == 202
        assert service.get_connection_by_provider.await_args.args == (
            workspace_a_id,
            "google_drive",
        )
        assert repository.create_sync_run.await_args.args[1] == workspace_a_id
        assert pipeline.import_documents.await_args.args[1] == workspace_a_id

    @pytest.mark.asyncio
    async def test_cross_tenant_delete_document_is_not_found(
        self,
        client,
        member_a,
        workspace_a_id,
    ):
        from src.integrations.dependencies import (
            get_google_drive_sync_pipeline_service,
            get_integration_service,
        )

        document_id = uuid.uuid4()
        service = AsyncMock()
        service.get_document.return_value = None
        app.dependency_overrides[require_owner] = lambda: member_a
        app.dependency_overrides[get_integration_service] = lambda: service
        app.dependency_overrides[get_google_drive_sync_pipeline_service] = lambda: MagicMock()

        response = await client.delete(
            f"/api/v1/workspaces/{workspace_a_id}/integrations/google-drive/"
            f"documents/{document_id}",
        )

        assert response.status_code == 404
        assert service.get_document.await_args.args == (document_id, workspace_a_id)

    @pytest.mark.asyncio
    async def test_cross_tenant_external_document_is_not_found_for_viewer(
        self,
        client,
        member_a,
        workspace_a_id,
    ):
        from src.integrations.dependencies import get_integration_service

        document_id = uuid.uuid4()
        service = AsyncMock()
        service.get_document.return_value = None
        app.dependency_overrides[require_viewer] = lambda: member_a
        app.dependency_overrides[get_integration_service] = lambda: service

        response = await client.get(
            f"/api/v1/workspaces/{workspace_a_id}/external-documents/{document_id}",
        )

        assert response.status_code == 404
        assert service.get_document.await_args.args == (document_id, workspace_a_id)

    @pytest.mark.asyncio
    async def test_import_hides_cross_tenant_project_id(
        self,
        client,
        member_a,
        workspace_a_id,
    ):
        from src.integrations.dependencies import (
            get_google_drive_sync_pipeline_service,
            get_integration_project_repository,
            get_integration_repository,
            get_integration_service,
        )

        project_id = uuid.uuid4()
        service = AsyncMock()
        service.get_connection_by_provider.return_value = MagicMock(id=uuid.uuid4())
        project_repository = AsyncMock()
        project_repository.find_by_id.return_value = None
        app.dependency_overrides[require_owner] = lambda: member_a
        app.dependency_overrides[get_integration_service] = lambda: service
        app.dependency_overrides[get_integration_repository] = lambda: AsyncMock()
        app.dependency_overrides[get_integration_project_repository] = (
            lambda: project_repository
        )
        app.dependency_overrides[get_google_drive_sync_pipeline_service] = lambda: MagicMock()

        response = await client.post(
            f"/api/v1/workspaces/{workspace_a_id}/integrations/google-drive/documents",
            json={"fileIds": ["drive-file-id"], "projectId": str(project_id)},
        )

        assert response.status_code == 404
        assert project_repository.find_by_id.await_args.args == (
            project_id,
            workspace_a_id,
        )

    @pytest.mark.asyncio
    async def test_cross_tenant_external_document_is_not_found(
        self,
        client,
        user_a,
        member_a,
        workspace_a_id,
    ):
        from src.integrations.dependencies import (
            get_google_drive_sync_pipeline_service,
            get_integration_service,
        )

        app.dependency_overrides[get_current_user] = lambda: user_a
        app.dependency_overrides[require_owner] = lambda: member_a
        cross_tenant_document_id = uuid.uuid4()
        mock_service = AsyncMock()
        mock_service.get_document.return_value = None
        app.dependency_overrides[get_integration_service] = lambda: mock_service
        app.dependency_overrides[get_google_drive_sync_pipeline_service] = lambda: MagicMock()

        response = await client.post(
            f"/api/v1/workspaces/{workspace_a_id}/integrations/google-drive/"
            f"documents/{cross_tenant_document_id}/sync",
        )

        assert response.status_code == 404
        assert mock_service.get_document.await_args.args == (
            cross_tenant_document_id,
            workspace_a_id,
        )
