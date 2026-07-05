# 프로젝트 삭제 시 join 행(ProjectMember/MeetingProjectLink) 정리 — FK 500 회귀 가드 (2026-07-05 T20 발견)
"""BUG-PROJECT-DELETE-FK: private 생성 시 creator 가 ProjectMember 로 자동 추가(락아웃 fix)되면서
DELETE /projects/{id} 가 fk_project_members_project_workspace 위반으로 500.
delete_project 는 join 행(멤버십/미팅 링크)을 같은 트랜잭션에서 먼저 지워야 한다.
콘텐츠 FK(notes/actions 의 project_id)는 별도 정책 결정 (REFACTORING-BACKLOG 등재).
"""
import uuid

import pytest
from sqlalchemy import text as sa_text

from src.actions.models import ActionItem
from src.auth.models import User
from src.embeddings.models import EmbeddingChunk, SemanticCache
from src.inbox.models import InboxItem
from src.meetings.models import Meeting
from src.memory.models import MemoryItem, PromotionAudit
from src.notes.models import Note
from src.projects.exceptions import ProjectHasContentError
from src.projects.models import MeetingProjectLink, Project, ProjectMember
from src.projects.repository import ProjectRepository
from src.projects.service import ProjectService
from src.workspaces.models import Workspace, WorkspaceMember
from src.workspaces.repository import WorkspaceRepository


async def _count(session, table: str, project_id: uuid.UUID) -> int:
    result = await session.execute(
        sa_text(f"SELECT COUNT(*) FROM {table} WHERE project_id = :pid"),
        {"pid": str(project_id)},
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_delete_project_removes_members_and_meeting_links(integration_session):
    """멤버십 + 미팅 링크가 있는 프로젝트 삭제가 FK 위반 없이 완료 + join 행 0."""
    session = integration_session
    owner = User(
        clerk_id=f"clerk_pdel_{uuid.uuid4()}",
        display_name="pdel",
        email=f"pdel_{uuid.uuid4()}@del.test",
    )
    session.add(owner)
    await session.flush()

    ws = Workspace(name="pdel ws", owner_id=owner.id, type="team")
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner"))

    project = Project(
        workspace_id=ws.id, title="pdel-private", created_by_id=owner.id,
        visibility="private",
    )
    session.add(project)
    await session.flush()
    session.add(
        ProjectMember(project_id=project.id, workspace_id=ws.id, user_id=owner.id)
    )
    meeting = Meeting(
        workspace_id=ws.id, title="pdel-m", file_key="pdel/m.webm",
        created_by_id=owner.id,
    )
    session.add(meeting)
    await session.flush()
    session.add(
        MeetingProjectLink(
            meeting_id=meeting.id, project_id=project.id, workspace_id=ws.id
        )
    )
    await session.flush()
    project_id = project.id

    service = ProjectService(
        repo=ProjectRepository(session), ws_repo=WorkspaceRepository(session)
    )
    await service.delete_project(ws.id, project_id)

    assert await _count(session, "project_members", project_id) == 0
    assert await _count(session, "meeting_project_links", project_id) == 0
    result = await session.execute(
        sa_text("SELECT COUNT(*) FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )
    assert int(result.scalar_one()) == 0


# ── BL-S27e-5: 콘텐츠 FK 정책 (notes/actions 409-block, 파생 DELETE/SET NULL) ──

async def _seed_base(session, visibility: str = "private"):
    """owner + team ws + owner 멤버 + 프로젝트 시드. 반환 (owner, ws, project)."""
    owner = User(
        clerk_id=f"clerk_pdel_{uuid.uuid4()}",
        display_name="pdel",
        email=f"pdel_{uuid.uuid4()}@del.test",
    )
    session.add(owner)
    await session.flush()
    ws = Workspace(name="pdel ws", owner_id=owner.id, type="team")
    session.add(ws)
    await session.flush()
    session.add(WorkspaceMember(workspace_id=ws.id, user_id=owner.id, role="owner"))
    project = Project(
        workspace_id=ws.id, title="pdel-p", created_by_id=owner.id,
        visibility=visibility,
    )
    session.add(project)
    await session.flush()
    return owner, ws, project


def _service(session) -> ProjectService:
    return ProjectService(
        repo=ProjectRepository(session), ws_repo=WorkspaceRepository(session)
    )


async def _project_count(session, project_id: uuid.UUID) -> int:
    result = await session.execute(
        sa_text("SELECT COUNT(*) FROM projects WHERE id = :pid"),
        {"pid": str(project_id)},
    )
    return int(result.scalar_one())


@pytest.mark.asyncio
async def test_delete_project_with_notes_blocked_409(integration_session):
    """콘텐츠(노트) 연결 프로젝트 삭제 → 409, 프로젝트/노트 보존."""
    session = integration_session
    owner, ws, project = await _seed_base(session)
    session.add(Note(
        workspace_id=ws.id, project_id=project.id, created_by_id=owner.id, title="n"
    ))
    await session.flush()

    with pytest.raises(ProjectHasContentError) as exc:
        await _service(session).delete_project(ws.id, project.id)
    assert exc.value.status_code == 409
    # 409 는 mutation 이전(pre-check)에 발생 → 세션 정상, 프로젝트/노트 보존.
    assert await _project_count(session, project.id) == 1
    assert await _count(session, "notes", project.id) == 1


@pytest.mark.asyncio
async def test_delete_project_with_actions_blocked_409(integration_session):
    """콘텐츠(액션) 연결 프로젝트 삭제 → 409."""
    session = integration_session
    _owner, ws, project = await _seed_base(session)
    session.add(ActionItem(workspace_id=ws.id, project_id=project.id, title="a"))
    await session.flush()

    with pytest.raises(ProjectHasContentError) as exc:
        await _service(session).delete_project(ws.id, project.id)
    assert exc.value.status_code == 409
    assert await _project_count(session, project.id) == 1


@pytest.mark.asyncio
async def test_delete_project_purges_embedding_chunks_and_caches(integration_session):
    """private 프로젝트 삭제 → 파생 RAG 인덱스/캐시 DELETE (누수 회귀 가드)."""
    session = integration_session
    _owner, ws, project = await _seed_base(session, "private")
    session.add(EmbeddingChunk(
        workspace_id=ws.id, project_id=project.id, source_id=uuid.uuid4(),
        source_type="note", chunk_text="private secret",
    ))
    session.add(SemanticCache(
        workspace_id=ws.id, project_id=project.id, question="q", answer="a",
    ))
    await session.flush()

    await _service(session).delete_project(ws.id, project.id)

    assert await _count(session, "embedding_chunks", project.id) == 0
    assert await _count(session, "semantic_caches", project.id) == 0
    assert await _project_count(session, project.id) == 0


@pytest.mark.asyncio
async def test_delete_project_chunk_hierarchy_and_memory_ref_no_500(integration_session):
    """파생 청크 DELETE 가 inbound FK(자기참조 parent + memory ref)로 500 안 남 검증.

    - 계층(parent level1 + child level2, 둘 다 project_id=pid): 한 DELETE 로 함께 제거
      → self-FK NO ACTION 은 statement-end 검사라 통과.
    - memory 청크(project_id=NULL, memory_items.embedding_chunk_id 참조): promote 는
      target_project_id=None 고정 → memory 청크는 pid 아님 → DELETE 대상 아님, 생존.
    """
    session = integration_session
    owner, ws, project = await _seed_base(session, "private")
    parent = EmbeddingChunk(
        workspace_id=ws.id, project_id=project.id, source_id=uuid.uuid4(),
        source_type="note", chunk_text="parent", chunk_level=1,
    )
    session.add(parent)
    await session.flush()
    session.add(EmbeddingChunk(
        workspace_id=ws.id, project_id=project.id, source_id=uuid.uuid4(),
        source_type="note", chunk_text="child", chunk_level=2,
        parent_chunk_id=parent.id,
    ))
    mem_chunk = EmbeddingChunk(
        workspace_id=ws.id, project_id=None, source_id=uuid.uuid4(),
        source_type="memory", chunk_text="recall memo",
    )
    session.add(mem_chunk)
    await session.flush()
    mem = MemoryItem(
        user_id=owner.id, workspace_id=ws.id, type="text", raw_content="",
        embedding_chunk_id=mem_chunk.id,
    )
    session.add(mem)
    await session.flush()
    mem_chunk_id = mem_chunk.id

    await _service(session).delete_project(ws.id, project.id)

    assert await _project_count(session, project.id) == 0
    assert await _count(session, "embedding_chunks", project.id) == 0  # 계층 함께 제거
    # memory 청크(project_id=NULL)는 생존 → memory_items.embedding_chunk_id FK 정상.
    survived = (await session.execute(
        sa_text("SELECT COUNT(*) FROM embedding_chunks WHERE id = :i"),
        {"i": str(mem_chunk_id)},
    )).scalar_one()
    assert int(survived) == 1


@pytest.mark.asyncio
async def test_delete_project_nulls_inbox_and_audit_pointers(integration_session):
    """프로젝트 삭제 → inbox 제안/promotion_audit 타깃 SET NULL (항목 보존)."""
    session = integration_session
    owner, ws, project = await _seed_base(session)
    inbox = InboxItem(
        workspace_id=ws.id, title="i", source_type="note", source_id=uuid.uuid4(),
        ai_suggested_project_id=project.id,
    )
    session.add(inbox)
    mem = MemoryItem(user_id=owner.id, workspace_id=ws.id, type="text", raw_content="")
    session.add(mem)
    await session.flush()
    audit = PromotionAudit(
        memory_id=mem.id, source_workspace_id=ws.id, target_workspace_id=ws.id,
        target_project_id=project.id, promoted_by_user_id=owner.id,
    )
    session.add(audit)
    await session.flush()
    inbox_id, audit_id = inbox.id, audit.id

    await _service(session).delete_project(ws.id, project.id)

    # 항목 자체는 생존, 프로젝트 포인터만 NULL (DB 원본 조회 — ORM 캐시 우회).
    inbox_ptr = (await session.execute(
        sa_text("SELECT ai_suggested_project_id FROM inbox_items WHERE id = :i"),
        {"i": str(inbox_id)},
    )).scalar_one()
    assert inbox_ptr is None
    audit_ptr = (await session.execute(
        sa_text("SELECT target_project_id FROM promotion_audit WHERE id = :i"),
        {"i": str(audit_id)},
    )).scalar_one()
    assert audit_ptr is None
    assert await _project_count(session, project.id) == 0


@pytest.mark.asyncio
async def test_delete_empty_private_project_succeeds(integration_session):
    """콘텐츠 0 private 프로젝트(창작자 멤버 有) → FK 위반 없이 삭제."""
    session = integration_session
    owner, ws, project = await _seed_base(session, "private")
    session.add(
        ProjectMember(project_id=project.id, workspace_id=ws.id, user_id=owner.id)
    )
    await session.flush()

    await _service(session).delete_project(ws.id, project.id)

    assert await _project_count(session, project.id) == 0
    assert await _count(session, "project_members", project.id) == 0


@pytest.mark.asyncio
async def test_all_project_fk_tables_are_handled(integration_session):
    """드리프트 가드 — projects.id 참조 FK 테이블 전수. 새 테이블 추가 시 실패.

    delete_project 가 커버해야 하는 테이블: join(선삭제) + 콘텐츠(409) + 파생(DELETE/SET NULL).
    여기에 없는 새 FK 가 생기면 삭제 시 500 → 정책(409/DELETE/SET NULL) 등록 강제.
    """
    session = integration_session
    rows = (await session.execute(sa_text(
        "SELECT DISTINCT conrelid::regclass::text FROM pg_constraint "
        "WHERE contype = 'f' AND confrelid = 'projects'::regclass"
    ))).all()
    tables = {r[0].split(".")[-1].strip('"') for r in rows}
    expected = {
        # join (repo.delete 선삭제)
        "project_members", "meeting_project_links",
        # 콘텐츠 (service 409-block)
        "notes", "action_items",
        # 파생 RAG (repo.delete DELETE)
        "embedding_chunks", "semantic_caches",
        # 참조 포인터 (repo.delete SET NULL)
        "inbox_items", "promotion_audit",
    }
    assert tables == expected, (
        f"projects.id 참조 FK 테이블 변경 감지: {tables ^ expected}. "
        "새 테이블은 delete_project 정책(409/DELETE/SET NULL)에 등록 필요 (BL-S27e-5)."
    )
