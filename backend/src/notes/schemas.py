# backend/src/notes/schemas.py
"""노트 요청/응답 스키마."""
import uuid

from pydantic import BaseModel, Field


class CreateNoteRequest(BaseModel):
    title: str = ""
    content: dict = Field(default_factory=dict)
    project_id: str | None = Field(default=None, alias="projectId")

    model_config = {"populate_by_name": True}


class UpdateNoteRequest(BaseModel):
    title: str | None = None
    content: dict | None = None
    project_id: str | None = Field(default=None, alias="projectId")

    model_config = {"populate_by_name": True}


# ── Sprint 23 D4 (Task 2 Step 2.3): notes promote ──
# meetings.schemas.MeetingPromoteIn/Out 패턴 정렬 — snake_case 응답 + camelCase alias 입력.
class NotePromoteIn(BaseModel):
    """POST /notes/{id}/promote 요청 — 대상 team workspace."""

    target_workspace_id: uuid.UUID = Field(alias="targetWorkspaceId")

    model_config = {"populate_by_name": True}


class NotePromoteOut(BaseModel):
    """POST /notes/{id}/promote 응답 — 복제본 + audit 식별자.

    meetings.MeetingPromoteOut 와 동일 — promote 도메인 일관성 (snake_case 응답).
    """

    new_note_id: uuid.UUID
    audit_id: uuid.UUID
    status: str = "embedding_pending"
