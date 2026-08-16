# Sprint 15 Stage 4 R1 memory capture API 통합 테스트
"""Memory capture API 테스트 — POST/GET /api/v1/workspaces/{ws_id}/memory.

patch §4 P-R1 acceptance:
- POST text → 202 + {memory_id, status: "processing", distilled_json: null} ≤500ms p95 (enqueue only)
- BackgroundTask: distill (Gemini) → embed (OpenAI) → save EmbeddingChunk
- GET /api/v1/workspaces/{ws_id}/memory/{memory_id} polling으로 distilled_json + embedding_chunk_id 확인
- memory_client fixture에서 BackgroundTask는 no-op monkeypatch — 외부 API 호출 차단
"""
import uuid

import pytest


@pytest.mark.asyncio
async def test_post_memory_text_returns_202_processing(memory_client, personal_ws):
    """텍스트 capture → 202 + processing + distilled_json null."""
    response = await memory_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/memory",
        data={"text": "Sprint 15 wedge 결정 Recall-first"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    assert body["distilled_json"] is None
    assert "memory_id" in body
    uuid.UUID(body["memory_id"])  # 유효 UUID 검증


@pytest.mark.asyncio
async def test_post_memory_empty_returns_422(memory_client, personal_ws):
    """빈 입력 → 422 EmptyMemoryError."""
    response = await memory_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/memory",
        data={"text": "   "},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_memory_no_text_no_audio_returns_422(memory_client, personal_ws):
    """text/audio 모두 미제공 → 422."""
    response = await memory_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/memory",
        data={},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_memory_returns_detail(memory_client, personal_ws, seed_memory):
    """seed_memory GET → distilled_json + status=active."""
    response = await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/{seed_memory.id}",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "active"
    assert body["distilled_json"]["title"] == "Sprint 15 wedge"
    assert body["type"] == "text"


@pytest.mark.asyncio
async def test_get_memory_not_found_returns_404(memory_client, personal_ws):
    """존재하지 않는 memory_id → 404."""
    response = await memory_client.get(
        f"/api/v1/workspaces/{personal_ws.id}/memory/{uuid.uuid4()}",
    )
    assert response.status_code == 404
