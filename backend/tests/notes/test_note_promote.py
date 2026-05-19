# Sprint 23 D4 Task 2 Step 2.3 — Notes promote 통합 테스트
"""Notes promote 1-button: Note 복제 + ItemPromotionAudit + 검증.

I-18 (복제 + tombstone): 원본 Note 변경 없이 target ws 복제본 신규 + audit.
검증: source != target / target type='team' / promoter 가 target ws 멤버.
4 케이스: success / same_workspace 400 / target_not_member 403 / target_personal 400.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import select


@pytest_asyncio.fixture
async def notes_client(integration_session, auth_user, monkeypatch):
    """Notes API 테스트용 AsyncClient — get_current_user + get_async_session + session_factory override.

    BG task 는 외부 OpenAI 호출 없이 EmbeddingChunk 복제만 수행 — 실제 호출 차단 불필요.
    단 session_factory 는 동일 integration_session 재사용 (테스트 격리 위해).
    """
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session, get_session_factory
    from src.main import app

    # session_factory 는 async context manager 인터페이스 필요 → 같은 session 반환하는 dummy.
    class _DummyFactory:
        def __call__(self):
            return _DummyAsyncCM(integration_session)

    class _DummyAsyncCM:
        def __init__(self, sess):
            self._sess = sess

        async def __aenter__(self):
            return self._sess

        async def __aexit__(self, *_args):
            return False

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_session_factory] = lambda: _DummyFactory()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_note(integration_session, auth_user, personal_ws):
    """personal ws 의 Note seed (project_id=None — cross-workspace promote 단순화)."""
    from src.notes.models import Note

    note = Note(
        workspace_id=personal_ws.id,
        project_id=None,
        title="테스트 노트",
        content={"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "첫 번째 문장"}]}]},
        plain_text="첫 번째 문장",
        created_by_id=auth_user.id,
    )
    integration_session.add(note)
    await integration_session.flush()
    await integration_session.commit()
    return note


@pytest.mark.asyncio
async def test_promote_creates_duplicate_and_audit(
    notes_client,
    integration_session,
    personal_ws,
    team_ws,
    seed_note,
    auth_user,
):
    """personal → team promote → 202 + new Note 복제 + audit row."""
    from src.common.promote_models import ItemPromotionAudit
    from src.notes.models import Note

    response = await notes_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/notes/{seed_note.id}/promote",
        json={"targetWorkspaceId": str(team_ws.id)},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    new_id = body["newNoteId"] if "newNoteId" in body else body["new_note_id"]
    audit_id = body["auditId"] if "auditId" in body else body["audit_id"]
    assert uuid.UUID(new_id)
    assert uuid.UUID(audit_id)
    assert body["status"] == "embedding_pending"
    assert new_id != str(seed_note.id)

    # 원본 보존 — workspace_id 변경 없음
    src_q = select(Note).where(Note.id == seed_note.id)
    src = (await integration_session.execute(src_q)).scalar_one()
    assert src.workspace_id == personal_ws.id
    assert src.title == "테스트 노트"

    # 복제본 Note (target ws)
    dup_q = select(Note).where(
        Note.workspace_id == team_ws.id,
        Note.id != seed_note.id,
    )
    dup = (await integration_session.execute(dup_q)).scalar_one()
    assert dup.title == seed_note.title
    assert dup.plain_text == seed_note.plain_text
    assert dup.content == seed_note.content
    assert dup.created_by_id == auth_user.id
    # project_id 는 복제본에서 None (cross-workspace 제약)
    assert dup.project_id is None

    # ItemPromotionAudit row
    audit_q = select(ItemPromotionAudit).where(
        ItemPromotionAudit.id == uuid.UUID(audit_id)
    )
    audit = (await integration_session.execute(audit_q)).scalar_one()
    assert audit.item_type == "note"
    assert audit.source_item_id == seed_note.id
    assert audit.new_item_id == dup.id
    assert audit.source_workspace_id == personal_ws.id
    assert audit.target_workspace_id == team_ws.id
    assert audit.promoted_by_user_id == auth_user.id


@pytest.mark.asyncio
async def test_promote_same_workspace_rejected(
    notes_client, personal_ws, seed_note
):
    """source == target → 400 (CannotPromoteToSameWorkspaceError)."""
    response = await notes_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/notes/{seed_note.id}/promote",
        json={"targetWorkspaceId": str(personal_ws.id)},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_promote_target_not_member_rejected(
    notes_client, integration_session, personal_ws, seed_note
):
    """target ws 가 promoter 의 멤버 아님 → 403 (TargetWorkspaceInvalidError)."""
    from src.auth.models import User
    from src.workspaces.models import Workspace, WorkspaceMember

    # promoter 가 멤버 아닌 별도 team workspace (다른 owner)
    other_owner = User(
        clerk_id="other_clerk_note",
        display_name="다른 오너",
        email="other_note@kairos.test",
    )
    integration_session.add(other_owner)
    await integration_session.flush()

    other_team = Workspace(
        name="다른 팀 노트",
        owner_id=other_owner.id,
        type="team",
    )
    integration_session.add(other_team)
    await integration_session.flush()
    # promoter (auth_user) 는 멤버 아님 — other_owner 만 멤버
    integration_session.add(
        WorkspaceMember(
            workspace_id=other_team.id,
            user_id=other_owner.id,
            role="owner",
        )
    )
    await integration_session.flush()
    await integration_session.commit()

    response = await notes_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/notes/{seed_note.id}/promote",
        json={"targetWorkspaceId": str(other_team.id)},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_promote_target_personal_rejected(
    notes_client, integration_session, personal_ws, seed_note, auth_user
):
    """target ws.type='personal' → 400 (CannotPromoteToPersonalError)."""
    from src.workspaces.models import Workspace, WorkspaceMember

    # auth_user 가 멤버인 두 번째 personal ws (보통 1인 1ws 정책이지만 테스트용)
    other_personal = Workspace(
        name="다른 개인 ws 노트",
        owner_id=auth_user.id,
        type="personal",
    )
    integration_session.add(other_personal)
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(
            workspace_id=other_personal.id,
            user_id=auth_user.id,
            role="owner",
        )
    )
    await integration_session.flush()
    await integration_session.commit()

    response = await notes_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/notes/{seed_note.id}/promote",
        json={"targetWorkspaceId": str(other_personal.id)},
    )
    assert response.status_code == 400
