# Memory API 입출력 스키마 (Pydantic V2)
"""Memory 도메인 입출력 스키마."""
import uuid
from datetime import datetime

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
