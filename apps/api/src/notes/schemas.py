# apps/api/src/notes/schemas.py
"""노트 요청/응답 스키마."""
import uuid
from typing import Literal

from pydantic import BaseModel, Field


# Sprint 24 BL-064: ItemPromotionAudit.embedding_status 의 raw value 그대로 노출.
# (alembic 변경 없이 기존 column 활용 — spec §Components BL-064 / Codex 2차 P2-2)
EmbeddingStatusValue = Literal["pending", "processing", "completed", "failed", "n/a"]


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

    Sprint 24 BL-064: embedding_status 필드 추가 (snake_case 보존).
    Codex 2차 P2-3: FE ItemPromoteModal 의 NEW_ID_KEY snake_case read 호환성 유지
    (alias 추가 X / populate_by_name 도 추가 X).
    """

    new_note_id: uuid.UUID
    audit_id: uuid.UUID
    status: str = "embedding_pending"
    # Sprint 24 BL-064: audit raw value 그대로 노출 (pending/processing/completed/failed/n/a)
    embedding_status: EmbeddingStatusValue = "pending"


class EmbeddingStatusOut(BaseModel):
    """GET /notes/{id}/embedding-status 응답 (Sprint 24 BL-064, NEW endpoint).

    NEW endpoint 이므로 camelCase alias 사용 (FE 가 신규로 read 하는 schema —
    기존 modal 의 snake_case 직접 read 흐름과 무관).
    """

    status: EmbeddingStatusValue
    chunk_count: int = Field(alias="chunkCount")

    model_config = {"populate_by_name": True}
