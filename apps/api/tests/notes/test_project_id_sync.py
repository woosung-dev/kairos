# notes-stale: project_id 변경 시 EmbeddingChunk.project_id 동기화 + 캐시 무효화 실DB 테스트.
"""Sprint 29 R1 (notes-stale) 회귀 가드.

content 미변경 PATCH(project_id-only) 시 embed_note_async 가 실행되지 않아
EmbeddingChunk.project_id 가 stale → RAG project-scope 필터 오류. sync_note_project_id
가 재임베딩 없이 chunk project_id 를 갱신하고 old/new SemanticCache 를 무효화하는지 검증.
기존 notes 테스트는 embed pipeline 을 mock 으로 우회 → 실 버그 미검출.
"""
import uuid
from types import SimpleNamespace

import pytest
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.embeddings.models import EmbeddingChunk, SemanticCache
from src.embeddings.repository import EmbeddingRepository
from src.notes.models import Note
from src.notes.pipeline_service import NotePipelineService
from src.notes.repository import NoteRepository

pytestmark = pytest.mark.integration


def _make_pipeline(session: AsyncSession) -> NotePipelineService:
    """sync_note_project_id 는 self.embedding_service.repo 만 사용 → repo stub 로 충분.

    EmbeddingService 의 OpenAI 클라이언트 init 을 피하기 위해 SimpleNamespace stub 사용
    (test_embedding_regenerate 의 embedding_service=None 회피 패턴과 동일 취지).
    """
    return NotePipelineService(
        note_repo=NoteRepository(session),
        embedding_service=SimpleNamespace(repo=EmbeddingRepository(session)),  # type: ignore[arg-type]
        project_repo=None,  # type: ignore[arg-type]
        session_factory=None,
    )


async def _seed(session: AsyncSession):
    from src.auth.models import User
    from src.projects.models import Project
    from src.workspaces.models import Workspace

    user = User(
        auth_user_id=f"c_{uuid.uuid4().hex}",
        display_name="u",
        email=f"{uuid.uuid4().hex}@example.test",
    )
    session.add(user)
    await session.flush()
    ws = Workspace(name="ws", owner_id=user.id, type="team")
    session.add(ws)
    await session.flush()
    proj_a = Project(
        title="A", workspace_id=ws.id, visibility="public", created_by_id=user.id
    )
    proj_b = Project(
        title="B", workspace_id=ws.id, visibility="public", created_by_id=user.id
    )
    proj_c = Project(
        title="C", workspace_id=ws.id, visibility="public", created_by_id=user.id
    )
    session.add_all([proj_a, proj_b, proj_c])
    await session.flush()
    return user, ws, proj_a, proj_b, proj_c


async def test_sync_note_project_id_propagates_and_invalidates(
    integration_session: AsyncSession,
):
    """project_id A→B 변경: chunk project_id 갱신 + A·B 캐시 무효화 + C 캐시 보존."""
    user, ws, proj_a, proj_b, proj_c = await _seed(integration_session)

    note = Note(
        workspace_id=ws.id,
        project_id=proj_a.id,
        title="n",
        content={},
        plain_text="hello",
        created_by_id=user.id,
    )
    integration_session.add(note)
    await integration_session.flush()

    # 기존 chunk (old project_id = A) — L1 + L2
    l1 = EmbeddingChunk(
        workspace_id=ws.id,
        project_id=proj_a.id,
        source_id=note.id,
        source_type="note",
        chunk_text="hello",
        chunk_level=1,
    )
    integration_session.add(l1)
    await integration_session.flush()
    l2 = EmbeddingChunk(
        workspace_id=ws.id,
        project_id=proj_a.id,
        source_id=note.id,
        source_type="note",
        chunk_text="hello",
        chunk_level=2,
        parent_chunk_id=l1.id,
    )
    integration_session.add(l2)

    # 캐시: A(old)·B(new) → 무효화 / C(control) → 보존
    integration_session.add_all([
        SemanticCache(workspace_id=ws.id, project_id=proj_a.id, question="qa", answer="aa"),
        SemanticCache(workspace_id=ws.id, project_id=proj_b.id, question="qb", answer="ab"),
        SemanticCache(workspace_id=ws.id, project_id=proj_c.id, question="qc", answer="ac"),
    ])
    await integration_session.flush()

    # update_note 가 한 일을 모사: note.project_id = B (new)
    note.project_id = proj_b.id
    integration_session.add(note)
    await integration_session.flush()

    # expire_all() 이후엔 ORM 속성 접근이 sync lazy-load(MissingGreenlet) 를 유발하므로
    # 필요한 ID 를 로컬로 캡처해 둔다.
    note_id, pa, pb, pc = note.id, proj_a.id, proj_b.id, proj_c.id

    pipeline = _make_pipeline(integration_session)
    await pipeline.sync_note_project_id(note_id, ws.id)

    # raw UPDATE 이후 identity-map stale 회피
    integration_session.expire_all()

    chunks = (
        await integration_session.exec(
            select(EmbeddingChunk).where(EmbeddingChunk.source_id == note_id)
        )
    ).all()
    assert len(chunks) == 2
    assert all(c.project_id == pb for c in chunks)  # A→B 전파

    caches = (await integration_session.exec(select(SemanticCache))).all()
    cache_projects = {c.project_id for c in caches}
    assert pa not in cache_projects  # old 무효화
    assert pb not in cache_projects  # new 무효화
    assert pc in cache_projects  # 무관 scope 보존


async def test_sync_note_project_id_noop_when_no_chunks(
    integration_session: AsyncSession,
):
    """아직 임베딩 전(chunk 0) 노트 → sync 는 no-op (예외 없음)."""
    user, ws, _proj_a, proj_b, _ = await _seed(integration_session)
    note = Note(
        workspace_id=ws.id,
        project_id=proj_b.id,
        title="n",
        content={},
        plain_text="",
        created_by_id=user.id,
    )
    integration_session.add(note)
    await integration_session.flush()

    pipeline = _make_pipeline(integration_session)
    await pipeline.sync_note_project_id(note.id, ws.id)  # 예외 없이 통과

    chunks = (
        await integration_session.exec(
            select(EmbeddingChunk).where(EmbeddingChunk.source_id == note.id)
        )
    ).all()
    assert chunks == []
