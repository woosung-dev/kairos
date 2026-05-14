# Sprint 15 Stage 4 R1 memory capture API 통합 테스트 — first failing test
"""Memory capture API 테스트 — POST /api/v1/workspaces/{ws_id}/memory.

patch §4 P-R1 acceptance:
- POST text → 202 + {memory_id, status: "processing", distilled_json: null} ≤500ms p95 (enqueue only)
- BackgroundTask: distill (Gemini) → embed (OpenAI) → save EmbeddingChunk
- GET /api/v1/workspaces/{ws_id}/memory/{memory_id} polling으로 distilled_json + embedding_chunk_id 확인
"""
import uuid

import pytest


@pytest.mark.asyncio
async def test_post_memory_text_returns_202_processing(memory_client):
    """R1 first failing test — memory POST 엔드포인트 미구현이므로 404 또는 router 부재로 fail.

    T-1 단계 placeholder workspace_id 사용. R2 이후 personal_ws fixture로 교체.
    memory_client는 auth_user를 transitive 의존성으로 끌어옴.
    """
    placeholder_ws_id = uuid.uuid4()
    response = await memory_client.post(
        f"/api/v1/workspaces/{placeholder_ws_id}/memory",
        data={"text": "Sprint 15 wedge 결정 Recall-first"},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "processing"
    assert body["distilled_json"] is None
    assert "memory_id" in body
