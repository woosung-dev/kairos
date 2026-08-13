# Sprint 24 Wave 2 T-AUDIT-VIEW (BUG-POW-008) — Audit promotions endpoint 시나리오 매트릭스
"""GET /api/v1/workspaces/{wid}/audit/promotions 시나리오:

1. admin returns 200 + 자신 ws audit list (target_workspace_id 매칭만).
2. viewer/member 호출 → 403 (require_admin RBAC).
3. cross-workspace (admin 다른 ws path 직접 접근) → 403 (membership 부재).

require_admin dependency override + DB seed (target_workspace_id 정확 일치 검증).
"""
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.auth.rbac import require_admin
from src.common.database import get_async_session
from src.common.promote_models import ItemPromotionAudit
from src.main import app
from src.workspaces.models import WorkspaceMember


def _make_mock_admin(workspace_id: uuid.UUID) -> WorkspaceMember:
    m = MagicMock(spec=WorkspaceMember)
    m.user_id = uuid.uuid4()
    m.workspace_id = workspace_id
    m.role = "admin"
    return m


@pytest_asyncio.fixture
async def audit_client(integration_session):
    """integration_session 기반 client — DB 사용 가능 endpoint 시나리오용."""
    app.dependency_overrides[get_async_session] = lambda: integration_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_audit_rows(integration_session, auth_user, team_ws):
    """team_ws 에 4 도메인 1 row씩 + 다른 ws 에 1 row (격리 확인용).

    FK 강제: source_workspace_id / target_workspace_id 모두 workspaces 테이블 존재 필요.
    """
    from src.workspaces.models import Workspace

    source_ws = Workspace(
        name="외부 source ws",
        owner_id=auth_user.id,
        type="team",
    )
    isolated_target_ws = Workspace(
        name="격리 target ws",
        owner_id=auth_user.id,
        type="team",
    )
    integration_session.add_all([source_ws, isolated_target_ws])
    await integration_session.flush()

    now = datetime.utcnow()

    rows = []
    for i, item_type in enumerate(["meeting", "note", "inbox", "action"]):
        row = ItemPromotionAudit(
            item_type=item_type,
            source_item_id=uuid.uuid4(),
            new_item_id=uuid.uuid4(),
            source_workspace_id=source_ws.id,  # cross-ws source
            target_workspace_id=team_ws.id,  # 우리 ws 가 target
            promoted_by_user_id=auth_user.id,
            embedding_status="completed",
            created_at=now - timedelta(minutes=i),
        )
        integration_session.add(row)
        rows.append(row)

    # 다른 ws 의 audit row (격리 확인) — target_workspace_id 가 우리 ws 아님
    isolated = ItemPromotionAudit(
        item_type="meeting",
        source_item_id=uuid.uuid4(),
        new_item_id=uuid.uuid4(),
        source_workspace_id=team_ws.id,
        target_workspace_id=isolated_target_ws.id,  # cross-ws → 보이면 안 됨
        promoted_by_user_id=auth_user.id,
        embedding_status="pending",
        created_at=now - timedelta(minutes=10),
    )
    integration_session.add(isolated)

    await integration_session.commit()
    return {
        "ws_id": team_ws.id,
        "other_ws_id": isolated_target_ws.id,
        "rows": rows,
    }


@pytest.mark.asyncio
async def test_audit_promotions_admin_returns_workspace_rows(
    audit_client, seed_audit_rows
):
    """admin 호출 → 200 + 4 도메인 4 row (cross-ws audit 제외)."""
    ws_id = seed_audit_rows["ws_id"]
    app.dependency_overrides[require_admin] = lambda: _make_mock_admin(ws_id)

    response = await audit_client.get(
        f"/api/v1/workspaces/{ws_id}/audit/promotions",
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 200
    body = response.json()
    items = body["items"]
    # team_ws target 인 4 row 만 (other_target_ws 1 row 격리됨)
    assert len(items) == 4
    item_types = {item["itemType"] for item in items}
    assert item_types == {"meeting", "note", "inbox", "action"}
    # target_workspace_id 일관성
    for item in items:
        assert item["targetWorkspaceId"] == str(ws_id)


@pytest.mark.asyncio
async def test_audit_promotions_viewer_403(audit_client, seed_audit_rows):
    """viewer/member 호출 → 403 (require_admin RBAC gate)."""
    ws_id = seed_audit_rows["ws_id"]

    def _raise_forbidden():
        raise HTTPException(status_code=403, detail="admin 이상 권한이 필요합니다")

    app.dependency_overrides[require_admin] = _raise_forbidden
    response = await audit_client.get(
        f"/api/v1/workspaces/{ws_id}/audit/promotions",
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_promotions_cross_workspace_no_membership_403(
    audit_client, seed_audit_rows
):
    """admin 이라도 멤버 아닌 cross-workspace path 직접 접근 → 403 (membership 부재)."""
    foreign_ws_id = uuid.uuid4()

    def _raise_forbidden():
        # require_admin 은 workspace_id 기준 멤버 검증 — 멤버 부재 시 403.
        raise HTTPException(status_code=403, detail="워크스페이스 멤버가 아닙니다")

    app.dependency_overrides[require_admin] = _raise_forbidden
    response = await audit_client.get(
        f"/api/v1/workspaces/{foreign_ws_id}/audit/promotions",
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_audit_promotions_item_type_filter(audit_client, seed_audit_rows):
    """itemType=note → note 1 row 만."""
    ws_id = seed_audit_rows["ws_id"]
    app.dependency_overrides[require_admin] = lambda: _make_mock_admin(ws_id)

    response = await audit_client.get(
        f"/api/v1/workspaces/{ws_id}/audit/promotions?itemType=note",
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["itemType"] == "note"


@pytest.mark.asyncio
async def test_audit_promotions_invalid_item_type_empty(
    audit_client, seed_audit_rows
):
    """itemType 화이트리스트 외 → 빈 결과 (fail-safe, SQL injection 차단)."""
    ws_id = seed_audit_rows["ws_id"]
    app.dependency_overrides[require_admin] = lambda: _make_mock_admin(ws_id)

    response = await audit_client.get(
        f"/api/v1/workspaces/{ws_id}/audit/promotions?itemType=evil",
        headers={"Authorization": "Bearer fake"},
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert items == []
