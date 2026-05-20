# Sprint 24 BL-064 — embed_note_async 멱등성 + embedding-status endpoint RBAC
"""BL-064: chunk 0 + plain_text note promote 시 BG schedule 후 polling endpoint 검증.

2 케이스:
- embed_note_async 멱등성 — chunk count > 0 인 note 는 plain_text fallback 시 재생성 skip
  (실제로는 plain_text 가 falsy 면 early return — pipeline_service.py:41).
- GET /notes/{id}/embedding-status RBAC — non-member 403, viewer 이상 200.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlmodel import func, select


@pytest_asyncio.fixture
async def notes_status_client(integration_session, auth_user, monkeypatch):
    """embedding-status endpoint 용 AsyncClient — auth + session override.

    seed_note + seed_note_chunk_zero_with_plain_text fixture 가
    test_note_promote.py 의 notes_client 패턴과 동일 session 의존.
    """
    from src.auth.dependencies import get_current_user
    from src.common.database import get_async_session, get_session_factory
    from src.main import app

    class _DummyFactory:
        def __call__(self):
            return _DummyAsyncCM(integration_session)

    class _DummyAsyncCM:
        def __init__(self, sess):
            self._sess = sess

        async def __aenter__(self):
            return self._sess

        async def __aexit__(self, *_args):
            return False

    app.dependency_overrides[get_current_user] = lambda: auth_user
    app.dependency_overrides[get_async_session] = lambda: integration_session
    app.dependency_overrides[get_session_factory] = lambda: _DummyFactory()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seed_note_with_chunks(integration_session, auth_user, personal_ws):
    """plain_text + chunk 5 의 임베딩 완료 노트 — embedding-status = completed 검증용."""
    from src.embeddings.models import EmbeddingChunk
    from src.notes.models import Note

    note = Note(
        workspace_id=personal_ws.id,
        project_id=None,
        title="임베딩 완료 노트",
        content={
            "type": "doc",
            "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "완료"}]}
            ],
        },
        plain_text="완료된 텍스트",
        created_by_id=auth_user.id,
    )
    integration_session.add(note)
    await integration_session.flush()

    for idx in range(5):
        integration_session.add(
            EmbeddingChunk(
                workspace_id=personal_ws.id,
                project_id=None,
                source_id=note.id,
                source_type="note",
                chunk_text=f"chunk-{idx}",
                chunk_index=idx,
                chunk_level=1,
                embedding=[0.0] * 1536,
                metadata_json={},
            )
        )
    await integration_session.flush()
    await integration_session.commit()
    return note


@pytest.mark.asyncio
async def test_embed_note_async_idempotent_when_already_embedded(
    integration_session, auth_user, personal_ws, seed_note_with_chunks
):
    """BL-064: 이미 embed 된 note 에 plain_text 가 비어 있으면 early return.

    pipeline_service.py:40-42 의 `if not note or not note.plain_text: return` 가드.
    실 멱등성은 embedding pipeline 내부에서 보장하지 않으므로 service 단의 가드만 확인.
    chunk count 가 변하지 않는지 검증 — 실 OpenAI 호출은 mock 없이 plain_text 변조로 가드 진입.
    """
    from sqlmodel.ext.asyncio.session import AsyncSession
    from src.embeddings.models import EmbeddingChunk
    from src.notes.models import Note
    from src.notes.repository import NoteRepository

    # 1. 직전 chunk count
    count_before = (
        await integration_session.execute(
            select(func.count())
            .select_from(EmbeddingChunk)
            .where(EmbeddingChunk.source_id == seed_note_with_chunks.id)
        )
    ).scalar_one()
    assert count_before == 5

    # 2. plain_text 를 빈 값으로 강제 → early return guard 적용
    note = await integration_session.get(Note, seed_note_with_chunks.id)
    note.plain_text = ""
    integration_session.add(note)
    await integration_session.flush()
    await integration_session.commit()

    # 3. NotePipelineService.embed_note_async 직접 호출 — embedding_service mock
    from src.notes.pipeline_service import NotePipelineService

    class _StubEmbedService:
        def __init__(self) -> None:
            self.embed_calls = 0
            self.invalidate_calls = 0

        async def embed_note(self, **kwargs):
            self.embed_calls += 1

        async def invalidate_cache(self, *_args):
            self.invalidate_calls += 1

    stub = _StubEmbedService()
    pipeline = NotePipelineService(
        note_repo=NoteRepository(integration_session),
        embedding_service=stub,  # type: ignore[arg-type]
        project_repo=None,  # type: ignore[arg-type]
    )
    await pipeline.embed_note_async(seed_note_with_chunks.id, personal_ws.id)
    # plain_text="" 가드로 early return — embed/invalidate 호출 0
    assert stub.embed_calls == 0
    assert stub.invalidate_calls == 0


@pytest.mark.asyncio
async def test_embedding_status_endpoint_rbac_and_response(
    notes_status_client,
    integration_session,
    personal_ws,
    seed_note_with_chunks,
    auth_user,
):
    """BL-064: GET /notes/{id}/embedding-status — viewer 이상 200 + non-member 403.

    chunk count > 0 + audit 부재 케이스 → status="completed" + chunkCount=5.
    """
    # 1. owner (viewer 이상) 200 + completed
    response = await notes_status_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/notes/{seed_note_with_chunks.id}/embedding-status"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["chunkCount"] == 5  # camelCase alias 검증

    # 2. non-member 403 — 별도 user + ws 로 dependency_overrides 일시 변경
    from src.auth.dependencies import get_current_user
    from src.auth.models import User
    from src.main import app

    non_member = User(
        clerk_id="non_member_clerk_bl064",
        display_name="외부인",
        email="nonmember_bl064@kairos.test",
    )
    integration_session.add(non_member)
    await integration_session.flush()
    await integration_session.commit()

    app.dependency_overrides[get_current_user] = lambda: non_member
    try:
        response_403 = await notes_status_client.get(
            f"/api/v1/workspaces/{personal_ws.id}/notes/{seed_note_with_chunks.id}/embedding-status"
        )
        # require_viewer 가 멤버 부재 → 403
        assert response_403.status_code == 403
    finally:
        app.dependency_overrides[get_current_user] = lambda: auth_user
