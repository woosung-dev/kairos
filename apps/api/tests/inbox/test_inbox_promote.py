# Sprint 23 D4 Task 2 Step 2.4 — Inbox promote 통합 테스트
"""Inbox promote 1-button: InboxItem 복제 + ItemPromotionAudit + 검증.

I-18 (복제 + tombstone): 원본 InboxItem 변경 없이 target ws 복제본 신규 + audit.
검증: source != target / target type='team' / promoter 가 target ws 멤버.
4 케이스: success / same_workspace 400 / target_not_member 403 / target_personal 400.

InboxItem 임베딩 ledger 부재 → audit.embedding_status='n/a' + status='completed'.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import select


@pytest_asyncio.fixture
async def inbox_client(integration_session, auth_user, monkeypatch):
    """Inbox API 테스트용 AsyncClient — get_current_user + get_async_session override.

    inbox promote 는 BG embedding 복제 없음 → session_factory override 불필요.
    """
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session
    from src.main import app

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_async_session] = lambda: integration_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_inbox_item(integration_session, auth_user, personal_ws):
    """personal ws 의 InboxItem seed.

    ai_suggested_project_id=None — composite FK fk_inbox_suggested_project_workspace
    위반 회피 (별도 project seed 불필요). 원본 메타 보존 검증을 위해 다른 필드는 채움.
    """
    from src.inbox.models import InboxItem

    item = InboxItem(
        workspace_id=personal_ws.id,
        title="테스트 Inbox 아이템",
        summary="요약 텍스트",
        source_type="note",
        source_id=uuid.uuid4(),
        ai_suggested_project_id=None,
        ai_suggested_project_title="추천 프로젝트 후보",
        ai_suggested_tags=["태그1", "태그2"],
        ai_confidence=0.85,
        is_processed=True,  # 원본은 처리된 상태 — 복제본은 False 로 reset 검증
    )
    integration_session.add(item)
    await integration_session.flush()
    await integration_session.commit()
    return item


@pytest.mark.asyncio
async def test_promote_creates_duplicate_and_audit(
    inbox_client,
    integration_session,
    personal_ws,
    team_ws,
    seed_inbox_item,
    auth_user,
):
    """personal → team promote → 202 + new InboxItem 복제 + audit row."""
    from src.common.promote_models import ItemPromotionAudit
    from src.inbox.models import InboxItem

    response = await inbox_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/inbox/{seed_inbox_item.id}/promote",
        json={"targetWorkspaceId": str(team_ws.id)},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    new_id = body["newInboxId"] if "newInboxId" in body else body["new_inbox_id"]
    audit_id = body["auditId"] if "auditId" in body else body["audit_id"]
    assert uuid.UUID(new_id)
    assert uuid.UUID(audit_id)
    # InboxItem 은 임베딩 ledger 없음 → status='completed' (notes/meetings 는 'embedding_pending')
    assert body["status"] == "completed"
    assert new_id != str(seed_inbox_item.id)

    # 원본 보존 — workspace_id 변경 없음 + is_processed 그대로
    src_q = select(InboxItem).where(InboxItem.id == seed_inbox_item.id)
    src = (await integration_session.execute(src_q)).scalar_one()
    assert src.workspace_id == personal_ws.id
    assert src.title == "테스트 Inbox 아이템"
    assert src.is_processed is True  # 원본 미변경

    # 복제본 InboxItem (target ws)
    dup_q = select(InboxItem).where(
        InboxItem.workspace_id == team_ws.id,
        InboxItem.id != seed_inbox_item.id,
    )
    dup = (await integration_session.execute(dup_q)).scalar_one()
    assert dup.title == seed_inbox_item.title
    assert dup.summary == seed_inbox_item.summary
    # Sprint 23 Codex 3차 P2 fix: source_type='attachment' + 새 UUID source_id 로 reset
    # (이전 source.source_type='meeting' 보존은 classify 시 target ws 의 meeting_repo.find_by_id
    # 실패 유발). attachment 로 reset → classify 의 meeting verify 분기 회피.
    assert dup.source_type == "attachment"
    assert dup.source_id != seed_inbox_item.source_id
    # ai_suggested_project_id = None (composite FK 제약 — target ws orphan)
    assert dup.ai_suggested_project_id is None
    # ai_suggested_project_title / tags / confidence 는 메타로 보존
    assert dup.ai_suggested_project_title == seed_inbox_item.ai_suggested_project_title
    assert dup.ai_suggested_tags == seed_inbox_item.ai_suggested_tags
    assert dup.ai_confidence == seed_inbox_item.ai_confidence
    # is_processed=False — 복제본은 사용자 재분류 대기
    assert dup.is_processed is False

    # ItemPromotionAudit row
    audit_q = select(ItemPromotionAudit).where(
        ItemPromotionAudit.id == uuid.UUID(audit_id)
    )
    audit = (await integration_session.execute(audit_q)).scalar_one()
    assert audit.item_type == "inbox"
    assert audit.source_item_id == seed_inbox_item.id
    assert audit.new_item_id == dup.id
    assert audit.source_workspace_id == personal_ws.id
    assert audit.target_workspace_id == team_ws.id
    assert audit.promoted_by_user_id == auth_user.id
    # InboxItem 임베딩 ledger 부재 → 'n/a' (BG embedding 복제 task 없음)
    assert audit.embedding_status == "n/a"


@pytest.mark.asyncio
async def test_promote_same_workspace_rejected(
    inbox_client, personal_ws, seed_inbox_item
):
    """source == target → 400 (CannotPromoteToSameWorkspaceError)."""
    response = await inbox_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/inbox/{seed_inbox_item.id}/promote",
        json={"targetWorkspaceId": str(personal_ws.id)},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_promote_target_not_member_rejected(
    inbox_client, integration_session, personal_ws, seed_inbox_item
):
    """target ws 가 promoter 의 멤버 아님 → 403 (TargetWorkspaceInvalidError)."""
    from src.auth.models import User
    from src.workspaces.models import Workspace, WorkspaceMember

    # promoter 가 멤버 아닌 별도 team workspace (다른 owner)
    other_owner = User(
        auth_user_id="other_ba_inbox",
        display_name="다른 오너 (Inbox)",
        email="other_inbox@kairos.test",
    )
    integration_session.add(other_owner)
    await integration_session.flush()

    other_team = Workspace(
        name="다른 팀 Inbox",
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

    response = await inbox_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/inbox/{seed_inbox_item.id}/promote",
        json={"targetWorkspaceId": str(other_team.id)},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_promote_target_personal_rejected(
    inbox_client, integration_session, personal_ws, seed_inbox_item, auth_user
):
    """target ws.type='personal' → 400 (CannotPromoteToPersonalError)."""
    from src.workspaces.models import Workspace, WorkspaceMember

    # auth_user 가 멤버인 두 번째 personal ws (보통 1인 1ws 정책이지만 테스트용)
    other_personal = Workspace(
        name="다른 개인 ws Inbox",
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

    response = await inbox_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/inbox/{seed_inbox_item.id}/promote",
        json={"targetWorkspaceId": str(other_personal.id)},
    )
    assert response.status_code == 400
