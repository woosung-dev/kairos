# Sprint 15 Recall-first wedge — voice/text 메모 + AI distill + recall 이벤트 모델
"""Memory 도메인 SQLModel 정의.

- MemoryItem: voice/text 메모 본체 (raw_content + distilled_json + status)
- MemoryAICall: transcription/distill/embedding 호출 추적 (C2)
- MemoryEvent: capture/recall/promote 이벤트 (C7 DB-backed metrics)
- PromotionAudit: R6 1-button promote audit row
- MemoryQueryEmbeddingCache: query 임베딩 7일 캐시 (C3, pgvector 1536d)

주의: `metadata`는 SQLModel 예약어 — `event_metadata` 사용.
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # 패키지 미설치 시 fallback


class MemoryItem(SQLModel, table=True):
    """Recall-first wedge 핵심 — voice/text 메모 1개 단위."""

    __tablename__ = "memory_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False, index=True
    )
    workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False, index=True
    )
    type: str = Field(nullable=False)  # 'voice' | 'text'
    raw_content: str = Field(
        sa_column=Column(Text, nullable=False, server_default="")
    )
    distilled_json: dict | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    r2_audio_key: str | None = None
    embedding_chunk_id: uuid.UUID | None = Field(
        default=None, foreign_key="embedding_chunks.id"
    )
    # processing | transcription_pending | embedding_pending |
    # embedding_failed | active | archived
    status: str = Field(default="processing", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None


class MemoryAICall(SQLModel, table=True):
    """AI 호출 추적 — cost/latency/usage_metadata (C2)."""

    __tablename__ = "memory_ai_calls"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    memory_id: uuid.UUID = Field(
        foreign_key="memory_items.id", nullable=False
    )
    workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False
    )
    # 'transcription' | 'distill' | 'embedding'
    call_type: str = Field(nullable=False)
    model_name: str | None = None
    elapsed_ms: int = Field(nullable=False)
    input_tokens: int = Field(default=0, nullable=False)
    output_tokens: int = Field(default=0, nullable=False)
    status: str = Field(default="success", nullable=False)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryEvent(SQLModel, table=True):
    """capture/recall/promote 이벤트 — Cloud Run stateless 정합 (C7)."""

    __tablename__ = "memory_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False
    )
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    # 'capture' | 'recall' | 'promote'
    event_type: str = Field(nullable=False)
    latency_ms: int | None = None
    # SQLModel `metadata` 예약어 회피 — event_metadata 사용
    event_metadata: dict | None = Field(
        default=None, sa_column=Column(JSONB, nullable=True)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PromotionAudit(SQLModel, table=True):
    """R6 1-button promote audit — memory → team workspace 승격 기록."""

    __tablename__ = "promotion_audit"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    memory_id: uuid.UUID = Field(
        foreign_key="memory_items.id", nullable=False
    )
    source_workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False
    )
    target_workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False
    )
    target_project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id"
    )
    promoted_by_user_id: uuid.UUID = Field(
        foreign_key="users.id", nullable=False
    )
    promoted_note_id: uuid.UUID | None = Field(
        default=None, foreign_key="notes.id"
    )
    # 'pending' | 'processing' | 'completed' | 'failed'
    embedding_status: str = Field(default="pending", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MemoryQueryEmbeddingCache(SQLModel, table=True):
    """Recall query 임베딩 캐시 — workspace + normalized query composite PK (C3)."""

    __tablename__ = "memory_query_embedding_cache"

    workspace_id: uuid.UUID = Field(
        foreign_key="workspaces.id", nullable=False, primary_key=True
    )
    normalized_query: str = Field(
        sa_column=Column(Text, nullable=False, primary_key=True)
    )
    embedding: list[float] = Field(
        sa_column=Column(Vector(1536) if Vector else Text, nullable=False)
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
