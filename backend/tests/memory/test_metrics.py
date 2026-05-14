# Sprint 15 R7 — Memory metrics endpoint 통합 테스트
"""DB-backed metrics — memory_events 집계 + recall p50/p95 percentile."""
import pytest


@pytest.mark.asyncio
async def test_metrics_empty_workspace_returns_zero(memory_client, personal_ws):
    """이벤트 없는 ws → 모든 count 0, percentile null."""
    response = await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/metrics",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["capture_count"] == 0
    assert body["recall_count"] == 0
    assert body["promote_count"] == 0
    assert body["recall_p50_ms"] is None
    assert body["recall_p95_ms"] is None


@pytest.mark.asyncio
async def test_metrics_after_capture_increments(memory_client, personal_ws):
    """capture 후 capture_count 증가."""
    await memory_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/memory",
        data={"text": "테스트 메모"},
    )
    response = await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/metrics",
    )
    body = response.json()
    assert body["capture_count"] >= 1


@pytest.mark.asyncio
async def test_metrics_after_recall_increments_and_records_latency(
    memory_client, personal_ws, seed_memory
):
    """recall 호출 후 recall_count + p50/p95 latency 기록."""
    await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/recall?q=Sprint",
    )
    response = await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/metrics",
    )
    body = response.json()
    assert body["recall_count"] >= 1
    # latency_ms 기록 — 0 이상 정수
    assert body["recall_p50_ms"] is not None
    assert body["recall_p50_ms"] >= 0
    assert body["recall_p95_ms"] is not None


@pytest.mark.asyncio
async def test_metrics_workspace_id_isolation(
    memory_client, personal_ws, team_ws, integration_session, auth_user
):
    """다른 workspace의 이벤트는 집계 X."""
    from src.memory.models import MemoryEvent
    # team_ws에 capture 이벤트 1건 직접 삽입
    integration_session.add(MemoryEvent(
        workspace_id=team_ws.id,
        user_id=auth_user.id,
        event_type="capture",
        event_metadata={"type": "text"},
    ))
    await integration_session.flush()

    response = await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/metrics",
    )
    body = response.json()
    assert body["capture_count"] == 0  # team_ws 이벤트 미포함
