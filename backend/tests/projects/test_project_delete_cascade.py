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
from src.embeddings.repository import EmbeddingRepository
from src.inbox.models import InboxItem
from src.integrations.models import ExternalDocument, IntegrationConnection
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
    connection = IntegrationConnection(
        workspace_id=ws.id,
        authorized_by_id=owner.id,
        encrypted_refresh_token="test-encrypted-refresh-token",
        scope="https://www.googleapis.com/auth/drive.file",
    )
    session.add(connection)
    await session.flush()
    document = ExternalDocument(
        workspace_id=ws.id,
        connection_id=connection.id,
        project_id=project.id,
        drive_file_id=f"project-delete-{uuid.uuid4().hex}",
        title="프로젝트 외부 문서",
        mime_type="application/vnd.google-apps.document",
        origin_url="https://docs.google.com/document/d/project-delete",
        revision_id="1",
        content_hash="project-delete-hash",
        plain_text="외부 문서 본문",
    )
    session.add(document)
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
    document_ptr = (await session.execute(
        sa_text("SELECT project_id FROM external_documents WHERE id = :i"),
        {"i": str(document.id)},
    )).scalar_one()
    assert document_ptr is None
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


# ── BL-EXT-CACHE-1: 삭제 후 잔존 전역 캐시로 인한 비-멤버 누수 회귀 가드 ──


def _axis_vec(axis: int, dim: int = 1536) -> list[float]:
    """축이 다르면 코사인 유사도 0 — 캐시행끼리 간섭 없이 결정적으로 매칭된다."""
    vec = [0.0] * dim
    vec[axis] = 1.0
    return vec


def _rag_cache_source(chunk: EmbeddingChunk) -> dict:
    """RAGService._format_sources 가 저장하는 production sources 형태."""
    return {
        "id": str(chunk.id),
        "sourceId": str(chunk.source_id),
        "text": chunk.chunk_text[:200],
        "source": "비공개 노트",
        "sourceType": chunk.source_type,
        "date": "",
        "speaker": None,
        "score": 0.0,
        "freshness": "recent",
    }


async def _seed_cache_leak_scenario(session):
    """private 프로젝트 + 청크 + 전역/해당 project/타 project 캐시 + 비-멤버 시드.

    반환 (ws, project, other_project, non_member).
    """
    owner, ws, project = await _seed_base(session, "private")
    other_project = Project(
        workspace_id=ws.id, title="pdel-other", created_by_id=owner.id,
        visibility="public",
    )
    non_member = User(
        clerk_id=f"clerk_pdel_nm_{uuid.uuid4()}",
        display_name="비-멤버",
        email=f"pdel_nm_{uuid.uuid4()}@del.test",
    )
    session.add_all([other_project, non_member])
    await session.flush()
    # 위협 모델: 같은 워크스페이스 멤버지만 private 프로젝트 멤버는 아닌 사용자.
    session.add(
        WorkspaceMember(workspace_id=ws.id, user_id=non_member.id, role="member")
    )
    chunk = EmbeddingChunk(
        workspace_id=ws.id, project_id=project.id, source_id=uuid.uuid4(),
        source_type="note", chunk_text="PD-LEAK-ANSWER private 본문", chunk_level=2,
        embedding=_axis_vec(0),
    )
    session.add(chunk)
    await session.flush()
    sources = [_rag_cache_source(chunk)]
    session.add_all([
        # 전역 질의 캐시 (project_id IS NULL) — project scope 삭제가 놓치는 행.
        SemanticCache(
            workspace_id=ws.id, project_id=None, question="전역 질문",
            question_embedding=_axis_vec(0), answer="PD-LEAK-ANSWER private 본문",
            sources=sources, max_visibility="private",
        ),
        SemanticCache(
            workspace_id=ws.id, project_id=project.id, question="프로젝트 질문",
            question_embedding=_axis_vec(1), answer="PD-LEAK-ANSWER private 본문",
            sources=sources, max_visibility="private",
        ),
        SemanticCache(
            workspace_id=ws.id, project_id=other_project.id,
            question="타 프로젝트 질문", question_embedding=_axis_vec(2),
            answer="타 프로젝트 답변",
        ),
    ])
    await session.commit()
    return ws, project, other_project, non_member


async def _non_member_probe(session, workspace_id: uuid.UUID, user_id: uuid.UUID):
    """RAG 진입점과 동일한 전역 scope(project_id=None) 캐시 조회."""
    return await EmbeddingRepository(session).find_similar_cache(
        question_embedding=_axis_vec(0),
        workspace_id=workspace_id,
        requester_user_id=user_id,
        requester_role="member",
    )


@pytest.mark.asyncio
async def test_delete_project_leaves_no_cache_hit_for_non_member(integration_session):
    """BL-EXT-CACHE-1: 삭제 전 MISS(대조군) → 삭제 후에도 비-멤버 probe MISS.

    캐시를 project scope 로만 지우면 전역 캐시행이 살아남고 그 sources 가 가리키는
    청크는 이미 삭제된 상태다. ALL_CHUNKS_VISIBLE_SQL 은 *존재하는* 청크만 검사하는
    anti-join 이라 사라진 id 는 위반을 만들지 못하고(fail-open) 비-멤버가 삭제된
    private 본문을 HIT 으로 받는다. 행 개수가 아니라 실제 probe 결과로 단언한다.
    """
    session = integration_session
    ws, project, _other_project, non_member = await _seed_cache_leak_scenario(session)

    # 대조군 — 삭제 전에는 청크가 살아 있어 anti-join 이 위반을 잡아낸다.
    assert await _non_member_probe(session, ws.id, non_member.id) is None

    await _service(session).delete_project(ws.id, project.id)

    leaked = await _non_member_probe(session, ws.id, non_member.id)
    assert leaked is None, (
        "삭제된 private 프로젝트 본문이 전역 캐시 HIT 으로 노출됐다: "
        f"{leaked and leaked['answer']}"
    )


@pytest.mark.asyncio
async def test_delete_project_invalidates_whole_workspace_caches(integration_session):
    """전량 무효화 정책 고정 — 같은 workspace 캐시는 전부, 타 workspace 는 보존.

    좁은 scope 가 안전할 수 없는 이유(anti-join fail-open)는 위 테스트가 지키고,
    이 테스트는 그 대가로 넓힌 범위가 workspace 경계를 넘지 않음을 고정한다.
    """
    session = integration_session
    ws, project, other_project, _non_member = await _seed_cache_leak_scenario(session)
    _owner2, other_ws, _p2 = await _seed_base(session)
    session.add(SemanticCache(
        workspace_id=other_ws.id, question="타 워크스페이스 질문", answer="보존 대상",
    ))
    await session.commit()

    await _service(session).delete_project(ws.id, project.id)

    remaining = (await session.execute(
        sa_text("SELECT COUNT(*) FROM semantic_caches WHERE workspace_id = :w"),
        {"w": str(ws.id)},
    )).scalar_one()
    assert int(remaining) == 0  # 전역 + 삭제 project + 타 project 캐시 모두 무효화
    assert await _count(session, "semantic_caches", other_project.id) == 0
    survived = (await session.execute(
        sa_text("SELECT COUNT(*) FROM semantic_caches WHERE workspace_id = :w"),
        {"w": str(other_ws.id)},
    )).scalar_one()
    assert int(survived) == 1  # 무효화는 workspace 경계 안에서만


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
        "inbox_items", "promotion_audit", "external_documents",
    }
    assert tables == expected, (
        f"projects.id 참조 FK 테이블 변경 감지: {tables ^ expected}. "
        "새 테이블은 delete_project 정책(409/DELETE/SET NULL)에 등록 필요 (BL-S27e-5)."
    )
