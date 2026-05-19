# Sprint 23 D4 Task 2 Step 2.5 — Action promote 통합 테스트
"""Action promote 1-button: ActionItem 복제 + ItemPromotionAudit + 검증.

I-18 (복제 + tombstone): 원본 ActionItem 변경 없이 target ws 복제본 신규 + audit.
검증: source != target / target type='team' / promoter 가 target ws 멤버.
4 케이스: success / same_workspace 400 / target_not_member 403 / target_personal 400.

ActionItem 임베딩 ledger 부재 → audit.embedding_status='n/a' + status='completed'.
meeting_id / project_id / assignee_id 모두 None reset (composite FK + 단순화).
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import select


@pytest_asyncio.fixture
async def action_client(integration_session, auth_user, monkeypatch):
    """Action API 테스트용 AsyncClient — get_current_user + get_async_session override.

    action promote 는 BG embedding 복제 없음 → session_factory override 불필요.
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
async def seed_action_item(integration_session, auth_user, personal_ws):
    """personal ws 의 ActionItem seed.

    meeting_id / project_id / assignee_id 는 None — composite FK 제약 + 별도 seed 불필요.
    복제본도 None reset 검증 위해 핵심 메타만 채움.
    """
    from datetime import date

    from src.actions.models import ActionItem

    item = ActionItem(
        workspace_id=personal_ws.id,
        meeting_id=None,
        project_id=None,
        assignee_id=None,
        title="테스트 액션 아이템",
        description="액션 설명 텍스트",
        due_date=date(2026, 7, 1),
        priority="high",
        status="in_progress",
    )
    integration_session.add(item)
    await integration_session.flush()
    await integration_session.commit()
    return item


@pytest.mark.asyncio
async def test_promote_creates_duplicate_and_audit(
    action_client,
    integration_session,
    personal_ws,
    team_ws,
    seed_action_item,
    auth_user,
):
    """personal → team promote → 202 + new ActionItem 복제 + audit row."""
    from src.actions.models import ActionItem
    from src.common.promote_models import ItemPromotionAudit

    response = await action_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/action-items/{seed_action_item.id}/promote",
        json={"targetWorkspaceId": str(team_ws.id)},
    )
    assert response.status_code == 202, response.text
    body = response.json()
    new_id = body["newActionId"] if "newActionId" in body else body["new_action_id"]
    audit_id = body["auditId"] if "auditId" in body else body["audit_id"]
    assert uuid.UUID(new_id)
    assert uuid.UUID(audit_id)
    # ActionItem 은 임베딩 ledger 없음 → status='completed' (notes/meetings 는 'embedding_pending')
    assert body["status"] == "completed"
    assert new_id != str(seed_action_item.id)

    # 원본 보존 — workspace_id 변경 없음 + 메타 그대로
    src_q = select(ActionItem).where(ActionItem.id == seed_action_item.id)
    src = (await integration_session.execute(src_q)).scalar_one()
    assert src.workspace_id == personal_ws.id
    assert src.title == "테스트 액션 아이템"
    assert src.status == "in_progress"  # 원본 미변경

    # 복제본 ActionItem (target ws)
    dup_q = select(ActionItem).where(
        ActionItem.workspace_id == team_ws.id,
        ActionItem.id != seed_action_item.id,
    )
    dup = (await integration_session.execute(dup_q)).scalar_one()
    assert dup.title == seed_action_item.title
    assert dup.description == seed_action_item.description
    assert dup.due_date == seed_action_item.due_date
    assert dup.priority == seed_action_item.priority
    assert dup.status == seed_action_item.status
    # meeting_id / project_id / assignee_id 모두 None reset
    # (composite FK 제약 — target ws 와 무관, 단순화 정책)
    assert dup.meeting_id is None
    assert dup.project_id is None
    assert dup.assignee_id is None

    # ItemPromotionAudit row
    audit_q = select(ItemPromotionAudit).where(
        ItemPromotionAudit.id == uuid.UUID(audit_id)
    )
    audit = (await integration_session.execute(audit_q)).scalar_one()
    assert audit.item_type == "action"
    assert audit.source_item_id == seed_action_item.id
    assert audit.new_item_id == dup.id
    assert audit.source_workspace_id == personal_ws.id
    assert audit.target_workspace_id == team_ws.id
    assert audit.promoted_by_user_id == auth_user.id
    # ActionItem 임베딩 ledger 부재 → 'n/a' (BG embedding 복제 task 없음)
    assert audit.embedding_status == "n/a"


@pytest.mark.asyncio
async def test_promote_same_workspace_rejected(
    action_client, personal_ws, seed_action_item
):
    """source == target → 400 (CannotPromoteToSameWorkspaceError)."""
    response = await action_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/action-items/{seed_action_item.id}/promote",
        json={"targetWorkspaceId": str(personal_ws.id)},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_promote_target_not_member_rejected(
    action_client, integration_session, personal_ws, seed_action_item
):
    """target ws 가 promoter 의 멤버 아님 → 403 (TargetWorkspaceInvalidError)."""
    from src.auth.models import User
    from src.workspaces.models import Workspace, WorkspaceMember

    # promoter 가 멤버 아닌 별도 team workspace (다른 owner)
    other_owner = User(
        clerk_id="other_clerk_action",
        display_name="다른 오너 (Action)",
        email="other_action@kairos.test",
    )
    integration_session.add(other_owner)
    await integration_session.flush()

    other_team = Workspace(
        name="다른 팀 Action",
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

    response = await action_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/action-items/{seed_action_item.id}/promote",
        json={"targetWorkspaceId": str(other_team.id)},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_promote_target_personal_rejected(
    action_client, integration_session, personal_ws, seed_action_item, auth_user
):
    """target ws.type='personal' → 400 (CannotPromoteToPersonalError)."""
    from src.workspaces.models import Workspace, WorkspaceMember

    # auth_user 가 멤버인 두 번째 personal ws (보통 1인 1ws 정책이지만 테스트용)
    other_personal = Workspace(
        name="다른 개인 ws Action",
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

    response = await action_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/action-items/{seed_action_item.id}/promote",
        json={"targetWorkspaceId": str(other_personal.id)},
    )
    assert response.status_code == 400
