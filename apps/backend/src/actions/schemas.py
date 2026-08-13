# apps/backend/src/actions/schemas.py
"""ActionItem 스키마 — Pydantic V2, camelCase alias."""
import uuid
from datetime import date

from pydantic import BaseModel, Field


class CreateActionItemRequest(BaseModel):
    title: str
    description: str | None = None
    meeting_id: str | None = Field(default=None, alias="meetingId")
    project_id: str | None = Field(default=None, alias="projectId")
    assignee_id: str | None = Field(default=None, alias="assigneeId")
    due_date: date | None = Field(default=None, alias="dueDate")
    priority: str = "medium"

    model_config = {"populate_by_name": True}


class UpdateActionItemRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    # Codex F-2 2차: meeting 재배정도 cross-workspace 검증 대상 (Sprint 19 PR #1 C7)
    meeting_id: str | None = Field(default=None, alias="meetingId")
    project_id: str | None = Field(default=None, alias="projectId")
    assignee_id: str | None = Field(default=None, alias="assigneeId")
    due_date: date | None = Field(default=None, alias="dueDate")
    priority: str | None = None
    status: str | None = None

    model_config = {"populate_by_name": True}


# ── Sprint 23 D4 (Task 2 Step 2.5): action promote ──
# meetings.MeetingPromoteIn/Out, notes.NotePromoteIn/Out, inbox.InboxPromoteIn/Out 패턴 정렬.
class ActionPromoteIn(BaseModel):
    """POST /action-items/{id}/promote 요청 — 대상 team workspace."""

    target_workspace_id: uuid.UUID = Field(alias="targetWorkspaceId")

    model_config = {"populate_by_name": True}


class ActionPromoteOut(BaseModel):
    """POST /action-items/{id}/promote 응답 — 복제본 + audit 식별자.

    ActionItem 은 임베딩 ledger 부재 (actions 도메인 임베딩 미적용) → BG embedding
    복제 없이 status='completed' 즉시 반환 (inbox 와 동일, notes/meetings 의
    'embedding_pending' 과 차이).
    """

    new_action_id: uuid.UUID
    audit_id: uuid.UUID
    status: str = "completed"
