# Sprint 28 QA sweep — 데이터 상태 엣지 2건 경험적(empirical) 증거 테스트.
"""QA 보고서용 deterministic 증거. 로컬 TestContainers PostgreSQL 전용 (프로덕션 Neon 아님).

각 테스트는 "바람직한 동작"이 아니라 **실제 동작을 문서화**한다.

대상 2건:
  1. Pagination contract — notes list (page1=20 / page2=5 / total=25 / hasNext).
     서비스 응답 shape: items / total / page / pageSize / hasNext (notes/service.py:129-135).
  2. Archived project list-filter — status 필터 미지정 시 archived project 가
     기본 목록에 노출되는지 결정적 실측 (projects/repository.py:46 `if status:`).
"""
import uuid

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.notes.models import Note
from src.notes.repository import NoteRepository
from src.notes.service import NoteService
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.models import Workspace, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository

pytestmark = pytest.mark.integration


# ─── 공통 헬퍼 (test_rbac_edges_s28b.py 패턴 복제) ──────────────────────────


async def _make_user(session: AsyncSession, name: str = "유저") -> User:
    user = User(
        clerk_id=f"clerk_{uuid.uuid4().hex}",
        display_name=name,
        email=f"{uuid.uuid4().hex}@kairos.test",
    )
    session.add(user)
    await session.flush()
    return user


async def _make_team_ws(session: AsyncSession, owner_id: uuid.UUID) -> Workspace:
    ws = Workspace(name="QA 팀", owner_id=owner_id, type="team")
    session.add(ws)
    await session.flush()
    return ws


async def _add_member(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = "owner",
) -> WorkspaceMember:
    m = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role)
    session.add(m)
    await session.flush()
    return m


def _note_service(session: AsyncSession) -> NoteService:
    return NoteService(repo=NoteRepository(session))


def _project_service(session: AsyncSession) -> ProjectService:
    return ProjectService(
        repo=ProjectRepository(session),
        ws_repo=WorkspaceRepository(session),
    )


# ─── 1. Pagination contract (notes list) ────────────────────────────────────


async def test_notes_pagination_contract_page1_and_page2(
    integration_session: AsyncSession,
):
    """25개 노트 seed → page1(size=20)=20개 hasNext=True / page2=5개 hasNext=False.

    EVIDENCE: NoteService.list_notes 응답 shape = items / total / page / pageSize /
    hasNext (notes/service.py:129-135). hasNext = page * page_size < total.
    seed 는 repo.save() 로 batch (25 HTTP 호출 아님) — 단일 트랜잭션 flush + commit.
    """
    owner = await _make_user(integration_session, "오너")
    ws = await _make_team_ws(integration_session, owner.id)
    await _add_member(integration_session, ws.id, owner.id, "owner")

    # repo 레이어로 25개 batch seed (HTTP 25회 아님).
    repo = NoteRepository(integration_session)
    for i in range(25):
        await repo.save(
            Note(
                workspace_id=ws.id,
                title=f"노트 {i:02d}",
                content={},
                plain_text=f"본문 {i}",
                created_by_id=owner.id,
            )
        )
    await integration_session.commit()

    service = _note_service(integration_session)

    # page 1 (pageSize=20)
    page1 = await service.list_notes(workspace_id=ws.id, page=1, page_size=20)
    # 정확한 응답 필드명 검증 (notes/service.py:129-135)
    assert set(page1.keys()) == {"items", "total", "page", "pageSize", "hasNext"}
    assert len(page1["items"]) == 20
    assert page1["total"] == 25
    assert page1["page"] == 1
    assert page1["pageSize"] == 20
    assert page1["hasNext"] is True

    # page 2 (pageSize=20) → 나머지 5개, hasNext=False
    page2 = await service.list_notes(workspace_id=ws.id, page=2, page_size=20)
    assert len(page2["items"]) == 5
    assert page2["total"] == 25
    assert page2["page"] == 2
    assert page2["pageSize"] == 20
    assert page2["hasNext"] is False


# ─── 2. Archived project list-filter 동작 (열린 질문 결판) ──────────────────


async def test_archived_project_appears_in_unfiltered_list(
    integration_session: AsyncSession,
):
    """status 필터 미지정 /projects 기본 목록에 archived project 가 노출되는지 실측.

    DEFINITIVE FINDING: projects/repository.py:46 의 `if status:` 는 status query 가
    들어올 때만 WHERE Project.status == status 를 적용한다. status=None(미지정) 이면
    분기를 타지 않아 active + archived 가 **모두** 반환된다.
    → archived project 는 기본 grid 에 누설된다 (YES). 본 테스트는 ACTUAL 동작을 assert.
    """
    owner = await _make_user(integration_session, "오너")
    ws = await _make_team_ws(integration_session, owner.id)
    await _add_member(integration_session, ws.id, owner.id, "owner")
    await integration_session.commit()

    service = _project_service(integration_session)

    # active project 1개 (status 기본값 'active')
    active = await service.create_project(
        workspace_id=ws.id, title="활성 프로젝트", created_by_id=owner.id
    )
    # archived project 1개 — create 후 archive_project (status → 'archived')
    to_archive = await service.create_project(
        workspace_id=ws.id, title="아카이브 프로젝트", created_by_id=owner.id
    )
    archived = await service.archive_project(
        workspace_id=ws.id, project_id=uuid.UUID(to_archive["id"])
    )
    assert archived["status"] == "archived"

    # owner 권한으로 조회 (visibility 필터 우회) — status 필터 미지정.
    unfiltered = await service.list_projects(
        workspace_id=ws.id,
        requester_user_id=owner.id,
        requester_role="owner",
        status=None,
    )
    statuses = {p["status"] for p in unfiltered["items"]}
    ids = {p["id"] for p in unfiltered["items"]}

    # DEFINITIVE: archived 가 기본(필터 미지정) 목록에 포함된다 (YES, 누설).
    assert unfiltered["total"] == 2, (
        f"필터 미지정 시 active+archived 모두 카운트되어야 함. statuses={statuses}"
    )
    assert "archived" in statuses, (
        "archived project 가 기본 목록에 노출됨 (projects/repository.py:46 `if status:` 미적용)"
    )
    assert "active" in statuses
    assert active["id"] in ids and to_archive["id"] in ids


async def test_status_active_filter_excludes_archived(
    integration_session: AsyncSession,
):
    """GET /projects?status=active → active 만 반환 (archived 제외)."""
    owner = await _make_user(integration_session, "오너")
    ws = await _make_team_ws(integration_session, owner.id)
    await _add_member(integration_session, ws.id, owner.id, "owner")
    await integration_session.commit()

    service = _project_service(integration_session)
    active = await service.create_project(
        workspace_id=ws.id, title="활성", created_by_id=owner.id
    )
    to_archive = await service.create_project(
        workspace_id=ws.id, title="아카이브", created_by_id=owner.id
    )
    await service.archive_project(
        workspace_id=ws.id, project_id=uuid.UUID(to_archive["id"])
    )

    result = await service.list_projects(
        workspace_id=ws.id,
        requester_user_id=owner.id,
        requester_role="owner",
        status="active",
    )
    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["id"] == active["id"]
    assert result["items"][0]["status"] == "active"


async def test_status_archived_filter_returns_only_archived(
    integration_session: AsyncSession,
):
    """GET /projects?status=archived → archived 만 반환 (active 제외)."""
    owner = await _make_user(integration_session, "오너")
    ws = await _make_team_ws(integration_session, owner.id)
    await _add_member(integration_session, ws.id, owner.id, "owner")
    await integration_session.commit()

    service = _project_service(integration_session)
    await service.create_project(
        workspace_id=ws.id, title="활성", created_by_id=owner.id
    )
    to_archive = await service.create_project(
        workspace_id=ws.id, title="아카이브", created_by_id=owner.id
    )
    await service.archive_project(
        workspace_id=ws.id, project_id=uuid.UUID(to_archive["id"])
    )

    result = await service.list_projects(
        workspace_id=ws.id,
        requester_user_id=owner.id,
        requester_role="owner",
        status="archived",
    )
    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0]["id"] == to_archive["id"]
    assert result["items"][0]["status"] == "archived"
