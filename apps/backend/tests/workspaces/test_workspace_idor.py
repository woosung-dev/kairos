# BUG-C01 회귀 가드 — Workspace IDOR (Sentinel P0 2026-05-17 발견)
"""GET /workspaces/{workspace_id} 가 require_viewer 없이 노출됐던 IDOR 회귀 가드.

Sentinel P0 (Sprint 18 → 19) 가 발견:
- Sentinel A 토큰 → GET /workspaces/{ws_b} → 200 + body 전체 leak (name/owner/memberCount/threshold)
- Codex 정적 분석 의심 → 실 검증 확정
- Fix: backend/src/workspaces/router.py:35 require_viewer 추가

본 테스트는 require_viewer 가 endpoint 에 연결돼 있는지 검증.
require_viewer 가 dependency_overrides 에서 fail (비멤버 시뮬) 시 endpoint 가 403 반환해야 함.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient

from src.auth.dependencies import get_current_user
from src.auth.models import User
from src.auth.rbac import require_viewer
from src.common.database import get_async_session
from src.main import app


@pytest_asyncio.fixture
async def client():
    mock_session = AsyncMock()
    app.dependency_overrides[get_async_session] = lambda: mock_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_sentinel_a():
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.clerk_id = "user_sentinel_a"
    user.display_name = "Sentinel A"
    user.email = "sentinel-a@kairos.test"
    user.avatar_url = None
    return user


@pytest.mark.asyncio
async def test_get_workspace_idor_non_member_403(client, mock_sentinel_a):
    """GET /workspaces/{ws_b} from non-member → 403.

    BUG-C01 회귀 가드: require_viewer 가 누락되면 본 테스트 즉시 fail.
    """
    app.dependency_overrides[get_current_user] = lambda: mock_sentinel_a

    # 비멤버 시뮬레이션 — require_viewer 가 호출되어 403 raise 해야
    async def deny_non_member():
        raise HTTPException(
            status_code=403, detail="워크스페이스 멤버가 아닙니다"
        )

    app.dependency_overrides[require_viewer] = deny_non_member

    other_workspace_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/workspaces/{other_workspace_id}",
        headers={"Authorization": "Bearer sentinel_a_token"},
    )
    assert response.status_code == 403, (
        f"BUG-C01 회귀: require_viewer 미적용. "
        f"status={response.status_code} body={response.text[:200]}"
    )
    assert "멤버" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_workspace_member_200(client, mock_sentinel_a):
    """GET /workspaces/{ws} from member → 200 (positive control)."""
    app.dependency_overrides[get_current_user] = lambda: mock_sentinel_a

    from src.workspaces.models import WorkspaceMember
    from src.workspaces.dependencies import get_workspace_service

    workspace_id = uuid.uuid4()
    mock_member = MagicMock(spec=WorkspaceMember)
    mock_member.user_id = mock_sentinel_a.id
    mock_member.workspace_id = workspace_id
    mock_member.role = "owner"

    async def allow_member():
        return mock_member

    app.dependency_overrides[require_viewer] = allow_member

    mock_service = AsyncMock()
    mock_service.get_workspace.return_value = {
        "id": str(workspace_id),
        "name": "My WS",
        "ownerId": str(mock_sentinel_a.id),
        "type": "team",
        "memberCount": 1,
        "inboxThreshold": 0.9,
        "createdAt": "2026-05-17T00:00:00",
        "updatedAt": "2026-05-17T00:00:00",
    }
    app.dependency_overrides[get_workspace_service] = lambda: mock_service

    response = await client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers={"Authorization": "Bearer sentinel_a_token"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(workspace_id)
    assert body["memberCount"] == 1
