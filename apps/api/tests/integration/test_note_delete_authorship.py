# BL-NOTE-DELETE-POLICY-1 — 노트 삭제 인가 매트릭스 (역할 × 작성자, real DB)
"""노트 삭제는 **작성자 본인 + admin 이상**만 가능하다 (2026-08-02 사용자 결정).

배경: 삭제는 되돌릴 수 없는 파괴적 액션이고 노트는 개인 저작물 성격이 강하다.
변경 전에는 라우터의 `require_member` + project visibility 게이트만 있어 **작성자 검사가 없었고**,
member 는 남이 쓴 노트를 삭제할 수 있었다.

게이트 순서가 계약이다 — visibility(404) 가 먼저, 작성자(403) 가 나중.
보이지 않는 노트의 존재를 403 으로 누출하지 않는다.

anti-hollow-green: 라우터 / RBAC(`require_member`) / `NotePipelineService` / repository 를 전부
실물로 두고 실 PostgreSQL(`integration_session`) 위에서 **HTTP 로** 행사한다. override 는
인증 신원(`get_current_user` — 실서명 JWT 는 이 테스트에서 재현 대상이 아님)과 DB 세션뿐이며,
이는 conftest 의 `memory_client` 픽스처와 동일한 선례다.
(참고: `tests/notes/test_notes_api.py` 는 `delete_note_with_cleanup` 을 AsyncMock 으로
대체하므로 인가 신호가 아니다.)
"""
from __future__ import annotations

import time
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# 시드 헬퍼 재사용 (R4) — 같은 도메인의 실 DB IDOR 테스트에서 이미 검증된 것들
from tests.integration.test_note_meeting_visibility_idor import (
    _add_project_member,
    _add_ws_member,
    _create_note,
    _create_project,
    _create_team_ws,
)

pytestmark = pytest.mark.integration


# --- 하네스 -----------------------------------------------------------------


async def _new_user(session: AsyncSession, tag: str):
    """`get_current_user` override 에 넣을 User 인스턴스."""
    from src.auth.models import User

    user = User(
        auth_user_id=f"ba_{uuid.uuid4().hex}",
        display_name=f"유저 {tag}",
        email=f"del_{tag}_{uuid.uuid4().hex}@example.com",
    )
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def as_user(integration_session: AsyncSession):
    """실 라우팅 + 실 RBAC HTTP 클라이언트. 요청 주체만 교체한다."""
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session, get_session_factory
    from src.main import app

    state: dict = {"user": None}

    def _dummy_factory():
        # DELETE 경로는 BG task 를 쓰지 않으므로 session_factory 는 미사용
        return None

    app.dependency_overrides[get_current_user] = lambda: state["user"]
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_session_factory] = _dummy_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        def _switch(user):
            state["user"] = user
            return client

        yield _switch

    app.dependency_overrides.clear()


def _delete_url(ws_id: uuid.UUID, note_id: uuid.UUID) -> str:
    return f"/api/v1/workspaces/{ws_id}/notes/{note_id}"


async def _note_exists(session: AsyncSession, note_id: uuid.UUID) -> bool:
    from src.notes.models import Note

    result = await session.exec(select(Note).where(Note.id == note_id))
    return result.first() is not None


# --- 매트릭스: 역할 × 작성자 --------------------------------------------------


class TestNoteDeleteAuthorship:
    """project_id=None 노트 — visibility 게이트가 개입하지 않는 순수 작성자 판정."""

    @pytest.mark.asyncio
    async def test_author_member_can_delete_own_note(
        self, integration_session: AsyncSession, as_user
    ):
        owner = await _new_user(integration_session, "owner")
        author = await _new_user(integration_session, "author")
        ws = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, ws, author.id, "member")
        note = await _create_note(integration_session, ws, None, author.id, "본인 노트")

        res = await as_user(author).delete(_delete_url(ws, note.id))

        assert res.status_code == 204, res.text
        assert not await _note_exists(integration_session, note.id)

    @pytest.mark.asyncio
    async def test_admin_can_delete_others_note(
        self, integration_session: AsyncSession, as_user
    ):
        owner = await _new_user(integration_session, "owner")
        author = await _new_user(integration_session, "author")
        admin = await _new_user(integration_session, "admin")
        ws = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, ws, author.id, "member")
        await _add_ws_member(integration_session, ws, admin.id, "admin")
        note = await _create_note(integration_session, ws, None, author.id, "남의 노트")

        res = await as_user(admin).delete(_delete_url(ws, note.id))

        assert res.status_code == 204, res.text
        assert not await _note_exists(integration_session, note.id)

    @pytest.mark.asyncio
    async def test_owner_can_delete_others_note(
        self, integration_session: AsyncSession, as_user
    ):
        owner = await _new_user(integration_session, "owner")
        author = await _new_user(integration_session, "author")
        ws = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, ws, author.id, "member")
        note = await _create_note(integration_session, ws, None, author.id, "남의 노트")

        res = await as_user(owner).delete(_delete_url(ws, note.id))

        assert res.status_code == 204, res.text
        assert not await _note_exists(integration_session, note.id)

    @pytest.mark.asyncio
    async def test_non_author_member_cannot_delete(
        self, integration_session: AsyncSession, as_user
    ):
        """핵심 회귀 — member 는 남의 노트를 삭제할 수 없다 (403, 노트 잔존)."""
        owner = await _new_user(integration_session, "owner")
        author = await _new_user(integration_session, "author")
        other = await _new_user(integration_session, "other")
        ws = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, ws, author.id, "member")
        await _add_ws_member(integration_session, ws, other.id, "member")
        note = await _create_note(integration_session, ws, None, author.id, "남의 노트")

        res = await as_user(other).delete(_delete_url(ws, note.id))

        assert res.status_code == 403, res.text
        # 부분 삭제가 일어나지 않았음을 확인 — 거부는 곧 보존이다
        assert await _note_exists(integration_session, note.id)

    @pytest.mark.asyncio
    async def test_non_author_member_can_still_read(
        self, integration_session: AsyncSession, as_user
    ):
        """403 을 고른 근거 — 읽기는 되는데 삭제만 막힌다 (404 로 숨길 실익이 없다)."""
        owner = await _new_user(integration_session, "owner")
        author = await _new_user(integration_session, "author")
        other = await _new_user(integration_session, "other")
        ws = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, ws, author.id, "member")
        await _add_ws_member(integration_session, ws, other.id, "member")
        note = await _create_note(integration_session, ws, None, author.id, "남의 노트")

        read = await as_user(other).get(_delete_url(ws, note.id))
        deleted = await as_user(other).delete(_delete_url(ws, note.id))

        assert read.status_code == 200, read.text
        assert deleted.status_code == 403, deleted.text

    @pytest.mark.asyncio
    async def test_viewer_cannot_delete_even_own_note(
        self, integration_session: AsyncSession, as_user
    ):
        """viewer 는 작성자여도 거부된다 — 라우터 `require_member` 가 앞에서 막는다."""
        owner = await _new_user(integration_session, "owner")
        viewer = await _new_user(integration_session, "viewer")
        ws = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, ws, viewer.id, "viewer")
        note = await _create_note(integration_session, ws, None, viewer.id, "viewer 노트")

        res = await as_user(viewer).delete(_delete_url(ws, note.id))

        assert res.status_code == 403, res.text
        assert await _note_exists(integration_session, note.id)


class TestNoteDeleteGateOrdering:
    """visibility(404) 가 작성자(403) 보다 앞선다 — 존재 누출 금지."""

    @pytest.mark.asyncio
    async def test_cross_workspace_note_is_404(
        self, integration_session: AsyncSession, as_user
    ):
        """두 워크스페이스 모두의 멤버라도, 경로 ws 에 없는 노트는 404 (기존 IDOR 계약)."""
        owner = await _new_user(integration_session, "owner")
        roamer = await _new_user(integration_session, "roamer")
        ws_a = await _create_team_ws(integration_session, owner.id)
        ws_b = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, ws_a, roamer.id, "member")
        await _add_ws_member(integration_session, ws_b, roamer.id, "member")
        # 노트는 ws_b 소속, 요청은 ws_a 경로로
        note = await _create_note(integration_session, ws_b, None, owner.id, "B 노트")

        res = await as_user(roamer).delete(_delete_url(ws_a, note.id))

        assert res.status_code == 404, res.text
        assert await _note_exists(integration_session, note.id)

    @pytest.mark.asyncio
    async def test_non_project_member_gets_404_not_403(
        self, integration_session: AsyncSession, as_user
    ):
        """private 프로젝트 비-멤버는 403(작성자 아님)이 아니라 404 를 받아야 한다."""
        owner = await _new_user(integration_session, "owner")
        outsider = await _new_user(integration_session, "outsider")
        ws = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, ws, outsider.id, "member")
        project = await _create_project(integration_session, ws, owner.id, "private")
        note = await _create_note(
            integration_session, ws, project.id, owner.id, "비밀 노트"
        )

        res = await as_user(outsider).delete(_delete_url(ws, note.id))

        assert res.status_code == 404, res.text
        assert await _note_exists(integration_session, note.id)

    @pytest.mark.asyncio
    async def test_project_member_author_can_delete_in_private_project(
        self, integration_session: AsyncSession, as_user
    ):
        """visibility 통과 + 작성자 → 허용 (허용 경로를 과잉 차단하지 않는다)."""
        owner = await _new_user(integration_session, "owner")
        insider = await _new_user(integration_session, "insider")
        ws = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, ws, insider.id, "member")
        project = await _create_project(integration_session, ws, owner.id, "private")
        await _add_project_member(integration_session, project.id, ws, insider.id)
        note = await _create_note(
            integration_session, ws, project.id, insider.id, "본인 노트"
        )

        res = await as_user(insider).delete(_delete_url(ws, note.id))

        assert res.status_code == 204, res.text
        assert not await _note_exists(integration_session, note.id)

    @pytest.mark.asyncio
    async def test_project_member_non_author_is_403_in_private_project(
        self, integration_session: AsyncSession, as_user
    ):
        """visibility 통과했어도 작성자가 아니면 403 (404 아님 — 이미 읽을 수 있는 노트다)."""
        owner = await _new_user(integration_session, "owner")
        insider = await _new_user(integration_session, "insider")
        ws = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, ws, insider.id, "member")
        project = await _create_project(integration_session, ws, owner.id, "private")
        await _add_project_member(integration_session, project.id, ws, insider.id)
        note = await _create_note(
            integration_session, ws, project.id, owner.id, "남의 노트"
        )

        res = await as_user(insider).delete(_delete_url(ws, note.id))

        assert res.status_code == 403, res.text
        assert await _note_exists(integration_session, note.id)


class TestDestructiveRouteCacheFreshness:
    @pytest.mark.asyncio
    async def test_stale_admin_cache_cannot_change_project_visibility(
        self, integration_session: AsyncSession, as_user
    ):
        """강등 직후에도 project PATCH 는 DB의 member role 로 거부한다."""
        from src.auth import rbac as auth_rbac
        from src.workspaces.models import WorkspaceMember

        owner = await _new_user(integration_session, "owner")
        downgraded_user = await _new_user(integration_session, "downgraded")
        workspace_id = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(
            integration_session, workspace_id, downgraded_user.id, "member"
        )
        project = await _create_project(
            integration_session, workspace_id, owner.id, "public"
        )
        cached_admin = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=downgraded_user.id,
            role="admin",
        )
        auth_rbac._MEMBER_CACHE[(workspace_id, downgraded_user.id)] = (
            cached_admin,
            time.time() + auth_rbac._MEMBER_CACHE_TTL_SEC,
        )

        response = await as_user(downgraded_user).patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project.id}",
            json={"visibility": "private"},
        )

        assert response.status_code == 403, response.text

    @pytest.mark.asyncio
    async def test_fresh_member_gate_allows_db_admin(
        self, integration_session: AsyncSession, as_user
    ):
        """파괴적 경로도 정상 DB admin을 과잉 차단하지 않는다."""

        owner = await _new_user(integration_session, "owner")
        admin_user = await _new_user(integration_session, "admin")
        workspace_id = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(integration_session, workspace_id, admin_user.id, "admin")
        project = await _create_project(
            integration_session, workspace_id, owner.id, "public"
        )
        response = await as_user(admin_user).patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project.id}",
            json={"visibility": "private"},
        )

        assert response.status_code == 200, response.text

    @pytest.mark.asyncio
    async def test_get_route_keeps_stale_admin_cache_behavior(
        self, integration_session: AsyncSession, as_user
    ):
        """GET은 의도적으로 캐시를 사용하므로 stale admin role 이 private project를 읽는다."""
        from src.auth import rbac as auth_rbac
        from src.workspaces.models import WorkspaceMember

        owner = await _new_user(integration_session, "owner")
        downgraded_user = await _new_user(integration_session, "downgraded")
        workspace_id = await _create_team_ws(integration_session, owner.id)
        await _add_ws_member(
            integration_session, workspace_id, downgraded_user.id, "member"
        )
        project = await _create_project(
            integration_session, workspace_id, owner.id, "private"
        )
        cached_admin = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=downgraded_user.id,
            role="admin",
        )
        auth_rbac._MEMBER_CACHE[(workspace_id, downgraded_user.id)] = (
            cached_admin,
            time.time() + auth_rbac._MEMBER_CACHE_TTL_SEC,
        )

        response = await as_user(downgraded_user).get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project.id}"
        )

        assert response.status_code == 200, response.text
