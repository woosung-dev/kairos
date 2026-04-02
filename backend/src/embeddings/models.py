# backend/src/embeddings/models.py
"""임베딩 청크 + 시맨틱 캐시 모델."""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None  # 패키지 미설치 시 fallback


class EmbeddingChunk(SQLModel, table=True):
    """계층적 임베딩 청크. Level 2(문단)가 검색 대상."""

    __tablename__ = "embedding_chunks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id", index=True
    )
    source_id: uuid.UUID = Field(nullable=False)
    source_type: str = Field(nullable=False)  # 'meeting' | 'note' | 'action'
    chunk_text: str = Field(sa_column=Column(Text, nullable=False))
    chunk_index: int = Field(default=0)
    chunk_level: int = Field(default=2)  # 0=문서, 1=섹션/화자, 2=문단
    parent_chunk_id: uuid.UUID | None = Field(
        default=None, foreign_key="embedding_chunks.id", index=True
    )
    embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(1536)) if Vector else Column(Text),
    )
    metadata_json: dict = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow)


def _default_expires_at() -> datetime:
    return datetime.utcnow() + timedelta(days=7)


class SemanticCache(SQLModel, table=True):
    """시맨틱 캐시. 유사 질문 → 캐시 답변 반환."""

    __tablename__ = "semantic_caches"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workspace_id: uuid.UUID = Field(foreign_key="workspaces.id", index=True)
    project_id: uuid.UUID | None = Field(
        default=None, foreign_key="projects.id"
    )
    question: str = Field(sa_column=Column(Text, nullable=False))
    question_embedding: list[float] | None = Field(
        default=None,
        sa_column=Column(Vector(1536)) if Vector else Column(Text),
    )
    answer: str = Field(sa_column=Column(Text, nullable=False))
    sources: list = Field(default_factory=list, sa_type=JSON)
    hit_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(default_factory=_default_expires_at)
