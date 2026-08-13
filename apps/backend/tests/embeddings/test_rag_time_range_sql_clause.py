# Sprint 24 Wave 2 T-RAG-TIME-FILTER (BUG-POW-006) — time_range 필터 SQL clause 통합 검증
"""RAG vector_search / text_search 의 time_range 필터 회귀 검증.

검증 대상:
- "1w" → 7일 이내 created_at 만 반환 (오래된 chunk 배제)
- "all" / None → 필터 미적용 (모든 chunk 반환)
- 화이트리스트 외 값 → fail-safe (필터 미적용)

visibility filter (ISSUE-040 RBAC) 보존 동시 검증 — 다른 chunk 가
private project 에 속해도 작성자 본인 (owner) 은 모두 통과.
"""
import uuid
from datetime import datetime, timedelta

import pytest

from src.embeddings.models import EmbeddingChunk
from src.embeddings.repository import EmbeddingRepository


def _make_vec(seed: int, dim: int = 1536) -> list[float]:
    base = 0.001 * (seed + 1)
    return [base + (i * 0.0001) for i in range(dim)]


async def _seed_chunks_with_ages(
    session, workspace_id, _source_workspace_id, ages_days: list[int]
) -> list[EmbeddingChunk]:
    """다양한 created_at 시간의 chunks seed. 각 chunk 는 ages_days 의 N 일 전 created.
    _source_workspace_id 는 시그니처 호환성 (호출자 일부가 명시적 전달) — 본 helper 는 미사용.
    """
    chunks: list[EmbeddingChunk] = []
    # NOTE: embedding_chunks.created_at = TIMESTAMP WITHOUT TIME ZONE → naive datetime 강제.
    # Pyright deprecation (utcnow) 은 informational — 컬럼 schema 변경 시 carry-over.
    now = datetime.utcnow()  # noqa: DTZ003  # pyright: ignore[reportDeprecated]
    for i, age in enumerate(ages_days):
        chunk = EmbeddingChunk(
            workspace_id=workspace_id,
            source_id=uuid.uuid4(),
            source_type="note",
            chunk_text=f"chunk {age}일 전",
            chunk_index=0,
            chunk_level=2,
            embedding=_make_vec(seed=i),
            created_at=now - timedelta(days=age),
        )
        session.add(chunk)
        chunks.append(chunk)
    await session.flush()
    # created_at 은 model default 가 server-side 가 아니므로 명시 set 후 flush.
    # 그래도 안전을 위해 UPDATE 로 다시 set (model.default_factory=datetime.utcnow 가
    # flush 시점에 적용될 수 있어 명시적 backdate 보장).
    from sqlmodel import text as _text
    for chunk, age in zip(chunks, ages_days, strict=True):
        await session.execute(
            _text("UPDATE embedding_chunks SET created_at = :ts WHERE id = :id"),
            {
                "ts": now - timedelta(days=age),
                "id": str(chunk.id),
            },
        )
    await session.flush()
    return chunks


@pytest.mark.asyncio
async def test_vector_search_time_range_1w_excludes_old_chunks(
    integration_session, auth_user, team_ws
):
    """time_range='1w' → 7일 이내 chunk 만 반환 (30일 / 100일 전 chunk 배제)."""
    await _seed_chunks_with_ages(
        integration_session,
        workspace_id=team_ws.id,
        _source_workspace_id=team_ws.id,
        ages_days=[1, 5, 30, 100],
    )

    repo = EmbeddingRepository(integration_session)
    results = await repo.vector_search(
        query_embedding=_make_vec(seed=0),
        workspace_id=team_ws.id,
        requester_user_id=auth_user.id,
        requester_role="owner",
        time_range="1w",
        limit=10,
    )
    texts = {r["chunk_text"] for r in results}
    # 7일 이내만 — 1일 / 5일 전 포함, 30일 / 100일 전 배제.
    assert "chunk 1일 전" in texts
    assert "chunk 5일 전" in texts
    assert "chunk 30일 전" not in texts
    assert "chunk 100일 전" not in texts


@pytest.mark.asyncio
async def test_vector_search_time_range_all_returns_all(
    integration_session, auth_user, team_ws
):
    """time_range='all' / None → 모든 chunk 반환 (필터 미적용)."""
    await _seed_chunks_with_ages(
        integration_session,
        workspace_id=team_ws.id,
        _source_workspace_id=team_ws.id,
        ages_days=[1, 30, 100],
    )

    repo = EmbeddingRepository(integration_session)

    # 'all' 명시
    results_all = await repo.vector_search(
        query_embedding=_make_vec(seed=0),
        workspace_id=team_ws.id,
        requester_user_id=auth_user.id,
        requester_role="owner",
        time_range="all",
        limit=10,
    )
    texts_all = {r["chunk_text"] for r in results_all}
    assert "chunk 1일 전" in texts_all
    assert "chunk 30일 전" in texts_all
    assert "chunk 100일 전" in texts_all

    # None (기본값) — 동일하게 모든 chunk
    results_none = await repo.vector_search(
        query_embedding=_make_vec(seed=0),
        workspace_id=team_ws.id,
        requester_user_id=auth_user.id,
        requester_role="owner",
        time_range=None,
        limit=10,
    )
    texts_none = {r["chunk_text"] for r in results_none}
    assert "chunk 100일 전" in texts_none


@pytest.mark.asyncio
async def test_vector_search_time_range_invalid_value_failsafe(
    integration_session, auth_user, team_ws
):
    """time_range 화이트리스트 외 값 → 필터 미적용 (fail-safe). SQL injection 차단."""
    await _seed_chunks_with_ages(
        integration_session,
        workspace_id=team_ws.id,
        _source_workspace_id=team_ws.id,
        ages_days=[1, 100],
    )

    repo = EmbeddingRepository(integration_session)
    # 'invalid' / '5y' / SQL fragment — 모두 silently skip → 전체 반환
    for evil in ["invalid", "5y", "'; DROP TABLE embedding_chunks; --"]:
        results = await repo.vector_search(
            query_embedding=_make_vec(seed=0),
            workspace_id=team_ws.id,
            requester_user_id=auth_user.id,
            requester_role="owner",
            time_range=evil,
            limit=10,
        )
        texts = {r["chunk_text"] for r in results}
        assert "chunk 1일 전" in texts
        assert "chunk 100일 전" in texts  # 필터 미적용 → 100일도 포함
