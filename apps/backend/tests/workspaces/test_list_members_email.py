# 멤버 목록 API 가 User.email 을 실제로 실어 보내는지 검증 (QA-0617-F)
"""GET /workspaces/{wid}/members 응답의 email 필드가 User.email 에서 채워지는지
실 DB 로 검증. 라이브에서 email:"" 로 비어 보이던 원인은 seed user 의 email 이
실제 빈 문자열(lazy-seed claims.get("email","")) 이었던 것 — 직렬화 경로 자체는
User.email 을 반환해야 한다 (조작/하드코딩 금지).
"""
import uuid

import pytest

from src.auth.models import User
from src.auth.repository import UserRepository
from src.workspaces.invite_service import InviteService
from src.workspaces.models import Workspace, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository


def _make_service(session) -> InviteService:
    return InviteService(
        repo=WorkspaceRepository(session),
        user_repo=UserRepository(session),
    )


@pytest.mark.asyncio
async def test_list_members_email_wired_from_user(integration_session):
    """멤버 목록의 email/displayName 이 User row 에서 정확히 채워진다."""
    user = User(
        clerk_id=f"clerk_{uuid.uuid4()}",
        display_name="홍길동",
        email="gildong@kairos.test",
    )
    integration_session.add(user)
    await integration_session.flush()

    ws = Workspace(name="팀", owner_id=user.id, type="team")
    integration_session.add(ws)
    await integration_session.flush()

    member = WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="owner")
    integration_session.add(member)
    await integration_session.flush()

    service = _make_service(integration_session)
    members = await service.list_members(ws.id)

    assert len(members) == 1
    m = members[0]
    # email/displayName 이 User row 에서 정확히 채워져야 (비어있지 않아야)
    assert m["email"] == "gildong@kairos.test"
    assert m["email"]  # non-empty
    assert m["displayName"] == "홍길동"
    assert m["role"] == "owner"
    assert m["userId"] == str(user.id)


@pytest.mark.asyncio
async def test_list_members_email_is_real_user_email_not_blank(integration_session):
    """User.email 이 채워진 경우 응답 email 도 동일 값 (빈 문자열로 떨어지지 않음)."""
    user = User(
        clerk_id=f"clerk_{uuid.uuid4()}",
        display_name="Acceptor",
        email="acceptor@kairos.test",
    )
    owner = User(
        clerk_id=f"clerk_{uuid.uuid4()}",
        display_name="Owner",
        email="owner@kairos.test",
    )
    integration_session.add(user)
    integration_session.add(owner)
    await integration_session.flush()

    ws = Workspace(name="팀", owner_id=owner.id, type="team")
    integration_session.add(ws)
    await integration_session.flush()

    integration_session.add(
        WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner")
    )
    integration_session.add(
        WorkspaceMember(workspace_id=ws.id, user_id=user.id, role="member")
    )
    await integration_session.flush()

    service = _make_service(integration_session)
    members = await service.list_members(ws.id)

    by_email = {m["email"] for m in members}
    assert by_email == {"owner@kairos.test", "acceptor@kairos.test"}
    assert "" not in by_email  # 어느 멤버도 빈 email 로 떨어지지 않음
