# Sprint 15 Stage 4 R3 recall endpoint 통합 테스트
"""Recall endpoint — vector + keyword fallback + I-9 workspace_id 격리.

patch §6 P-R3 acceptance:
- GET /api/v1/workspaces/{ws_id}/memory/recall?q=... → MemoryRecallOut
- vector 미존재(_call_embedding error) → keyword fallback 자동 (fallback_used=True)
- I-9: 다른 workspace memory 절대 미반환
- q min_length=2 → 1자 query 422
"""
import uuid

import pytest


@pytest.mark.asyncio
async def test_recall_returns_keyword_when_no_vector(
    memory_client, personal_ws, seed_memory
):
    """vector search 미동작(monkeypatch error) → keyword fallback로 seed_memory 매칭."""
    response = await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/recall",
        params={"q": "Sprint wedge"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "Sprint wedge"
    assert body["fallback_used"] is True
    assert len(body["sources"]) >= 1
    assert body["sources"][0]["memory_id"] == str(seed_memory.id)
    assert body["sources"][0]["match_type"] == "keyword"


@pytest.mark.asyncio
async def test_recall_query_too_short_returns_422(memory_client, personal_ws):
    """q min_length=2 → 1자 query 422 (FastAPI Query 검증)."""
    response = await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/recall",
        params={"q": "x"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_recall_empty_workspace_returns_empty_sources(
    memory_client, personal_ws
):
    """memory 없는 workspace → sources=[] + fallback_used=True."""
    response = await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/recall",
        params={"q": "nothing matches here"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == []
    assert body["fallback_used"] is True


@pytest.mark.asyncio
async def test_recall_workspace_id_filter_enforced(
    memory_client, personal_ws, team_ws, integration_session, auth_user
):
    """I-9: 다른 workspace의 memory는 절대 반환 안 됨 (cross-tenant 격리)."""
    from src.memory.models import MemoryItem

    foreign = MemoryItem(
        user_id=auth_user.id,
        workspace_id=team_ws.id,
        type="text",
        raw_content="foreign workspace content keyword sample",
        distilled_json={
            "title": "foreign keyword",
            "atomic_notes": ["foreign keyword content"],
            "suggested_visibility": "team",
        },
        status="active",
    )
    integration_session.add(foreign)
    await integration_session.flush()

    response = await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/recall",
        params={"q": "foreign keyword"},
    )
    assert response.status_code == 200
    body = response.json()
    foreign_id = str(foreign.id)
    assert all(
        s["memory_id"] != foreign_id for s in body["sources"]
    ), f"I-9 violation: foreign workspace memory ({foreign_id}) returned"


@pytest.mark.asyncio
async def test_query_embedding_cache_returns_native_python_floats(
    integration_session, personal_ws
):
    """C3 cache regression — pgvector ndarray가 native Python float list로 변환되어야 함.

    Stage 5-6 qa Exhaustive 발견 (2026-05-14):
    동일 query 두 번째 hit 시 cache 경로가 numpy.ndarray 그대로 반환 → asyncpg가
    pgvector bind 시 numpy float 직렬화 실패 → /memory/recall 500.

    Fix: repository.get_query_embedding_cache이 [float(x) for x in cached.embedding]로
    명시 캐스팅하여 asyncpg pgvector 호환 보장.
    """
    from src.memory.repository import MemoryRepository

    repo = MemoryRepository(integration_session)
    fake_embedding = [0.1 * i for i in range(1536)]
    normalized = "wedge recall regression"

    await repo.save_query_embedding_cache(
        personal_ws.id, normalized, fake_embedding
    )
    await repo.commit()

    cached = await repo.get_query_embedding_cache(personal_ws.id, normalized)
    assert cached is not None
    assert len(cached) == 1536
    # 핵심 회귀: 모든 element가 native Python float여야 함 (numpy.float32/64 X)
    assert all(type(x) is float for x in cached), (
        "C3 cache must return native Python float list; "
        f"got types {set(type(x).__name__ for x in cached[:5])}"
    )
    # 값 정밀도 유지
    assert cached[0] == pytest.approx(0.0)
    assert cached[10] == pytest.approx(1.0)
