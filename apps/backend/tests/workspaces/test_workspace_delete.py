# 워크스페이스 삭제 API — cascade 완전성 + personal 차단 + 타 ws 격리 회귀 가드
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text as sa_text

from src.actions.models import ActionItem
from src.auth.models import User
from src.auth.rbac import require_owner
from src.common.promote_models import ItemPromotionAudit
from src.embeddings.models import EmbeddingChunk, SemanticCache
from src.feedback.models import FeedbackEntry
from src.inbox.models import InboxItem
from src.integrations.models import (
    ExternalDocument,
    IntegrationConnection,
    IntegrationOAuthState,
    IntegrationSyncRun,
)
from src.main import app
from src.meetings.models import Meeting, MeetingSummary, TranscriptSegment
from src.memory.models import (
    MemoryAICall,
    MemoryEvent,
    MemoryItem,
    MemoryQueryEmbeddingCache,
    PromotionAudit,
)
from src.notes.models import Note
from src.projects.models import MeetingProjectLink, Project, ProjectMember
from src.projects.repository import ProjectRepository
from src.workspaces.dependencies import get_workspace_service
from src.workspaces.exceptions import PersonalWorkspaceProtected
from src.workspaces.models import Workspace, WorkspaceInvite, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository
from src.workspaces.service import WorkspaceService


def _service(session) -> WorkspaceService:
    return WorkspaceService(
        repo=WorkspaceRepository(session),
        project_repo=ProjectRepository(session),
    )


async def _seed_user(session, tag: str) -> User:
    user = User(
        clerk_id=f"clerk_{tag}_{uuid.uuid4()}",
        display_name=tag,
        email=f"{tag}_{uuid.uuid4()}@del.test",
    )
    session.add(user)
    await session.flush()
    return user


async def _seed_full_workspace(session, owner: User, member_user: User) -> Workspace:
    """모든 산하 엔티티를 1개 이상 가진 team 워크스페이스 시드."""
    ws = Workspace(name="삭제 대상", owner_id=owner.id, type="team")
    session.add(ws)
    await session.flush()

    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner"))
    session.add(
        WorkspaceMember(workspace_id=ws.id, user_id=member_user.id, role="member")
    )
    session.add(
        WorkspaceInvite(
            workspace_id=ws.id,
            code=f"del{uuid.uuid4().hex[:8]}",
            role="member",
            created_by_id=owner.id,
        )
    )

    project = Project(workspace_id=ws.id, title="P", created_by_id=owner.id)
    session.add(project)
    await session.flush()
    session.add(
        ProjectMember(
            project_id=project.id, workspace_id=ws.id, user_id=member_user.id
        )
    )

    meeting = Meeting(
        workspace_id=ws.id, title="M", file_key="k", created_by_id=owner.id
    )
    session.add(meeting)
    await session.flush()
    session.add(
        TranscriptSegment(
            meeting_id=meeting.id, start_sec=0.0, end_sec=1.0, text="t"
        )
    )
    session.add(MeetingSummary(meeting_id=meeting.id, summary="s"))
    session.add(
        MeetingProjectLink(
            workspace_id=ws.id, meeting_id=meeting.id, project_id=project.id
        )
    )

    note = Note(workspace_id=ws.id, created_by_id=owner.id, title="N")
    session.add(note)
    session.add(ActionItem(workspace_id=ws.id, title="A", meeting_id=meeting.id))
    session.add(
        InboxItem(
            workspace_id=ws.id,
            title="I",
            source_type="meeting",
            source_id=meeting.id,
        )
    )

    chunk = EmbeddingChunk(
        workspace_id=ws.id,
        project_id=project.id,
        source_id=meeting.id,
        source_type="meeting",
        chunk_text="c",
    )
    session.add(chunk)
    await session.flush()
    session.add(
        SemanticCache(workspace_id=ws.id, question="q", answer="a")
    )

    memory = MemoryItem(
        user_id=owner.id,
        workspace_id=ws.id,
        type="text",
        raw_content="m",
        embedding_chunk_id=chunk.id,
    )
    session.add(memory)
    await session.flush()
    session.add(
        MemoryAICall(
            memory_id=memory.id,
            workspace_id=ws.id,
            call_type="distill",
            elapsed_ms=1,
        )
    )
    session.add(
        MemoryEvent(workspace_id=ws.id, user_id=owner.id, event_type="capture")
    )
    session.add(
        PromotionAudit(
            memory_id=memory.id,
            source_workspace_id=ws.id,
            target_workspace_id=ws.id,
            promoted_by_user_id=owner.id,
            promoted_note_id=note.id,
        )
    )
    session.add(
        MemoryQueryEmbeddingCache(
            workspace_id=ws.id, normalized_query="q", embedding=[0.0] * 1536
        )
    )
    session.add(
        ItemPromotionAudit(
            item_type="note",
            source_item_id=note.id,
            new_item_id=uuid.uuid4(),
            source_workspace_id=ws.id,
            target_workspace_id=ws.id,
            promoted_by_user_id=owner.id,
        )
    )
    session.add(FeedbackEntry(user_id=owner.id, workspace_id=ws.id, body="fb"))

    connection = IntegrationConnection(
        workspace_id=ws.id,
        authorized_by_id=owner.id,
        encrypted_refresh_token="test-encrypted-refresh-token",
        scope="https://www.googleapis.com/auth/drive.file",
    )
    session.add(connection)
    await session.flush()
    session.add(
        ExternalDocument(
            workspace_id=ws.id,
            connection_id=connection.id,
            project_id=project.id,
            drive_file_id=f"drive-{uuid.uuid4().hex}",
            title="외부 문서",
            mime_type="application/vnd.google-apps.document",
            origin_url="https://docs.google.com/document/d/test",
            revision_id="1",
            content_hash="test-content-hash",
            plain_text="외부 문서 본문",
        )
    )
    session.add(
        IntegrationSyncRun(
            workspace_id=ws.id,
            connection_id=connection.id,
            requested_by_id=owner.id,
        )
    )
    session.add(
        IntegrationOAuthState(
            nonce=f"workspace-delete-{uuid.uuid4().hex}",
            workspace_id=ws.id,
            requester_user_id=owner.id,
            expires_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )

    await session.flush()
    return ws


_WS_SCOPED_TABLES = [
    "memory_ai_calls",
    "memory_events",
    "memory_items",
    "memory_query_embedding_cache",
    "semantic_caches",
    "embedding_chunks",
    "external_documents",
    "integration_sync_runs",
    "integration_oauth_states",
    "integration_connections",
    "action_items",
    "meeting_project_links",
    "inbox_items",
    "notes",
    "meetings",
    "project_members",
    "projects",
    "workspace_invites",
    "workspace_members",
]


async def _count(session, table: str, where: str, params: dict) -> int:
    return (
        await session.execute(
            sa_text(f"SELECT COUNT(*) FROM {table} WHERE {where}"), params
        )
    ).scalar_one()


@pytest.mark.asyncio
async def test_delete_workspace_cascade_removes_all(integration_session):
    """삭제 후 ws-scoped 전 테이블 잔재 0 + feedback 은 workspace_id NULL 로 보존."""
    owner = await _seed_user(integration_session, "owner")
    member_user = await _seed_user(integration_session, "member")
    ws = await _seed_full_workspace(integration_session, owner, member_user)
    ws_id = ws.id

    await _service(integration_session).delete_workspace(ws_id)

    for table in _WS_SCOPED_TABLES:
        remaining = await _count(
            integration_session, table, "workspace_id = :ws", {"ws": str(ws_id)}
        )
        assert remaining == 0, f"{table} 에 잔재 {remaining}건"

    # meeting 경유 자식 (workspace_id 컬럼 없음)
    for table in ["transcript_segments", "meeting_summaries"]:
        remaining = (
            await integration_session.execute(sa_text(f"SELECT COUNT(*) FROM {table}"))
        ).scalar_one()
        assert remaining == 0, f"{table} 에 잔재 {remaining}건"

    for audit_table in ["promotion_audit", "item_promotion_audit"]:
        audit_remaining = await _count(
            integration_session,
            audit_table,
            "source_workspace_id = :ws OR target_workspace_id = :ws",
            {"ws": str(ws_id)},
        )
        assert audit_remaining == 0, f"{audit_table} 잔재 {audit_remaining}건"

    ws_remaining = await _count(
        integration_session, "workspaces", "id = :ws", {"ws": str(ws_id)}
    )
    assert ws_remaining == 0

    # feedback 은 user-level — row 보존 + workspace_id NULL
    fb_total = (
        await integration_session.execute(
            sa_text("SELECT COUNT(*) FROM feedback_entries WHERE user_id = :u"),
            {"u": str(owner.id)},
        )
    ).scalar_one()
    assert fb_total == 1
    fb_ws_null = (
        await integration_session.execute(
            sa_text(
                "SELECT COUNT(*) FROM feedback_entries"
                " WHERE user_id = :u AND workspace_id IS NULL"
            ),
            {"u": str(owner.id)},
        )
    ).scalar_one()
    assert fb_ws_null == 1


@pytest.mark.asyncio
async def test_delete_workspace_isolation_other_ws_untouched(integration_session):
    """타 워크스페이스 데이터는 삭제에 영향받지 않는다 (I-9)."""
    owner = await _seed_user(integration_session, "owner")
    member_user = await _seed_user(integration_session, "member")
    other_owner = await _seed_user(integration_session, "other")

    target = await _seed_full_workspace(integration_session, owner, member_user)
    survivor = await _seed_full_workspace(
        integration_session, other_owner, member_user
    )

    await _service(integration_session).delete_workspace(target.id)

    for table in _WS_SCOPED_TABLES:
        remaining = await _count(
            integration_session, table, "workspace_id = :ws", {"ws": str(survivor.id)}
        )
        assert remaining > 0, f"생존 ws 의 {table} 이 잘못 삭제됨"


@pytest.mark.asyncio
async def test_delete_personal_workspace_blocked(integration_session):
    """personal 워크스페이스 삭제 → PersonalWorkspaceProtected (I-19)."""
    owner = await _seed_user(integration_session, "owner")
    ws = Workspace(name="개인", owner_id=owner.id, type="personal")
    integration_session.add(ws)
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner")
    )
    await integration_session.flush()

    with pytest.raises(PersonalWorkspaceProtected):
        await _service(integration_session).delete_workspace(ws.id)

    remaining = await _count(
        integration_session, "workspaces", "id = :ws", {"ws": str(ws.id)}
    )
    assert remaining == 1


def test_cascade_statements_cover_all_workspace_fk_tables():
    """codex P1 가드 — workspaces.id FK 를 가진 모든 테이블이 cascade 목록에 포함.

    새 도메인 모델이 workspace_id FK 를 추가하고 cascade 목록을 갱신하지 않으면
    이 테스트가 먼저 깨진다 (런타임 FK 오류 대신 CI 에서 포착).
    """
    from sqlmodel import SQLModel

    statements = " ".join(
        WorkspaceRepository._CASCADE_DELETE_STATEMENTS
    )
    missing = []
    for table in SQLModel.metadata.tables.values():
        refs_workspace = any(
            fk.column.table.name == "workspaces"
            for fk in table.foreign_keys
        )
        if not refs_workspace or table.name == "workspaces":
            continue
        if table.name not in statements:
            missing.append(table.name)
    assert missing == [], (
        f"workspace FK 테이블이 cascade 목록에 없음: {missing} — "
        "delete_workspace_cascade 순서에 추가 필요"
    )


# --- API 레벨 (mock service — require_owner 통과 시 204) ---

WID = str(uuid.uuid4())


def _mock_owner() -> WorkspaceMember:
    member = MagicMock(spec=WorkspaceMember)
    member.user_id = uuid.uuid4()
    member.workspace_id = uuid.UUID(WID)
    member.role = "owner"
    return member


@pytest_asyncio.fixture
async def api_client():
    mock_service = AsyncMock()
    app.dependency_overrides[require_owner] = _mock_owner
    app.dependency_overrides[get_workspace_service] = lambda: mock_service
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c, mock_service
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_workspace_api_204(api_client):
    client, mock_service = api_client
    res = await client.delete(f"/api/v1/workspaces/{WID}")
    assert res.status_code == 204
    mock_service.delete_workspace.assert_awaited_once_with(uuid.UUID(WID))
