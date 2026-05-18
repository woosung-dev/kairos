# Sprint 15 R6 — Promote 1-button BE 통합 테스트
"""Promote 1-button: 복제 MemoryItem + PromotionAudit row + 검증.

ADR-016 AD-41 (복제 + tombstone): 원본 MemoryItem.status 변경 없이 target ws 복제본 신규 + audit.
검증: source != target / target type='team' / user가 target ws 멤버.
"""
import uuid

import pytest
from sqlmodel import select


@pytest.mark.asyncio
async def test_promote_creates_duplicate_and_audit(
    memory_client, personal_ws, team_ws, seed_memory
):
    """personal → team promote → 202 + new_memory_id + audit_id + status=embedding_pending."""
    response = await memory_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/memory/{seed_memory.id}/promote",
        json={"target_workspace_id": str(team_ws.id)},
    )
    assert response.status_code == 202
    body = response.json()
    assert uuid.UUID(body["new_memory_id"])  # valid UUID
    assert uuid.UUID(body["audit_id"])
    assert body["status"] == "embedding_pending"
    # 원본은 보존 — id 다르면 OK
    assert body["new_memory_id"] != str(seed_memory.id)


@pytest.mark.asyncio
async def test_promote_audit_row_inserted(
    memory_client,
    integration_session,
    personal_ws,
    team_ws,
    seed_memory,
    auth_user,
):
    """promote 후 promotion_audit row + memory_events promote 이벤트 검증."""
    from src.memory.models import MemoryEvent, MemoryItem, PromotionAudit

    response = await memory_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/memory/{seed_memory.id}/promote",
        json={"target_workspace_id": str(team_ws.id)},
    )
    assert response.status_code == 202

    audit_q = select(PromotionAudit).where(
        PromotionAudit.target_workspace_id == team_ws.id,
        PromotionAudit.memory_id == seed_memory.id,
    )
    audit = (await integration_session.execute(audit_q)).scalar_one_or_none()
    assert audit is not None
    assert audit.promoted_by_user_id == auth_user.id
    assert audit.source_workspace_id == personal_ws.id
    assert audit.embedding_status == "pending"

    # 원본 보존 — status 변경 없음
    src_q = select(MemoryItem).where(MemoryItem.id == seed_memory.id)
    src = (await integration_session.execute(src_q)).scalar_one()
    assert src.status == "active"  # seed_memory 픽스처 초기 status

    # 복제본 신규 row 존재 (target ws)
    dup_q = select(MemoryItem).where(
        MemoryItem.workspace_id == team_ws.id,
        MemoryItem.id != seed_memory.id,
    )
    dup = (await integration_session.execute(dup_q)).scalar_one_or_none()
    assert dup is not None
    assert dup.raw_content == seed_memory.raw_content

    # promote 이벤트
    ev_q = select(MemoryEvent).where(
        MemoryEvent.workspace_id == personal_ws.id,
        MemoryEvent.event_type == "promote",
    )
    ev = (await integration_session.execute(ev_q)).scalar_one_or_none()
    assert ev is not None


@pytest.mark.asyncio
async def test_promote_same_workspace_rejected(
    memory_client, personal_ws, seed_memory
):
    """source == target → 422 (CannotPromoteToSameWorkspaceError)."""
    response = await memory_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/memory/{seed_memory.id}/promote",
        json={"target_workspace_id": str(personal_ws.id)},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_promote_nonexistent_memory_404(
    memory_client, personal_ws, team_ws
):
    """존재하지 않는 memory_id → 404."""
    response = await memory_client.post(
        f"/api/v1/workspaces/{personal_ws.id}/memory/{uuid.uuid4()}/promote",
        json={"target_workspace_id": str(team_ws.id)},
    )
    assert response.status_code == 404
