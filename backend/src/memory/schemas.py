# Memory API 입출력 스키마 (Pydantic V2)
"""Memory 도메인 입출력 스키마."""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class MemoryCreateOut(BaseModel):
    """POST /memory 응답 — 202 enqueue 시점."""

    memory_id: uuid.UUID
    status: str
    distilled_json: dict | None
    created_at: datetime


class MemoryDetailOut(BaseModel):
    """GET /memory/{id} 응답 — polling 시점."""

    memory_id: uuid.UUID
    workspace_id: uuid.UUID
    type: str
    raw_content: str
    distilled_json: dict | None
    status: str
    embedding_chunk_id: uuid.UUID | None
    r2_audio_key: str | None
    created_at: datetime
    updated_at: datetime


class MemoryRecallSource(BaseModel):
    """Recall 단건 결과 — vector 또는 keyword 매치."""

    memory_id: uuid.UUID
    title: str
    atomic_notes_excerpt: str
    score: float
    match_type: Literal["vector", "keyword"]
    created_at: datetime


class MemoryRecallOut(BaseModel):
    """GET /memory/recall 응답 — Top 3 sources + fallback 표시."""

    query: str
    sources: list[MemoryRecallSource]
    fallback_used: bool


class MemoryPromoteIn(BaseModel):
    """POST /memory/{id}/promote 요청 — 대상 팀 workspace."""

    target_workspace_id: uuid.UUID


class MemoryPromoteOut(BaseModel):
    """POST /memory/{id}/promote 응답 — 복제본 + audit 식별자."""

    new_memory_id: uuid.UUID
    audit_id: uuid.UUID
    status: str
