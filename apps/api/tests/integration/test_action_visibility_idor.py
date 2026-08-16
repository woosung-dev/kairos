# F1/F2 — action-item list/update visibility-residue IDOR 회귀 (real DB)
"""private/draft 프로젝트에 속한 ActionItem 을 ProjectMember 가 아닌 워크스페이스
멤버가 list 로 읽거나 update 로 수정하는 visibility-residue IDOR 회귀 가드.

배경 (2026-06-23 fullsweep QA-1/QA-2):
- list_action_items/update_action_item 은 workspace_id(I-9)만 필터하고 project
  visibility 게이트가 없어, private/draft project 의 ActionItem(title/description=회의
  결정·태스크 L2) 이 비-ProjectMember 워크스페이스 멤버에게 노출/수정 가능했다.
- 기대: notes(CAND-A)와 동일한 게이트 — list 는 비-멤버에게 private/draft 액션을
  제외, update 는 비-멤버 → 404. admin/owner 우회, public/null project 는 통과.

anti-hollow-green: service mock 금지 — 실제 ActionItemService + repository seam 을
integration_session(실 PostgreSQL) 위에서 직접 행사한다.
"""
from __future__ import annotations

import uuid

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from src.actions.exceptions import ActionItemNotFoundError
from src.actions.repository import ActionItemRepository
from src.actions.service import ActionItemService
from src.projects.repository import ProjectRepository
from tests.integration.test_note_meeting_visibility_idor import (
    _add_project_member,
    _add_ws_member,
    _create_project,
    _create_team_ws,
    _create_user,
)

pytestmark = pytest.mark.integration


async def _create_action(
    session: AsyncSession,
    ws_id: uuid.UUID,
    project_id: uuid.UUID | None,
    title: str,
):
    from src.actions.models import ActionItem

    item = ActionItem(workspace_id=ws_id, project_id=project_id, title=title)
    session.add(item)
    await session.flush()
    return item


def _svc(session: AsyncSession) -> ActionItemService:
    return ActionItemService(
        repo=ActionItemRepository(session),
        project_repo=ProjectRepository(session),
    )


def _titles(result: dict) -> set[str]:
    return {i["title"] for i in result["items"]}


# --- LIST: read IDOR (F1) ----------------------------------------------------


class TestActionListPrivateVisibilityIDOR:
    @pytest.mark.asyncio
    async def test_non_member_cannot_list_private_action(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        outsider = await _create_user(integration_session, "out")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, outsider, "member")
        project = await _create_project(integration_session, ws, owner, "private")
        await _create_action(integration_session, ws, project.id, "PRIVATE_ACTION")

        result = await _svc(integration_session).list_action_items(
            ws, requester_user_id=outsider, requester_role="member"
        )
        assert "PRIVATE_ACTION" not in _titles(result)
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_project_member_can_list_private_action(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        insider = await _create_user(integration_session, "in")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, insider, "member")
        project = await _create_project(integration_session, ws, owner, "private")
        await _add_project_member(integration_session, project.id, ws, insider)
        await _create_action(integration_session, ws, project.id, "PRIVATE_ACTION")

        result = await _svc(integration_session).list_action_items(
            ws, requester_user_id=insider, requester_role="member"
        )
        assert "PRIVATE_ACTION" in _titles(result)

    @pytest.mark.asyncio
    async def test_admin_bypasses_private_action_list(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        admin = await _create_user(integration_session, "admin")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, admin, "admin")
        project = await _create_project(integration_session, ws, owner, "private")
        await _create_action(integration_session, ws, project.id, "PRIVATE_ACTION")

        result = await _svc(integration_session).list_action_items(
            ws, requester_user_id=admin, requester_role="admin"
        )
        assert "PRIVATE_ACTION" in _titles(result)

    @pytest.mark.asyncio
    async def test_non_creator_cannot_list_draft_action(
        self, integration_session: AsyncSession
    ):
        creator = await _create_user(integration_session, "creator")
        other = await _create_user(integration_session, "other")
        ws = await _create_team_ws(integration_session, creator)
        await _add_ws_member(integration_session, ws, other, "member")
        project = await _create_project(integration_session, ws, creator, "draft")
        await _create_action(integration_session, ws, project.id, "DRAFT_ACTION")

        result = await _svc(integration_session).list_action_items(
            ws, requester_user_id=other, requester_role="member"
        )
        assert "DRAFT_ACTION" not in _titles(result)

    @pytest.mark.asyncio
    async def test_public_and_null_project_action_visible(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        member = await _create_user(integration_session, "mem")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, member, "member")
        public = await _create_project(integration_session, ws, owner, "public")
        await _create_action(integration_session, ws, public.id, "PUBLIC_ACTION")
        await _create_action(integration_session, ws, None, "UNSCOPED_ACTION")

        result = await _svc(integration_session).list_action_items(
            ws, requester_user_id=member, requester_role="member"
        )
        assert {"PUBLIC_ACTION", "UNSCOPED_ACTION"} <= _titles(result)


# --- UPDATE: write IDOR (F2) -------------------------------------------------


class TestActionUpdatePrivateVisibilityIDOR:
    @pytest.mark.asyncio
    async def test_non_member_cannot_update_private_action(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        outsider = await _create_user(integration_session, "out")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, outsider, "member")
        project = await _create_project(integration_session, ws, owner, "private")
        action = await _create_action(integration_session, ws, project.id, "PRIVATE")

        with pytest.raises(ActionItemNotFoundError):
            await _svc(integration_session).update_action_item(
                action_id=action.id,
                workspace_id=ws,
                status="cancelled",
                requester_user_id=outsider,
                requester_role="member",
            )

    @pytest.mark.asyncio
    async def test_project_member_can_update_private_action(
        self, integration_session: AsyncSession
    ):
        owner = await _create_user(integration_session, "owner")
        insider = await _create_user(integration_session, "in")
        ws = await _create_team_ws(integration_session, owner)
        await _add_ws_member(integration_session, ws, insider, "member")
        project = await _create_project(integration_session, ws, owner, "private")
        await _add_project_member(integration_session, project.id, ws, insider)
        action = await _create_action(integration_session, ws, project.id, "PRIVATE")

        result = await _svc(integration_session).update_action_item(
            action_id=action.id,
            workspace_id=ws,
            status="cancelled",
            requester_user_id=insider,
            requester_role="member",
        )
        assert result["status"] == "cancelled"
