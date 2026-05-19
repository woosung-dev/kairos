# backend/src/meetings/schemas.py
"""Meeting 스키마."""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreateMeetingRequest(BaseModel):
    title: str
    file_key: str = Field(alias="fileKey")
    recorded_at: datetime | None = Field(default=None, alias="recordedAt")

    model_config = {"populate_by_name": True}


class MeetingCreatedResponse(BaseModel):
    id: str
    status: str
    message: str


class MeetingStatusResponse(BaseModel):
    status: str
    error_message: str | None = None


class CaptureTextRequest(BaseModel):
    title: str
    transcript_text: str = Field(alias="transcriptText", min_length=50)

    model_config = {"populate_by_name": True}


# ── Sprint 23 D4 (Task 2 Step 2.2): meetings promote ──
# 응답 필드는 memory.MemoryPromoteOut 패턴 정렬 — snake_case (alias 없음).
# 요청은 camelCase alias 허용 — FE 일관성 위해 (memory 도 snake_case 만 받음 → 정렬).
class MeetingPromoteIn(BaseModel):
    """POST /meetings/{id}/promote 요청 — 대상 team workspace."""

    target_workspace_id: uuid.UUID = Field(alias="targetWorkspaceId")

    model_config = {"populate_by_name": True}


class MeetingPromoteOut(BaseModel):
    """POST /meetings/{id}/promote 응답 — 복제본 + audit 식별자.

    memory.MemoryPromoteOut 와 동일하게 snake_case 응답 — promote 도메인 일관성.
    """

    new_meeting_id: uuid.UUID
    audit_id: uuid.UUID
    status: str = "embedding_pending"
