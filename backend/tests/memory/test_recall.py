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
