# 2026-09-26 실사용 준비 정검 Gate 0-A — 회의 가시성 파생 데이터 · 링크 API · PATCH · 메모 회귀 (real DB)
"""회의 가시성 규칙(링크 0개 통과 / 접근 가능한 링크 1개 이상 통과)이 회의에서 파생된 데이터
(RAG 청크 · 인박스 · 추출 액션)와 링크 변경 API 에도 똑같이 적용되는지 고정한다.

결함 ID 는 `docs/plans/active/2026-09-26-launch-readiness/report.md` §4:
- C-014 RAG 청크 (수동 연결·인박스 확정 회의의 청크 project_id NULL → 필터 통과)
- C-015 인박스 목록·조작
- C-016 추출 액션 목록·수정·promote
- C-017 프로젝트 PATCH (가시성 게이트 · archived admin 전용 · status Literal)
- C-018 회의↔프로젝트 링크 POST/DELETE · 인박스 classify
- C-020 (a) 메모 작성자 전용 (팀으로 올린 사본만 공유)
- 2026-09-27 결정: 프로젝트 작성자는 member 여도 자기 프로젝트 visibility 변경 가능

anti-hollow-green: 게이트 계층을 mock 하지 않는다 — 실제 service/repository 를 integration_session
(실 PostgreSQL + pgvector) 위에서 행사한다. 과잉 차단(볼 권한이 있는 사람까지 막힘) 대조군을 같이 둔다.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

pytestmark = pytest.mark.integration


def _vec(seed: int, dim: int = 1536) -> list[float]:
    base = 0.001 * (seed + 1)
    return [base + (i * 0.0001) for i in range(dim)]


QUERY_VEC = _vec(7)


@dataclass
class World:
    ws: uuid.UUID
    owner: uuid.UUID
    admin: uuid.UUID
    member: uuid.UUID
    viewer: uuid.UUID
    alpha: uuid.UUID  # public (owner 작성)
    beta: uuid.UUID  # draft (member 작성)
    gamma: uuid.UUID  # private, ProjectMember = admin · member
    delta: uuid.UUID  # private, ProjectMember = admin
    m_gamma: uuid.UUID  # Gamma 에만 연결, 청크 project_id NULL (수동 연결 경로)
    m_delta: uuid.UUID  # Delta 에만 연결
    m_both: uuid.UUID  # Alpha + Gamma 연결 (과잉 차단 대조군)
    m_none: uuid.UUID  # 링크 0개 (과잉 차단 대조군)
    m_stale: uuid.UUID  # 링크 0개인데 청크 project_id=Gamma 가 남은 회의 (과잉 차단 대조군)
    inbox: dict[str, uuid.UUID]
    actions: dict[str, uuid.UUID]


async def _user(session: AsyncSession, tag: str) -> uuid.UUID:
    from src.auth.models import User

    user = User(
        auth_user_id=f"ba_{uuid.uuid4().hex}",
        display_name=f"유저 {tag}",
        email=f"lr_{tag}_{uuid.uuid4().hex}@example.com",
    )
    session.add(user)
    await session.flush()
    return user.id


async def _project(session, ws, creator, visibility, title):
    from src.projects.models import Project

    p = Project(
        workspace_id=ws, title=title, created_by_id=creator,
        status="active", visibility=visibility,
    )
    session.add(p)
    await session.flush()
    return p.id


async def _meeting(session, ws, creator, title, links, chunk_project_id=None):
    from src.embeddings.models import EmbeddingChunk
    from src.meetings.models import Meeting
    from src.projects.models import MeetingProjectLink

    m = Meeting(
        workspace_id=ws, title=title, file_key=f"uploads/{uuid.uuid4().hex}.m4a",
        created_by_id=creator, status="completed",
        has_transcript=True, has_summary=True,
    )
    session.add(m)
    await session.flush()
    for pid in links:
        session.add(MeetingProjectLink(meeting_id=m.id, project_id=pid, workspace_id=ws))
    session.add(
        EmbeddingChunk(
            workspace_id=ws, project_id=chunk_project_id, source_id=m.id,
            source_type="meeting", chunk_text=f"{title} 본문 비밀",
            chunk_index=0, chunk_level=2, embedding=QUERY_VEC,
        )
    )
    await session.flush()
    return m.id


@pytest.fixture
async def world(integration_session: AsyncSession) -> World:
    from src.actions.models import ActionItem
    from src.inbox.models import InboxItem
    from src.projects.models import ProjectMember
    from src.workspaces.models import Workspace, WorkspaceMember

    s = integration_session
    owner = await _user(s, "owner")
    admin = await _user(s, "admin")
    member = await _user(s, "member")
    viewer = await _user(s, "viewer")
    ws_row = Workspace(name="QA Team", owner_id=owner, type="team")
    s.add(ws_row)
    await s.flush()
    ws = ws_row.id
    for uid, role in ((owner, "owner"), (admin, "admin"), (member, "member"), (viewer, "viewer")):
        s.add(WorkspaceMember(workspace_id=ws, user_id=uid, role=role))
    await s.flush()

    alpha = await _project(s, ws, owner, "public", "Alpha")
    beta = await _project(s, ws, member, "draft", "Beta")
    gamma = await _project(s, ws, admin, "private", "Gamma")
    delta = await _project(s, ws, admin, "private", "Delta")
    for pid, uid in ((gamma, admin), (gamma, member), (delta, admin)):
        s.add(ProjectMember(project_id=pid, workspace_id=ws, user_id=uid, role="member"))
    await s.flush()

    m_gamma = await _meeting(s, ws, admin, "감마회의", [gamma])
    m_delta = await _meeting(s, ws, admin, "델타회의", [delta])
    m_both = await _meeting(s, ws, admin, "양쪽회의", [alpha, gamma])
    m_none = await _meeting(s, ws, member, "무링크회의", [])
    m_stale = await _meeting(s, ws, admin, "잔재회의", [], chunk_project_id=gamma)

    inbox: dict[str, uuid.UUID] = {}
    actions: dict[str, uuid.UUID] = {}
    for key, mid in (
        ("gamma", m_gamma), ("delta", m_delta), ("both", m_both),
        ("none", m_none), ("stale", m_stale),
    ):
        item = InboxItem(
            workspace_id=ws, title=f"{key} 요약", summary=f"{key} 요약 원문",
            source_type="meeting", source_id=mid, is_processed=False,
        )
        s.add(item)
        act = ActionItem(workspace_id=ws, meeting_id=mid, title=f"{key} 액션")
        s.add(act)
        await s.flush()
        inbox[key] = item.id
        actions[key] = act.id
    # 회의와 무관한 수동 액션 (meeting_id NULL) — 전원에게 보여야 한다
    manual = ActionItem(workspace_id=ws, title="수동 액션")
    s.add(manual)
    await s.flush()
    actions["manual"] = manual.id
    await s.commit()
    return World(
        ws=ws, owner=owner, admin=admin, member=member, viewer=viewer,
        alpha=alpha, beta=beta, gamma=gamma, delta=delta,
        m_gamma=m_gamma, m_delta=m_delta, m_both=m_both, m_none=m_none,
        m_stale=m_stale, inbox=inbox, actions=actions,
    )


def _role(w: World, name: str) -> tuple[uuid.UUID, str]:
    return getattr(w, name), name


# ── C-014 · RAG 청크 ────────────────────────────────────────────────────────────


RAG_EXPECTED = {
    # 과잉 차단 대조군: m_both(Alpha 링크) · m_none · m_stale(링크 0개) 는 viewer 에게도 보인다
    "viewer": {"m_both", "m_none", "m_stale"},
    "member": {"m_gamma", "m_both", "m_none", "m_stale"},
    "admin": {"m_gamma", "m_delta", "m_both", "m_none", "m_stale"},
    "owner": {"m_gamma", "m_delta", "m_both", "m_none", "m_stale"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", sorted(RAG_EXPECTED))
async def test_rag_search_applies_meeting_rule(integration_session, world, role):
    from src.embeddings.repository import EmbeddingRepository

    uid, r = _role(world, role)
    repo = EmbeddingRepository(integration_session)
    rows = await repo.vector_search(
        QUERY_VEC, world.ws, requester_user_id=uid, requester_role=r, limit=50
    )
    id_to_key = {
        getattr(world, k): k for k in ("m_gamma", "m_delta", "m_both", "m_none", "m_stale")
    }
    got = {id_to_key[row["source_id"]] for row in rows if row["source_type"] == "meeting"}
    assert got == RAG_EXPECTED[role]


@pytest.mark.asyncio
async def test_rag_text_search_applies_same_rule(integration_session, world):
    from src.embeddings.repository import EmbeddingRepository

    await integration_session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    repo = EmbeddingRepository(integration_session)
    rows = await repo.text_search(
        "감마회의 본문 비밀", world.ws, requester_user_id=world.viewer,
        requester_role="viewer", limit=50,
    )
    assert world.m_gamma not in {r["source_id"] for r in rows}
    rows_member = await repo.text_search(
        "감마회의 본문 비밀", world.ws, requester_user_id=world.member,
        requester_role="member", limit=50,
    )
    assert world.m_gamma in {r["source_id"] for r in rows_member}


@pytest.mark.asyncio
async def test_rag_cache_hit_rechecks_meeting_rule(integration_session, world):
    """member 가 만든 캐시(감마 청크 포함)는 viewer 에게 miss, member 에게 hit."""
    from sqlmodel import select

    from src.embeddings.models import EmbeddingChunk, SemanticCache
    from src.embeddings.repository import EmbeddingRepository

    chunk = (await integration_session.exec(
        select(EmbeddingChunk).where(EmbeddingChunk.source_id == world.m_gamma)
    )).one()
    integration_session.add(SemanticCache(
        workspace_id=world.ws, question="감마 일정?", question_embedding=QUERY_VEC,
        answer="10월 20일", sources=[{"id": str(chunk.id), "sourceId": str(world.m_gamma)}],
        max_visibility="public",
    ))
    await integration_session.commit()
    repo = EmbeddingRepository(integration_session)
    assert await repo.find_similar_cache(
        QUERY_VEC, world.ws, requester_user_id=world.viewer, requester_role="viewer"
    ) is None
    hit = await repo.find_similar_cache(
        QUERY_VEC, world.ws, requester_user_id=world.member, requester_role="member"
    )
    assert hit is not None and hit["answer"] == "10월 20일"


# ── C-015 · 인박스 ──────────────────────────────────────────────────────────────


def _inbox_service(session):
    from src.inbox.repository import InboxRepository
    from src.inbox.service import InboxService
    from src.meetings.repository import MeetingRepository
    from src.projects.repository import ProjectRepository

    return InboxService(
        InboxRepository(session), ProjectRepository(session),
        meeting_repo=MeetingRepository(session),
    )


INBOX_EXPECTED = {
    "viewer": {"both", "none", "stale"},
    "member": {"gamma", "both", "none", "stale"},
    "admin": {"gamma", "delta", "both", "none", "stale"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", sorted(INBOX_EXPECTED))
async def test_inbox_list_and_total_apply_meeting_rule(integration_session, world, role):
    uid, r = _role(world, role)
    page = await _inbox_service(integration_session).list_inbox(
        world.ws, requester_user_id=uid, requester_role=r, page_size=50
    )
    key_by_id = {str(v): k for k, v in world.inbox.items()}
    got = {key_by_id[i["id"]] for i in page["items"]}
    assert got == INBOX_EXPECTED[role]
    assert page["total"] == len(INBOX_EXPECTED[role])  # list/count 동일 계약


@pytest.mark.asyncio
async def test_inbox_mutations_on_hidden_item_are_404(integration_session, world):
    from src.inbox.exceptions import InboxItemNotFoundError

    svc = _inbox_service(integration_session)
    with pytest.raises(InboxItemNotFoundError):
        await svc.dismiss(world.inbox["delta"], world.ws, world.member, "member")
    with pytest.raises(InboxItemNotFoundError):
        await svc.classify(
            world.inbox["delta"], world.ws, [world.alpha], world.member, "member"
        )


@pytest.mark.asyncio
async def test_inbox_classify_into_hidden_project_is_404_and_item_stays(
    integration_session, world
):
    """C-018 인박스 경로: 볼 수 있는 회의를 볼 수 없는 Delta 로 확정 → 404, 미처리 유지."""
    from src.inbox.models import InboxItem
    from src.projects.exceptions import ProjectNotFoundError

    svc = _inbox_service(integration_session)
    with pytest.raises(ProjectNotFoundError):
        await svc.classify(
            world.inbox["none"], world.ws, [world.delta], world.member, "member"
        )
    await integration_session.rollback()
    item = await integration_session.get(InboxItem, world.inbox["none"])
    assert item.is_processed is False
    # 대조군: 볼 수 있는 Alpha 로는 확정된다
    result = await svc.classify(
        world.inbox["none"], world.ws, [world.alpha], world.member, "member"
    )
    assert result["isProcessed"] is True
    assert result["linkedProjects"][0]["id"] == str(world.alpha)


# ── C-016 · 추출 액션 ───────────────────────────────────────────────────────────


def _action_service(session):
    from src.actions.repository import ActionItemRepository
    from src.actions.service import ActionItemService
    from src.meetings.repository import MeetingRepository
    from src.projects.repository import ProjectRepository
    from src.workspaces.repository import WorkspaceRepository

    return ActionItemService(
        ActionItemRepository(session), project_repo=ProjectRepository(session),
        meeting_repo=MeetingRepository(session),
        workspace_repo=WorkspaceRepository(session),
    )


ACTION_EXPECTED = {
    "viewer": {"both", "none", "stale", "manual"},
    "member": {"gamma", "both", "none", "stale", "manual"},
    "admin": {"gamma", "delta", "both", "none", "stale", "manual"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", sorted(ACTION_EXPECTED))
async def test_action_list_applies_meeting_rule(integration_session, world, role):
    uid, r = _role(world, role)
    page = await _action_service(integration_session).list_action_items(
        world.ws, page_size=50, requester_user_id=uid, requester_role=r
    )
    key_by_id = {str(v): k for k, v in world.actions.items()}
    got = {key_by_id[i["id"]] for i in page["items"]}
    assert got == ACTION_EXPECTED[role]
    assert page["total"] == len(ACTION_EXPECTED[role])


@pytest.mark.asyncio
async def test_action_update_and_promote_on_hidden_meeting_are_404(
    integration_session, world
):
    from fastapi import BackgroundTasks

    from src.actions.exceptions import ActionItemNotFoundError
    from src.workspaces.models import Workspace, WorkspaceMember

    svc = _action_service(integration_session)
    with pytest.raises(ActionItemNotFoundError):
        await svc.update_action_item(
            world.actions["delta"], world.ws, title="탈취",
            requester_user_id=world.member, requester_role="member",
        )
    # promote 대상 팀 WS (member 가 멤버)
    other = Workspace(name="Other", owner_id=world.member, type="team")
    integration_session.add(other)
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(workspace_id=other.id, user_id=world.member, role="owner")
    )
    await integration_session.commit()
    with pytest.raises(ActionItemNotFoundError):
        await svc.promote(
            action_id=world.actions["delta"], source_workspace_id=world.ws,
            target_workspace_id=other.id, promoted_by_user_id=world.member,
            background_tasks=BackgroundTasks(), requester_role="member",
        )
    # 대조군: 볼 수 있는 회의의 액션은 수정된다
    updated = await svc.update_action_item(
        world.actions["gamma"], world.ws, title="감마 액션 수정",
        requester_user_id=world.member, requester_role="member",
    )
    assert updated["title"] == "감마 액션 수정"


# ── C-018 · 회의↔프로젝트 링크 API ──────────────────────────────────────────────


def _project_service(session):
    from src.meetings.repository import MeetingRepository
    from src.projects.repository import ProjectRepository
    from src.projects.service import ProjectService
    from src.workspaces.repository import WorkspaceRepository

    return ProjectService(
        ProjectRepository(session), WorkspaceRepository(session),
        meeting_repo=MeetingRepository(session),
    )


async def _links(session, meeting_id) -> set[uuid.UUID]:
    from sqlmodel import select

    from src.projects.models import MeetingProjectLink

    rows = (await session.exec(
        select(MeetingProjectLink.project_id).where(
            MeetingProjectLink.meeting_id == meeting_id
        )
    )).all()
    return set(rows)


@pytest.mark.asyncio
async def test_link_hidden_meeting_to_public_project_is_404(integration_session, world):
    """T-09: member 가 숨겨진 Delta 회의를 Alpha 에 붙여 전원 공개 → 404, 링크 불변."""
    from src.meetings.exceptions import MeetingNotFoundError

    svc = _project_service(integration_session)
    with pytest.raises(MeetingNotFoundError):
        await svc.add_meeting_project(
            world.ws, world.m_delta, world.alpha, world.member, "member"
        )
    await integration_session.rollback()
    assert await _links(integration_session, world.m_delta) == {world.delta}


@pytest.mark.asyncio
async def test_unlink_hidden_meeting_is_404(integration_session, world):
    """T-10: member 가 숨겨진 회의의 private 링크를 끊어 링크 0개(=전원 공개) → 404."""
    from src.meetings.exceptions import MeetingNotFoundError

    svc = _project_service(integration_session)
    with pytest.raises(MeetingNotFoundError):
        await svc.remove_meeting_project(
            world.ws, world.m_delta, world.delta, world.member, "member"
        )
    await integration_session.rollback()
    assert await _links(integration_session, world.m_delta) == {world.delta}


@pytest.mark.asyncio
async def test_link_visible_meeting_to_hidden_project_is_404(integration_session, world):
    """T-11: 대상 프로젝트도 볼 수 있어야 한다."""
    from src.projects.exceptions import ProjectNotFoundError

    svc = _project_service(integration_session)
    with pytest.raises(ProjectNotFoundError):
        await svc.add_meeting_project(
            world.ws, world.m_none, world.delta, world.member, "member"
        )


@pytest.mark.asyncio
async def test_link_and_unlink_visible_pair_still_work(integration_session, world):
    """T-13 대조군 + T-20 경로: 볼 수 있는 회의 ↔ 볼 수 있는 프로젝트."""
    svc = _project_service(integration_session)
    link = await svc.add_meeting_project(
        world.ws, world.m_none, world.alpha, world.member, "member"
    )
    assert link["projectId"] == str(world.alpha)
    await svc.remove_meeting_project(
        world.ws, world.m_none, world.alpha, world.member, "member"
    )
    assert await _links(integration_session, world.m_none) == set()
    # admin 은 숨겨진 회의도 연결할 수 있다 (우회)
    await svc.add_meeting_project(
        world.ws, world.m_delta, world.alpha, world.admin, "admin"
    )
    assert await _links(integration_session, world.m_delta) == {world.delta, world.alpha}


# ── C-017 · 프로젝트 PATCH + 작성자 visibility 변경 ─────────────────────────────


@pytest.mark.asyncio
async def test_patch_hidden_project_is_404_including_empty_patch(integration_session, world):
    """T-14 / T-15: 안 보이는 Delta 는 수정도, 빈 PATCH 로 메타데이터 읽기도 404."""
    from src.projects.exceptions import ProjectNotFoundError
    from src.projects.models import Project

    svc = _project_service(integration_session)
    with pytest.raises(ProjectNotFoundError):
        await svc.update_project(
            world.ws, world.delta, description="x",
            requester_user_id=world.member, requester_role="member",
        )
    with pytest.raises(ProjectNotFoundError):
        await svc.update_project(
            world.ws, world.delta,
            requester_user_id=world.member, requester_role="member",
        )
    await integration_session.rollback()
    delta = await integration_session.get(Project, world.delta)
    assert delta.description is None


@pytest.mark.asyncio
async def test_member_cannot_archive_via_patch(integration_session, world):
    """T-16: archived 전환은 admin 전용 (/archive 우회 차단). 해제도 마찬가지."""
    from src.projects.exceptions import ProjectArchiveForbiddenError
    from src.projects.models import Project

    svc = _project_service(integration_session)
    with pytest.raises(ProjectArchiveForbiddenError):
        await svc.update_project(
            world.ws, world.alpha, status="archived",
            requester_user_id=world.member, requester_role="member",
        )
    # admin 은 가능
    await svc.update_project(
        world.ws, world.alpha, status="archived",
        requester_user_id=world.admin, requester_role="admin",
    )
    # 이미 보관된 프로젝트: member 가 같은 status 를 재전송하며 제목만 바꾸는 것은 허용
    out = await svc.update_project(
        world.ws, world.alpha, title="Alpha 2", status="archived",
        requester_user_id=world.member, requester_role="member",
    )
    assert out["title"] == "Alpha 2"
    with pytest.raises(ProjectArchiveForbiddenError):
        await svc.update_project(
            world.ws, world.alpha, status="active",
            requester_user_id=world.member, requester_role="member",
        )
    await integration_session.rollback()
    assert (await integration_session.get(Project, world.alpha)).status == "archived"


def test_patch_status_rejects_unknown_value():
    """T-17: status 는 Literal — 임의 문자열은 422 (스키마 검증)."""
    from pydantic import ValidationError

    from src.projects.schemas import UpdateProjectRequest

    with pytest.raises(ValidationError):
        UpdateProjectRequest(status="zzz")  # type: ignore[arg-type]
    assert UpdateProjectRequest(status="completed").status == "completed"


@pytest.mark.asyncio
async def test_creator_member_can_change_own_project_visibility(integration_session, world):
    """2026-09-27 결정: 작성자는 member 여도 자기 프로젝트 visibility 를 바꿀 수 있다.

    private 전환 시 작성자가 ProjectMember 로 보장돼 스스로 잠기지 않는다.
    """
    svc = _project_service(integration_session)
    out = await svc.update_project(
        world.ws, world.beta, visibility="private",
        requester_user_id=world.member, requester_role="member",
    )
    assert out["visibility"] == "private"
    got = await svc.get_project(
        world.ws, world.beta, requester_user_id=world.member, requester_role="member"
    )
    assert got["visibility"] == "private"
    out = await svc.update_project(
        world.ws, world.beta, visibility="public",
        requester_user_id=world.member, requester_role="member",
    )
    assert out["visibility"] == "public"


@pytest.mark.asyncio
async def test_non_creator_member_cannot_change_visibility(integration_session, world):
    from src.projects.exceptions import ProjectVisibilityChangeForbiddenError

    svc = _project_service(integration_session)
    with pytest.raises(ProjectVisibilityChangeForbiddenError):
        await svc.update_project(
            world.ws, world.alpha, visibility="private",
            requester_user_id=world.member, requester_role="member",
        )
    # 같은 값 재전송은 변경이 아니므로 허용 (편집 다이얼로그 전체 필드 전송 대비)
    out = await svc.update_project(
        world.ws, world.alpha, title="Alpha 제목", visibility="public",
        requester_user_id=world.member, requester_role="member",
    )
    assert out["title"] == "Alpha 제목"
    # admin 은 누구 프로젝트든 가능
    out = await svc.update_project(
        world.ws, world.alpha, visibility="draft",
        requester_user_id=world.admin, requester_role="admin",
    )
    assert out["visibility"] == "draft"


# ── C-020 (a) · 메모 작성자 전용 ────────────────────────────────────────────────


async def _memo(session, ws, user_id, content, is_shared=False):
    from src.embeddings.models import EmbeddingChunk
    from src.memory.models import MemoryItem

    item = MemoryItem(
        user_id=user_id, workspace_id=ws, type="text", raw_content=content,
        distilled_json={"title": content, "atomic_notes": [content]},
        status="active", is_shared=is_shared,
    )
    session.add(item)
    await session.flush()
    chunk = EmbeddingChunk(
        workspace_id=ws, source_id=item.id, source_type="memory",
        chunk_text=content, chunk_index=0, chunk_level=2, embedding=QUERY_VEC,
    )
    session.add(chunk)
    await session.flush()
    item.embedding_chunk_id = chunk.id
    await session.commit()
    return item.id


def _memory_service(session):
    from src.memory.pipeline_service import MemoryPipelineService
    from src.memory.repository import MemoryRepository
    from src.memory.service import MemoryService
    from src.workspaces.repository import WorkspaceRepository

    # session_factory / r2_service 는 BG task·음성 경로 전용 — 이 테스트는 호출하지 않는다
    return MemoryService(
        MemoryRepository(session), session_factory=None, r2_service=None,  # type: ignore[arg-type]
        workspace_repo=WorkspaceRepository(session), pipeline=MemoryPipelineService(),
    )


@pytest.mark.asyncio
async def test_memo_is_author_only_in_team_workspace(integration_session, world):
    """T-18: admin 이 팀 WS 에서 캡처한 메모 — viewer·member·owner 는 recall 0 · 상세 404."""
    from src.embeddings.repository import EmbeddingRepository
    from src.memory.exceptions import MemoryNotFoundError

    memo = await _memo(integration_session, world.ws, world.admin, "치과 예약 목요일")
    svc = _memory_service(integration_session)
    for uid in (world.viewer, world.member, world.owner):
        out = await svc.recall(world.ws, uid, "치과 예약", top_k=3)
        assert memo not in {src.memory_id for src in out.sources}
        with pytest.raises(MemoryNotFoundError):
            await svc.get_memory(memo, world.ws, uid)
    # 작성자 본인은 본다
    out = await svc.recall(world.ws, world.admin, "치과 예약", top_k=3)
    assert memo in {src.memory_id for src in out.sources}
    assert (await svc.get_memory(memo, world.ws, world.admin)).memory_id == memo

    # RAG 검색: owner(역할 우회 대상)도 남의 메모 청크는 못 받는다
    repo = EmbeddingRepository(integration_session)
    for uid, role in ((world.viewer, "viewer"), (world.owner, "owner")):
        rows = await repo.vector_search(
            QUERY_VEC, world.ws, requester_user_id=uid, requester_role=role, limit=50
        )
        assert memo not in {r["source_id"] for r in rows}
    rows = await repo.vector_search(
        QUERY_VEC, world.ws, requester_user_id=world.admin, requester_role="admin", limit=50
    )
    assert memo in {r["source_id"] for r in rows}


@pytest.mark.asyncio
async def test_shared_memo_is_visible_to_team(integration_session, world):
    """과잉 차단 대조군: 팀으로 올린 사본(is_shared)은 팀 전원이 본다."""
    from src.embeddings.repository import EmbeddingRepository

    memo = await _memo(
        integration_session, world.ws, world.admin, "공유 회의실 규칙", is_shared=True
    )
    svc = _memory_service(integration_session)
    out = await svc.recall(world.ws, world.viewer, "공유 회의실", top_k=3)
    assert memo in {src.memory_id for src in out.sources}
    assert (await svc.get_memory(memo, world.ws, world.viewer)).memory_id == memo
    rows = await EmbeddingRepository(integration_session).vector_search(
        QUERY_VEC, world.ws, requester_user_id=world.viewer,
        requester_role="viewer", limit=50,
    )
    assert memo in {r["source_id"] for r in rows}


@pytest.mark.asyncio
async def test_rag_cache_built_from_others_memo_misses_even_for_owner(
    integration_session, world
):
    from src.embeddings.models import SemanticCache
    from src.embeddings.repository import EmbeddingRepository
    from src.memory.models import MemoryItem

    memo = await _memo(integration_session, world.ws, world.admin, "비밀번호 힌트 고양이")
    chunk_id = (await integration_session.get(MemoryItem, memo)).embedding_chunk_id
    integration_session.add(SemanticCache(
        workspace_id=world.ws, question="힌트?", question_embedding=QUERY_VEC,
        answer="고양이", sources=[{"id": str(chunk_id), "sourceId": str(memo)}],
        max_visibility="public",
    ))
    await integration_session.commit()
    repo = EmbeddingRepository(integration_session)
    assert await repo.find_similar_cache(
        QUERY_VEC, world.ws, requester_user_id=world.owner, requester_role="owner"
    ) is None
    assert await repo.find_similar_cache(
        QUERY_VEC, world.ws, requester_user_id=world.admin, requester_role="admin"
    ) is not None


@pytest.mark.asyncio
async def test_member_cannot_promote_others_memo(integration_session, world):
    from fastapi import BackgroundTasks

    from src.memory.exceptions import MemoryNotFoundError
    from src.workspaces.models import Workspace, WorkspaceMember

    memo = await _memo(integration_session, world.ws, world.admin, "개인 메모")
    other = Workspace(name="Other", owner_id=world.member, type="team")
    integration_session.add(other)
    await integration_session.flush()
    integration_session.add(
        WorkspaceMember(workspace_id=other.id, user_id=world.member, role="owner")
    )
    await integration_session.commit()
    with pytest.raises(MemoryNotFoundError):
        await _memory_service(integration_session).promote(
            memory_id=memo, source_workspace_id=world.ws,
            target_workspace_id=other.id, promoted_by_user_id=world.member,
            background_tasks=BackgroundTasks(),
        )


# ── C-001 · 워크스페이스 목록 순서 ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_find_by_user_is_ordered_by_creation(integration_session, world):
    from datetime import datetime, timedelta

    from src.workspaces.models import Workspace, WorkspaceMember
    from src.workspaces.repository import WorkspaceRepository

    base = datetime(2026, 1, 1)
    ids = []
    for i, name in enumerate(("나중", "처음", "중간")):
        ws = Workspace(
            name=name, owner_id=world.viewer, type="team",
            created_at=base + timedelta(days=(2, 0, 1)[i]),
        )
        integration_session.add(ws)
        await integration_session.flush()
        integration_session.add(
            WorkspaceMember(workspace_id=ws.id, user_id=world.viewer, role="owner")
        )
        ids.append(ws.id)
    await integration_session.commit()
    names = [w.name for w in await WorkspaceRepository(integration_session).find_by_user(world.viewer)]
    # world.ws(QA Team, 가장 최근 생성)는 맨 뒤
    assert names[:3] == ["처음", "중간", "나중"]


# ── 2026-09-27 Evaluator 후속 (E1-01/02/03/05/10 · E2-01/02/07) ──────────────────


async def _file_action_under(session, world, meeting_id, project_id, title):
    """회의 액션을 프로젝트로 분류한 상태 (admin 이 PATCH projectId 로 옮긴 경우와 같다)."""
    from src.actions.models import ActionItem

    act = ActionItem(
        workspace_id=world.ws, meeting_id=meeting_id, project_id=project_id, title=title
    )
    session.add(act)
    await session.commit()
    return act.id


def _meeting_service(session):
    from src.actions.repository import ActionItemRepository
    from src.meetings.repository import MeetingRepository
    from src.meetings.service import MeetingService
    from src.projects.repository import ProjectRepository
    from src.workspaces.repository import WorkspaceRepository

    return MeetingService(
        MeetingRepository(session), action_repo=ActionItemRepository(session),
        project_repo=ProjectRepository(session), workspace_repo=WorkspaceRepository(session),
    )


@pytest.mark.asyncio
async def test_meeting_export_hides_actions_filed_under_hidden_project(
    integration_session, world
):
    """E1-01: 회의는 보여도 private 프로젝트로 분류된 액션은 export 에 나오지 않는다."""
    await _file_action_under(
        integration_session, world, world.m_none, world.delta, "델타로 옮긴 비밀 액션"
    )
    svc = _meeting_service(integration_session)
    for fmt in ("md", "json"):
        body, _, _ = await svc.export_meeting(
            world.m_none, world.ws, fmt,
            requester_user_id=world.member, requester_role="member",
        )
        assert "델타로 옮긴 비밀 액션" not in body
        assert "none 액션" in body  # 대조군: 프로젝트 미분류 액션은 그대로
    body, _, _ = await svc.export_meeting(
        world.m_none, world.ws, "md", requester_user_id=world.admin, requester_role="admin"
    )
    assert "델타로 옮긴 비밀 액션" in body


@pytest.mark.asyncio
async def test_meeting_promote_does_not_clone_actions_promoter_cannot_see(
    integration_session, world
):
    """E1-02: promote 사본 액션은 project_id=None 이라 대상 WS 전원이 본다 → 숨겨진 것은 복제 금지."""
    from sqlmodel import select

    from src.actions.models import ActionItem
    from src.common.promote_helpers import clone_action_items_for_promote
    from src.meetings.models import Meeting
    from src.workspaces.models import Workspace, WorkspaceMember

    await _file_action_under(
        integration_session, world, world.m_none, world.delta, "델타로 옮긴 비밀 액션"
    )
    other = Workspace(name="Other", owner_id=world.member, type="team")
    integration_session.add(other)
    await integration_session.flush()
    integration_session.add(WorkspaceMember(workspace_id=other.id, user_id=world.member, role="owner"))
    target = Meeting(
        workspace_id=other.id, title="사본", file_key="", created_by_id=world.member,
        status="completed",
    )
    integration_session.add(target)
    await integration_session.flush()
    n = await clone_action_items_for_promote(
        source_meeting_id=world.m_none, target_meeting_id=target.id,
        target_workspace_id=other.id, target_project_id=None,
        session=integration_session,
        requester_user_id=world.member, requester_role="member",
    )
    titles = set((await integration_session.exec(
        select(ActionItem.title).where(ActionItem.meeting_id == target.id)
    )).all())
    assert titles == {"none 액션"}
    assert n == 1


@pytest.mark.asyncio
async def test_cache_revalidation_treats_null_role_as_non_admin(integration_session, world):
    """E1-03: role=None 이 SQL NULL 로 들어가도 anti-join 이 fail-open 하지 않는다."""
    from sqlmodel import select

    from src.embeddings.models import EmbeddingChunk
    from src.embeddings.repository import EmbeddingRepository

    chunk_id = (await integration_session.exec(
        select(EmbeddingChunk.id).where(EmbeddingChunk.source_id == world.m_delta)
    )).one()
    repo = EmbeddingRepository(integration_session)
    assert await repo._all_chunks_visible([chunk_id], world.viewer, None) is False  # type: ignore[arg-type]
    assert await repo._all_chunks_visible([chunk_id], world.admin, "admin") is True


@pytest.mark.asyncio
async def test_action_create_and_patch_into_hidden_meeting_or_project_is_404(
    integration_session, world
):
    """E1-05: 숨겨진 회의·프로젝트 id 로 액션을 만들거나 옮기면 404 (존재 확인·끼워 넣기 차단)."""
    from src.meetings.exceptions import MeetingNotFoundError
    from src.projects.exceptions import ProjectNotFoundError

    svc = _action_service(integration_session)
    with pytest.raises(MeetingNotFoundError):
        await svc.create_action_item(
            world.ws, "끼워 넣기", meeting_id=world.m_delta,
            requester_user_id=world.member, requester_role="member",
        )
    with pytest.raises(ProjectNotFoundError):
        await svc.create_action_item(
            world.ws, "끼워 넣기", project_id=world.delta,
            requester_user_id=world.member, requester_role="member",
        )
    with pytest.raises(MeetingNotFoundError):
        await svc.update_action_item(
            world.actions["manual"], world.ws, meeting_id=world.m_delta,
            requester_user_id=world.member, requester_role="member",
        )
    await integration_session.rollback()
    # 대조군: 보이는 회의·프로젝트는 된다, admin 은 우회
    ok = await svc.create_action_item(
        world.ws, "정상", meeting_id=world.m_gamma, project_id=world.gamma,
        requester_user_id=world.member, requester_role="member",
    )
    assert ok["meetingId"] == str(world.m_gamma)
    await svc.create_action_item(
        world.ws, "admin", meeting_id=world.m_delta,
        requester_user_id=world.admin, requester_role="admin",
    )


@pytest.mark.asyncio
async def test_private_switch_adds_creator_only_when_creator_switches(
    integration_session, world
):
    """E1-10: admin 이 private 으로 바꾸면 작성자를 자동 추가하지 않는다 (멤버 구성은 admin 이 정함)."""
    from sqlmodel import select

    from src.projects.models import ProjectMember

    async def members(pid):
        return set((await integration_session.exec(
            select(ProjectMember.user_id).where(ProjectMember.project_id == pid)
        )).all())

    svc = _project_service(integration_session)
    await svc.update_project(
        world.ws, world.alpha, visibility="private",
        requester_user_id=world.admin, requester_role="admin",
    )
    assert world.owner not in await members(world.alpha)
    await svc.update_project(
        world.ws, world.beta, visibility="private",
        requester_user_id=world.member, requester_role="member",
    )
    assert world.member in await members(world.beta)


async def _team(session, owner_id, name, extra=()):
    from src.workspaces.models import Workspace, WorkspaceMember

    ws = Workspace(name=name, owner_id=owner_id, type="team")
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner_id, role="owner"))
    for uid, role in extra:
        session.add(WorkspaceMember(workspace_id=ws.id, user_id=uid, role=role))
    await session.commit()
    return ws.id


@pytest.mark.asyncio
async def test_memo_promote_marks_copy_shared_and_blocks_target_viewer(
    integration_session, world
):
    """E2-07: 사본은 is_shared=True. E2-01: 대상 WS 에서 viewer 인 사람은 올릴 수 없다."""
    from fastapi import BackgroundTasks

    from src.memory.exceptions import TargetWorkspaceInvalidError
    from src.memory.models import MemoryItem

    memo = await _memo(integration_session, world.ws, world.admin, "공유할 메모")
    as_viewer = await _team(integration_session, world.owner, "Viewer target", ((world.admin, "viewer"),))
    as_member = await _team(integration_session, world.owner, "Member target", ((world.admin, "member"),))
    svc = _memory_service(integration_session)
    with pytest.raises(TargetWorkspaceInvalidError):
        await svc.promote(
            memory_id=memo, source_workspace_id=world.ws, target_workspace_id=as_viewer,
            promoted_by_user_id=world.admin, background_tasks=BackgroundTasks(),
        )
    await integration_session.rollback()
    out = await svc.promote(
        memory_id=memo, source_workspace_id=world.ws, target_workspace_id=as_member,
        promoted_by_user_id=world.admin, background_tasks=BackgroundTasks(),
    )
    copy = await integration_session.get(MemoryItem, uuid.UUID(str(out.new_memory_id)))
    assert copy is not None and copy.is_shared is True and copy.workspace_id == as_member
    source = await integration_session.get(MemoryItem, memo)
    assert source is not None and source.is_shared is False


@pytest.mark.asyncio
async def test_non_author_cannot_repromote_shared_copy(integration_session, world):
    """E2-02: 팀이 볼 수 있는 공유 사본이어도 다른 WS 로 공유 범위를 넓히는 건 작성자만."""
    from fastapi import BackgroundTasks

    from src.memory.exceptions import MemoryPromoteForbiddenError

    shared = await _memo(integration_session, world.ws, world.admin, "공유 사본", is_shared=True)
    elsewhere = await _team(integration_session, world.member, "Member own team")
    with pytest.raises(MemoryPromoteForbiddenError):
        await _memory_service(integration_session).promote(
            memory_id=shared, source_workspace_id=world.ws, target_workspace_id=elsewhere,
            promoted_by_user_id=world.member, background_tasks=BackgroundTasks(),
        )
