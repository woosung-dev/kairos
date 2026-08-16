# apps/api/src/inbox/schemas.py
"""Inbox Pydantic V2 입출력 스키마."""
import uuid

from pydantic import BaseModel, Field


class ClassifyInboxRequest(BaseModel):
    """Inbox 아이템을 프로젝트에 연결 확정."""

    project_ids: list[str] = Field(alias="projectIds")
    model_config = {"populate_by_name": True}


# ── Sprint 23 D4 (Task 2 Step 2.4): inbox promote ──
# meetings.MeetingPromoteIn/Out, notes.NotePromoteIn/Out 패턴 정렬.
class InboxPromoteIn(BaseModel):
    """POST /inbox/{id}/promote 요청 — 대상 team workspace."""

    target_workspace_id: uuid.UUID = Field(alias="targetWorkspaceId")

    model_config = {"populate_by_name": True}


class InboxPromoteOut(BaseModel):
    """POST /inbox/{id}/promote 응답 — 복제본 + audit 식별자.

    InboxItem 은 source_type='inbox' EmbeddingChunk 가 존재하지 않으므로
    BG embedding 복제 없이 status='completed' 즉시 반환 (notes/meetings 는
    'embedding_pending' — BG 흐름 차이).
    """

    new_inbox_id: uuid.UUID
    audit_id: uuid.UUID
    status: str = "completed"
